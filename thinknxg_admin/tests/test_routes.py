"""Internal routing: every server-built link stays inside the Command Center,
old Desk addresses map to internal pages, and the document API refuses users
without read permission."""

import frappe
from frappe.tests import IntegrationTestCase

from thinknxg_admin.api import docs, routes
from thinknxg_admin.api.utils import desk_route

PLAIN_USER = "thinknxg-routes-plain@example.com"


class TestInternalRoutes(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.db.exists("User", PLAIN_USER):
			frappe.get_doc({"doctype": "User", "email": PLAIN_USER, "first_name": "Plain", "send_welcome_email": 0, "user_type": "System User"}).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_desk_route_is_internal(self):
		for dt in ("User", "Role", "ToDo", "Note", "File", "Error Log"):
			self.assertTrue(desk_route(dt).startswith("/thinknxg/"), dt)
			self.assertTrue(desk_route(dt, "x").startswith("/thinknxg/"), dt)

	def test_users_and_roles_open_in_their_panel(self):
		self.assertEqual(routes.internal_route("User", "a@example.com"), "/thinknxg/admin/users?open=a%40example.com")
		self.assertTrue(routes.internal_route("Role", "Accounts User").startswith("/thinknxg/admin/roles?open="))

	def test_other_core_records_open_in_generic_form(self):
		self.assertEqual(routes.internal_route("Error Log", "E1"), "/thinknxg/admin/doc/error-log/E1")
		self.assertEqual(routes.internal_route("Workflow", new=True), "/thinknxg/admin/doc/workflow/new")

	def test_module_doctypes_route_to_their_module(self):
		if "erpnext" not in frappe.get_installed_apps():
			self.skipTest("thinkNXG ERP not installed")
		self.assertEqual(routes.internal_route("Sales Invoice"), "/thinknxg/erp/accounting/sales-invoice")
		self.assertEqual(routes.internal_route("Sales Invoice", "SINV-1"), "/thinknxg/erp/accounting/sales-invoice/SINV-1")
		self.assertEqual(routes.internal_route("Sales Invoice", new=True), "/thinknxg/erp/accounting/sales-invoice/new")
		self.assertIn("status=Overdue", routes.internal_route("Sales Invoice", filters={"status": "Overdue"}))

	def test_desk_only_tools_stay_in_desk(self):
		self.assertTrue(routes.internal_route("DocType", "User").startswith("/desk/"))

	def test_legacy_desk_paths(self):
		self.assertEqual(routes.from_desk_path("/app/user"), "/thinknxg/admin/users")
		self.assertTrue(routes.from_desk_path("/desk/no-such-thing-xyz").startswith("/thinknxg/not-found"))
		if "erpnext" in frappe.get_installed_apps():
			self.assertEqual(routes.from_desk_path("/desk/sales-invoice/SINV-9"), "/thinknxg/erp/accounting/sales-invoice/SINV-9")
			self.assertEqual(routes.from_desk_path("/desk/accounting"), "/thinknxg/erp/accounting")
			self.assertTrue(routes.from_desk_path("/desk/query-report/General Ledger").startswith("/thinknxg/erp/reports/"))

	def test_registry_lists_only_readable_doctypes(self):
		frappe.set_user(PLAIN_USER)
		reg = routes.get_registry([{"key": "erp", "access": "limited"}, {"key": "hr", "access": "team"}])
		for dt in reg["doctypes"]:
			self.assertTrue(frappe.has_permission(dt, "read"), dt)
		for mod in reg["modules"].get("hr", []):
			self.assertNotIn(mod["key"], ("payroll", "recruitment", "performance", "lifecycle", "employees", "training"))

	def test_document_api_needs_read_permission(self):
		frappe.set_user(PLAIN_USER)
		for call in (lambda: docs.get_list_meta("Error Log"), lambda: docs.get_list("Error Log"), lambda: docs.get_form_meta("Error Log"), lambda: docs.get_new_doc("Error Log")):
			with self.assertRaises(frappe.PermissionError):
				call()

	def test_document_api_resolves_slugs(self):
		self.assertEqual(docs.resolve_doctype("error-log"), "Error Log")
		with self.assertRaises(frappe.DoesNotExistError):
			docs.resolve_doctype("no-such-doctype-xyz")

	def test_list_filters_only_on_readable_fields(self):
		clean = docs._clean_filters("ToDo", [["password", "=", "x"], ["status", "=", "Open"], ["status", "; drop", "x"]])
		self.assertEqual(clean, [["ToDo", "status", "=", "Open"]])

	def test_request_cache_on_frappe_local(self):
		from thinknxg_admin.api.utils import request_cache

		request_cache("_nxg_test_cache")["k"] = 1
		self.assertEqual(request_cache("_nxg_test_cache"), {"k": 1})
		self.assertTrue(routes.internal_route("ToDo").startswith("/thinknxg/"))

	def test_resolve_doctype_returns_stored_name(self):
		# Lookups ignore case: "workspace" must come back as "Workspace", or
		# frappe.new_doc cannot import the controller (ImportError: workspace).
		self.assertEqual(docs.resolve_doctype("workspace"), "Workspace")
		self.assertEqual(docs.resolve_doctype("todo"), "ToDo")
		self.assertEqual(docs.resolve_doctype("error-log"), "Error Log")
		self.assertEqual(docs.get_new_doc("workspace").get("doctype"), "Workspace")

	def test_rebrand(self):
		from thinknxg_admin.api.brand import app_title, rebrand

		self.assertEqual(rebrand("Frappe HR"), "thinkNXG HR")
		self.assertEqual(rebrand("Frappe Cloud Marketplace"), "thinkNXG Cloud Marketplace")
		self.assertEqual(rebrand("frappe.client"), "frappe.client")
		self.assertEqual(app_title("helpdesk", "Helpdesk"), "thinkDesk")


class TestBrandImages(IntegrationTestCase):
	def test_stock_detection(self):
		from thinknxg_admin.install import _is_stock

		self.assertTrue(_is_stock(None))
		self.assertTrue(_is_stock("/assets/frappe/images/thinkNXG-favicon.png"))
		self.assertFalse(_is_stock("/files/company-logo.png"))

	def test_apply_sets_navbar_logo(self):
		from thinknxg_admin.install import LOGO, apply_brand_images

		frappe.db.set_single_value("Navbar Settings", "app_logo", None)
		apply_brand_images()
		self.assertEqual(frappe.db.get_single_value("Navbar Settings", "app_logo"), LOGO)
