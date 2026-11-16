"""Server-side navigation registry.

Each item declares who may see it: ``admin`` (needs an administrator role)
and/or ``doctype`` (read permission checked with frappe.has_permission).
Items the user may not open are never sent to the browser.

``status``
  live     - implemented in the thinkNXG shell
  desk     - opens the native thinkNXG screen (``href``) in the Desk
  planned  - shell shows a clearly labelled roadmap page and a working link
             to the native Desk screen
"""

import frappe

from thinknxg_admin.api.utils import is_admin

NAVIGATION = [
	{
		"section": "Overview",
		"items": [
			{"key": "command-center", "label": "Command Center", "icon": "layout-dashboard", "route": "/admin", "admin": True, "status": "live"},
			{"key": "notifications", "label": "Notifications", "icon": "bell", "route": "/notifications", "status": "live"},
			{
				"key": "my-workspace", "label": "My Workspace", "icon": "user-round", "route": "/my-workspace", "status": "live",
				"description": "Your role-based landing page with shortcuts, tasks and approvals.",
				"capabilities": ["Personal landing page per role", "Pinned shortcuts and favourites", "Assigned tasks and approvals"],
			},
		],
	},
	{
		"section": "Administration",
		"items": [
			{
				"key": "organization", "label": "Organization", "icon": "building-2", "route": "/admin/organization", "doctype": "Company", "admin": True, "status": "live",
				"description": "Companies, branches, departments and the organisation hierarchy.",
				"capabilities": ["Company, branch, department and designation management", "Visual organisation hierarchy", "Cost centers, warehouses, fiscal years, currencies"],
			},
			{
				"key": "users", "label": "Users & Access", "icon": "users", "route": "/admin/users", "doctype": "User",
				"admin": True, "status": "live",
				"description": "Directory, invitations, activation, login history and API access.",
				"capabilities": ["User directory with filters, bulk actions and export", "Invite, enable/disable, reset password", "Login history and per-user activity"],
				"children": [
					{"key": "users-list", "label": "Users", "route": "/admin/users", "doctype": "User"},
					{"key": "invitations", "label": "Invitations", "route": "/admin/users/invitations", "doctype": "User Invitation"},
					{"key": "user-permissions", "label": "User Permissions", "route": "/admin/users/permissions", "doctype": "User Permission"},
				],
			},
			{
				"key": "roles", "label": "Roles & Permissions", "icon": "shield-check", "route": "/admin/roles", "doctype": "Role",
				"admin": True, "status": "live",
				"description": "Roles, role profiles and the DocType permission matrix.",
				"capabilities": ["Role directory, duplicate role, assign users", "Role x DocType permission matrix", "Module and workspace access per role"],
				"children": [
					{"key": "roles-list", "label": "Roles", "route": "/admin/roles", "doctype": "Role"},
					{"key": "role-profiles", "label": "Role Profiles", "route": "/admin/roles/profiles", "doctype": "Role Profile"},
					{"key": "permission-matrix", "label": "Permission Matrix", "route": "/admin/roles/matrix", "admin": True},
				],
			},
			{
				"key": "workspaces", "label": "Workspaces", "icon": "panels-top-left", "route": "/admin/workspaces", "doctype": "Workspace",
				"admin": True, "status": "live",
				"description": "Role workspaces, sidebars and desktop icons, with a visual builder.",
				"capabilities": ["Workspace directory by role", "Workspace Sidebar and Desktop Icon editor", "Default workspace and app per user"],
			},
			{
				"key": "apps", "label": "Apps & Modules", "icon": "blocks", "route": "/admin/apps", "doctype": "Module Def",
				"admin": True, "status": "live",
				"description": "Installed applications, versions, modules and their visibility.",
				"capabilities": ["Installed apps and versions", "Module visibility per role (never uninstalls)", "Desktop icon availability"],
			},
		],
	},
	{
		"section": "Platform",
		"items": [
			{
				"key": "configuration", "label": "Configuration", "icon": "sliders-horizontal", "route": "/admin/configuration",
				"doctype": "System Settings", "admin": True, "status": "live",
				"description": "General, security, email and system settings in one place.",
				"capabilities": ["General, regional and branding settings", "Security: password policy, sessions, 2FA", "Email accounts and templates"],
			},
			{
				"key": "integrations", "label": "Integrations", "icon": "plug", "route": "/admin/integrations", "doctype": "Webhook",
				"admin": True, "status": "live",
				"description": "Webhooks, OAuth clients, connected apps and their logs.",
				"capabilities": ["Webhooks and connected apps", "OAuth clients and API keys (masked)", "Integration request logs"],
			},
			{
				"key": "automation", "label": "Automation", "icon": "workflow", "route": "/admin/automation", "doctype": "Workflow",
				"admin": True, "status": "live",
				"description": "Workflows, notifications, assignment rules and scheduled jobs.",
				"capabilities": ["Workflows and approval states", "Notifications and assignment rules", "Scheduled job overview"],
			},
			{
				"key": "reports", "label": "Reports", "icon": "chart-column", "route": "/reports", "doctype": "Report",
				"status": "live",
				"description": "Report catalogue, saved filters and dashboards.",
				"capabilities": ["Report catalogue by module", "Saved filters and favourites", "Dashboards"],
			},
		],
	},
	{
		"section": "Governance",
		"items": [
			{
				"key": "audit", "label": "Audit & Compliance", "icon": "scroll-text", "route": "/admin/audit", "doctype": "Activity Log",
				"admin": True, "status": "live",
				"description": "Logins, permission changes and configuration history with before/after values.",
				"capabilities": ["Login history and failed attempts", "Permission, role and workspace change trail", "Before/after values with export"],
			},
			{"key": "system-health", "label": "System Health", "icon": "activity", "route": "/admin/system-health", "admin": True, "status": "live"},
			{
				"key": "developer", "label": "Developer Tools", "icon": "terminal", "route": "/admin/developer", "doctype": "DocType",
				"admin": True, "status": "live",
				"description": "DocType explorer, customisations, scheduled jobs and logs.",
				"capabilities": ["DocType explorer, custom fields, property setters", "Server scripts and scheduled jobs", "Error, API and webhook logs"],
			},
		],
	},
]


INTERNAL_KEYS = ("admin", "children", "hr_only", "payroll")


def _allowed(item: dict, admin: bool) -> bool:
	if item.get("admin") and not admin:
		return False
	doctype = item.get("doctype")
	if doctype:
		if not frappe.db.exists("DocType", doctype):
			return False
		if not frappe.has_permission(doctype, "read"):
			return False
	return True


def filter_sections(sections: list[dict], extra=None) -> list[dict]:
	"""Drop every entry the user may not open. ``extra`` adds a center's own rule."""
	admin = is_admin()

	def ok(item):
		return _allowed(item, admin) and (extra is None or extra(item))

	out = []
	for section in sections:
		items = []
		for item in section["items"]:
			if not ok(item):
				continue
			entry = {k: v for k, v in item.items() if k not in INTERNAL_KEYS}
			children = [{k: v for k, v in c.items() if k not in INTERNAL_KEYS} for c in item.get("children", []) if ok(c)]
			if children:
				entry["children"] = children
			items.append(entry)
		if items:
			out.append({"section": section["section"], "items": items})
	return out


def get_navigation() -> list[dict]:
	return filter_sections(NAVIGATION)


def get_app_launcher() -> list[dict]:
	"""Installed apps from their own add_to_apps_screen hooks, honouring each
	app's has_permission check - the same source the V16 apps screen uses."""
	apps = []
	for app in frappe.get_installed_apps():
		for entry in frappe.get_hooks("add_to_apps_screen", app_name=app) or []:
			check = entry.get("has_permission")
			if check:
				try:
					if not frappe.get_attr(check)():
						continue
				except Exception:
					continue
			apps.append({
				"app": app,
				"name": entry.get("name") or app,
				"title": entry.get("title") or app,
				"logo": entry.get("logo"),
				"route": entry.get("route") or "/desk",
			})
	return apps
