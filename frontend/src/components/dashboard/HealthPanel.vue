<script setup lang="ts">
import NxgPanel from "@/components/ui/NxgPanel.vue";
import NxgStatus from "@/components/ui/NxgStatus.vue";
import Icon from "@/components/ui/Icon.vue";
import type { PanelState } from "@/data/api";

const props = defineProps<{ state: PanelState<any>; roundTrip: number | null; compact?: boolean }>();
defineEmits<{ retry: [] }>();
const icons: Record<string, string> = { app: "layers", database: "database", redis: "cpu", queues: "list-checks", workers: "server", scheduler: "timer", storage: "hard-drive", errors: "triangle-alert" };
const statusLabel: Record<string, string> = { ok: "Healthy", warning: "Warning", critical: "Action", unknown: "Unknown" };
function apiStatus(ms: number | null) {
	if (ms === null) return "unknown";
	return ms < 400 ? "ok" : ms < 1200 ? "warning" : "critical";
}
</script>

<template>
	<NxgPanel title="System health" :subtitle="state.data ? `${state.data.healthy} of ${state.data.total} checks healthy` : 'Live checks'" :loading="state.loading && !state.data" :error="state.error" href="/thinknxg/system-health" href-label="Details" :skeleton-rows="7" @retry="$emit('retry')">
		<ul v-if="state.data" class="divide-y divide-nxg-border">
			<li v-for="c in state.data.checks" :key="c.key" class="flex items-center gap-2.5 py-2">
				<Icon :name="icons[c.key]" :size="15" class="text-nxg-text-2" />
				<div class="min-w-0 flex-1">
					<div class="text-[13px] font-medium leading-5">{{ c.label }}</div>
					<div class="truncate text-[12px] text-nxg-text-2" :title="c.detail">{{ c.detail }}<span v-if="c.latency_ms !== undefined" class="nxg-tnum"> · {{ c.latency_ms }} ms</span></div>
				</div>
				<NxgStatus :status="c.status" :label="statusLabel[c.status]" />
			</li>
			<li class="flex items-center gap-2.5 py-2">
				<Icon name="activity" :size="15" class="text-nxg-text-2" />
				<div class="min-w-0 flex-1">
					<div class="text-[13px] font-medium leading-5">API round-trip</div>
					<div class="truncate text-[12px] text-nxg-text-2" title="Measured by your browser for the health call itself. Server-side latency percentiles need monitor logging or an APM tool.">Measured from your browser<span v-if="roundTrip !== null" class="nxg-tnum"> · {{ roundTrip }} ms</span></div>
				</div>
				<NxgStatus :status="apiStatus(roundTrip)" :label="statusLabel[apiStatus(roundTrip)]" />
			</li>
		</ul>
	</NxgPanel>
</template>
