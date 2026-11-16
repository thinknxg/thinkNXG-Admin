"""Short-lived per-site cache for dashboard panels.

Counts are cheap individually but a dashboard runs many of them; caching each
panel for a short window keeps the Command Center fast on large sites while
staying close to live. Writes to User / Role / Workspace / Company clear it.
"""

import functools
import hashlib
import json

import frappe

PREFIX = "thinknxg_admin:panel:"


def _ttl() -> int:
	try:
		value = frappe.db.get_single_value("thinkNXG Admin Settings", "dashboard_cache_seconds")
		return max(0, int(value if value is not None else 60))
	except Exception:
		return 60


def cached_panel(fn):
	@functools.wraps(fn)
	def wrapper(*args, **kwargs):
		ttl = _ttl()
		if not ttl or str(frappe.form_dict.get("refresh") or "") in ("1", "true"):
			return fn(*args, **kwargs)
		raw = json.dumps([fn.__name__, args, kwargs, frappe.session.user], sort_keys=True, default=str)
		key = PREFIX + hashlib.sha1(raw.encode()).hexdigest()
		hit = frappe.cache.get_value(key)
		if hit is not None:
			return hit
		result = fn(*args, **kwargs)
		frappe.cache.set_value(key, result, expires_in_sec=ttl)
		return result

	return wrapper


def clear_dashboard_cache(doc=None, method=None):
	try:
		frappe.cache.delete_keys(PREFIX)
	except Exception:
		pass
