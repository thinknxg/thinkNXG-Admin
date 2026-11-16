<script setup lang="ts">
import { ref, watch } from "vue";
import { call } from "frappe-ui";
import Icon from "@/components/ui/Icon.vue";

/** Link field: live search through thinkNXG's own link search
 *  (frappe.desk.search.search_link), so its permission and filter rules apply. */
const props = defineProps<{ modelValue: string | null | undefined; doctype: string; disabled?: boolean; placeholder?: string; referenceDoctype?: string; invalid?: boolean; inputId?: string }>();
const emit = defineEmits<{ "update:modelValue": [string | null] }>();
const text = ref(props.modelValue || "");
const open = ref(false);
const results = ref<{ value: string; description?: string; label?: string }[]>([]);
const active = ref(0);
let timer: number | undefined;
let seq = 0;

watch(() => props.modelValue, (v) => (text.value = v || ""));

function search() {
	window.clearTimeout(timer);
	timer = window.setTimeout(async () => {
		const mine = ++seq;
		try {
			const res: any = await call("frappe.desk.search.search_link", { doctype: props.doctype, txt: text.value, page_length: 10, reference_doctype: props.referenceDoctype });
			if (mine === seq) {
				results.value = (Array.isArray(res) ? res : res?.message || []).map((r: any) => ({ value: r.value, description: r.description, label: r.label }));
				active.value = 0;
			}
		} catch {
			if (mine === seq) results.value = [];
		}
	}, 160);
}
function focus() {
	if (props.disabled) return;
	open.value = true;
	search();
}
function pick(v: string | null) {
	text.value = v || "";
	emit("update:modelValue", v);
	open.value = false;
}
function blur() {
	window.setTimeout(() => {
		open.value = false;
		// Free text that is not a pick is cleared, as in the Desk.
		if (text.value !== (props.modelValue || "")) {
			if (!text.value) pick(null);
			else text.value = props.modelValue || "";
		}
	}, 150);
}
function key(e: KeyboardEvent) {
	if (!open.value) return;
	if (e.key === "ArrowDown") {
		e.preventDefault();
		active.value = Math.min(results.value.length - 1, active.value + 1);
	} else if (e.key === "ArrowUp") {
		e.preventDefault();
		active.value = Math.max(0, active.value - 1);
	} else if (e.key === "Enter" && results.value[active.value]) {
		e.preventDefault();
		pick(results.value[active.value].value);
	} else if (e.key === "Escape") {
		open.value = false;
	}
}
</script>

<template>
	<div class="relative">
		<input
			:id="inputId"
			v-model="text"
			class="nxg-input h-8 w-full pr-7"
			:class="invalid && 'border-nxg-danger'"
			:disabled="disabled"
			:placeholder="placeholder || `Search ${doctype}`"
			role="combobox"
			:aria-expanded="open"
			autocomplete="off"
			@focus="focus"
			@input="open = true; search()"
			@keydown="key"
			@blur="blur"
		/>
		<Icon name="search" :size="13" class="pointer-events-none absolute right-2 top-2.5 text-nxg-text-3" />
		<ul v-if="open && !disabled" role="listbox" class="nxg-scroll absolute z-40 mt-1 max-h-64 w-full overflow-y-auto rounded-nxg border border-nxg-border bg-nxg-surface p-1 shadow-e2">
			<li v-if="!results.length" class="px-2 py-1.5 text-[12.5px] text-nxg-text-2">No matches</li>
			<li
				v-for="(r, i) in results"
				:key="r.value"
				role="option"
				:aria-selected="i === active"
				class="cursor-pointer rounded-nxg-sm px-2 py-1.5 text-[13px]"
				:class="i === active ? 'bg-nxg-surface-2' : ''"
				@mousedown.prevent="pick(r.value)"
				@mouseenter="active = i"
			>
				<div class="truncate font-medium">{{ r.label || r.value }}</div>
				<div v-if="r.description || (r.label && r.label !== r.value)" class="truncate text-[11.5px] text-nxg-text-2">{{ r.label && r.label !== r.value ? r.value : "" }} {{ r.description }}</div>
			</li>
		</ul>
	</div>
</template>
