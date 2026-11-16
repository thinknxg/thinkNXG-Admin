import { reactive } from "vue";
import { call } from "frappe-ui";
import { setServerNow } from "@/composables/format";

export interface NavItem {
	key: string;
	label: string;
	icon?: string;
	route: string;
	/** Native Desk screen: rendered as a normal link, not a router link. */
	href?: string;
	desk?: string;
	doctype?: string;
	status?: "live" | "planned" | "desk";
	phase?: number | string;
	description?: string;
	capabilities?: string[];
	children?: NavItem[];
}
export type CenterKey = "admin" | "erp" | "hr";
export type CenterFilter = "company" | "branch" | "department" | "fiscal_year" | "date_range";
export interface NavSection { section: string; items: NavItem[] }
export interface QuickCreate { doctype: string; icon: string; route: string; center?: CenterKey }
export interface Center {
	key: CenterKey;
	label: string;
	short: string;
	icon: string;
	description: string;
	route: string;
	title: string;
	subtitle: string;
	docs_url: string;
	filters: CenterFilter[];
	/** Decided on the server: full, limited (some figures restricted) or team (direct reports only). */
	access: "full" | "limited" | "team";
	navigation: NavSection[];
	quick_create: QuickCreate[];
}
export interface CenterState { company?: string; branch?: string; department?: string; fiscal_year?: string; days?: number; last_route?: string }
export interface Preferences { default_center: CenterKey | null; last_center: CenterKey | null; state: Partial<Record<CenterKey, CenterState>> }
export interface Boot {
	user: { name: string; full_name: string; email?: string; image?: string; theme?: string; roles: string[]; is_admin: boolean };
	brand: { name: string; product: string; logo: string; docs_url: string; support_url: string; whats_new_url: string };
	version: string;
	centers: Center[];
	default_center: CenterKey | null;
	preferences: Preferences;
	personal_navigation: NavSection[];
	apps: { app: string; name: string; title: string; logo?: string; route: string }[];
	companies: { name: string; abbr?: string; default_currency?: string }[];
	default_company: string | null;
	show_classic_desk_link: boolean;
	site: string;
	server_now?: string;
}

declare global {
	interface Window {
		thinknxg_boot?: Boot | string;
		csrf_token?: string;
	}
}

export const boot = reactive({ ready: false, data: null as Boot | null, error: null as string | null });

export async function loadBoot() {
	const embedded = window.thinknxg_boot;
	// The production page embeds boot JSON server-side; Vite dev serves the raw
	// Jinja placeholder instead, so fall back to the API.
	if (embedded && typeof embedded === "object") {
		boot.data = embedded;
	} else {
		try {
			boot.data = await call("thinknxg_admin.api.boot.get_boot");
		} catch (e: any) {
			if (e?.exc_type === "AuthenticationError" || e?.status === 403 || e?.httpStatus === 403) {
				window.location.href = "/login?redirect-to=" + encodeURIComponent(window.location.pathname);
				return;
			}
			boot.error = e?.messages?.[0] || e?.message || "Could not load the Command Center.";
		}
	}
	if (boot.data?.server_now) setServerNow(boot.data.server_now);
	boot.ready = true;
}

/** Every navigation entry across the user's centers (deduplicated by route). */
export function allNavItems(): NavItem[] {
	const out: NavItem[] = [];
	const seen = new Set<string>();
	const sections = [...(boot.data?.centers || []).flatMap((c) => c.navigation), ...(boot.data?.personal_navigation || [])];
	for (const s of sections)
		for (const i of s.items)
			for (const x of [i, ...(i.children || [])]) {
				if (seen.has(x.route)) continue;
				seen.add(x.route);
				out.push(x);
			}
	return out;
}

export function getCenter(key: string | null | undefined): Center | undefined {
	return boot.data?.centers.find((c) => c.key === key);
}

export function findNavByRoute(path: string): NavItem | undefined {
	const items = allNavItems();
	const inApp = items.filter((i) => !i.href);
	return inApp.find((i) => i.route === path) || inApp.filter((i) => i.route !== "/" && path.startsWith(i.route + "/")).sort((a, b) => b.route.length - a.route.length)[0];
}
