<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from "vue";

/** Lightweight popover menu: click-outside and Escape close it. */
const props = withDefaults(defineProps<{ align?: "left" | "right"; width?: string; placement?: "bottom" | "top" }>(), { align: "left", width: "w-56", placement: "bottom" });
const open = ref(false);
const root = ref<HTMLElement | null>(null);

function onDoc(e: MouseEvent) {
	if (root.value && !root.value.contains(e.target as Node)) open.value = false;
}
function onKey(e: KeyboardEvent) {
	if (e.key === "Escape") open.value = false;
}
watch(open, (v) => {
	if (v) {
		document.addEventListener("mousedown", onDoc);
		document.addEventListener("keydown", onKey);
	} else {
		document.removeEventListener("mousedown", onDoc);
		document.removeEventListener("keydown", onKey);
	}
});
onBeforeUnmount(() => (open.value = false));
const close = () => (open.value = false);
defineExpose({ close });
</script>

<template>
	<div ref="root" class="relative">
		<slot name="trigger" :open="open" :toggle="() => (open = !open)" />
		<transition enter-active-class="transition duration-100 ease-out" enter-from-class="opacity-0 scale-[0.98]" leave-active-class="transition duration-75" leave-to-class="opacity-0">
			<div
				v-if="open"
				role="menu"
				class="absolute z-50 overflow-hidden rounded-nxg border border-nxg-border bg-nxg-surface p-1 shadow-e2"
				:class="[props.width, props.align === 'right' ? 'right-0' : 'left-0', props.placement === 'top' ? 'bottom-full mb-1.5' : 'top-full mt-1.5']"
				@click="($event.target as HTMLElement).closest('[data-close]') && close()"
			>
				<slot :close="close" />
			</div>
		</transition>
	</div>
</template>
