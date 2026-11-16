"""Shared helpers for thinkNXG Admin APIs.

Security model: every admin endpoint calls ``require_admin()`` on the server.
The browser only renders what the server already decided the user may see.
Frappe's permission engine stays the single authority.
"""

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import now_datetime

SYSTEM_ACCOUNTS = ("Administrator", "Guest")
BASE_ADMIN_ROLES = ("System Manager",)


def admin_roles() -> set[str]:
	"""System Manager plus any roles mapped in thinkNXG Admin Settings."""
	roles = set(BASE_ADMIN_ROLES)
	try:
		if frappe.db.exists("DocType", "thinkNXG Admin Role"):
			roles.update(
				frappe.get_all(
					"thinkNXG Admin Role",
					filters={"parent": "thinkNXG Admin Settings", "parenttype": "thinkNXG Admin Settings", "parentfield": "admin_roles"},
					pluck="role",
				)
			)
	except Exception:
		pass
	return {r for r in roles if r}


def is_admin(user: str | None = None) -> bool:
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	if user == "Guest":
		return False
	return bool(set(frappe.get_roles(user)) & admin_roles())


def require_admin():
	if not is_admin():
		frappe.throw(_("You need an administrator role to use the Command Center."), frappe.PermissionError)


def require_login():
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in."), frappe.AuthenticationError)


def doctype_exists(doctype: str) -> bool:
	return bool(frappe.db.exists("DocType", doctype))


def has_field(doctype: str, fieldname: str) -> bool:
	try:
		return bool(frappe.get_meta(doctype).has_field(fieldname))
	except Exception:
		return False


def safe_count(doctype: str, filters=None):
	"""Row count, or None when the DocType is not installed on this site.

	None renders as "Not available" in the UI - figures are never estimated.
	"""
	if not doctype_exists(doctype):
		return None
	try:
		return frappe.db.count(doctype, filters or {})
	except Exception:
		return None


def period(days):
	"""Return (prev_start, start, end) for a rolling window of ``days`` (1-365)."""
	try:
		days = int(days or 30)
	except (TypeError, ValueError):
		days = 30
	days = max(1, min(days, 365))
	end = now_datetime()
	start = end - timedelta(days=days)
	return start - timedelta(days=days), start, end


def slug(doctype: str) -> str:
	return doctype.lower().replace(" ", "-")


def desk_route(doctype: str | None, name: str | None = None) -> str:
	"""Internal thinkNXG address for a DocType list or document (kept under its
	old name so every caller moved to internal routes at once)."""
	from thinknxg_admin.api.routes import internal_route

	return internal_route(doctype, name)


def delta(current, previous):
	"""Percent change, or None when it would be meaningless."""
	if current is None or previous in (None, 0):
		return None
	return round((current - previous) * 100.0 / previous, 1)
