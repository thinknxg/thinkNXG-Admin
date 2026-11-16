import frappe
from frappe import _
from frappe.model.document import Document


class thinkNXGUserPreference(Document):
	"""Per-user command center choices. Written only through
	thinknxg_admin.api.centers.save_preferences, which scopes every write to the
	session user; System Managers can review or delete rows in the Desk."""

	def validate(self):
		if self.default_center and self.default_center not in ("admin", "erp", "hr"):
			frappe.throw(_("Unknown command center."))
