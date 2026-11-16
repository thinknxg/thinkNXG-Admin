import { ref, watch } from "vue";
import { call } from "frappe-ui";

export type ThemeMode = "light" | "dark" | "system";
const DESK_VALUE: Record<ThemeMode, string> = { light: "Light", dark: "Dark", system: "Automatic" };
const media = typeof window !== "undefined" ? window.matchMedia("(prefers-color-scheme: dark)") : null;

function stored(): ThemeMode {
	try {
		return (localStorage.getItem("nxg:theme") as ThemeMode) || "system";
	} catch {
		return "system";
	}
}

export const themeMode = ref<ThemeMode>(stored());
export const isDark = ref(false);

function apply() {
	isDark.value = themeMode.value === "dark" || (themeMode.value === "system" && !!media?.matches);
	document.documentElement.setAttribute("data-theme", isDark.value ? "dark" : "light");
}
media?.addEventListener("change", apply);
apply();

watch(themeMode, (mode) => {
	try {
		localStorage.setItem("nxg:theme", mode);
	} catch {
		/* ignore */
	}
	apply();
});

/** Also saved to User.desk_theme through Core's own whitelisted method, so the
 *  classic Desk follows the same choice. */
export function setTheme(mode: ThemeMode, persist = true) {
	themeMode.value = mode;
	if (persist) call("frappe.core.doctype.user.user.switch_theme", { theme: DESK_VALUE[mode] }).catch(() => {});
}

export function initThemeFromUser(deskTheme?: string) {
	try {
		if (localStorage.getItem("nxg:theme")) return;
	} catch {
		/* ignore */
	}
	const map: Record<string, ThemeMode> = { Light: "light", Dark: "dark", Automatic: "system" };
	if (deskTheme && map[deskTheme]) setTheme(map[deskTheme], false);
}
