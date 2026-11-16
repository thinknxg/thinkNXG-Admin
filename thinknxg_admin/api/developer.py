"""Developer Tools: DocType explorer, customisations, error logs, background jobs.

Read-only by design, apart from marking error logs as seen and stopping or
clearing background jobs through Core's own RQ Job methods. There is no code
execution, no script bodies of Server Scripts, and no site configuration values.
"""

import frappe
from frappe import _
from frappe.utils import cint, now_datetime
from datetime import timedelta

from thinknxg_admin.api.utils import desk_route, doctype_exists, require_admin


def _require_sm():
	require_admin()
	frappe.only_for("System Manager")


@frappe.whitelist()
def get_overview():
	_require_sm()
	now = now_datetime()
	out = {
		"developer_mode": bool(frappe.conf.developer_mode),
		"server_scripts_enabled": bool(frappe.conf.get("server_script_enabled")),
		"doctypes": frappe.db.count("DocType", {"istable": 0}),
		"custom_doctypes": frappe.db.count("DocType", {"custom": 1}),
		"child_tables": frappe.db.count("DocType", {"istable": 1}),
		"custom_fields": frappe.db.count("Custom Field"),
		"property_setters": frappe.db.count("Property Setter"),
		"client_scripts": frappe.db.count("Client Script") if doctype_exists("Client Script") else None,
		"server_scripts": frappe.db.count("Server Script") if doctype_exists("Server Script") else None,
		"errors_24h": frappe.db.count("Error Log", {"creation": [">=", now - timedelta(hours=24)]}),
		"errors_unseen": frappe.db.count("Error Log", {"seen": 0}),
		"modules": frappe.db.count("Module Def"),
	}
	try:
		from frappe.utils.change_log import get_versions

		out["apps"] = [{"name": k, "title": v.get("title"), "version": v.get("version"), "branch": v.get("branch")} for k, v in get_versions().items()]
	except Exception:
		out["apps"] = [{"name": a} for a in frappe.get_installed_apps()]
	return out


@frappe.whitelist()
def list_doctypes(search: str | None = None, module: str | None = None, kind: str | None = None, start: int = 0, page_length: int = 50):
	_require_sm()
	filters = {}
	if search:
		filters["name"] = ["like", f"%{search}%"]
	if module:
		filters["module"] = module
	if kind == "custom":
		filters["custom"] = 1
	elif kind == "child":
		filters["istable"] = 1
	elif kind == "single":
		filters["issingle"] = 1
	elif kind == "submittable":
		filters["is_submittable"] = 1
	else:
		filters["istable"] = 0
	rows = frappe.get_all("DocType", filters=filters, fields=["name", "module", "custom", "istable", "issingle", "is_submittable", "track_changes", "is_virtual", "modified"],
		order_by="name asc", start=cint(start), page_length=max(10, min(cint(page_length) or 50, 200)))
	names = [r.name for r in rows] or ["__none__"]
	cf = dict(frappe.db.sql("select dt, count(*) from `tabCustom Field` where dt in %(n)s group by dt", {"n": tuple(names)}))
	ps = dict(frappe.db.sql("select doc_type, count(*) from `tabProperty Setter` where doc_type in %(n)s group by doc_type", {"n": tuple(names)}))
	app_of = dict(frappe.get_all("Module Def", fields=["name", "app_name"], as_list=True))
	for r in rows:
		r.update({"app": app_of.get(r.module), "custom_fields": cf.get(r.name, 0), "property_setters": ps.get(r.name, 0)})
	return {"rows": rows, "total": frappe.db.count("DocType", filters), "modules": frappe.get_all("Module Def", pluck="name", order_by="name asc")}


@frappe.whitelist()
def get_doctype(name: str):
	_require_sm()
	if not frappe.db.exists("DocType", name):
		frappe.throw(_("DocType not found."))
	meta = frappe.get_meta(name)
	custom_names = set(frappe.get_all("Custom Field", filters={"dt": name}, pluck="fieldname"))
	fields = [
		{"fieldname": f.fieldname, "label": f.label, "fieldtype": f.fieldtype, "options": (f.options or "")[:80], "reqd": f.reqd, "permlevel": f.permlevel,
		 "hidden": f.hidden, "read_only": f.read_only, "in_list_view": f.in_list_view, "unique": f.unique, "custom": f.fieldname in custom_names}
		for f in meta.fields
	]
	records = None
	if not meta.issingle and not meta.is_virtual:
		try:
			records = frappe.db.estimate_count(name) if hasattr(frappe.db, "estimate_count") else frappe.db.count(name)
		except Exception:
			records = None
	perms = frappe.get_all("Custom DocPerm" if frappe.db.exists("Custom DocPerm", {"parent": name}) else "DocPerm", filters={"parent": name},
		fields=["role", "permlevel", "read", "write", "create", "delete", "submit", "cancel", "if_owner"], order_by="permlevel asc, role asc")
	return {
		"name": name, "module": meta.module, "app": frappe.db.get_value("Module Def", meta.module, "app_name"),
		"custom": meta.custom, "istable": meta.istable, "issingle": meta.issingle, "is_submittable": meta.is_submittable,
		"track_changes": meta.track_changes, "autoname": meta.autoname, "title_field": meta.title_field, "search_fields": meta.search_fields,
		"records": records, "fields": fields, "permissions": perms,
		"links": [{"link_doctype": l.link_doctype, "link_fieldname": l.link_fieldname, "group": l.group} for l in (meta.links or [])],
		"property_setters": frappe.get_all("Property Setter", filters={"doc_type": name}, fields=["name", "field_name", "property", "value", "doctype_or_field"], order_by="field_name asc", limit=200),
		"client_scripts": frappe.get_all("Client Script", filters={"dt": name}, fields=["name", "view", "enabled"]) if doctype_exists("Client Script") else [],
		"server_scripts": frappe.get_all("Server Script", filters={"reference_doctype": name}, fields=["name", "script_type", "doctype_event", "disabled"]) if doctype_exists("Server Script") else [],
		"route": desk_route(name),
	}


@frappe.whitelist()
def list_customizations(kind: str, doctype: str | None = None, start: int = 0):
	"""Custom fields, property setters, client scripts, server scripts. No script bodies."""
	_require_sm()
	spec = {
		"custom_field": ("Custom Field", "dt", ["name", "dt", "fieldname", "label", "fieldtype", "insert_after", "module", "modified"]),
		"property_setter": ("Property Setter", "doc_type", ["name", "doc_type", "field_name", "property", "value", "is_system_generated", "module", "modified"]),
		"client_script": ("Client Script", "dt", ["name", "dt", "view", "enabled", "module", "modified"]),
		"server_script": ("Server Script", "reference_doctype", ["name", "script_type", "reference_doctype", "doctype_event", "api_method", "disabled", "module", "modified"]),
	}
	if kind not in spec:
		frappe.throw(_("Unknown kind"))
	dt, dt_field, fields = spec[kind]
	if not doctype_exists(dt):
		return None
	filters = {dt_field: doctype} if doctype else {}
	rows = frappe.get_all(dt, filters=filters, fields=fields, order_by="modified desc", start=cint(start), page_length=50)
	for r in rows:
		if "value" in r and r.value and len(str(r.value)) > 80:
			r["value"] = str(r.value)[:79] + "…"
		r["route"] = desk_route(dt, r.name)
	return {"rows": rows, "total": frappe.db.count(dt, filters)}


@frappe.whitelist()
def list_errors(search: str | None = None, seen: str | None = None, start: int = 0):
	_require_sm()
	filters = {}
	if seen in ("0", "1"):
		filters["seen"] = cint(seen)
	if search:
		filters["method"] = ["like", f"%{search}%"]
	rows = frappe.get_all("Error Log", filters=filters, fields=["name", "method", "reference_doctype", "reference_name", "seen", "creation", "error"], order_by="creation desc", start=cint(start), page_length=40)
	for r in rows:
		lines = [ln.strip() for ln in (r.pop("error") or "").strip().splitlines() if ln.strip()]
		r["exception"] = lines[-1][:220] if lines else None
	return {"rows": rows, "total": frappe.db.count("Error Log", filters)}


@frappe.whitelist()
def get_error(name: str):
	_require_sm()
	doc = frappe.get_doc("Error Log", name)
	return {f: doc.get(f) for f in ("name", "method", "error", "reference_doctype", "reference_name", "seen", "creation", "trace_id")}


@frappe.whitelist(methods=["POST"])
def mark_errors_seen(names=None, all_unseen: int = 0):
	_require_sm()
	if cint(all_unseen):
		frappe.db.set_value("Error Log", {"seen": 0}, "seen", 1, update_modified=False)
		return True
	for n in frappe.parse_json(names) or []:
		frappe.db.set_value("Error Log", n, "seen", 1, update_modified=False)
	return True


@frappe.whitelist()
def list_jobs(status: str = "failed", queue: str | None = None):
	_require_sm()
	filters = {"status": status}
	if queue:
		filters["queue"] = queue
	try:
		rows = frappe.get_list("RQ Job", filters=filters, fields=["job_id", "job_name", "queue", "status", "started_at", "ended_at", "time_taken", "exc_info"], limit_page_length=100)
	except Exception as e:
		return {"rows": [], "error": str(e)[:200]}
	out = []
	for r in rows:
		lines = [ln.strip() for ln in (r.get("exc_info") or "").strip().splitlines() if ln.strip()]
		out.append({**{k: r.get(k) for k in ("job_id", "job_name", "queue", "status", "started_at", "ended_at", "time_taken")}, "exception": lines[-1][:220] if lines else None, "route": desk_route("RQ Job", r.get("job_id"))})
	return {"rows": out}


@frappe.whitelist(methods=["POST"])
def stop_job(job_id: str):
	_require_sm()
	from frappe.core.doctype.rq_job.rq_job import stop_job as core_stop

	core_stop(job_id)
	return True


@frappe.whitelist(methods=["POST"])
def clear_failed_jobs():
	_require_sm()
	from frappe.core.doctype.rq_job.rq_job import remove_failed_jobs

	remove_failed_jobs()
	return True
