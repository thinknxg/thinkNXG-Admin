<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { onBeforeRouteLeave, useRoute, useRouter } from "vue-router";
import { call, toast } from "frappe-ui";
import Icon from "@/components/ui/Icon.vue";
import NxgMenu from "@/components/ui/NxgMenu.vue";
import MenuItem from "@/components/ui/MenuItem.vue";
import NxgTabs from "@/components/ui/NxgTabs.vue";
import NxgAvatar from "@/components/ui/NxgAvatar.vue";
import NxgDialog from "@/components/ui/NxgDialog.vue";
import FieldInput from "./FieldInput.vue";
import ChildTable from "./ChildTable.vue";
import { LAYOUT, NO_VALUE, TABLES, docStatus, evalCondition, layout, type Doc, type Field, type FormMeta } from "./meta";
import { frappeRaw, uploadFile } from "@/lib/frappe";
import { boot } from "@/data/boot";
import { errorMessage } from "@/data/api";
import { confirmAction } from "@/composables/useConfirm";
import { timeAgo, fmtDateTime } from "@/composables/format";

/** Reusable document form for any DocType, laid out from its own metadata.
 *  Every read and write uses thinkNXG's own server methods, unchanged:
 *  load  frappe.desk.form.load.getdoc   (read permission, field-level masking)
 *  save  frappe.desk.form.save.savedocs (validate, on_submit, naming, workflow)
 *  cancel, workflow actions, comments, attachments, delete and print likewise.
 *  Nothing is validated only in the browser: required-field hints here are a
 *  convenience; the server decides. */
const props = defineProps<{ slug: string; name: string | null; base: string }>();
const emit = defineEmits<{ loaded: [meta: FormMeta, doc: Doc] }>();
const route = useRoute();
const router = useRouter();

const meta = ref<FormMeta | null>(null);
const doc = ref<Doc>({});
const docinfo = ref<any>(null);
const error = ref<string | null>(null);
const loading = ref(true);
const busy = ref<string | null>(null);
const dirty = ref(false);
const invalid = reactive(new Set<string>());
const invalidRows = reactive(new Set<string>());
const tab = ref("tab-0");
const transitions = ref<string[]>([]);
const isNew = computed(() => !!doc.value.__islocal);
const perms = computed(() => meta.value?.perms || {});
const docstatus = computed(() => Number(doc.value.docstatus || 0));
const canEdit = computed(() => (isNew.value ? perms.value.create : perms.value.write) && docstatus.value !== 2);
const tabs = computed(() => (meta.value ? layout(meta.value.fields) : []));
const visibleTabs = computed(() => tabs.value.filter((t) => evalCondition(t.depends_on, doc.value) && t.sections.some((s) => sectionVisible(s))));
const title = computed(() => {
	if (!meta.value) return "";
	if (isNew.value) return `New ${meta.value.doctype}`;
	const tf = meta.value.title_field;
	return (tf && tf !== "name" && doc.value[tf]) || doc.value.name;
});
const status = computed(() => docStatus(doc.value, ["status", "workflow_state", "approval_status"].find((f) => meta.value?.fields.some((x) => x.fieldname === f)) || null));
const wfField = computed(() => meta.value?.workflow?.state_field);

// Field rules ------------------------------------------------------------------
function isReadonly(f: Field, row?: Doc): boolean {
	const d = row || doc.value;
	if (!canEdit.value) return true;
	if (f.read_only || f.no_write) return true;
	if (docstatus.value === 1 && !f.allow_on_submit) return true;
	if (f.set_only_once && !isNew.value && d[f.fieldname!]) return true;
	if (f.read_only_depends_on && evalCondition(f.read_only_depends_on, d, row ? doc.value : undefined)) return true;
	if (wfField.value && f.fieldname === wfField.value) return true;
	return false;
}
function isRequired(f: Field, row?: Doc): boolean {
	const d = row || doc.value;
	return !!f.reqd || (!!f.mandatory_depends_on && evalCondition(f.mandatory_depends_on, d, row ? doc.value : undefined));
}
function fieldVisible(f: Field): boolean {
	if (f.hidden || LAYOUT.has(f.fieldtype)) return false;
	if (!evalCondition(f.depends_on, doc.value)) return false;
	// Like the Desk: empty read-only fields are not shown.
	if (!NO_VALUE.has(f.fieldtype) && isReadonly(f) && !isRequired(f)) {
		const v = doc.value[f.fieldname!];
		if (v === null || v === undefined || v === "" || (Array.isArray(v) && !v.length) || (f.fieldtype === "Check" && !v && docstatus.value !== 0)) return false;
	}
	return !["HTML", "Button", "Image", "Fold"].includes(f.fieldtype);
}
function sectionVisible(s: { depends_on?: string; columns: Field[][] }) {
	return evalCondition(s.depends_on, doc.value) && s.columns.some((c) => c.some(fieldVisible));
}

// Load ---------------------------------------------------------------------------
function localName(dt: string) {
	return `new-${dt.toLowerCase().replace(/ /g, "-")}-${Math.random().toString(36).slice(2, 8)}`;
}
function markLocal(d: Doc, m: FormMeta) {
	d.__islocal = 1;
	d.name = localName(m.doctype);
	d.docstatus = 0;
	for (const f of m.fields.filter((x) => TABLES.has(x.fieldtype))) {
		d[f.fieldname!] = (d[f.fieldname!] || []).map((r: Doc, i: number) => ({ ...r, __islocal: 1, name: localName(f.options!), parent: d.name, parentfield: f.fieldname, parenttype: m.doctype, doctype: f.options, idx: i + 1 }));
	}
}
async function load() {
	loading.value = true;
	error.value = null;
	try {
		const m: FormMeta = await call("thinknxg_admin.api.docs.get_form_meta", { doctype: props.slug });
		meta.value = m;
		const docName = m.issingle ? m.doctype : props.name;
		if (docName) {
			const res: any = await frappeRaw("frappe.desk.form.load.getdoc", { doctype: m.doctype, name: docName }, "GET");
			doc.value = res.docs?.[0] || {};
			docinfo.value = res.docinfo || null;
		} else {
			const amend = route.query.amend ? sessionStorage.getItem("nxg:amend") : null;
			const fresh: Doc = amend ? JSON.parse(amend) : await call("thinknxg_admin.api.docs.get_new_doc", { doctype: m.doctype });
			if (amend) sessionStorage.removeItem("nxg:amend");
			// Values passed in the address (e.g. ?customer=…) prefill the new document.
			for (const [k, v] of Object.entries(route.query)) if (k !== "amend" && typeof v === "string" && m.fields.some((f) => f.fieldname === k)) fresh[k] = v;
			markLocal(fresh, m);
			doc.value = fresh;
			docinfo.value = null;
		}
		dirty.value = !docName && !!route.query.amend;
		tab.value = visibleTabs.value[0]?.key || "tab-0";
		await loadTransitions();
		emit("loaded", m, doc.value);
	} catch (e: any) {
		error.value = e?.message || errorMessage(e);
	} finally {
		loading.value = false;
	}
}
async function loadTransitions() {
	transitions.value = [];
	if (!meta.value?.workflow || isNew.value) return;
	try {
		const t: any[] = await call("frappe.model.workflow.get_transitions", { doc: JSON.stringify({ doctype: meta.value.doctype, name: doc.value.name }) });
		transitions.value = [...new Set((t || []).map((x) => x.action))];
	} catch {
		transitions.value = [];
	}
}

// Edits --------------------------------------------------------------------------
async function fetchFrom(target: Doc, fields: Field[], changed: Field, value: any) {
	const deps = fields.filter((f) => f.fetch_from && f.fetch_from.split(".")[0] === changed.fieldname);
	if (!deps.length || changed.fieldtype !== "Link" || !changed.options) return;
	if (!value) {
		for (const d of deps) if (!d.fetch_if_empty) target[d.fieldname!] = null;
		return;
	}
	try {
		const res: any = await call("frappe.client.get_value", { doctype: changed.options, filters: value, fieldname: deps.map((d) => d.fetch_from!.split(".")[1]) });
		for (const d of deps) {
			const remote = d.fetch_from!.split(".")[1];
			if (d.fetch_if_empty && target[d.fieldname!]) continue;
			if (res && remote in res) target[d.fieldname!] = res[remote];
		}
	} catch {
		/* the server fills fetched values on save as well */
	}
}
function setValue(f: Field, v: any) {
	doc.value[f.fieldname!] = v;
	dirty.value = true;
	invalid.delete(f.fieldname!);
	fetchFrom(doc.value, meta.value!.fields, f, v);
}
function setRowValue(tableField: Field, row: Doc, f: Field, v: any) {
	row[f.fieldname!] = v;
	dirty.value = true;
	invalidRows.delete(String(row.name));
	fetchFrom(row, meta.value!.children[tableField.options!]?.fields || [], f, v);
}
function addRow(tableField: Field) {
	const rows = (doc.value[tableField.fieldname!] ||= []);
	const childFields = meta.value!.children[tableField.options!]?.fields || [];
	const row: Doc = { __islocal: 1, name: localName(tableField.options!), doctype: tableField.options, parent: doc.value.name, parentfield: tableField.fieldname, parenttype: meta.value!.doctype, idx: rows.length + 1, docstatus: 0 };
	for (const f of childFields) if (f.default && f.fieldname && !NO_VALUE.has(f.fieldtype)) row[f.fieldname] = ["Int", "Float", "Currency", "Percent", "Check"].includes(f.fieldtype) ? Number(f.default) || 0 : f.default;
	rows.push(row);
	dirty.value = true;
}
function removeRows(tableField: Field, names: string[]) {
	doc.value[tableField.fieldname!] = (doc.value[tableField.fieldname!] || []).filter((r: Doc) => !names.includes(String(r.name || r.idx))).map((r: Doc, i: number) => ({ ...r, idx: i + 1 }));
	dirty.value = true;
}

// Server actions -----------------------------------------------------------------
function checkRequired(): string[] {
	invalid.clear();
	invalidRows.clear();
	const missing: string[] = [];
	const empty = (v: any) => v === null || v === undefined || v === "" || (Array.isArray(v) && !v.length);
	for (const f of meta.value!.fields) {
		if (!f.fieldname || NO_VALUE.has(f.fieldtype) || f.hidden || !evalCondition(f.depends_on, doc.value)) continue;
		if (isRequired(f) && empty(doc.value[f.fieldname])) {
			invalid.add(f.fieldname);
			missing.push(f.label || f.fieldname);
		}
		if (TABLES.has(f.fieldtype)) {
			for (const row of doc.value[f.fieldname] || []) {
				for (const cf of meta.value!.children[f.options!]?.fields || []) {
					if (cf.fieldname && !cf.hidden && isRequired(cf, row) && evalCondition(cf.depends_on, row, doc.value) && empty(row[cf.fieldname])) {
						invalidRows.add(String(row.name));
						missing.push(`${f.label} row ${row.idx}: ${cf.label}`);
					}
				}
			}
		}
	}
	return missing;
}
async function save(action: "Save" | "Submit" | "Update" = "Save") {
	if (!meta.value) return;
	const missing = checkRequired();
	if (missing.length) {
		toast.error(`Fill in: ${missing.slice(0, 4).join(", ")}${missing.length > 4 ? ` and ${missing.length - 4} more` : ""}`);
		return;
	}
	if (action === "Submit" && !(await confirmAction({ title: `Submit ${title.value}?`, message: "Submitted documents can no longer be edited; they can be cancelled and amended.", confirmLabel: "Submit" }))) return;
	if (meta.value.naming_prompt && isNew.value && !doc.value.__newname) {
		const n = window.prompt(`Name for the new ${meta.value.doctype}`);
		if (!n) return;
		doc.value.__newname = n;
	}
	busy.value = action;
	try {
		const wasNew = isNew.value;
		const res: any = await frappeRaw("frappe.desk.form.save.savedocs", { doc: JSON.stringify(doc.value), action });
		const saved = res.docs?.[0];
		dirty.value = false;
		toast.success(action === "Submit" ? "Submitted" : "Saved");
		if (!saved) {
			toast.success("Queued: the document will be submitted in the background");
			return;
		}
		if (wasNew && saved.name) {
			await router.replace(`${props.base}/${encodeURIComponent(saved.name)}`);
			return;
		}
		doc.value = saved;
		await refreshInfo();
	} catch (e: any) {
		toast.error(e?.message || errorMessage(e));
	} finally {
		busy.value = null;
	}
}
async function refreshInfo() {
	if (!meta.value || isNew.value) return;
	try {
		const res: any = await frappeRaw("frappe.desk.form.load.getdoc", { doctype: meta.value.doctype, name: doc.value.name }, "GET");
		doc.value = res.docs?.[0] || doc.value;
		docinfo.value = res.docinfo || docinfo.value;
	} catch {
		/* keep what we have */
	}
	await loadTransitions();
}
async function cancelDoc() {
	if (!(await confirmAction({ title: `Cancel ${title.value}?`, message: "thinkNXG reverses its effects (ledger entries, stock) and keeps it for the record. You can amend it afterwards.", confirmLabel: "Cancel document", danger: true }))) return;
	busy.value = "Cancel";
	try {
		await frappeRaw("frappe.desk.form.save.cancel", { doctype: meta.value!.doctype, name: doc.value.name });
		toast.success("Cancelled");
		await refreshInfo();
	} catch (e: any) {
		toast.error(e?.message || errorMessage(e));
	} finally {
		busy.value = null;
	}
}
function amend() {
	const copy: Doc = JSON.parse(JSON.stringify(doc.value));
	copy.amended_from = doc.value.name;
	for (const k of ["name", "docstatus", "creation", "modified", "owner", "modified_by", "__onload", "__last_sync_on"]) delete copy[k];
	if (wfField.value) delete copy[wfField.value];
	for (const f of meta.value!.fields.filter((x) => TABLES.has(x.fieldtype))) copy[f.fieldname!] = (copy[f.fieldname!] || []).map((r: Doc) => ({ ...r, name: undefined, docstatus: 0 }));
	sessionStorage.setItem("nxg:amend", JSON.stringify(copy));
	router.push(`${props.base}/new?amend=1`);
}
function duplicate() {
	const copy: Doc = JSON.parse(JSON.stringify(doc.value));
	for (const k of ["name", "docstatus", "creation", "modified", "owner", "modified_by", "amended_from", "__onload"]) delete copy[k];
	if (wfField.value) delete copy[wfField.value];
	for (const f of meta.value!.fields) if ((f as any).no_copy && f.fieldname) delete copy[f.fieldname];
	sessionStorage.setItem("nxg:amend", JSON.stringify(copy));
	router.push(`${props.base}/new?amend=1`);
}
async function deleteDoc() {
	if (!(await confirmAction({ title: `Delete ${title.value}?`, message: "This cannot be undone from here.", confirmLabel: "Delete", danger: true, typeToConfirm: undefined }))) return;
	busy.value = "Delete";
	try {
		await call("frappe.client.delete", { doctype: meta.value!.doctype, name: doc.value.name });
		dirty.value = false;
		toast.success("Deleted");
		router.push(props.base);
	} catch (e) {
		toast.error(errorMessage(e));
	} finally {
		busy.value = null;
	}
}
async function workflow(action: string) {
	if (dirty.value) {
		toast.error("Save your changes first");
		return;
	}
	if (!(await confirmAction({ title: `${action}: ${title.value}?`, message: "The workflow moves this document to its next state and records your action.", confirmLabel: action, danger: /reject|cancel/i.test(action) }))) return;
	busy.value = action;
	try {
		await call("frappe.model.workflow.apply_workflow", { doc: JSON.stringify({ doctype: meta.value!.doctype, name: doc.value.name }), action });
		toast.success(`${action} done`);
		await refreshInfo();
	} catch (e) {
		toast.error(errorMessage(e));
	} finally {
		busy.value = null;
	}
}

// Comments, attachments, print ------------------------------------------------------
const comment = ref("");
async function addComment() {
	if (!comment.value.trim()) return;
	try {
		await call("frappe.desk.form.utils.add_comment", { reference_doctype: meta.value!.doctype, reference_name: doc.value.name, content: comment.value.trim(), comment_email: boot.data!.user.name, comment_by: boot.data!.user.full_name });
		comment.value = "";
		await refreshInfo();
	} catch (e) {
		toast.error(errorMessage(e));
	}
}
async function attach(e: Event) {
	const file = (e.target as HTMLInputElement).files?.[0];
	if (!file) return;
	try {
		await uploadFile(file, { doctype: meta.value!.doctype, docname: doc.value.name });
		toast.success("Attached");
		await refreshInfo();
	} catch (err: any) {
		toast.error(err?.message || "Upload failed");
	} finally {
		(e.target as HTMLInputElement).value = "";
	}
}
async function removeAttachment(f: any) {
	if (!(await confirmAction({ title: `Remove ${f.file_name}?`, confirmLabel: "Remove", danger: true }))) return;
	try {
		await call("frappe.desk.form.utils.remove_attach", { fid: f.name, dt: meta.value!.doctype, dn: doc.value.name });
		await refreshInfo();
	} catch (err) {
		toast.error(errorMessage(err));
	}
}
const printOpen = ref(false);
const printHtml = ref<string | null>(null);
const printFrame = ref<HTMLIFrameElement | null>(null);
async function openPrint() {
	printOpen.value = true;
	printHtml.value = null;
	try {
		const res: any = await call("frappe.www.printview.get_html_and_style", { doc: meta.value!.doctype, name: doc.value.name });
		printHtml.value = `<!doctype html><html><head><meta charset="utf-8"><style>${res.style || ""}</style></head><body>${res.html || ""}</body></html>`;
	} catch (e) {
		printOpen.value = false;
		toast.error(errorMessage(e));
	}
}
function printNow() {
	printFrame.value?.contentWindow?.print();
}
function copyLink() {
	navigator.clipboard?.writeText(window.location.href).then(() => toast.success("Link copied"));
}

const timeline = computed(() => {
	const items: { when: string; who: string; text: string; kind: string }[] = [];
	for (const c of docinfo.value?.comments || []) items.push({ when: c.creation, who: c.comment_by || c.owner, text: String(c.content || "").replace(/<[^>]+>/g, " ").trim(), kind: "comment" });
	for (const v of docinfo.value?.versions || []) {
		let text = "made changes";
		try {
			const data = JSON.parse(v.data || "{}");
			const changed = (data.changed || []).map((x: any[]) => x[0]).slice(0, 3);
			if (changed.length) text = `changed ${changed.join(", ")}${(data.changed || []).length > 3 ? "…" : ""}`;
			if (data.added?.length) text = `added ${data.added.length} row${data.added.length === 1 ? "" : "s"}`;
		} catch {
			/* keep generic */
		}
		items.push({ when: v.creation, who: v.owner, text, kind: "version" });
	}
	if (doc.value.creation && !isNew.value) items.push({ when: doc.value.creation, who: doc.value.owner, text: "created this", kind: "created" });
	return items.sort((a, b) => String(b.when).localeCompare(String(a.when))).slice(0, 40);
});

// Unsaved changes, shortcuts -----------------------------------------------------------
onBeforeRouteLeave(async () => {
	if (!dirty.value) return true;
	return await confirmAction({ title: "Leave without saving?", message: "Your changes to this document will be lost.", confirmLabel: "Leave", danger: true });
});
function onKey(e: KeyboardEvent) {
	if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s") {
		e.preventDefault();
		if (canEdit.value && (docstatus.value === 0 || dirty.value)) save(docstatus.value === 1 ? "Update" : "Save");
	}
}
function beforeUnload(e: BeforeUnloadEvent) {
	if (dirty.value) e.preventDefault();
}
onMounted(() => {
	load();
	window.addEventListener("keydown", onKey);
	window.addEventListener("beforeunload", beforeUnload);
});
onBeforeUnmount(() => {
	window.removeEventListener("keydown", onKey);
	window.removeEventListener("beforeunload", beforeUnload);
});

const tones: Record<string, string> = {
	success: "bg-[var(--nxg-success-soft)] text-nxg-success",
	warning: "bg-[var(--nxg-warning-soft)] text-nxg-warning",
	danger: "bg-[var(--nxg-danger-soft)] text-nxg-danger",
	info: "bg-nxg-surface-2 text-nxg-text-2",
	neutral: "bg-nxg-surface-2 text-nxg-text-2",
};
const wide = (f: Field) => ["Small Text", "Text", "Long Text", "Text Editor", "Code", "HTML Editor", "Markdown Editor", "JSON"].includes(f.fieldtype);
defineExpose({ doc, meta, dirty });
</script>

<template>
	<div v-if="error" class="nxg-panel flex items-start gap-3 p-6 text-[13.5px]">
		<Icon name="circle-alert" :size="18" class="mt-0.5 text-nxg-danger" />
		<div><p class="font-medium">This document couldn't be opened</p><p class="text-nxg-text-2">{{ error }}</p><button class="nxg-btn nxg-btn-secondary mt-3 h-8" @click="load">Try again</button></div>
	</div>
	<div v-else-if="loading || !meta" class="space-y-3"><div class="nxg-skeleton h-14" /><div class="nxg-skeleton h-64" /></div>
	<div v-else>
		<!-- Header with actions -->
		<div class="sticky top-0 z-20 -mx-4 mb-4 border-b border-nxg-border bg-nxg-bg px-4 py-3 sm:-mx-6 sm:px-6">
			<div class="flex flex-wrap items-center gap-3">
				<div class="min-w-0 flex-1">
					<div class="flex flex-wrap items-center gap-2">
						<h1 class="truncate text-[20px] font-semibold leading-7">{{ title }}</h1>
						<span v-if="!isNew" class="whitespace-nowrap rounded-full px-2 py-0.5 text-[11.5px] font-medium" :class="tones[status.tone]">{{ status.label }}</span>
						<span v-if="dirty" class="rounded-full border border-nxg-border px-2 py-0.5 text-[11.5px] text-nxg-text-2">Not saved</span>
					</div>
					<p class="truncate text-[12.5px] text-nxg-text-2">{{ meta.doctype }}<template v-if="!isNew && title !== doc.name"> · {{ doc.name }}</template><template v-if="!isNew && doc.modified"> · updated {{ timeAgo(doc.modified) }}</template></p>
				</div>
				<div class="flex flex-wrap items-center gap-2">
					<button v-for="a in transitions" :key="a" class="nxg-btn h-8" :class="/reject|cancel/i.test(a) ? 'nxg-btn-secondary' : 'nxg-btn-primary'" :disabled="!!busy" @click="workflow(a)">{{ a }}</button>
					<template v-if="!meta.workflow || isNew">
						<button v-if="canEdit && docstatus === 0" class="nxg-btn h-8" :class="meta.is_submittable && !isNew && !dirty ? 'nxg-btn-secondary' : 'nxg-btn-primary'" :disabled="!!busy" @click="save('Save')"><Icon v-if="busy === 'Save'" name="refresh-cw" :size="13" class="animate-spin" />Save</button>
						<button v-if="meta.is_submittable && perms.submit && docstatus === 0 && !isNew && !dirty" class="nxg-btn nxg-btn-primary h-8" :disabled="!!busy" @click="save('Submit')">Submit</button>
					</template>
					<button v-else-if="canEdit && docstatus === 0 && dirty" class="nxg-btn nxg-btn-primary h-8" :disabled="!!busy" @click="save('Save')">Save</button>
					<button v-if="docstatus === 1 && dirty && perms.submit" class="nxg-btn nxg-btn-primary h-8" :disabled="!!busy" @click="save('Update')">Update</button>
					<button v-if="docstatus === 1 && perms.cancel && !meta.workflow" class="nxg-btn nxg-btn-secondary h-8" :disabled="!!busy" @click="cancelDoc">Cancel</button>
					<button v-if="docstatus === 2 && perms.amend" class="nxg-btn nxg-btn-primary h-8" :disabled="!!busy" @click="amend">Amend</button>
					<NxgMenu v-if="!isNew" align="right" width="w-52">
						<template #trigger="{ toggle }"><button class="nxg-icon-btn" aria-label="More actions" @click="toggle"><Icon name="layout-grid" :size="16" /></button></template>
						<MenuItem v-if="perms.print" label="Print preview" icon="file-text" @click="openPrint" />
						<MenuItem v-if="perms.create" label="Duplicate" icon="plus" @click="duplicate" />
						<MenuItem label="Copy link" icon="external-link" @click="copyLink" />
						<MenuItem label="Reload" icon="refresh-cw" @click="refreshInfo" />
						<template v-if="perms.delete && docstatus !== 1">
							<div class="my-1 border-t border-nxg-border" />
							<MenuItem label="Delete" icon="x" @click="deleteDoc" />
						</template>
					</NxgMenu>
				</div>
			</div>
		</div>

		<div class="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
			<!-- Fields -->
			<div class="min-w-0">
				<NxgTabs v-if="visibleTabs.length > 1" class="mb-4" :tabs="visibleTabs.map((t) => ({ key: t.key, label: t.label }))" :model-value="tab" @update:model-value="(v: string) => (tab = v)" />
				<template v-for="t in visibleTabs" :key="t.key">
					<div v-show="visibleTabs.length === 1 || tab === t.key" class="space-y-4">
						<template v-for="s in t.sections" :key="s.key">
							<section v-if="sectionVisible(s)" class="nxg-panel px-4 py-4">
								<h2 v-if="s.label" class="mb-3 text-[13.5px] font-semibold">{{ s.label }}</h2>
								<div class="grid gap-x-6 gap-y-3" :class="{ 'md:grid-cols-2': s.columns.length === 2, 'md:grid-cols-2 xl:grid-cols-3': s.columns.length >= 3 }">
									<div v-for="(col, ci) in s.columns" :key="ci" class="min-w-0 space-y-3">
										<template v-for="f in col" :key="f.fieldname">
											<div v-if="fieldVisible(f) && TABLES.has(f.fieldtype)" :class="s.columns.length > 1 && 'md:col-span-2'">
												<div v-if="f.label !== s.label" class="mb-1.5 flex items-baseline justify-between"><span class="text-[12.5px] font-medium text-nxg-text-2">{{ f.label }}<span v-if="isRequired(f)" class="text-nxg-danger"> *</span></span></div>
												<ChildTable :field="f" :rows="doc[f.fieldname!] || []" :fields="meta.children[f.options!]?.fields || []" :child-doctype="f.options!" :readonly="isReadonly(f)" :parent="doc" :is-readonly="(cf: Field, row: Doc) => isReadonly(cf, row)" :invalid="invalidRows" @change="(row, cf, v) => setRowValue(f, row, cf, v)" @add="addRow(f)" @remove="(names) => removeRows(f, names)" />
											</div>
											<h3 v-else-if="fieldVisible(f) && f.fieldtype === 'Heading'" class="pt-1 text-[13px] font-semibold">{{ f.label }}</h3>
											<div v-else-if="fieldVisible(f) && !NO_VALUE.has(f.fieldtype)" :class="wide(f) && 'md:col-span-2'">
												<label v-if="f.fieldtype !== 'Check' || isReadonly(f)" :for="`f-${f.fieldname}`" class="mb-1 block text-[12px] text-nxg-text-2">{{ f.label }}<span v-if="isRequired(f) && !isReadonly(f)" class="text-nxg-danger"> *</span></label>
												<FieldInput :input-id="`f-${f.fieldname}`" :field="f" :model-value="doc[f.fieldname!]" :doc="doc" :doctype="meta.doctype" :readonly="isReadonly(f)" :invalid="invalid.has(f.fieldname!)" @update:model-value="(v) => setValue(f, v)" />
												<p v-if="f.description && !isReadonly(f)" class="mt-1 text-[11.5px] text-nxg-text-3">{{ String(f.description).replace(/<[^>]+>/g, "") }}</p>
											</div>
										</template>
									</div>
								</div>
							</section>
						</template>
					</div>
				</template>
			</div>

			<!-- Activity -->
			<aside v-if="!isNew" class="space-y-4">
				<section class="nxg-panel px-4 py-3">
					<h2 class="mb-2 flex items-center justify-between text-[13px] font-semibold">Attachments <label class="nxg-btn nxg-btn-ghost h-7 cursor-pointer text-[12px] font-normal"><Icon name="plus" :size="13" />Add<input type="file" class="sr-only" @change="attach" /></label></h2>
					<p v-if="!docinfo?.attachments?.length" class="text-[12.5px] text-nxg-text-2">No files attached</p>
					<ul v-else class="space-y-1">
						<li v-for="f in docinfo.attachments" :key="f.name" class="group flex items-center gap-2 text-[12.5px]">
							<Icon name="file-text" :size="13" class="text-nxg-text-3" />
							<a :href="f.file_url" target="_blank" rel="noopener" class="min-w-0 flex-1 truncate hover:underline">{{ f.file_name }}</a>
							<button v-if="perms.write" class="hidden text-nxg-text-3 hover:text-nxg-danger group-hover:block" :aria-label="`Remove ${f.file_name}`" @click="removeAttachment(f)"><Icon name="x" :size="13" /></button>
						</li>
					</ul>
				</section>
				<section class="nxg-panel px-4 py-3">
					<h2 class="mb-2 text-[13px] font-semibold">Activity</h2>
					<div class="mb-3 flex gap-2">
						<textarea v-model="comment" rows="2" class="nxg-input min-w-0 flex-1 py-1.5 text-[12.5px]" placeholder="Add a comment" aria-label="Add a comment" @keydown.ctrl.enter="addComment" @keydown.meta.enter="addComment" />
						<button class="nxg-btn nxg-btn-secondary h-8 self-end" :disabled="!comment.trim()" @click="addComment">Post</button>
					</div>
					<ol class="space-y-2.5">
						<li v-for="(i, n) in timeline" :key="n" class="flex gap-2 text-[12.5px]">
							<NxgAvatar :name="i.who" :size="20" />
							<div class="min-w-0">
								<p :class="i.kind === 'comment' ? 'rounded-nxg-sm bg-nxg-surface-2 px-2 py-1' : 'text-nxg-text-2'"><span class="font-medium text-nxg-text">{{ i.kind === "comment" ? "" : i.who + " " }}</span>{{ i.text }}</p>
								<p class="mt-0.5 text-[11px] text-nxg-text-3" :title="fmtDateTime(i.when)">{{ i.kind === "comment" ? i.who + " · " : "" }}{{ timeAgo(i.when) }}</p>
							</div>
						</li>
					</ol>
				</section>
			</aside>
		</div>

		<NxgDialog :open="printOpen" title="Print preview" width="max-w-[920px]" @close="printOpen = false">
			<div v-if="!printHtml" class="nxg-skeleton h-[60vh]" />
			<iframe v-else ref="printFrame" :srcdoc="printHtml" sandbox="allow-modals allow-same-origin" class="h-[65vh] w-full rounded-nxg border border-nxg-border bg-white" title="Print preview" />
			<template #footer>
				<button class="nxg-btn nxg-btn-secondary" @click="printOpen = false">Close</button>
				<button class="nxg-btn nxg-btn-primary" :disabled="!printHtml" @click="printNow"><Icon name="file-text" :size="14" />Print</button>
			</template>
		</NxgDialog>
	</div>
</template>
