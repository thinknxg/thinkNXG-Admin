<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { call, toast } from "frappe-ui";
import PageHeader from "@/components/ui/PageHeader.vue";
import NxgTabs from "@/components/ui/NxgTabs.vue";
import DataTable from "@/components/ui/DataTable.vue";
import NxgPagination from "@/components/ui/NxgPagination.vue";
import NxgDrawer from "@/components/ui/NxgDrawer.vue";
import NxgStatus from "@/components/ui/NxgStatus.vue";
import NxgEmpty from "@/components/ui/NxgEmpty.vue";
import Icon from "@/components/ui/Icon.vue";
import { errorMessage, runAction, usePanel } from "@/data/api";
import { confirmAction } from "@/composables/useConfirm";
import { fmtDateTime, fmtNumber, timeAgo } from "@/composables/format";

const API = "thinknxg_admin.api.developer.";
const tab = ref("overview");
const ov = usePanel<any>(API + "get_overview");

// DocType explorer
const dt = reactive({ search: "", module: "", kind: "", start: 0 });
const dts = ref<any>(null);
const dtLoading = ref(false);
let t: number | undefined;
async function loadDts() {
	dtLoading.value = true;
	try {
		dts.value = await call(API + "list_doctypes", { ...dt, page_length: 50 });
	} catch (e) {
		dts.value = { error: errorMessage(e) };
	} finally {
		dtLoading.value = false;
	}
}
watch(() => [dt.search, dt.module, dt.kind], () => { dt.start = 0; window.clearTimeout(t); t = window.setTimeout(loadDts, 250); });
watch(() => dt.start, loadDts);
const openDt = ref<string | null>(null);
const dtDetail = ref<any>(null);
const fieldSearch = ref("");
watch(openDt, async (n) => {
	dtDetail.value = null;
	fieldSearch.value = "";
	if (!n) return;
	try {
		dtDetail.value = await call(API + "get_doctype", { name: n });
	} catch (e) {
		dtDetail.value = { error: errorMessage(e) };
	}
});
const fields = computed(() => (dtDetail.value?.fields || []).filter((f: any) => !fieldSearch.value || `${f.fieldname} ${f.label} ${f.fieldtype}`.toLowerCase().includes(fieldSearch.value.toLowerCase())));

// Customisations
const ck = reactive({ kind: "custom_field", doctype: "", start: 0 });
const cust = ref<any>(null);
async function loadCust() {
	try {
		cust.value = await call(API + "list_customizations", { ...ck });
	} catch (e) {
		cust.value = { error: errorMessage(e) };
	}
}
watch(() => [ck.kind, ck.doctype], () => { ck.start = 0; window.clearTimeout(t); t = window.setTimeout(loadCust, 250); });
watch(() => ck.start, loadCust);
const custColumns: Record<string, any[]> = {
	custom_field: [{ key: "dt", label: "DocType" }, { key: "label", label: "Field" }, { key: "fieldtype", label: "Type" }, { key: "insert_after", label: "After" }, { key: "module", label: "Module" }, { key: "modified", label: "Changed" }],
	property_setter: [{ key: "doc_type", label: "DocType" }, { key: "field_name", label: "Field" }, { key: "property", label: "Property" }, { key: "value", label: "Value" }, { key: "module", label: "Module" }, { key: "modified", label: "Changed" }],
	client_script: [{ key: "name", label: "Script" }, { key: "dt", label: "DocType" }, { key: "view", label: "View" }, { key: "enabled", label: "Enabled" }, { key: "modified", label: "Changed" }],
	server_script: [{ key: "name", label: "Script" }, { key: "script_type", label: "Type" }, { key: "reference_doctype", label: "DocType" }, { key: "doctype_event", label: "Event" }, { key: "disabled", label: "Status" }, { key: "modified", label: "Changed" }],
};

// Errors
const er = reactive({ search: "", seen: "0", start: 0 });
const errors = ref<any>(null);
async function loadErrors() {
	try {
		errors.value = await call(API + "list_errors", { ...er });
	} catch (e) {
		errors.value = { error: errorMessage(e) };
	}
}
watch(() => [er.search, er.seen], () => { er.start = 0; window.clearTimeout(t); t = window.setTimeout(loadErrors, 250); });
watch(() => er.start, loadErrors);
const openErr = ref<string | null>(null);
const errDetail = ref<any>(null);
watch(openErr, async (n) => {
	errDetail.value = null;
	if (!n) return;
	try {
		errDetail.value = await call(API + "get_error", { name: n });
		if (!errDetail.value.seen) await call(API + "mark_errors_seen", { names: [n] });
	} catch (e) {
		errDetail.value = { error: errorMessage(e) };
	}
});
async function markAllSeen() {
	if (!(await confirmAction({ title: "Mark every unseen error as seen?", confirmLabel: "Mark all seen" }))) return;
	if (await runAction(API + "mark_errors_seen", { all_unseen: 1 }, "All errors marked as seen")) {
		loadErrors();
		ov.load(true);
	}
}
function copy(text: string) {
	navigator.clipboard?.writeText(text).then(() => toast.success("Copied"));
}

// Jobs
const jobStatus = ref("failed");
const jobs = ref<any>(null);
async function loadJobs() {
	jobs.value = null;
	try {
		jobs.value = await call(API + "list_jobs", { status: jobStatus.value });
	} catch (e) {
		jobs.value = { error: errorMessage(e) };
	}
}
watch(jobStatus, loadJobs);
async function stop(j: any) {
	if (!(await confirmAction({ title: "Stop this job?", message: j.job_name, confirmLabel: "Stop job", danger: true }))) return;
	if (await runAction(API + "stop_job", { job_id: j.job_id }, "Stop signal sent")) loadJobs();
}
async function clearFailed() {
	if (!(await confirmAction({ title: "Remove all failed jobs?", message: "Clears the failed-job registry. Error details stay in the Error Log.", confirmLabel: "Remove", danger: true }))) return;
	if (await runAction(API + "clear_failed_jobs", {}, "Failed jobs removed")) loadJobs();
}

watch(tab, (v) => {
	if (v === "doctypes" && !dts.value) loadDts();
	if (v === "custom" && !cust.value) loadCust();
	if (v === "errors" && !errors.value) loadErrors();
	if (v === "jobs" && !jobs.value) loadJobs();
});
const o = computed(() => ov.state.data || {});
function openRoute(r: any) {
	window.location.href = r.route;
}
</script>

<template>
	<div class="mx-auto w-full max-w-[1480px] px-4 pb-10 pt-6 sm:px-6">
		<PageHeader title="Developer Tools" description="Inspect DocTypes and customisations, read error logs and manage background jobs. Read-only by design: no code runs from here.">
			<a href="/desk/doctype" class="nxg-btn nxg-btn-ghost">DocType list<Icon name="external-link" :size="13" /></a>
		</PageHeader>
		<NxgTabs v-model="tab" class="mb-4" :tabs="[{ key: 'overview', label: 'Overview' }, { key: 'doctypes', label: 'DocType explorer', count: o.doctypes }, { key: 'custom', label: 'Customisations' }, { key: 'errors', label: 'Error logs', count: o.errors_unseen }, { key: 'jobs', label: 'Background jobs' }]" />
		<div v-if="ov.state.error && tab === 'overview'" class="nxg-panel p-4 text-[13px] text-nxg-danger">{{ ov.state.error }}</div>

		<div v-if="tab === 'overview'" class="space-y-4">
			<div class="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-8">
				<button v-for="[k, l, target] in [['doctypes', 'DocTypes', 'doctypes'], ['custom_doctypes', 'Custom DocTypes', 'doctypes'], ['child_tables', 'Child tables', 'doctypes'], ['custom_fields', 'Custom fields', 'custom'], ['property_setters', 'Property setters', 'custom'], ['client_scripts', 'Client scripts', 'custom'], ['server_scripts', 'Server scripts', 'custom'], ['errors_24h', 'Errors (24 h)', 'errors']]" :key="k" class="nxg-panel px-3.5 py-3 text-left hover:border-nxg-border-strong" @click="tab = target">
					<div class="truncate text-[12px] text-nxg-text-2">{{ l }}</div>
					<div v-if="ov.state.loading && !ov.state.data" class="nxg-skeleton mt-1 h-6 w-10" />
					<div v-else class="nxg-tnum text-[20px] font-semibold" :class="k === 'errors_24h' && o[k] ? 'text-nxg-warning' : ''">{{ o[k] === null || o[k] === undefined ? "—" : fmtNumber(o[k]) }}</div>
				</button>
			</div>
			<div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
				<section class="nxg-panel lg:col-span-2">
					<header class="border-b border-nxg-border px-4 py-3"><h2 class="text-[15px] font-semibold">Installed applications</h2></header>
					<table class="w-full text-[13px]"><thead><tr class="border-b border-nxg-border"><th class="px-4 py-2 text-left nxg-micro">App</th><th class="px-3 py-2 text-left nxg-micro">Version</th><th class="px-4 py-2 text-left nxg-micro">Branch</th></tr></thead>
						<tbody class="divide-y divide-nxg-border"><tr v-for="a in o.apps || []" :key="a.name"><td class="px-4 py-2"><span class="font-medium">{{ a.title || a.name }}</span> <code class="text-[11.5px] text-nxg-text-3">{{ a.name }}</code></td><td class="nxg-tnum px-3">{{ a.version || "—" }}</td><td class="px-4 text-nxg-text-2">{{ a.branch || "—" }}</td></tr></tbody>
					</table>
				</section>
				<section class="nxg-panel p-4 text-[13px]">
					<h2 class="mb-3 text-[15px] font-semibold">Environment</h2>
					<dl class="divide-y divide-nxg-border">
						<div class="flex items-center justify-between py-2"><dt class="text-nxg-text-2">Developer mode</dt><dd><NxgStatus :status="o.developer_mode ? 'warning' : 'ok'" :label="o.developer_mode ? 'On' : 'Off'" /></dd></div>
						<div class="flex items-center justify-between py-2"><dt class="text-nxg-text-2">Server scripts</dt><dd><NxgStatus :status="o.server_scripts_enabled ? 'info' : 'unknown'" :label="o.server_scripts_enabled ? 'Enabled' : 'Disabled'" /></dd></div>
						<div class="flex items-center justify-between py-2"><dt class="text-nxg-text-2">Modules</dt><dd class="nxg-tnum">{{ o.modules ?? "—" }}</dd></div>
						<div class="flex items-center justify-between py-2"><dt class="text-nxg-text-2">Unseen errors</dt><dd class="nxg-tnum">{{ o.errors_unseen ?? "—" }}</dd></div>
					</dl>
					<p v-if="o.developer_mode" class="mt-3 text-[12px] text-nxg-warning">Developer mode is meant for development benches. Turn it off on production sites.</p>
				</section>
			</div>
		</div>

		<div v-else-if="tab === 'doctypes'" class="nxg-panel">
			<div class="flex flex-wrap items-center gap-2 border-b border-nxg-border p-3">
				<input v-model="dt.search" class="nxg-input max-w-xs" placeholder="Search DocTypes" aria-label="Search DocTypes" />
				<select v-model="dt.module" class="nxg-input w-auto max-w-[200px]" aria-label="Module"><option value="">Any module</option><option v-for="m in dts?.modules || []" :key="m">{{ m }}</option></select>
				<select v-model="dt.kind" class="nxg-input w-auto" aria-label="Kind"><option value="">Documents</option><option value="custom">Custom</option><option value="submittable">Submittable</option><option value="single">Single</option><option value="child">Child tables</option></select>
			</div>
			<div v-if="dts?.error" class="p-4 text-[13px] text-nxg-danger">{{ dts.error }}</div>
			<DataTable v-else :columns="[{ key: 'name', label: 'DocType' }, { key: 'module', label: 'Module · app' }, { key: 'flags', label: 'Kind' }, { key: 'custom_fields', label: 'Custom fields', align: 'right' }, { key: 'property_setters', label: 'Property setters', align: 'right' }, { key: 'modified', label: 'Changed' }]" :rows="dts?.rows || []" :loading="dtLoading" clickable @row-click="(r) => (openDt = r.name)">
				<template #cell-name="{ row }"><span class="font-medium">{{ row.name }}</span></template>
				<template #cell-module="{ row }"><span class="text-nxg-text-2">{{ row.module }} · {{ row.app }}</span></template>
				<template #cell-flags="{ row }"><span class="flex flex-wrap gap-1"><span v-if="row.custom" class="nxg-chip">Custom</span><span v-if="row.is_submittable" class="nxg-chip">Submittable</span><span v-if="row.issingle" class="nxg-chip">Single</span><span v-if="row.istable" class="nxg-chip">Child</span><span v-if="row.is_virtual" class="nxg-chip">Virtual</span><span v-if="row.track_changes" class="nxg-chip" title="Changes recorded in Version">Tracked</span></span></template>
				<template #cell-custom_fields="{ row }"><span class="nxg-tnum" :class="!row.custom_fields && 'text-nxg-text-3'">{{ row.custom_fields || "—" }}</span></template>
				<template #cell-property_setters="{ row }"><span class="nxg-tnum" :class="!row.property_setters && 'text-nxg-text-3'">{{ row.property_setters || "—" }}</span></template>
				<template #cell-modified="{ row }"><span class="text-nxg-text-2">{{ timeAgo(row.modified) }}</span></template>
			</DataTable>
			<NxgPagination v-if="dts?.total" :start="dt.start" :page-length="50" :total="dts.total" class="border-t border-nxg-border" @change="(s) => (dt.start = s)" />
		</div>

		<div v-else-if="tab === 'custom'" class="nxg-panel">
			<div class="flex flex-wrap items-center gap-2 border-b border-nxg-border p-3">
				<div class="inline-flex flex-wrap rounded-nxg border border-nxg-border p-0.5"><button v-for="[k, l] in [['custom_field', 'Custom fields'], ['property_setter', 'Property setters'], ['client_script', 'Client scripts'], ['server_script', 'Server scripts']]" :key="k" class="h-7 rounded-[6px] px-2.5 text-[12.5px] font-medium" :class="ck.kind === k ? 'bg-nxg-primary text-nxg-primary-fg' : 'text-nxg-text-2'" @click="ck.kind = k">{{ l }}</button></div>
				<input v-model="ck.doctype" class="nxg-input max-w-[220px]" placeholder="Exact DocType name" aria-label="Filter by DocType" />
			</div>
			<div v-if="cust?.error" class="p-4 text-[13px] text-nxg-danger">{{ cust.error }}</div>
			<NxgEmpty v-else-if="cust === null" text="Not available on this site" />
			<DataTable v-else :columns="custColumns[ck.kind]" :rows="cust?.rows || []" :loading="!cust" clickable empty-text="No customisations of this kind" @row-click="openRoute">
				<template #cell-label="{ row }"><span class="font-medium">{{ row.label || row.fieldname }}</span> <code class="text-[11.5px] text-nxg-text-3">{{ row.fieldname }}</code></template>
				<template #cell-value="{ row }"><code class="text-[12px]">{{ row.value }}</code></template>
				<template #cell-enabled="{ row }"><NxgStatus :status="row.enabled ? 'ok' : 'unknown'" :label="row.enabled ? 'Enabled' : 'Disabled'" /></template>
				<template #cell-disabled="{ row }"><NxgStatus :status="row.disabled ? 'unknown' : 'ok'" :label="row.disabled ? 'Disabled' : 'Enabled'" /></template>
				<template #cell-modified="{ row }"><span class="text-nxg-text-2">{{ timeAgo(row.modified) }}</span></template>
			</DataTable>
			<NxgPagination v-if="cust?.total" :start="ck.start" :page-length="50" :total="cust.total" class="border-t border-nxg-border" @change="(s) => (ck.start = s)" />
		</div>

		<div v-else-if="tab === 'errors'" class="nxg-panel">
			<div class="flex flex-wrap items-center gap-2 border-b border-nxg-border p-3">
				<input v-model="er.search" class="nxg-input max-w-xs" placeholder="Search method" aria-label="Search errors" />
				<select v-model="er.seen" class="nxg-input w-auto" aria-label="Seen"><option value="0">Unseen</option><option value="1">Seen</option><option value="">All</option></select>
				<button class="nxg-btn nxg-btn-secondary ml-auto" :disabled="!o.errors_unseen" @click="markAllSeen">Mark all seen</button>
			</div>
			<div v-if="errors?.error" class="p-4 text-[13px] text-nxg-danger">{{ errors.error }}</div>
			<DataTable v-else :columns="[{ key: 'creation', label: 'When' }, { key: 'method', label: 'Where' }, { key: 'exception', label: 'Exception' }, { key: 'reference', label: 'Document' }]" :rows="errors?.rows || []" :loading="!errors" clickable empty-text="No errors here" @row-click="(r) => (openErr = r.name)">
				<template #cell-creation="{ row }"><span class="flex items-center gap-2 whitespace-nowrap"><span v-if="!row.seen" class="h-2 w-2 rounded-full bg-nxg-red" aria-label="Unseen" /><span class="text-nxg-text-2" :title="fmtDateTime(row.creation)">{{ timeAgo(row.creation) }}</span></span></template>
				<template #cell-method="{ row }"><span class="block max-w-[280px] truncate font-mono text-[12px]" :title="row.method">{{ row.method || "—" }}</span></template>
				<template #cell-exception="{ row }"><span class="block max-w-[420px] truncate font-mono text-[12px] text-nxg-danger" :title="row.exception">{{ row.exception || "—" }}</span></template>
				<template #cell-reference="{ row }"><span class="text-nxg-text-2">{{ row.reference_doctype ? `${row.reference_doctype} ${row.reference_name || ""}` : "—" }}</span></template>
			</DataTable>
			<NxgPagination v-if="errors?.total" :start="er.start" :page-length="40" :total="errors.total" class="border-t border-nxg-border" @change="(s) => (er.start = s)" />
		</div>

		<div v-else class="nxg-panel">
			<div class="flex flex-wrap items-center gap-2 border-b border-nxg-border p-3">
				<div class="inline-flex rounded-nxg border border-nxg-border p-0.5"><button v-for="s in ['failed', 'started', 'queued', 'finished']" :key="s" class="h-7 rounded-[6px] px-2.5 text-[12.5px] font-medium capitalize" :class="jobStatus === s ? 'bg-nxg-primary text-nxg-primary-fg' : 'text-nxg-text-2'" @click="jobStatus = s">{{ s === "started" ? "Running" : s }}</button></div>
				<button v-if="jobStatus === 'failed'" class="nxg-btn nxg-btn-secondary ml-auto" :disabled="!jobs?.rows?.length" @click="clearFailed">Remove failed jobs</button>
				<button class="nxg-icon-btn" :class="jobStatus !== 'failed' && 'ml-auto'" aria-label="Reload" @click="loadJobs"><Icon name="refresh-cw" :size="15" /></button>
			</div>
			<div v-if="jobs?.error" class="p-4 text-[13px] text-nxg-danger">{{ jobs.error }}</div>
			<DataTable v-else :columns="[{ key: 'job_name', label: 'Job' }, { key: 'queue', label: 'Queue' }, { key: 'started_at', label: 'Started' }, { key: 'time_taken', label: 'Duration', align: 'right' }, { key: 'exception', label: 'Error' }, { key: 'actions', label: '', align: 'right' }]" :rows="jobs?.rows || []" row-key="job_id" :loading="!jobs" empty-text="No jobs in this state">
				<template #cell-job_name="{ row }"><span class="block max-w-[320px] truncate font-mono text-[12px]" :title="row.job_name">{{ row.job_name }}</span></template>
				<template #cell-started_at="{ row }"><span class="whitespace-nowrap text-nxg-text-2">{{ row.started_at ? timeAgo(row.started_at) : "—" }}</span></template>
				<template #cell-time_taken="{ row }"><span class="nxg-tnum text-nxg-text-2">{{ row.time_taken ? `${Number(row.time_taken).toFixed(1)} s` : "—" }}</span></template>
				<template #cell-exception="{ row }"><span class="block max-w-[360px] truncate font-mono text-[12px] text-nxg-danger" :title="row.exception">{{ row.exception || "" }}</span></template>
				<template #cell-actions="{ row }"><button v-if="row.status === 'started'" class="nxg-btn nxg-btn-ghost h-7" @click="stop(row)">Stop</button><a v-else :href="row.route" class="nxg-btn nxg-btn-ghost h-7">Open<Icon name="external-link" :size="12" /></a></template>
			</DataTable>
		</div>

		<NxgDrawer :open="!!openDt" :title="openDt || ''" :subtitle="dtDetail && !dtDetail.error ? `${dtDetail.module} · ${dtDetail.app} · ${dtDetail.records ?? '—'} records` : ''" width="max-w-[760px]" @close="openDt = null">
			<div v-if="!dtDetail" class="space-y-2 p-5"><div v-for="i in 8" :key="i" class="nxg-skeleton h-7" /></div>
			<div v-else-if="dtDetail.error" class="p-5 text-[13px] text-nxg-danger">{{ dtDetail.error }}</div>
			<div v-else class="space-y-5 p-5">
				<dl class="grid grid-cols-2 gap-x-6 text-[13px] sm:grid-cols-3">
					<div class="border-b border-nxg-border py-1.5"><dt class="text-[11.5px] text-nxg-text-2">Naming</dt><dd class="truncate font-mono text-[12px]">{{ dtDetail.autoname || "hash" }}</dd></div>
					<div class="border-b border-nxg-border py-1.5"><dt class="text-[11.5px] text-nxg-text-2">Title field</dt><dd>{{ dtDetail.title_field || "—" }}</dd></div>
					<div class="border-b border-nxg-border py-1.5"><dt class="text-[11.5px] text-nxg-text-2">Change tracking</dt><dd>{{ dtDetail.track_changes ? "On" : "Off" }}</dd></div>
				</dl>
				<section>
					<div class="mb-2 flex items-center gap-2"><h3 class="nxg-micro">Fields · {{ dtDetail.fields.length }}</h3><input v-model="fieldSearch" class="nxg-input ml-auto h-7 max-w-[200px]" placeholder="Filter fields" /></div>
					<div class="max-h-[340px] overflow-y-auto rounded-nxg border border-nxg-border">
						<table class="w-full text-[12.5px]"><thead class="sticky top-0 bg-nxg-surface"><tr class="border-b border-nxg-border"><th class="px-3 py-1.5 text-left nxg-micro">Field</th><th class="px-3 py-1.5 text-left nxg-micro">Type</th><th class="px-3 py-1.5 text-left nxg-micro">Options</th><th class="px-3 py-1.5 text-left nxg-micro">Flags</th></tr></thead>
							<tbody class="divide-y divide-nxg-border"><tr v-for="f in fields" :key="f.fieldname"><td class="px-3 py-1"><span class="font-medium">{{ f.label || f.fieldname }}</span> <code class="text-[11px] text-nxg-text-3">{{ f.fieldname }}</code></td><td class="px-3">{{ f.fieldtype }}</td><td class="max-w-[160px] truncate px-3 text-nxg-text-2">{{ f.options }}</td><td class="px-3"><span class="flex flex-wrap gap-1"><span v-if="f.custom" class="nxg-chip">Custom</span><span v-if="f.reqd" class="nxg-chip">Required</span><span v-if="f.unique" class="nxg-chip">Unique</span><span v-if="f.permlevel" class="nxg-chip">Level {{ f.permlevel }}</span><span v-if="f.hidden" class="nxg-chip">Hidden</span></span></td></tr></tbody>
						</table>
					</div>
				</section>
				<section>
					<h3 class="mb-2 nxg-micro">Permissions</h3>
					<div class="flex flex-wrap gap-1.5"><span v-for="p in dtDetail.permissions" :key="p.role + p.permlevel" class="nxg-chip">{{ p.role }}{{ p.permlevel ? ` · L${p.permlevel}` : "" }}: {{ ["read", "write", "create", "delete", "submit"].filter((k) => p[k]).join(", ") || "none" }}</span></div>
					<RouterLink :to="{ path: '/roles/matrix', query: { doctype: openDt } }" class="nxg-btn nxg-btn-ghost mt-2 h-7">Edit in matrix</RouterLink>
				</section>
				<section v-if="dtDetail.property_setters.length || dtDetail.client_scripts.length || dtDetail.server_scripts.length">
					<h3 class="mb-2 nxg-micro">Customisations</h3>
					<ul class="space-y-1 text-[12.5px]">
						<li v-for="p in dtDetail.property_setters" :key="p.name"><span class="nxg-chip mr-1">Property</span>{{ p.field_name || "DocType" }} · {{ p.property }} = <code>{{ p.value }}</code></li>
						<li v-for="c in dtDetail.client_scripts" :key="c.name"><span class="nxg-chip mr-1">Client script</span><a :href="`/desk/client-script/${encodeURIComponent(c.name)}`" class="hover:underline">{{ c.name }}</a> · {{ c.view }} · {{ c.enabled ? "enabled" : "disabled" }}</li>
						<li v-for="s in dtDetail.server_scripts" :key="s.name"><span class="nxg-chip mr-1">Server script</span><a :href="`/desk/server-script/${encodeURIComponent(s.name)}`" class="hover:underline">{{ s.name }}</a> · {{ s.doctype_event }} · {{ s.disabled ? "disabled" : "enabled" }}</li>
					</ul>
				</section>
			</div>
			<template v-if="dtDetail && !dtDetail.error" #footer>
				<a :href="`/desk/doctype/${encodeURIComponent(openDt || '')}`" class="nxg-btn nxg-btn-ghost mr-auto">Edit DocType<Icon name="external-link" :size="13" /></a>
				<a :href="`/desk/customize-form?doc_type=${encodeURIComponent(openDt || '')}`" class="nxg-btn nxg-btn-secondary">Customize form</a>
				<a :href="dtDetail.route" class="nxg-btn nxg-btn-primary">Open records</a>
			</template>
		</NxgDrawer>

		<NxgDrawer :open="!!openErr" title="Error details" :subtitle="errDetail?.method || ''" width="max-w-[840px]" @close="openErr = null">
			<div v-if="!errDetail" class="p-5"><div class="nxg-skeleton h-64" /></div>
			<div v-else-if="errDetail.error && !errDetail.name" class="p-5 text-[13px] text-nxg-danger">{{ errDetail.error }}</div>
			<div v-else class="space-y-3 p-5">
				<div class="flex flex-wrap items-center gap-3 text-[12.5px] text-nxg-text-2"><span>{{ fmtDateTime(errDetail.creation) }}</span><span v-if="errDetail.reference_doctype">{{ errDetail.reference_doctype }} {{ errDetail.reference_name }}</span><span v-if="errDetail.trace_id" class="font-mono">trace {{ errDetail.trace_id }}</span><button class="nxg-btn nxg-btn-secondary ml-auto h-7" @click="copy(errDetail.error)">Copy traceback</button></div>
				<pre class="nxg-scroll max-h-[70vh] overflow-auto rounded-nxg border border-nxg-border bg-nxg-surface-2 p-3 font-mono text-[12px] leading-5">{{ errDetail.error }}</pre>
			</div>
			<template v-if="errDetail?.name" #footer><a :href="`/desk/error-log/${encodeURIComponent(errDetail.name)}`" class="nxg-btn nxg-btn-ghost">Open in Desk<Icon name="external-link" :size="13" /></a></template>
		</NxgDrawer>
	</div>
</template>
