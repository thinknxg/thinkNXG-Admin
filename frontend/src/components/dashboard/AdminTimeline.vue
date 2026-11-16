<script setup lang="ts">
import NxgPanel from "@/components/ui/NxgPanel.vue";
import NxgAvatar from "@/components/ui/NxgAvatar.vue";
import NxgStatus from "@/components/ui/NxgStatus.vue";
import type { PanelState } from "@/data/api";
import { fmtDateTime, timeAgo } from "@/composables/format";

defineProps<{ state: PanelState<any[]>; days: number }>();
defineEmits<{ retry: [] }>();
</script>

<template>
	<NxgPanel title="Recent administrative activity" :subtitle="`Users, roles, permissions, workspaces and settings · last ${days} days`" :loading="state.loading && !state.data" :error="state.error" :empty="!!state.data && !state.data.length" empty-text="No administrative changes in this period" :href="$href('/desk/version')" href-label="Full history" :skeleton-rows="5" @retry="$emit('retry')">
		<div class="-mx-4 overflow-x-auto">
			<table class="w-full min-w-[720px] text-left text-[13px]">
				<thead>
					<tr class="border-b border-nxg-border">
						<th class="px-4 pb-2 nxg-micro">Actor</th>
						<th class="pb-2 nxg-micro">Action</th>
						<th class="pb-2 nxg-micro">Resource</th>
						<th class="pb-2 nxg-micro">Change</th>
						<th class="pb-2 nxg-micro">When</th>
						<th class="px-4 pb-2 text-right nxg-micro">Status</th>
					</tr>
				</thead>
				<tbody class="divide-y divide-nxg-border">
					<tr v-for="e in state.data || []" :key="e.id" class="hover:bg-nxg-surface-2/60">
						<td class="px-4 py-2">
							<span class="flex items-center gap-2"><NxgAvatar :name="e.actor_name" :size="22" /><span class="max-w-[160px] truncate font-medium">{{ e.actor_name }}</span></span>
						</td>
						<td class="py-2 pr-3 text-nxg-text-2">{{ e.action }}</td>
						<td class="py-2 pr-3"><a :href="e.route" class="nxg-link block max-w-[220px] truncate" :title="`${e.doctype}: ${e.docname}`"><span class="text-nxg-text-2">{{ e.doctype }}</span> · {{ e.docname }}</a></td>
						<td class="py-2 pr-3 text-[12.5px]">
							<span v-if="e.change" class="flex max-w-[240px] items-center gap-1 truncate"><span class="truncate text-nxg-text-3 line-through decoration-nxg-border-strong">{{ e.change.old ?? "empty" }}</span><span class="text-nxg-text-3">→</span><span class="truncate">{{ e.change.new ?? "empty" }}</span></span>
							<span v-else-if="e.ip" class="nxg-tnum text-nxg-text-3">IP {{ e.ip }}</span>
							<span v-else class="text-nxg-text-3">—</span>
						</td>
						<td class="whitespace-nowrap py-2 pr-3 text-nxg-text-2" :title="fmtDateTime(e.timestamp)">{{ timeAgo(e.timestamp) }}</td>
						<td class="px-4 py-2 text-right"><NxgStatus :status="e.status === 'Failed' ? 'failed' : 'success'" :label="e.status" /></td>
					</tr>
				</tbody>
			</table>
		</div>
	</NxgPanel>
</template>
