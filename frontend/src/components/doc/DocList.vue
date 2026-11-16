<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { call, toast } from "frappe-ui";
import Icon from "@/components/ui/Icon.vue";
import NxgEmpty from "@/components/ui/NxgEmpty.vue";
import NxgMenu from "@/components/ui/NxgMenu.vue";
import NxgPagination from "@/components/ui/NxgPagination.vue";
import LinkInput from "./LinkInput.vue";
import { displayValue, docStatus } from "./meta";
import { downloadCsv, errorMessage } from "@/data/api";
import { confirmAction } from "@/composables/useConfirm";
import { readPref, writePref } from "@/composables/storage";
import { timeAgo } from "@/composables/format";

/** Reusable document list for any DocType. Rows, counts and filters run on the
 *  server under the user's permissions (thinknxg_admin.api.docs.get_list); bulk
 *  submit/cancel/delete use thinkNXG's own bulk methods, so each document's
 *  validation and permission checks run one by one. */
const props = defineProps<{ slug: string; base: string }>();
const emit = defineEmits<{ meta: [any] }>();
const route = useRoute();
const router = useRouter();

interface Col { fieldname: string; label: string; fieldtype: string; options?: string }
interface ListMeta { doctype: string; title_field?: string; status_field?: string; image_field?: string; is_submittable: number; issingle: number; columns: Col[]; filters: Col[]; sort_field: string; sort_order: string; perms: Record<string, boolean>; description?: string }
const meta = ref<ListMeta | null>(null);
const metaError = ref<string | null>(null);
const rows = ref<any[]>([]);
const total = ref(0);
const loading = ref(false);
const error = ref<string | null>(null);
const selected = ref<Set<string>>(new Set());

const prefKey = computed(() => `list:${props.slug}`);
const saved = readPref<{ pageSize?: number; hidden?: string[]; views?: { name: string; filters: Record<string, any> }[] }>(prefKey.value, {});
const state = reactive({
	search: "",
	filters: {} as Record<string, any>,
	sort: "",
	page: 1,
	pageSize: saved.pageSize || 20,
	hidden: new Set<string>(saved.hidden || []),
	views: saved.views || ([] as { name: string; filters: Record<string, any> }[]),
});

function persist() {
	writePref(prefKey.value, { pageSize: state.pageSize, hidden: [...state.hidden], views: state.views });
}

// Filters can arrive in the address (from KPI and dashboard links).
function fromQuery() {
	const f: Record<string, any> = {};
	for (const [k, v] of Object.entries(route.query)) if (!["page", "q", "sort"].includes(k) && typeof v === "string") f[k] = v;
	state.filters = f;
	state.search = typeof route.query.q === "string" ? route.query.q : "";
	state.page = Number(route.query.page) || 1;
}
fromQuery();

async function loadMeta() {
	try {
		meta.value = await call("thinknxg_admin.api.docs.get_list_meta", { doctype: props.slug });
		emit("meta", meta.value);
		if (meta.value && !state.sort) state.sort = `${meta.value.sort_field} ${meta.value.sort_order.toLowerCase()}`;
	} catch (e) {
		metaError.value = errorMessage(e);
	}
}

let seq = 0;
async function load() {
	if (!meta.value) return;
	const mine = ++seq;
	loading.value = true;
	error.value = null;
	try {
		const filters = Object.entries(state.filters).filter(([, v]) => v !== "" && v !== null && v !== undefined).map(([k, v]) => [k, "=", v]);
		const res: any = await call("thinknxg_admin.api.docs.get_list", {
			doctype: meta.value.doctype,
			filters,
			search: state.search || null,
			order_by: state.sort,
			start: (state.page - 1) * state.pageSize,
			page_length: state.pageSize,
			fields: meta.value.columns.map((c) => c.fieldname),
		});
		if (mine !== seq) return;
		rows.value = res.rows;
		total.value = res.total;
		selected.value = new Set();
	} catch (e) {
		if (mine === seq) error.value = errorMessage(e);
	} finally {
		if (mine === seq) loading.value = false;
	}
}

let searchTimer: number | undefined;
watch(() => state.search, () => {
	window.clearTimeout(searchTimer);
	searchTimer = window.setTimeout(() => {
		state.page = 1;
		sync();
	}, 250);
});
watch(() => [JSON.stringify(state.filters), state.sort, state.pageSize], () => {
	state.page = 1;
	sync();
});
watch(() => state.page, () => sync());
function sync() {
	const q: Record<string, string> = {};
	for (const [k, v] of Object.entries(state.filters)) if (v !== "" && v != null) q[k] = String(v);
	if (state.search) q.q = state.search;
	if (state.page > 1) q.page = String(state.page);
	router.replace({ query: q }).catch(() => {});
	load();
}
loadMeta().then(load);

const columns = computed(() => (meta.value?.columns || []).filter((c) => !state.hidden.has(c.fieldname) && c.fieldname !== meta.value?.title_field && c.fieldname !== meta.value?.status_field));
const titleOf = (r: any) => (meta.value?.title_field && r[meta.value.title_field]) || r.name;
const href = (r: any) => `/thinknxg${props.base}/${encodeURIComponent(r.name)}`;
const activeFilters = computed(() => Object.entries(state.filters).filter(([, v]) => v !== "" && v != null).length);
const allSelected = computed(() => rows.value.length > 0 && rows.value.every((r) => selected.value.has(r.name)));
function toggleAll() {
	selected.value = allSelected.value ? new Set() : new Set(rows.value.map((r) => r.name));
}
function toggle(name: string) {
	const s = new Set(selected.value);
	s.has(name) ? s.delete(name) : s.add(name);
	selected.value = s;
}
function sortBy(field: string) {
	const [f, d] = state.sort.split(" ");
	state.sort = `${field} ${f === field && d === "desc" ? "asc" : "desc"}`;
}
function clearFilters() {
	state.filters = {};
	state.search = "";
}
function saveView() {
	const name = window.prompt("Name this filter set");
	if (!name) return;
	state.views = [...state.views.filter((v) => v.name !== name), { name, filters: { ...state.filters } }];
	persist();
	toast.success(`Saved "${name}"`);
}
function applyView(v: { filters: Record<string, any> }) {
	state.filters = { ...v.filters };
}
function deleteView(name: string) {
	state.views = state.views.filter((v) => v.name !== name);
	persist();
}
function toggleColumn(f: string) {
	state.hidden.has(f) ? state.hidden.delete(f) : state.hidden.add(f);
	state.hidden = new Set(state.hidden);
	persist();
}

const busy = ref(false);
async function bulk(action: "submit" | "cancel" | "delete") {
	const names = [...selected.value];
	if (!names.length || !meta.value) return;
	const verb = { submit: "Submit", cancel: "Cancel", delete: "Delete" }[action];
	if (!(await confirmAction({ title: `${verb} ${names.length} ${meta.value.doctype}${names.length === 1 ? "" : " records"}?`, message: action === "delete" ? "Deleted records cannot be restored from here." : "Each document is validated by thinkNXG one by one; any that fail are left as they are.", confirmLabel: verb, danger: action !== "submit" }))) return;
	busy.value = true;
	try {
		if (action === "delete") await call("frappe.desk.reportview.delete_items", { items: JSON.stringify(names), doctype: meta.value.doctype });
		else await call("frappe.desk.doctype.bulk_update.bulk_update.submit_cancel_or_update_docs", { doctype: meta.value.doctype, docnames: names, action });
		toast.success(names.length > 10 ? `${verb} queued for ${names.length} records` : `${verb} done`);
		await load();
	} catch (e) {
		toast.error(errorMessage(e));
	} finally {
		busy.value = false;
	}
}
function exportCsv() {
	if (!meta.value) return;
	const cols = [{ fieldname: "name", label: "ID", fieldtype: "Data" }, ...columns.value];
	downloadCsv(`${meta.value.doctype}.csv`, cols.map((c) => c.label || c.fieldname), rows.value.map((r) => cols.map((c) => r[c.fieldname])));
}
const statusTone: Record<string, string> = {
	success: "bg-[var(--nxg-success-soft)] text-nxg-success",
	warning: "bg-[var(--nxg-warning-soft)] text-nxg-warning",
	danger: "bg-[var(--nxg-danger-soft)] text-nxg-danger",
	info: "bg-nxg-surface-2 text-nxg-text-2",
	neutral: "bg-nxg-surface-2 text-nxg-text-2",
};
defineExpose({ reload: load, meta });
</script>

<template>
	<div v-if="metaError" class="nxg-panel p-6 text-[13px] text-nxg-danger">{{ metaError }}</div>
	<div v-else class="nxg-panel min-w-0">
		<!-- Toolbar -->
		<div class="flex flex-wrap items-center gap-2 border-b border-nxg-border px-3 py-2.5">
			<label class="relative min-w-[200px] flex-1">
				<Icon name="search" :size="14" class="pointer-events-none absolute left-2.5 top-2 text-nxg-text-3" />
				<input v-model="state.search" class="nxg-input h-8 w-full pl-8" :placeholder="`Search ${meta?.doctype || ''}`" :aria-label="`Search ${meta?.doctype || ''}`" />
			</label>
			<NxgMenu v-if="meta?.filters.length" width="w-[300px]">
				<template #trigger="{ toggle }">
					<button class="nxg-btn nxg-btn-secondary h-8" @click="toggle"><Icon name="filter" :size="14" />Filters<span v-if="activeFilters" class="nxg-tnum rounded-full bg-nxg-surface-2 px-1.5 text-[11px]">{{ activeFilters }}</span></button>
				</template>
				<div class="space-y-2.5 p-2" @click.stop>
					<label v-for="f in meta.filters" :key="f.fieldname" class="block">
						<span class="mb-1 block text-[12px] text-nxg-text-2">{{ f.label }}</span>
						<select v-if="f.fieldtype === 'Select'" v-model="state.filters[f.fieldname]" class="nxg-input h-8 w-full">
							<option value="">Any</option>
							<option v-for="o in (f.options || '').split('\n').filter(Boolean)" :key="o" :value="o">{{ o }}</option>
						</select>
						<select v-else-if="f.fieldtype === 'Check'" v-model="state.filters[f.fieldname]" class="nxg-input h-8 w-full">
							<option value="">Any</option><option value="1">Yes</option><option value="0">No</option>
						</select>
						<LinkInput v-else-if="f.fieldtype === 'Link' && f.options" :model-value="state.filters[f.fieldname]" :doctype="f.options" @update:model-value="(v) => (state.filters[f.fieldname] = v || '')" />
						<input v-else-if="f.fieldtype === 'Date'" v-model="state.filters[f.fieldname]" type="date" class="nxg-input h-8 w-full" />
						<input v-else v-model.lazy="state.filters[f.fieldname]" class="nxg-input h-8 w-full" />
					</label>
					<div class="flex items-center justify-between pt-1">
						<button class="text-[12.5px] text-nxg-text-2 hover:text-nxg-text" @click="clearFilters">Clear all</button>
						<button class="nxg-btn nxg-btn-secondary h-7" :disabled="!activeFilters" @click="saveView">Save as view</button>
					</div>
				</div>
			</NxgMenu>
			<NxgMenu v-if="state.views.length" width="w-56">
				<template #trigger="{ toggle }"><button class="nxg-btn nxg-btn-ghost h-8" @click="toggle"><Icon name="star" :size="14" />Views</button></template>
				<div v-for="v in state.views" :key="v.name" class="flex items-center gap-1">
					<button class="flex h-8 min-w-0 flex-1 items-center rounded-nxg-sm px-2 text-left text-[13px] hover:bg-nxg-surface-2" data-close @click="applyView(v)"><span class="truncate">{{ v.name }}</span></button>
					<button class="nxg-icon-btn h-7 w-7" :aria-label="`Delete view ${v.name}`" @click="deleteView(v.name)"><Icon name="x" :size="13" /></button>
				</div>
			</NxgMenu>
			<NxgMenu v-if="meta?.columns.length" width="w-56" align="right">
				<template #trigger="{ toggle }"><button class="nxg-icon-btn" aria-label="Choose columns" title="Columns" @click="toggle"><Icon name="sliders-horizontal" :size="15" /></button></template>
				<div class="px-2 pb-1 pt-1.5 nxg-micro">Columns</div>
				<label v-for="c in meta.columns" :key="c.fieldname" class="flex h-8 cursor-pointer items-center gap-2 rounded-nxg-sm px-2 text-[13px] hover:bg-nxg-surface-2">
					<input type="checkbox" :checked="!state.hidden.has(c.fieldname)" class="rounded-1 border-nxg-border-strong text-nxg-espresso focus:ring-0" @change="toggleColumn(c.fieldname)" />{{ c.label }}
				</label>
			</NxgMenu>
			<button v-if="meta?.perms.export" class="nxg-icon-btn" aria-label="Export this page as CSV" title="Export CSV" :disabled="!rows.length" @click="exportCsv"><Icon name="arrow-down" :size="15" /></button>
			<button class="nxg-icon-btn" aria-label="Refresh" title="Refresh" @click="load"><Icon name="refresh-cw" :size="15" :class="loading && 'animate-spin'" /></button>
		</div>

		<!-- Bulk bar -->
		<div v-if="selected.size" class="flex flex-wrap items-center gap-2 border-b border-nxg-border bg-nxg-surface-2 px-3 py-2 text-[13px]">
			<span class="font-medium">{{ selected.size }} selected</span>
			<button v-if="meta?.is_submittable && meta.perms.submit" class="nxg-btn nxg-btn-secondary h-7" :disabled="busy" @click="bulk('submit')">Submit</button>
			<button v-if="meta?.is_submittable && meta.perms.cancel" class="nxg-btn nxg-btn-secondary h-7" :disabled="busy" @click="bulk('cancel')">Cancel</button>
			<button v-if="meta?.perms.delete" class="nxg-btn nxg-btn-secondary h-7 text-nxg-danger" :disabled="busy" @click="bulk('delete')">Delete</button>
			<button class="ml-auto text-[12.5px] text-nxg-text-2 hover:text-nxg-text" @click="selected = new Set()">Clear selection</button>
		</div>

		<div v-if="error" class="flex items-center justify-between gap-3 px-4 py-4 text-[13px]">
			<span class="flex items-center gap-2 text-nxg-danger"><Icon name="circle-alert" :size="15" />{{ error }}</span>
			<button class="nxg-btn nxg-btn-secondary h-7" @click="load">Retry</button>
		</div>
		<div v-else-if="!meta || (loading && !rows.length)" class="space-y-2 p-4"><div v-for="i in 6" :key="i" class="nxg-skeleton h-9" /></div>
		<NxgEmpty v-else-if="!rows.length" :text="activeFilters || state.search ? 'No records match these filters' : `No ${meta.doctype} records yet`" />
		<div v-else class="nxg-scroll overflow-x-auto" :class="loading && 'opacity-60'">
			<table class="w-full min-w-[640px] text-[13px]">
				<thead>
					<tr class="border-b border-nxg-border text-left text-[12px] text-nxg-text-2">
						<th class="w-9 py-2 pl-3"><input type="checkbox" :checked="allSelected" aria-label="Select all on this page" class="rounded-1 border-nxg-border-strong text-nxg-espresso focus:ring-0" @change="toggleAll" /></th>
						<th class="py-2 pr-3 font-medium"><button class="hover:text-nxg-text" @click="sortBy(meta.title_field || 'name')">{{ meta.title_field ? "Title" : "ID" }}</button></th>
						<th v-if="meta.status_field || meta.is_submittable" class="py-2 pr-3 font-medium">Status</th>
						<th v-for="c in columns" :key="c.fieldname" class="py-2 pr-3 font-medium" :class="['Int', 'Float', 'Currency', 'Percent'].includes(c.fieldtype) && 'text-right'">
							<button class="hover:text-nxg-text" @click="sortBy(c.fieldname)">{{ c.label }}<Icon v-if="state.sort.startsWith(c.fieldname + ' ')" :name="state.sort.endsWith('asc') ? 'arrow-up' : 'arrow-down'" :size="11" class="ml-0.5 inline" /></button>
						</th>
						<th class="py-2 pr-3 text-right font-medium"><button class="hover:text-nxg-text" @click="sortBy('modified')">Updated</button></th>
					</tr>
				</thead>
				<tbody class="divide-y divide-nxg-border">
					<tr v-for="r in rows" :key="r.name" class="group hover:bg-nxg-surface-2/60" :class="selected.has(r.name) && 'bg-nxg-surface-2/60'">
						<td class="py-2 pl-3"><input type="checkbox" :checked="selected.has(r.name)" :aria-label="`Select ${r.name}`" class="rounded-1 border-nxg-border-strong text-nxg-espresso focus:ring-0" @change="toggle(r.name)" /></td>
						<td class="max-w-[320px] py-2 pr-3">
							<a :href="href(r)" class="block truncate font-medium group-hover:underline">{{ titleOf(r) }}</a>
							<span v-if="titleOf(r) !== r.name" class="block truncate text-[11.5px] text-nxg-text-3">{{ r.name }}</span>
						</td>
						<td v-if="meta.status_field || meta.is_submittable" class="py-2 pr-3">
							<span class="whitespace-nowrap rounded-full px-2 py-0.5 text-[11.5px] font-medium" :class="statusTone[docStatus(r, meta.status_field).tone]">{{ docStatus(r, meta.status_field).label }}</span>
						</td>
						<td v-for="c in columns" :key="c.fieldname" class="max-w-[240px] truncate py-2 pr-3" :class="['Int', 'Float', 'Currency', 'Percent'].includes(c.fieldtype) && 'nxg-tnum text-right'">{{ displayValue(r[c.fieldname], c, r) }}</td>
						<td class="whitespace-nowrap py-2 pr-3 text-right text-[12px] text-nxg-text-2">{{ timeAgo(r.modified) }}</td>
					</tr>
				</tbody>
			</table>
		</div>
		<div v-if="rows.length" class="flex flex-wrap items-center justify-end gap-2 border-t border-nxg-border pr-3">
			<NxgPagination class="min-w-0 flex-1" :start="(state.page - 1) * state.pageSize" :page-length="state.pageSize" :total="total" @change="(s: number) => (state.page = Math.floor(s / state.pageSize) + 1)" />
			<select v-model.number="state.pageSize" class="nxg-input h-7 w-auto text-[12.5px]" aria-label="Rows per page" @change="persist"><option v-for="n in [20, 50, 100]" :key="n" :value="n">{{ n }} per page</option></select>
		</div>
	</div>
</template>
