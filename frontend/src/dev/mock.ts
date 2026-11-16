// LOCAL PREVIEW ONLY (VITE_MOCK=1). Sample responses so the UI can be viewed
// without a site. Never bundled into production builds; the app shows a
// "Preview build with sample data" banner whenever this module is active.

const now = Date.now();
const local = (d: Date) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().replace("T", " ").slice(0, 19);
const ago = (mins: number) => local(new Date(now - mins * 60000));
const days = (n: number) =>
	Array.from({ length: n + 1 }, (_, i) => {
		const d = new Date(now - (n - i) * 86400000);
		const weekend = [5, 6].includes(d.getDay());
		const users = weekend ? 6 + (i % 3) : 28 + Math.round(8 * Math.sin(i / 2.3)) + (i % 5);
		return { date: d.toISOString().slice(0, 10), users, logins: users + Math.round(users * 0.6) };
	});

const nav = [
	{ section: "Overview", items: [
		{ key: "command-center", label: "Command Center", icon: "layout-dashboard", route: "/", status: "live" },
		{ key: "notifications", label: "Notifications", icon: "bell", route: "/notifications", status: "live" },
		{ key: "my-workspace", label: "My Workspace", icon: "user-round", route: "/my-workspace", desk: "/desk", status: "planned", phase: 6, description: "Your role-based landing page with shortcuts, tasks and approvals.", capabilities: ["Personal landing page per role", "Pinned shortcuts and favourites", "Assigned tasks and approvals"] },
	] },
	{ section: "Administration", items: [
		{ key: "organization", label: "Organization", icon: "building-2", route: "/organization", desk: "/desk/company", status: "live", description: "Companies, branches, departments and the organisation hierarchy.", capabilities: ["Company, branch, department and designation management", "Visual organisation hierarchy"] },
		{ key: "users", status: "live", label: "Users & Access", icon: "users", route: "/users", desk: "/desk/user", phase: 6, description: "Directory, invitations, activation, login history and API access.", capabilities: ["User directory with filters, bulk actions and export"], children: [
			{ key: "users-list", label: "Users", route: "/users", desk: "/desk/user" },
			{ key: "invitations", label: "Invitations", route: "/users/invitations", desk: "/desk/user-invitation" },
			{ key: "user-permissions", label: "User Permissions", route: "/users/permissions", desk: "/desk/user-permission" },
		] },
		{ key: "roles", status: "live", label: "Roles & Permissions", icon: "shield-check", route: "/roles", desk: "/desk/role", children: [{ key: "roles-list", label: "Roles", route: "/roles" }, { key: "role-profiles", label: "Role Profiles", route: "/roles/profiles" }, { key: "permission-matrix", label: "Permission Matrix", route: "/roles/matrix" }], phase: 6, description: "Roles, role profiles and the DocType permission matrix.", capabilities: ["Role x DocType permission matrix"] },
		{ key: "workspaces", status: "live", label: "Workspaces", icon: "panels-top-left", route: "/workspaces", desk: "/desk/workspace", phase: 6, description: "Role workspaces, sidebars and desktop icons.", capabilities: [] },
		{ key: "apps", status: "live", label: "Apps & Modules", icon: "blocks", route: "/apps", desk: "/desk/module-def", phase: 6, description: "Installed applications and modules.", capabilities: [] },
	] },
	{ section: "Platform", items: [
		{ key: "configuration", label: "Configuration", icon: "sliders-horizontal", route: "/configuration", desk: "/desk/system-settings", status: "planned", phase: 6 },
		{ key: "integrations", status: "live", label: "Integrations", icon: "plug", route: "/integrations", desk: "/desk/webhook" },
		{ key: "automation", status: "live", label: "Automation", icon: "workflow", route: "/automation", desk: "/desk/workflow" },
		{ key: "reports", label: "Reports", icon: "chart-column", route: "/reports", desk: "/desk/report", status: "planned", phase: 7 },
	] },
	{ section: "Governance", items: [
		{ key: "audit", status: "live", label: "Audit & Compliance", icon: "scroll-text", route: "/audit", desk: "/desk/activity-log" },
		{ key: "system-health", label: "System Health", icon: "activity", route: "/system-health", status: "live" },
		{ key: "developer", status: "live", label: "Developer Tools", icon: "terminal", route: "/developer", desk: "/desk/doctype" },
	] },
];

const responses: Record<string, (args: any) => any> = {
	"thinknxg_admin.api.boot.get_boot": () => ({
		user: { name: "admin@example.com", full_name: "Sample Admin", email: "admin@example.com", theme: "Light", roles: ["System Manager"], is_admin: true },
		brand: { name: "thinkNXG", product: "thinkNXG ERP", logo: "/assets/frappe/images/thinkNXG-favicon.png", docs_url: "https://docs.thinknxg.com/thinknxgerp", support_url: "https://thinknxg.com/thinkdesk", whats_new_url: "https://docs.thinknxg.com/thinknxgerp" },
		version: "16.0.0",
		navigation: nav,
		apps: [
			{ app: "frappe", name: "frappe", title: "thinkNXG Framework", route: "/desk/build" },
			{ app: "erpnext", name: "erpnext", title: "thinkNXG ERP", route: "/desk/home" },
			{ app: "hrms", name: "hrms", title: "thinkNXG HR", route: "/app/hr-setup" },
			{ app: "thinknxg_admin", name: "thinknxg_admin", title: "Command Center", route: "/thinknxg" },
		],
		quick_create: [{ doctype: "User", icon: "user", route: "/desk/user/new" }, { doctype: "Role", icon: "role", route: "/desk/role/new" }, { doctype: "Company", icon: "building-2", route: "/desk/company/new" }, { doctype: "Workspace", icon: "panels-top-left", route: "/desk/workspace/new" }],
		companies: [{ name: "Sample Trading LLC", abbr: "STL" }, { name: "Sample Services SPC", abbr: "SSS" }],
		default_company: "Sample Trading LLC",
		show_classic_desk_link: true,
		site: "preview.local",
		server_now: local(new Date()),
	}),
	"thinknxg_admin.api.dashboard.get_kpis": (a) => ({
		total_users: { value: 148, secondary: 6, delta: 50 },
		active_users: { value: 97, delta: 8.9 },
		companies: { value: 2 },
		workspaces: { value: 31 },
		installed_apps: { value: 4, items: ["frappe", "erpnext", "hrms", "thinknxg_admin"] },
		modules: { value: 38 },
		pending_approvals: { value: 12, secondary: 3 },
		background_jobs: { value: 4, secondary: 1 },
		login_series: days(Number(a.days || 30)),
	}),
	"thinknxg_admin.api.dashboard.get_activity": () => ({
		successful_logins: 1286, failed_logins: 14, config_changes: 37, errors: 9, scheduled_job_failures: 0,
		logins: [
			{ name: "1", user: "noor@example.com", full_name: "Noor Al Balushi", operation: "Login", status: "Success", creation: ago(4), ip_address: "10.0.4.21" },
			{ name: "2", user: "rahul@example.com", full_name: "Rahul Menon", operation: "Login", status: "Success", creation: ago(11), ip_address: "10.0.4.37" },
			{ name: "3", user: "fatma@example.com", full_name: "Fatma Al Hinai", operation: "Logout", status: "Success", creation: ago(26), ip_address: "10.0.4.12" },
			{ name: "4", user: "ops@example.com", full_name: "Ops Desk", operation: "Login", status: "Failed", creation: ago(40), ip_address: "10.0.9.3" },
			{ name: "5", user: "omar@example.com", full_name: "Omar Al Said", operation: "Login", status: "Success", creation: ago(65), ip_address: "10.0.4.50" },
		],
	}),
	"thinknxg_admin.api.dashboard.get_access_overview": () => ({
		active: 148, disabled: 11, website: 26, never_logged_in: 7, dormant_90d: 9, pending_invitations: 3, failed_logins_24h: 2, total_roles: 64,
		role_distribution: [{ role: "Employee", users: 131 }, { role: "Sales User", users: 34 }, { role: "Accounts User", users: 22 }, { role: "HR User", users: 12 }, { role: "Stock User", users: 11 }, { role: "Purchase User", users: 9 }],
		recent_permission_changes: [
			{ id: "p1", actor_name: "Sample Admin", action: "Added permission on Sales Invoice", doctype: "Custom DocPerm", docname: "Accounts User", timestamp: ago(90), route: "/desk/permission-log" },
			{ id: "p2", actor_name: "Noor Al Balushi", action: "Roles added", doctype: "User", docname: "rahul@example.com", timestamp: ago(260), route: "/desk/user/rahul@example.com" },
			{ id: "p3", actor_name: "Sample Admin", action: "Removed permission on Payroll Entry", doctype: "Custom DocPerm", docname: "HR User", timestamp: ago(1500), route: "/desk/permission-log" },
		],
	}),
	"thinknxg_admin.api.dashboard.get_organization_overview": () => ({
		business_units_configured: false,
		items: [
			{ doctype: "Company", label: "Companies", value: 2, icon: "building-2", route: "/desk/company" },
			{ doctype: "Branch", label: "Branches", value: 5, icon: "git-branch", route: "/desk/branch" },
			{ doctype: "Department", label: "Departments", value: 14, icon: "network", route: "/desk/department" },
			{ doctype: "Designation", label: "Designations", value: 27, icon: "id-card", route: "/desk/designation" },
			{ doctype: "Cost Center", label: "Cost Centers", value: 9, icon: "target", route: "/desk/cost-center" },
			{ doctype: "Warehouse", label: "Warehouses", value: 6, icon: "warehouse", route: "/desk/warehouse" },
			{ doctype: "Employee", label: "Employees", value: 131, icon: "contact", route: "/desk/employee" },
			{ doctype: "Fiscal Year", label: "Fiscal Years", value: 3, icon: "calendar-range", route: "/desk/fiscal-year" },
		],
	}),
	"thinknxg_admin.api.dashboard.get_pending_actions": () => ({
		approval_count: 12, todo_count: 3,
		alerts: [{ kind: "alert", severity: "critical", title: "9 unseen error logs", subtitle: "Server exceptions recorded on this site", route: "/desk/error-log?seen=0" }, { kind: "alert", severity: "serious", title: "1 failed background job", subtitle: "Inspect and retry from RQ Job", route: "/desk/rq-job?status=failed" }],
		actions: [
			{ kind: "approval", title: "Leave Application HR-LAP-2026-00412", subtitle: "Awaiting action · Pending Approval", creation: ago(35), route: "#" },
			{ kind: "approval", title: "Purchase Order PUR-ORD-2026-00188", subtitle: "Awaiting action · To Approve", creation: ago(120), route: "#" },
			{ kind: "task", title: "Review new joiner access for Finance", subtitle: "Assigned to you · High priority", creation: ago(300), route: "#" },
		],
	}),
	"thinknxg_admin.api.dashboard.get_admin_timeline": () => [
		{ id: "t1", actor_name: "Sample Admin", action: "Changed Enabled", change: { field: "enabled", old: "1", new: "0" }, doctype: "User", docname: "temp.contractor@example.com", timestamp: ago(18), status: "Success", route: "#" },
		{ id: "t2", actor_name: "Noor Al Balushi", action: "Roles added", doctype: "User", docname: "rahul@example.com", timestamp: ago(260), status: "Success", route: "#" },
		{ id: "t3", actor_name: "Ops Desk", action: "Failed login attempt", doctype: "Activity Log", docname: "ops@example.com", ip: "10.0.9.3", timestamp: ago(40), status: "Failed", route: "#" },
		{ id: "t4", actor_name: "Sample Admin", action: "Changed Session Expiry", change: { field: "session_expiry", old: "06:00", new: "04:00" }, doctype: "System Settings", docname: "System Settings", timestamp: ago(800), status: "Success", route: "#" },
		{ id: "t5", actor_name: "Rahul Menon", action: "Rows added to links", doctype: "Workspace", docname: "Selling", timestamp: ago(1400), status: "Success", route: "#" },
	],
	"thinknxg_admin.api.health.get_live_health": () => ({
		status: "warning", summary: "Needs attention", healthy: 7, total: 8, checked_at: ago(0),
		checks: [
			{ key: "app", label: "Application", status: "ok", detail: "thinkNXG Framework 16.56.0" },
			{ key: "database", label: "Database", status: "ok", detail: "mariadb 11.4.4", latency_ms: 1.8 },
			{ key: "redis", label: "Redis cache", status: "ok", detail: "Redis cache reachable", latency_ms: 0.6 },
			{ key: "queues", label: "Queues", status: "ok", detail: "4 queued · 1 failed", queued: 4, failed: 1, queues: [{ name: "default", queued: 3, running: 1, failed: 1 }, { name: "short", queued: 1, running: 0, failed: 0 }, { name: "long", queued: 0, running: 1, failed: 0 }] },
			{ key: "workers", label: "Workers", status: "ok", detail: "3 workers · 2 busy" },
			{ key: "scheduler", label: "Scheduler", status: "ok", detail: "Running" },
			{ key: "storage", label: "Storage", status: "ok", detail: "41.2% of disk used", used_pct: 41.2, free_bytes: 118e9, total_bytes: 200e9 },
			{ key: "errors", label: "Application errors", status: "warning", detail: "9 in the last 24 h", count: 9 },
		],
	}),
	"thinknxg_admin.api.notifications.get_notifications": () => ({
		unread: 2, open_todos: 3,
		items: [
			{ name: "n1", subject: "Rahul Menon assigned you a task: Review new joiner access for Finance", from_name: "Rahul Menon", read: 0, creation: ago(30) },
			{ name: "n2", subject: "Leave Application HR-LAP-2026-00412 is awaiting your approval", from_name: "Fatma Al Hinai", read: 0, creation: ago(36) },
			{ name: "n3", subject: "Noor Al Balushi mentioned you on Purchase Order PUR-ORD-2026-00188", from_name: "Noor Al Balushi", read: 1, creation: ago(400) },
		],
	}),
	"thinknxg_admin.api.search.search": (a) => [
		{ type: "DocType", label: "Sales Invoice", description: "Accounts", route: "/desk/sales-invoice", icon: "file-text" },
		{ type: "User", label: "Rahul Menon", description: "rahul@example.com", route: "/desk/user/rahul", icon: "user" },
	].filter((r) => r.label.toLowerCase().includes(String(a.query || "").toLowerCase().slice(0, 2))),
};


const people = [
	["Noor Al Balushi", "noor@example.com", ["System Manager", "HR Manager"], 4, 1],
	["Rahul Menon", "rahul@example.com", ["Sales Manager", "Sales User"], 11, 1],
	["Fatma Al Hinai", "fatma@example.com", ["Accounts Manager", "Accounts User", "Auditor"], 26, 1],
	["Omar Al Said", "omar@example.com", ["Stock User", "Purchase User"], 65, 1],
	["Priya Nair", "priya@example.com", ["HR User", "Employee"], 900, 1],
	["Ahmed Al Rawahi", "ahmed@example.com", ["Projects Manager", "Employee"], null, 1],
	["Temp Contractor", "temp.contractor@example.com", ["Employee"], 20000, 0],
	["Sara Al Kindi", "sara@example.com", ["Workspace Manager", "System Manager"], 180, 1],
];
const userRows = people.map(([n, e, r, mins, en]: any) => ({ name: e, full_name: n, email: e, enabled: en, user_type: "System User", last_login: mins === null ? null : ago(mins), roles: r, companies: e.startsWith("omar") ? ["Sample Trading LLC"] : [], role_profiles: [], default_workspace: r[0].includes("HR") ? "HR" : r[0].includes("Sales") ? "Selling" : "" }));
Object.assign(responses, {
	"thinknxg_admin.api.users.list_users": () => ({ rows: userRows, total: userRows.length, start: 0, page_length: 25 }),
	"thinknxg_admin.api.users.get_form_options": () => ({ roles: ["Accounts Manager", "Accounts User", "Auditor", "Employee", "HR Manager", "HR User", "Projects Manager", "Purchase User", "Sales Manager", "Sales User", "Stock User", "System Manager", "Workspace Manager"].map((name) => ({ name, desk_access: 1 })), role_profiles: ["Sales Team", "Finance Team"], module_profiles: ["HR only"], workspaces: [{ name: "Selling", label: "Selling" }, { name: "HR", label: "HR" }], apps: ["frappe", "erpnext", "hrms"], companies: ["Sample Trading LLC", "Sample Services SPC"] }),
	"thinknxg_admin.api.users.get_user": (a: any) => { const u = userRows.find((r) => r.name === a.name) || userRows[1]; return { ...u, first_name: u.full_name.split(" ")[0], creation: ago(90000), last_ip: "10.0.4.37", roles: u.roles, role_profiles: [], blocked_modules: [], has_api_key: false, api_key: null, is_self: false, module_profile: "", default_app: "erpnext", user_permissions: [{ name: "up1", allow: "Company", for_value: "Sample Trading LLC", is_default: 1, apply_to_all_doctypes: 1 }], logins: [{ name: "l1", operation: "Login", status: "Success", creation: ago(11), ip_address: "10.0.4.37" }, { name: "l2", operation: "Logout", status: "Success", creation: ago(600), ip_address: "10.0.4.37" }], recent_changes: [{ name: "v1", ref_doctype: "Sales Order", docname: "SAL-ORD-2026-00231", creation: ago(30) }] }; },
	"thinknxg_admin.api.users.list_invitations": () => [{ name: "i1", email: "new.hire@example.com", status: "Pending", invited_by: "noor@example.com", creation: ago(120), roles: ["Employee"] }, { name: "i2", email: "analyst@example.com", status: "Pending", invited_by: "noor@example.com", creation: ago(2000), roles: ["Accounts User"] }, { name: "i3", email: "intern@example.com", status: "Accepted", invited_by: "sara@example.com", creation: ago(9000), roles: ["Employee"] }],
	"thinknxg_admin.api.users.list_user_permissions": () => ({ rows: [{ name: "up1", user: "omar@example.com", allow: "Company", for_value: "Sample Trading LLC", is_default: 1, apply_to_all_doctypes: 1 }, { name: "up2", user: "rahul@example.com", allow: "Territory", for_value: "Muscat", is_default: 0, apply_to_all_doctypes: 1 }], total: 2, allow_options: ["Company", "Territory"] }),
	"thinknxg_admin.api.roles.list_roles": () => [["Accounts Manager", 6, 84, 3, 0], ["Accounts User", 22, 71, 3, 0], ["Auditor", 2, 40, 0, 0], ["Employee", 131, 33, 2, 0], ["HR Manager", 3, 96, 4, 0], ["Payroll Manager", 0, 0, 0, 1], ["Sales Manager", 4, 58, 2, 0], ["Sales User", 34, 49, 2, 0], ["System Manager", 3, 412, 9, 0]].map(([name, users, doctypes, workspaces, custom]: any) => ({ name, users, doctypes, workspaces, is_custom: custom, desk_access: 1, disabled: 0, two_factor_auth: name === "System Manager" ? 1 : 0 })),
	"thinknxg_admin.api.roles.get_role": (a: any) => ({ role: { name: a.name, desk_access: 1, disabled: 0, two_factor_auth: 0, is_custom: 0 }, users: userRows.filter((u) => u.roles.includes(a.name)).map((u) => ({ name: u.name, full_name: u.full_name, enabled: u.enabled, last_login: u.last_login })), permissions: [{ doctype: "Sales Order", module: "Selling", read: 1, write: 1, create: 1, delete: 0, submit: 1, cancel: 1, report: 1, export: 1, import: 0, share: 1, print: 1, email: 1, if_owner: 0 }, { doctype: "Quotation", module: "Selling", read: 1, write: 1, create: 1, delete: 1, submit: 1, cancel: 1, report: 1, export: 1, import: 0, share: 1, print: 1, email: 1, if_owner: 0 }, { doctype: "Customer", module: "Selling", read: 1, write: 1, create: 1, delete: 0, submit: 0, cancel: 0, report: 1, export: 0, import: 0, share: 1, print: 1, email: 1, if_owner: 0 }], workspaces: ["Selling"], role_profiles: ["Sales Team"], standard: false }),
	"thinknxg_admin.api.roles.list_role_profiles": () => [{ name: "Sales Team", roles: ["Sales User", "Employee"], users: 31 }, { name: "Finance Team", roles: ["Accounts User", "Accounts Manager", "Employee"], users: 8 }],
	"frappe.core.page.permission_manager.permission_manager.get_roles_and_doctypes": () => ({ doctypes: ["Customer", "Quotation", "Sales Invoice", "Sales Order", "User"].map((value) => ({ value, label: value })), roles: ["Accounts Manager", "Accounts User", "Sales Manager", "Sales User", "System Manager"].map((value) => ({ value, label: value })), doctype_ptype_map: { "Sales Invoice": ["approve_discount"] } }),
	"frappe.core.page.permission_manager.permission_manager.get_permissions": (a: any) => [["Accounts Manager", 0, [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]], ["Accounts User", 0, [1, 1, 1, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 1]], ["Sales User", 0, [1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0]], ["Accounts Manager", 1, [0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]]].map(([role, permlevel, v]: any) => ({ parent: a.doctype || "Sales Invoice", role, permlevel, if_owner: 0, is_submittable: 1, select: v[0], read: v[1], write: v[2], create: v[3], delete: v[4], submit: v[5], cancel: v[6], amend: v[7], report: v[8], export: v[9], import: v[10], share: v[11], print: v[12], email: v[13], approve_discount: role === "Accounts Manager" ? 1 : 0 })),
	"thinknxg_admin.api.organization.get_organization": () => ({ available: true, companies: [{ name: "Sample Trading LLC", abbr: "STL", default_currency: "OMR", country: "Oman", counts: { employees: 96, departments: 9, cost_centers: 6, warehouses: 5 } }, { name: "Sample Services SPC", abbr: "SSS", default_currency: "OMR", country: "Oman", parent_company: "Sample Trading LLC", counts: { employees: 35, departments: 5, cost_centers: 3, warehouses: 1 } }], departments: [["All Departments", null, 1, 0], ["Operations", "All Departments", 1, 4], ["Logistics", "Operations", 0, 22], ["Warehouse", "Operations", 0, 18], ["Commercial", "All Departments", 1, 2], ["Sales", "Commercial", 0, 27], ["Marketing", "Commercial", 0, 6], ["Finance", "All Departments", 0, 11], ["Human Resources", "All Departments", 0, 7]].map(([n, p, g, e]: any) => ({ name: n, department_name: n, parent_department: p, is_group: g, employees: e })), branches: [{ name: "Muscat HQ", employees: 71 }, { name: "Sohar", employees: 34 }, { name: "Salalah", employees: 26 }], designations: [{ name: "Sales Executive", employees: 21 }, { name: "Storekeeper", employees: 14 }, { name: "Accountant", employees: 8 }, { name: "HR Officer", employees: 4 }], fiscal_years: [{ name: "2026", year_start_date: "2026-01-01", year_end_date: "2026-12-31", disabled: 0 }, { name: "2025", year_start_date: "2025-01-01", year_end_date: "2025-12-31", disabled: 0 }], currencies_enabled: 4, regional: { country: "Oman", time_zone: "Asia/Muscat", language: "en", currency: "OMR", date_format: "dd-mm-yyyy", time_format: "HH:mm:ss", number_format: "#,###.###", first_day_of_the_week: "Sunday" } }),
	"thinknxg_admin.api.workspaces.get_overview": () => ({ is_workspace_manager: true, roles: ["Accounts User", "Employee", "HR Manager", "Sales User", "Stock User"], workspaces: [["Home", "Setup", "erpnext", 1, []], ["Selling", "Selling", "erpnext", 1, ["Sales User", "Sales Manager"]], ["Buying", "Buying", "erpnext", 1, ["Purchase User"]], ["Accounting", "Accounts", "erpnext", 1, ["Accounts User"]], ["HR", "HR", "hrms", 1, ["HR User", "HR Manager"]], ["Payroll", "Payroll", "hrms", 1, ["HR Manager"]], ["My notes", "", "", 0, []]].map(([n, m, app, pub, roles]: any, i) => ({ name: n, label: n, module: m, app, public: pub, roles, is_hidden: n === "Payroll" ? 1 : 0, for_user: pub ? null : "noor@example.com", sequence_id: i + 1 })), modules: [["Selling", "erpnext", true], ["Buying", "erpnext", false], ["Accounts", "erpnext", false], ["Stock", "erpnext", false], ["HR", "hrms", false], ["Payroll", "hrms", true], ["Core", "frappe", false]].map(([name, app_name, site_layer]) => ({ name, app_name, site_layer })), icons: [["Accounting", "erpnext", "Workspace Sidebar", "Accounting", 0], ["Selling", "erpnext", "Workspace Sidebar", "Selling", 0], ["Banking", "erpnext", "URL", "/banking", 1], ["HR Setup", "hrms", "Workspace Sidebar", "HR Setup", 0], ["Users", "frappe", "Workspace Sidebar", "Users", 0]].map(([label, app, lt, lto, hidden]: any) => ({ name: label, label, app, icon: "layout-grid", link_type: lt, link_to: lto, hidden, roles: label === "Accounting" ? ["Accounts User"] : [] })) }),
	"frappe.desk.doctype.custom_sidebar.custom_sidebar.get_site_sidebar_layer": () => [["Section Break", "Transactions", null, null, 0, 0, 0], ["Link", "Quotation", "DocType", "Quotation", 1, 0, 0], ["Link", "Sales Order", "DocType", "Sales Order", 1, 0, 0], ["Link", "Sales Invoice", "DocType", "Sales Invoice", 1, 0, 0], ["Section Break", "Masters", null, null, 0, 0, 0], ["Link", "Customer", "DocType", "Customer", 1, 0, 0], ["Link", "Product Bundle", "DocType", "Product Bundle", 1, 1, 0], ["Link", "Sales Analytics", "Report", "Sales Analytics", 0, 0, 1]].map(([type, label, link_type, link_to, child, hidden, added]: any) => ({ type, label, link_type, link_to, child, hidden, added, key: label })),
	"thinknxg_admin.api.apps.get_apps": () => ({ apps: [["frappe", "thinkNXG Framework", "16.56.0", "version-16", [["Core", 74], ["Desk", 51], ["Website", 28], ["Automation", 19]]], ["erpnext", "thinkNXG ERP", "16.54.0", "version-16", [["Accounts", 212], ["Selling", 41], ["Buying", 33], ["Stock", 96], ["Manufacturing", 61]]], ["hrms", "thinkNXG HR", "16.53.2", "version-16", [["HR", 167], ["Payroll", 58]]], ["thinknxg_admin", "thinkNXG Admin", "16.0.0", "version-16", [["thinkNXG Admin", 2]]]].map(([name, title, version, branch, mods]: any) => ({ name, title, version, branch, publisher: "Kreatao", description: "", logo: "/assets/frappe/images/thinkNXG-favicon.png", icons: { total: mods.length, hidden: name === "erpnext" ? 1 : 0 }, modules: mods.map(([m, d]: any) => ({ name: m, doctypes: d, custom: 0, blocked_users: m === "Payroll" ? 12 : 0, blocked_in_profiles: m === "Payroll" ? ["Sales team"] : [] })) })), module_profiles: [{ name: "Sales team", blocked_modules: ["Payroll", "HR", "Manufacturing"], users: 12 }] }),
});

Object.assign(responses, {
	"thinknxg_admin.api.notifications.list_notifications": () => ({ total: 6, unread: 3, unread_by_type: { Assignment: 1, Mention: 1, Alert: 1 }, types: ["Alert", "Assignment", "Mention", "Share"], rows: [
		{ name: "n1", type: "Assignment", subject: "Rahul Menon assigned you Review new joiner access for Finance", from_name: "Rahul Menon", read: 0, creation: ago(30), document_type: "ToDo", document_name: "TD-0091", route: "#" },
		{ name: "n2", type: "Mention", subject: "Fatma Al Hinai mentioned you on Purchase Order PUR-ORD-2026-00188: “can you approve the revised quantity?”", from_name: "Fatma Al Hinai", read: 0, creation: ago(95), document_type: "Purchase Order", document_name: "PUR-ORD-2026-00188", route: "#" },
		{ name: "n3", type: "Alert", subject: "Failed background job: erpnext.stock.reorder_item.reorder_item", from_name: "Administrator", read: 0, creation: ago(300), route: "#" },
		{ name: "n4", type: "Share", subject: "Noor Al Balushi shared Payroll Entry HR-PRUN-2026-00011 with you", from_name: "Noor Al Balushi", read: 1, creation: ago(1600), route: "#" },
		{ name: "n5", type: "Mention", subject: "Omar Al Said mentioned you on Stock Entry MAT-STE-2026-00412", from_name: "Omar Al Said", read: 1, creation: ago(3200), route: "#" },
		{ name: "n6", type: "Assignment", subject: "Sara Al Kindi assigned you Quarterly access review", from_name: "Sara Al Kindi", read: 1, creation: ago(7000), route: "#" } ] }),
	"thinknxg_admin.api.audit.get_summary": () => ({ logins: 1286, failed_logins: 14, permission_changes: 9, access_changes: 23, config_changes: 14, exports: 31, api_requests: null, api_logging_enabled: false, top_failed_users: [{ user: "ops@example.com", n: 9 }, { user: "temp.contractor@example.com", n: 3 }], top_failed_ips: [{ ip: "10.0.9.3", n: 9 }, { ip: "185.22.14.7", n: 4 }] }),
	"thinknxg_admin.api.audit.get_events": () => ({ has_more: true, window_capped: false, categories: {}, rows: [
		{ id: "e1", source: "Version", category: "access_control", actor_name: "Sample Admin", action: "Changed Enabled", resource_type: "User", resource: "temp.contractor@example.com", timestamp: ago(18), result: "Success", route: "#", changes: [{ field: "Enabled", old: "1", new: "0" }] },
		{ id: "e2", source: "Activity Log", category: "authentication", actor_name: "Ops Desk", action: "Failed sign-in", resource_type: "User", resource: "ops@example.com", timestamp: ago(40), result: "Failed", ip: "10.0.9.3", route: "#" },
		{ id: "e3", source: "Permission Log", category: "permissions", actor_name: "Sample Admin", action: "Updated permission on Sales Invoice", resource_type: "Custom DocPerm", resource: "Accounts User", timestamp: ago(90), result: "Success", route: "#", changes: [{ field: "Delete", old: "0", new: "1" }, { field: "Export", old: "0", new: "1" }] },
		{ id: "e4", source: "Access Log", category: "data_access", actor_name: "Fatma Al Hinai", action: "Exported CSV", resource_type: "Sales Invoice", resource: "Report view", timestamp: ago(150), result: "Success", route: "#" },
		{ id: "e5", source: "Version", category: "configuration", actor_name: "Sample Admin", action: "Changed Session Expiry", resource_type: "System Settings", resource: "System Settings", timestamp: ago(800), result: "Success", route: "#", changes: [{ field: "Session Expiry", old: "06:00", new: "04:00" }] },
		{ id: "e6", source: "Activity Log", category: "authentication", actor_name: "Noor Al Balushi", action: "Signed in", resource_type: "User", resource: "noor@example.com", timestamp: ago(4), result: "Success", ip: "10.0.4.21", route: "#" } ] }),
	"thinknxg_admin.api.integrations.get_overview": () => ({
		webhooks: [{ name: "WH-1", webhook_doctype: "Sales Invoice", webhook_docevent: "on_submit", request_url: "https://hooks.example-erp-sync.com/invoices", request_method: "POST", enabled: 1, enable_security: 1, calls_7d: 412, failed_7d: 0, failed_24h: 0, last_call: ago(12) }, { name: "WH-2", webhook_doctype: "Customer", webhook_docevent: "after_insert", request_url: "https://crm.example.com/api/customers", request_method: "POST", enabled: 1, enable_security: 0, calls_7d: 38, failed_7d: 6, failed_24h: 2, last_call: ago(140) }, { name: "WH-3", webhook_doctype: "Item", webhook_docevent: "on_update", request_url: "https://shop.example.com/sync", request_method: "PUT", enabled: 0, calls_7d: 0, failed_7d: 0, failed_24h: 0 }],
		oauth_clients: [{ name: "oc1", app_name: "thinkNXG Mobile", client_id: "a1b2c3", grant_type: "Authorization Code", scopes: ["all", "openid"], redirect: "https://app.example.com/callback", active_tokens: 42 }],
		connected_apps: [{ name: "ca1", provider_name: "Google Workspace", authorization_uri: "https://accounts.google.com/o/oauth2/auth", connected_users: 7 }],
		social_logins: [{ name: "google", provider_name: "Google", enable_social_login: 1, sign_ups: "Deny" }, { name: "microsoft", provider_name: "Microsoft", enable_social_login: 0, sign_ups: "" }],
		email_accounts: [{ name: "Notifications", email_account_name: "Notifications", email_id: "notifications@example.com", service: "GMail", enable_outgoing: 1, default_outgoing: 1, sent_7d: 2140, errors_7d: 3, pending: 4 }, { name: "Support", email_account_name: "Support", email_id: "support@example.com", service: "Outlook.com", enable_incoming: 1, enable_outgoing: 1, default_incoming: 1, sent_7d: 310, errors_7d: 0, pending: 0 }],
		email_queue: { pending: 4, errors_24h: 1, sent_24h: 388 },
		api_users: [{ name: "integration@example.com", full_name: "Integration Bot", enabled: 1, api_key: "8f3c1a2b9d0e4f5", last_request: ago(3) }, { name: "temp.contractor@example.com", full_name: "Temp Contractor", enabled: 0, api_key: "11aa22bb33cc44d", last_request: ago(30000) }],
		api_requests_24h: 18420, integration_requests: [{ service: "Razorpay", status: "Completed", n: 120 }, { service: "Razorpay", status: "Failed", n: 2 }] }),
	"thinknxg_admin.api.automation.get_overview": () => ({ scheduler: "running", server_scripts_enabled: false,
		workflows: [{ name: "Leave Approval", document_type: "Leave Application", is_active: 1, states: 4, transitions: 5, open_actions: 7 }, { name: "PO Approval", document_type: "Purchase Order", is_active: 1, states: 3, transitions: 4, open_actions: 5 }, { name: "PO Approval (old)", document_type: "Purchase Order", is_active: 0, states: 2, transitions: 2, open_actions: 0 }],
		notifications: [{ name: "Invoice overdue reminder", document_type: "Sales Invoice", event: "Days After", days_in_advance: 3, date_changed: "due_date", channel: "Email", enabled: 1 }, { name: "New lead to sales team", document_type: "Lead", event: "New", channel: "System Notification", enabled: 1 }],
		assignment_rules: [{ name: "Support round robin", document_type: "Issue", rule: "Round Robin", users: 4, priority: 1, disabled: 0, last_user: "rahul@example.com" }],
		scheduled_jobs: [["erpnext.stock.reorder_item.reorder_item", "Hourly", 1, 0], ["frappe.email.queue.flush", "All", 0, 0], ["hrms.hr.doctype.attendance.attendance.mark_absent", "Daily", 0, 0], ["frappe.desk.doctype.event.event.send_event_digest", "Daily", 0, 1]].map(([method, frequency, fail, stopped]: any, i) => ({ name: `job${i}`, method, frequency, stopped, app: method.split(".")[0], last_execution: ago(10 + i * 50), next_execution: ago(-50), failures_7d: fail ? 3 : 0, runs_7d: frequency === "Hourly" ? 168 : 7, create_log: 1 })),
		server_scripts: [{ name: "Validate credit limit", script_type: "DocType Event", reference_doctype: "Sales Order", doctype_event: "Before Submit", disabled: 0, module: "Selling", modified: ago(9000) }],
		auto_repeat: { active: 12, by_doctype: [{ reference_doctype: "Sales Invoice", n: 9 }, { reference_doctype: "Journal Entry", n: 3 }], upcoming: [{ name: "AR-1", reference_doctype: "Sales Invoice", reference_document: "ACC-SINV-2026-00120", frequency: "Monthly", next_schedule_date: "2026-12-01" }] },
		naming_rules: [], milestones: [] }),
	"thinknxg_admin.api.developer.get_overview": () => ({ developer_mode: false, server_scripts_enabled: false, doctypes: 1184, custom_doctypes: 6, child_tables: 702, custom_fields: 148, property_setters: 391, client_scripts: 4, server_scripts: 1, errors_24h: 9, errors_unseen: 9, modules: 64, apps: [{ name: "frappe", title: "thinkNXG Framework", version: "16.56.0", branch: "version-16" }, { name: "erpnext", title: "thinkNXG ERP", version: "16.54.0", branch: "version-16" }, { name: "hrms", title: "thinkNXG HR", version: "16.53.2", branch: "version-16" }, { name: "thinknxg_admin", title: "thinkNXG Admin", version: "16.2.0", branch: "main" }] }),
	"thinknxg_admin.api.developer.list_errors": () => ({ total: 3, rows: [{ name: "er1", method: "erpnext.stock.reorder_item.reorder_item", exception: "frappe.exceptions.ValidationError: Warehouse Stores - STL not found", creation: ago(300), seen: 0 }, { name: "er2", method: "webhook: WH-2", exception: "requests.exceptions.ConnectTimeout: HTTPSConnectionPool(host='crm.example.com')", reference_doctype: "Customer", reference_name: "CUST-0412", creation: ago(140), seen: 0 }] }),
});

const realFetch = window.fetch.bind(window);
window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
	const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
	const m = url.match(/\/api\/method\/([\w.]+)/);
	if (m) {
		let args: any = {};
		try {
			const q = url.split("?")[1];
			if (q) args = Object.fromEntries(new URLSearchParams(q));
			if (init?.body && typeof init.body === "string") args = { ...args, ...JSON.parse(init.body) };
		} catch {
			/* ignore */
		}
		const handler = responses[m[1]];
		await new Promise((r) => setTimeout(r, 250 + Math.random() * 350));
		const body = handler ? { message: handler(args) } : { message: null };
		return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
	}
	return realFetch(input, init);
};
