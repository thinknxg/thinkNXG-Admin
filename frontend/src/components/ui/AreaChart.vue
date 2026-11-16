<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

/** One series over time: 2px line, soft area, recessive grid, crosshair + tooltip on hover.
 *  The panel title names the series, so no legend box is drawn. */
interface Point { date: string; [k: string]: any }
const props = withDefaults(defineProps<{ points: Point[]; valueKey: string; valueLabel: string; secondaryKey?: string; secondaryLabel?: string; height?: number }>(), { height: 168 });

const el = ref<HTMLElement | null>(null);
const width = ref(600);
let ro: ResizeObserver | null = null;
onMounted(() => {
	if (!el.value) return;
	width.value = el.value.clientWidth || 600;
	ro = new ResizeObserver(([e]) => (width.value = Math.max(240, e.contentRect.width)));
	ro.observe(el.value);
});
onBeforeUnmount(() => ro?.disconnect());

const compact = new Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 1 });
const tickText = (v: number) => (Math.abs(v) >= 10000 ? compact.format(v) : new Intl.NumberFormat().format(v));
const max = computed(() => {
	const m = Math.max(1, ...props.points.map((p) => Number(p[props.valueKey]) || 0));
	const step = m <= 5 ? 1 : Math.pow(10, Math.floor(Math.log10(m)));
	return Math.ceil(m / step) * step;
});
const ticks = computed(() => [0, max.value / 2, max.value].map((v) => Math.round(v)));
// Left padding fits the widest tick label, so large values are never clipped.
const pad = computed(() => ({ l: Math.max(28, 12 + 6.6 * Math.max(...ticks.value.map((t) => tickText(t).length))), r: 8, t: 10, b: 22 }));
const X = (i: number) => pad.value.l + (props.points.length <= 1 ? 0 : (i * (width.value - pad.value.l - pad.value.r)) / (props.points.length - 1));
const Y = (v: number) => pad.value.t + (1 - v / max.value) * (props.height - pad.value.t - pad.value.b);
const line = computed(() => props.points.map((p, i) => `${i ? "L" : "M"}${X(i).toFixed(1)} ${Y(Number(p[props.valueKey]) || 0).toFixed(1)}`).join(""));
const area = computed(() => (props.points.length ? `${line.value}L${X(props.points.length - 1)} ${Y(0)}L${X(0)} ${Y(0)}Z` : ""));
const labels = computed(() => {
	const n = props.points.length;
	if (!n) return [];
	const every = Math.max(1, Math.ceil(n / Math.max(2, Math.floor(width.value / 90))));
	return props.points.map((p, i) => ({ i, text: fmtDay(p.date) })).filter((l) => l.i % every === 0 || l.i === n - 1).filter((l, idx, arr) => !(l.i === n - 1 && idx > 0 && l.i - arr[idx - 1].i < every * 0.6));
});
function fmtDay(d: string) {
	const dt = new Date(d + "T00:00:00");
	return dt.toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

const hover = ref<number | null>(null);
function onMove(e: MouseEvent) {
	const rect = (e.currentTarget as SVGElement).getBoundingClientRect();
	const x = e.clientX - rect.left;
	const n = props.points.length;
	if (n < 1) return;
	const i = Math.round(((x - pad.value.l) / (width.value - pad.value.l - pad.value.r)) * (n - 1));
	hover.value = Math.max(0, Math.min(n - 1, i));
}
const tip = computed(() => (hover.value === null ? null : props.points[hover.value]));
</script>

<template>
	<div ref="el" class="relative w-full select-none">
		<svg :width="width" :height="height" role="img" :aria-label="`${valueLabel} per day`" @mousemove="onMove" @mouseleave="hover = null">
			<g>
				<line v-for="t in ticks" :key="t" :x1="pad.l" :x2="width - pad.r" :y1="Y(t)" :y2="Y(t)" stroke="var(--nxg-chart-grid)" />
				<text v-for="t in ticks" :key="'l' + t" :x="pad.l - 8" :y="Y(t) + 4" text-anchor="end" class="nxg-tnum fill-[var(--nxg-text-3)] text-[11px]">{{ tickText(t) }}</text>
				<text v-for="l in labels" :key="'x' + l.i" :x="X(l.i)" :y="height - 6" :text-anchor="l.i === 0 ? 'start' : l.i === points.length - 1 ? 'end' : 'middle'" class="fill-[var(--nxg-text-3)] text-[11px]">{{ l.text }}</text>
			</g>
			<path :d="area" fill="var(--nxg-chart-1-soft)" />
			<path :d="line" fill="none" stroke="var(--nxg-chart-1)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />
			<g v-if="hover !== null && tip">
				<line :x1="X(hover)" :x2="X(hover)" :y1="pad.t" :y2="Y(0)" stroke="var(--nxg-border-strong)" stroke-dasharray="3 3" />
				<circle :cx="X(hover)" :cy="Y(Number(tip[valueKey]) || 0)" r="4.5" fill="var(--nxg-chart-1)" stroke="var(--nxg-surface)" stroke-width="2" />
			</g>
		</svg>
		<div
			v-if="tip && hover !== null"
			class="pointer-events-none absolute top-0 z-10 rounded-nxg border border-nxg-border bg-nxg-surface px-2.5 py-1.5 text-[12px] shadow-e2"
			:style="{ left: `${Math.min(Math.max(X(hover) - 70, 0), width - 150)}px` }"
		>
			<div class="font-medium">{{ fmtDay(tip.date) }}</div>
			<div class="nxg-tnum text-nxg-text-2">{{ valueLabel }}: <span class="font-semibold text-nxg-text">{{ tip[valueKey] }}</span></div>
			<div v-if="secondaryKey" class="nxg-tnum text-nxg-text-2">{{ secondaryLabel }}: <span class="text-nxg-text">{{ tip[secondaryKey] }}</span></div>
		</div>
	</div>
</template>
