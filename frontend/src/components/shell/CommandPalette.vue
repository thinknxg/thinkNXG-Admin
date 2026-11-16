<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { call } from "frappe-ui";
import Icon from "@/components/ui/Icon.vue";
import { allNavItems, boot } from "@/data/boot";
import { shell } from "@/data/shell";
import { favorites, pushRecent, recent } from "@/composables/useRecent";
import { setTheme, isDark } from "@/composables/useTheme";
import { isExternal } from "@/composables/format";

interface Entry { id: string; group: string; label: string; description?: string; icon?: string; route?: string; run?: () => void }

const router = useRouter();
const query = ref("");
const active = ref(0);
const input = ref<HTMLInputElement | null>(null);
const remote = ref<Entry[]>([]);
const searching = ref(false);
let debounce: number | undefined;
let seq = 0;

watch(() => shell.paletteOpen, async (open) => {
	if (open) {
		query.value = "";
		remote.value = [];
		active.value = 0;
		await nextTick();
		input.value?.focus();
	}
});

watch(query, (q) => {
	active.value = 0;
	window.clearTimeout(debounce);
	if (q.trim().length < 2) {
		remote.value = [];
		searching.value = false;
		return;
	}
	searching.value = true;
	debounce = window.setTimeout(async () => {
		const mine = ++seq;
		try {
			const rows: any[] = await call("thinknxg_admin.api.search.search", { query: q.trim(), limit: 6 });
			if (mine !== seq) return;
			remote.value = rows.map((r, i) => ({ id: `r${i}${r.route}`, group: r.type === "DocType" ? "DocTypes" : r.type + "s", label: r.label, description: r.description, icon: r.icon, route: r.route }));
		} catch {
			if (mine === seq) remote.value = [];
		} finally {
			if (mine === seq) searching.value = false;
		}
	}, 180);
});

const actions = computed<Entry[]>(() => {
	const b = boot.data!;
	const list: Entry[] = [
		{ id: "a-theme", group: "Actions", label: isDark.value ? "Switch to light theme" : "Switch to dark theme", icon: isDark.value ? "sun" : "moon", run: () => setTheme(isDark.value ? "light" : "dark") },
		{ id: "a-shortcuts", group: "Actions", label: "Show keyboard shortcuts", icon: "command", run: () => (shell.shortcutsOpen = true) },
	];
	if (b.quick_create.some((q) => q.doctype === "User")) list.push({ id: "a-invite", group: "Actions", label: "Invite a user", icon: "users", route: "/desk/user-invitation/new" });
	for (const q of b.quick_create) list.push({ id: "a-new-" + q.doctype, group: "Actions", label: `New ${q.doctype}`, icon: q.icon, route: q.route });
	if (b.show_classic_desk_link) list.push({ id: "a-desk", group: "Actions", label: "Open classic Desk", icon: "monitor", route: "/desk" });
	return list;
});

const entries = computed<Entry[]>(() => {
	const q = query.value.trim().toLowerCase();
	const pages: Entry[] = allNavItems().map((i) => ({ id: "p-" + i.key, group: "Pages", label: i.label, description: i.status === "planned" ? "Planned" : undefined, icon: i.icon || "file-text", route: i.route }));
	if (!q) {
		const fav = favorites.value.map((f) => ({ id: "f-" + f.route, group: "Favorites", label: f.label, icon: f.icon || "star", route: f.route }));
		const rec = recent.value.map((r) => ({ id: "r-" + r.route, group: "Recent", label: r.label, icon: r.icon || "clock", route: r.route }));
		return [...fav, ...rec, ...pages.slice(0, 8), ...actions.value.slice(0, 4)];
	}
	const match = (e: Entry) => e.label.toLowerCase().includes(q) || (e.description || "").toLowerCase().includes(q);
	return [...pages.filter(match), ...actions.value.filter(match), ...remote.value];
});

const groups = computed(() => {
	const out: { name: string; items: (Entry & { index: number })[] }[] = [];
	entries.value.forEach((e, index) => {
		let g = out.find((x) => x.name === e.group);
		if (!g) out.push((g = { name: e.group, items: [] }));
		g.items.push({ ...e, index });
	});
	return out;
});

function choose(e?: Entry) {
	if (!e) return;
	shell.paletteOpen = false;
	if (e.run) return e.run();
	if (!e.route) return;
	pushRecent({ label: e.label, route: e.route, icon: e.icon });
	if (isExternal(e.route)) window.location.href = e.route;
	else router.push(e.route);
}

function onKey(ev: KeyboardEvent) {
	const n = entries.value.length;
	if (ev.key === "ArrowDown") {
		ev.preventDefault();
		active.value = n ? (active.value + 1) % n : 0;
		scrollActive();
	} else if (ev.key === "ArrowUp") {
		ev.preventDefault();
		active.value = n ? (active.value - 1 + n) % n : 0;
		scrollActive();
	} else if (ev.key === "Enter") {
		ev.preventDefault();
		choose(entries.value[active.value]);
	} else if (ev.key === "Escape") {
		shell.paletteOpen = false;
	}
}
function scrollActive() {
	nextTick(() => document.querySelector(`[data-pal="${active.value}"]`)?.scrollIntoView({ block: "nearest" }));
}
</script>

<template>
	<Teleport to="body">
		<transition enter-active-class="transition duration-150" enter-from-class="opacity-0" leave-active-class="transition duration-100" leave-to-class="opacity-0">
			<div v-if="shell.paletteOpen" class="fixed inset-0 z-[60] flex items-start justify-center bg-[rgba(28,10,8,0.45)] px-3 pt-[12vh] backdrop-blur-[2px]" @mousedown.self="shell.paletteOpen = false">
				<div role="dialog" aria-modal="true" aria-label="Command palette" class="w-full max-w-[620px] overflow-hidden rounded-nxg-lg border border-nxg-border bg-nxg-surface shadow-e3">
					<div class="flex items-center gap-2.5 border-b border-nxg-border px-4">
						<Icon name="search" :size="17" class="text-nxg-text-3" />
						<input
							ref="input"
							v-model="query"
							class="h-12 flex-1 border-0 bg-transparent p-0 text-[15px] text-nxg-text placeholder:text-nxg-text-3 focus:ring-0"
							placeholder="Search pages, users, DocTypes, reports, workspaces…"
							aria-label="Search"
							role="combobox"
							aria-expanded="true"
							:aria-activedescendant="`pal-${active}`"
							@keydown="onKey"
						/>
						<Icon v-if="searching" name="refresh-cw" :size="15" class="animate-spin text-nxg-text-3" />
						<kbd class="rounded-1 border border-nxg-border px-1.5 text-[11px] text-nxg-text-2">Esc</kbd>
					</div>
					<div class="nxg-scroll max-h-[min(440px,60vh)] overflow-y-auto p-1.5" role="listbox">
						<div v-if="!entries.length && !searching" class="px-3 py-8 text-center text-[13px] text-nxg-text-2">No results for "{{ query }}"</div>
						<div v-for="g in groups" :key="g.name" class="mb-1">
							<div class="px-2.5 pb-1 pt-2 nxg-micro">{{ g.name }}</div>
							<button
								v-for="e in g.items"
								:id="`pal-${e.index}`"
								:key="e.id"
								:data-pal="e.index"
								role="option"
								:aria-selected="active === e.index"
								class="flex h-9 w-full items-center gap-2.5 rounded-nxg px-2.5 text-left text-[13.5px]"
								:class="active === e.index ? 'bg-nxg-surface-2 text-nxg-text' : 'text-nxg-text'"
								@mousemove="active = e.index"
								@click="choose(e)"
							>
								<Icon :name="e.icon" :size="15" class="text-nxg-text-2" />
								<span class="min-w-0 flex-1 truncate">{{ e.label }}</span>
								<span v-if="e.description" class="max-w-[40%] truncate text-[12px] text-nxg-text-3">{{ e.description }}</span>
								<Icon v-if="e.route && isExternal(e.route)" name="external-link" :size="13" class="text-nxg-text-3" />
							</button>
						</div>
					</div>
					<div class="flex items-center gap-4 border-t border-nxg-border bg-nxg-surface-2/50 px-4 py-2 text-[11.5px] text-nxg-text-2">
						<span><kbd class="font-medium">↑↓</kbd> navigate</span><span><kbd class="font-medium">↵</kbd> open</span><span class="ml-auto">Results respect your permissions</span>
					</div>
				</div>
			</div>
		</transition>
	</Teleport>
</template>
