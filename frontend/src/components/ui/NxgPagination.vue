<script setup lang="ts">
import { computed } from "vue";
import Icon from "./Icon.vue";
const props = defineProps<{ start: number; pageLength: number; total: number }>();
const emit = defineEmits<{ change: [number] }>();
const end = computed(() => Math.min(props.start + props.pageLength, props.total));
</script>

<template>
	<div class="flex items-center justify-between gap-3 px-3 py-2.5 text-[12.5px] text-nxg-text-2">
		<span class="nxg-tnum">{{ total ? `${start + 1}–${end} of ${total}` : "0 results" }}</span>
		<div class="flex gap-1">
			<button class="nxg-icon-btn h-7 w-7" :disabled="start === 0" aria-label="Previous page" @click="emit('change', Math.max(0, start - pageLength))"><Icon name="chevron-right" :size="15" class="rotate-180" /></button>
			<button class="nxg-icon-btn h-7 w-7" :disabled="end >= total" aria-label="Next page" @click="emit('change', start + pageLength)"><Icon name="chevron-right" :size="15" /></button>
		</div>
	</div>
</template>
