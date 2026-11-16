"""Users & Access endpoints.

Every write goes through the User / User Invitation / User Permission documents,
so their own validation, Version tracking and Permission Log keep working.
Safety rails: you cannot disable yourself, and the last enabled System Manager
can neither be disabled nor lose that role.
"""

import json

import frappe
from frappe import _
from frappe.utils import add_days, cint, now_datetime

from thinknxg_admin.api.cache import clear_dashboard_cache
from thinknxg_admin.api.utils import SYSTEM_ACCOUNTS, doctype_exists, has_field, require_admin

HIDDEN_ROLES = ("All", "Guest", "Administrator", "Desk User")
SORTABLE = {"full_name", "name", "last_login", "creation", "enabled", "user_type"}


def _parse_list(value) -> list:
	if value is None or value == "":
		return []
	if isinstance(value, str):
		try:
			parsed = json.loads(value)
			return parsed if isinstance(parsed, list) else [parsed]
		except ValueError:
			return [v.strip() for v in value.split(",") if v.strip()]
	return list(value)


def _enabled_system_managers() -> set[str]:
	return set(
		frappe.db.sql_list(
			"""select distinct u.name from `tabUser` u join `tabHas Role` hr on hr.parent = u.name
			where hr.parenttype = 'User' and hr.role = 'System Manager' and u.enabled = 1
			and u.name not in ('Administrator', 'Guest')"""
		)
	)


def _guard_disable(names: list[str]):
	if frappe.session.user in names:
		frappe.throw(_("You cannot disable your own account."))
	remaining = _enabled_system_managers() - set(names)
	if not remaining and frappe.session.user != "Administrator":
		frappe.throw(_("At least one enabled System Manager must remain."))


def _filters(status=None, user_type=None, role=None, company=None):
	filters = {"name": ["not in", SYSTEM_ACCOUNTS]}
	if user_type:
		filters["user_type"] = user_type
	if status == "Active":
		filters["enabled"] = 1
	elif status == "Disabled":
		filters["enabled"] = 0
	elif status == "Never signed in":
		filters.update({"enabled": 1, "last_login": ["is", "not set"]})
	elif status == "Dormant":
		filters.update({"enabled": 1, "last_login": ["<", add_days(now_datetime(), -90)]})
	names = None
	if role:
		names = set(frappe.get_all("Has Role", filters={"parenttype": "User", "role": role}, pluck="parent"))
	if company and doctype_exists("User Permission"):
		with_company = set(frappe.get_all("User Permission", filters={"allow": "Company", "for_value": company}, pluck="user"))
		names = with_company if names is None else names & with_company
	if names is not None:
		filters["name"] = ["in", list(names) or ["__none__"]]
	return filters


@frappe.whitelist()
def list_users(search: str | None = None, status: str | None = None, user_type: str | None = None, role: str | None = None,
		company: str | None = None, sort: str = "full_name", order: str = "asc", start: int = 0, page_length: int = 25):
	require_admin()
	frappe.has_permission("User", "read", throw=True)
	filters = _filters(status, user_type, role, company)
	or_filters = None
	if search:
		like = f"%{search.strip()}%"
		or_filters = {"name": ["like", like], "full_name": ["like", like], "email": ["like", like]}
	sort = sort if sort in SORTABLE else "full_name"
	order = "desc" if str(order).lower() == "desc" else "asc"
	page_length = max(5, min(cint(page_length) or 25, 200))
	fields = ["name", "full_name", "email", "user_image", "enabled", "user_type", "last_login", "creation"]
	for f in ("default_workspace", "default_app"):
		if has_field("User", f):
			fields.append(f)
	rows = frappe.get_list("User", filters=filters, or_filters=or_filters, fields=fields,
		order_by=f"{sort} {order}, name asc", start=cint(start), page_length=page_length)
	total = len(frappe.get_list("User", filters=filters, or_filters=or_filters, pluck="name", limit_page_length=0))
	_attach_access(rows)
	return {"rows": rows, "total": total, "start": cint(start), "page_length": page_length}


def _attach_access(rows):
	names = [r.name for r in rows]
	if not names:
		return
	roles, companies, profiles = {}, {}, {}
	for hr in frappe.get_all("Has Role", filters={"parenttype": "User", "parent": ["in", names], "role": ["not in", HIDDEN_ROLES]}, fields=["parent", "role"]):
		roles.setdefault(hr.parent, []).append(hr.role)
	if doctype_exists("User Permission"):
		for up in frappe.get_all("User Permission", filters={"user": ["in", names], "allow": "Company"}, fields=["user", "for_value"]):
			companies.setdefault(up.user, []).append(up.for_value)
	if doctype_exists("User Role Profile"):
		for rp in frappe.get_all("User Role Profile", filters={"parenttype": "User", "parent": ["in", names]}, fields=["parent", "role_profile"]):
			profiles.setdefault(rp.parent, []).append(rp.role_profile)
	for r in rows:
		r["roles"] = sorted(roles.get(r.name, []))
		r["companies"] = companies.get(r.name, [])
		r["role_profiles"] = profiles.get(r.name, [])


@frappe.whitelist()
def export_users(search: str | None = None, status: str | None = None, user_type: str | None = None, role: str | None = None, company: str | None = None):
	"""Rows for a CSV export of the current filter. Needs export permission on User."""
	require_admin()
	frappe.has_permission("User", "export", throw=True)
	data = list_users(search=search, status=status, user_type=user_type, role=role, company=company, page_length=200)
	rows, start = list(data["rows"]), 200
	while start < min(data["total"], 5000):
		rows += list_users(search=search, status=status, user_type=user_type, role=role, company=company, start=start, page_length=200)["rows"]
		start += 200
	return rows


@frappe.whitelist()
def get_user(name: str):
	require_admin()
	doc = frappe.get_doc("User", name)
	doc.check_permission("read")
	info = {
		f: doc.get(f)
		for f in ("name", "email", "first_name", "last_name", "full_name", "user_image", "enabled", "user_type",
			"last_login", "last_ip", "creation", "language", "time_zone", "role_profile_name", "module_profile",
			"default_workspace", "default_app", "login_after", "login_before", "restrict_ip", "mobile_no", "desk_theme")
	}
	info["roles"] = sorted(r.role for r in doc.roles if r.role not in HIDDEN_ROLES)
	info["role_profiles"] = [r.role_profile for r in (doc.get("role_profiles") or [])]
	info["blocked_modules"] = [b.module for b in (doc.get("block_modules") or [])]
	info["has_api_key"] = bool(doc.api_key)
	info["api_key"] = doc.api_key  # the key is an identifier; the secret is never returned
	info["is_self"] = doc.name == frappe.session.user

	info["user_permissions"] = []
	if doctype_exists("User Permission"):
		info["user_permissions"] = frappe.get_all("User Permission", filters={"user": name},
			fields=["name", "allow", "for_value", "is_default", "apply_to_all_doctypes", "applicable_for"], order_by="allow asc")
	info["logins"] = []
	if doctype_exists("Activity Log"):
		fields = ["name", "operation", "status", "creation"] + (["ip_address"] if has_field("Activity Log", "ip_address") else [])
		info["logins"] = frappe.get_all("Activity Log", filters={"user": name, "operation": ["in", ["Login", "Logout"]]}, fields=fields, order_by="creation desc", limit=15)
	info["recent_changes"] = frappe.get_all("Version", filters={"owner": name}, fields=["name", "ref_doctype", "docname", "creation"], order_by="creation desc", limit=10)
	info["invitation"] = None
	if doctype_exists("User Invitation"):
		info["invitation"] = frappe.db.get_value("User Invitation", {"email": doc.email}, ["name", "status", "creation"], as_dict=True, order_by="creation desc")
	return info


@frappe.whitelist()
def get_form_options():
	"""Choices for user forms: assignable roles, role/module profiles, workspaces, apps, companies."""
	require_admin()
	roles = frappe.get_all("Role", filters={"disabled": 0, "name": ["not in", HIDDEN_ROLES]}, fields=["name", "desk_access"], order_by="name asc")
	return {
		"roles": roles,
		"role_profiles": frappe.get_all("Role Profile", pluck="name", order_by="name asc") if doctype_exists("Role Profile") else [],
		"module_profiles": frappe.get_all("Module Profile", pluck="name", order_by="name asc") if doctype_exists("Module Profile") else [],
		"workspaces": frappe.get_all("Workspace", filters={"public": 1}, fields=["name", "label"], order_by="label asc") if doctype_exists("Workspace") else [],
		"apps": frappe.get_installed_apps(),
		"companies": frappe.get_list("Company", pluck="name", order_by="name asc") if doctype_exists("Company") else [],
	}


@frappe.whitelist(methods=["POST"])
def create_user(email: str, first_name: str, last_name: str | None = None, user_type: str = "System User",
		roles=None, role_profiles=None, send_welcome_email: int = 1):
	require_admin()
	frappe.has_permission("User", "create", throw=True)
	doc = frappe.get_doc({
		"doctype": "User", "email": email.strip(), "first_name": first_name.strip(), "last_name": (last_name or "").strip(),
		"user_type": user_type, "send_welcome_email": cint(send_welcome_email),
	})
	for rp in _parse_list(role_profiles):
		doc.append("role_profiles", {"role_profile": rp})
	doc.insert()
	if _parse_list(roles):
		doc.add_roles(*_parse_list(roles))
	clear_dashboard_cache()
	return doc.name


@frappe.whitelist(methods=["POST"])
def update_user(name: str, values: str | dict):
	"""Update profile and access fields. `roles` / `role_profiles` replace the current set."""
	require_admin()
	values = frappe.parse_json(values) or {}
	doc = frappe.get_doc("User", name)
	doc.check_permission("write")

	if "enabled" in values and not cint(values["enabled"]) and doc.enabled:
		_guard_disable([name])

	for f in ("first_name", "last_name", "enabled", "user_type", "module_profile", "default_workspace", "default_app", "language", "time_zone", "mobile_no"):
		if f in values and doc.meta.has_field(f):
			doc.set(f, values[f])

	if "role_profiles" in values and doc.meta.has_field("role_profiles"):
		doc.set("role_profiles", [{"role_profile": rp} for rp in _parse_list(values["role_profiles"])])

	if "roles" in values:
		wanted = set(_parse_list(values["roles"]))
		current = {r.role for r in doc.roles}
		if "System Manager" in current and "System Manager" not in wanted:
			_guard_remove_sm([name])
		keep = [r for r in doc.roles if r.role in wanted or r.role in HIDDEN_ROLES]
		doc.set("roles", keep)
		for role in sorted(wanted - current):
			doc.append("roles", {"role": role})

	if "blocked_modules" in values:
		doc.set("block_modules", [{"module": m} for m in _parse_list(values["blocked_modules"])])

	doc.save()
	clear_dashboard_cache()
	return get_user(name)


def _guard_remove_sm(names: list[str]):
	if frappe.session.user in names and frappe.session.user != "Administrator":
		frappe.throw(_("You cannot remove the System Manager role from yourself."))
	if not (_enabled_system_managers() - set(names)):
		frappe.throw(_("At least one enabled System Manager must remain."))


@frappe.whitelist(methods=["POST"])
def bulk_update(names, action: str, role: str | None = None):
	"""Bulk actions from the directory: enable, disable, add_role, remove_role."""
	require_admin()
	names = [n for n in _parse_list(names) if n not in SYSTEM_ACCOUNTS]
	if not names:
		return {"updated": 0}
	if len(names) > 500:
		frappe.throw(_("Select at most 500 users at a time."))
	if action == "disable":
		_guard_disable(names)
	if action == "remove_role" and role == "System Manager":
		_guard_remove_sm(names)
	if action in ("add_role", "remove_role") and not (role and frappe.db.exists("Role", role)):
		frappe.throw(_("Choose a valid role."))

	updated = 0
	for name in names:
		doc = frappe.get_doc("User", name)
		doc.check_permission("write")
		if action == "enable":
			doc.enabled = 1
			doc.save()
		elif action == "disable":
			doc.enabled = 0
			doc.save()
		elif action == "add_role":
			doc.add_roles(role)
		elif action == "remove_role":
			doc.remove_roles(role)
		else:
			frappe.throw(_("Unknown action"))
		updated += 1
	clear_dashboard_cache()
	return {"updated": updated}


@frappe.whitelist(methods=["POST"])
def send_password_reset(name: str):
	require_admin()
	doc = frappe.get_doc("User", name)
	doc.check_permission("write")
	if not doc.enabled:
		frappe.throw(_("Enable the user before sending a reset link."))
	doc.reset_password(send_email=True)
	return True


# -------------------------------------------------------------------- invitations
@frappe.whitelist()
def list_invitations(status: str | None = None):
	require_admin()
	if not doctype_exists("User Invitation"):
		return None
	frappe.has_permission("User Invitation", "read", throw=True)
	filters = {"status": status} if status else {}
	rows = frappe.get_list("User Invitation", filters=filters,
		fields=["name", "email", "status", "invited_by", "email_sent_at", "accepted_at", "creation", "app_name"],
		order_by="creation desc", limit_page_length=200)
	names = [r.name for r in rows]
	roles = {}
	for r in frappe.get_all("User Role", filters={"parenttype": "User Invitation", "parent": ["in", names or ["__none__"]]}, fields=["parent", "role"]):
		roles.setdefault(r.parent, []).append(r.role)
	for r in rows:
		r["roles"] = roles.get(r.name, [])
	return rows


@frappe.whitelist(methods=["POST"])
def invite_users(emails, roles=None, redirect_to_path: str = "/desk"):
	"""One invitation per address, through Core's User Invitation (which sends the email)."""
	require_admin()
	frappe.has_permission("User Invitation", "create", throw=True)
	results = []
	for email in _parse_list(emails)[:100]:
		email = email.strip()
		if not email:
			continue
		try:
			doc = frappe.get_doc({
				"doctype": "User Invitation", "email": email, "app_name": "frappe",
				"redirect_to_path": redirect_to_path or "/desk",
				"roles": [{"role": r} for r in _parse_list(roles)],
			})
			doc.insert()
			results.append({"email": email, "ok": True, "name": doc.name})
		except Exception as e:
			frappe.clear_last_message()
			results.append({"email": email, "ok": False, "error": frappe.utils.strip_html(str(e))[:200]})
	clear_dashboard_cache()
	return results


@frappe.whitelist(methods=["POST"])
def cancel_invitation(name: str):
	require_admin()
	doc = frappe.get_doc("User Invitation", name)
	doc.check_permission("write")
	doc.cancel_invite()
	clear_dashboard_cache()
	return True


# -------------------------------------------------------------------- user permissions
@frappe.whitelist()
def list_user_permissions(user: str | None = None, allow: str | None = None, start: int = 0, page_length: int = 50):
	require_admin()
	frappe.has_permission("User Permission", "read", throw=True)
	filters = {}
	if user:
		filters["user"] = user
	if allow:
		filters["allow"] = allow
	rows = frappe.get_list("User Permission", filters=filters,
		fields=["name", "user", "allow", "for_value", "is_default", "apply_to_all_doctypes", "applicable_for", "creation"],
		order_by="user asc, allow asc", start=cint(start), page_length=max(10, min(cint(page_length) or 50, 200)))
	total = frappe.db.count("User Permission", filters)
	allows = frappe.db.sql_list("select distinct allow from `tabUser Permission` order by allow")
	return {"rows": rows, "total": total, "allow_options": allows}


@frappe.whitelist(methods=["POST"])
def add_user_permission(user: str, allow: str, for_value: str, is_default: int = 0, apply_to_all_doctypes: int = 1, applicable_for: str | None = None):
	require_admin()
	doc = frappe.get_doc({
		"doctype": "User Permission", "user": user, "allow": allow, "for_value": for_value,
		"is_default": cint(is_default), "apply_to_all_doctypes": cint(apply_to_all_doctypes),
		"applicable_for": None if cint(apply_to_all_doctypes) else applicable_for,
	})
	doc.insert()
	return doc.name


@frappe.whitelist(methods=["POST"])
def delete_user_permission(name: str):
	require_admin()
	frappe.delete_doc("User Permission", name)
	return True
