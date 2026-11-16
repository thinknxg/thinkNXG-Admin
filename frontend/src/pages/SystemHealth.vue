<script setup lang="ts">
import { computed, ref, watch } from "vue";
import Icon from "@/components/ui/Icon.vue";
import NxgPanel from "@/components/ui/NxgPanel.vue";
import NxgStatus from "@/components/ui/NxgStatus.vue";
import HealthPanel from "@/components/dashboard/HealthPanel.vue";
import { usePanel } from "@/data/api";
import { fmtBytes, fmtNumber, timeAgo } from "@/composables/format";

const live = usePanel<any>("thinknxg_admin.api.health.get_live_health");
const roundTrip = computed(() => live.state.ms);

// The full V16 System Health Report is heavier, so it loads only when asked.
const report = ref<any>(null);
const reportLoading = ref(false);
const reportError = ref<string | null>(null);
import { call } from "frappe-ui";
import { errorMessage } from "@/data/api";
async function loadReport() {
	reportLoading.value = true;
	reportError.value = null;
	try {
		report.value = await call("thinknxg_admin.api.health.get_full_report");
	} catch (e) {
		reportError.value = errorMessage(e);
	} finally {
		reportLoading.value = false;
	}
}
const queues = computed(() => live.state.data?.checks?.find((c: any) => c.key === "queues")?.queues || []);
const facts = computed(() => {
	const r = report.value;
	if (!r) return [];
	return [
		{ label: "Database", value: [r.database, r.database_version].filter(Boolean).join(" ") || "—" },
		{ label: "Database size", value: r.db_storage_usage != null ? `${fmtNumber(r.db_storage_usage)} MB` : "—" },
		{ label: "Cache keys", value: fmtNumber(r.cache_keys) },
		{ label: "Cache memory", value: r.cache_memory_usage || "—" },
		{ label: "Socket.IO", value: r.socketio_ping_check ? `${r.socketio_ping_check} (${r.socketio_transport_mode || "?"})` : "—" },
		{ label: "Background jobs check", value: r.background_jobs_check || "—" },
		{ label: "Public files", value: r.public_files_size != null ? `${fmtNumber(r.public_files_size)} MB` : "—" },
		{ label: "Private files", value: r.private_files_size != null ? `${fmtNumber(r.private_files_size)} MB` : "—" },
		{ label: "Backups on site", value: r.onsite_backups != null ? `${r.onsite_backups} (${fmtNumber(r.backups_size)} MB)` : "—" },
		{ label: "Outgoing email (failed / pending)", value: `${fmtNumber(r.failed_emails)} / ${fmtNumber(r.pending_emails)}` },
		{ label: "Errors (report window)", value: fmtNumber(r.total_errors) },
		{ label: "Active sessions", value: fmtNumber(r.active_sessions) },
		{ label: "Failed logins", value: fmtNumber(r.failed_logins) },
	];
});
const storage = computed(() => live.state.data?.checks?.find((c: any) => c.key === "storage"));
</script>

<template>
	<div class="mx-auto w-full max-w-[1280px] px-4 pb-10 pt-6 sm:px-6">
		<div class="mb-5 flex flex-wrap items-end justify-between gap-3">
			<div>
				<h1 class="text-[20px] font-semibold leading-7">System Health</h1>
				<p class="text-[13.5px] text-nxg-text-2">Live checks of the services this site depends on, plus the full thinkNXG System Health Report.</p>
			</div>
			<div class="flex gap-2">
				<button class="nxg-btn nxg-btn-secondary" :disabled="live.state.loading" @click="live.load(true)"><Icon name="refresh-cw" :size="14" :class="live.state.loading && 'animate-spin'" />Re-run checks</button>
				<a href="/thinknxg/admin/doc/system-health-report/System%20Health%20Report" class="nxg-btn nxg-btn-ghost">Open full report<Icon name="chevron-right" :size="13" /></a>
			</div>
		</div>

		<div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
			<HealthPanel :state="live.state" :round-trip="roundTrip" class="lg:col-span-1" @retry="live.load(true)" />
			<div class="flex flex-col gap-4 lg:col-span-2">
				<NxgPanel title="Queues" subtitle="RQ queues for this bench" :loading="live.state.loading && !live.state.data" :error="live.state.error" :empty="!!live.state.data && !queues.length" empty-text="No queues reported" @retry="live.load(true)">
					<table class="w-full text-left text-[13px]">
						<thead><tr class="border-b border-nxg-border"><th class="pb-2 nxg-micro">Queue</th><th class="pb-2 text-right nxg-micro">Queued</th><th class="pb-2 text-right nxg-micro">Running</th><th class="pb-2 text-right nxg-micro">Failed</th></tr></thead>
						<tbody class="divide-y divide-nxg-border">
							<tr v-for="q in queues" :key="q.name">
								<td class="py-2 font-medium">{{ q.name }}</td>
								<td class="nxg-tnum py-2 text-right">{{ q.queued }}</td>
								<td class="nxg-tnum py-2 text-right">{{ q.running }}</td>
								<td class="nxg-tnum py-2 text-right"><a v-if="q.failed" :href="$href('/desk/rq-job?status=failed')" class="font-medium text-nxg-danger hover:underline">{{ q.failed }}</a><span v-else>0</span></td>
							</tr>
						</tbody>
					</table>
				</NxgPanel>
				<NxgPanel v-if="storage" title="Storage" :subtitle="storage.detail" :loading="false">
					<div class="h-2 w-full rounded-full bg-nxg-surface-2" role="meter" :aria-valuenow="storage.used_pct" aria-valuemin="0" aria-valuemax="100" aria-label="Disk used">
						<div class="h-2 rounded-full" :class="storage.status === 'ok' ? 'bg-[var(--nxg-chart-1)]' : storage.status === 'warning' ? 'bg-nxg-warning' : 'bg-nxg-danger'" :style="{ width: `${storage.used_pct || 0}%` }" />
					</div>
					<div class="nxg-tnum mt-2 flex justify-between text-[12.5px] text-nxg-text-2"><span>{{ storage.used_pct }}% used</span><span>{{ fmtBytes(storage.free_bytes) }} free of {{ fmtBytes(storage.total_bytes) }}</span></div>
				</NxgPanel>
			</div>
		</div>

		<NxgPanel class="mt-4" title="System Health Report" subtitle="The framework's full diagnostic: database, cache, email, backups, workers, failing jobs" :loading="reportLoading" :error="reportError" @retry="loadReport">
			<div v-if="!report && !reportLoading" class="flex flex-col items-start gap-2 py-2">
				<p class="text-[13px] text-nxg-text-2">This report runs several heavier queries, so it is generated on request.</p>
				<button class="nxg-btn nxg-btn-primary" @click="loadReport"><Icon name="activity" :size="14" />Generate report</button>
			</div>
			<template v-else-if="report">
				<p class="mb-3 text-[12px] text-nxg-text-3">Generated {{ timeAgo(report.generated_at) }}</p>
				<dl class="grid grid-cols-1 gap-x-6 sm:grid-cols-2 lg:grid-cols-3">
					<div v-for="f in facts" :key="f.label" class="flex justify-between gap-3 border-b border-nxg-border py-2 text-[13px]"><dt class="text-nxg-text-2">{{ f.label }}</dt><dd class="nxg-tnum text-right font-medium">{{ f.value }}</dd></div>
				</dl>
				<div class="mt-5 grid grid-cols-1 gap-6 lg:grid-cols-2">
					<div>
						<h3 class="mb-2 nxg-micro">Top errors</h3>
						<p v-if="!report.top_errors?.length" class="text-[13px] text-nxg-text-2">None recorded.</p>
						<ul v-else class="divide-y divide-nxg-border text-[13px]">
							<li v-for="(e, i) in report.top_errors" :key="i" class="flex justify-between gap-3 py-1.5"><span class="truncate">{{ e.title || e.method || e.error || "Error" }}</span><span class="nxg-tnum shrink-0 text-nxg-text-2">{{ e.occurrences ?? e.count ?? "" }}</span></li>
						</ul>
					</div>
					<div>
						<h3 class="mb-2 nxg-micro">Failing scheduled jobs</h3>
						<p v-if="!report.failing_scheduled_jobs?.length" class="text-[13px] text-nxg-text-2">None.</p>
						<ul v-else class="divide-y divide-nxg-border text-[13px]">
							<li v-for="(j, i) in report.failing_scheduled_jobs" :key="i" class="flex items-center justify-between gap-3 py-1.5"><span class="truncate">{{ j.scheduled_job_type || j.method || "Job" }}</span><NxgStatus status="failed" :label="`${j.failure_rate ?? ''}${j.failure_rate != null ? '%' : 'Failing'}`" /></li>
						</ul>
					</div>
				</div>
			</template>
		</NxgPanel>
	</div>
</template>
