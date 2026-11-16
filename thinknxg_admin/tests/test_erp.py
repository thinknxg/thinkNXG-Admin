"""ERP Command Center: refused without access, figures withheld without read
permission, approvals limited to thinkNXG ERP documents."""

import unittest

import frappe
from frappe.tests import IntegrationTestCase

from thinknxg_admin.api import erp

PLAIN_USER = "thinknxg-erp-plain@example.com"


@unittest.skipUnless("erpnext" in frappe.get_installed_apps(), "thinkNXG ERP not installed")
class TestErpCommandCenter(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.db.exists("User", PLAIN_USER):
			frappe.get_doc({"doctype": "User", "email": PLAIN_USER, "first_name": "Plain", "send_welcome_email": 0, "user_type": "System User"}).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_plain_user_refused_everywhere(self):
		frappe.set_user(PLAIN_USER)
		calls = [
			lambda: erp.get_kpis(),
			lambda: erp.get_section("sales"),
			lambda: erp.get_pending(),
			lambda: erp.get_approvals(),
			lambda: erp.apply_approval("Sales Order", "X", "Approve"),
		]
		for call in calls:
			with self.assertRaises(frappe.PermissionError):
				call()

	def test_administrator_gets_every_kpi(self):
		frappe.set_user("Administrator")
		if not frappe.get_all("Company", limit=1):
			self.skipTest("no company")
		out = erp.get_kpis(days=30)
		for key in erp.KPIS:
			self.assertIn(key, out)
			self.assertNotIn("restricted", out[key], key)
		self.assertIn("currency", out["_context"])

	def test_every_section_runs_for_administrator(self):
		frappe.set_user("Administrator")
		if not frappe.get_all("Company", limit=1):
			self.skipTest("no company")
		for section in erp.SECTIONS:
			self.assertIsInstance(erp.get_section(section, days=30), dict, section)

	def test_unknown_section_refused(self):
		with self.assertRaises(frappe.ValidationError):
			erp.get_section("payroll")

	def test_restricted_figure_sends_no_number(self):
		def refused(ctx):
			frappe.throw("no", frappe.PermissionError)

		self.assertEqual(erp._figure(refused, frappe._dict()), {"restricted": True})

		def missing(ctx):
			raise erp.Missing

		self.assertEqual(erp._figure(missing, frappe._dict()), {"value": None})

	def test_approval_outside_erp_refused(self):
		frappe.set_user("Administrator")
		with self.assertRaises(frappe.PermissionError):
			erp.apply_approval("User", "Administrator", "Approve")

	def test_forged_company_refused(self):
		frappe.set_user("Administrator")
		with self.assertRaises(frappe.PermissionError):
			erp.get_kpis(company="No Such Company Ltd")
