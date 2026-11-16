<script setup lang="ts">
import { onBeforeUnmount, watch } from "vue";
import Icon from "./Icon.vue";
const props = withDefaults(defineProps<{ open: boolean; title: string; description?: string; width?: string }>(), { width: "max-w-[480px]" });
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
			<div v-if="open" class="fixed inset-0 z-[55] flex items-center justify-center bg-[rgba(28,10,8,0.45)] px-3" @mousedown.self="emit('close')">
				<div role="dialog" aria-modal="true" :aria-label="title" class="w-full rounded-nxg-lg border border-nxg-border bg-nxg-surface shadow-e3" :class="width">
					<div class="flex items-start justify-between gap-3 px-5 pb-2 pt-4">
						<div><h2 class="text-[16px] font-semibold">{{ title }}</h2><p v-if="description" class="mt-0.5 text-[13px] text-nxg-text-2">{{ description }}</p></div>
						<button class="nxg-icon-btn -mr-1.5" aria-label="Close" @click="emit('close')"><Icon name="x" :size="17" /></button>
					</div>
					<div class="nxg-scroll max-h-[70vh] overflow-y-auto px-5 pb-2"><slot /></div>
					<div v-if="$slots.footer" class="flex items-center justify-end gap-2 px-5 pb-4 pt-3"><slot name="footer" /></div>
				</div>
			</div>
		</transition>
	</Teleport>
</template>
