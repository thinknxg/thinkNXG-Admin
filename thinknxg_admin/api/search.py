"""Command palette search across the Admin, ERP and HR command centers.

Every result is permission-checked on the server: DocTypes need read access,
records come from frappe.get_list (role permissions + User Permissions), and
record search only runs for centers the server grants the user. Employees are
searched only for HR roles, never for the team-only manager view.
"""

import frappe

from thinknxg_admin.api.centers import center_access
from thinknxg_admin.api.utils import desk_route, doctype_exists, has_field, require_login, slug

# (DocType, title field, icon) searched by name or title, per center.
RECORDS = {
	"erp": [
		("Customer", "customer_name", "user-round"),
		("Supplier", "supplier_name", "truck"),
		("Item", "item_name", "package"),
		("Sales Invoice", "customer_name", "receipt"),
		("Sales Order", "customer_name", "shopping-cart"),
		("Purchase Order", "supplier_name", "shopping-bag"),
		("Project", "project_name", "folder-kanban"),
		("Lead", "lead_name", "user-plus"),
	],
	"hr": [
		("Employee", "employee_name", "users"),
		("Job Opening", "job_title", "briefcase"),
		("Job Applicant", "applicant_name", "user-search"),
	],
}
CENTER_LABEL = {"erp": "ERP", "hr": "HR"}


def _records(center, like, per_type):
	out = []
	for doctype, title, icon in RECORDS[center]:
		if not doctype_exists(doctype) or not frappe.has_permission(doctype, "read"):
			continue
		has_title = has_field(doctype, title)
		or_filters = {"name": ["like", like]}
		if has_title:
			or_filters[title] = ["like", like]
		fields = ["name"] + ([title] if has_title else [])
		try:
			rows = frappe.get_list(doctype, or_filters=or_filters, fields=fields, order_by="modified desc", limit_page_length=per_type)
		except frappe.PermissionError:
			frappe.clear_last_message()
			continue
		for r in rows:
			label = r.get(title) or r.name
			out.append({
				"type": doctype, "group": f"{CENTER_LABEL[center]} · {doctype}", "center": center,
				"label": label, "description": r.name if label != r.name else doctype,
				"route": desk_route(doctype, r.name), "icon": icon,
			})
	return out


@frappe.whitelist()
def search(query: str, limit: int = 6):
	require_login()
	q = (query or "").strip()
	if len(q) < 2:
		return []
	limit = max(1, min(int(limit or 6), 20))
	like = f"%{q}%"
	results = []

	for d in frappe.get_all(
		"DocType", filters={"name": ["like", like], "istable": 0}, fields=["name", "module", "issingle"],
		order_by="name asc", limit=limit * 3,
	):
		if len([r for r in results if r["type"] == "DocType"]) >= limit:
			break
		if frappe.has_permission(d.name, "read"):
			results.append({"type": "DocType", "group": "DocTypes", "label": d.name, "description": d.module, "route": desk_route(d.name), "icon": "file-text"})

	if frappe.has_permission("User", "read"):
		for u in frappe.get_list(
			"User", or_filters={"name": ["like", like], "full_name": ["like", like]},
			filters={"name": ["not in", ["Guest"]]}, fields=["name", "full_name", "enabled", "user_type"], limit=limit,
		):
			results.append({
				"type": "User", "group": "Users", "label": u.full_name or u.name, "description": u.name + ("" if u.enabled else " · disabled"),
				"route": desk_route("User", u.name), "icon": "user",
			})

	if doctype_exists("Report"):
		for r in frappe.get_list("Report", filters={"name": ["like", like], "disabled": 0}, fields=["name", "ref_doctype", "report_type"], limit=limit):
			route = f"/desk/query-report/{r.name}" if r.report_type in ("Script Report", "Query Report") else f"/desk/{slug(r.ref_doctype)}/view/report?report_name={r.name}"
			results.append({"type": "Report", "group": "Reports", "label": r.name, "description": r.ref_doctype, "route": route, "icon": "chart-column"})

	if doctype_exists("Workspace"):
		for w in frappe.get_list("Workspace", filters={"label": ["like", like]}, fields=["name", "label", "public"], limit=limit):
			results.append({"type": "Workspace", "group": "Workspaces", "label": w.label or w.name, "description": "Public workspace" if w.public else "Private workspace", "route": f"/desk/{slug(w.name)}", "icon": "panels-top-left"})

	# Business records, only for centers the server grants (HR roles only for HR).
	per_type = max(2, min(limit // 2, 4))
	if center_access("erp"):
		results += _records("erp", like, per_type)
	if center_access("hr") in ("full", "limited"):
		results += _records("hr", like, per_type)

	return results
