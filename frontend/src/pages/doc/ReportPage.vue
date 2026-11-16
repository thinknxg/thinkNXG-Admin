<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { call } from "frappe-ui";
import Icon from "@/components/ui/Icon.vue";
import NxgEmpty from "@/components/ui/NxgEmpty.vue";
import FieldInput from "@/components/doc/FieldInput.vue";
import { displayValue, evalCondition } from "@/components/doc/meta";
import { reportFilters, type ReportFilter } from "@/lib/reportFilters";
import { downloadCsv, errorMessage } from "@/data/api";
import { toInternal, internalHref } from "@/lib/links";

/** /<center>/reports/<name>: runs a query, script or custom report through
 *  frappe.desk.query_report.run, so the report's own permission check, SQL and
 *  Python logic run unchanged. Results stay inside the command center. */
const props = defineProps<{ center: string; report: string }>();
const name = computed(() => decodeURIComponent(props.report));
const filters = ref<ReportFilter[]>([]);
const parsed = ref(true);
const values = reactive<Record<string, any>>({});
const loading = ref(true);
const running = ref(false);
const error = ref<string | null>(null);
interface Col { fieldname: string; label: string; fieldtype: string; options?: string; width?: number }
const columns = ref<Col[]>([]);
const rows = ref<any[]>([]);
const summary = ref<any[]>([]);
const message = ref<string | null>(null);
const q = ref("");

function normCol(c: any, i: number): Col {
	if (typeof c === "string") {
		const [label, typeOpt = "Data", width] = c.split(":");
		const [fieldtype, options] = typeOpt.split("/");
		return { fieldname: String(i), label, fieldtype: fieldtype || "Data", options, width: Number(width) || undefined };
	}
	return { fieldname: c.fieldname || c.id || String(i), label: c.label || c.fieldname, fieldtype: c.fieldtype || "Data", options: c.options, width: c.width };
}
function normRow(r: any, cols: Col[]) {
	if (Array.isArray(r)) return Object.fromEntries(cols.map((c, i) => [c.fieldname, r[i]]));
	return r;
}

onMounted(async () => {
	try {
		const res = await reportFilters(name.value);
		filters.value = res.filters;
		parsed.value = res.parsed;
		for (const f of res.filters) if (f.default !== undefined) values[f.fieldname] = f.default;
		if (ready.value) await run();
	} catch (e) {
		error.value = errorMessage(e);
	} finally {
		loading.value = false;
	}
});
const ready = computed(() => filters.value.every((f) => !f.reqd || (values[f.fieldname] !== undefined && values[f.fieldname] !== "" && values[f.fieldname] !== null)));

async function run() {
	running.value = true;
	error.value = null;
	message.value = null;
	try {
		const clean = Object.fromEntries(Object.entries(values).filter(([, v]) => v !== "" && v !== null && v !== undefined));
		const res: any = await call("frappe.desk.query_report.run", { report_name: name.value, filters: clean, ignore_prepared_report: false });
		if (res?.prepared_report) {
			message.value = "This report is prepared in the background. Run it again in a minute to see the result.";
			columns.value = [];
			rows.value = [];
			return;
		}
		const cols = (res?.columns || []).map(normCol);
		columns.value = cols;
		rows.value = (res?.result || []).filter((r: any) => r && (Array.isArray(r) || typeof r === "object")).map((r: any) => normRow(r, cols));
		summary.value = res?.report_summary || [];
		if (res?.message && typeof res.message === "string") message.value = res.message.replace(/<[^>]+>/g, "");
	} catch (e) {
		error.value = errorMessage(e);
	} finally {
		running.value = false;
	}
}
const shown = computed(() => {
	const s = q.value.trim().toLowerCase();
	return s ? rows.value.filter((r) => columns.value.some((c) => String(r[c.fieldname] ?? "").toLowerCase().includes(s))) : rows.value;
});
const numeric = (c: Col) => ["Currency", "Float", "Int", "Percent"].includes(c.fieldtype);
function linkFor(c: Col, r: any): string | null {
	const v = r[c.fieldname];
	if (!v) return null;
	let dt = c.fieldtype === "Link" ? c.options : c.fieldtype === "Dynamic Link" && c.options ? r[c.options] : null;
	if (!dt) return null;
	const internal = toInternal(`/desk/${String(dt).toLowerCase().replace(/ /g, "-")}/${encodeURIComponent(v)}`);
	return internal ? internalHref(internal) : null;
}
function exportCsv() {
	downloadCsv(`${name.value}.csv`, columns.value.map((c) => c.label), shown.value.map((r) => columns.value.map((c) => r[c.fieldname])));
}
</script>

<template>
	<div class="mx-auto w-full max-w-[1480px] px-4 pb-10 pt-6 sm:px-6">
		<div class="mb-4 flex flex-wrap items-end justify-between gap-3">
			<div><p class="text-[12.5px] text-nxg-text-2">Report</p><h1 class="text-[22px] font-semibold leading-8">{{ name }}</h1></div>
			<div class="flex gap-2">
				<button class="nxg-btn nxg-btn-secondary" :disabled="!rows.length" @click="exportCsv"><Icon name="arrow-down" :size="14" />Export CSV</button>
				<button class="nxg-btn nxg-btn-primary" :disabled="running || !ready" @click="run"><Icon name="refresh-cw" :size="14" :class="running && 'animate-spin'" />Run</button>
			</div>
		</div>

		<div class="nxg-panel mb-4 px-4 py-3">
			<div v-if="loading" class="nxg-skeleton h-10" />
			<div v-else class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6">
				<template v-for="f in filters" :key="f.fieldname">
					<div v-if="!f.hidden && evalCondition(f.depends_on, values) && !['Section Break', 'Column Break', 'Break'].includes(f.fieldtype)">
						<label v-if="f.fieldtype !== 'Check'" :for="`rf-${f.fieldname}`" class="mb-1 block text-[12px] text-nxg-text-2">{{ f.label || f.fieldname }}<span v-if="f.reqd" class="text-nxg-danger"> *</span></label>
						<FieldInput :input-id="`rf-${f.fieldname}`" :field="{ ...f, fieldtype: ['MultiSelectList', 'MultiSelect'].includes(f.fieldtype) ? 'Data' : f.fieldtype }" :model-value="values[f.fieldname]" :doc="values" :doctype="name" @update:model-value="(v) => (values[f.fieldname] = v)" />
					</div>
				</template>
			</div>
			<p v-if="!loading && !parsed" class="mt-2 text-[11.5px] text-nxg-text-3">Showing the common filters for this report.</p>
		</div>

		<div v-if="summary.length" class="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
			<div v-for="(s, i) in summary" :key="i" class="nxg-panel px-4 py-3">
				<div class="text-[12px] text-nxg-text-2">{{ s.label }}</div>
				<div class="nxg-tnum text-[20px] font-semibold">{{ displayValue(s.value, { fieldtype: s.datatype || 'Data', options: s.currency }) || s.value }}</div>
			</div>
		</div>

		<div class="nxg-panel min-w-0">
			<div v-if="rows.length" class="flex items-center gap-2 border-b border-nxg-border px-3 py-2">
				<label class="relative max-w-sm flex-1"><Icon name="search" :size="14" class="pointer-events-none absolute left-2.5 top-2 text-nxg-text-3" /><input v-model="q" class="nxg-input h-8 w-full pl-8" placeholder="Search in results" aria-label="Search in results" /></label>
				<span class="nxg-tnum ml-auto text-[12.5px] text-nxg-text-2">{{ shown.length }} row{{ shown.length === 1 ? "" : "s" }}</span>
			</div>
			<div v-if="error" class="flex items-start gap-2 px-4 py-4 text-[13px] text-nxg-danger"><Icon name="circle-alert" :size="15" class="mt-0.5" />{{ error }}</div>
			<div v-else-if="running && !rows.length" class="space-y-2 p-4"><div v-for="i in 6" :key="i" class="nxg-skeleton h-8" /></div>
			<NxgEmpty v-else-if="!rows.length" :text="message || (ready ? 'No data for these filters' : 'Fill in the required filters, then Run')" icon="chart-column" />
			<div v-else class="nxg-scroll max-h-[70vh] overflow-auto" :class="running && 'opacity-60'">
				<table class="w-full text-[12.5px]">
					<thead class="sticky top-0 bg-nxg-surface">
						<tr class="border-b border-nxg-border text-left text-[12px] text-nxg-text-2">
							<th v-for="c in columns" :key="c.fieldname" class="whitespace-nowrap px-3 py-2 font-medium" :class="numeric(c) && 'text-right'">{{ c.label }}</th>
						</tr>
					</thead>
					<tbody class="divide-y divide-nxg-border">
						<tr v-for="(r, i) in shown.slice(0, 2000)" :key="i" class="hover:bg-nxg-surface-2/50" :class="r.is_group || r.bold ? 'font-semibold' : ''">
							<td v-for="(c, ci) in columns" :key="c.fieldname" class="whitespace-nowrap px-3 py-1.5" :class="numeric(c) && 'nxg-tnum text-right'" :style="ci === 0 && r.indent ? { paddingLeft: `${12 + r.indent * 16}px` } : undefined">
								<a v-if="linkFor(c, r)" :href="linkFor(c, r)!" class="hover:underline">{{ r[c.fieldname] }}</a>
								<template v-else>{{ displayValue(r[c.fieldname], c, r) }}</template>
							</td>
						</tr>
					</tbody>
				</table>
				<p v-if="shown.length > 2000" class="px-3 py-2 text-[12px] text-nxg-text-3">Showing the first 2,000 rows. Export CSV for all of them.</p>
			</div>
		</div>
	</div>
</template>
