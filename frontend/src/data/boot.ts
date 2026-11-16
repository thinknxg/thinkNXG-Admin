import { reactive } from "vue";
import { call } from "frappe-ui";
import { setServerNow } from "@/composables/format";

export interface NavItem {
	key: string;
	label: string;
	icon?: string;
	route: string;
	desk?: string;
	doctype?: string;
	status?: "live" | "planned";
	phase?: number;
	description?: string;
	capabilities?: string[];
	children?: NavItem[];
}
export interface Boot {
	user: { name: string; full_name: string; email?: string; image?: string; theme?: string; roles: string[]; is_admin: boolean };
	brand: { name: string; product: string; logo: string; docs_url: string; support_url: string; whats_new_url: string };
	version: string;
	navigation: { section: string; items: NavItem[] }[];
	apps: { app: string; name: string; title: string; logo?: string; route: string }[];
	quick_create: { doctype: string; icon: string; route: string }[];
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

export function allNavItems(): NavItem[] {
	const out: NavItem[] = [];
	for (const s of boot.data?.navigation || []) for (const i of s.items) out.push(i, ...(i.children || []));
	return out;
}

export function findNavByRoute(path: string): NavItem | undefined {
	const items = allNavItems();
	return items.find((i) => i.route === path) || items.filter((i) => i.route !== "/" && path.startsWith(i.route)).sort((a, b) => b.route.length - a.route.length)[0];
}
