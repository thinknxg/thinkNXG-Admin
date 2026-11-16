"""My Workspace: the personal landing page for every desk user (admins included).

Everything here is the session user's own: their open tasks, approvals waiting for
their roles, recent work, the workspaces their roles can open, and their own
preferences. Nothing reads another user's data.
"""

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from thinknxg_admin.api.utils import desk_route, doctype_exists, has_field, require_login, slug

PREF_FIELDS = ("language", "time_zone", "desk_theme", "default_workspace", "default_app")


@frappe.whitelist()
def get_my_workspace():
	require_login()
	user = frappe.session.user
	roles = frappe.get_roles(user)
	out = {}

	out["todos"] = []
	if doctype_exists("ToDo"):
		rows = frappe.get_all("ToDo", filters={"allocated_to": user, "status": "Open"},
			fields=["name", "description", "reference_type", "reference_name", "date", "priority", "assigned_by_full_name", "creation"],
			order_by="creation desc", limit=50)
		today = getdate(nowdate())
		for r in rows:
			r["description"] = frappe.utils.strip_html(r.description or "")[:200]
			r["overdue"] = bool(r.date and getdate(r.date) < today)
			r["route"] = desk_route(r.reference_type, r.reference_name) if r.reference_type and r.reference_name else desk_route("ToDo", r.name)
		# due-dated first (earliest first), then undated, newest first
		rows.sort(key=lambda r: (r.date is None, str(r.date or ""), -frappe.utils.get_datetime(r.creation).timestamp()))
		out["todos"] = rows

	out["approvals"] = []
	if doctype_exists("Workflow Action"):
		out["approvals"] = frappe.db.sql(
			"""select wa.name, wa.reference_doctype, wa.reference_name, wa.workflow_state, wa.creation
			from `tabWorkflow Action` wa
			where wa.status = 'Open' and (wa.user = %(user)s or exists (
				select 1 from `tabWorkflow Action Permitted Role` r where r.parent = wa.name and r.role in %(roles)s))
			order by wa.creation desc limit 30""",
			{"user": user, "roles": tuple(roles) or ("",)}, as_dict=True)
		for a in out["approvals"]:
			a["route"] = desk_route(a.reference_doctype, a.reference_name)

	out["recent"] = []
	if doctype_exists("Version"):
		seen = set()
		for v in frappe.get_all("Version", filters={"owner": user}, fields=["ref_doctype", "docname", "creation"], order_by="creation desc", limit=60):
			key = (v.ref_doctype, v.docname)
			if key in seen:
				continue
			seen.add(key)
			out["recent"].append({**v, "route": desk_route(v.ref_doctype, v.docname)})
			if len(out["recent"]) >= 10:
				break

	out["visited"] = []
	if doctype_exists("Route History"):
		seen = set()
		for (route, created) in frappe.db.sql("select route, creation from `tabRoute History` where user = %s order by creation desc limit 120", user):
			if route in seen or not route:
				continue
			seen.add(route)
			out["visited"].append({"route": f"/desk/{route.lstrip('/')}", "label": _route_label(route), "creation": created})
			if len(out["visited"]) >= 10:
				break

	out["workspaces"] = []
	if doctype_exists("Workspace"):
		ws = frappe.get_all("Workspace", filters={"public": 1, "is_hidden": 0} if has_field("Workspace", "is_hidden") else {"public": 1},
			fields=["name", "label", "module", "icon", "parent_page", "sequence_id"], order_by="sequence_id asc")
		ws_roles = {}
		for r in frappe.get_all("Has Role", filters={"parenttype": "Workspace"}, fields=["parent", "role"]):
			ws_roles.setdefault(r.parent, set()).add(r.role)
		blocked = set(frappe.get_all("Block Module", filters={"parenttype": "User", "parent": user}, pluck="module"))
		mine = set(roles)
		for w in ws:
			allowed = ws_roles.get(w.name)
			if (allowed and not (allowed & mine)) or (w.module and w.module in blocked) or w.parent_page:
				continue
			out["workspaces"].append({**w, "route": f"/desk/{slug(w.name)}"})

	info = frappe.db.get_value("User", user, ["full_name", "user_image", "email", "last_login", *[f for f in PREF_FIELDS if has_field("User", f)]], as_dict=True) or {}
	out["user"] = {"name": user, "full_name": info.get("full_name"), "image": info.get("user_image"), "email": info.get("email"), "last_login": info.get("last_login")}
	out["preferences"] = {f: info.get(f) for f in PREF_FIELDS}
	out["unread_notifications"] = frappe.db.count("Notification Log", {"for_user": user, "read": 0}) if doctype_exists("Notification Log") else None
	return out


def _route_label(route: str) -> str:
	parts = [p for p in route.strip("/").split("/") if p]
	if not parts:
		return "Desk"
	head = parts[0]
	if head in ("query-report", "dashboard-view") and len(parts) > 1:
		return parts[1]
	name = frappe.unscrub(head.replace("-", "_"))
	return f"{name} · {parts[1]}" if len(parts) > 1 and parts[1] not in ("view", "new") else name


@frappe.whitelist()
def get_preference_options():
	require_login()
	from frappe.core.doctype.user.user import get_timezones

	return {
		"languages": frappe.get_all("Language", filters={"enabled": 1} if has_field("Language", "enabled") else {}, fields=["name", "language_name"], order_by="language_name asc") if doctype_exists("Language") else [],
		"time_zones": get_timezones()["timezones"],
		"apps": frappe.get_installed_apps(),
	}


@frappe.whitelist(methods=["POST"])
def update_my_preferences(values):
	"""Update the session user's own display preferences (a fixed list of fields)."""
	require_login()
	values = frappe.parse_json(values) or {}
	doc = frappe.get_doc("User", frappe.session.user)
	for f in PREF_FIELDS:
		if f in values and doc.meta.has_field(f):
			doc.set(f, values[f] or None)
	# Users may always edit these fields on their own record; nothing else is touched.
	doc.save(ignore_permissions=True)
	return {f: doc.get(f) for f in PREF_FIELDS}


@frappe.whitelist(methods=["POST"])
def set_todo_status(name: str, status: str = "Closed"):
	require_login()
	if status not in ("Open", "Closed", "Cancelled"):
		frappe.throw(_("Invalid status"))
	doc = frappe.get_doc("ToDo", name)
	if doc.allocated_to != frappe.session.user:
		doc.check_permission("write")
	doc.status = status
	doc.save(ignore_permissions=doc.allocated_to == frappe.session.user)
	return True
