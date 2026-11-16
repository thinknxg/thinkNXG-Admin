"""HR Command Center data.

Three access levels, all decided by ``centers.center_access("hr")``:

full / limited  HR roles. Every figure goes through the core query builder with
                permissions on, so role permissions and User Permissions on
                Employee, Company, Department... narrow every count. "limited"
                means payroll is withheld.
team            a manager whose Employee record has active direct reports. Rows
                are limited on the server to those direct reports and to a short
                list of non-sensitive DocTypes (TEAM_DOCTYPES); payroll,
                recruitment, performance and lifecycle are never sent.

Payroll totals also need ``can_view_payroll()`` (Payroll Entry read, HR Manager
by default, or a configured payroll role) AND read access to Salary Slip. Only
totals are sent, never an individual's pay.
"""

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, flt, getdate, today

from thinknxg_admin.api.cache import cached_panel
from thinknxg_admin.api.centers import can_view_payroll, permitted_companies, require_center, team_employees, validate_company
from thinknxg_admin.api.figures import Missing, Restricted, _between, _figure, _part, _q, _quiet
from thinknxg_admin.api.utils import delta, desk_route, doctype_exists, has_field, slug

SECTIONS = ("employee", "attendance", "leave", "payroll", "recruitment", "performance", "lifecycle", "team")
TEAM_SECTIONS = ("team", "attendance", "leave")
TEAM_DOCTYPES = {"Employee", "Attendance", "Leave Application", "Employee Checkin", "Expense Claim", "Shift Request"}
PRESENT = ["Present", "Work From Home"]

# Requests HR approves without a workflow: the named approver sets the outcome
# and submits, exactly as in the Desk. thinkNXG HR's own validation still runs.
APPROVALS = {
	"Leave Application": {"approver": "leave_approver", "field": "status", "open": "Open", "approve": "Approved", "reject": "Rejected"},
	"Expense Claim": {"approver": "expense_approver", "field": "approval_status", "open": "Draft", "approve": "Approved", "reject": "Rejected"},
	"Shift Request": {"approver": "approver", "field": "status", "open": "Draft", "approve": "Approved", "reject": "Rejected"},
}


# Context ------------------------------------------------------------------------

def _context(company=None, department=None, branch=None, days=None) -> frappe._dict:
	level = require_center("hr")
	team = level == "team"
	company = validate_company(company) if company and not team else company
	if not company and not team:
		allowed = permitted_companies()
		preferred = frappe.defaults.get_user_default("Company")
		company = preferred if preferred in allowed else (allowed[0] if allowed else None)

	for doctype, value in (("Department", department), ("Branch", branch)):
		if value and not team and not frappe.get_list(doctype, filters={"name": value}, limit=1):
			frappe.throw(_("You do not have access to {0} {1}.").format(_(doctype), value), frappe.PermissionError)

	try:
		n = max(1, min(int(days or 30), 366))
	except (TypeError, ValueError):
		n = 30
	end = getdate(today())
	start = add_days(end, -(n - 1))

	employees = None
	if team:
		employees = team_employees()
		narrow = {k: v for k, v in (("company", company), ("department", department), ("branch", branch)) if v}
		if narrow and employees:
			employees = frappe.get_all("Employee", filters={"name": ["in", employees], **narrow}, pluck="name")
	elif branch:
		# Branch lives on Employee only; other records are matched through it.
		employees = frappe.get_list("Employee", filters={k: v for k, v in (("company", company), ("branch", branch)) if v}, pluck="name", limit_page_length=0)

	return frappe._dict(
		level=level, team=team, company=company, department=department, branch=branch,
		start=start, end=end, prev_start=add_days(start, -n), prev_end=add_days(start, -1),
		today=end, employees=employees, payroll=(not team and can_view_payroll()),
	)


def _need(ctx, *doctypes):
	for dt in doctypes:
		if not doctype_exists(dt):
			raise Missing
		if ctx.team:
			if dt not in TEAM_DOCTYPES:
				raise Restricted
		elif not frappe.has_permission(dt, "read"):
			raise Restricted
	return True


def _f(ctx, doctype, extra=None) -> dict:
	"""Scope filters: company, department, branch or the manager's direct reports."""
	key = "name" if doctype == "Employee" else "employee"
	f = {}
	if ctx.employees is not None:
		f[key] = ["in", ctx.employees or [""]]
	if not ctx.team:
		if ctx.company and has_field(doctype, "company"):
			f["company"] = ctx.company
		if ctx.department:
			if has_field(doctype, "department"):
				f["department"] = ctx.department
			elif doctype != "Employee" and has_field(doctype, "employee"):
				depts = frappe.get_list("Employee", filters={"department": ctx.department}, pluck="name", limit_page_length=0)
				scoped = list(set(depts) & set(ctx.employees)) if ctx.employees is not None else depts
				f[key] = ["in", scoped or [""]]
	f.update(extra or {})
	return f


def Q(ctx, doctype, fields, filters, group_by=None, limit=None, order_by=None):
	# Team rows are already limited to direct reports by _f, so the framework's
	# own Employee-record permissions (which would hide them) are not applied.
	return _q(doctype, fields, filters, group_by=group_by, limit=limit, order_by=order_by, ignore_permissions=ctx.team)


def C(ctx, doctype, filters) -> int:
	rows = Q(ctx, doctype, [{"COUNT": "*", "as": "n"}], filters)
	return int(rows[0].n or 0) if rows else 0


def L(ctx, doctype, filters, fields, order_by=None, limit=8):
	if ctx.team:
		return frappe.get_all(doctype, filters=filters, fields=fields, order_by=order_by, limit=limit)
	return frappe.get_list(doctype, filters=filters, fields=fields, order_by=order_by, limit_page_length=limit)


def _route(doctype, **params):
	from urllib.parse import urlencode

	q = urlencode({k: v for k, v in params.items() if v is not None})
	return f"/desk/{slug(doctype)}" + (f"?{q}" if q else "")


HIDDEN = {"hidden": True}


# KPIs ---------------------------------------------------------------------------

def kpi_total(ctx):
	if ctx.team:
		return HIDDEN
	_need(ctx, "Employee")
	return {"value": C(ctx, "Employee", _f(ctx, "Employee")), "route": _route("Employee", company=ctx.company)}


def kpi_active(ctx):
	_need(ctx, "Employee")
	n = C(ctx, "Employee", _f(ctx, "Employee", {"status": "Active"}))
	return {"value": n, "route": None if ctx.team else _route("Employee", company=ctx.company, status="Active")}


def kpi_joiners(ctx):
	if ctx.team:
		return HIDDEN
	_need(ctx, "Employee")
	cur = C(ctx, "Employee", _f(ctx, "Employee", {"date_of_joining": _between(ctx.start, ctx.end)}))
	prev = C(ctx, "Employee", _f(ctx, "Employee", {"date_of_joining": _between(ctx.prev_start, ctx.prev_end)}))
	return {"value": cur, "delta": delta(cur, prev), "route": _route("Employee", company=ctx.company)}


def _on_leave_filters(ctx, day):
	return _f(ctx, "Leave Application", {"status": "Approved", "docstatus": 1, "from_date": ["<=", day], "to_date": [">=", day]})


def kpi_on_leave(ctx):
	_need(ctx, "Leave Application")
	return {"value": C(ctx, "Leave Application", _on_leave_filters(ctx, ctx.today)), "route": None if ctx.team else _route("Leave Application", status="Approved")}


def _attendance(ctx, statuses, start, end):
	return C(ctx, "Attendance", _f(ctx, "Attendance", {"docstatus": 1, "status": ["in", statuses], "attendance_date": _between(start, end)}))


def kpi_present(ctx):
	_need(ctx, "Attendance")
	return {"value": _attendance(ctx, PRESENT, ctx.today, ctx.today), "route": None if ctx.team else _route("Attendance", attendance_date=str(ctx.today))}


def kpi_absent(ctx):
	_need(ctx, "Attendance")
	return {"value": _attendance(ctx, ["Absent"], ctx.today, ctx.today), "route": None if ctx.team else _route("Attendance", attendance_date=str(ctx.today), status="Absent")}


def kpi_rate(ctx):
	_need(ctx, "Attendance")

	def rate(a, b):
		p, ab = _attendance(ctx, PRESENT, a, b), _attendance(ctx, ["Absent"], a, b)
		return round(p * 100.0 / (p + ab), 1) if (p + ab) else None

	cur, prev = rate(ctx.start, ctx.end), rate(ctx.prev_start, ctx.prev_end)
	return {"value": cur, "delta": round(cur - prev, 1) if cur is not None and prev is not None else None, "unit": "%"}


def kpi_pending_leave(ctx):
	_need(ctx, "Leave Application")
	return {"value": C(ctx, "Leave Application", _f(ctx, "Leave Application", {"status": "Open", "docstatus": 0})), "route": None if ctx.team else _route("Leave Application", status="Open")}


def kpi_positions(ctx):
	if ctx.team:
		return HIDDEN
	_need(ctx, "Job Opening")
	rows = Q(ctx, "Job Opening", [{"COUNT": "*", "as": "n"}, {"SUM": "planned_vacancies", "as": "v"}], _f(ctx, "Job Opening", {"status": "Open"}))
	r = rows[0] if rows else frappe._dict()
	return {"value": int(r.v or 0) or int(r.n or 0), "secondary": int(r.n or 0), "route": _route("Job Opening", status="Open")}


def kpi_approvals(ctx):
	return {"value": len(approval_rows(ctx, with_actions=False)), "route": "/thinknxg/hr/approvals"}


KPIS = {
	"total_employees": kpi_total,
	"active_employees": kpi_active,
	"new_joiners": kpi_joiners,
	"on_leave_today": kpi_on_leave,
	"present_today": kpi_present,
	"absent_today": kpi_absent,
	"attendance_rate": kpi_rate,
	"pending_leave": kpi_pending_leave,
	"open_positions": kpi_positions,
	"pending_approvals": kpi_approvals,
}


@frappe.whitelist()
@cached_panel
def get_kpis(company=None, department=None, branch=None, days=None):
	ctx = _context(company, department, branch, days)
	out = {key: _figure(fn, ctx) for key, fn in KPIS.items()}
	out["_context"] = {"level": ctx.level, "company": ctx.company, "start": str(ctx.start), "end": str(ctx.end), "team_size": len(ctx.employees) if ctx.team else None}
	return out


# Sections -----------------------------------------------------------------------

def _bars(rows, key, value="n", n=8, as_int=True):
	rows = [r for r in rows if r.get(key) is not None]
	rows.sort(key=lambda r: flt(r.get(value)), reverse=True)
	return [{"label": r[key] or _("Not set"), "value": int(r[value]) if as_int else flt(r[value])} for r in rows[:n]]


def section_employee(ctx):
	_need(ctx, "Employee")
	active = _f(ctx, "Employee", {"status": "Active"})
	return {
		"by_department": _bars(Q(ctx, "Employee", ["department", {"COUNT": "*", "as": "n"}], active, group_by="department"), "department"),
		"by_designation": _bars(Q(ctx, "Employee", ["designation", {"COUNT": "*", "as": "n"}], active, group_by="designation"), "designation"),
		"joiners": C(ctx, "Employee", _f(ctx, "Employee", {"date_of_joining": _between(ctx.start, ctx.end)})),
		"leavers": C(ctx, "Employee", _f(ctx, "Employee", {"relieving_date": _between(ctx.start, ctx.end)})),
	}


def section_attendance(ctx):
	_need(ctx, "Attendance")
	rows = Q(ctx, "Attendance", ["attendance_date", "status", {"COUNT": "*", "as": "n"}],
		_f(ctx, "Attendance", {"docstatus": 1, "attendance_date": _between(ctx.start, ctx.end)}), group_by="attendance_date, status")
	per = {}
	for r in rows:
		d = per.setdefault(str(r.attendance_date), {"present": 0, "absent": 0})
		if r.status in PRESENT:
			d["present"] += int(r.n)
		elif r.status == "Absent":
			d["absent"] += int(r.n)
	trend = [{"date": str(add_days(ctx.start, i)), **per.get(str(add_days(ctx.start, i)), {"present": 0, "absent": 0})} for i in range(date_diff(ctx.end, ctx.start) + 1)]
	base = _f(ctx, "Attendance", {"docstatus": 1, "attendance_date": _between(ctx.start, ctx.end)})

	def checkins():
		_need(ctx, "Employee Checkin")
		return C(ctx, "Employee Checkin", _f(ctx, "Employee Checkin", {"time": _between(f"{ctx.today} 00:00:00", f"{ctx.today} 23:59:59")}))

	return {
		"trend": trend,
		"late_entries": C(ctx, "Attendance", {**base, "late_entry": 1}),
		"early_exits": C(ctx, "Attendance", {**base, "early_exit": 1}),
		"half_days": C(ctx, "Attendance", {**base, "status": "Half Day"}),
		"checkins_today": _part(checkins),
	}


def section_leave(ctx):
	_need(ctx, "Leave Application")
	by_type = Q(ctx, "Leave Application", ["leave_type", {"SUM": "total_leave_days", "as": "n"}],
		_f(ctx, "Leave Application", {"status": "Approved", "docstatus": 1, "from_date": _between(ctx.start, ctx.end)}), group_by="leave_type")
	upcoming = L(ctx, "Leave Application",
		_f(ctx, "Leave Application", {"status": "Approved", "docstatus": 1, "to_date": [">=", ctx.today], "from_date": ["<=", add_days(ctx.today, 14)]}),
		["name", "employee_name", "leave_type", "from_date", "to_date", "total_leave_days"], order_by="from_date asc", limit=10)
	return {
		"by_type": _bars(by_type, "leave_type", as_int=False),
		"upcoming": [{**u, "route": desk_route("Leave Application", u.name) if not ctx.team else None} for u in upcoming],
		"open_requests": C(ctx, "Leave Application", _f(ctx, "Leave Application", {"status": "Open", "docstatus": 0})),
	}


def section_payroll(ctx):
	if not ctx.payroll:
		raise Restricted
	_need(ctx, "Payroll Entry", "Salary Slip")
	runs = frappe.get_list("Payroll Entry", filters={"docstatus": 1, **({"company": ctx.company} if ctx.company else {})},
		fields=["name", "posting_date", "start_date", "end_date"], order_by="posting_date desc", limit_page_length=1)
	latest = None
	if runs:
		r = runs[0]
		t = Q(ctx, "Salary Slip", [{"COUNT": "*", "as": "n"}, {"SUM": "base_gross_pay", "as": "gross"}, {"SUM": "base_net_pay", "as": "net"}],
			_f(ctx, "Salary Slip", {"docstatus": 1, "payroll_entry": r.name}))
		t = t[0] if t else frappe._dict()
		latest = {"name": r.name, "posting_date": str(r.posting_date), "start_date": str(r.start_date), "end_date": str(r.end_date),
			"slips": int(t.n or 0), "gross": flt(t.gross), "net": flt(t.net), "route": desk_route("Payroll Entry", r.name)}
	history = Q(ctx, "Salary Slip", ["start_date", {"SUM": "base_gross_pay", "as": "gross"}, {"SUM": "base_net_pay", "as": "net"}],
		_f(ctx, "Salary Slip", {"docstatus": 1, "start_date": [">=", add_days(ctx.today, -400)]}), group_by="start_date")
	history = sorted(history, key=lambda h: h.start_date)[-6:]
	status = Q(ctx, "Salary Slip", ["status", {"COUNT": "*", "as": "n"}], _f(ctx, "Salary Slip", {"start_date": _between(ctx.start, ctx.end)}), group_by="status")
	return {
		"currency": frappe.get_cached_value("Company", ctx.company, "default_currency") if ctx.company else None,
		"latest": latest,
		"history": [{"label": str(h.start_date), "gross": flt(h.gross), "net": flt(h.net)} for h in history],
		"slips_by_status": _bars(status, "status"),
	}


def section_recruitment(ctx):
	_need(ctx, "Job Opening")
	openings = L(ctx, "Job Opening", _f(ctx, "Job Opening", {"status": "Open"}), ["name", "job_title", "designation", "planned_vacancies", "closes_on"], order_by="closes_on asc", limit=8)

	def applicants():
		_need(ctx, "Job Applicant")
		return _bars(Q(ctx, "Job Applicant", ["status", {"COUNT": "*", "as": "n"}], {"creation": [">=", f"{ctx.start} 00:00:00"]}, group_by="status"), "status")

	def interviews():
		_need(ctx, "Interview")
		return C(ctx, "Interview", {"status": "Pending", "scheduled_on": [">=", ctx.today]})

	def offers():
		_need(ctx, "Job Offer")
		return _bars(Q(ctx, "Job Offer", ["status", {"COUNT": "*", "as": "n"}], _f(ctx, "Job Offer", {"status": ["in", ["Awaiting Response", "Accepted"]]}), group_by="status"), "status")

	return {
		"openings": [{**o, "route": desk_route("Job Opening", o.name)} for o in openings],
		"applicants_by_status": _part(applicants),
		"upcoming_interviews": _part(interviews),
		"offers": _part(offers),
	}


def section_performance(ctx):
	_need(ctx, "Appraisal Cycle")
	cycles = L(ctx, "Appraisal Cycle", _f(ctx, "Appraisal Cycle", {"status": ["!=", "Completed"]}), ["name", "cycle_name", "status", "start_date", "end_date"], order_by="start_date desc", limit=6)

	def appraisals():
		_need(ctx, "Appraisal")
		rows = Q(ctx, "Appraisal", ["appraisal_cycle", {"COUNT": "*", "as": "n"}], _f(ctx, "Appraisal", {"appraisal_cycle": ["in", [c.name for c in cycles] or [""]]}), group_by="appraisal_cycle")
		return {r.appraisal_cycle: int(r.n) for r in rows}

	def goals():
		_need(ctx, "Goal")
		return _bars(Q(ctx, "Goal", ["status", {"COUNT": "*", "as": "n"}], _f(ctx, "Goal", {"status": ["in", ["Pending", "In Progress", "Completed"]]}), group_by="status"), "status")

	counts = _part(appraisals)
	return {
		"cycles": [{**c, "appraisals": counts.get(c.name, 0) if isinstance(counts, dict) and not counts.get("restricted") else None, "route": desk_route("Appraisal Cycle", c.name)} for c in cycles],
		"goals_by_status": _part(goals),
	}


def section_lifecycle(ctx):
	def boarding(dt):
		_need(ctx, dt)
		return _bars(Q(ctx, dt, ["boarding_status", {"COUNT": "*", "as": "n"}], _f(ctx, dt, {"boarding_status": ["in", ["Pending", "In Process"]]}), group_by="boarding_status"), "boarding_status")

	def moves(dt, field):
		_need(ctx, dt)
		return C(ctx, dt, _f(ctx, dt, {"docstatus": 1, field: _between(ctx.start, ctx.end)}))

	def grievances():
		_need(ctx, "Employee Grievance")
		return C(ctx, "Employee Grievance", {"status": ["in", ["Open", "Investigated"]]})

	return {
		"onboarding": _part(lambda: boarding("Employee Onboarding")),
		"separation": _part(lambda: boarding("Employee Separation")),
		"promotions": _part(lambda: moves("Employee Promotion", "promotion_date")),
		"transfers": _part(lambda: moves("Employee Transfer", "transfer_date")),
		"open_grievances": _part(grievances),
	}


def section_team(ctx):
	if not ctx.team:
		raise Restricted
	_need(ctx, "Employee")
	members = frappe.get_all("Employee", filters={"name": ["in", ctx.employees or [""]]}, fields=["name", "employee_name", "designation", "department", "image"], order_by="employee_name asc")
	status = {}
	if doctype_exists("Attendance"):
		for r in frappe.get_all("Attendance", filters={"employee": ["in", ctx.employees or [""]], "docstatus": 1, "attendance_date": ctx.today}, fields=["employee", "status"]):
			status[r.employee] = r.status
	leave = set()
	if doctype_exists("Leave Application"):
		leave = set(frappe.get_all("Leave Application", filters=_on_leave_filters(ctx, ctx.today), pluck="employee"))
	return {
		"members": [{**m, "today": "On Leave" if m.name in leave else status.get(m.name) or "Not marked"} for m in members],
	}


SECTION_FNS = {
	"employee": section_employee, "attendance": section_attendance, "leave": section_leave, "payroll": section_payroll,
	"recruitment": section_recruitment, "performance": section_performance, "lifecycle": section_lifecycle, "team": section_team,
}


@frappe.whitelist()
@cached_panel
def get_section(section, company=None, department=None, branch=None, days=None):
	if section not in SECTION_FNS:
		frappe.throw(_("Unknown section."))
	ctx = _context(company, department, branch, days)
	if ctx.team and section not in TEAM_SECTIONS:
		return {"restricted": True}
	try:
		return SECTION_FNS[section](ctx)
	except Missing:
		return {"available": False}
	except (Restricted, frappe.PermissionError) as exc:
		_quiet(exc)
		return {"restricted": True}


# Pending -------------------------------------------------------------------------

@frappe.whitelist()
@cached_panel
def get_pending(company=None):
	ctx = _context(company)
	items = []

	def add(key, label, icon, fn):
		res = _figure(fn, ctx)
		if isinstance(res, dict) and not res.get("restricted") and res.get("value"):
			items.append({"key": key, "label": label, "icon": icon, **res})

	add("approvals", "Requests waiting for your approval", "stamp", lambda c: {"value": len(approval_rows(c, with_actions=False)), "route": "/thinknxg/hr/approvals"})
	if not ctx.team:
		for dt, label, icon in (
			("Attendance Request", "Attendance requests to review", "calendar-check"),
			("Compensatory Leave Request", "Compensatory leave requests to review", "calendar-plus"),
		):
			add(slug(dt), label, icon, lambda c, dt=dt: _need(c, dt) and frappe.has_permission(dt, "submit") and {
				"value": C(c, dt, _f(c, dt, {"docstatus": 0})), "route": _route(dt, docstatus=0)})
		add("onboarding", "Onboarding in progress", "log-in", lambda c: _need(c, "Employee Onboarding") and {
			"value": C(c, "Employee Onboarding", _f(c, "Employee Onboarding", {"boarding_status": ["in", ["Pending", "In Process"]]})), "route": _route("Employee Onboarding")})
		add("grievances", "Open grievances", "messages-square", lambda c: _need(c, "Employee Grievance") and {
			"value": C(c, "Employee Grievance", {"status": ["in", ["Open", "Investigated"]]}), "route": _route("Employee Grievance", status="Open")})
	return {"items": items}


# Approvals -----------------------------------------------------------------------

def _workflow(doctype):
	from frappe.model.workflow import get_workflow_name

	return get_workflow_name(doctype)


def approval_rows(ctx, with_actions=True, limit=100):
	"""Requests where the user is the named approver, plus HR workflow actions."""
	from thinknxg_admin.api.erp import _approval_rows, app_doctypes

	user = frappe.session.user
	out = []
	for dt, cfg in APPROVALS.items():
		if not doctype_exists(dt) or _workflow(dt):
			continue
		fields = ["name", "employee", "employee_name", "creation", "company"]
		fields += {"Leave Application": ["leave_type", "from_date", "to_date", "total_leave_days"],
			"Expense Claim": ["grand_total", "currency", "posting_date"],
			"Shift Request": ["shift_type", "from_date", "to_date"]}[dt]
		rows = frappe.get_all(dt, filters={cfg["approver"]: user, cfg["field"]: cfg["open"], "docstatus": 0}, fields=fields, order_by="creation asc", limit=limit)
		for r in rows:
			if not frappe.has_permission(dt, "read", doc=r.name):
				continue
			if ctx.company and r.company and r.company != ctx.company:
				continue
			out.append({
				"doctype": dt, "name": r.name, "title": r.employee_name or r.employee, "employee": r.employee,
				"creation": r.creation, "company": r.company, "route": desk_route(dt, r.name),
				"detail": _detail(dt, r), "amount": r.get("grand_total"), "currency": r.get("currency"),
				"actions": ["Approve", "Reject"] if with_actions else [], "kind": "approver",
			})
	hr_types = app_doctypes("hrms")
	for row in _approval_rows(ctx.company, limit=limit, with_actions=with_actions, doctypes=hr_types, check_company=False):
		row["kind"] = "workflow"
		row["detail"] = row.get("state")
		out.append(row)
	out.sort(key=lambda r: str(r.get("creation")))
	return out[:limit]


def _detail(dt, r):
	if dt == "Leave Application":
		days = flt(r.total_leave_days)
		return f"{r.leave_type} · {r.from_date} to {r.to_date} · {days:g} day{'s' if days != 1 else ''}"
	if dt == "Shift Request":
		return f"{r.shift_type} · from {r.from_date}" + (f" to {r.to_date}" if r.to_date else "")
	return f"Expense claim · {r.posting_date}"


@frappe.whitelist()
def get_approvals(company=None):
	ctx = _context(company)
	return {"items": approval_rows(ctx)}


@frappe.whitelist(methods=["POST"])
def apply_approval(doctype, name, action):
	"""Approve or reject one HR request.

	With an active workflow: the core workflow engine decides (as for ERP).
	Without one: only the named approver may act; the outcome is set and the
	document submitted with the user's own submit permission, so thinkNXG HR's
	validation (balances, overlaps, accounting for expenses) runs as in the Desk.
	"""
	require_center("hr")
	from thinknxg_admin.api.cache import clear_dashboard_cache
	from thinknxg_admin.api.erp import app_doctypes

	if doctype not in app_doctypes("hrms") and doctype not in APPROVALS:
		frappe.throw(_("This document is not part of thinkNXG HR."), frappe.PermissionError)
	if not frappe.has_permission(doctype, "read", doc=name):
		frappe.throw(_("You do not have access to this document."), frappe.PermissionError)

	if _workflow(doctype):
		from frappe.model.workflow import apply_workflow, get_workflow_state_field

		doc = apply_workflow({"doctype": doctype, "name": name}, action)
		clear_dashboard_cache()
		return {"name": doc.name, "doctype": doctype, "docstatus": int(doc.docstatus), "state": doc.get(get_workflow_state_field(_workflow(doctype)))}

	cfg = APPROVALS.get(doctype)
	if not cfg:
		frappe.throw(_("{0} has no approval step here.").format(_(doctype)))
	if action not in ("Approve", "Reject"):
		frappe.throw(_("Unknown action."))
	doc = frappe.get_doc(doctype, name)
	if doc.get(cfg["approver"]) != frappe.session.user:
		frappe.throw(_("Only the approver named on this request can approve or reject it."), frappe.PermissionError)
	if doc.docstatus != 0 or doc.get(cfg["field"]) != cfg["open"]:
		frappe.throw(_("This request has already been decided."))
	doc.set(cfg["field"], cfg["approve"] if action == "Approve" else cfg["reject"])
	doc.submit()  # checks the user's submit permission and runs thinkNXG HR's validation
	clear_dashboard_cache()
	return {"name": doc.name, "doctype": doctype, "docstatus": int(doc.docstatus), "state": doc.get(cfg["field"])}
