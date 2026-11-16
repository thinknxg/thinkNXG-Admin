"""Workspace management.

V16 navigation has three parts, each edited the way Core intends:
- Workspace pages: roles, visibility and sequence are saved on the Workspace document
  (Core requires the Workspace Manager role for public pages).
- Module sidebars: arranged as the site-wide Custom Sidebar layer. The browser calls Core's
  own endpoints (frappe.desk.doctype.custom_sidebar.custom_sidebar.get_site_sidebar_layer /
  save_site_sidebar / reset_site_sidebar), which gate on Workspace Manager. The old
  Workspace Sidebar DocType is a read-only archive in this release and is not written to.
- Desktop icons: hidden flag and roles saved on the Desktop Icon document.
"""

import frappe
from frappe import _
from frappe.utils import cint

from thinknxg_admin.api.cache import clear_dashboard_cache
from thinknxg_admin.api.users import _parse_list
from thinknxg_admin.api.utils import doctype_exists, has_field, require_admin


def _is_workspace_manager() -> bool:
	return "Workspace Manager" in frappe.get_roles()


@frappe.whitelist()
def get_overview():
	require_admin()
	workspaces = []
	if doctype_exists("Workspace"):
		fields = ["name", "label", "title", "module", "public", "is_hidden", "for_user", "sequence_id", "icon", "parent_page"]
		fields = [f for f in fields if f in ("name",) or has_field("Workspace", f)]
		if has_field("Workspace", "type"):
			fields.append("type")
		workspaces = frappe.get_all("Workspace", fields=fields, order_by="public desc, sequence_id asc, label asc")
		roles = {}
		for r in frappe.get_all("Has Role", filters={"parenttype": "Workspace"}, fields=["parent", "role"]):
			roles.setdefault(r.parent, []).append(r.role)
		app_of = dict(frappe.get_all("Module Def", fields=["name", "app_name"], as_list=True))
		for w in workspaces:
			w["roles"] = sorted(roles.get(w.name, []))
			w["app"] = app_of.get(w.get("module"))

	modules = frappe.get_all("Module Def", fields=["name", "app_name"], filters={"app_name": ["in", frappe.get_installed_apps()]}, order_by="app_name asc, name asc")
	customized = set()
	if doctype_exists("Custom Sidebar"):
		customized = set(frappe.get_all("Custom Sidebar", filters={"user": ["in", ["", None]]}, pluck="module"))
	for m in modules:
		m["site_layer"] = m.name in customized

	icons = []
	if doctype_exists("Desktop Icon"):
		ifields = [f for f in ("name", "label", "app", "icon", "logo_url", "link_type", "link_to", "parent_icon", "hidden", "standard", "icon_type", "idx") if f == "name" or has_field("Desktop Icon", f)]
		icons = frappe.get_all("Desktop Icon", fields=ifields, order_by="app asc, idx asc, label asc")
		iroles = {}
		for r in frappe.get_all("Has Role", filters={"parenttype": "Desktop Icon"}, fields=["parent", "role"]):
			iroles.setdefault(r.parent, []).append(r.role)
		for i in icons:
			i["roles"] = sorted(iroles.get(i.name, []))

	return {
		"workspaces": workspaces,
		"modules": modules,
		"icons": icons,
		"is_workspace_manager": _is_workspace_manager(),
		"roles": frappe.get_all("Role", filters={"disabled": 0, "name": ["not in", ["Administrator", "Guest", "All"]]}, pluck="name", order_by="name asc"),
	}


@frappe.whitelist(methods=["POST"])
def update_workspace(name: str, values):
	require_admin()
	values = frappe.parse_json(values) or {}
	doc = frappe.get_doc("Workspace", name)
	doc.check_permission("write")
	if "roles" in values:
		doc.set("roles", [{"role": r} for r in _parse_list(values["roles"])])
	for f in ("is_hidden", "sequence_id", "icon"):
		if f in values and doc.meta.has_field(f):
			doc.set(f, values[f])
	doc.save()  # Core's validate enforces Workspace Manager for public pages
	clear_dashboard_cache()
	return True


@frappe.whitelist(methods=["POST"])
def reorder_workspaces(names):
	"""Set sequence_id in the given order (public pages; Workspace Manager required by Core)."""
	require_admin()
	if not _is_workspace_manager():
		frappe.throw(_("You need the Workspace Manager role to reorder public workspaces."), frappe.PermissionError)
	for i, name in enumerate(_parse_list(names)):
		doc = frappe.get_doc("Workspace", name)
		doc.check_permission("write")
		if cint(doc.sequence_id) != i + 1:
			doc.sequence_id = i + 1
			doc.save()
	return True


@frappe.whitelist(methods=["POST"])
def update_desktop_icon(name: str, values):
	require_admin()
	values = frappe.parse_json(values) or {}
	doc = frappe.get_doc("Desktop Icon", name)
	doc.check_permission("write")
	if "hidden" in values:
		doc.hidden = cint(values["hidden"])
	if "roles" in values and doc.meta.has_field("roles"):
		doc.set("roles", [{"role": r} for r in _parse_list(values["roles"])])
	doc.save()
	try:
		from frappe.desk.doctype.desktop_icon.desktop_icon import clear_desktop_icons_cache

		clear_desktop_icons_cache()
	except Exception:
		pass
	return True


@frappe.whitelist(methods=["POST"])
def grant_workspace_manager():
	"""Let an administrator give themselves the Workspace Manager role, which Core requires
	for site-wide navigation changes. Recorded in Version/Permission Log like any role change."""
	require_admin()
	frappe.only_for("System Manager")
	doc = frappe.get_doc("User", frappe.session.user)
	doc.add_roles("Workspace Manager")
	return True
