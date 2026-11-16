import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";
import { allNavItems, boot } from "@/data/boot";
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
	// Every other registry route is resolved at runtime against the server-filtered navigation.
	{ path: "/:pathMatch(.*)*", name: "dynamic", component: () => import("@/pages/Planned.vue") },
];

export const router = createRouter({ history: createWebHistory("/thinknxg"), routes, scrollBehavior: () => ({ top: 0 }) });

router.beforeEach((to) => {
	const data = boot.data;
	if (!data) return true;
	// UX guard only - the server refuses the data anyway (require_admin).
	if (to.meta.admin && !data.user.is_admin) {
		const first = allNavItems().find((i) => !i.route.startsWith("/system") && i.route !== "/");
		return first ? first.route : { name: "dynamic", params: { pathMatch: ["not-found"] } };
	}
	if (to.name === "dynamic" && !allNavItems().some((i) => i.route === to.path)) {
		return true; // Planned.vue shows "not available" when the route isn't in the user's navigation
	}
	return true;
});

router.afterEach((to) => {
	const item = allNavItems().find((i) => i.route === to.path);
	const title = (to.meta.title as string) || item?.label || "Not found";
	document.title = `${title} · thinkNXG`;
	if (item || to.meta.title) pushRecent({ label: title, route: to.path, icon: item?.icon });
});
