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
