"""Command center gates are decided on the server and cannot be widened from the browser."""

import json

import frappe
from frappe.tests import IntegrationTestCase

from thinknxg_admin.api import centers

PLAIN_USER = "thinknxg-centers-plain@example.com"


class TestCommandCenters(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.db.exists("User", PLAIN_USER):
			frappe.get_doc({"doctype": "User", "email": PLAIN_USER, "first_name": "Plain", "send_welcome_email": 0, "user_type": "System User"}).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_administrator_gets_admin_center(self):
		frappe.set_user("Administrator")
		keys = [c["key"] for c in centers.get_centers()]
		self.assertIn("admin", keys)
		self.assertEqual(centers.center_access("admin"), "full")

	def test_plain_user_has_no_center(self):
		frappe.set_user(PLAIN_USER)
		self.assertEqual(centers.get_centers(), [])
		for key in centers.CENTER_KEYS:
			self.assertIsNone(centers.center_access(key))
			with self.assertRaises(frappe.PermissionError):
				centers.require_center(key)
			with self.assertRaises(frappe.PermissionError):
				centers.get_filter_options(key)

	def test_preferences_refuse_unpermitted_center(self):
		frappe.set_user(PLAIN_USER)
		with self.assertRaises(frappe.PermissionError):
			centers.save_preferences(default_center="admin")
		with self.assertRaises(frappe.PermissionError):
			centers.save_preferences(last_center="erp")

	def test_preferences_are_scoped_to_session_user(self):
		frappe.set_user(PLAIN_USER)
		prefs = centers.save_preferences(state=json.dumps({"admin": {"days": 9999, "last_route": "//evil.example"}, "bogus": {"x": 1}}))
		self.assertEqual(prefs["state"], {"admin": {"days": 366}})
		self.assertTrue(frappe.db.exists(centers.PREFERENCE, PLAIN_USER))
		self.assertFalse(frappe.db.exists(centers.PREFERENCE, "Administrator"))

	def test_company_outside_user_permissions_refused(self):
		frappe.set_user(PLAIN_USER)
		with self.assertRaises(frappe.PermissionError):
			centers.validate_company("Company That Does Not Exist")

	def test_erp_gate_does_not_use_app_check(self):
		# A desk user with no ERP read rights must not get the ERP center, even
		# though erpnext.check_app_permission would allow them.
		frappe.set_user(PLAIN_USER)
		self.assertIsNone(centers.center_access("erp"))

	def test_payroll_hidden_without_gate(self):
		frappe.set_user(PLAIN_USER)
		self.assertFalse(centers.can_view_payroll())

	def test_navigation_never_leaks_internal_flags(self):
		frappe.set_user("Administrator")
		for c in centers.get_centers():
			for s in c["navigation"]:
				for i in s["items"]:
					for flag in ("admin", "hr_only", "payroll"):
						self.assertNotIn(flag, i)
