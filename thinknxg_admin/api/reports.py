"""Reports & Analytics: a permission-aware catalogue of reports and dashboards,
usage from the Access Log, and scheduled (Auto Email) reports.

Visibility follows Core's rule for Report: when a report lists roles, the user
needs one of them; otherwise read access to the report's reference DocType.
"""

from datetime import timedelta

import frappe
from frappe.utils import cint, now_datetime

from thinknxg_admin.api.utils import doctype_exists, is_admin, require_login, slug


def report_route(name, report_type, ref_doctype):
	if report_type in ("Script Report", "Query Report"):
		return f"/desk/query-report/{name}"
	if ref_doctype:
		return f"/desk/{slug(ref_doctype)}/view/report/{name}"
	return f"/desk/report/{name}"


def _visible(reports, admin):
	roles = {}
	for r in frappe.get_all("Has Role", filters={"parenttype": "Report", "parent": ["in", [x.name for x in reports] or ["__none__"]]}, fields=["parent", "role"]):
		roles.setdefault(r.parent, set()).add(r.role)
	mine = set(frappe.get_roles())
	cache = {}
	out = []
	for r in reports:
		r_roles = roles.get(r.name, set())
		if not admin:
			if r_roles and not (r_roles & mine):
				continue
			if not r_roles and r.ref_doctype:
				if r.ref_doctype not in cache:
					cache[r.ref_doctype] = frappe.has_permission(r.ref_doctype, "read")
				if not cache[r.ref_doctype]:
					continue
		r["roles"] = sorted(r_roles)
		out.append(r)
	return out


@frappe.whitelist()
def get_catalog(include_disabled: int = 0):
	require_login()
	admin = is_admin()
	filters = {} if (admin and cint(include_disabled)) else {"disabled": 0}
	reports = frappe.get_all("Report", filters=filters,
		fields=["name", "report_type", "ref_doctype", "module", "is_standard", "disabled", "prepared_report", "modified"], order_by="name asc")
	reports = _visible(reports, admin)
	app_of = dict(frappe.get_all("Module Def", fields=["name", "app_name"], as_list=True))

	usage = {}
	if doctype_exists("Access Log"):
		since = now_datetime() - timedelta(days=30)
		usage = dict(frappe.db.sql("select report_name, count(*) from `tabAccess Log` where ifnull(report_name, '') != '' and creation >= %s group by report_name", since))
	mine = {}
	if doctype_exists("Route History"):
		for (route,) in frappe.db.sql("select route from `tabRoute History` where user = %s and route like 'query-report/%%' order by creation desc limit 200", frappe.session.user):
			name = route.split("/", 1)[1] if "/" in route else route
			mine[name] = mine.get(name, 0) + 1
	for r in reports:
		r["app"] = app_of.get(r.module)
		r["route"] = report_route(r.name, r.report_type, r.ref_doctype)
		r["exports_30d"] = usage.get(r.name, 0)
		r["my_opens"] = mine.get(r.name, 0)

	dashboards = []
	if doctype_exists("Dashboard"):
		dashboards = frappe.get_list("Dashboard", fields=["name", "module", "is_default", "is_standard"], order_by="name asc", limit_page_length=500)
		charts = dict(frappe.db.sql("select parent, count(*) from `tabDashboard Chart Link` group by parent")) if frappe.db.table_exists("Dashboard Chart Link") else {}
		cards = dict(frappe.db.sql("select parent, count(*) from `tabNumber Card Link` group by parent")) if frappe.db.table_exists("Number Card Link") else {}
		for d in dashboards:
			d["charts"] = charts.get(d.name, 0)
			d["cards"] = cards.get(d.name, 0)
			d["route"] = f"/desk/dashboard-view/{d.name}"

	scheduled = []
	if doctype_exists("Auto Email Report"):
		f = {} if admin else {"user": frappe.session.user}
		scheduled = frappe.get_list("Auto Email Report", filters=f, fields=["name", "report", "user", "enabled", "frequency", "format", "day_of_week", "email_to"], order_by="report asc", limit_page_length=500)
		for s in scheduled:
			s["recipients"] = len([e for e in (s.pop("email_to") or "").replace(",", "\n").split("\n") if e.strip()])

	return {
		"reports": reports,
		"dashboards": dashboards,
		"scheduled": scheduled,
		"is_admin": admin,
		"modules": sorted({r.module for r in reports if r.module}),
		"counts": {
			"charts": frappe.db.count("Dashboard Chart") if doctype_exists("Dashboard Chart") else None,
			"number_cards": frappe.db.count("Number Card") if doctype_exists("Number Card") else None,
			"prepared_running": frappe.db.count("Prepared Report", {"status": ["in", ["Queued", "Started"]]}) if doctype_exists("Prepared Report") else None,
		},
	}


@frappe.whitelist(methods=["POST"])
def set_auto_email_enabled(name: str, enabled: int):
	require_login()
	doc = frappe.get_doc("Auto Email Report", name)
	doc.check_permission("write")
	doc.enabled = cint(enabled)
	doc.save()
	return True
