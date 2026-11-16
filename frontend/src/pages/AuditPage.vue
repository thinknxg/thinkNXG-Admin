<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { call } from "frappe-ui";
import PageHeader from "@/components/ui/PageHeader.vue";
import NxgAvatar from "@/components/ui/NxgAvatar.vue";
import NxgStatus from "@/components/ui/NxgStatus.vue";
import NxgEmpty from "@/components/ui/NxgEmpty.vue";
import Icon from "@/components/ui/Icon.vue";
import { downloadCsv, errorMessage, runAction, usePanel } from "@/data/api";
import { readPref, writePref } from "@/composables/storage";
import { fmtDateTime, fmtNumber, timeAgo } from "@/composables/format";

const API = "thinknxg_admin.api.audit.";
const iso = (d: Date) => d.toISOString().slice(0, 10);
const f = reactive(readPref("audit-filters", { category: "", user: "", result: "", search: "", from_date: iso(new Date(Date.now() - 29 * 86400000)), to_date: iso(new Date()) }));
const start = ref(0);
const PAGE = 50;
const rows = ref<any[]>([]);
const hasMore = ref(false);
const capped = ref(false);
const loading = ref(false);
const error = ref<string | null>(null);
const expanded = ref<Set<string>>(new Set());

const summary = usePanel<any>(API + "get_summary", () => ({ from_date: f.from_date, to_date: f.to_date }));

let t: number | undefined;
async function load() {
	loading.value = true;
	error.value = null;
	try {
		const res: any = await call(API + "get_events", { ...f, start: start.value, page_length: PAGE });
		rows.value = res.rows;
		hasMore.value = res.has_more;
		capped.value = res.window_capped;
	} catch (e) {
		error.value = errorMessage(e);
	} finally {
		loading.value = false;
	}
}
watch(() => ({ ...f }), (v) => {
	writePref("audit-filters", v);
	start.value = 0;
	window.clearTimeout(t);
	t = window.setTimeout(load, 300);
}, { deep: true, immediate: true });
watch(start, load);

const categories = [
	{ key: "", label: "All administration", icon: "scroll-text" },
	{ key: "authentication", label: "Sign-ins", icon: "key-round" },
	{ key: "permissions", label: "Permissions", icon: "shield-check" },
	{ key: "access_control", label: "Users & roles", icon: "users" },
	{ key: "configuration", label: "Configuration", icon: "sliders-horizontal" },
	{ key: "data_access", label: "Data exports", icon: "file-text" },
	{ key: "documents", label: "Documents", icon: "layers" },
	{ key: "api", label: "API access", icon: "plug" },
];
const catLabel = Object.fromEntries(categories.map((c) => [c.key, c.label]));
const presets = [
	{ label: "24 h", days: 1 },
	{ label: "7 days", days: 7 },
	{ label: "30 days", days: 30 },
	{ label: "90 days", days: 90 },
];
function preset(days: number) {
	f.from_date = iso(new Date(Date.now() - (days - 1) * 86400000));
	f.to_date = iso(new Date());
}
function toggle(id: string) {
	const s = new Set(expanded.value);
	s.has(id) ? s.delete(id) : s.add(id);
	expanded.value = s;
}
const tiles = computed(() => {
	const s = summary.state.data || {};
	return [
		{ label: "Sign-ins", value: s.logins, cat: "authentication" },
		{ label: "Failed sign-ins", value: s.failed_logins, cat: "authentication", warn: true, result: "failed" },
		{ label: "Permission changes", value: s.permission_changes, cat: "permissions" },
		{ label: "User & role changes", value: s.access_changes, cat: "access_control" },
		{ label: "Configuration changes", value: s.config_changes, cat: "configuration" },
		{ label: "Data exports", value: s.exports, cat: "data_access" },
	];
});
function applyTile(tile: any) {
	f.category = tile.cat;
	f.result = tile.result || "";
}

async function exportCsv() {
	const events: any[] | undefined = await runAction(API + "export_events", { category: f.category, user: f.user, result: f.result, from_date: f.from_date, to_date: f.to_date });
	if (!events) return;
	downloadCsv(`audit-${f.from_date}-to-${f.to_date}.csv`, ["Timestamp", "Category", "Actor", "Action", "Resource type", "Resource", "Result", "IP", "Changes", "Source"],
		events.map((e) => [e.timestamp, catLabel[e.category] || e.category, e.actor, e.action, e.resource_type, e.resource, e.result, e.ip, (e.changes || []).map((c: any) => `${c.field}: ${c.old ?? ""} -> ${c.new ?? ""}`).join(" | "), e.source]));
}
</script>

<template>
	<div class="mx-auto w-full max-w-[1480px] px-4 pb-10 pt-6 sm:px-6">
		<PageHeader title="Audit & Compliance" description="One timeline over the framework's own audit records: sign-ins, permission and role changes, configuration history, exports and API access.">
			<button class="nxg-btn nxg-btn-secondary" @click="exportCsv"><Icon name="file-text" :size="14" />Export CSV</button>
		</PageHeader>

		<div class="mb-4 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
			<button v-for="tile in tiles" :key="tile.label" class="nxg-panel px-3.5 py-3 text-left transition-colors hover:border-nxg-border-strong" @click="applyTile(tile)">
				<div class="truncate text-[12px] text-nxg-text-2">{{ tile.label }}</div>
				<div v-if="summary.state.loading && !summary.state.data" class="nxg-skeleton mt-1 h-6 w-12" />
				<div v-else class="nxg-tnum text-[20px] font-semibold" :class="[tile.value === null || tile.value === undefined ? 'text-[13px] font-medium text-nxg-text-3' : '', tile.warn && tile.value ? 'text-nxg-warning' : '']">{{ tile.value === null || tile.value === undefined ? "Not available" : fmtNumber(tile.value) }}</div>
			</button>
		</div>
		<div v-if="summary.state.data && (summary.state.data.top_failed_users?.length || summary.state.data.top_failed_ips?.length)" class="mb-4 flex flex-wrap gap-x-8 gap-y-2 rounded-nxg border border-nxg-border bg-nxg-surface px-4 py-2.5 text-[12.5px]">
			<span v-if="summary.state.data.top_failed_users?.length"><b class="mr-1">Most failed sign-ins:</b><button v-for="u in summary.state.data.top_failed_users" :key="u.user" class="mr-2 text-nxg-text-2 hover:text-nxg-text hover:underline" @click="Object.assign(f, { user: u.user, category: 'authentication', result: 'failed' })">{{ u.user }} ({{ u.n }})</button></span>
			<span v-if="summary.state.data.top_failed_ips?.length"><b class="mr-1">By IP:</b><button v-for="i in summary.state.data.top_failed_ips" :key="i.ip" class="nxg-tnum mr-2 text-nxg-text-2 hover:text-nxg-text hover:underline" @click="Object.assign(f, { search: i.ip, category: 'authentication', result: 'failed' })">{{ i.ip }} ({{ i.n }})</button></span>
		</div>

		<div class="nxg-panel">
			<div class="space-y-2 border-b border-nxg-border p-3">
				<div class="flex flex-wrap gap-1" role="group" aria-label="Category">
					<button v-for="c in categories" :key="c.key" class="inline-flex h-7 items-center gap-1.5 rounded-nxg-sm px-2.5 text-[12.5px] font-medium" :class="f.category === c.key ? 'bg-nxg-primary text-nxg-primary-fg' : 'text-nxg-text-2 hover:bg-nxg-surface-2'" @click="f.category = c.key"><Icon :name="c.icon" :size="13" />{{ c.label }}</button>
				</div>
				<div class="flex flex-wrap items-center gap-2">
					<div class="relative min-w-[200px] flex-1 sm:max-w-xs"><Icon name="search" :size="15" class="pointer-events-none absolute left-2.5 top-2 text-nxg-text-3" /><input v-model="f.search" class="nxg-input pl-8" placeholder="Search actor, action, resource, IP" aria-label="Search events" /></div>
					<input v-model="f.user" class="nxg-input w-52" placeholder="Actor (user email)" aria-label="Actor" />
					<select v-model="f.result" class="nxg-input w-auto" aria-label="Result"><option value="">Any result</option><option value="success">Success</option><option value="failed">Failed</option></select>
					<input v-model="f.from_date" type="date" class="nxg-input w-auto" aria-label="From date" />
					<span class="text-nxg-text-3">→</span>
					<input v-model="f.to_date" type="date" class="nxg-input w-auto" aria-label="To date" />
					<div class="flex gap-1"><button v-for="p in presets" :key="p.label" class="nxg-btn nxg-btn-ghost h-7 px-2 text-[12px]" @click="preset(p.days)">{{ p.label }}</button></div>
				</div>
				<p v-if="f.category === 'api' && summary.state.data?.api_logging_enabled === false" class="text-[12px] text-nxg-warning">API request logging is off in System Settings, so API calls are not being recorded.</p>
			</div>

			<div v-if="error" class="p-4 text-[13px] text-nxg-danger">{{ error }} <button class="nxg-btn nxg-btn-secondary ml-2 h-7" @click="load">Retry</button></div>
			<div v-else-if="loading && !rows.length" class="space-y-2 p-4"><div v-for="i in 8" :key="i" class="nxg-skeleton h-9" /></div>
			<NxgEmpty v-else-if="!rows.length" text="No events match these filters" icon="scroll-text" />
			<div v-else class="overflow-x-auto">
				<table class="w-full min-w-[900px] text-[13px]">
					<thead><tr class="border-b border-nxg-border"><th class="w-8" /><th class="px-3 py-2 text-left nxg-micro">When</th><th class="px-3 py-2 text-left nxg-micro">Actor</th><th class="px-3 py-2 text-left nxg-micro">Action</th><th class="px-3 py-2 text-left nxg-micro">Resource</th><th class="px-3 py-2 text-left nxg-micro">Category</th><th class="px-3 py-2 text-left nxg-micro">IP</th><th class="px-3 py-2 text-right nxg-micro">Result</th></tr></thead>
					<tbody :class="loading && 'opacity-60'">
						<template v-for="e in rows" :key="e.id">
							<tr class="border-b border-nxg-border hover:bg-nxg-surface-2/60" :class="e.changes?.length && 'cursor-pointer'" @click="e.changes?.length && toggle(e.id)">
								<td class="pl-3"><Icon v-if="e.changes?.length" :name="expanded.has(e.id) ? 'chevron-down' : 'chevron-right'" :size="14" class="text-nxg-text-3" /></td>
								<td class="whitespace-nowrap px-3 py-2 text-nxg-text-2" :title="fmtDateTime(e.timestamp)">{{ timeAgo(e.timestamp) }}</td>
								<td class="px-3 py-2"><span class="flex items-center gap-2"><NxgAvatar :name="e.actor_name" :size="22" /><span class="max-w-[170px] truncate">{{ e.actor_name || "—" }}</span></span></td>
								<td class="px-3 py-2">{{ e.action }}</td>
								<td class="px-3 py-2"><a :href="e.route" class="nxg-link block max-w-[260px] truncate" :title="`${e.resource_type}: ${e.resource}`" @click.stop><span class="text-nxg-text-2">{{ e.resource_type }}</span> · {{ e.resource }}</a></td>
								<td class="px-3 py-2"><span class="nxg-chip">{{ catLabel[e.category] }}</span></td>
								<td class="nxg-tnum px-3 py-2 text-nxg-text-2">{{ e.ip || "—" }}</td>
								<td class="px-3 py-2 text-right"><NxgStatus :status="e.result === 'Failed' ? 'failed' : 'success'" :label="e.result" /></td>
							</tr>
							<tr v-if="expanded.has(e.id)" class="border-b border-nxg-border bg-nxg-surface-2/40">
								<td />
								<td colspan="7" class="px-3 py-2.5">
									<table class="w-full max-w-[880px] text-[12.5px]">
										<thead><tr><th class="w-48 pb-1 text-left nxg-micro">Field</th><th class="pb-1 text-left nxg-micro">Previous value</th><th class="pb-1 text-left nxg-micro">New value</th></tr></thead>
										<tbody><tr v-for="(c, i) in e.changes" :key="i" class="align-top"><td class="py-0.5 pr-3 font-medium">{{ c.field }}</td><td class="py-0.5 pr-3 text-nxg-text-2"><span class="line-through decoration-nxg-border-strong">{{ c.old ?? "empty" }}</span></td><td class="py-0.5">{{ c.new ?? "empty" }}</td></tr></tbody>
									</table>
									<p class="mt-1.5 text-[11.5px] text-nxg-text-3">Source: {{ e.source }} · {{ fmtDateTime(e.timestamp) }}</p>
								</td>
							</tr>
						</template>
					</tbody>
				</table>
			</div>
			<div class="flex items-center justify-between gap-3 border-t border-nxg-border px-3 py-2.5 text-[12.5px] text-nxg-text-2">
				<span>{{ rows.length ? `Showing ${start + 1}–${start + rows.length}` : "" }}<span v-if="capped"> · narrow the date range to page beyond 2,000 events</span></span>
				<div class="flex gap-1">
					<button class="nxg-icon-btn h-7 w-7" :disabled="start === 0" aria-label="Previous page" @click="start = Math.max(0, start - PAGE)"><Icon name="chevron-right" :size="15" class="rotate-180" /></button>
					<button class="nxg-icon-btn h-7 w-7" :disabled="!hasMore" aria-label="Next page" @click="start += PAGE"><Icon name="chevron-right" :size="15" /></button>
				</div>
			</div>
		</div>
	</div>
</template>
