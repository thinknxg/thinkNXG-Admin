import { reactive, watch } from "vue";
import { readPref, writePref } from "@/composables/storage";

export const shell = reactive({
	collapsed: readPref<boolean>("sidebar-collapsed", false),
	mobileOpen: false,
	paletteOpen: false,
	shortcutsOpen: false,
	company: readPref<string | null>("company", null),
	days: readPref<number>("days", 30),
});

watch(() => shell.collapsed, (v) => writePref("sidebar-collapsed", v));
watch(() => shell.company, (v) => writePref("company", v));
watch(() => shell.days, (v) => writePref("days", v));
