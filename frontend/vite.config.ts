import fs from "node:fs";
import path from "node:path";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// Inside a bench, thinkNXG Core's shared library lives at apps/frappe/ui.
// It is wired here so Phase 6 screens (ListView, Filter, InviteUser) can import
// "@framework/ui"; the shell and Command Center do not depend on it.
const frameworkUiPath = path.resolve(__dirname, "../../frappe/ui");
const hasFrameworkUi = fs.existsSync(path.join(frameworkUiPath, "package.json"));

export default defineConfig(async () => {
	const plugins = [vue()];
	const alias: Record<string, string> = { "@": path.resolve(__dirname, "src") };
	if (hasFrameworkUi) {
		const { default: frameworkUI } = await import(path.join(frameworkUiPath, "vite/index.js"));
		plugins.push(...frameworkUI());
		alias["@framework/ui"] = path.join(frameworkUiPath, "src");
	}
	return {
		plugins,
		resolve: { alias, dedupe: ["vue", "vue-router", "frappe-ui"] },
		server: {
			port: 8090,
			proxy: { "^/(api|assets|files|private)": { target: process.env.FRAPPE_URL || "http://127.0.0.1:8000", changeOrigin: true } },
		},
		build: {
			outDir: "../thinknxg_admin/public/frontend",
			emptyOutDir: true,
			target: "es2020",
			chunkSizeWarningLimit: 1200,
		},
	};
});
