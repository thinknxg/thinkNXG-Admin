import frappe
from frappe.tests import IntegrationTestCase


class TestthinkNXGAdminSettings(IntegrationTestCase):
	def test_guest_cannot_be_admin_role(self):
		doc = frappe.get_single("thinkNXG Admin Settings")
		doc.set("admin_roles", [{"role": "Guest"}])
		self.assertRaises(frappe.ValidationError, doc.save)
