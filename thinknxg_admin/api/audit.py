"""Audit & Compliance Center.

One timeline over the framework's own audit tables - nothing is recorded twice:
  Activity Log     sign-ins, sign-outs, failed attempts (with IP)
  Permission Log   DocType permission and user permission changes
  Version          before/after changes on users, roles, workspaces, settings ... or any document
  Access Log       exports, report downloads, prints
  API Request Log  REST API calls (when API request logging is enabled)
"""

import json
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import add_days, cint, get_datetime, getdate, now_datetime

from thinknxg_admin.api.dashboard import ADMIN_DOCTYPES
from thinknxg_admin.api.utils import desk_route, doctype_exists, has_field, require_admin

CATEGORIES = {
	"authentication": "Sign-ins",
	"permissions": "Permissions",
	"access_control": "Users & roles",
	"configuration": "Configuration",
	"documents": "Documents",
	"data_access": "Data exports",
	"api": "API access",
}
ACCESS_CONTROL_DOCTYPES = {"User", "Role", "Role Profile", "User Permission", "Module Profile", "User Invitation"}
MAX_WINDOW = 2000


def _range(from_date, to_date):
	end = get_datetime(add_days(getdate(to_date), 1)) if to_date else now_datetime()
	start = get_datetime(getdate(from_date)) if from_date else end - timedelta(days=30)
	return start, end


def _names(users):
	users = {u for u in users if u}
	return dict(frappe.get_all("User", filters={"name": ["in", list(users)]}, fields=["name", "full_name"], as_list=True)) if users else {}


def _version_summary(data):
	try:
		d = json.loads(data or "{}")
	except Exception:
		return "Updated", []
	changes = []
	for field, old, new in (d.get("changed") or [])[:12]:
		changes.append({"field": frappe.unscrub(field), "old": _clip(old), "new": _clip(new)})
	if d.get("added"):
		tables = sorted({r[0] for r in d["added"] if r})
		return ("Added rows to " + ", ".join(tables)), changes
	if d.get("removed"):
		tables = sorted({r[0] for r in d["removed"] if r})
		return ("Removed rows from " + ", ".join(tables)), changes
	if changes:
		more = f" +{len(d['changed']) - 1} more" if len(d["changed"]) > 1 else ""
		return f"Changed {changes[0]['field']}{more}", changes
	if d.get("row_changed"):
		return "Updated child rows", changes
	return "Updated", changes


def _clip(v, n=120):
	if v is None:
		return None
	s = frappe.utils.strip_html(str(v))
	return s if len(s) <= n else s[: n - 1] + "…"


# ------------------------------------------------------------------ sources
def _activity(start, end, user, result, limit):
	if not doctype_exists("Activity Log"):
		return []
	f = {"creation": ["between", [start, end]], "operation": ["in", ["Login", "Logout"]]}
	if user:
		f["user"] = user
	if result == "failed":
		f["status"] = "Failed"
	elif result == "success":
		f["status"] = "Success"
	fields = ["name", "user", "full_name", "operation", "status", "subject", "creation"] + (["ip_address"] if has_field("Activity Log", "ip_address") else [])
	out = []
	for r in frappe.get_all("Activity Log", filters=f, fields=fields, order_by="creation desc", limit=limit):
		failed = r.status == "Failed"
		out.append({
			"id": f"activity:{r.name}", "source": "Activity Log", "category": "authentication",
			"actor": r.user, "actor_name": r.full_name or r.user,
			"action": ("Failed sign-in" if failed else ("Signed out" if r.operation == "Logout" else "Signed in")),
			"resource_type": "User", "resource": r.user, "timestamp": r.creation, "ip": r.get("ip_address"),
			"result": "Failed" if failed else "Success", "detail": _clip(r.subject, 200), "route": desk_route("Activity Log", r.name),
		})
	return out


def _permission(start, end, user, result, limit):
	if result == "failed" or not doctype_exists("Permission Log"):
		return []
	date_field = "changed_at" if has_field("Permission Log", "changed_at") else "creation"
	f = {date_field: ["between", [start, end]]}
	if user:
		f["changed_by"] = user
	out = []
	for r in frappe.get_all("Permission Log", filters=f, fields=["name", "changed_by", "changed_at", "creation", "for_doctype", "for_document", "reference_type", "reference", "status", "changes"], order_by=f"{date_field} desc", limit=limit):
		changes = []
		try:
			raw = json.loads(r.changes or "{}")
			before, after = raw.get("from") or {}, raw.get("to") or {}
			for k in list(dict.fromkeys([*before.keys(), *after.keys()]))[:12]:
				if before.get(k) != after.get(k):
					changes.append({"field": frappe.unscrub(k), "old": _clip(before.get(k)), "new": _clip(after.get(k))})
		except Exception:
			pass
		out.append({
			"id": f"permission:{r.name}", "source": "Permission Log", "category": "permissions", "actor": r.changed_by,
			"action": f"{r.status or 'Updated'} permission" + (f" on {r.for_doctype}" if r.for_doctype else ""),
			"resource_type": r.reference_type or r.for_doctype, "resource": r.reference or r.for_document,
			"timestamp": r.changed_at or r.creation, "result": "Success", "changes": changes[:12], "route": desk_route("Permission Log", r.name),
		})
	return out


def _versions(start, end, user, result, limit, category):
	if result == "failed" or not doctype_exists("Version"):
		return []
	f = {"creation": ["between", [start, end]]}
	if user:
		f["owner"] = user
	if category == "access_control":
		f["ref_doctype"] = ["in", [d for d in ACCESS_CONTROL_DOCTYPES if doctype_exists(d)]]
	elif category == "configuration":
		f["ref_doctype"] = ["in", [d for d in ADMIN_DOCTYPES if d not in ACCESS_CONTROL_DOCTYPES and doctype_exists(d)]]
	elif category == "documents":
		f["ref_doctype"] = ["not in", list(set(ADMIN_DOCTYPES) | ACCESS_CONTROL_DOCTYPES)]
	out = []
	for r in frappe.get_all("Version", filters=f, fields=["name", "owner", "ref_doctype", "docname", "creation", "data"], order_by="creation desc", limit=limit):
		summary, changes = _version_summary(r.data)
		cat = "access_control" if r.ref_doctype in ACCESS_CONTROL_DOCTYPES else ("configuration" if r.ref_doctype in ADMIN_DOCTYPES else "documents")
		out.append({
			"id": f"version:{r.name}", "source": "Version", "category": cat, "actor": r.owner, "action": summary,
			"resource_type": r.ref_doctype, "resource": r.docname, "timestamp": r.creation, "result": "Success",
			"changes": changes, "route": desk_route(r.ref_doctype, r.docname),
		})
	return out


def _access(start, end, user, result, limit):
	if result == "failed" or not doctype_exists("Access Log"):
		return []
	f = {"creation": ["between", [start, end]]}
	if user:
		f["user"] = user
	out = []
	for r in frappe.get_all("Access Log", filters=f, fields=["name", "user", "export_from", "reference_document", "file_type", "report_name", "page", "method", "creation"], order_by="creation desc", limit=limit):
		what = r.report_name or r.export_from or r.page or r.method or "data"
		out.append({
			"id": f"access:{r.name}", "source": "Access Log", "category": "data_access", "actor": r.user,
			"action": f"Exported {r.file_type or 'file'}" if r.file_type else "Accessed",
			"resource_type": r.export_from or ("Report" if r.report_name else "Page"), "resource": r.reference_document or what,
			"timestamp": r.creation, "result": "Success", "route": desk_route("Access Log", r.name),
		})
	return out


def _api(start, end, user, result, limit):
	if result == "failed" or not doctype_exists("API Request Log"):
		return []
	f = {"creation": ["between", [start, end]]}
	if user:
		f["user"] = user
	return [
		{
			"id": f"api:{r.name}", "source": "API Request Log", "category": "api", "actor": r.user,
			"action": f"{r.method or 'API'} request", "resource_type": "Endpoint", "resource": (r.path or "")[:160],
			"timestamp": r.creation, "result": "Success", "route": desk_route("API Request Log", r.name),
		}
		for r in frappe.get_all("API Request Log", filters=f, fields=["name", "user", "path", "method", "creation"], order_by="creation desc", limit=limit)
	]


def _collect(category, start, end, user, result, window):
	cats = [category] if category else list(CATEGORIES)
	events = []
	if "authentication" in cats:
		events += _activity(start, end, user, result, window)
	if "permissions" in cats:
		events += _permission(start, end, user, result, window)
	if any(c in cats for c in ("access_control", "configuration", "documents")):
		version_cat = category if category in ("access_control", "configuration", "documents") else None
		if not category:
			# the default feed covers administration, not every business document edit
			for c in ("access_control", "configuration"):
				events += _versions(start, end, user, result, window, c)
		else:
			events += _versions(start, end, user, result, window, version_cat)
	if "data_access" in cats:
		events += _access(start, end, user, result, window)
	if "api" in cats and category == "api":
		events += _api(start, end, user, result, window)
	events.sort(key=lambda e: str(e["timestamp"]), reverse=True)
	return events


@frappe.whitelist()
def get_events(category: str | None = None, user: str | None = None, result: str | None = None, from_date: str | None = None,
		to_date: str | None = None, search: str | None = None, start: int = 0, page_length: int = 50):
	require_admin()
	if category and category not in CATEGORIES:
		frappe.throw(_("Unknown category"))
	start_dt, end_dt = _range(from_date, to_date)
	start, page_length = cint(start), max(10, min(cint(page_length) or 50, 200))
	window = min(start + page_length + 1, MAX_WINDOW)
	events = _collect(category, start_dt, end_dt, user, result, window)
	if search:
		q = search.lower()
		events = [e for e in events if q in " ".join(str(e.get(k) or "") for k in ("actor", "action", "resource_type", "resource", "ip")).lower()]
	page = events[start : start + page_length]
	names = _names(e.get("actor") for e in page)
	for e in page:
		e.setdefault("actor_name", names.get(e.get("actor")) or e.get("actor"))
	return {"rows": page, "has_more": len(events) > start + page_length, "window_capped": window >= MAX_WINDOW, "categories": CATEGORIES}


@frappe.whitelist()
def export_events(category: str | None = None, user: str | None = None, result: str | None = None, from_date: str | None = None, to_date: str | None = None):
	"""Up to 2,000 events for CSV. Requires export permission on Activity Log."""
	require_admin()
	frappe.has_permission("Activity Log", "export", throw=True)
	start_dt, end_dt = _range(from_date, to_date)
	events = _collect(category, start_dt, end_dt, user, result, MAX_WINDOW)[:MAX_WINDOW]
	names = _names(e.get("actor") for e in events)
	for e in events:
		e.setdefault("actor_name", names.get(e.get("actor")) or e.get("actor"))
	if doctype_exists("Access Log"):
		# the export itself is an auditable event
		frappe.get_doc({"doctype": "Access Log", "user": frappe.session.user, "export_from": "Activity Log", "file_type": "CSV", "method": "thinknxg_admin.api.audit.export_events"}).insert(ignore_permissions=True)
	return events


@frappe.whitelist()
def get_summary(from_date: str | None = None, to_date: str | None = None):
	require_admin()
	start, end = _range(from_date, to_date)
	out = {"from": start, "to": end}

	def count(dt, f):
		return frappe.db.count(dt, f) if doctype_exists(dt) else None

	out["logins"] = count("Activity Log", {"operation": "Login", "status": "Success", "creation": ["between", [start, end]]})
	out["failed_logins"] = count("Activity Log", {"operation": "Login", "status": "Failed", "creation": ["between", [start, end]]})
	pl_field = "changed_at" if has_field("Permission Log", "changed_at") else "creation"
	out["permission_changes"] = count("Permission Log", {pl_field: ["between", [start, end]]})
	out["access_changes"] = count("Version", {"creation": ["between", [start, end]], "ref_doctype": ["in", [d for d in ACCESS_CONTROL_DOCTYPES if doctype_exists(d)]]})
	out["config_changes"] = count("Version", {"creation": ["between", [start, end]], "ref_doctype": ["in", [d for d in ADMIN_DOCTYPES if d not in ACCESS_CONTROL_DOCTYPES and doctype_exists(d)]]})
	out["exports"] = count("Access Log", {"creation": ["between", [start, end]]})
	out["api_requests"] = count("API Request Log", {"creation": ["between", [start, end]]})
	out["top_failed_users"] = []
	out["top_failed_ips"] = []
	if doctype_exists("Activity Log"):
		out["top_failed_users"] = frappe.db.sql("""select user, count(*) n from `tabActivity Log` where operation='Login' and status='Failed'
			and creation between %s and %s group by user order by n desc limit 5""", (start, end), as_dict=True)
		if has_field("Activity Log", "ip_address"):
			out["top_failed_ips"] = frappe.db.sql("""select ip_address ip, count(*) n from `tabActivity Log` where operation='Login' and status='Failed'
				and ifnull(ip_address, '') != '' and creation between %s and %s group by ip_address order by n desc limit 5""", (start, end), as_dict=True)
	out["api_logging_enabled"] = bool(frappe.db.get_single_value("System Settings", "log_api_requests")) if has_field("System Settings", "log_api_requests") else None
	return out
