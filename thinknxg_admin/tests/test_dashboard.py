import frappe
from frappe.tests import IntegrationTestCase

from thinknxg_admin.api import dashboard
from thinknxg_admin.api.utils import SYSTEM_ACCOUNTS


class TestDashboardFigures(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def test_total_users_matches_direct_query(self):
		frappe.form_dict.refresh = 1
		kpis = dashboard.get_kpis(days=30)
		expected = frappe.db.count("User", {"enabled": 1, "user_type": "System User", "name": ["not in", SYSTEM_ACCOUNTS]})
		self.assertEqual(kpis["total_users"]["value"], expected)

	def test_missing_doctype_is_none_not_zero(self):
		from thinknxg_admin.api.utils import safe_count

		self.assertIsNone(safe_count("No Such DocType For thinkNXG"))
