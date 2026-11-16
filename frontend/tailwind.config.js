import frappeUIPreset from "frappe-ui/tailwind";
import { content as frappeUIContent } from "frappe-ui/tailwind";

/** thinkNXG tokens are CSS variables (src/styles/tokens.css) so light and dark
 *  themes switch with one attribute: <html data-theme="dark">. */
const v = (name) => `var(--nxg-${name})`;

/** @type {import('tailwindcss').Config} */
export default {
	presets: [frappeUIPreset],
	content: ["./index.html", "./src/**/*.{vue,js,ts}", ...(frappeUIContent || [])],
	theme: {
		extend: {
			fontFamily: { sans: ['InterVar', "Inter", "system-ui", "sans-serif"] },
			colors: {
				nxg: {
					espresso: v("brand-espresso"),
					ink: v("brand-ink"),
					red: v("brand-red"),
					"red-strong": v("brand-red-strong"),
					bg: v("bg"),
					surface: v("surface"),
					"surface-2": v("surface-2"),
					border: v("border"),
					"border-strong": v("border-strong"),
					text: v("text"),
					"text-2": v("text-2"),
					"text-3": v("text-3"),
					"sb-bg": v("sidebar-bg"),
					"sb-text": v("sidebar-text"),
					"sb-muted": v("sidebar-muted"),
					"sb-hover": v("sidebar-hover"),
					success: v("success"),
					warning: v("warning"),
					danger: v("danger"),
					info: v("info"),
					primary: v("primary"),
					"primary-fg": v("primary-fg"),
					"primary-hover": v("primary-hover"),
				},
			},
			borderRadius: { "nxg-sm": "6px", nxg: "8px", "nxg-lg": "12px" },
			boxShadow: { e1: v("shadow-e1"), e2: v("shadow-e2"), e3: v("shadow-e3") },
		},
	},
};
