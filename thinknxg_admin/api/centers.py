"""Command center registry.

One shell, many command centers. Each center is declared here once: label,
description, route, which filters its header shows, its navigation and its
quick actions. The browser only ever receives the centers this module grants,
so the switcher, search and default landing can never offer a center the
server would refuse.

Access is decided here, never in the browser:

admin  administrator roles (``require_admin``)
erp    thinkNXG ERP installed and read access to at least one core ledger or
       order DocType. ``erpnext.check_app_permission`` is not used because it
       lets every desk user in.
hr     thinkNXG HR installed and an HR role (HR User, HR Manager or roles set
       in thinkNXG Admin Settings) -> "full"/"limited"; otherwise a user whose
       Employee record has active direct reports -> "team" (direct reports only).
       ``hrms.hr.utils.check_app_permission`` is not used because any employee
       who can read their own Employee record passes it.
"""

import json

import frappe
from frappe import _

from thinknxg_admin.api.navigation import NAVIGATION, filter_sections
from thinknxg_admin.api.routes import internal_route
from thinknxg_admin.api.utils import doctype_exists, is_admin, require_login

DOCS = "https://docs.thinknxg.com"
CENTER_KEYS = ("admin", "erp", "hr")
SETTINGS = "thinkNXG Admin Settings"
PREFERENCE = "thinkNXG User Preference"

# Shared entries every center carries in its Overview section.
NOTIFICATIONS = {"key": "notifications", "label": "Notifications", "icon": "bell", "route": "/notifications", "status": "live"}
MY_WORKSPACE = {"key": "my-workspace", "label": "My Workspace", "icon": "user-round", "route": "/my-workspace", "status": "live"}
REPORTS = {"key": "reports", "label": "Reports", "icon": "chart-column", "route": "/reports", "doctype": "Report", "status": "live"}


ERP_GATE_DOCTYPES = ("GL Entry", "Sales Order", "Purchase Order", "Stock Ledger Entry")
# Every ERP KPI reads one of these; missing any one makes access "limited".
ERP_KPI_DOCTYPES = ("GL Entry", "Sales Order", "Purchase Order", "Payment Ledger Entry", "Bin", "Sales Invoice")

ERP_QUICK = [
	("Sales Invoice", "receipt"), ("Sales Order", "shopping-cart"), ("Purchase Order", "shopping-bag"),
	("Purchase Invoice", "file-text"), ("Payment Entry", "banknote"), ("Journal Entry", "book-open"),
	("Stock Entry", "package"), ("Material Request", "clipboard-list"), ("Customer", "user-round"),
	("Supplier", "truck"), ("Lead", "user-plus"), ("Opportunity", "target"), ("Project", "folder-kanban"),
]

HR_BASE_ROLES = ("HR User", "HR Manager")

HR_QUICK = [
	("Employee", "user-plus", True), ("Attendance", "calendar-check", False), ("Leave Application", "plane", False),
	("Leave Allocation", "calendar-plus", True), ("Shift Assignment", "clock", True), ("Job Opening", "briefcase", True),
	("Job Applicant", "user-search", True), ("Interview", "messages-square", True), ("Employee Onboarding", "log-in", True),
	("Employee Separation", "log-out", True), ("Expense Claim", "receipt", False), ("Training Event", "graduation-cap", True),
]

ADMIN_QUICK = [("User", "user"), ("Role", "role"), ("Company", "building-2"), ("Workspace", "panels-top-left"), ("Workflow", "workflow"), ("Webhook", "plug")]

PERSONAL_NAVIGATION = [
	{"section": "Overview", "items": [MY_WORKSPACE, NOTIFICATIONS]},
	{"section": "Insights", "items": [REPORTS]},
]

CENTERS = {
	"admin": {
		"label": "Admin Command Center", "short": "Admin", "icon": "shield-check",
		"description": "Users, access, platform and governance", "route": "/admin",
		"title": "Welcome to thinkNXG Command Center",
		"subtitle": "Your premium administration command center.",
		"docs_url": f"{DOCS}/thinknxgframework", "filters": ["company"],
	},
	"erp": {
		"label": "ERP Command Center", "short": "ERP", "icon": "briefcase",
		"description": "Finance, sales, purchasing, stock and operations", "route": "/erp", "app": "erpnext",
		"title": "Welcome to thinkNXG ERP Command Center",
		"subtitle": "Your intelligent business operations command center.",
		"docs_url": f"{DOCS}/thinknxgerp", "filters": ["company", "branch", "fiscal_year", "date_range"],
	},
	"hr": {
		"label": "HR Command Center", "short": "HR", "icon": "users-round",
		"description": "Workforce, attendance, leave and people operations", "route": "/hr", "app": "hrms",
		"title": "Welcome to thinkNXG HR Command Center",
		"subtitle": "Your intelligent workforce management and people operations command center.",
		"docs_url": f"{DOCS}/thinknxghr", "filters": ["company", "department", "branch", "date_range"],
	},
}


# Settings ----------------------------------------------------------------------

def _settings_roles(fieldname: str) -> set[str]:
	if not doctype_exists("thinkNXG Admin Role"):
		return set()
	try:
		return set(frappe.get_all("thinkNXG Admin Role", filters={"parent": SETTINGS, "parenttype": SETTINGS, "parentfield": fieldname}, pluck="role"))
	except Exception:
		return set()


def _landing_rules() -> list[dict]:
	if not doctype_exists("thinkNXG Center Landing"):
		return []
	try:
		return frappe.get_all(
			"thinkNXG Center Landing",
			filters={"parent": SETTINGS, "parenttype": SETTINGS, "parentfield": "landing_rules"},
			fields=["role", "center", "priority"],
			order_by="priority asc, idx asc",
		)
	except Exception:
		return []


# Access ------------------------------------------------------------------------

def _readable(doctype: str) -> bool:
	return doctype_exists(doctype) and frappe.has_permission(doctype, "read")


def _app_installed(app: str | None) -> bool:
	return not app or app in frappe.get_installed_apps()


def hr_roles() -> set[str]:
	return set(HR_BASE_ROLES) | _settings_roles("hr_roles")


def can_view_payroll(user: str | None = None) -> bool:
	"""Payroll totals need more than an HR role: HR User can read every slip."""
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	if set(frappe.get_roles(user)) & _settings_roles("payroll_roles"):
		return True
	return _readable("Payroll Entry")


def team_employees(user: str | None = None) -> list[str]:
	"""Active direct reports of the user's own Employee record(s)."""
	user = user or frappe.session.user
	if not doctype_exists("Employee") or user in ("Guest",):
		return []
	mine = frappe.get_all("Employee", filters={"user_id": user, "status": "Active"}, pluck="name")
	if not mine:
		return []
	return frappe.get_all("Employee", filters={"reports_to": ["in", mine], "status": "Active"}, pluck="name")


def center_access(key: str, user: str | None = None) -> str | None:
	"""Return the access level for a center ("full", "limited", "team") or None."""
	user = user or frappe.session.user
	if user == "Guest" or key not in CENTERS:
		return None
	if not _app_installed(CENTERS[key].get("app")):
		return None
	if key == "admin":
		return "full" if is_admin(user) else None
	if key == "erp":
		if user == "Administrator":
			return "full"
		if not any(_readable(dt) for dt in ERP_GATE_DOCTYPES):
			return None
		return "full" if all(_readable(dt) for dt in ERP_KPI_DOCTYPES) else "limited"
	if key == "hr":
		if user == "Administrator" or set(frappe.get_roles(user)) & hr_roles():
			return "full" if can_view_payroll(user) else "limited"
		return "team" if team_employees(user) else None
	return None


def require_center(key: str) -> str:
	"""Server gate for every center endpoint. Returns the access level."""
	require_login()
	level = center_access(key)
	if not level:
		frappe.throw(_("You do not have access to this command center."), frappe.PermissionError)
	return level


def permitted_companies() -> list[str]:
	if not doctype_exists("Company"):
		return []
	try:
		return frappe.get_list("Company", pluck="name", order_by="name asc", limit_page_length=500)
	except frappe.PermissionError:
		return []


def validate_company(company: str | None) -> str | None:
	"""Refuse a company the user's User Permissions do not allow."""
	if not company:
		return None
	if company not in permitted_companies():
		frappe.throw(_("You do not have access to company {0}.").format(company), frappe.PermissionError)
	return company


# Registry output -----------------------------------------------------------------

def _center_nav(key: str, level: str, registry: dict) -> list[dict]:
	"""Overview, one entry per permitted module (from the route registry), insights."""
	home = {"key": f"{key}-home", "label": CENTERS[key]["label"], "icon": "layout-dashboard", "route": f"/{key}", "status": "live"}
	overview = [home, {"key": f"{key}-approvals", "label": "Approvals", "icon": "stamp", "route": f"/{key}/approvals", "status": "live"}, MY_WORKSPACE, NOTIFICATIONS]
	modules = []
	for m in registry.get("modules", {}).get(key, []):
		first = m["groups"][0]["items"]
		modules.append({
			"key": f"{key}-{m['key']}", "label": m["label"], "icon": m["icon"], "route": f"/{key}/{m['key']}", "status": "live",
			"children": [{"key": f"{key}-{m['key']}-{d['slug']}", "label": d["doctype"], "route": f"/{key}/{m['key']}/{d['slug']}", "status": "live"} for d in first[:6]],
		})
	sections = [{"section": "Overview", "items": overview}]
	if modules:
		sections.append({"section": "Modules", "items": modules})
	if level != "team":
		sections.append({"section": "Insights", "items": [dict(REPORTS, key=f"{key}-reports")]})
	return filter_sections(sections)


def _nav_for(key: str, level: str, registry: dict) -> list[dict]:
	if key == "admin":
		return filter_sections(NAVIGATION)
	return _center_nav(key, level, registry)


def _quick_for(key: str, level: str) -> list[dict]:
	if key == "admin":
		rows = [(dt, icon) for dt, icon in ADMIN_QUICK]
	elif key == "erp":
		rows = ERP_QUICK
	else:
		rows = [(dt, icon) for dt, icon, hr_only in HR_QUICK if not (hr_only and level == "team")]
	return [
		{"doctype": dt, "icon": icon, "route": internal_route(dt, new=True), "center": key}
		for dt, icon in rows
		if doctype_exists(dt) and frappe.has_permission(dt, "create")
	]


def center_levels() -> dict[str, str]:
	return {k: lvl for k in CENTER_KEYS if (lvl := center_access(k))}


def get_centers(levels: dict | None = None, registry: dict | None = None) -> list[dict]:
	from thinknxg_admin.api.routes import get_registry

	levels = levels if levels is not None else center_levels()
	if registry is None:
		registry = get_registry([{"key": k, "access": v} for k, v in levels.items()])
	out = []
	for key in CENTER_KEYS:
		level = levels.get(key)
		if not level:
			continue
		c = CENTERS[key]
		out.append({
			"key": key,
			"label": c["label"], "short": c["short"], "icon": c["icon"], "description": c["description"],
			"route": c["route"], "title": c["title"], "subtitle": c["subtitle"], "docs_url": c["docs_url"],
			"filters": c["filters"], "access": level,
			"navigation": _nav_for(key, level, registry),
			"quick_create": _quick_for(key, level),
		})
	return out


def personal_navigation() -> list[dict]:
	return filter_sections(PERSONAL_NAVIGATION)


def _preference_doc(user: str | None = None):
	user = user or frappe.session.user
	if not doctype_exists(PREFERENCE) or not frappe.db.exists(PREFERENCE, user):
		return None
	return frappe.get_doc(PREFERENCE, user)


def on_user_trash(doc, method=None):
	"""A deleted user's preferences go with them (and never block the delete)."""
	if doctype_exists(PREFERENCE) and frappe.db.exists(PREFERENCE, doc.name):
		frappe.delete_doc(PREFERENCE, doc.name, ignore_permissions=True, force=True)


def get_preferences() -> dict:
	doc = _preference_doc()
	if not doc:
		return {"default_center": None, "last_center": None, "state": {}}
	try:
		state = json.loads(doc.state or "{}")
	except ValueError:
		state = {}
	return {"default_center": doc.default_center or None, "last_center": doc.last_center or None, "state": state if isinstance(state, dict) else {}}


def default_center(centers: list[dict], prefs: dict) -> str | None:
	keys = [c["key"] for c in centers]
	if prefs.get("default_center") in keys:
		return prefs["default_center"]
	roles = set(frappe.get_roles())
	for rule in _landing_rules():
		if rule.role in roles and rule.center in keys:
			return rule.center
	if "admin" in keys:
		return "admin"
	return keys[0] if keys else None


# Endpoints -------------------------------------------------------------------------

STATE_KEYS = {"company": str, "branch": str, "department": str, "fiscal_year": str, "days": int, "last_route": str}


def _clean_state(state) -> dict:
	if isinstance(state, str):
		if len(state) > 16000:
			frappe.throw(_("Preferences are too large."))
		try:
			state = json.loads(state)
		except ValueError:
			frappe.throw(_("Preferences must be valid JSON."))
	if not isinstance(state, dict):
		frappe.throw(_("Preferences must be an object."))
	clean = {}
	for center, values in state.items():
		if center not in CENTER_KEYS or not isinstance(values, dict):
			continue
		row = {}
		for k, kind in STATE_KEYS.items():
			v = values.get(k)
			if v is None or v == "":
				continue
			if kind is int:
				try:
					v = max(1, min(int(v), 366))
				except (TypeError, ValueError):
					continue
			else:
				v = str(v)[:140]
				if k == "last_route" and not (v.startswith("/") and not v.startswith("//")):
					continue
			row[k] = v
		clean[center] = row
	return clean


@frappe.whitelist(methods=["POST"])
def save_preferences(default_center=None, last_center=None, state=None):
	"""Store the user's own landing choice, last center and per-center filters.

	Only ever writes the session user's row; centers must be ones they may open.
	"""
	require_login()
	user = frappe.session.user
	allowed = {c for c in CENTER_KEYS if center_access(c)}
	for value, label in ((default_center, "default"), (last_center, "last")):
		if value and value not in allowed:
			frappe.throw(_("You do not have access to the {0} command center.").format(value), frappe.PermissionError)
	doc = _preference_doc(user) or frappe.new_doc(PREFERENCE)
	doc.user = user
	if default_center is not None:
		doc.default_center = default_center or None
	if last_center is not None:
		doc.last_center = last_center or None
	if state is not None:
		doc.state = json.dumps(_clean_state(state), separators=(",", ":"))
	doc.flags.ignore_permissions = True  # scoped to the session user above
	doc.save() if not doc.is_new() else doc.insert()
	return get_preferences()


def _branch_is_dimension() -> bool:
	return doctype_exists("Accounting Dimension") and bool(
		frappe.db.exists("Accounting Dimension", {"document_type": "Branch", "disabled": 0})
	)


@frappe.whitelist()
def get_filter_options(center: str, company: str | None = None):
	"""Header filter values for a center, each list read under the user's permissions."""
	require_center(center)
	company = validate_company(company)
	filters = CENTERS[center]["filters"]
	out = {"branches": None, "departments": None, "fiscal_years": None}

	if "branch" in filters and _readable("Branch") and (center != "erp" or _branch_is_dimension()):
		out["branches"] = frappe.get_list("Branch", pluck="name", order_by="name asc", limit_page_length=500)

	if "department" in filters and _readable("Department"):
		dept_filters = {"company": company} if company else {}
		out["departments"] = frappe.get_list(
			"Department", filters=dept_filters, fields=["name", "department_name"], order_by="lft asc", limit_page_length=500
		)

	if "fiscal_year" in filters and _readable("Fiscal Year"):
		years = frappe.get_list(
			"Fiscal Year", filters={"disabled": 0}, fields=["name", "year_start_date", "year_end_date"],
			order_by="year_start_date desc", limit_page_length=50,
		)
		if company:
			# A fiscal year with no company rows applies to every company.
			linked = frappe.get_all("Fiscal Year Company", fields=["parent", "company"])
			scoped = {}
			for row in linked:
				scoped.setdefault(row.parent, set()).add(row.company)
			years = [y for y in years if y.name not in scoped or company in scoped[y.name]]
		out["fiscal_years"] = years
	return out
