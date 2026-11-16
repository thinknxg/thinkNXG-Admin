<script setup lang="ts">
import { computed } from "vue";
import NxgPanel from "@/components/ui/NxgPanel.vue";
import AreaChart from "@/components/ui/AreaChart.vue";
import NxgAvatar from "@/components/ui/NxgAvatar.vue";
import NxgEmpty from "@/components/ui/NxgEmpty.vue";
import type { PanelState } from "@/data/api";
import { fmtNumber, timeAgo } from "@/composables/format";

const props = defineProps<{ state: PanelState<any>; series: any[] | null | undefined; seriesLoading: boolean; days: number }>();
defineEmits<{ retry: [] }>();
const stats = computed(() => {
	const d = props.state.data || {};
	return [
		{ label: "Successful sign-ins", value: d.successful_logins, href: "/desk/activity-log?operation=Login&status=Success" },
		{ label: "Failed sign-ins", value: d.failed_logins, href: "/desk/activity-log?operation=Login&status=Failed", warn: (d.failed_logins || 0) > 0 },
		{ label: "Config changes", value: d.config_changes, href: "/desk/version" },
		{ label: "Errors logged", value: d.errors, href: "/desk/error-log", warn: (d.errors || 0) > 0 },
	];
});
const hasSeries = computed(() => (props.series || []).some((p) => p.logins > 0));
</script>

<template>
	<NxgPanel title="System activity" :subtitle="`People signing in per day · last ${days} days`" :loading="state.loading && !state.data" :error="state.error" href="/desk/activity-log" href-label="Activity log" :skeleton-rows="6" @retry="$emit('retry')">
		<dl class="mb-3 grid grid-cols-2 gap-px overflow-hidden rounded-nxg border border-nxg-border bg-nxg-border sm:grid-cols-4">
			<a v-for="s in stats" :key="s.label" :href="s.href" class="bg-nxg-surface px-3 py-2 hover:bg-nxg-surface-2">
				<dt class="truncate text-[11.5px] text-nxg-text-2">{{ s.label }}</dt>
				<dd class="nxg-tnum text-[17px] font-semibold" :class="s.value === null || s.value === undefined ? 'text-nxg-text-3 text-[13px] font-medium' : s.warn ? 'text-nxg-warning' : ''">
					{{ s.value === null || s.value === undefined ? "Not available" : fmtNumber(s.value) }}
				</dd>
			</a>
		</dl>
		<div v-if="seriesLoading && !series" class="nxg-skeleton h-[168px]" />
		<AreaChart v-else-if="series && hasSeries" :points="series" value-key="users" value-label="People" secondary-key="logins" secondary-label="Sign-ins" />
		<NxgEmpty v-else :text="series === null ? 'Activity Log is not available on this site' : `No sign-ins recorded in the last ${days} days`" icon="activity" />
		<div v-if="state.data?.logins?.length" class="mt-3">
			<div class="mb-1 nxg-micro">Recent sign-ins</div>
			<ul class="divide-y divide-nxg-border">
				<li v-for="l in state.data.logins.slice(0, 5)" :key="l.name" class="flex items-center gap-2.5 py-1.5 text-[13px]">
					<NxgAvatar :name="l.full_name || l.user" :size="22" />
					<span class="min-w-0 flex-1 truncate"><span class="font-medium">{{ l.full_name || l.user }}</span> <span class="text-nxg-text-2">{{ l.operation === "Logout" ? "signed out" : l.status === "Failed" ? "failed to sign in" : "signed in" }}</span></span>
					<span v-if="l.ip_address" class="nxg-tnum hidden text-[12px] text-nxg-text-3 sm:inline">{{ l.ip_address }}</span>
					<span class="shrink-0 text-[12px] text-nxg-text-3">{{ timeAgo(l.creation) }}</span>
				</li>
			</ul>
		</div>
	</NxgPanel>
</template>
