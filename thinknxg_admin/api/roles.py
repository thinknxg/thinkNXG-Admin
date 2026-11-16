"""Roles, role profiles and permission summaries.

Editing DocType permission rules is done by the browser through Core's own
Role Permission Manager methods (frappe.core.page.permission_manager.*), which
enforce System Manager and keep DocPerm / Custom DocPerm consistent. This
module adds the role-centric reads and the role/profile writes around them.
"""

import frappe
from frappe import _
from frappe.permissions import get_all_perms, setup_custom_perms
from frappe.utils import cint

from thinknxg_admin.api.cache import clear_dashboard_cache
from thinknxg_admin.api.users import HIDDEN_ROLES, _enabled_system_managers, _parse_list
from thinknxg_admin.api.utils import doctype_exists, require_admin

PTYPES = ["read", "write", "create", "delete", "submit", "cancel", "amend", "report", "export", "import", "share", "print", "email"]


@frappe.whitelist()
def list_roles(search: str | None = None, include_disabled: int = 1):
	require_admin()
	filters = {"name": ["not in", ["Administrator", "Guest", "All"]]}
	if not cint(include_disabled):
		filters["disabled"] = 0
	if search:
		filters["name"] = ["like", f"%{search}%"]
	roles = frappe.get_all("Role", filters=filters, fields=["name", "desk_access", "disabled", "is_custom", "two_factor_auth", "home_page", "modified"], order_by="name asc")
	users = dict(frappe.db.sql("""select hr.role, count(distinct hr.parent) from `tabHas Role` hr join `tabUser` u on u.name = hr.parent
		where hr.parenttype = 'User' and u.enabled = 1 and u.name not in ('Administrator','Guest') group by hr.role"""))
	rules = {}
	for dt in ("DocPerm", "Custom DocPerm"):
		for role, parent in frappe.db.sql(f"select role, parent from `tab{dt}`"):
			rules.setdefault(role, set()).add(parent)
	workspaces = dict(frappe.db.sql("select role, count(*) from `tabHas Role` where parenttype = 'Workspace' group by role")) if doctype_exists("Workspace") else {}
	for r in roles:
		r["users"] = users.get(r.name, 0)
		r["doctypes"] = len(rules.get(r.name, ()))
		r["workspaces"] = workspaces.get(r.name, 0)
	return roles


@frappe.whitelist()
def get_role(name: str):
	require_admin()
	doc = frappe.get_doc("Role", name)
	users = frappe.db.sql("""select u.name, u.full_name, u.enabled, u.user_image, u.last_login from `tabUser` u
		join `tabHas Role` hr on hr.parent = u.name where hr.parenttype = 'User' and hr.role = %s
		and u.name not in ('Administrator','Guest') order by u.enabled desc, u.full_name asc""", name, as_dict=True)
	perms = {}
	for p in get_all_perms(name):
		if cint(p.permlevel) != 0:
			continue
		row = perms.setdefault(p.parent, {"doctype": p.parent, **{pt: 0 for pt in PTYPES}, "if_owner": 0})
		for pt in PTYPES:
			row[pt] = row[pt] or cint(p.get(pt))
		row["if_owner"] = row["if_owner"] or cint(p.get("if_owner"))
	module_of = dict(frappe.get_all("DocType", filters={"name": ["in", list(perms) or ["__none__"]]}, fields=["name", "module"], as_list=True))
	for row in perms.values():
		row["module"] = module_of.get(row["doctype"])
	return {
		"role": {f: doc.get(f) for f in ("name", "role_name", "desk_access", "disabled", "is_custom", "two_factor_auth", "home_page")},
		"users": users,
		"permissions": sorted(perms.values(), key=lambda r: ((r["module"] or ""), r["doctype"])),
		"workspaces": frappe.get_all("Has Role", filters={"parenttype": "Workspace", "role": name}, pluck="parent") if doctype_exists("Workspace") else [],
		"role_profiles": frappe.get_all("Has Role", filters={"parenttype": "Role Profile", "role": name}, pluck="parent"),
		"standard": name in ("System Manager", "Administrator", "Guest", "All", "Desk User"),
	}


@frappe.whitelist(methods=["POST"])
def create_role(role_name: str, desk_access: int = 1, two_factor_auth: int = 0):
	require_admin()
	frappe.has_permission("Role", "create", throw=True)
	doc = frappe.get_doc({"doctype": "Role", "role_name": role_name.strip(), "desk_access": cint(desk_access), "two_factor_auth": cint(two_factor_auth)})
	doc.insert()
	clear_dashboard_cache()
	return doc.name


@frappe.whitelist(methods=["POST"])
def update_role(name: str, values):
	require_admin()
	values = frappe.parse_json(values) or {}
	doc = frappe.get_doc("Role", name)
	doc.check_permission("write")
	if cint(values.get("disabled")) and name == "System Manager":
		frappe.throw(_("System Manager cannot be disabled."))
	for f in ("desk_access", "disabled", "two_factor_auth", "home_page"):
		if f in values:
			doc.set(f, values[f])
	doc.save()
	clear_dashboard_cache()
	return get_role(name)


@frappe.whitelist(methods=["POST"])
def duplicate_role(source: str, new_name: str, copy_users: int = 0):
	"""New role with the same DocType permission rules (all perm levels) as `source`."""
	require_admin()
	frappe.only_for("System Manager")
	if frappe.db.exists("Role", new_name):
		frappe.throw(_("Role {0} already exists.").format(new_name))
	src = frappe.get_doc("Role", source)
	new = frappe.get_doc({"doctype": "Role", "role_name": new_name.strip(), "desk_access": src.desk_access, "two_factor_auth": src.two_factor_auth, "home_page": src.home_page})
	new.insert()

	copied = 0
	for p in get_all_perms(source):
		setup_custom_perms(p.parent)
		exists = frappe.db.exists("Custom DocPerm", {"parent": p.parent, "role": new.name, "permlevel": p.permlevel, "if_owner": p.if_owner})
		if exists:
			continue
		row = frappe.new_doc("Custom DocPerm")
		row.update({k: p.get(k) for k in PTYPES + ["permlevel", "if_owner", "select", "mask"] if k in p})
		row.update({"parent": p.parent, "parenttype": "DocType", "parentfield": "permissions", "role": new.name})
		row.insert(ignore_permissions=True)
		copied += 1
		frappe.clear_cache(doctype=p.parent)

	users = 0
	if cint(copy_users):
		for user in frappe.get_all("Has Role", filters={"parenttype": "User", "role": source}, pluck="parent"):
			if user in ("Administrator", "Guest"):
				continue
			frappe.get_doc("User", user).add_roles(new.name)
			users += 1
	clear_dashboard_cache()
	return {"name": new.name, "rules": copied, "users": users}


@frappe.whitelist(methods=["POST"])
def set_role_users(role: str, add=None, remove=None):
	require_admin()
	if not frappe.db.exists("Role", role):
		frappe.throw(_("Role not found."))
	remove = [u for u in _parse_list(remove) if u not in ("Administrator", "Guest")]
	if role == "System Manager" and remove:
		if frappe.session.user in remove and frappe.session.user != "Administrator":
			frappe.throw(_("You cannot remove the System Manager role from yourself."))
		if not (_enabled_system_managers() - set(remove)):
			frappe.throw(_("At least one enabled System Manager must remain."))
	for user in _parse_list(add):
		doc = frappe.get_doc("User", user)
		doc.check_permission("write")
		doc.add_roles(role)
	for user in remove:
		doc = frappe.get_doc("User", user)
		doc.check_permission("write")
		doc.remove_roles(role)
	clear_dashboard_cache()
	return get_role(role)


@frappe.whitelist()
def get_permission_overview(doctype: str):
	"""Roles x permission types for one DocType at perm level 0, merged from the rules
	Core will actually apply (Custom DocPerm when present, else DocPerm)."""
	require_admin()
	if not frappe.db.exists("DocType", doctype):
		frappe.throw(_("DocType not found."))
	table = "Custom DocPerm" if frappe.db.exists("Custom DocPerm", {"parent": doctype}) else "DocPerm"
	rows = frappe.get_all(table, filters={"parent": doctype}, fields=["*"], order_by="permlevel asc, role asc")
	meta = frappe.get_meta(doctype)
	return {"rows": rows, "customized": table == "Custom DocPerm", "is_submittable": meta.is_submittable, "module": meta.module}


# -------------------------------------------------------------------- role profiles
@frappe.whitelist()
def list_role_profiles():
	require_admin()
	if not doctype_exists("Role Profile"):
		return None
	profiles = frappe.get_all("Role Profile", fields=["name", "modified"], order_by="name asc")
	roles = {}
	for r in frappe.get_all("Has Role", filters={"parenttype": "Role Profile"}, fields=["parent", "role"]):
		roles.setdefault(r.parent, []).append(r.role)
	users = {}
	if doctype_exists("User Role Profile"):
		users = dict(frappe.db.sql("select role_profile, count(distinct parent) from `tabUser Role Profile` where parenttype = 'User' group by role_profile"))
	for p in profiles:
		p["roles"] = sorted(roles.get(p.name, []))
		p["users"] = users.get(p.name, 0)
	return profiles


@frappe.whitelist(methods=["POST"])
def save_role_profile(name: str, roles, create: int = 0):
	"""Create or update a Role Profile. Core propagates role changes to its users on save."""
	require_admin()
	roles = [r for r in _parse_list(roles) if r not in HIDDEN_ROLES]
	if cint(create):
		frappe.has_permission("Role Profile", "create", throw=True)
		doc = frappe.get_doc({"doctype": "Role Profile", "role_profile": name.strip(), "roles": [{"role": r} for r in roles]})
		doc.insert()
	else:
		doc = frappe.get_doc("Role Profile", name)
		doc.check_permission("write")
		doc.set("roles", [{"role": r} for r in roles])
		doc.save()
	clear_dashboard_cache()
	return doc.name
