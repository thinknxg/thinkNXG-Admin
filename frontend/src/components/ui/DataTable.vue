<script setup lang="ts" generic="T extends Record<string, any>">
import { computed } from "vue";
import Icon from "./Icon.vue";

/** Dense, accessible data table: sortable headers, row selection, row click, slots per cell. */
export interface Column { key: string; label: string; sortable?: boolean; width?: string; align?: "left" | "right" | "center"; class?: string }
const props = defineProps<{ columns: Column[]; rows: T[]; rowKey?: string; loading?: boolean; selectable?: boolean; selected?: string[]; sort?: string; order?: "asc" | "desc"; emptyText?: string; clickable?: boolean }>();
const emit = defineEmits<{ "update:selected": [string[]]; sort: [string]; rowClick: [T] }>();
const key = (r: T) => String(r[props.rowKey || "name"]);
const allSelected = computed(() => !!props.rows.length && props.rows.every((r) => props.selected?.includes(key(r))));
function toggleAll() {
	emit("update:selected", allSelected.value ? [] : props.rows.map(key));
}
function toggle(r: T) {
	const k = key(r);
	const s = props.selected || [];
	emit("update:selected", s.includes(k) ? s.filter((x) => x !== k) : [...s, k]);
}
</script>

<template>
	<div class="overflow-x-auto">
		<table class="w-full text-left text-[13px]">
			<thead class="sticky top-0 z-[1] bg-nxg-surface">
				<tr class="border-b border-nxg-border">
					<th v-if="selectable" class="w-10 px-3 py-2"><input type="checkbox" class="rounded border-nxg-border-strong text-nxg-espresso focus:ring-0" :checked="allSelected" aria-label="Select all rows" @change="toggleAll" /></th>
					<th v-for="c in columns" :key="c.key" class="whitespace-nowrap px-3 py-2 nxg-micro" :style="{ width: c.width }" :class="[c.align === 'right' && 'text-right', c.align === 'center' && 'text-center']" :aria-sort="sort === c.key ? (order === 'desc' ? 'descending' : 'ascending') : undefined">
						<button v-if="c.sortable" class="inline-flex items-center gap-1 uppercase hover:text-nxg-text" @click="emit('sort', c.key)">
							{{ c.label }}<Icon :name="sort === c.key ? (order === 'desc' ? 'arrow-down' : 'arrow-up') : 'chevrons-up-down'" :size="12" />
						</button>
						<template v-else>{{ c.label }}</template>
					</th>
				</tr>
			</thead>
			<tbody class="divide-y divide-nxg-border">
				<template v-if="loading && !rows.length">
					<tr v-for="i in 6" :key="'s' + i"><td :colspan="columns.length + (selectable ? 1 : 0)" class="px-3 py-2.5"><div class="nxg-skeleton h-4" :style="{ width: `${70 + (i % 3) * 10}%` }" /></td></tr>
				</template>
				<tr v-else-if="!rows.length"><td :colspan="columns.length + (selectable ? 1 : 0)" class="px-3 py-10 text-center text-nxg-text-2">{{ emptyText || "No records match these filters" }}</td></tr>
				<tr
					v-for="r in rows"
					:key="key(r)"
					class="group transition-colors"
					:class="[clickable && 'cursor-pointer', selected?.includes(key(r)) ? 'bg-[var(--nxg-brand-red-soft)]' : 'hover:bg-nxg-surface-2/60', loading && 'opacity-60']"
					@click="clickable && emit('rowClick', r)"
				>
					<td v-if="selectable" class="px-3 py-2" @click.stop><input type="checkbox" class="rounded border-nxg-border-strong text-nxg-espresso focus:ring-0" :checked="selected?.includes(key(r))" :aria-label="`Select ${key(r)}`" @change="toggle(r)" /></td>
					<td v-for="c in columns" :key="c.key" class="px-3 py-2" :class="[c.align === 'right' && 'text-right', c.align === 'center' && 'text-center', c.class]">
						<slot :name="`cell-${c.key}`" :row="r" :value="r[c.key]">{{ r[c.key] ?? "—" }}</slot>
					</td>
				</tr>
			</tbody>
		</table>
	</div>
</template>
