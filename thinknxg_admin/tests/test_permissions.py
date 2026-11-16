"""Every Command Center endpoint must refuse non-admins and guests."""

import frappe
from frappe.tests import IntegrationTestCase

from thinknxg_admin.api import dashboard, health

ADMIN_ENDPOINTS = [
	dashboard.get_kpis,
	dashboard.get_activity,
	dashboard.get_access_overview,
	dashboard.get_organization_overview,
	dashboard.get_pending_actions,
	dashboard.get_admin_timeline,
	health.get_live_health,
	health.get_full_report,
]

PLAIN_USER = "thinknxg-admin-test-user@example.com"


class TestEndpointPermissions(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.db.exists("User", PLAIN_USER):
			frappe.get_doc({"doctype": "User", "email": PLAIN_USER, "first_name": "Plain", "send_welcome_email": 0, "user_type": "System User"}).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_admin_allowed(self):
		frappe.set_user("Administrator")
		for fn in ADMIN_ENDPOINTS:
			fn()

	def test_plain_user_denied(self):
		frappe.set_user(PLAIN_USER)
		for fn in ADMIN_ENDPOINTS:
			with self.assertRaises(frappe.PermissionError, msg=fn.__name__):
				fn()

	def test_guest_denied(self):
		frappe.set_user("Guest")
		for fn in ADMIN_ENDPOINTS:
			with self.assertRaises(frappe.PermissionError, msg=fn.__name__):
				fn()

	def test_navigation_hides_admin_items_from_plain_user(self):
		from thinknxg_admin.api.navigation import get_navigation

		frappe.set_user(PLAIN_USER)
		keys = {i["key"] for s in get_navigation() for i in s["items"]}
		self.assertNotIn("command-center", keys)
		self.assertNotIn("system-health", keys)


class TestPhase6Permissions(IntegrationTestCase):
	"""Phase 6 screens: every read and write must refuse plain users and guests."""

	def tearDown(self):
		frappe.set_user("Administrator")

	def _calls(self):
		from thinknxg_admin.api import apps, organization, roles, users, workspaces

		return [
			lambda: users.list_users(),
			lambda: users.get_user("Administrator"),
			lambda: users.get_form_options(),
			lambda: users.list_user_permissions(),
			lambda: users.bulk_update(["Administrator"], "enable"),
			lambda: users.update_user("Administrator", {"first_name": "X"}),
			lambda: roles.list_roles(),
			lambda: roles.get_role("System Manager"),
			lambda: roles.create_role("thinkNXG Test Role"),
			lambda: roles.list_role_profiles(),
			lambda: organization.get_organization(),
			lambda: workspaces.get_overview(),
			lambda: workspaces.grant_workspace_manager(),
			lambda: apps.get_apps(),
		]

	def test_plain_user_denied(self):
		frappe.set_user(PLAIN_USER)
		for i, fn in enumerate(self._calls()):
			with self.assertRaises(frappe.PermissionError, msg=f"call {i}"):
				fn()

	def test_guest_denied(self):
		frappe.set_user("Guest")
		for i, fn in enumerate(self._calls()):
			with self.assertRaises(frappe.PermissionError, msg=f"call {i}"):
				fn()

	def test_admin_reads(self):
		from thinknxg_admin.api import apps, organization, roles, users, workspaces

		frappe.set_user("Administrator")
		self.assertIn("rows", users.list_users())
		self.assertTrue(roles.list_roles())
		organization.get_organization()
		workspaces.get_overview()
		self.assertTrue(apps.get_apps()["apps"])

	def test_cannot_remove_last_system_manager(self):
		from thinknxg_admin.api.users import _guard_remove_sm, _enabled_system_managers

		frappe.set_user("Administrator")
		managers = list(_enabled_system_managers())
		if managers:
			with self.assertRaises(frappe.ValidationError):
				_guard_remove_sm(managers)
