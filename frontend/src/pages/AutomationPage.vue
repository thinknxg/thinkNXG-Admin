<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { call } from "frappe-ui";
import PageHeader from "@/components/ui/PageHeader.vue";
import NxgTabs from "@/components/ui/NxgTabs.vue";
import DataTable from "@/components/ui/DataTable.vue";
import NxgStatus from "@/components/ui/NxgStatus.vue";
import NxgSwitch from "@/components/ui/NxgSwitch.vue";
import NxgDrawer from "@/components/ui/NxgDrawer.vue";
import NxgEmpty from "@/components/ui/NxgEmpty.vue";
import Icon from "@/components/ui/Icon.vue";
import { errorMessage, runAction, usePanel } from "@/data/api";
import { confirmAction } from "@/composables/useConfirm";
import { fmtDateTime, timeAgo } from "@/composables/format";

const API = "thinknxg_admin.api.automation.";
const ov = usePanel<any>(API + "get_overview");
const d = computed(() => ov.state.data || {});
const tab = ref("workflows");
const search = ref("");
const match = (...v: any[]) => !search.value || v.join(" ").toLowerCase().includes(search.value.toLowerCase());

/** Toggle through each document's own save. `on` is the user-facing state. */
async function setOn(doctype: string, row: any, field: string, onValue: number, on: boolean, label: string) {
	if (!on && !(await confirmAction({ title: `Turn off ${label}?`, confirmLabel: "Turn off", danger: true }))) return;
	const prev = row[field];
	row[field] = on ? onValue : 1 - onValue;
	if (!(await runAction(API + "set_enabled", { doctype, name: row.name, enabled: on ? 1 : 0 }, `${label} turned ${on ? "on" : "off"}`))) row[field] = prev;
	else if (doctype === "Workflow") ov.load(true); // activating one may deactivate another for the same DocType
}

async function runJob(j: any) {
	if (!(await confirmAction({ title: "Run this job now?", message: j.method || j.name, confirmLabel: "Queue now" }))) return;
	await runAction(API + "run_scheduled_job", { name: j.name }, "Job queued");
}
const logsFor = ref<string | null>(null);
const logs = ref<any>(null);
watch(logsFor, async (job) => {
	logs.value = null;
	if (!job) return;
	try {
		logs.value = await call(API + "list_job_logs", { job });
	} catch (e) {
		logs.value = { error: errorMessage(e) };
	}
});
const jobFilter = ref<"all" | "failing" | "stopped">("all");
const jobs = computed(() => (d.value.scheduled_jobs || []).filter((j: any) => match(j.method, j.name, j.frequency) && (jobFilter.value === "all" || (jobFilter.value === "failing" ? j.failures_7d : j.stopped))));
const schedulerTone: Record<string, [string, string]> = { running: ["ok", "Scheduler running"], inactive: ["warning", "Scheduler inactive"], disabled: ["critical", "Scheduler disabled"], unknown: ["unknown", "Scheduler unknown"] };
</script>

<template>
	<div class="mx-auto w-full max-w-[1480px] px-4 pb-10 pt-6 sm:px-6">
		<PageHeader title="Automation" description="Workflows, notifications, assignment rules, scheduled jobs and scripts that act on your data automatically.">
			<NxgStatus v-if="d.scheduler" :status="schedulerTone[d.scheduler][0]" :label="schedulerTone[d.scheduler][1]" size="md" />
			<button class="nxg-icon-btn" aria-label="Reload" @click="ov.load(true)"><Icon name="refresh-cw" :size="15" :class="ov.state.loading && 'animate-spin'" /></button>
		</PageHeader>

		<NxgTabs v-model="tab" class="mb-4" :tabs="[{ key: 'workflows', label: 'Workflows', count: d.workflows?.length }, { key: 'notifications', label: 'Notifications', count: d.notifications?.length }, { key: 'assignment', label: 'Assignment rules', count: d.assignment_rules?.length }, { key: 'jobs', label: 'Scheduled jobs', count: d.scheduled_jobs?.length }, { key: 'scripts', label: 'Server scripts', count: d.server_scripts?.length }, { key: 'other', label: 'Recurring & naming' }]" />
		<div v-if="ov.state.error" class="nxg-panel p-4 text-[13px] text-nxg-danger">{{ ov.state.error }} <button class="nxg-btn nxg-btn-secondary ml-2 h-7" @click="ov.load(true)">Retry</button></div>
		<div v-else-if="ov.state.loading && !ov.state.data" class="space-y-2"><div v-for="i in 6" :key="i" class="nxg-skeleton h-11" /></div>

		<div v-else class="nxg-panel">
			<div v-if="tab !== 'other'" class="flex flex-wrap items-center gap-2 border-b border-nxg-border p-3">
				<input v-model="search" class="nxg-input max-w-xs" placeholder="Search" aria-label="Search" />
				<div v-if="tab === 'jobs'" class="inline-flex rounded-nxg border border-nxg-border p-0.5"><button v-for="o in ['all', 'failing', 'stopped']" :key="o" class="h-7 rounded-[6px] px-2.5 text-[12.5px] font-medium capitalize" :class="jobFilter === o ? 'bg-nxg-primary text-nxg-primary-fg' : 'text-nxg-text-2'" @click="jobFilter = o as any">{{ o }}</button></div>
				<a :href="$href({ workflows: '/desk/workflow/new', notifications: '/desk/notification/new', assignment: '/desk/assignment-rule/new', jobs: '/desk/scheduled-job-type', scripts: '/desk/server-script/new' }[tab])" class="nxg-btn nxg-btn-secondary ml-auto">{{ tab === "jobs" ? "View all" : "New" }}<Icon :name="tab === 'jobs' ? 'external-link' : 'plus'" :size="13" /></a>
			</div>

			<template v-if="tab === 'workflows'">
				<NxgEmpty v-if="!d.workflows?.length" :text="d.workflows === null ? 'Workflows are not available' : 'No workflows yet'" icon="workflow" />
				<DataTable v-else :columns="[{ key: 'name', label: 'Workflow' }, { key: 'document_type', label: 'Applies to' }, { key: 'states', label: 'States', align: 'right' }, { key: 'transitions', label: 'Transitions', align: 'right' }, { key: 'open_actions', label: 'Awaiting action', align: 'right' }, { key: 'is_active', label: 'Active', align: 'right' }]" :rows="d.workflows.filter((w: any) => match(w.name, w.document_type))">
					<template #cell-name="{ row }"><a :href="$href(`/desk/workflow/${encodeURIComponent(row.name)}`)" class="font-medium hover:underline">{{ row.name }}</a></template>
					<template #cell-open_actions="{ row }"><a v-if="row.open_actions" :href="$href(`/desk/workflow-action?status=Open&reference_doctype=${encodeURIComponent(row.document_type)}`)" class="nxg-tnum font-medium hover:underline">{{ row.open_actions }}</a><span v-else class="text-nxg-text-3">—</span></template>
					<template #cell-is_active="{ row }"><NxgSwitch :model-value="!!row.is_active" :label="`Activate ${row.name}`" @update:model-value="(v) => setOn('Workflow', row, 'is_active', 1, v, row.name)" /></template>
				</DataTable>
				<p v-if="d.workflows?.length" class="border-t border-nxg-border px-4 py-2 text-[12px] text-nxg-text-2">Only one workflow can be active per DocType; activating one deactivates the others.</p>
			</template>

			<template v-else-if="tab === 'notifications'">
				<NxgEmpty v-if="!d.notifications?.length" text="No notification rules" icon="bell" />
				<DataTable v-else :columns="[{ key: 'name', label: 'Notification' }, { key: 'document_type', label: 'Document' }, { key: 'event', label: 'When' }, { key: 'channel', label: 'Channel' }, { key: 'enabled', label: 'On', align: 'right' }]" :rows="d.notifications.filter((n: any) => match(n.name, n.document_type, n.event))">
					<template #cell-name="{ row }"><a :href="$href(`/desk/notification/${encodeURIComponent(row.name)}`)" class="font-medium hover:underline">{{ row.name }}</a><span v-if="row.is_standard" class="nxg-chip ml-2">Standard</span></template>
					<template #cell-event="{ row }"><span class="text-nxg-text-2">{{ row.event }}<span v-if="row.event === 'Days Before' || row.event === 'Days After'"> · {{ row.days_in_advance }} d on {{ row.date_changed }}</span><span v-if="row.event === 'Value Change'"> · {{ row.value_changed }}</span></span></template>
					<template #cell-enabled="{ row }"><NxgSwitch :model-value="!!row.enabled" :label="`Enable ${row.name}`" @update:model-value="(v) => setOn('Notification', row, 'enabled', 1, v, row.name)" /></template>
				</DataTable>
			</template>

			<template v-else-if="tab === 'assignment'">
				<NxgEmpty v-if="!d.assignment_rules?.length" text="No assignment rules" icon="list-checks" />
				<DataTable v-else :columns="[{ key: 'name', label: 'Rule' }, { key: 'document_type', label: 'Document' }, { key: 'rule', label: 'Method' }, { key: 'users', label: 'Users', align: 'right' }, { key: 'priority', label: 'Priority', align: 'right' }, { key: 'last_user', label: 'Last assigned' }, { key: 'disabled', label: 'On', align: 'right' }]" :rows="d.assignment_rules.filter((r: any) => match(r.name, r.document_type))">
					<template #cell-name="{ row }"><a :href="$href(`/desk/assignment-rule/${encodeURIComponent(row.name)}`)" class="font-medium hover:underline">{{ row.name }}</a></template>
					<template #cell-disabled="{ row }"><NxgSwitch :model-value="!row.disabled" :label="`Enable ${row.name}`" @update:model-value="(v) => setOn('Assignment Rule', row, 'disabled', 0, v, row.name)" /></template>
				</DataTable>
			</template>

			<template v-else-if="tab === 'jobs'">
				<DataTable :columns="[{ key: 'method', label: 'Job' }, { key: 'frequency', label: 'Schedule' }, { key: 'last_execution', label: 'Last run' }, { key: 'next_execution', label: 'Next run' }, { key: 'health', label: 'Last 7 days' }, { key: 'actions', label: '', align: 'right' }, { key: 'stopped', label: 'On', align: 'right' }]" :rows="jobs" clickable empty-text="No jobs match" @row-click="(r) => (logsFor = r.name)">
					<template #cell-method="{ row }"><span class="block max-w-[360px] truncate font-mono text-[12px]" :title="row.method">{{ row.method || row.server_script }}</span><span class="text-[11.5px] text-nxg-text-3">{{ row.app }}</span></template>
					<template #cell-frequency="{ row }"><span class="text-nxg-text-2">{{ row.frequency }}<span v-if="row.cron_format" class="font-mono"> · {{ row.cron_format }}</span></span></template>
					<template #cell-last_execution="{ row }"><span class="whitespace-nowrap text-nxg-text-2" :title="fmtDateTime(row.last_execution)">{{ row.last_execution ? timeAgo(row.last_execution) : "Never" }}</span></template>
					<template #cell-next_execution="{ row }"><span class="whitespace-nowrap text-nxg-text-2">{{ row.stopped ? "—" : fmtDateTime(row.next_execution) || "—" }}</span></template>
					<template #cell-health="{ row }"><NxgStatus v-if="row.failures_7d" status="failed" :label="`${row.failures_7d} of ${row.runs_7d} failed`" /><span v-else class="nxg-tnum text-[12.5px] text-nxg-text-2">{{ row.runs_7d ? `${row.runs_7d} logged runs` : row.create_log ? "No runs logged" : "Not logged" }}</span></template>
					<template #cell-actions="{ row }"><button class="nxg-btn nxg-btn-ghost h-7" :disabled="!!row.stopped" @click.stop="runJob(row)">Run now</button></template>
					<template #cell-stopped="{ row }"><span @click.stop><NxgSwitch :model-value="!row.stopped" :label="`Enable ${row.method}`" @update:model-value="(v) => setOn('Scheduled Job Type', row, 'stopped', 0, v, row.method || row.name)" /></span></template>
				</DataTable>
			</template>

			<template v-else-if="tab === 'scripts'">
				<p v-if="!d.server_scripts_enabled" class="border-b border-nxg-border bg-[var(--nxg-warning-soft)] px-4 py-2 text-[12.5px]">Server scripts are disabled for this bench (<code>server_script_enabled</code>), so none of these run.</p>
				<NxgEmpty v-if="!d.server_scripts?.length" text="No server scripts" icon="terminal" />
				<DataTable v-else :columns="[{ key: 'name', label: 'Script' }, { key: 'script_type', label: 'Type' }, { key: 'target', label: 'Runs on' }, { key: 'module', label: 'Module' }, { key: 'modified', label: 'Changed' }, { key: 'disabled', label: 'On', align: 'right' }]" :rows="d.server_scripts.filter((s: any) => match(s.name, s.reference_doctype, s.api_method))">
					<template #cell-name="{ row }"><a :href="$href(`/desk/server-script/${encodeURIComponent(row.name)}`)" class="font-medium hover:underline">{{ row.name }}</a><span v-if="row.allow_guest" class="nxg-chip ml-2" title="Callable without signing in">Guest</span></template>
					<template #cell-target="{ row }"><span class="text-nxg-text-2">{{ row.script_type === "API" ? `/api/method/${row.api_method}` : row.script_type === "Scheduler Event" ? row.event_frequency : `${row.reference_doctype || ""} · ${row.doctype_event || ""}` }}</span></template>
					<template #cell-modified="{ row }"><span class="text-nxg-text-2">{{ timeAgo(row.modified) }}</span></template>
					<template #cell-disabled="{ row }"><NxgSwitch :model-value="!row.disabled" :label="`Enable ${row.name}`" @update:model-value="(v) => setOn('Server Script', row, 'disabled', 0, v, row.name)" /></template>
				</DataTable>
			</template>

			<div v-else class="grid grid-cols-1 gap-6 p-4 lg:grid-cols-2">
				<section>
					<h3 class="mb-2 nxg-micro">Auto repeat · {{ d.auto_repeat?.active ?? 0 }} active</h3>
					<p v-if="d.auto_repeat === null" class="text-[13px] text-nxg-text-2">Auto Repeat is not available.</p>
					<template v-else>
						<div class="mb-3 flex flex-wrap gap-1.5"><span v-for="b in d.auto_repeat.by_doctype" :key="b.reference_doctype" class="nxg-chip">{{ b.reference_doctype }} · {{ b.n }}</span></div>
						<ul class="divide-y divide-nxg-border rounded-nxg border border-nxg-border text-[13px]">
							<li v-for="a in d.auto_repeat.upcoming" :key="a.name" class="flex justify-between gap-3 px-3 py-2"><a :href="$href(`/desk/auto-repeat/${encodeURIComponent(a.name)}`)" class="truncate hover:underline">{{ a.reference_doctype }} {{ a.reference_document }}</a><span class="shrink-0 text-nxg-text-2">{{ a.frequency }} · next {{ a.next_schedule_date }}</span></li>
							<li v-if="!d.auto_repeat.upcoming.length" class="px-3 py-3 text-nxg-text-2">Nothing scheduled.</li>
						</ul>
					</template>
				</section>
				<section>
					<h3 class="mb-2 nxg-micro">Document naming rules</h3>
					<ul class="divide-y divide-nxg-border rounded-nxg border border-nxg-border text-[13px]">
						<li v-for="r in d.naming_rules || []" :key="r.name" class="flex items-center gap-3 px-3 py-2"><a :href="$href(`/desk/document-naming-rule/${encodeURIComponent(r.name)}`)" class="flex-1 truncate hover:underline">{{ r.document_type }}</a><code class="text-[12px] text-nxg-text-2">{{ r.prefix }}…</code><NxgSwitch :model-value="!r.disabled" :label="`Enable naming rule for ${r.document_type}`" @update:model-value="(v) => setOn('Document Naming Rule', r, 'disabled', 0, v, `naming rule for ${r.document_type}`)" /></li>
						<li v-if="!d.naming_rules?.length" class="px-3 py-3 text-nxg-text-2">No naming rules; DocTypes use their own naming series.</li>
					</ul>
					<h3 class="mb-2 mt-5 nxg-micro">Milestone trackers</h3>
					<ul class="divide-y divide-nxg-border rounded-nxg border border-nxg-border text-[13px]">
						<li v-for="m in d.milestones || []" :key="m.name" class="flex items-center gap-3 px-3 py-2"><span class="flex-1">{{ m.document_type }} · <span class="text-nxg-text-2">{{ m.track_field }}</span></span><NxgSwitch :model-value="!m.disabled" :label="`Enable milestone tracker for ${m.document_type}`" @update:model-value="(v) => setOn('Milestone Tracker', m, 'disabled', 0, v, `milestone tracker for ${m.document_type}`)" /></li>
						<li v-if="!d.milestones?.length" class="px-3 py-3 text-nxg-text-2">No milestone trackers.</li>
					</ul>
				</section>
			</div>
		</div>

		<NxgDrawer :open="!!logsFor" title="Job runs" :subtitle="logsFor || ''" width="max-w-[640px]" @close="logsFor = null">
			<div v-if="!logs" class="space-y-2 p-5"><div v-for="i in 6" :key="i" class="nxg-skeleton h-9" /></div>
			<div v-else-if="logs.error" class="p-5 text-[13px] text-nxg-danger">{{ logs.error }}</div>
			<NxgEmpty v-else-if="!logs.rows?.length" text="No runs logged for this job" />
			<ul v-else class="divide-y divide-nxg-border">
				<li v-for="l in logs.rows" :key="l.name" class="px-5 py-2.5 text-[13px]">
					<div class="flex items-center gap-2"><NxgStatus :status="l.status === 'Failed' ? 'failed' : l.status === 'Complete' ? 'success' : 'info'" :label="l.status" /><a :href="l.route" class="ml-auto text-[12px] text-nxg-text-2 hover:underline" :title="fmtDateTime(l.creation)">{{ timeAgo(l.creation) }}</a></div>
					<p v-if="l.error" class="mt-1 font-mono text-[12px] text-nxg-danger">{{ l.error }}</p>
				</li>
			</ul>
		</NxgDrawer>
	</div>
</template>
