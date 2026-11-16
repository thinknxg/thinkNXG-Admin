"""Automation Center: workflows, notifications, assignment rules, auto repeat,
scheduled jobs, server scripts and naming rules.

Script bodies are never returned. Enabling/disabling goes through each document's
own save, so its validation runs (for example only one active Workflow per DocType).
"""

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import cint, now_datetime, nowdate

from thinknxg_admin.api.utils import desk_route, doctype_exists, has_field, require_admin

# doctype -> (field, value meaning "on")
TOGGLES = {
	"Workflow": ("is_active", 1),
	"Notification": ("enabled", 1),
	"Assignment Rule": ("disabled", 0),
	"Auto Repeat": ("disabled", 0),
	"Scheduled Job Type": ("stopped", 0),
	"Server Script": ("disabled", 0),
	"Document Naming Rule": ("disabled", 0),
	"Milestone Tracker": ("disabled", 0),
}


def _group_counts(sql, params=None):
	return {row[0]: row[1] for row in frappe.db.sql(sql, params or ())}


@frappe.whitelist()
def get_overview():
	require_admin()
	week = now_datetime() - timedelta(days=7)
	out = {}

	out["workflows"] = None
	if doctype_exists("Workflow"):
		wfs = frappe.get_all("Workflow", fields=["name", "document_type", "is_active", "send_email_alert", "modified"], order_by="document_type asc")
		states = _group_counts("select parent, count(*) from `tabWorkflow Document State` group by parent")
		transitions = _group_counts("select parent, count(*) from `tabWorkflow Transition` group by parent")
		open_actions = _group_counts("select reference_doctype, count(*) from `tabWorkflow Action` where status = 'Open' group by reference_doctype") if doctype_exists("Workflow Action") else {}
		for w in wfs:
			w.update({"states": states.get(w.name, 0), "transitions": transitions.get(w.name, 0), "open_actions": open_actions.get(w.document_type, 0) if w.is_active else 0})
		out["workflows"] = wfs

	out["notifications"] = frappe.get_all("Notification", fields=["name", "document_type", "event", "channel", "enabled", "is_standard", "module", "days_in_advance", "date_changed", "value_changed"], order_by="document_type asc") if doctype_exists("Notification") else None

	out["assignment_rules"] = None
	if doctype_exists("Assignment Rule"):
		rules = frappe.get_all("Assignment Rule", fields=["name", "document_type", "rule", "priority", "disabled", "last_user", "modified"], order_by="priority desc, document_type asc")
		users = _group_counts("select parent, count(*) from `tabAssignment Rule User` group by parent") if frappe.db.table_exists("Assignment Rule User") else {}
		for r in rules:
			r["users"] = users.get(r.name, 0)
		out["assignment_rules"] = rules

	out["auto_repeat"] = None
	if doctype_exists("Auto Repeat"):
		out["auto_repeat"] = {
			"active": frappe.db.count("Auto Repeat", {"disabled": 0, "status": ["!=", "Completed"]}) if has_field("Auto Repeat", "status") else frappe.db.count("Auto Repeat", {"disabled": 0}),
			"by_doctype": frappe.db.sql("select reference_doctype, count(*) n from `tabAuto Repeat` where disabled = 0 group by reference_doctype order by n desc", as_dict=True),
			"upcoming": frappe.get_all("Auto Repeat", filters={"disabled": 0, "next_schedule_date": [">=", nowdate()]}, fields=["name", "reference_doctype", "reference_document", "frequency", "next_schedule_date"], order_by="next_schedule_date asc", limit=10),
		}

	out["scheduled_jobs"] = None
	if doctype_exists("Scheduled Job Type"):
		jobs = frappe.get_all("Scheduled Job Type", fields=["name", "method", "frequency", "cron_format", "stopped", "last_execution", "next_execution", "server_script", "create_log"], order_by="frequency asc, method asc")
		failures = _group_counts("select scheduled_job_type, count(*) from `tabScheduled Job Log` where status = 'Failed' and creation >= %s group by scheduled_job_type", (week,)) if doctype_exists("Scheduled Job Log") else {}
		runs = _group_counts("select scheduled_job_type, count(*) from `tabScheduled Job Log` where creation >= %s group by scheduled_job_type", (week,)) if doctype_exists("Scheduled Job Log") else {}
		for j in jobs:
			j["app"] = (j.method or "").split(".")[0] if j.method else ("server script" if j.server_script else None)
			j["failures_7d"] = failures.get(j.name, 0)
			j["runs_7d"] = runs.get(j.name, 0)
		out["scheduled_jobs"] = jobs

	out["server_scripts"] = frappe.get_all("Server Script", fields=["name", "script_type", "reference_doctype", "doctype_event", "api_method", "allow_guest", "disabled", "event_frequency", "module", "modified"], order_by="script_type asc, name asc") if doctype_exists("Server Script") else None
	out["server_scripts_enabled"] = bool(frappe.conf.get("server_script_enabled"))
	out["naming_rules"] = frappe.get_all("Document Naming Rule", fields=["name", "document_type", "prefix", "counter", "priority", "disabled"], order_by="document_type asc") if doctype_exists("Document Naming Rule") else None
	out["milestones"] = frappe.get_all("Milestone Tracker", fields=["name", "document_type", "track_field", "disabled"]) if doctype_exists("Milestone Tracker") else None

	try:
		from frappe.utils.scheduler import is_scheduler_disabled, is_scheduler_inactive

		out["scheduler"] = "disabled" if is_scheduler_disabled(verbose=False) else ("inactive" if is_scheduler_inactive(verbose=False) else "running")
	except Exception:
		out["scheduler"] = "unknown"
	return out


@frappe.whitelist(methods=["POST"])
def set_enabled(doctype: str, name: str, enabled: int):
	require_admin()
	if doctype not in TOGGLES:
		frappe.throw(_("Not supported here."))
	field, on_value = TOGGLES[doctype]
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("write")
	doc.set(field, on_value if cint(enabled) else (1 - on_value))
	doc.save()
	return True


@frappe.whitelist(methods=["POST"])
def run_scheduled_job(name: str):
	"""Queue a scheduled job now (the same as Desk's 'Execute'). System Manager only."""
	require_admin()
	frappe.only_for("System Manager")
	doc = frappe.get_doc("Scheduled Job Type", name)
	if not doc.enqueue(force=True):
		frappe.throw(_("This job is already queued or running."))
	return True


@frappe.whitelist()
def list_job_logs(job: str | None = None, status: str | None = None, start: int = 0):
	require_admin()
	if not doctype_exists("Scheduled Job Log"):
		return None
	filters = {}
	if job:
		filters["scheduled_job_type"] = job
	if status:
		filters["status"] = status
	rows = frappe.get_all("Scheduled Job Log", filters=filters, fields=["name", "scheduled_job_type", "status", "creation", "details"], order_by="creation desc", start=cint(start), page_length=40)
	for r in rows:
		lines = [ln for ln in (r.pop("details") or "").strip().splitlines() if ln.strip()]
		r["error"] = lines[-1][:200] if (lines and r.status == "Failed") else None
		r["route"] = desk_route("Scheduled Job Log", r.name)
	return {"rows": rows, "total": frappe.db.count("Scheduled Job Log", filters)}
