import frappe
from frappe import _
from frappe.model.document import Document


class thinkNXGAdminSettings(Document):
	def validate(self):
		roles = [r.role for r in self.admin_roles or []]
		blocked = {"Guest", "All"} & set(roles)
		if blocked:
			frappe.throw(_("{0} cannot be an admin role.").format(", ".join(sorted(blocked))))
