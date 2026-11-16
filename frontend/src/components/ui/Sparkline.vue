<script setup lang="ts">
import { computed } from "vue";
/** Single-series trend, no axes. Decorative support for a KPI value that is printed beside it. */
const props = withDefaults(defineProps<{ values: number[]; width?: number; height?: number }>(), { width: 88, height: 28 });
const path = computed(() => {
	const v = props.values || [];
	if (v.length < 2) return { line: "", area: "" };
	const max = Math.max(...v, 1);
	const step = props.width / (v.length - 1);
	const pts = v.map((y, i) => [i * step, props.height - 2 - (y / max) * (props.height - 4)]);
	const line = pts.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join("");
	return { line, area: `${line}L${props.width} ${props.height}L0 ${props.height}Z` };
});
</script>

<template>
	<svg v-if="path.line" :width="width" :height="height" :viewBox="`0 0 ${width} ${height}`" aria-hidden="true" class="overflow-visible">
		<path :d="path.area" fill="var(--nxg-chart-1-soft)" />
		<path :d="path.line" fill="none" stroke="var(--nxg-chart-1)" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round" />
	</svg>
</template>
