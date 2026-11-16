<script setup lang="ts">
import { nav } from "@/lib/links";
import { computed, reactive, ref } from "vue";
import PageHeader from "@/components/ui/PageHeader.vue";
import NxgTabs from "@/components/ui/NxgTabs.vue";
import DataTable from "@/components/ui/DataTable.vue";
import NxgSwitch from "@/components/ui/NxgSwitch.vue";
import NxgEmpty from "@/components/ui/NxgEmpty.vue";
import Icon from "@/components/ui/Icon.vue";
import { runAction, usePanel } from "@/data/api";
import { isFavorite, toggleFavorite, pushRecent } from "@/composables/useRecent";
import { readPref, writePref } from "@/composables/storage";
import { timeAgo } from "@/composables/format";

const API = "thinknxg_admin.api.reports.";
const f = reactive(readPref("reports-filters", { search: "", module: "", type: "", disabled: false, favouritesOnly: false }));
const cat = usePanel<any>(API + "get_catalog", () => ({ include_disabled: f.disabled ? 1 : 0 }));
const tab = ref("reports");
const d = computed(() => cat.state.data || {});
const types = ["Report Builder", "Query Report", "Script Report", "Custom Report"];

const reports = computed(() => {
	writePref("reports-filters", { ...f });
	const q = f.search.toLowerCase();
	return (d.value.reports || []).filter((r: any) =>
		(!q || `${r.name} ${r.ref_doctype || ""} ${r.module || ""}`.toLowerCase().includes(q)) &&
		(!f.module || r.module === f.module) && (!f.type || r.report_type === f.type) &&
		(!f.favouritesOnly || isFavorite(r.route)));
});
const popular = computed(() => [...(d.value.reports || [])].filter((r: any) => r.exports_30d || r.my_opens).sort((a: any, b: any) => b.my_opens * 3 + b.exports_30d - (a.my_opens * 3 + a.exports_30d)).slice(0, 6));
function open(r: any) {
	pushRecent({ label: r.name, route: r.route, icon: "chart-column", external: true });
	nav(r.route);
}
function fav(r: any) {
	toggleFavorite({ label: r.name, route: r.route, icon: "chart-column", external: true });
}
async function toggleSchedule(s: any, on: boolean) {
	const prev = s.enabled;
	s.enabled = on ? 1 : 0;
	if (!(await runAction(API + "set_auto_email_enabled", { name: s.name, enabled: s.enabled }, on ? "Scheduled report on" : "Scheduled report paused"))) s.enabled = prev;
}
const typeIcon: Record<string, string> = { "Report Builder": "layout-grid", "Query Report": "database", "Script Report": "terminal", "Custom Report": "sliders-horizontal" };
</script>

<template>
	<div class="mx-auto w-full max-w-[1480px] px-4 pb-10 pt-6 sm:px-6">
		<PageHeader title="Reports & Analytics" description="Every report and dashboard you can open, what people use most, and reports emailed on a schedule.">
			<a :href="$href('/desk/report/new')" v-if="d.is_admin" class="nxg-btn nxg-btn-secondary"><Icon name="plus" :size="14" />Report</a>
			<a :href="$href('/desk/dashboard/new')" v-if="d.is_admin" class="nxg-btn nxg-btn-secondary"><Icon name="plus" :size="14" />Dashboard</a>
		</PageHeader>

		<div v-if="cat.state.error" class="nxg-panel p-4 text-[13px] text-nxg-danger">{{ cat.state.error }} <button class="nxg-btn nxg-btn-secondary ml-2 h-7" @click="cat.load(true)">Retry</button></div>
		<template v-else>
			<section v-if="popular.length" class="mb-4">
				<h2 class="mb-2 nxg-micro">Most used</h2>
				<div class="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
					<button v-for="r in popular" :key="r.name" class="nxg-panel flex items-center gap-3 px-4 py-3 text-left transition-colors hover:border-nxg-border-strong" @click="open(r)">
						<span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-nxg bg-nxg-surface-2"><Icon :name="typeIcon[r.report_type] || 'chart-column'" :size="16" /></span>
						<span class="min-w-0 flex-1"><span class="block truncate text-[13.5px] font-medium">{{ r.name }}</span><span class="block truncate text-[12px] text-nxg-text-2">{{ r.module }} · {{ r.my_opens ? `you opened ${r.my_opens}×` : "" }}{{ r.my_opens && r.exports_30d ? " · " : "" }}{{ r.exports_30d ? `${r.exports_30d} exports (30 d)` : "" }}</span></span>
						<Icon name="arrow-up-right" :size="14" class="text-nxg-text-3" />
					</button>
				</div>
			</section>

			<NxgTabs v-model="tab" class="mb-4" :tabs="[{ key: 'reports', label: 'Reports', count: d.reports?.length }, { key: 'dashboards', label: 'Dashboards', count: d.dashboards?.length }, { key: 'scheduled', label: 'Scheduled reports', count: d.scheduled?.length }]" />

			<div v-if="tab === 'reports'" class="nxg-panel">
				<div class="flex flex-wrap items-center gap-2 border-b border-nxg-border p-3">
					<div class="relative min-w-[220px] flex-1 sm:max-w-xs"><Icon name="search" :size="15" class="pointer-events-none absolute left-2.5 top-2 text-nxg-text-3" /><input v-model="f.search" class="nxg-input pl-8" placeholder="Search reports" aria-label="Search reports" /></div>
					<select v-model="f.module" class="nxg-input w-auto max-w-[200px]" aria-label="Module"><option value="">Any module</option><option v-for="m in d.modules || []" :key="m">{{ m }}</option></select>
					<select v-model="f.type" class="nxg-input w-auto" aria-label="Report type"><option value="">Any type</option><option v-for="t in types" :key="t">{{ t }}</option></select>
					<label class="flex items-center gap-2 text-[12.5px] text-nxg-text-2"><NxgSwitch v-model="f.favouritesOnly" label="Favourites only" />Favourites</label>
					<label v-if="d.is_admin" class="flex items-center gap-2 text-[12.5px] text-nxg-text-2"><NxgSwitch v-model="f.disabled" label="Include disabled" />Include disabled</label>
					<span class="nxg-tnum ml-auto text-[12.5px] text-nxg-text-2">{{ reports.length }} reports</span>
				</div>
				<DataTable :columns="[{ key: 'fav', label: '', width: '40px' }, { key: 'name', label: 'Report' }, { key: 'report_type', label: 'Type' }, { key: 'module', label: 'Module · app' }, { key: 'ref_doctype', label: 'Based on' }, { key: 'usage', label: 'Usage', align: 'right' }, { key: 'roles', label: 'Restricted to' }]" :rows="reports" :loading="cat.state.loading" clickable empty-text="No reports match" @row-click="open">
					<template #cell-fav="{ row }"><button class="nxg-icon-btn h-7 w-7" :aria-label="isFavorite(row.route) ? `Remove ${row.name} from favourites` : `Add ${row.name} to favourites`" @click.stop="fav(row)"><Icon name="star" :size="15" :class="isFavorite(row.route) ? 'fill-current text-nxg-warning' : 'text-nxg-text-3'" /></button></template>
					<template #cell-name="{ row }"><span class="font-medium">{{ row.name }}</span><span v-if="row.disabled" class="nxg-chip ml-2">Disabled</span><span v-if="row.prepared_report" class="nxg-chip ml-2" title="Runs in the background">Prepared</span></template>
					<template #cell-report_type="{ row }"><span class="inline-flex items-center gap-1.5 text-nxg-text-2"><Icon :name="typeIcon[row.report_type] || 'chart-column'" :size="13" />{{ row.report_type }}</span></template>
					<template #cell-module="{ row }"><span class="text-nxg-text-2">{{ row.module }}<span v-if="row.app"> · {{ row.app }}</span></span></template>
					<template #cell-usage="{ row }"><span class="nxg-tnum text-[12.5px] text-nxg-text-2">{{ row.exports_30d || row.my_opens ? `${row.exports_30d} exp · ${row.my_opens} you` : "—" }}</span></template>
					<template #cell-roles="{ row }"><span class="flex max-w-[220px] flex-wrap gap-1"><span v-for="r in row.roles.slice(0, 2)" :key="r" class="nxg-chip">{{ r }}</span><span v-if="row.roles.length > 2" class="nxg-chip">+{{ row.roles.length - 2 }}</span><span v-if="!row.roles.length" class="text-[12.5px] text-nxg-text-3">DocType access</span></span></template>
				</DataTable>
			</div>

			<div v-else-if="tab === 'dashboards'">
				<NxgEmpty v-if="!d.dashboards?.length" text="No dashboards you can open" icon="layout-grid" />
				<div v-else class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
					<a v-for="db in d.dashboards" :key="db.name" :href="db.route" class="nxg-panel flex flex-col gap-2 p-4 transition-colors hover:border-nxg-border-strong">
						<div class="flex items-center justify-between gap-2"><span class="truncate text-[14px] font-semibold">{{ db.name }}</span><span v-if="db.is_default" class="nxg-chip">Default</span></div>
						<div class="text-[12.5px] text-nxg-text-2">{{ db.module || "No module" }} · {{ db.charts }} chart{{ db.charts === 1 ? "" : "s" }} · {{ db.cards }} number card{{ db.cards === 1 ? "" : "s" }}</div>
					</a>
				</div>
				<p v-if="d.counts" class="mt-3 text-[12px] text-nxg-text-2">{{ d.counts.charts ?? "—" }} dashboard charts and {{ d.counts.number_cards ?? "—" }} number cards on this site<span v-if="d.counts.prepared_running"> · {{ d.counts.prepared_running }} prepared reports running</span>.</p>
			</div>

			<div v-else class="nxg-panel">
				<div class="border-b border-nxg-border px-4 py-3 text-[12.5px] text-nxg-text-2">{{ d.is_admin ? "All reports emailed on a schedule." : "Reports you have scheduled by email." }} Create one from a report's menu in Desk (“Setup Auto Email”).</div>
				<NxgEmpty v-if="!d.scheduled?.length" text="No scheduled reports" icon="inbox" />
				<DataTable v-else :columns="[{ key: 'report', label: 'Report' }, { key: 'frequency', label: 'When' }, { key: 'format', label: 'Format' }, { key: 'recipients', label: 'Recipients', align: 'right' }, { key: 'user', label: 'Owner' }, { key: 'enabled', label: 'On', align: 'right' }]" :rows="d.scheduled">
					<template #cell-report="{ row }"><a :href="$href(`/desk/auto-email-report/${encodeURIComponent(row.name)}`)" class="font-medium hover:underline">{{ row.report }}</a></template>
					<template #cell-frequency="{ row }"><span class="text-nxg-text-2">{{ row.frequency }}<span v-if="row.frequency === 'Weekly' && row.day_of_week"> · {{ row.day_of_week }}</span></span></template>
					<template #cell-recipients="{ row }"><span class="nxg-tnum">{{ row.recipients }}</span></template>
					<template #cell-enabled="{ row }"><NxgSwitch :model-value="!!row.enabled" :label="`Enable ${row.report}`" @update:model-value="(v) => toggleSchedule(row, v)" /></template>
				</DataTable>
			</div>
		</template>
	</div>
</template>
