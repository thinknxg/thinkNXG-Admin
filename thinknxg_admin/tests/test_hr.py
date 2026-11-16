"""HR Command Center: refused without access, payroll withheld without the
payroll gate, team view limited to direct reports and non-sensitive areas."""

import unittest

import frappe
from frappe.tests import IntegrationTestCase

from thinknxg_admin.api import hr
from thinknxg_admin.api.figures import Restricted

PLAIN_USER = "thinknxg-hr-plain@example.com"


@unittest.skipUnless("hrms" in frappe.get_installed_apps(), "thinkNXG HR not installed")
class TestHrCommandCenter(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.db.exists("User", PLAIN_USER):
			frappe.get_doc({"doctype": "User", "email": PLAIN_USER, "first_name": "Plain", "send_welcome_email": 0, "user_type": "System User"}).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_plain_user_refused_everywhere(self):
		frappe.set_user(PLAIN_USER)
		for call in (
			lambda: hr.get_kpis(),
			lambda: hr.get_section("employee"),
			lambda: hr.get_pending(),
			lambda: hr.get_approvals(),
			lambda: hr.apply_approval("Leave Application", "X", "Approve"),
		):
			with self.assertRaises(frappe.PermissionError):
				call()

	def test_administrator_sections_run(self):
		frappe.set_user("Administrator")
		out = hr.get_kpis(days=30)
		for key in hr.KPIS:
			self.assertIn(key, out)
		for section in hr.SECTIONS:
			if section == "team":
				continue
			self.assertIsInstance(hr.get_section(section, days=30), dict, section)

	def test_payroll_withheld_without_gate(self):
		ctx = frappe._dict(payroll=False, team=False)
		with self.assertRaises(Restricted):
			hr.section_payroll(ctx)

	def test_team_scope_never_reaches_sensitive_doctypes(self):
		ctx = frappe._dict(team=True, employees=["EMP-X"], company=None, department=None)
		for dt in ("Salary Slip", "Payroll Entry", "Job Applicant", "Appraisal", "Employee Grievance"):
			with self.assertRaises(Restricted, msg=dt):
				hr._need(ctx, dt)
		self.assertEqual(hr._f(ctx, "Attendance")["employee"], ["in", ["EMP-X"]])
		self.assertEqual(hr._f(ctx, "Employee")["name"], ["in", ["EMP-X"]])

	def test_team_view_hides_hr_only_sections(self):
		self.assertNotIn("payroll", hr.TEAM_SECTIONS)
		self.assertNotIn("Salary Slip", hr.TEAM_DOCTYPES)

	def test_non_hr_document_refused(self):
		frappe.set_user("Administrator")
		with self.assertRaises(frappe.PermissionError):
			hr.apply_approval("User", "Administrator", "Approve")

	def test_unknown_section_refused(self):
		with self.assertRaises(frappe.ValidationError):
			hr.get_section("salaries")
