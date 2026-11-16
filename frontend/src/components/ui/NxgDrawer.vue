<script setup lang="ts">
import { onBeforeUnmount, watch } from "vue";
import Icon from "./Icon.vue";
/** Contextual side panel. Escape or the backdrop closes it. */
const props = withDefaults(defineProps<{ open: boolean; title?: string; subtitle?: string; width?: string }>(), { width: "max-w-[560px]" });
const emit = defineEmits<{ close: [] }>();
function onKey(e: KeyboardEvent) {
	if (e.key === "Escape") emit("close");
}
watch(() => props.open, (v) => (v ? window.addEventListener("keydown", onKey) : window.removeEventListener("keydown", onKey)), { immediate: true });
onBeforeUnmount(() => window.removeEventListener("keydown", onKey));
</script>

<template>
	<Teleport to="body">
		<transition enter-active-class="transition duration-150" enter-from-class="opacity-0" leave-active-class="transition duration-100" leave-to-class="opacity-0">
			<div v-if="open" class="fixed inset-0 z-50 bg-[rgba(28,10,8,0.35)]" @click="emit('close')" />
		</transition>
		<transition enter-active-class="transition duration-200 ease-out" enter-from-class="translate-x-full" leave-active-class="transition duration-150 ease-in" leave-to-class="translate-x-full">
			<aside v-if="open" role="dialog" aria-modal="true" :aria-label="title" class="fixed inset-y-0 right-0 z-50 flex w-full flex-col border-l border-nxg-border bg-nxg-surface shadow-e3" :class="width">
				<header class="flex items-start justify-between gap-3 border-b border-nxg-border px-5 py-4">
					<div class="min-w-0"><slot name="header"><h2 class="truncate text-[16px] font-semibold">{{ title }}</h2><p v-if="subtitle" class="truncate text-[12.5px] text-nxg-text-2">{{ subtitle }}</p></slot></div>
					<button class="nxg-icon-btn -mr-1.5 shrink-0" aria-label="Close panel" @click="emit('close')"><Icon name="x" :size="17" /></button>
				</header>
				<div class="nxg-scroll min-h-0 flex-1 overflow-y-auto"><slot /></div>
				<footer v-if="$slots.footer" class="flex items-center justify-end gap-2 border-t border-nxg-border px-5 py-3"><slot name="footer" /></footer>
			</aside>
		</transition>
	</Teleport>
</template>
