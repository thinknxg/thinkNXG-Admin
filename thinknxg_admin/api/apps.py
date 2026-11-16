"""Applications & modules.

Distinguishes four things the UI must never blur:
- installation  (bench operation - shown, never changed here)
- module visibility (Module Profile / per-user Block Module - native Desk mechanism)
- role access   (DocType permissions - see Roles & Permissions)
- launcher icon (Desktop Icon hidden flag)
"""

import frappe

from thinknxg_admin.api.users import _parse_list
from thinknxg_admin.api.utils import doctype_exists, require_admin


@frappe.whitelist()
def get_apps():
	require_admin()
	try:
		from frappe.utils.change_log import get_versions

		versions = get_versions()
	except Exception:
		versions = {}
	installed = frappe.get_installed_apps()
	installed_meta = {}
	if doctype_exists("Installed Application"):
		for row in frappe.get_all("Installed Application", fields=["app_name", "app_version", "git_branch"], filters={"parenttype": "Installed Applications"}):
			installed_meta[row.app_name] = row

	modules = frappe.get_all("Module Def", fields=["name", "app_name", "custom"], filters={"app_name": ["in", installed]}, order_by="name asc")
	doctypes = dict(frappe.db.sql("select module, count(*) from `tabDocType` where istable = 0 group by module"))
	blocked = dict(frappe.db.sql("""select bm.module, count(distinct bm.parent) from `tabBlock Module` bm
		join `tabUser` u on u.name = bm.parent where bm.parenttype = 'User' and u.enabled = 1 group by bm.module"""))
	profile_blocked = {}
	if doctype_exists("Module Profile"):
		for module, profile in frappe.db.sql("select module, parent from `tabBlock Module` where parenttype = 'Module Profile'"):
			profile_blocked.setdefault(module, []).append(profile)

	icons = {}
	if doctype_exists("Desktop Icon"):
		for i in frappe.get_all("Desktop Icon", fields=["name", "label", "app", "hidden"]):
			icons.setdefault(i.app, []).append(i)

	apps = []
	for app in installed:
		hooks = frappe.get_hooks(app_name=app)
		v = versions.get(app, {})
		meta = installed_meta.get(app) or {}
		mods = [m for m in modules if m.app_name == app]
		for m in mods:
			m["doctypes"] = doctypes.get(m.name, 0)
			m["blocked_users"] = blocked.get(m.name, 0)
			m["blocked_in_profiles"] = profile_blocked.get(m.name, [])
		app_icons = icons.get(app, [])
		apps.append({
			"name": app,
			"title": (hooks.get("app_title") or [app])[0],
			"publisher": (hooks.get("app_publisher") or [""])[0],
			"description": (hooks.get("app_description") or [""])[0],
			"version": v.get("version") or meta.get("app_version"),
			"branch": v.get("branch") or meta.get("git_branch"),
			"logo": v.get("logo") or (hooks.get("app_logo_url") or [None])[0],
			"modules": mods,
			"icons": {"total": len(app_icons), "hidden": sum(1 for i in app_icons if i.hidden)},
		})
	return {"apps": apps, "module_profiles": list_module_profiles()}


def list_module_profiles():
	if not doctype_exists("Module Profile"):
		return None
	profiles = frappe.get_all("Module Profile", fields=["name"], order_by="name asc")
	blocked = {}
	for module, parent in frappe.db.sql("select module, parent from `tabBlock Module` where parenttype = 'Module Profile'"):
		blocked.setdefault(parent, []).append(module)
	users = dict(frappe.db.sql("select module_profile, count(*) from `tabUser` where module_profile is not null and module_profile != '' and enabled = 1 group by module_profile"))
	for p in profiles:
		p["blocked_modules"] = sorted(blocked.get(p.name, []))
		p["users"] = users.get(p.name, 0)
	return profiles


@frappe.whitelist(methods=["POST"])
def save_module_profile(name: str, blocked_modules, create: int = 0):
	"""Module Profiles hide modules for the users assigned to them (Core syncs on save)."""
	require_admin()
	rows = [{"module": m} for m in _parse_list(blocked_modules)]
	if int(create or 0):
		frappe.has_permission("Module Profile", "create", throw=True)
		doc = frappe.get_doc({"doctype": "Module Profile", "module_profile_name": name.strip(), "block_modules": rows})
		doc.insert()
	else:
		doc = frappe.get_doc("Module Profile", name)
		doc.check_permission("write")
		doc.set("block_modules", rows)
		doc.save()
	return doc.name
