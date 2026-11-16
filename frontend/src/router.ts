import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";
import { allNavItems, boot, doctypeFromSlug, getCenter, getModule } from "@/data/boot";
import { pushRecent } from "@/composables/useRecent";

/** The internal router. Every page of the three command centers has its own
 *  route here; nothing navigates to the Desk. Route meta drives the guards:
 *  admin (needs an admin role), center (needs that center), and for module,
 *  list and form routes the user's route registry from boot. The server checks
 *  every request again; these guards only decide which page to show. */
const admin = (path: string, load: () => Promise<any>, title: string): RouteRecordRaw => ({ path: `/admin${path}`, component: load, meta: { admin: true, center: "admin", title } });

const centerRoutes = (center: "erp" | "hr" | "admin"): RouteRecordRaw[] => [
	{ path: `/${center}/reports/:report`, name: `${center}-report`, component: () => import("@/pages/doc/ReportPage.vue"), props: (r) => ({ center, report: r.params.report }), meta: { center, title: "Report" } },
	{ path: `/${center}/doc/:doctype`, name: `${center}-doc-list`, component: () => import("@/pages/doc/DocListPage.vue"), props: (r) => ({ center, slug: r.params.doctype }), meta: { center, kind: "list" } },
	{ path: `/${center}/doc/:doctype/new`, name: `${center}-doc-new`, component: () => import("@/pages/doc/DocFormPage.vue"), props: (r) => ({ center, slug: r.params.doctype, name: null }), meta: { center, kind: "form" } },
	{ path: `/${center}/doc/:doctype/:name(.*)+`, name: `${center}-doc-form`, component: () => import("@/pages/doc/DocFormPage.vue"), props: (r) => ({ center, slug: r.params.doctype, name: ([] as string[]).concat(r.params.name as any).join("/") }), meta: { center, kind: "form" } },
];
const moduleRoutes = (center: "erp" | "hr"): RouteRecordRaw[] => [
	{ path: `/${center}/:module`, name: `${center}-module`, component: () => import("@/pages/doc/ModulePage.vue"), props: (r) => ({ center, module: r.params.module }), meta: { center, kind: "module" } },
	{ path: `/${center}/:module/:doctype`, name: `${center}-list`, component: () => import("@/pages/doc/DocListPage.vue"), props: (r) => ({ center, module: r.params.module, slug: r.params.doctype }), meta: { center, kind: "list" } },
	{ path: `/${center}/:module/:doctype/new`, name: `${center}-new`, component: () => import("@/pages/doc/DocFormPage.vue"), props: (r) => ({ center, module: r.params.module, slug: r.params.doctype, name: null }), meta: { center, kind: "form" } },
	{ path: `/${center}/:module/:doctype/:name(.*)+`, name: `${center}-form`, component: () => import("@/pages/doc/DocFormPage.vue"), props: (r) => ({ center, module: r.params.module, slug: r.params.doctype, name: ([] as string[]).concat(r.params.name as any).join("/") }), meta: { center, kind: "form" } },
];

// Old Admin addresses (before /admin) keep working.
const LEGACY_ADMIN = ["/system-health", "/users", "/users/invitations", "/users/permissions", "/roles", "/roles/profiles", "/roles/matrix", "/organization", "/workspaces", "/apps", "/integrations", "/automation", "/audit", "/developer", "/configuration"];

const routes: RouteRecordRaw[] = [
	{ path: "/", name: "landing", component: () => import("@/pages/NotFound.vue"), meta: { landing: true } },
	admin("", () => import("@/pages/CommandCenter.vue"), "Command Center"),
	admin("/system-health", () => import("@/pages/SystemHealth.vue"), "System Health"),
	admin("/users", () => import("@/pages/users/UsersPage.vue"), "Users"),
	admin("/users/invitations", () => import("@/pages/users/InvitationsPage.vue"), "Invitations"),
	admin("/users/permissions", () => import("@/pages/users/UserPermissionsPage.vue"), "User Permissions"),
	admin("/roles", () => import("@/pages/roles/RolesPage.vue"), "Roles"),
	admin("/roles/profiles", () => import("@/pages/roles/RoleProfilesPage.vue"), "Role Profiles"),
	admin("/roles/matrix", () => import("@/pages/roles/PermissionMatrix.vue"), "Permission Matrix"),
	admin("/organization", () => import("@/pages/OrganizationPage.vue"), "Organization"),
	admin("/workspaces", () => import("@/pages/WorkspacesPage.vue"), "Workspaces"),
	admin("/apps", () => import("@/pages/AppsPage.vue"), "Apps & Modules"),
	admin("/integrations", () => import("@/pages/IntegrationsPage.vue"), "Integrations"),
	admin("/automation", () => import("@/pages/AutomationPage.vue"), "Automation"),
	admin("/audit", () => import("@/pages/AuditPage.vue"), "Audit & Compliance"),
	admin("/developer", () => import("@/pages/DeveloperPage.vue"), "Developer Tools"),
	admin("/configuration", () => import("@/pages/ConfigurationPage.vue"), "System Configuration"),
	...LEGACY_ADMIN.map((p) => ({ path: p, redirect: (to: any) => ({ path: `/admin${p}`, query: to.query }) })),
	{ path: "/notifications", component: () => import("@/pages/NotificationsPage.vue"), meta: { title: "Notifications" } },
	{ path: "/my-workspace", component: () => import("@/pages/MyWorkspacePage.vue"), meta: { title: "My Workspace" } },
	{ path: "/reports", component: () => import("@/pages/ReportsPage.vue"), meta: { title: "Reports & Analytics" } },
	{ path: "/erp", component: () => import("@/pages/erp/ErpCommandCenter.vue"), meta: { center: "erp", title: "ERP Command Center" } },
	{ path: "/erp/approvals", component: () => import("@/pages/ApprovalsPage.vue"), props: { centerKey: "erp" }, meta: { center: "erp", title: "Approvals" } },
	{ path: "/hr", component: () => import("@/pages/hr/HrCommandCenter.vue"), meta: { center: "hr", title: "HR Command Center" } },
	{ path: "/hr/approvals", component: () => import("@/pages/ApprovalsPage.vue"), props: { centerKey: "hr" }, meta: { center: "hr", title: "HR Approvals" } },
	...centerRoutes("erp"),
	...centerRoutes("hr"),
	...centerRoutes("admin"),
	...moduleRoutes("erp"),
	...moduleRoutes("hr"),
	{ path: "/resolve", name: "resolve", component: () => import("@/pages/doc/ResolvePage.vue"), meta: { title: "Opening…" } },
	{ path: "/denied", name: "denied", component: () => import("@/pages/doc/AccessDenied.vue"), meta: { title: "Access denied" } },
	{ path: "/:pathMatch(.*)*", name: "not-found", component: () => import("@/pages/NotFound.vue"), meta: { title: "Not found" } },
];

export const router = createRouter({ history: createWebHistory("/thinknxg"), routes, scrollBehavior: (to, from, saved) => saved || (to.path === from.path ? undefined : { top: 0 }) });

/** Where a user lands: their default center, else My Workspace. */
export function landingRoute(): string {
	const c = getCenter(boot.data?.default_center);
	return c ? c.route : "/my-workspace";
}

const denied = (from: string, reason: string) => ({ name: "denied", query: { from, reason } });

router.beforeEach((to) => {
	const data = boot.data;
	if (!data) return true;
	if (to.meta.landing) return landingRoute();
	const center = to.meta.center as string | undefined;
	// Route-level checks. The server refuses the data anyway; these choose the page.
	if (to.meta.admin && !data.user.is_admin) return denied(to.fullPath, "admin");
	if (center && !getCenter(center)) return denied(to.fullPath, "center");
	const kind = to.meta.kind as string | undefined;
	if ((center === "erp" || center === "hr") && to.params.module) {
		const mod = getModule(center, String(to.params.module));
		if (!mod) return denied(to.fullPath, "module");
		if (kind === "list" || kind === "form") {
			const slug = String(to.params.doctype);
			const inModule = mod.groups.some((g) => g.items.some((i) => i.slug === slug));
			if (!inModule) return denied(to.fullPath, "doctype");
			if (kind === "form" && !to.params.name && !mod.groups.some((g) => g.items.some((i) => i.slug === slug && i.create))) return denied(to.fullPath, "create");
		}
	}
	return true;
});

router.afterEach((to) => {
	const item = allNavItems().find((i) => i.route === to.path);
	let title = (to.meta.title as string) || item?.label;
	if (!title && to.params.doctype) title = to.params.name ? `${decodeURIComponent(String(([] as any[]).concat(to.params.name).join("/")))}` : doctypeFromSlug(String(to.params.doctype));
	if (!title && to.params.module) title = getModule(String(to.meta.center), String(to.params.module))?.label;
	document.title = `${title || "thinkNXG"} · thinkNXG`;
	if (title && to.name !== "not-found" && to.name !== "denied" && to.name !== "resolve") pushRecent({ label: title, route: to.fullPath, icon: item?.icon });
});
