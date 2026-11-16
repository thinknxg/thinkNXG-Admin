import frappe
from frappe import _
from frappe.model.document import Document


class thinkNXGAdminSettings(Document):
	def validate(self):
		roles = [r.role for r in self.admin_roles or []]
		blocked = {"Guest", "All"} & set(roles)
		if blocked:
			frappe.throw(_("{0} cannot be an admin role.").format(", ".join(sorted(blocked))))
		for table, label in (("hr_roles", _("HR Command Center role")), ("payroll_roles", _("payroll role"))):
			bad = {"Guest", "All"} & {r.role for r in self.get(table) or []}
			if bad:
				frappe.throw(_("{0} cannot be a {1}.").format(", ".join(sorted(bad)), label))
		for row in self.landing_rules or []:
			if row.role in ("Guest",):
				frappe.throw(_("Guest cannot have a default command center."))
