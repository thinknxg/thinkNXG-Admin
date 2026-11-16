"""Integration Center.

Secrets never leave the server: webhook secrets and header values, OAuth client
secrets, connected-app secrets and tokens, email passwords and API secrets are
not selected at all. URLs are reduced to scheme, host and path, because query
strings and user-info often carry credentials.
"""

from datetime import timedelta
from urllib.parse import urlsplit

import frappe
from frappe.utils import cint, now_datetime

from thinknxg_admin.api.utils import desk_route, doctype_exists, has_field, require_admin, safe_count


def safe_url(url: str | None) -> str | None:
	if not url:
		return None
	try:
		parts = urlsplit(url)
		if not parts.netloc:
			return parts.path[:120] or None
		host = parts.hostname or ""
		if parts.port:
			host += f":{parts.port}"
		return f"{parts.scheme}://{host}{parts.path}"[:160]
	except Exception:
		return None


def _short(text, n=240):
	if not text:
		return None
	text = frappe.utils.strip_html(str(text)).strip()
	return text if len(text) <= n else text[: n - 1] + "…"


def _last_error_line(trace: str | None):
	if not trace:
		return None
	lines = [ln.strip() for ln in str(trace).strip().splitlines() if ln.strip()]
	return _short(lines[-1], 200) if lines else None


@frappe.whitelist()
def get_overview():
	require_admin()
	now = now_datetime()
	day, week = now - timedelta(hours=24), now - timedelta(days=7)
	out = {}

	# Webhooks + their delivery health from Webhook Request Log
	out["webhooks"] = None
	if doctype_exists("Webhook"):
		hooks = frappe.get_all("Webhook", fields=["name", "webhook_doctype", "webhook_docevent", "request_url", "request_method", "enabled", "enable_security", "is_dynamic_url", "modified"], order_by="modified desc")
		stats = {}
		if doctype_exists("Webhook Request Log"):
			for row in frappe.db.sql(
				"""select webhook, count(*) total, sum(case when ifnull(error, '') != '' then 1 else 0 end) failed, max(creation) last_call
				from `tabWebhook Request Log` where creation >= %s group by webhook""", week, as_dict=True):
				stats[row.webhook] = row
			fails24 = dict(frappe.db.sql("""select webhook, count(*) from `tabWebhook Request Log` where creation >= %s and ifnull(error, '') != '' group by webhook""", day))
		else:
			fails24 = {}
		for h in hooks:
			s = stats.get(h.name) or {}
			h["request_url"] = "Dynamic URL" if h.is_dynamic_url else safe_url(h.request_url)
			h.update({"calls_7d": cint(s.get("total")), "failed_7d": cint(s.get("failed")), "failed_24h": cint(fails24.get(h.name)), "last_call": s.get("last_call")})
		out["webhooks"] = hooks

	out["oauth_clients"] = None
	if doctype_exists("OAuth Client"):
		clients = frappe.get_all("OAuth Client", fields=["name", "app_name", "client_id", "grant_type", "response_type", "scopes", "default_redirect_uri", "skip_authorization", "modified"])
		tokens = dict(frappe.db.sql("select client, count(*) from `tabOAuth Bearer Token` where status = 'Active' group by client")) if doctype_exists("OAuth Bearer Token") else {}
		for c in clients:
			c["redirect"] = safe_url(c.pop("default_redirect_uri", None))
			c["scopes"] = [s for s in (c.scopes or "").split() if s]
			c["active_tokens"] = tokens.get(c.name, 0)
		out["oauth_clients"] = clients

	out["connected_apps"] = None
	if doctype_exists("Connected App"):
		apps = frappe.get_all("Connected App", fields=["name", "provider_name", "client_id", "authorization_uri", "modified"])
		tokens = dict(frappe.db.sql("select connected_app, count(*) from `tabToken Cache` group by connected_app")) if doctype_exists("Token Cache") else {}
		for a in apps:
			a["authorization_uri"] = safe_url(a.authorization_uri)
			a["connected_users"] = tokens.get(a.name, 0)
		out["connected_apps"] = apps

	out["social_logins"] = frappe.get_all("Social Login Key", fields=["name", "provider_name", "social_login_provider", "enable_social_login", "sign_ups"]) if doctype_exists("Social Login Key") else None

	out["email_accounts"] = None
	if doctype_exists("Email Account"):
		fields = [f for f in ("name", "email_account_name", "email_id", "service", "enable_incoming", "enable_outgoing", "default_incoming", "default_outgoing", "use_imap") if f == "name" or has_field("Email Account", f)]
		accounts = frappe.get_all("Email Account", fields=fields, order_by="default_outgoing desc, name asc")
		queue = {}
		if doctype_exists("Email Queue") and has_field("Email Queue", "email_account"):
			for acc, status, n in frappe.db.sql("select email_account, status, count(*) from `tabEmail Queue` where creation >= %s group by email_account, status", week):
				queue.setdefault(acc, {})[status] = n
		for a in accounts:
			q = queue.get(a.name, {})
			a["sent_7d"] = q.get("Sent", 0)
			a["errors_7d"] = q.get("Error", 0)
			a["pending"] = q.get("Not Sent", 0) + q.get("Sending", 0)
		out["email_accounts"] = accounts
	out["email_queue"] = {
		"pending": safe_count("Email Queue", {"status": ["in", ["Not Sent", "Sending"]]}),
		"errors_24h": safe_count("Email Queue", {"status": "Error", "creation": [">=", day]}),
		"sent_24h": safe_count("Email Queue", {"status": "Sent", "creation": [">=", day]}),
	}

	# REST API access: users holding an API key (the key is an identifier; secrets stay hidden)
	api_users = frappe.get_all("User", filters={"api_key": ["is", "set"]}, fields=["name", "full_name", "enabled", "api_key"], order_by="full_name asc", limit=200)
	last_call = {}
	if doctype_exists("API Request Log") and api_users:
		last_call = dict(frappe.db.sql("select user, max(creation) from `tabAPI Request Log` where user in %(u)s group by user", {"u": tuple(u.name for u in api_users)}))
	for u in api_users:
		u["last_request"] = last_call.get(u.name)
	out["api_users"] = api_users
	out["api_requests_24h"] = safe_count("API Request Log", {"creation": [">=", day]})

	out["integration_requests"] = None
	if doctype_exists("Integration Request"):
		out["integration_requests"] = frappe.db.sql(
			"""select ifnull(integration_request_service, 'Other') service, status, count(*) n
			from `tabIntegration Request` where creation >= %s group by service, status order by service""", week, as_dict=True)
	return out


@frappe.whitelist()
def list_webhook_logs(webhook: str | None = None, only_errors: int = 0, start: int = 0, page_length: int = 30):
	require_admin()
	if not doctype_exists("Webhook Request Log"):
		return None
	filters = {}
	if webhook:
		filters["webhook"] = webhook
	if cint(only_errors):
		filters["error"] = ["is", "set"]
	rows = frappe.get_all("Webhook Request Log", filters=filters,
		fields=["name", "webhook", "url", "user", "reference_doctype", "reference_document", "error", "response", "creation"],
		order_by="creation desc", start=cint(start), page_length=max(10, min(cint(page_length) or 30, 100)))
	for r in rows:
		r["url"] = safe_url(r.url)
		r["error"] = _last_error_line(r.error)
		r["response"] = _short(r.response, 160)
		r["route"] = desk_route("Webhook Request Log", r.name)
	return {"rows": rows, "total": frappe.db.count("Webhook Request Log", filters)}


@frappe.whitelist()
def list_integration_requests(status: str | None = None, start: int = 0):
	require_admin()
	if not doctype_exists("Integration Request"):
		return None
	filters = {"status": status} if status else {}
	rows = frappe.get_all("Integration Request", filters=filters,
		fields=["name", "integration_request_service", "status", "reference_doctype", "reference_docname", "is_remote_request", "url", "error", "creation"],
		order_by="creation desc", start=cint(start), page_length=30)
	for r in rows:
		r["url"] = safe_url(r.url)
		r["error"] = _last_error_line(r.error)
		r["route"] = desk_route("Integration Request", r.name)
	return {"rows": rows, "total": frappe.db.count("Integration Request", filters)}


@frappe.whitelist(methods=["POST"])
def set_webhook_enabled(name: str, enabled: int):
	require_admin()
	doc = frappe.get_doc("Webhook", name)
	doc.check_permission("write")
	doc.enabled = cint(enabled)
	doc.save()
	return True


@frappe.whitelist(methods=["POST"])
def set_social_login_enabled(name: str, enabled: int):
	require_admin()
	doc = frappe.get_doc("Social Login Key", name)
	doc.check_permission("write")
	doc.enable_social_login = cint(enabled)
	doc.save()
	return True
