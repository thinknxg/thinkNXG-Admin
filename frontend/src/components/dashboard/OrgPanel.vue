<script setup lang="ts">
import NxgPanel from "@/components/ui/NxgPanel.vue";
import Icon from "@/components/ui/Icon.vue";
import type { PanelState } from "@/data/api";
import { fmtNumber } from "@/composables/format";

defineProps<{ state: PanelState<any>; company: string | null }>();
defineEmits<{ retry: [] }>();
</script>

<template>
	<NxgPanel title="Organization" :subtitle="company ? `Scoped to ${company}` : 'All companies'" :loading="state.loading && !state.data" :error="state.error" :href="$href('/desk/company')" href-label="Companies" :skeleton-rows="6" @retry="$emit('retry')">
		<ul class="grid grid-cols-2 gap-2">
			<li v-for="i in state.data?.items || []" :key="i.doctype">
				<a :href="i.value === null ? undefined : i.route" class="flex items-center gap-2.5 rounded-nxg border border-nxg-border px-2.5 py-2 transition-colors" :class="i.value === null ? 'opacity-60' : 'hover:border-nxg-border-strong hover:bg-nxg-surface-2'" :title="i.value === null ? `${i.doctype} is not installed on this site` : `Open ${i.label}`">
					<Icon :name="i.icon" :size="15" class="text-nxg-text-2" />
					<span class="min-w-0 flex-1">
						<span class="block truncate text-[11.5px] text-nxg-text-2">{{ i.label }}</span>
						<span class="nxg-tnum block text-[15px] font-semibold leading-5" :class="i.value === null && 'text-[12px] font-medium text-nxg-text-3'">{{ i.value === null ? "Not available" : fmtNumber(i.value) }}</span>
					</span>
				</a>
			</li>
			<li v-if="state.data && !state.data.business_units_configured" class="col-span-2">
				<a :href="$href('/desk/thinknxg-admin-settings')" class="flex items-center gap-2 rounded-nxg border border-dashed border-nxg-border-strong px-2.5 py-2 text-[12px] text-nxg-text-2 hover:text-nxg-text"><Icon name="layers" :size="14" />Business units: choose a source in Command Center settings</a>
			</li>
		</ul>
	</NxgPanel>
</template>
