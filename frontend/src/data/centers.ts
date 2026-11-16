import { computed, reactive, watch } from "vue";
import { call } from "frappe-ui";
import { boot, getCenter, type Center, type CenterKey, type CenterState, type NavSection, type Preferences } from "@/data/boot";
import { readPref, writePref } from "@/composables/storage";
import { router } from "@/router";

/** Route prefixes owned by a center. Every other route belongs to Admin when the
 *  user has it, or is shared (Notifications, My Workspace, Reports). */
const PREFIX: Record<CenterKey, string> = { admin: "/admin", erp: "/erp", hr: "/hr" };

/** The center that owns a path, or null for shared pages (Notifications, My
 *  Workspace, Reports, not-found), which keep the last center's sidebar. */
export function centerForPath(path: string): CenterKey | null {
	for (const [key, prefix] of Object.entries(PREFIX)) if (path === prefix || path.startsWith(prefix + "/")) return key as CenterKey;
	return null;
}

const local = readPref<{ last?: CenterKey; state?: Partial<Record<CenterKey, CenterState>> }>("centers", {});

export const centers = reactive({
	/** Last center the user was in; decides the sidebar on shared pages. */
	last: (local.last ?? null) as CenterKey | null,
	state: (local.state ?? {}) as Partial<Record<CenterKey, CenterState>>,
});

export function initCenters() {
	const prefs = boot.data?.preferences;
	if (!prefs) return;
	// Server copy wins for anything it holds, so choices follow the user across devices.
	for (const [k, v] of Object.entries(prefs.state || {})) centers.state[k as CenterKey] = { ...(centers.state[k as CenterKey] || {}), ...v };
	if (prefs.last_center && getCenter(prefs.last_center)) centers.last = prefs.last_center;
	if (centers.last && !getCenter(centers.last)) centers.last = null;
	// Drop saved companies the user can no longer see.
	const companies = new Set((boot.data?.companies || []).map((c) => c.name));
	for (const s of Object.values(centers.state)) if (s?.company && !companies.has(s.company)) delete s.company;
}

/** The center whose sidebar, header filters and quick actions are shown. */
export const activeCenter = computed<Center | undefined>(() => {
	const path = router.currentRoute.value.path;
	const owned = centerForPath(path);
	if (owned) return getCenter(owned);
	return getCenter(centers.last) || getCenter(boot.data?.default_center) || boot.data?.centers[0];
});

export const activeNavigation = computed<NavSection[]>(() => activeCenter.value?.navigation || boot.data?.personal_navigation || []);

/** Read-only view of a center's saved filters (never creates state). */
export function peekState(key: CenterKey): CenterState {
	return centers.state[key] || {};
}

export function stateFor(key: CenterKey): CenterState {
	if (!centers.state[key]) centers.state[key] = {};
	return centers.state[key]!;
}

/** Route that opens a center: the page last visited in it, else its home. */
export function entryRoute(c: Center): string {
	const last = centers.state[c.key]?.last_route;
	if (last && centerForPath(last.split("?")[0]) === c.key) return last;
	return c.route;
}

// Persistence -------------------------------------------------------------------
// Instant in this browser; debounced to the server so it follows the user.
let timer: number | undefined;
let pending: Record<string, unknown> = {};
function saveServer(patch: Record<string, unknown>) {
	if (import.meta.env.VITE_MOCK === "1") return;
	pending = { ...pending, ...patch };
	window.clearTimeout(timer);
	timer = window.setTimeout(() => {
		const body = pending;
		pending = {};
		call("thinknxg_admin.api.centers.save_preferences", body).catch(() => {
			/* a convenience; the local copy still works */
		});
	}, 1500);
}

watch(
	() => [centers.last, JSON.stringify(centers.state)],
	() => {
		writePref("centers", { last: centers.last, state: centers.state });
		saveServer({ last_center: centers.last || "", state: JSON.stringify(centers.state) });
	},
);

export async function setDefaultCenter(key: CenterKey | null) {
	if (!boot.data) return;
	if (import.meta.env.VITE_MOCK !== "1") {
		const prefs = (await call("thinknxg_admin.api.centers.save_preferences", { default_center: key || "" })) as Preferences;
		boot.data.preferences = prefs;
	} else {
		boot.data.preferences.default_center = key;
	}
	boot.data.default_center = key || boot.data.centers[0]?.key || null;
}

// Track the center and the page inside it as the user moves around.
router.afterEach((to) => {
	const key = centerForPath(to.path);
	if (!key || !getCenter(key)) return;
	centers.last = key;
	stateFor(key).last_route = to.fullPath.length <= 140 ? to.fullPath : to.path;
});
