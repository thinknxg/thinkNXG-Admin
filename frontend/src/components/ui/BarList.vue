<script setup lang="ts">
import { computed } from "vue";
/** Horizontal magnitude bars, one hue, labels and values in text ink. */
const props = defineProps<{ items: { label: string; value: number; href?: string }[]; unit?: string; format?: (v: number) => string }>();
const show = (v: number) => (props.format ? props.format(v) : v);
const max = computed(() => Math.max(1, ...props.items.map((i) => i.value)));
</script>

<template>
	<ul class="space-y-1.5">
		<li v-for="item in items" :key="item.label">
			<component :is="item.href ? 'a' : 'div'" :href="item.href" class="group block rounded-nxg-sm" :title="`${item.label}: ${show(item.value)} ${unit || ''}`">
				<div class="flex items-center justify-between gap-2 text-[12.5px]">
					<span class="truncate text-nxg-text group-hover:underline">{{ item.label }}</span>
					<span class="nxg-tnum shrink-0 text-nxg-text-2">{{ show(item.value) }}</span>
				</div>
				<div class="mt-1 h-1.5 w-full rounded-full bg-nxg-surface-2">
					<div class="h-1.5 rounded-full bg-[var(--nxg-chart-1)]" :style="{ width: `${Math.max(2, (Math.max(0, item.value) / max) * 100)}%` }" />
				</div>
			</component>
		</li>
	</ul>
</template>
