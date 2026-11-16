"""Command Center dashboard data.

Every figure here is read from the site's own tables. When a source DocType
is not installed (for example ERPNext is absent) the value is ``None`` and the
UI shows "Not available" - nothing is estimated or invented.
"""

import json
from datetime import timedelta

import frappe
from frappe.utils import getdate, now_datetime

from thinknxg_admin.api.cache import cached_panel
from thinknxg_admin.api.utils import (
	SYSTEM_ACCOUNTS,
	delta,
	desk_route,
	doctype_exists,
	has_field,
	period,
	require_admin,
	safe_count,
)

# DocTypes whose changes count as "administrative" in the activity timeline.
ADMIN_DOCTYPES = [
	"User", "Role", "Role Profile", "Custom DocPerm", "User Permission", "Workspace",
	"System Settings", "Custom Field", "Property Setter", "Company", "Module Def",
	"Workflow", "Server Script", "Webhook", "Email Account", "Module Profile",
	"Workspace Sidebar", "Desktop Icon", "Security Settings", "Navbar Settings",
]
PERMISSION_DOCTYPES = ["Custom DocPerm", "User Permission", "Role", "Role Profile", "User"]
HIDDEN_ROLES = ("All", "Guest", "Administrator", "Desk User")


# ---------------------------------------------------------------- KPIs
def _system_user_filters(extra=None):
	f = {"user_type": "System User", "name": ["not in", SYSTEM_ACCOUNTS]}
	if extra:
		f.update(extra)
	return f


def _distinct_logins(start, end):
	if not doctype_exists("Activity Log"):
		return None
	return frappe.db.sql(
		"""select count(distinct `user`) from `tabActivity Log`
		where operation='Login' and status='Success' and creation between %s and %s""",
		(start, end),
	)[0][0]


def _rq_job_counts():
	try:
		from frappe.utils.background_jobs import get_queue_list, get_queues, get_redis_conn  # noqa: F401

		conn = get_redis_conn()
		queued = started = failed = 0
		from rq.registry import FailedJobRegistry, StartedJobRegistry

		for q in get_queues(connection=conn):
			queued += q.count
			started += StartedJobRegistry(queue=q).count
			failed += FailedJobRegistry(queue=q).count
		return {"queued": queued, "running": started, "failed": failed}
	except Exception:
		return None


@frappe.whitelist()
@cached_panel
def get_kpis(days: int = 30, company: str | None = None):
	require_admin()
	prev_start, start, end = period(days)

	total_users = safe_count("User", _system_user_filters({"enabled": 1}))
	new_now = safe_count("User", _system_user_filters({"creation": ["between", [start, end]]}))
	new_prev = safe_count("User", _system_user_filters({"creation": ["between", [prev_start, start]]}))

	active_now = _distinct_logins(start, end)
	active_prev = _distinct_logins(prev_start, start)

	ws_filters = {}
	if doctype_exists("Workspace"):
		if has_field("Workspace", "public"):
			ws_filters["public"] = 1
		if has_field("Workspace", "is_hidden"):
			ws_filters["is_hidden"] = 0

	installed = frappe.get_installed_apps()
	modules = safe_count("Module Def", {"app_name": ["in", installed]})

	pending = safe_count("Workflow Action", {"status": "Open"})
	pending_prev = None
	if pending is not None:
		pending_prev = safe_count("Workflow Action", {"status": "Open", "creation": ["<", start]})

	jobs = _rq_job_counts()

	return {
		"total_users": {"value": total_users, "secondary": new_now, "secondary_label": "new in period", "delta": delta(new_now, new_prev)},
		"active_users": {"value": active_now, "delta": delta(active_now, active_prev), "secondary": active_prev, "secondary_label": "previous period"},
		"companies": {"value": safe_count("Company")},
		"workspaces": {"value": safe_count("Workspace", ws_filters)},
		"installed_apps": {"value": len(installed), "items": installed},
		"modules": {"value": modules, "secondary_label": "across installed apps"},
		"pending_approvals": {"value": pending, "secondary": pending_prev, "secondary_label": "older than period"},
		"background_jobs": {
			"value": None if jobs is None else jobs["queued"] + jobs["running"],
			"secondary": None if jobs is None else jobs["failed"],
			"secondary_label": "failed",
		},
		"login_series": _login_series(start, end),
		"generated_at": now_datetime(),
	}


def _login_series(start, end):
	if not doctype_exists("Activity Log"):
		return None
	rows = frappe.db.sql(
		"""select date(creation) as d, count(*) as c, count(distinct `user`) as u
		from `tabActivity Log` where operation='Login' and status='Success'
		and creation between %s and %s group by date(creation)""",
		(start, end),
		as_dict=True,
	)
	by_day = {str(getdate(r.d)): r for r in rows}
	series, day, last = [], getdate(start), getdate(end)
	while day <= last:
		r = by_day.get(str(day))
		series.append({"date": str(day), "logins": int(r.c) if r else 0, "users": int(r.u) if r else 0})
		day += timedelta(days=1)
	return series


# ---------------------------------------------------------------- Activity
@frappe.whitelist()
@cached_panel
def get_activity(days: int = 30):
	require_admin()
	_, start, end = period(days)
	out = {"logins": [], "failed_logins": None, "logouts": None}
	if doctype_exists("Activity Log"):
		fields = ["name", "user", "full_name", "operation", "status", "creation"]
		if has_field("Activity Log", "ip_address"):
			fields.append("ip_address")
		out["logins"] = frappe.get_all(
			"Activity Log",
			filters={"operation": ["in", ["Login", "Logout"]]},
			fields=fields,
			order_by="creation desc",
			limit=8,
		)
		out["failed_logins"] = safe_count("Activity Log", {"operation": "Login", "status": "Failed", "creation": ["between", [start, end]]})
		out["successful_logins"] = safe_count("Activity Log", {"operation": "Login", "status": "Success", "creation": ["between", [start, end]]})
	out["config_changes"] = safe_count("Version", {"ref_doctype": ["in", ADMIN_DOCTYPES], "creation": ["between", [start, end]]})
	out["errors"] = safe_count("Error Log", {"creation": ["between", [start, end]]})
	out["scheduled_job_failures"] = safe_count("Scheduled Job Log", {"status": "Failed", "creation": ["between", [start, end]]})
	return out


# ---------------------------------------------------------------- Users & access
@frappe.whitelist()
@cached_panel
def get_access_overview(days: int = 30):
	require_admin()
	_, start, end = period(days)
	active = safe_count("User", _system_user_filters({"enabled": 1}))
	disabled = safe_count("User", _system_user_filters({"enabled": 0}))
	website = safe_count("User", {"user_type": "Website User", "enabled": 1})
	never_logged = safe_count("User", _system_user_filters({"enabled": 1, "last_login": ["is", "not set"]}))

	dormant_cutoff = now_datetime() - timedelta(days=90)
	dormant = safe_count("User", _system_user_filters({"enabled": 1, "last_login": ["<", dormant_cutoff]}))

	invitations = None
	if doctype_exists("User Invitation") and has_field("User Invitation", "status"):
		invitations = safe_count("User Invitation", {"status": "Pending"})
	failed_24h = safe_count("Activity Log", {"operation": "Login", "status": "Failed", "creation": [">", now_datetime() - timedelta(hours=24)]})

	roles = frappe.db.sql(
		"""select hr.role as role, count(distinct hr.parent) as users
		from `tabHas Role` hr join `tabUser` u on u.name = hr.parent
		where hr.parenttype='User' and u.enabled=1 and u.user_type='System User'
		and u.name not in %(sys)s and hr.role not in %(hidden)s
		group by hr.role order by users desc limit 8""",
		{"sys": SYSTEM_ACCOUNTS, "hidden": HIDDEN_ROLES},
		as_dict=True,
	)

	changes = _permission_log(start, end, limit=5) or _versions([d for d in PERMISSION_DOCTYPES if doctype_exists(d)], start, end, limit=5, fields_of_interest={"User": {"roles", "role_profiles", "role_profile_name", "enabled", "module_profile", "block_modules", "user_type"}})
	return {
		"active": active,
		"disabled": disabled,
		"website": website,
		"never_logged_in": never_logged,
		"dormant_90d": dormant,
		"pending_invitations": invitations,
		"failed_logins_24h": failed_24h,
		"role_distribution": roles,
		"recent_permission_changes": changes,
		"total_roles": safe_count("Role", {"disabled": 0} if has_field("Role", "disabled") else {}),
	}


# ---------------------------------------------------------------- Organization
@frappe.whitelist()
@cached_panel
def get_organization_overview(company: str | None = None):
	require_admin()

	def scoped(doctype, extra=None):
		f = dict(extra or {})
		if company and doctype_exists(doctype) and has_field(doctype, "company"):
			f["company"] = company
		return safe_count(doctype, f)

	items = [
		("Company", "Companies", safe_count("Company"), "building-2"),
		("Branch", "Branches", safe_count("Branch"), "git-branch"),
		("Department", "Departments", scoped("Department", {"is_group": 0} if has_field("Department", "is_group") else None), "network"),
		("Designation", "Designations", safe_count("Designation"), "id-card"),
		("Cost Center", "Cost Centers", scoped("Cost Center", {"is_group": 0}) if doctype_exists("Cost Center") else None, "target"),
		("Warehouse", "Warehouses", scoped("Warehouse", {"is_group": 0}) if doctype_exists("Warehouse") else None, "warehouse"),
		("Employee", "Employees", scoped("Employee", {"status": "Active"}) if doctype_exists("Employee") else None, "contact"),
		("Fiscal Year", "Fiscal Years", safe_count("Fiscal Year"), "calendar-range"),
	]
	out = [{"doctype": dt, "label": label, "value": v, "icon": icon, "route": desk_route(dt)} for dt, label, v, icon in items]

	# Business units have no native DocType; the source is chosen in thinkNXG Admin Settings.
	source = None
	try:
		source = frappe.db.get_single_value("thinkNXG Admin Settings", "business_unit_source")
	except Exception:
		pass
	configured = source in ("Department Groups", "Cost Center Groups")
	if source == "Department Groups":
		out.append({"doctype": "Department", "label": "Business Units", "value": scoped("Department", {"is_group": 1}), "icon": "layers", "route": desk_route("Department") + "?is_group=1"})
	elif source == "Cost Center Groups":
		out.append({"doctype": "Cost Center", "label": "Business Units", "value": scoped("Cost Center", {"is_group": 1}), "icon": "layers", "route": desk_route("Cost Center") + "?is_group=1"})
	return {"company": company, "items": out, "business_units_configured": configured}


# ---------------------------------------------------------------- Pending actions
@frappe.whitelist()
@cached_panel
def get_pending_actions():
	require_admin()
	user = frappe.session.user
	actions = []

	if doctype_exists("Workflow Action"):
		fields = ["name", "reference_doctype", "reference_name", "workflow_state", "creation"]
		for row in frappe.get_all("Workflow Action", filters={"status": "Open"}, fields=fields, order_by="creation desc", limit=6):
			actions.append({
				"kind": "approval", "title": f"{row.reference_doctype} {row.reference_name}",
				"subtitle": f"Awaiting action · {row.workflow_state or 'Open'}",
				"creation": row.creation, "route": desk_route(row.reference_doctype, row.reference_name),
			})

	if doctype_exists("ToDo"):
		for row in frappe.get_all(
			"ToDo", filters={"allocated_to": user, "status": "Open"},
			fields=["name", "description", "reference_type", "reference_name", "priority", "creation"],
			order_by="creation desc", limit=5,
		):
			title = frappe.utils.strip_html(row.description or "")[:90] or row.name
			actions.append({
				"kind": "task", "title": title,
				"subtitle": f"Assigned to you · {row.priority or 'Medium'} priority",
				"creation": row.creation,
				"route": desk_route(row.reference_type, row.reference_name) if row.reference_type and row.reference_name else desk_route("ToDo", row.name),
			})

	alerts = []
	unseen = safe_count("Error Log", {"seen": 0}) if has_field("Error Log", "seen") else None
	if unseen:
		alerts.append({"kind": "alert", "severity": "critical", "title": f"{unseen} unseen error log{'s' if unseen != 1 else ''}", "subtitle": "Server exceptions recorded on this site", "route": "/desk/error-log?seen=0"})

	try:
		from frappe.utils.scheduler import is_scheduler_disabled, is_scheduler_inactive

		if is_scheduler_disabled():
			alerts.append({"kind": "alert", "severity": "warning", "title": "Scheduler is disabled", "subtitle": "Scheduled jobs and emails will not run", "route": "/desk/system-settings"})
		elif is_scheduler_inactive():
			alerts.append({"kind": "alert", "severity": "warning", "title": "Scheduler is inactive", "subtitle": "No scheduler activity detected recently", "route": "/desk/scheduled-job-type"})
	except Exception:
		pass

	jobs = _rq_job_counts()
	if jobs and jobs["failed"]:
		alerts.append({"kind": "alert", "severity": "serious", "title": f"{jobs['failed']} failed background job{'s' if jobs['failed'] != 1 else ''}", "subtitle": "Inspect and retry from RQ Job", "route": "/desk/rq-job?status=failed"})

	actions.sort(key=lambda a: a.get("creation") or "", reverse=True)
	return {"alerts": alerts, "actions": actions[:8], "approval_count": safe_count("Workflow Action", {"status": "Open"}), "todo_count": safe_count("ToDo", {"allocated_to": user, "status": "Open"})}


# ---------------------------------------------------------------- Admin timeline
def _summarize_version(data: str, interesting=None):
	try:
		d = json.loads(data or "{}")
	except Exception:
		return "Updated", None
	changed = d.get("changed") or []
	if interesting:
		changed = [c for c in changed if c and c[0] in interesting] or changed
	if d.get("added"):
		tables = sorted({row[0] for row in d["added"] if row})
		if "roles" in tables:
			return "Roles added", None
		return f"Rows added to {', '.join(tables)}", None
	if d.get("removed"):
		tables = sorted({row[0] for row in d["removed"] if row})
		if "roles" in tables:
			return "Roles removed", None
		return f"Rows removed from {', '.join(tables)}", None
	if changed:
		field, old, new = (changed[0] + [None, None, None])[:3]
		more = f" +{len(changed) - 1} more" if len(changed) > 1 else ""
		return f"Changed {frappe.unscrub(field)}{more}", {"field": field, "old": _short(old), "new": _short(new)}
	if d.get("row_changed"):
		return "Child rows updated", None
	if d.get("updater_reference"):
		return "Updated", None
	return "Created" if not d else "Updated", None


def _short(v):
	if v is None:
		return None
	s = str(v)
	return s if len(s) <= 60 else s[:57] + "..."


def _versions(doctypes, start, end, limit=20, fields_of_interest=None):
	if not doctypes or not doctype_exists("Version"):
		return []
	rows = frappe.get_all(
		"Version",
		filters={"ref_doctype": ["in", doctypes], "creation": ["between", [start, end]]},
		fields=["name", "ref_doctype", "docname", "owner", "creation", "data"],
		order_by="creation desc",
		limit=limit,
	)
	names = {r.owner for r in rows}
	full_names = dict(frappe.get_all("User", filters={"name": ["in", list(names)]}, fields=["name", "full_name"], as_list=True)) if names else {}
	out = []
	for r in rows:
		summary, change = _summarize_version(r.data, (fields_of_interest or {}).get(r.ref_doctype))
		out.append({
			"id": r.name, "actor": r.owner, "actor_name": full_names.get(r.owner) or r.owner,
			"action": summary, "change": change, "doctype": r.ref_doctype, "docname": r.docname,
			"timestamp": r.creation, "route": desk_route(r.ref_doctype, r.docname), "status": "Success",
		})
	return out


def _permission_log(start, end, limit=10):
	"""V16 Permission Log: who changed which permission, with before/after."""
	if not doctype_exists("Permission Log"):
		return []
	rows = frappe.get_all(
		"Permission Log",
		filters={"changed_at": ["between", [start, end]]} if has_field("Permission Log", "changed_at") else {"creation": ["between", [start, end]]},
		fields=["name", "changed_by", "changed_at", "creation", "for_doctype", "for_document", "reference_type", "reference", "status", "changes"],
		order_by="creation desc",
		limit=limit,
	)
	names = {r.changed_by for r in rows if r.changed_by}
	full = dict(frappe.get_all("User", filters={"name": ["in", list(names)]}, fields=["name", "full_name"], as_list=True)) if names else {}
	out = []
	for r in rows:
		target = r.for_document or r.reference or r.for_doctype
		action = f"{r.status or 'Updated'} permission"
		if r.for_doctype:
			action += f" on {r.for_doctype}"
		out.append({
			"id": r.name, "actor": r.changed_by, "actor_name": full.get(r.changed_by) or r.changed_by,
			"action": action, "change": None, "doctype": r.reference_type or r.for_doctype or "Permission Log",
			"docname": target, "timestamp": r.changed_at or r.creation, "status": "Success",
			"route": desk_route("Permission Log", r.name),
		})
	return out


@frappe.whitelist()
@cached_panel
def get_admin_timeline(days: int = 30, limit: int = 20):
	require_admin()
	_, start, end = period(days)
	limit = max(5, min(int(limit or 20), 100))
	events = _versions([d for d in ADMIN_DOCTYPES if doctype_exists(d)], start, end, limit=limit)
	events += _permission_log(start, end, limit=limit)

	if doctype_exists("Activity Log"):
		for r in frappe.get_all(
			"Activity Log",
			filters={"operation": "Login", "status": "Failed", "creation": ["between", [start, end]]},
			fields=["name", "user", "full_name", "creation"] + (["ip_address"] if has_field("Activity Log", "ip_address") else []),
			order_by="creation desc", limit=10,
		):
			events.append({
				"id": r.name, "actor": r.user, "actor_name": r.full_name or r.user, "action": "Failed login attempt",
				"doctype": "Activity Log", "docname": r.name, "timestamp": r.creation, "status": "Failed",
				"ip": r.get("ip_address"), "route": desk_route("Activity Log", r.name),
			})

	events.sort(key=lambda e: str(e["timestamp"]), reverse=True)
	return events[:limit]
