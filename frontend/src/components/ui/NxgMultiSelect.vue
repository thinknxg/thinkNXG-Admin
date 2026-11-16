<script setup lang="ts">
import { computed, ref } from "vue";
import Icon from "./Icon.vue";
import NxgMenu from "./NxgMenu.vue";
/** Chip picker with search. Values are plain strings. */
const props = withDefaults(defineProps<{ modelValue: string[]; options: string[]; placeholder?: string; disabled?: boolean; locked?: string[] }>(), { placeholder: "Add…" });
const emit = defineEmits<{ "update:modelValue": [string[]] }>();
const q = ref("");
const filtered = computed(() => props.options.filter((o) => !props.modelValue.includes(o) && o.toLowerCase().includes(q.value.toLowerCase())).slice(0, 60));
function add(o: string) {
	emit("update:modelValue", [...props.modelValue, o]);
	q.value = "";
}
function remove(o: string) {
	emit("update:modelValue", props.modelValue.filter((v) => v !== o));
}
</script>

<template>
	<div class="flex flex-wrap items-center gap-1.5 rounded-nxg border border-nxg-border-strong bg-nxg-surface p-1.5">
		<span v-for="v in modelValue" :key="v" class="inline-flex h-6 items-center gap-1 rounded-nxg-sm bg-nxg-surface-2 pl-2 pr-1 text-[12.5px]">
			{{ v }}
			<button v-if="!disabled && !(locked || []).includes(v)" class="rounded p-0.5 text-nxg-text-3 hover:text-nxg-text" :aria-label="`Remove ${v}`" @click="remove(v)"><Icon name="x" :size="12" /></button>
		</span>
		<NxgMenu v-if="!disabled" width="w-64">
			<template #trigger="{ toggle }">
				<button type="button" class="inline-flex h-6 items-center gap-1 rounded-nxg-sm px-1.5 text-[12.5px] text-nxg-text-2 hover:bg-nxg-surface-2 hover:text-nxg-text" @click="toggle"><Icon name="plus" :size="13" />{{ placeholder }}</button>
			</template>
			<input v-model="q" class="nxg-input mb-1 h-8" placeholder="Search…" @keydown.enter.prevent="filtered[0] && add(filtered[0])" />
			<div class="nxg-scroll max-h-56 overflow-y-auto">
				<button v-for="o in filtered" :key="o" class="flex h-8 w-full items-center rounded-nxg-sm px-2 text-left text-[13px] hover:bg-nxg-surface-2" @click="add(o)">{{ o }}</button>
				<div v-if="!filtered.length" class="px-2 py-2 text-[12.5px] text-nxg-text-2">No matches</div>
			</div>
		</NxgMenu>
		<span v-if="!modelValue.length && disabled" class="px-1 text-[12.5px] text-nxg-text-3">None</span>
	</div>
</template>
