<script setup lang="ts">
import { computed } from "vue";
import NxgPanel from "@/components/ui/NxgPanel.vue";
import NxgStatus from "@/components/ui/NxgStatus.vue";
import Icon from "@/components/ui/Icon.vue";
import type { PanelState } from "@/data/api";
import { timeAgo } from "@/composables/format";

const props = defineProps<{ state: PanelState<any> }>();
defineEmits<{ retry: [] }>();
const empty = computed(() => !!props.state.data && !props.state.data.alerts?.length && !props.state.data.actions?.length);
const kindIcon: Record<string, string> = { approval: "circle-check", task: "list-checks" };
</script>

<template>
	<NxgPanel title="Pending actions" :subtitle="state.data ? `${state.data.approval_count ?? 0} approvals · ${state.data.todo_count ?? 0} tasks for you` : 'Approvals, tasks, alerts'" :loading="state.loading && !state.data" :error="state.error" :empty="empty" empty-text="Nothing needs your attention" :skeleton-rows="6" @retry="$emit('retry')">
		<ul v-if="state.data" class="space-y-1.5">
			<li v-for="(a, i) in state.data.alerts" :key="'a' + i">
				<a :href="a.route" class="flex items-start gap-2.5 rounded-nxg border border-nxg-border px-2.5 py-2 hover:border-nxg-border-strong">
					<NxgStatus :status="a.severity" :label="a.severity === 'critical' ? 'Alert' : 'Check'" class="mt-px" />
					<span class="min-w-0 flex-1"><span class="block truncate text-[13px] font-medium">{{ a.title }}</span><span class="block truncate text-[12px] text-nxg-text-2">{{ a.subtitle }}</span></span>
				</a>
			</li>
			<li v-for="(a, i) in state.data.actions" :key="'x' + i">
				<a :href="a.route" class="flex items-start gap-2.5 rounded-nxg px-2.5 py-1.5 hover:bg-nxg-surface-2">
					<Icon :name="kindIcon[a.kind]" :size="15" class="mt-0.5 text-nxg-text-2" />
					<span class="min-w-0 flex-1"><span class="block truncate text-[13px]">{{ a.title }}</span><span class="block truncate text-[12px] text-nxg-text-2">{{ a.subtitle }} · {{ timeAgo(a.creation) }}</span></span>
				</a>
			</li>
		</ul>
	</NxgPanel>
</template>
