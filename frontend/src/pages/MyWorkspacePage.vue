<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { call, toast } from "frappe-ui";
import NxgPanel from "@/components/ui/NxgPanel.vue";
import NxgAvatar from "@/components/ui/NxgAvatar.vue";
import NxgDrawer from "@/components/ui/NxgDrawer.vue";
import Icon from "@/components/ui/Icon.vue";
import { errorMessage, runAction, usePanel } from "@/data/api";
import { boot } from "@/data/boot";
import { favorites, recent } from "@/composables/useRecent";
import { setTheme, themeMode, type ThemeMode } from "@/composables/useTheme";
import { fmtDateTime, timeAgo } from "@/composables/format";

const API = "thinknxg_admin.api.my_workspace.";
const ws = usePanel<any>(API + "get_my_workspace");
const d = computed(() => ws.state.data || {});
const hour = new Date().getHours();
const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
const firstName = computed(() => (d.value.user?.full_name || boot.data?.user.full_name || "").split(" ")[0]);
const todayLabel = new Date().toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" });

const closing = ref<Set<string>>(new Set());
async function done(t: any) {
	closing.value = new Set([...closing.value, t.name]);
	try {
		await call(API + "set_todo_status", { name: t.name, status: "Closed" });
		ws.state.data.todos = ws.state.data.todos.filter((x: any) => x.name !== t.name);
		toast.success("Task done", { action: { label: "Undo", onClick: () => undo(t) } } as any);
	} catch (e) {
		toast.error(errorMessage(e));
	} finally {
		closing.value.delete(t.name);
	}
}
async function undo(t: any) {
	if (await runAction(API + "set_todo_status", { name: t.name, status: "Open" })) ws.load(true);
}
const overdue = computed(() => (d.value.todos || []).filter((t: any) => t.overdue).length);
const prioTone: Record<string, string> = { High: "text-nxg-danger", Medium: "text-nxg-text-2", Low: "text-nxg-text-3" };

// Preferences (own account)
const prefsOpen = ref(false);
const prefOptions = ref<any>(null);
const prefs = reactive({ language: "", time_zone: "", default_workspace: "", default_app: "" });
watch(() => d.value.preferences, (p) => p && Object.assign(prefs, { language: p.language || "", time_zone: p.time_zone || "", default_workspace: p.default_workspace || "", default_app: p.default_app || "" }), { immediate: true });
async function openPrefs() {
	prefsOpen.value = true;
	if (!prefOptions.value) {
		try {
			prefOptions.value = await call(API + "get_preference_options");
		} catch (e) {
			toast.error(errorMessage(e));
		}
	}
}
async function savePrefs() {
	if (await runAction(API + "update_my_preferences", { values: { ...prefs } }, "Preferences saved")) {
		prefsOpen.value = false;
		ws.load(true);
	}
}
const themes: { mode: ThemeMode; label: string; icon: string }[] = [{ mode: "light", label: "Light", icon: "sun" }, { mode: "dark", label: "Dark", icon: "moon" }, { mode: "system", label: "System", icon: "monitor" }];
const shortcuts = computed(() => [...favorites.value, ...recent.value.filter((r) => !favorites.value.some((f) => f.route === r.route))].slice(0, 8));
function go(route: string) {
	if (route.startsWith("/desk") || route.startsWith("http")) window.location.href = route;
	else window.location.href = "/thinknxg" + (route === "/" ? "" : route);
}
</script>

<template>
	<div class="mx-auto w-full max-w-[1320px] px-4 pb-10 pt-6 sm:px-6">
		<div class="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
			<div class="flex items-center gap-4">
				<NxgAvatar :name="d.user?.full_name || boot.data?.user.full_name" :image="d.user?.image || boot.data?.user.image" :size="52" />
				<div>
					<p class="text-[12.5px] font-medium text-nxg-text-2">{{ todayLabel }}</p>
					<h1 class="text-[24px] font-semibold leading-8 tracking-[-0.02em]">{{ greeting }}{{ firstName ? `, ${firstName}` : "" }}</h1>
					<p class="text-[13.5px] text-nxg-text-2">
						<template v-if="ws.state.data">{{ d.todos.length }} open task{{ d.todos.length === 1 ? "" : "s" }}<span v-if="overdue" class="text-nxg-danger"> ({{ overdue }} overdue)</span> · {{ d.approvals.length }} approval{{ d.approvals.length === 1 ? "" : "s" }} waiting<span v-if="d.unread_notifications"> · {{ d.unread_notifications }} unread notification{{ d.unread_notifications === 1 ? "" : "s" }}</span></template>
						<template v-else>Loading your day…</template>
					</p>
				</div>
			</div>
			<div class="flex flex-wrap gap-2">
				<a v-if="d.preferences?.default_workspace" :href="`/desk/${d.preferences.default_workspace.toLowerCase().replace(/ /g, '-')}`" class="nxg-btn nxg-btn-primary"><Icon name="panels-top-left" :size="14" />Open {{ d.preferences.default_workspace }}</a>
				<button class="nxg-btn nxg-btn-secondary" @click="openPrefs"><Icon name="settings" :size="14" />Preferences</button>
			</div>
		</div>

		<div v-if="ws.state.error" class="nxg-panel mb-4 p-4 text-[13px] text-nxg-danger">{{ ws.state.error }} <button class="nxg-btn nxg-btn-secondary ml-2 h-7" @click="ws.load(true)">Retry</button></div>

		<div class="grid grid-cols-1 gap-4 xl:grid-cols-3">
			<NxgPanel class="xl:col-span-2" title="My tasks" :subtitle="d.todos ? `${d.todos.length} open, assigned to you` : ''" :loading="ws.state.loading && !ws.state.data" :empty="!!ws.state.data && !d.todos.length" empty-text="No open tasks. Nice." href="/desk/todo?status=Open" href-label="All tasks" :skeleton-rows="6">
				<ul class="divide-y divide-nxg-border">
					<li v-for="t in d.todos" :key="t.name" class="group flex items-start gap-3 py-2.5" :class="closing.has(t.name) && 'opacity-50'">
						<button class="mt-0.5 flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-full border border-nxg-border-strong text-transparent transition-colors hover:border-nxg-success hover:text-nxg-success" :aria-label="`Mark done: ${t.description}`" :disabled="closing.has(t.name)" @click="done(t)"><Icon name="check" :size="12" :stroke-width="2.5" /></button>
						<a :href="t.route" class="min-w-0 flex-1">
							<span class="block text-[13.5px] leading-5 group-hover:underline">{{ t.description || t.name }}</span>
							<span class="mt-0.5 flex flex-wrap items-center gap-x-2 text-[12px] text-nxg-text-2">
								<span v-if="t.reference_type">{{ t.reference_type }} {{ t.reference_name }}</span>
								<span v-if="t.assigned_by_full_name">from {{ t.assigned_by_full_name }}</span>
								<span :class="prioTone[t.priority]">{{ t.priority }} priority</span>
							</span>
						</a>
						<span v-if="t.date" class="shrink-0 text-[12px]" :class="t.overdue ? 'font-medium text-nxg-danger' : 'text-nxg-text-2'">{{ t.overdue ? "Overdue · " : "Due " }}{{ new Date(t.date + "T00:00:00").toLocaleDateString(undefined, { day: "numeric", month: "short" }) }}</span>
					</li>
				</ul>
			</NxgPanel>

			<NxgPanel title="Waiting for your approval" :subtitle="d.approvals ? `${d.approvals.length} document${d.approvals.length === 1 ? '' : 's'}` : ''" :loading="ws.state.loading && !ws.state.data" :empty="!!ws.state.data && !d.approvals.length" empty-text="Nothing waiting for you" :skeleton-rows="5">
				<ul class="space-y-1.5">
					<li v-for="a in d.approvals" :key="a.name"><a :href="a.route" class="flex items-center gap-2.5 rounded-nxg border border-nxg-border px-3 py-2 hover:border-nxg-border-strong"><Icon name="circle-check" :size="15" class="text-nxg-text-2" /><span class="min-w-0 flex-1"><span class="block truncate text-[13px] font-medium">{{ a.reference_doctype }} {{ a.reference_name }}</span><span class="block truncate text-[12px] text-nxg-text-2">{{ a.workflow_state }} · {{ timeAgo(a.creation) }}</span></span><Icon name="chevron-right" :size="14" class="text-nxg-text-3" /></a></li>
				</ul>
			</NxgPanel>

			<NxgPanel title="My workspaces" subtitle="Workspaces your roles can open" :loading="ws.state.loading && !ws.state.data" :empty="!!ws.state.data && !d.workspaces.length" empty-text="No workspaces available to your roles" :skeleton-rows="5">
				<div class="grid grid-cols-2 gap-2">
					<a v-for="w in d.workspaces" :key="w.name" :href="w.route" class="flex items-center gap-2 rounded-nxg border border-nxg-border px-2.5 py-2 text-[13px] hover:border-nxg-border-strong hover:bg-nxg-surface-2" :class="d.preferences?.default_workspace === w.name && 'ring-1 ring-nxg-border-strong'"><Icon name="panels-top-left" :size="14" class="text-nxg-text-2" /><span class="truncate">{{ w.label || w.name }}</span></a>
				</div>
			</NxgPanel>

			<NxgPanel title="Pick up where you left off" subtitle="Records you changed recently" :loading="ws.state.loading && !ws.state.data" :empty="!!ws.state.data && !d.recent.length" empty-text="No recent changes" :skeleton-rows="5">
				<ul class="divide-y divide-nxg-border">
					<li v-for="r in d.recent" :key="r.ref_doctype + r.docname"><a :href="r.route" class="flex items-center justify-between gap-2 py-1.5 text-[13px] hover:underline"><span class="min-w-0 truncate"><span class="text-nxg-text-2">{{ r.ref_doctype }}</span> · {{ r.docname }}</span><span class="shrink-0 text-[12px] text-nxg-text-3" :title="fmtDateTime(r.creation)">{{ timeAgo(r.creation) }}</span></a></li>
				</ul>
			</NxgPanel>

			<NxgPanel title="Shortcuts" subtitle="Favourites and recently opened pages" :empty="!shortcuts.length && !(d.visited || []).length" empty-text="Star pages and reports to pin them here">
				<div v-if="shortcuts.length" class="mb-3 flex flex-wrap gap-1.5">
					<button v-for="s in shortcuts" :key="s.route" class="inline-flex h-7 items-center gap-1.5 rounded-nxg-sm border border-nxg-border px-2 text-[12.5px] hover:border-nxg-border-strong" @click="go(s.route)"><Icon :name="s.icon || 'star'" :size="13" class="text-nxg-text-2" />{{ s.label }}</button>
				</div>
				<div v-if="d.visited?.length">
					<div class="mb-1 nxg-micro">Recently visited in Desk</div>
					<ul class="divide-y divide-nxg-border"><li v-for="v in d.visited" :key="v.route"><a :href="v.route" class="flex items-center justify-between gap-2 py-1.5 text-[13px] hover:underline"><span class="truncate">{{ v.label }}</span><span class="shrink-0 text-[12px] text-nxg-text-3">{{ timeAgo(v.creation) }}</span></a></li></ul>
				</div>
			</NxgPanel>
		</div>

		<NxgDrawer :open="prefsOpen" title="Preferences" subtitle="Your account only" width="max-w-[480px]" @close="prefsOpen = false">
			<div class="space-y-4 p-5">
				<div>
					<label class="nxg-label">Theme</label>
					<div class="grid grid-cols-3 gap-2"><button v-for="t in themes" :key="t.mode" class="flex h-16 flex-col items-center justify-center gap-1 rounded-nxg border text-[12.5px]" :class="themeMode === t.mode ? 'border-nxg-text font-medium' : 'border-nxg-border hover:border-nxg-border-strong'" :aria-pressed="themeMode === t.mode" @click="setTheme(t.mode)"><Icon :name="t.icon" :size="17" />{{ t.label }}</button></div>
				</div>
				<div><label class="nxg-label" for="pref-lang">Language</label><select id="pref-lang" v-model="prefs.language" class="nxg-input"><option value="">Site default</option><option v-for="l in prefOptions?.languages || []" :key="l.name" :value="l.name">{{ l.language_name || l.name }}</option></select></div>
				<div><label class="nxg-label" for="pref-tz">Time zone</label><select id="pref-tz" v-model="prefs.time_zone" class="nxg-input"><option value="">Site default</option><option v-for="z in prefOptions?.time_zones || []" :key="z">{{ z }}</option></select></div>
				<div><label class="nxg-label" for="pref-ws">Default workspace</label><select id="pref-ws" v-model="prefs.default_workspace" class="nxg-input"><option value="">Not set</option><option v-for="w in d.workspaces || []" :key="w.name" :value="w.name">{{ w.label || w.name }}</option></select></div>
				<div><label class="nxg-label" for="pref-app">Default app after sign-in</label><select id="pref-app" v-model="prefs.default_app" class="nxg-input"><option value="">Not set</option><option v-for="a in boot.data?.apps || []" :key="a.app" :value="a.app">{{ a.title }}</option></select></div>
				<div class="rounded-nxg border border-nxg-border p-3 text-[12.5px] text-nxg-text-2">Password, two-factor and API keys are on your <a :href="`/desk/user/${encodeURIComponent(boot.data?.user.name || '')}`" class="nxg-link">user record</a>. Notification preferences are in the <RouterLink to="/notifications" class="nxg-link">Notification Center</RouterLink>.</div>
			</div>
			<template #footer><button class="nxg-btn nxg-btn-secondary" @click="prefsOpen = false">Cancel</button><button class="nxg-btn nxg-btn-primary" @click="savePrefs">Save</button></template>
		</NxgDrawer>
	</div>
</template>
