<script setup lang="ts">
import { computed } from "vue";
import Icon from "./Icon.vue";

/** Status is always icon + label + colour, never colour alone. */
const props = withDefaults(defineProps<{ status: string; label?: string; size?: "sm" | "md" }>(), { size: "sm" });
const meta: Record<string, { icon: string; cls: string; text: string }> = {
	ok: { icon: "circle-check", cls: "text-nxg-success bg-[var(--nxg-success-soft)]", text: "Healthy" },
	success: { icon: "circle-check", cls: "text-nxg-success bg-[var(--nxg-success-soft)]", text: "Success" },
	warning: { icon: "triangle-alert", cls: "text-nxg-warning bg-[var(--nxg-warning-soft)]", text: "Warning" },
	serious: { icon: "circle-alert", cls: "text-nxg-warning bg-[var(--nxg-warning-soft)]", text: "Serious" },
	critical: { icon: "circle-x", cls: "text-nxg-danger bg-[var(--nxg-danger-soft)]", text: "Critical" },
	failed: { icon: "circle-x", cls: "text-nxg-danger bg-[var(--nxg-danger-soft)]", text: "Failed" },
	info: { icon: "info", cls: "text-nxg-info bg-[var(--nxg-info-soft)]", text: "Info" },
	unknown: { icon: "circle", cls: "text-nxg-text-2 bg-nxg-surface-2", text: "Unknown" },
};
const m = computed(() => meta[props.status?.toLowerCase()] || meta.unknown);
</script>

<template>
	<span class="inline-flex items-center gap-1 rounded-full font-medium" :class="[m.cls, size === 'sm' ? 'h-5 px-1.5 text-[11.5px]' : 'h-6 px-2 text-[12.5px]']">
		<Icon :name="m.icon" :size="size === 'sm' ? 12 : 14" :stroke-width="2" />
		{{ label || m.text }}
	</span>
</template>
