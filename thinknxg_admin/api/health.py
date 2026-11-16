"""System health for the Command Center.

``get_live_health`` - fast checks (pings and counts) used by the dashboard
panel and the header status pill.
``get_full_report`` - the V16 System Health Report (virtual DocType) for the
System Health page; it is heavier, so it is only loaded on demand.
"""

import os
import shutil
import time
from datetime import timedelta

import frappe
from frappe.utils import now_datetime

from thinknxg_admin.api.cache import cached_panel
from thinknxg_admin.api.utils import doctype_exists, require_admin, safe_count

OK, WARN, FAIL, UNKNOWN = "ok", "warning", "critical", "unknown"


def _timed(fn):
	t = time.perf_counter()
	value = fn()
	return value, round((time.perf_counter() - t) * 1000, 1)


def _check(key, label, fn):
	try:
		return {"key": key, "label": label, **fn()}
	except Exception as e:
		return {"key": key, "label": label, "status": FAIL, "detail": str(e)[:160]}


def _database():
	version, ms = _timed(lambda: frappe.db.sql("select version()")[0][0])
	return {"status": OK if ms < 250 else WARN, "detail": f"{frappe.conf.db_type or 'mariadb'} {version}", "latency_ms": ms}


def _cache():
	_, ms = _timed(lambda: frappe.cache.ping())
	return {"status": OK if ms < 100 else WARN, "detail": "Redis cache reachable", "latency_ms": ms}


def _queues_and_workers():
	from rq.registry import FailedJobRegistry, StartedJobRegistry

	from frappe.utils.background_jobs import get_queues, get_redis_conn, get_workers

	conn = get_redis_conn()
	queues, total_queued, total_failed = [], 0, 0
	for q in get_queues(connection=conn):
		name = q.name.split(":")[-1]
		queued, running, failed = q.count, StartedJobRegistry(queue=q).count, FailedJobRegistry(queue=q).count
		total_queued += queued
		total_failed += failed
		queues.append({"name": name, "queued": queued, "running": running, "failed": failed})
	workers = get_workers()
	busy = sum(1 for w in workers if w.get_state() == "busy")
	queue_status = OK if total_queued < 500 else WARN
	worker_status = FAIL if not workers else (WARN if busy == len(workers) and total_queued else OK)
	return (
		{"status": queue_status, "detail": f"{total_queued} queued · {total_failed} failed", "queued": total_queued, "failed": total_failed, "queues": queues},
		{"status": worker_status, "detail": f"{len(workers)} workers · {busy} busy", "workers": len(workers), "busy": busy},
	)


def _scheduler():
	from frappe.utils.scheduler import is_scheduler_disabled, is_scheduler_inactive

	if is_scheduler_disabled(verbose=False):
		return {"status": FAIL, "detail": "Disabled"}
	if is_scheduler_inactive(verbose=False):
		return {"status": WARN, "detail": "Enabled, no recent activity"}
	return {"status": OK, "detail": "Running"}


def _storage():
	site = frappe.get_site_path()
	usage = shutil.disk_usage(os.path.abspath(site))
	pct = round(usage.used * 100 / usage.total, 1) if usage.total else None
	status = OK if pct is None or pct < 80 else (WARN if pct < 92 else FAIL)
	return {"status": status, "detail": f"{pct}% of disk used", "used_pct": pct, "free_bytes": usage.free, "total_bytes": usage.total}


def _errors():
	n = safe_count("Error Log", {"creation": [">", now_datetime() - timedelta(hours=24)]})
	if n is None:
		return {"status": UNKNOWN, "detail": "Error Log not available"}
	return {"status": OK if n == 0 else (WARN if n < 25 else FAIL), "detail": f"{n} in the last 24 h", "count": n}


@frappe.whitelist()
@cached_panel
def get_live_health():
	require_admin()
	checks = [
		_check("app", "Application", lambda: {"status": OK, "detail": f"thinkNXG Framework {frappe.__version__}"}),
		_check("database", "Database", _database),
		_check("redis", "Redis cache", _cache),
	]
	try:
		q, w = _queues_and_workers()
		checks += [{"key": "queues", "label": "Queues", **q}, {"key": "workers", "label": "Workers", **w}]
	except Exception as e:
		checks += [
			{"key": "queues", "label": "Queues", "status": FAIL, "detail": str(e)[:160]},
			{"key": "workers", "label": "Workers", "status": UNKNOWN, "detail": "Queue connection failed"},
		]
	checks += [
		_check("scheduler", "Scheduler", _scheduler),
		_check("storage", "Storage", _storage),
		_check("errors", "Application errors", _errors),
	]
	rank = {OK: 0, UNKNOWN: 1, WARN: 2, FAIL: 3}
	worst = max((c["status"] for c in checks), key=lambda s: rank.get(s, 1))
	healthy = sum(1 for c in checks if c["status"] == OK)
	return {
		"status": worst,
		"summary": {OK: "All systems operational", WARN: "Needs attention", FAIL: "Action required", UNKNOWN: "Some checks unavailable"}[worst],
		"healthy": healthy,
		"total": len(checks),
		"checks": checks,
		"checked_at": now_datetime(),
	}


REPORT_FIELDS = [
	"total_background_workers", "scheduler_status", "socketio_ping_check", "socketio_transport_mode",
	"failed_emails", "total_outgoing_emails", "pending_emails", "total_errors", "database", "database_version",
	"db_storage_usage", "bufferpool_size", "binary_logging", "cache_keys", "cache_memory_usage", "backups_size",
	"private_files_size", "public_files_size", "onsite_backups", "total_users", "new_users", "failed_logins",
	"active_sessions", "background_jobs_check", "oldest_unscheduled_job",
]
REPORT_TABLES = ["background_workers", "queue_status", "top_errors", "top_db_tables", "failing_scheduled_jobs"]


@frappe.whitelist()
def get_full_report():
	"""V16 System Health Report, as the Desk form shows it. Heavy: on demand only."""
	require_admin()
	if not doctype_exists("System Health Report"):
		return None
	doc = frappe.get_doc("System Health Report")
	out = {f: doc.get(f) for f in REPORT_FIELDS}
	for t in REPORT_TABLES:
		out[t] = [{k: v for k, v in row.as_dict().items() if not k.startswith("_") and k not in ("parent", "parenttype", "parentfield", "doctype", "owner", "modified_by", "docstatus")} for row in (doc.get(t) or [])]
	out["generated_at"] = now_datetime()
	return out
