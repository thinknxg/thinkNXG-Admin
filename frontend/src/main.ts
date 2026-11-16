import { createApp } from "vue";
import { frappeRequest, setConfig } from "frappe-ui";
import "./styles/main.css";
import App from "./App.vue";
import { router } from "./router";
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
	createApp(App).use(router).mount("#app");
}
start();
