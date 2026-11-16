<script setup lang="ts">
import { computed } from "vue";
import Icon from "./Icon.vue";
import Sparkline from "./Sparkline.vue";
import { fmtMoney, fmtNumber } from "@/composables/format";

const props = defineProps<{
	label: string;
	value: number | null | undefined;
	delta?: number | null;
	deltaLabel?: string;
	secondary?: string | null;
	trend?: number[] | null;
	href?: string;
	hint?: string;
	loading?: boolean;
	icon?: string;
	/** For metrics where an increase is bad (e.g. failed jobs). */
	invert?: boolean;
	/** The server withheld this figure: the user cannot read its source. */
	restricted?: boolean;
	/** Show the value as money in this currency (compact). */
	currency?: string | null;
	/** Appended to the value, e.g. "%". */
	suffix?: string;
}>();
const shown = computed(() => (props.currency ? fmtMoney(props.value, props.currency, true) : fmtNumber(props.value) + (props.suffix && props.value != null ? props.suffix : "")));

const unavailable = computed(() => !props.loading && !props.restricted && (props.value === null || props.value === undefined));
const deltaTone = computed(() => {
	if (props.delta === null || props.delta === undefined || props.delta === 0) return "text-nxg-text-2";
	const up = props.delta > 0;
	return up !== !!props.invert ? "text-nxg-success" : "text-nxg-danger";
});
</script>

<template>
	<component :is="href && !restricted ? 'a' : 'div'" :href="restricted ? undefined : href" :title="hint" class="nxg-panel group flex min-w-0 flex-col justify-between gap-2 px-4 py-3.5 transition-colors" :class="href && 'hover:border-nxg-border-strong'">
		<div class="flex items-center justify-between gap-2">
			<span class="flex min-w-0 items-center gap-1.5 truncate text-[12.5px] font-medium text-nxg-text-2" :title="label">
				<Icon v-if="icon" :name="icon" :size="14" />{{ label }}
			</span>
			<Icon v-if="href" name="arrow-up-right" :size="14" class="text-nxg-text-3 opacity-0 transition-opacity group-hover:opacity-100" />
		</div>
		<div v-if="loading" class="nxg-skeleton h-8 w-20" />
		<div v-else class="flex items-end justify-between gap-2">
			<div class="min-w-0">
				<div v-if="restricted" class="flex items-center gap-1.5 text-[13px] font-medium text-nxg-text-3" title="Your role cannot see this figure"><Icon name="lock" :size="13" />Restricted</div>
				<div v-else-if="unavailable" class="text-[13px] font-medium text-nxg-text-3" title="The source for this figure is not installed on this site">Not available</div>
				<div v-else class="nxg-tnum truncate text-[26px] font-semibold leading-8 tracking-[-0.01em]" :title="currency ? fmtMoney(value, currency) : undefined">{{ shown }}</div>
				<div class="mt-0.5 flex items-center gap-1.5 truncate text-[12px]">
					<span v-if="delta !== null && delta !== undefined" class="nxg-tnum inline-flex items-center font-medium" :class="deltaTone">
						<Icon :name="delta >= 0 ? 'arrow-up-right' : 'arrow-down-right'" :size="13" :stroke-width="2" />{{ Math.abs(delta) }}%
					</span>
					<span v-if="deltaLabel && delta !== null && delta !== undefined" class="text-nxg-text-3">{{ deltaLabel }}</span>
					<span v-if="secondary" class="truncate text-nxg-text-2">{{ secondary }}</span>
				</div>
			</div>
			<Sparkline v-if="trend && trend.length > 1" :values="trend" />
		</div>
	</component>
</template>
