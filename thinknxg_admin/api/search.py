"""Command palette search. Every result is permission-checked on the server."""

import frappe

from thinknxg_admin.api.utils import desk_route, doctype_exists, require_login, slug


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
			results.append({"type": "DocType", "label": d.name, "description": d.module, "route": desk_route(d.name), "icon": "file-text"})

	if frappe.has_permission("User", "read"):
		for u in frappe.get_list(
			"User", or_filters={"name": ["like", like], "full_name": ["like", like]},
			filters={"name": ["not in", ["Guest"]]}, fields=["name", "full_name", "enabled", "user_type"], limit=limit,
		):
			results.append({
				"type": "User", "label": u.full_name or u.name, "description": u.name + ("" if u.enabled else " · disabled"),
				"route": desk_route("User", u.name), "icon": "user",
			})

	if doctype_exists("Report"):
		for r in frappe.get_list("Report", filters={"name": ["like", like], "disabled": 0}, fields=["name", "ref_doctype", "report_type"], limit=limit):
			route = f"/desk/query-report/{r.name}" if r.report_type in ("Script Report", "Query Report") else f"/desk/{slug(r.ref_doctype)}/view/report?report_name={r.name}"
			results.append({"type": "Report", "label": r.name, "description": r.ref_doctype, "route": route, "icon": "chart-column"})

	if doctype_exists("Workspace"):
		for w in frappe.get_list("Workspace", filters={"label": ["like", like]}, fields=["name", "label", "public"], limit=limit):
			results.append({"type": "Workspace", "label": w.label or w.name, "description": "Public workspace" if w.public else "Private workspace", "route": f"/desk/{slug(w.name)}", "icon": "panels-top-left"})

	return results
