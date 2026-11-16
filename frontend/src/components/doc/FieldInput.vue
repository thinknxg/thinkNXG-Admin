<script setup lang="ts">
import { computed, ref } from "vue";
import { toast } from "frappe-ui";
import { uploadFile } from "@/lib/frappe";
import LinkInput from "./LinkInput.vue";
import { displayValue, type Doc, type Field } from "./meta";
import { internalHref, toInternal } from "@/lib/links";

/** One field of the document form, by field type. Values are only edited here;
 *  validation and saving happen on the server. */
const props = defineProps<{ field: Field; modelValue: any; readonly?: boolean; doc: Doc; doctype: string; invalid?: boolean; inputId?: string }>();
const emit = defineEmits<{ "update:modelValue": [any] }>();
const t = computed(() => props.field.fieldtype);
const v = computed({ get: () => props.modelValue, set: (x) => emit("update:modelValue", x) });
const selectOptions = computed(() => (props.field.options || "").split("\n"));
const dynamicDoctype = computed(() => (t.value === "Dynamic Link" && props.field.options ? props.doc[props.field.options] : props.field.options) || "");
const linkHref = computed(() => {
	if (!props.modelValue || !dynamicDoctype.value) return null;
	const internal = toInternal(`/desk/${dynamicDoctype.value.toLowerCase().replace(/ /g, "-")}/${encodeURIComponent(props.modelValue)}`);
	return internal ? internalHref(internal) : null;
});
const uploading = ref(false);
async function upload(e: Event) {
	const file = (e.target as HTMLInputElement).files?.[0];
	if (!file) return;
	uploading.value = true;
	try {
		const saved = !props.doc.__islocal && props.doc.name;
		const f = await uploadFile(file, saved ? { doctype: props.doctype, docname: props.doc.name, fieldname: props.field.fieldname } : {});
		emit("update:modelValue", f.file_url);
	} catch (err: any) {
		toast.error(err?.message || "Upload failed");
	} finally {
		uploading.value = false;
		(e.target as HTMLInputElement).value = "";
	}
}
function num(e: Event) {
	const raw = (e.target as HTMLInputElement).value;
	emit("update:modelValue", raw === "" ? null : t.value === "Int" ? parseInt(raw, 10) : parseFloat(raw));
}
</script>

<template>
	<!-- Read-only: show the value, links stay clickable inside thinkNXG -->
	<div v-if="readonly" class="min-h-8 py-1.5 text-[13px]" :class="field.bold && 'font-semibold'">
		<template v-if="t === 'Check'">{{ modelValue ? "Yes" : "No" }}</template>
		<a v-else-if="(t === 'Link' || t === 'Dynamic Link') && linkHref" :href="linkHref" class="font-medium hover:underline">{{ modelValue }}</a>
		<div v-else-if="t === 'Text Editor' || t === 'HTML Editor'" class="prose-sm max-w-none whitespace-pre-wrap break-words">{{ String(modelValue || "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim() || "—" }}</div>
		<a v-else-if="(t === 'Attach' || t === 'Attach Image') && modelValue" :href="modelValue" target="_blank" rel="noopener" class="font-medium hover:underline">{{ String(modelValue).split("/").pop() }}</a>
		<span v-else class="whitespace-pre-wrap break-words">{{ displayValue(modelValue, field, doc) || "—" }}</span>
	</div>

	<label v-else-if="t === 'Check'" class="flex h-8 items-center gap-2 text-[13px]">
		<input :id="inputId" type="checkbox" class="rounded-1 border-nxg-border-strong text-nxg-espresso focus:ring-0" :checked="!!modelValue" @change="v = ($event.target as HTMLInputElement).checked ? 1 : 0" />
		<span>{{ field.label }}</span>
	</label>
	<LinkInput v-else-if="t === 'Link' || t === 'Dynamic Link'" :input-id="inputId" v-model="v" :doctype="dynamicDoctype" :reference-doctype="doctype" :invalid="invalid" :disabled="!dynamicDoctype" />
	<select v-else-if="t === 'Select'" :id="inputId" v-model="v" class="nxg-input h-8 w-full" :class="invalid && 'border-nxg-danger'">
		<option v-for="o in selectOptions" :key="o" :value="o">{{ o || "—" }}</option>
	</select>
	<input v-else-if="t === 'Date'" :id="inputId" v-model="v" type="date" class="nxg-input h-8 w-full" :class="invalid && 'border-nxg-danger'" />
	<input v-else-if="t === 'Datetime'" :id="inputId" :value="modelValue ? String(modelValue).replace(' ', 'T').slice(0, 16) : ''" type="datetime-local" class="nxg-input h-8 w-full" :class="invalid && 'border-nxg-danger'" @change="v = ($event.target as HTMLInputElement).value ? ($event.target as HTMLInputElement).value.replace('T', ' ') + ':00' : null" />
	<input v-else-if="t === 'Time'" :id="inputId" v-model="v" type="time" step="1" class="nxg-input h-8 w-full" />
	<input v-else-if="['Int', 'Float', 'Currency', 'Percent'].includes(t)" :id="inputId" :value="modelValue ?? ''" type="number" :step="t === 'Int' ? 1 : 'any'" :min="field.non_negative ? 0 : undefined" class="nxg-input nxg-tnum h-8 w-full text-right" :class="invalid && 'border-nxg-danger'" @input="num" />
	<textarea v-else-if="['Small Text', 'Text', 'Long Text', 'Code', 'Text Editor', 'Markdown Editor', 'HTML Editor', 'JSON'].includes(t)" :id="inputId" v-model="v" :rows="t === 'Small Text' ? 2 : 4" class="nxg-input w-full py-1.5" :class="[invalid && 'border-nxg-danger', t === 'Code' || t === 'JSON' ? 'font-mono text-[12px]' : '']" />
	<input v-else-if="t === 'Password'" :id="inputId" v-model="v" type="password" autocomplete="new-password" class="nxg-input h-8 w-full" />
	<div v-else-if="t === 'Attach' || t === 'Attach Image'" class="flex h-8 items-center gap-2 text-[13px]">
		<a v-if="modelValue" :href="modelValue" target="_blank" rel="noopener" class="min-w-0 truncate font-medium hover:underline">{{ String(modelValue).split("/").pop() }}</a>
		<label class="nxg-btn nxg-btn-secondary h-7 cursor-pointer" :class="uploading && 'opacity-60'">
			{{ uploading ? "Uploading…" : modelValue ? "Replace" : "Upload" }}
			<input :id="inputId" type="file" class="sr-only" :accept="t === 'Attach Image' ? 'image/*' : undefined" :disabled="uploading" @change="upload" />
		</label>
		<button v-if="modelValue" type="button" class="text-[12px] text-nxg-text-2 hover:text-nxg-text" @click="v = null">Remove</button>
	</div>
	<input v-else :id="inputId" v-model="v" type="text" class="nxg-input h-8 w-full" :class="invalid && 'border-nxg-danger'" :placeholder="field.placeholder" />
</template>
