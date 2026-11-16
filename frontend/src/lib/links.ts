import type { Router } from "vue-router";
import { boot } from "@/data/boot";

/** Every link in the Command Center goes through here. Internal thinkNXG
 *  addresses are routed without a reload; old Desk addresses (/desk/…, /app/…)
 *  are translated to their internal page; only genuinely external addresses and
 *  explicit developer-tool links (data-desk) leave the app. */
export const BASE = "/thinknxg";

// Core DocTypes that have their own Admin page (mirrors routes.ADMIN_PAGES).
const ADMIN_PAGES: Record<string, string> = {
	user: "/admin/users", "user-invitation": "/admin/users/invitations", "user-permission": "/admin/users/permissions",
	role: "/admin/roles", "role-profile": "/admin/roles/profiles", company: "/admin/organization", workspace: "/admin/workspaces",
	"module-def": "/admin/apps", "system-settings": "/admin/configuration", "notification-log": "/notifications", report: "/reports",
	"activity-log": "/admin/audit", "access-log": "/admin/audit", version: "/admin/audit", webhook: "/admin/integrations",
	"oauth-client": "/admin/integrations", workflow: "/admin/automation", "assignment-rule": "/admin/automation",
	"scheduled-job-type": "/admin/automation", "error-log": "/admin/developer", "rq-job": "/admin/system-health",
	"permission-manager": "/admin/roles/matrix", "user-profile": "/admin/users",
};
// Desk-only developer tools: these stay in the Desk, for System Managers.
const DESK_ONLY = new Set(["doctype", "customize-form", "print-format", "server-script", "client-script", "web-form", "property-setter", "custom-field", "print-format-builder", "form-builder"]);
// Old workspace pages -> module pages.
const WORKSPACES: Record<string, string> = {
	accounting: "/erp/accounting", invoicing: "/erp/accounting", payments: "/erp/accounting", "financial-reports": "/erp/accounting",
	selling: "/erp/selling", buying: "/erp/buying", stock: "/erp/stock", manufacturing: "/erp/manufacturing", crm: "/erp/crm",
	projects: "/erp/projects", assets: "/erp/assets", quality: "/erp/quality", support: "/erp/support", home: "/erp", "erpnext-settings": "/erp",
	"hr-setup": "/hr/employees", leaves: "/hr/leave", payroll: "/hr/payroll", "tax-&-benefits": "/hr/payroll", "tax-%26-benefits": "/hr/payroll",
	recruitment: "/hr/recruitment", performance: "/hr/performance", tenure: "/hr/lifecycle", expenses: "/hr/expenses",
	"shift-&-attendance": "/hr/attendance", "shift-%26-attendance": "/hr/attendance", people: "/hr", "organizational-chart": "/hr/employees",
	build: "/admin", users: "/admin/users", tools: "/admin", "integrations": "/admin/integrations", website: "/admin",
};

function bySlug(slug: string) {
	const entry = Object.entries(boot.data?.registry?.doctypes || {}).find(([, v]) => v.slug === slug);
	return entry?.[1];
}

/** Internal router path (without /thinknxg) for an href, or null if it must stay external. */
export function toInternal(href: string | null | undefined): string | null {
	if (!href) return null;
	let url: URL;
	try {
		url = new URL(href, window.location.origin);
	} catch {
		return null;
	}
	if (url.origin !== window.location.origin) return null;
	const path = url.pathname;
	if (path === BASE || path.startsWith(BASE + "/")) return (path.slice(BASE.length) || "/") + url.search + url.hash;
	if (!(path === "/desk" || path === "/app" || path.startsWith("/desk/") || path.startsWith("/app/"))) return null;

	const segs = path.split("/").filter(Boolean).slice(1).map((s) => decodeURIComponent(s));
	if (!segs.length) return "/";
	const [first, second] = segs;
	const slug = first.toLowerCase();
	if (DESK_ONLY.has(slug)) return null;
	if (slug === "query-report" && second) return `/resolve?path=${encodeURIComponent(path)}`;
	if (ADMIN_PAGES[slug]) {
		if (!second || second === "view") return ADMIN_PAGES[slug] + url.search;
		// Users and roles open in their own panel; other Core records in the generic form.
		if (second !== "new" && (slug === "user" || slug === "role")) return `${ADMIN_PAGES[slug]}?open=${encodeURIComponent(second)}`;
		return `/admin/doc/${slug}/${second === "new" ? "new" : encodeURIComponent(second)}`;
	}
	const hit = bySlug(slug);
	if (hit) {
		const base = `/${hit.center}/${hit.module}/${hit.slug}`;
		if (!second || second === "view") return base + url.search;
		if (second === "new") return `${base}/new`;
		return `${base}/${encodeURIComponent(second)}`;
	}
	if (!second && WORKSPACES[slug]) return WORKSPACES[slug];
	// Unknown here: let the server map it (DocTypes of any app, other workspaces).
	return `/resolve?path=${encodeURIComponent(path + url.search)}`;
}

/** Full href for an internal path, for <a> elements (keeps new-tab working). */
export function internalHref(path: string): string {
	return BASE + (path.startsWith("/") ? path : "/" + path);
}

/** Route clicks on any <a> in the app through the router; rewrite Desk hrefs. */
export function installLinkInterceptor(router: Router) {
	const rewrite = (a: HTMLAnchorElement) => {
		if (a.dataset.desk !== undefined || a.dataset.nxgChecked === a.getAttribute("href")) return null;
		const internal = toInternal(a.getAttribute("href"));
		if (internal) {
			a.setAttribute("href", internalHref(internal));
			a.removeAttribute("target");
			a.removeAttribute("rel");
		}
		a.dataset.nxgChecked = a.getAttribute("href") || "";
		return internal;
	};
	// Before any click or context menu, so "open in new tab" also stays inside thinkNXG.
	document.addEventListener("mousedown", (e) => {
		const a = (e.target as HTMLElement)?.closest?.("a[href]") as HTMLAnchorElement | null;
		if (a) rewrite(a);
	}, true);
	document.addEventListener("focusin", (e) => {
		const a = (e.target as HTMLElement)?.closest?.("a[href]") as HTMLAnchorElement | null;
		if (a) rewrite(a);
	}, true);
	document.addEventListener("click", (e) => {
		if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
		const a = (e.target as HTMLElement)?.closest?.("a[href]") as HTMLAnchorElement | null;
		if (!a || a.dataset.desk !== undefined || a.hasAttribute("download")) return;
		rewrite(a);
		const internal = toInternal(a.getAttribute("href"));
		if (!internal) return;
		e.preventDefault();
		router.push(internal);
	});
}

/** Navigate to any href: internal via the router, external via the browser. */
export function go(router: Router, href: string) {
	const internal = toInternal(href);
	if (internal) router.push(internal);
	else window.location.href = href;
}

/** Navigate anywhere from code (notifications, palette, row clicks). */
export async function nav(href: string) {
	const { router } = await import("@/router");
	go(router, href);
}
