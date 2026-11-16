import { createApp } from "vue";
import { frappeRequest, setConfig } from "frappe-ui";
import "./styles/main.css";
import App from "./App.vue";
import { router } from "./router";
import { installLinkInterceptor, internalHref, toInternal } from "./lib/links";
import { boot, loadBoot } from "./data/boot";
import { shell } from "./data/shell";
import { initCenters } from "./data/centers";
import { initThemeFromUser } from "./composables/useTheme";

async function start() {
	// Local preview only: replaced by a constant at build time, so the sample
	// data module is never part of the production bundle.
	if (import.meta.env.VITE_MOCK === "1") {
		await import("./dev/mock");
	}
	setConfig("resourceFetcher", frappeRequest);

	await loadBoot();
	if (boot.data) {
		initThemeFromUser(boot.data.user.theme);
		const names = boot.data.companies.map((c) => c.name);
		if (shell.company && !names.includes(shell.company)) shell.company = null;
		initCenters();
	}
	installLinkInterceptor(router);
	const app = createApp(App);
	// $href(any address) in templates: the internal thinkNXG address for old Desk
	// links, so even hover and "open in new tab" stay inside the Command Center.
	app.config.globalProperties.$href = (href: string) => {
		const internal = toInternal(href);
		return internal ? internalHref(internal) : href;
	};
	if (boot.data) {
		(window as any).__nxgRoles = boot.data.user.roles;
		(window as any).__nxgUser = boot.data.user.name;
	}
	app.use(router).mount("#app");
}
start();
