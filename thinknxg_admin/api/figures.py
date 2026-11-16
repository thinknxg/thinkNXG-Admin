"""Permission-aware figure helpers shared by the ERP and HR command centers.

Every query runs through the core query builder with permissions on, so role
permissions and User Permissions narrow every count and total.
"""

import frappe

from thinknxg_admin.api.utils import doctype_exists


def _quiet(exc):
	"""Drop the message a refused framework permission check queued, so a
	restricted figure does not pop up an error dialog in the browser."""
	if isinstance(exc, frappe.PermissionError):
		frappe.clear_last_message()


class Restricted(Exception):
	"""The user cannot read a source DocType: no number is sent."""


class Missing(Exception):
	"""The source DocType is not installed on this site."""


def _check(*doctypes):
	for dt in doctypes:
		if not doctype_exists(dt):
			raise Missing
		if not frappe.has_permission(dt, "read"):
			raise Restricted
	return True


def _q(doctype, fields, filters, group_by=None, limit=None, order_by=None, ignore_permissions=False):
	"""Aggregate query with the user's permissions applied by the framework.

	``ignore_permissions`` is used only by the HR team view, whose rows are
	already limited on the server to the manager's direct reports.
	"""
	return frappe.qb.get_query(
		doctype, fields=fields, filters=filters, group_by=group_by, limit=limit, order_by=order_by, ignore_permissions=ignore_permissions
	).run(as_dict=True)


def _one(doctype, fields, filters, ignore_permissions=False) -> frappe._dict:
	rows = _q(doctype, fields, filters, ignore_permissions=ignore_permissions)
	return frappe._dict(rows[0] if rows else {})


def _count(doctype, filters, ignore_permissions=False) -> int:
	return int(_one(doctype, [{"COUNT": "*", "as": "n"}], filters, ignore_permissions=ignore_permissions).n or 0)


def _between(a, b):
	return ["between", [a, b]]


def _figure(fn, ctx):
	"""Run one figure; map missing DocTypes and missing permissions to honest states."""
	try:
		out = fn(ctx)
	except Missing:
		return {"value": None}
	except (Restricted, frappe.PermissionError) as exc:
		_quiet(exc)
		return {"restricted": True}
	return out if out is not None else {"value": None}


def _part(fn):
	try:
		return fn()
	except Missing:
		return {"available": False}
	except (Restricted, frappe.PermissionError) as exc:
		_quiet(exc)
		return {"restricted": True}


