"""Central route registry for the unified Command Center.

Every ERP and HR page lives at an internal route; this module is the single
source for them, on the server and (through boot) in the browser:

    /thinknxg/<center>                              center dashboard
    /thinknxg/<center>/<module>                     module page
    /thinknxg/<center>/<module>/<doctype-slug>      document list
    /thinknxg/<center>/<module>/<doctype-slug>/new  new document
    /thinknxg/<center>/<module>/<doctype-slug>/<name>
    /thinknxg/<center>/reports/<report name>        report runner
    /thinknxg/<center>/doc/<doctype-slug>[/<name>]  any other DocType of that app

``internal_route()`` turns a DocType (+ name, filters) or an old Desk path into
one of these. Boot sends each user only the modules and DocTypes they may read;
every list, form and save is checked again on the server.
"""

from urllib.parse import quote, urlencode

import frappe

from thinknxg_admin.api.utils import doctype_exists, request_cache

BASE = "/thinknxg"

# center -> modules. Each module: key, label, icon, app, groups [(label, [DocTypes])], reports.
MODULES = {
	"erp": [
		{"key": "accounting", "label": "Accounting", "icon": "landmark", "workspaces": ["Accounting", "Invoicing", "Payments", "Financial Reports"], "groups": [
			("Transactions", ["Sales Invoice", "Purchase Invoice", "Payment Entry", "Journal Entry", "Payment Request"]),
			("Masters", ["Account", "Cost Center", "Bank Account", "Mode of Payment", "Fiscal Year"]),
		], "reports": ["General Ledger", "Trial Balance", "Balance Sheet", "Profit and Loss Statement", "Cash Flow", "Accounts Receivable", "Accounts Payable", "Gross Profit"]},
		{"key": "selling", "label": "Selling", "icon": "shopping-cart", "workspaces": ["Selling"], "groups": [
			("Transactions", ["Quotation", "Sales Order", "Delivery Note", "Sales Invoice"]),
			("Customers", ["Customer", "Lead", "Opportunity", "Customer Group", "Sales Person"]),
		], "reports": ["Sales Analytics", "Sales Register", "Item-wise Sales Register"]},
		{"key": "buying", "label": "Buying", "icon": "shopping-bag", "workspaces": ["Buying"], "groups": [
			("Transactions", ["Material Request", "Request for Quotation", "Supplier Quotation", "Purchase Order", "Purchase Receipt", "Purchase Invoice"]),
			("Suppliers", ["Supplier", "Supplier Group"]),
		], "reports": ["Purchase Analytics", "Purchase Register"]},
		{"key": "stock", "label": "Stock", "icon": "package", "workspaces": ["Stock"], "groups": [
			("Transactions", ["Stock Entry", "Stock Reconciliation", "Material Request", "Delivery Note", "Purchase Receipt"]),
			("Items", ["Item", "Item Group", "Item Price", "Price List", "Batch", "Serial No", "UOM", "Warehouse"]),
		], "reports": ["Stock Balance", "Stock Ledger", "Stock Ageing", "Stock Projected Qty"]},
		{"key": "manufacturing", "label": "Manufacturing", "icon": "factory", "workspaces": ["Manufacturing"], "groups": [
			("Production", ["Work Order", "Job Card", "Production Plan"]),
			("Setup", ["BOM", "Workstation", "Operation", "Routing"]),
		], "reports": ["Production Planning Report", "Work Order Summary"]},
		{"key": "crm", "label": "CRM", "icon": "handshake", "workspaces": ["CRM"], "groups": [
			("Pipeline", ["Lead", "Opportunity", "Prospect", "Appointment"]),
			("Contacts", ["Customer", "Contact", "Campaign"]),
		], "reports": ["Lead Details"]},
		{"key": "projects", "label": "Projects", "icon": "folder-kanban", "workspaces": ["Projects"], "groups": [
			("Projects", ["Project", "Task", "Timesheet"]),
			("Setup", ["Activity Type", "Project Template"]),
		], "reports": ["Project Summary"]},
		{"key": "assets", "label": "Assets", "icon": "box", "workspaces": ["Assets"], "groups": [
			("Assets", ["Asset", "Asset Movement", "Asset Maintenance", "Asset Repair"]),
			("Setup", ["Asset Category", "Location"]),
		], "reports": ["Asset Depreciation Ledger"]},
		{"key": "quality", "label": "Quality", "icon": "badge-check", "workspaces": ["Quality"], "groups": [
			("Quality", ["Quality Inspection", "Non Conformance", "Quality Action", "Quality Feedback", "Quality Review"]),
			("Setup", ["Quality Goal", "Quality Procedure"]),
		], "reports": []},
		{"key": "support", "label": "Support", "icon": "life-buoy", "workspaces": ["Support"], "groups": [
			("Support", ["Issue", "Warranty Claim", "Maintenance Visit", "Maintenance Schedule"]),
			("Setup", ["Service Level Agreement"]),
		], "reports": []},
	],
	"hr": [
		{"key": "employees", "label": "Employees", "icon": "users", "hr_only": True, "workspaces": ["HR Setup"], "groups": [
			("People", ["Employee"]),
			("Organization", ["Department", "Designation", "Branch", "Employee Grade", "Employee Group", "Holiday List"]),
		], "reports": ["Employee Analytics", "Employee Birthday"]},
		{"key": "attendance", "label": "Attendance", "icon": "calendar-check", "workspaces": ["Shift & Attendance"], "groups": [
			("Attendance", ["Attendance", "Employee Checkin", "Attendance Request"]),
			("Shifts", ["Shift Assignment", "Shift Request", "Shift Type"]),
		], "reports": ["Monthly Attendance Sheet", "Shift Attendance"]},
		{"key": "leave", "label": "Leave", "icon": "plane", "workspaces": ["Leaves"], "groups": [
			("Requests", ["Leave Application", "Compensatory Leave Request", "Leave Encashment"]),
			("Allocation", ["Leave Allocation", "Leave Policy Assignment"]),
			("Setup", ["Leave Type", "Leave Policy", "Holiday List"]),
		], "reports": ["Employee Leave Balance", "Employee Leave Balance Summary"]},
		{"key": "payroll", "label": "Payroll", "icon": "wallet", "payroll": True, "workspaces": ["Payroll", "Tax & Benefits"], "groups": [
			("Payroll", ["Payroll Entry", "Salary Slip", "Additional Salary"]),
			("Setup", ["Salary Structure", "Salary Structure Assignment", "Salary Component", "Payroll Period", "Income Tax Slab"]),
		], "reports": ["Salary Register"]},
		{"key": "recruitment", "label": "Recruitment", "icon": "user-search", "hr_only": True, "workspaces": ["Recruitment"], "groups": [
			("Hiring", ["Job Opening", "Job Applicant", "Interview", "Interview Feedback", "Job Offer"]),
			("Planning", ["Job Requisition", "Staffing Plan"]),
		], "reports": ["Recruitment Analytics"]},
		{"key": "performance", "label": "Performance", "icon": "trophy", "hr_only": True, "workspaces": ["Performance"], "groups": [
			("Appraisals", ["Appraisal Cycle", "Appraisal", "Employee Performance Feedback"]),
			("Goals", ["Goal", "KRA", "Appraisal Template"]),
		], "reports": ["Appraisal Overview"]},
		{"key": "training", "label": "Training", "icon": "graduation-cap", "hr_only": True, "workspaces": [], "groups": [
			("Training", ["Training Program", "Training Event", "Training Feedback", "Training Result"]),
		], "reports": []},
		{"key": "lifecycle", "label": "Lifecycle", "icon": "route", "hr_only": True, "workspaces": ["Tenure"], "groups": [
			("Lifecycle", ["Employee Onboarding", "Employee Separation", "Employee Transfer", "Employee Promotion"]),
			("Exits and grievances", ["Exit Interview", "Full and Final Statement", "Employee Grievance"]),
		], "reports": ["Employee Exits"]},
		{"key": "expenses", "label": "Expenses", "icon": "receipt", "workspaces": ["Expenses"], "groups": [
			("Expenses", ["Expense Claim", "Employee Advance"]),
			("Setup", ["Expense Claim Type"]),
		], "reports": ["Employee Advance Summary"]},
	],
}

# Existing Admin pages for Core DocTypes; everything else in Core opens in the
# generic form at /thinknxg/admin/doc/... .
ADMIN_PAGES = {
	"User": "/admin/users", "User Invitation": "/admin/users/invitations", "User Permission": "/admin/users/permissions",
	"Role": "/admin/roles", "Role Profile": "/admin/roles/profiles", "Company": "/admin/organization",
	"Workspace": "/admin/workspaces", "Module Def": "/admin/apps", "Installed Application": "/admin/apps",
	"System Settings": "/admin/configuration", "Notification Log": "/notifications", "Report": "/reports",
	"Activity Log": "/admin/audit", "Access Log": "/admin/audit", "Version": "/admin/audit",
	"Webhook": "/admin/integrations", "OAuth Client": "/admin/integrations", "Workflow": "/admin/automation",
	"Assignment Rule": "/admin/automation", "Scheduled Job Type": "/admin/automation", "Error Log": "/admin/developer",
	"RQ Job": "/admin/system-health", "System Health Report": "/admin/system-health",
}
# Developer tools that exist only in the Desk; offered to System Managers only.
DESK_ONLY = {"DocType", "Customize Form", "Print Format", "Server Script", "Client Script", "Web Form", "Property Setter", "Custom Field", "Report Builder"}
APP_CENTER = {"erpnext": "erp", "hrms": "hr"}


def slug(doctype: str) -> str:
	return doctype.lower().replace(" ", "-")


def _app_of(doctype: str) -> str | None:
	cache = request_cache("_nxg_doctype_app")
	if doctype not in cache:
		module = frappe.db.get_value("DocType", doctype, "module")
		cache[doctype] = frappe.db.get_value("Module Def", module, "app_name") if module else None
	return cache[doctype]


def _index() -> dict:
	"""DocType -> (center, module) for the first module that lists it."""
	idx = request_cache("_nxg_route_index")
	if not idx:
		for center, modules in MODULES.items():
			for m in modules:
				for _label, doctypes in m["groups"]:
					for dt in doctypes:
						idx.setdefault(dt, (center, m["key"]))
	return idx


def workspace_route(name: str) -> str | None:
	for center, modules in MODULES.items():
		for m in modules:
			if name in m.get("workspaces", []):
				return f"{BASE}/{center}/{m['key']}"
	return None


def report_route(report: str, center: str | None = None) -> str:
	if not center:
		ref = frappe.db.get_value("Report", report, "ref_doctype") if doctype_exists("Report") else None
		center = _center_for(ref) if ref else "erp"
	return f"{BASE}/{center}/reports/{quote(report)}"


def _center_for(doctype: str) -> str:
	hit = _index().get(doctype)
	if hit:
		return hit[0]
	return APP_CENTER.get(_app_of(doctype) or "", "admin")


def internal_route(doctype: str | None, name: str | None = None, filters: dict | None = None, new: bool = False) -> str:
	"""The internal thinkNXG address for a DocType list, a new document or one document."""
	if not doctype:
		return f"{BASE}/"
	if doctype in DESK_ONLY:
		return f"/desk/{slug(doctype)}" + (f"/{quote(str(name), safe='')}" if name else "")
	if doctype in ADMIN_PAGES and not new and (not name or doctype in ("User", "Role")):
		# Lists open their Admin page; users and roles open in that page's panel.
		page = ADMIN_PAGES[doctype]
		params = dict(filters or {})
		if name:
			params["open"] = name
		return f"{BASE}{page}" + (f"?{urlencode(params)}" if params else "")
	hit = _index().get(doctype)
	if hit:
		base = f"{BASE}/{hit[0]}/{hit[1]}/{slug(doctype)}"
	else:
		base = f"{BASE}/{_center_for(doctype)}/doc/{slug(doctype)}"
	if new:
		return f"{base}/new"
	if name:
		return f"{base}/{quote(str(name), safe='')}"
	return base + (f"?{urlencode({k: v for k, v in filters.items() if v is not None})}" if filters else "")


def from_desk_path(path: str) -> str:
	"""Translate an old /desk or /app address into its internal route."""
	from urllib.parse import parse_qsl, urlsplit

	parts = urlsplit(path)
	segs = [s for s in parts.path.split("/") if s]
	if not segs or segs[0] not in ("desk", "app"):
		return path
	segs = segs[1:]
	if not segs:
		return f"{BASE}/"
	if segs[0] == "query-report" and len(segs) > 1:
		return report_route(frappe.utils.unquote(segs[1]))
	doctype = frappe.db.get_value("DocType", {"name": ["like", segs[0].replace("-", " ")]}, "name")
	if not doctype:
		ws = frappe.db.get_value("Workspace", {"name": ["like", frappe.utils.unquote(segs[0]).replace("-", " ")]}, "name") if doctype_exists("Workspace") else None
		return (workspace_route(ws) if ws else None) or f"{BASE}/not-found?from={quote(path)}"
	if len(segs) == 1:
		return internal_route(doctype, filters=dict(parse_qsl(parts.query)) or None)
	if segs[1] == "new":
		return internal_route(doctype, new=True)
	if segs[1] == "view":
		return internal_route(doctype)
	return internal_route(doctype, frappe.utils.unquote(segs[1]))


# Registry for boot ----------------------------------------------------------------

def _readable(doctype):
	return doctype_exists(doctype) and frappe.has_permission(doctype, "read")


def get_registry(centers: list[dict]) -> dict:
	"""Modules, DocTypes and reports this user may open, per granted center."""
	from thinknxg_admin.api.centers import can_view_payroll

	granted = {c["key"]: c["access"] for c in centers}
	out = {"modules": {}, "doctypes": {}}
	payroll = can_view_payroll()
	report_ok = set()
	if doctype_exists("Report"):
		names = [r for mods in MODULES.values() for m in mods for r in m["reports"]]
		report_ok = {r.name for r in frappe.get_all("Report", filters={"name": ["in", names], "disabled": 0}, fields=["name"])}
	for center, modules in MODULES.items():
		level = granted.get(center)
		if not level:
			continue
		mods = []
		for m in modules:
			if m.get("payroll") and not payroll:
				continue
			if m.get("hr_only") and level == "team":
				continue
			groups = []
			for label, doctypes in m["groups"]:
				items = []
				for dt in doctypes:
					if not _readable(dt):
						continue
					items.append({"doctype": dt, "slug": slug(dt), "create": frappe.has_permission(dt, "create")})
					out["doctypes"].setdefault(dt, {"center": center, "module": m["key"], "slug": slug(dt)})
				if items:
					groups.append({"label": label, "items": items})
			if not groups:
				continue
			reports = [r for r in m["reports"] if r in report_ok and _report_allowed(r)]
			mods.append({"key": m["key"], "label": m["label"], "icon": m["icon"], "groups": groups, "reports": reports})
		out["modules"][center] = mods
	return out


def _report_allowed(name: str) -> bool:
	try:
		return frappe.get_cached_doc("Report", name).is_permitted()
	except Exception:
		return False
