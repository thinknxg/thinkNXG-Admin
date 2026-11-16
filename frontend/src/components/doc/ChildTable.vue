<script setup lang="ts">
import { computed, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import FieldInput from "./FieldInput.vue";
import { NO_VALUE, TABLES, displayValue, evalCondition, type Doc, type Field } from "./meta";

/** A child table (e.g. invoice items): a compact grid; each row opens inline
 *  with all of its fields. Rows are saved with the parent document. */
const props = defineProps<{ field: Field; rows: Doc[]; fields: Field[]; readonly: boolean; parent: Doc; childDoctype: string; isReadonly: (f: Field, row: Doc) => boolean; invalid: Set<string> }>();
const emit = defineEmits<{ change: [row: Doc, field: Field, value: any]; add: []; remove: [names: string[]] }>();
const open = ref<string | null>(null);
const picked = ref<Set<string>>(new Set());

const valueFields = computed(() => props.fields.filter((f) => !NO_VALUE.has(f.fieldtype) && !TABLES.has(f.fieldtype) && f.fieldname));
const columns = computed(() => {
	const listed = valueFields.value.filter((f) => f.in_list_view && !f.hidden);
	return (listed.length ? listed : valueFields.value.filter((f) => !f.hidden)).slice(0, 5);
});
const visible = (f: Field, row: Doc) => !f.hidden && evalCondition(f.depends_on, row, props.parent);
const rowKey = (r: Doc) => String(r.name || r.idx);
function toggle(r: Doc) {
	const k = rowKey(r);
	const s = new Set(picked.value);
	s.has(k) ? s.delete(k) : s.add(k);
	picked.value = s;
}
function removePicked() {
	emit("remove", [...picked.value]);
	picked.value = new Set();
}
const numeric = (f: Field) => ["Int", "Float", "Currency", "Percent"].includes(f.fieldtype);
</script>

<template>
	<div class="rounded-nxg border border-nxg-border">
		<div class="nxg-scroll overflow-x-auto">
			<table class="w-full min-w-[560px] text-[13px]">
				<thead>
					<tr class="border-b border-nxg-border bg-nxg-surface-2/60 text-left text-[12px] text-nxg-text-2">
						<th v-if="!readonly" class="w-8 py-1.5 pl-2" />
						<th class="w-10 py-1.5 pl-2 font-medium">#</th>
						<th v-for="c in columns" :key="c.fieldname" class="py-1.5 pr-3 font-medium" :class="numeric(c) && 'text-right'">{{ c.label }}<span v-if="c.reqd" class="text-nxg-danger"> *</span></th>
						<th class="w-8" />
					</tr>
				</thead>
				<tbody class="divide-y divide-nxg-border">
					<template v-for="(r, i) in rows" :key="rowKey(r)">
						<tr class="cursor-pointer hover:bg-nxg-surface-2/50" :class="invalid.has(rowKey(r)) && 'bg-[var(--nxg-danger-soft)]'" @click="open = open === rowKey(r) ? null : rowKey(r)">
							<td v-if="!readonly" class="py-1.5 pl-2" @click.stop><input type="checkbox" :checked="picked.has(rowKey(r))" :aria-label="`Select row ${i + 1}`" class="rounded-1 border-nxg-border-strong text-nxg-espresso focus:ring-0" @change="toggle(r)" /></td>
							<td class="nxg-tnum py-1.5 pl-2 text-nxg-text-2">{{ i + 1 }}</td>
							<td v-for="c in columns" :key="c.fieldname" class="max-w-[220px] truncate py-1.5 pr-3" :class="numeric(c) && 'nxg-tnum text-right'">{{ displayValue(r[c.fieldname], c, { ...parent, ...r }) || "—" }}</td>
							<td class="pr-2 text-right"><Icon :name="open === rowKey(r) ? 'chevron-down' : 'chevron-right'" :size="14" class="text-nxg-text-3" /></td>
						</tr>
						<tr v-if="open === rowKey(r)">
							<td :colspan="columns.length + (readonly ? 2 : 3)" class="bg-nxg-surface-2/40 px-3 py-3">
								<div class="grid gap-x-4 gap-y-2.5 sm:grid-cols-2 lg:grid-cols-3">
									<template v-for="f in valueFields" :key="f.fieldname">
										<div v-if="visible(f, r)" :class="['Small Text', 'Text', 'Long Text', 'Text Editor'].includes(f.fieldtype) && 'sm:col-span-2 lg:col-span-3'">
											<label v-if="f.fieldtype !== 'Check'" :for="`${field.fieldname}-${rowKey(r)}-${f.fieldname}`" class="mb-1 block text-[12px] text-nxg-text-2">{{ f.label }}<span v-if="f.reqd" class="text-nxg-danger"> *</span></label>
							<FieldInput :input-id="`${field.fieldname}-${rowKey(r)}-${f.fieldname}`" :field="f" :model-value="r[f.fieldname!]" :doc="r" :doctype="childDoctype" :readonly="readonly || isReadonly(f, r)" @update:model-value="(v) => emit('change', r, f, v)" />
										</div>
									</template>
								</div>
							</td>
						</tr>
					</template>
					<tr v-if="!rows.length"><td :colspan="columns.length + 3" class="px-3 py-4 text-center text-[12.5px] text-nxg-text-2">No rows</td></tr>
				</tbody>
			</table>
		</div>
		<div v-if="!readonly" class="flex items-center gap-2 border-t border-nxg-border px-2 py-1.5">
			<button type="button" class="nxg-btn nxg-btn-secondary h-7" @click="emit('add')"><Icon name="plus" :size="13" />Add row</button>
			<button v-if="picked.size" type="button" class="nxg-btn nxg-btn-ghost h-7 text-nxg-danger" @click="removePicked">Remove {{ picked.size }}</button>
		</div>
	</div>
</template>
