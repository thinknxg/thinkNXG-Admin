import { createRouter, createWebHistory, START_LOCATION, type RouteRecordRaw } from "vue-router";
import { allNavItems, boot, getCenter } from "@/data/boot";
import { pushRecent } from "@/composables/useRecent";

const routes: RouteRecordRaw[] = [
	{ path: "/", name: "command-center", component: () => import("@/pages/CommandCenter.vue"), meta: { admin: true, title: "Command Center" } },
	{ path: "/system-health", name: "system-health", component: () => import("@/pages/SystemHealth.vue"), meta: { admin: true, title: "System Health" } },
	{ path: "/users", component: () => import("@/pages/users/UsersPage.vue"), meta: { admin: true, title: "Users" } },
	{ path: "/users/invitations", component: () => import("@/pages/users/InvitationsPage.vue"), meta: { admin: true, title: "Invitations" } },
	{ path: "/users/permissions", component: () => import("@/pages/users/UserPermissionsPage.vue"), meta: { admin: true, title: "User Permissions" } },
	{ path: "/roles", component: () => import("@/pages/roles/RolesPage.vue"), meta: { admin: true, title: "Roles" } },
	{ path: "/roles/profiles", component: () => import("@/pages/roles/RoleProfilesPage.vue"), meta: { admin: true, title: "Role Profiles" } },
	{ path: "/roles/matrix", component: () => import("@/pages/roles/PermissionMatrix.vue"), meta: { admin: true, title: "Permission Matrix" } },
	{ path: "/organization", component: () => import("@/pages/OrganizationPage.vue"), meta: { admin: true, title: "Organization" } },
	{ path: "/workspaces", component: () => import("@/pages/WorkspacesPage.vue"), meta: { admin: true, title: "Workspaces" } },
	{ path: "/apps", component: () => import("@/pages/AppsPage.vue"), meta: { admin: true, title: "Apps & Modules" } },
	{ path: "/notifications", component: () => import("@/pages/NotificationsPage.vue"), meta: { title: "Notifications" } },
	{ path: "/integrations", component: () => import("@/pages/IntegrationsPage.vue"), meta: { admin: true, title: "Integrations" } },
	{ path: "/automation", component: () => import("@/pages/AutomationPage.vue"), meta: { admin: true, title: "Automation" } },
	{ path: "/audit", component: () => import("@/pages/AuditPage.vue"), meta: { admin: true, title: "Audit & Compliance" } },
	{ path: "/developer", component: () => import("@/pages/DeveloperPage.vue"), meta: { admin: true, title: "Developer Tools" } },
	{ path: "/my-workspace", component: () => import("@/pages/MyWorkspacePage.vue"), meta: { title: "My Workspace" } },
	{ path: "/configuration", component: () => import("@/pages/ConfigurationPage.vue"), meta: { admin: true, title: "System Configuration" } },
	{ path: "/reports", component: () => import("@/pages/ReportsPage.vue"), meta: { title: "Reports & Analytics" } },
	{ path: "/erp", component: () => import("@/pages/CenterHome.vue"), props: { centerKey: "erp" }, meta: { center: "erp", title: "ERP Command Center" } },
	{ path: "/hr", component: () => import("@/pages/CenterHome.vue"), props: { centerKey: "hr" }, meta: { center: "hr", title: "HR Command Center" } },
	// Every other registry route is resolved at runtime against the server-filtered navigation.
	{ path: "/:pathMatch(.*)*", name: "dynamic", component: () => import("@/pages/Planned.vue") },
];

export const router = createRouter({ history: createWebHistory("/thinknxg"), routes, scrollBehavior: () => ({ top: 0 }) });

/** Where a user lands: their default center, else My Workspace. */
export function landingRoute(): string {
	const c = getCenter(boot.data?.default_center);
	return c ? c.route : "/my-workspace";
}

const CENTER_PREFIX: Record<string, string> = { "/erp": "erp", "/hr": "hr" };

router.beforeEach((to, from) => {
	const data = boot.data;
	if (!data) return true;
	// Opening /thinknxg itself goes to the user's default command center.
	if (from === START_LOCATION && to.path === "/" && landingRoute() !== "/") return landingRoute();
	// UX guards only - every endpoint refuses on the server anyway.
	if (to.meta.admin && !data.user.is_admin) return landingRoute() === "/" ? "/my-workspace" : landingRoute();
	const prefix = Object.keys(CENTER_PREFIX).find((p) => to.path === p || to.path.startsWith(p + "/"));
	if (prefix && !getCenter(CENTER_PREFIX[prefix])) return landingRoute() === to.path ? "/my-workspace" : landingRoute();
	return true;
});

router.afterEach((to) => {
	const item = allNavItems().find((i) => i.route === to.path);
	const title = (to.meta.title as string) || item?.label || "Not found";
	document.title = `${title} · thinkNXG`;
	if (item || to.meta.title) pushRecent({ label: title, route: to.path, icon: item?.icon });
});
