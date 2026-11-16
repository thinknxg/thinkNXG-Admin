<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import PageHeader from "@/components/ui/PageHeader.vue";
import NxgPanel from "@/components/ui/NxgPanel.vue";
import NxgTabs from "@/components/ui/NxgTabs.vue";
import NxgEmpty from "@/components/ui/NxgEmpty.vue";
import Icon from "@/components/ui/Icon.vue";
import { usePanel } from "@/data/api";
import { shell } from "@/data/shell";
import { fmtNumber } from "@/composables/format";

const org = usePanel<any>("thinknxg_admin.api.organization.get_organization", () => ({ company: shell.company }));
const tab = ref("structure");
const collapsed = reactive<Record<string, boolean>>({});
const deptSearch = ref("");

/** Flatten the department nested set into rows with depth, honouring collapsed nodes. */
const tree = computed(() => {
	const depts: any[] = org.state.data?.departments || [];
	const byParent: Record<string, any[]> = {};
	const names = new Set(depts.map((d) => d.name));
	for (const d of depts) {
		const p = d.parent_department && names.has(d.parent_department) ? d.parent_department : "__root__";
		(byParent[p] ||= []).push(d);
	}
	const total = (d: any): number => (d.employees || 0) + (byParent[d.name] || []).reduce((s, c) => s + total(c), 0);
	const out: any[] = [];
	const q = deptSearch.value.toLowerCase();
	const walk = (parent: string, depth: number) => {
		for (const d of byParent[parent] || []) {
			const kids = byParent[d.name] || [];
			if (!q || (d.department_name || d.name).toLowerCase().includes(q)) out.push({ ...d, depth, hasChildren: kids.length > 0, total: total(d) });
			if (!collapsed[d.name] || q) walk(d.name, q ? 0 : depth + 1);
		}
	};
	walk("__root__", 0);
	return out;
});
const maxBranch = computed(() => Math.max(1, ...(org.state.data?.branches || []).map((b: any) => b.employees || 0)));
const regionalRows = computed(() => {
	const r = org.state.data?.regional || {};
	return [["Country", r.country], ["Time zone", r.time_zone], ["Language", r.language], ["Default currency", r.currency], ["Date format", r.date_format], ["Time format", r.time_format], ["Number format", r.number_format], ["First day of week", r.first_day_of_the_week]];
});
</script>

<template>
	<div class="mx-auto w-full max-w-[1480px] px-4 pb-10 pt-6 sm:px-6">
		<PageHeader title="Organization" :description="shell.company ? `Structure for ${shell.company}. Change the scope with the organisation selector in the top bar.` : 'Companies, departments, branches and designations across the organisation.'">
			<a href="/desk/company/new" class="nxg-btn nxg-btn-secondary"><Icon name="plus" :size="14" />Company</a>
			<a href="/desk/department/new" class="nxg-btn nxg-btn-secondary"><Icon name="plus" :size="14" />Department</a>
			<button class="nxg-icon-btn" aria-label="Reload" @click="org.load(true)"><Icon name="refresh-cw" :size="15" :class="org.state.loading && 'animate-spin'" /></button>
		</PageHeader>

		<div v-if="org.state.data && !org.state.data.available" class="nxg-panel p-8 text-center text-[13px] text-nxg-text-2">Company is not installed on this site. Install thinkNXG ERP to manage organisation structure.</div>
		<template v-else>
			<!-- Companies -->
			<div class="mb-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
				<template v-if="org.state.loading && !org.state.data"><div v-for="i in 3" :key="i" class="nxg-skeleton h-36" /></template>
				<a v-for="c in org.state.data?.companies || []" :key="c.name" :href="`/desk/company/${encodeURIComponent(c.name)}`" class="nxg-panel group flex flex-col gap-3 p-4 transition-colors hover:border-nxg-border-strong" :class="shell.company === c.name && 'ring-1 ring-nxg-border-strong'">
					<div class="flex items-start justify-between gap-2">
						<div class="min-w-0">
							<div class="flex items-center gap-2"><span class="truncate text-[14.5px] font-semibold">{{ c.name }}</span><span class="nxg-chip">{{ c.abbr }}</span></div>
							<div class="truncate text-[12.5px] text-nxg-text-2">{{ [c.country, c.default_currency].filter(Boolean).join(" · ") }}<span v-if="c.parent_company"> · part of {{ c.parent_company }}</span></div>
						</div>
						<Icon name="arrow-up-right" :size="14" class="text-nxg-text-3 opacity-0 transition-opacity group-hover:opacity-100" />
					</div>
					<dl class="grid grid-cols-4 gap-2 text-center">
						<div v-for="[k, l] in [['employees', 'Employees'], ['departments', 'Depts'], ['cost_centers', 'Cost ctrs'], ['warehouses', 'Warehouses']]" :key="k" class="rounded-nxg bg-nxg-surface-2 px-1 py-1.5">
							<dd class="nxg-tnum text-[15px] font-semibold" :class="c.counts[k] === null && 'text-[12px] font-medium text-nxg-text-3'">{{ c.counts[k] === null ? "n/a" : fmtNumber(c.counts[k]) }}</dd>
							<dt class="truncate text-[11px] text-nxg-text-2">{{ l }}</dt>
						</div>
					</dl>
				</a>
			</div>

			<div class="nxg-panel">
				<div class="px-4 pt-1"><NxgTabs v-model="tab" :tabs="[{ key: 'structure', label: 'Department hierarchy', count: org.state.data?.departments?.length }, { key: 'branches', label: 'Branches', count: org.state.data?.branches?.length }, { key: 'designations', label: 'Designations', count: org.state.data?.designations?.length }, { key: 'fiscal', label: 'Fiscal years & regional' }]" /></div>
				<div v-if="org.state.error" class="p-4 text-[13px] text-nxg-danger">{{ org.state.error }} <button class="nxg-btn nxg-btn-secondary ml-2 h-7" @click="org.load(true)">Retry</button></div>
				<div v-else-if="org.state.loading && !org.state.data" class="space-y-2 p-4"><div v-for="i in 8" :key="i" class="nxg-skeleton h-6" /></div>

				<div v-else-if="tab === 'structure'" class="p-4">
					<div class="mb-3 flex items-center gap-2"><input v-model="deptSearch" class="nxg-input max-w-xs" placeholder="Find a department" aria-label="Find a department" /><span class="text-[12px] text-nxg-text-2">Head counts are active employees, including sub-departments.</span></div>
					<NxgEmpty v-if="!tree.length" text="No departments yet" icon="network" />
					<ul v-else role="tree" class="text-[13px]">
						<li v-for="d in tree" :key="d.name" role="treeitem" :aria-expanded="d.hasChildren ? !collapsed[d.name] : undefined" class="group flex items-center gap-1.5 rounded-nxg-sm py-1 pr-2 hover:bg-nxg-surface-2" :style="{ paddingLeft: `${8 + d.depth * 22}px` }">
							<button v-if="d.hasChildren" class="flex h-5 w-5 items-center justify-center rounded text-nxg-text-2 hover:text-nxg-text" :aria-label="collapsed[d.name] ? 'Expand' : 'Collapse'" @click="collapsed[d.name] = !collapsed[d.name]"><Icon :name="collapsed[d.name] ? 'chevron-right' : 'chevron-down'" :size="14" /></button>
							<span v-else class="w-5" />
							<Icon :name="d.is_group ? 'network' : 'users'" :size="14" class="text-nxg-text-3" />
							<a :href="`/desk/department/${encodeURIComponent(d.name)}`" class="min-w-0 flex-1 truncate hover:underline" :class="d.is_group && 'font-medium'">{{ d.department_name || d.name }}</a>
							<span v-if="d.company && !shell.company" class="hidden text-[11.5px] text-nxg-text-3 sm:inline">{{ d.company }}</span>
							<span class="nxg-tnum w-16 text-right text-[12px] text-nxg-text-2" :title="d.total !== null ? `${d.total} active employees` : ''">{{ d.employees === null ? "" : d.total }}</span>
						</li>
					</ul>
				</div>

				<div v-else-if="tab === 'branches'" class="p-4">
					<NxgEmpty v-if="!org.state.data.branches.length" text="No branches yet" icon="git-branch"><a href="/desk/branch/new" class="nxg-btn nxg-btn-secondary mt-2 h-7">Add branch</a></NxgEmpty>
					<ul v-else class="grid grid-cols-1 gap-x-8 gap-y-2 md:grid-cols-2">
						<li v-for="b in org.state.data.branches" :key="b.name">
							<a :href="`/desk/branch/${encodeURIComponent(b.name)}`" class="block rounded-nxg-sm" :title="`${b.name}: ${b.employees ?? 'n/a'} employees`">
								<div class="flex justify-between text-[13px]"><span class="truncate hover:underline">{{ b.name }}</span><span class="nxg-tnum text-nxg-text-2">{{ b.employees ?? "—" }}</span></div>
								<div class="mt-1 h-1.5 rounded-full bg-nxg-surface-2"><div class="h-1.5 rounded-full bg-[var(--nxg-chart-1)]" :style="{ width: `${Math.max(2, ((b.employees || 0) / maxBranch) * 100)}%` }" /></div>
							</a>
						</li>
					</ul>
				</div>

				<div v-else-if="tab === 'designations'" class="p-4">
					<NxgEmpty v-if="!org.state.data.designations.length" text="No designations yet" icon="id-card" />
					<ul v-else class="grid grid-cols-1 gap-x-6 sm:grid-cols-2 lg:grid-cols-3">
						<li v-for="d in org.state.data.designations" :key="d.name"><a :href="`/desk/designation/${encodeURIComponent(d.name)}`" class="flex justify-between border-b border-nxg-border py-1.5 text-[13px] hover:text-nxg-text"><span class="truncate">{{ d.name }}</span><span class="nxg-tnum text-nxg-text-2">{{ d.employees ?? "—" }}</span></a></li>
					</ul>
				</div>

				<div v-else class="grid grid-cols-1 gap-6 p-4 lg:grid-cols-2">
					<div>
						<h3 class="mb-2 nxg-micro">Fiscal years</h3>
						<ul class="divide-y divide-nxg-border rounded-nxg border border-nxg-border text-[13px]">
							<li v-for="y in org.state.data.fiscal_years" :key="y.name" class="flex items-center justify-between px-3 py-2"><a :href="`/desk/fiscal-year/${encodeURIComponent(y.name)}`" class="font-medium hover:underline">{{ y.name }}</a><span class="text-nxg-text-2">{{ y.year_start_date }} → {{ y.year_end_date }}<span v-if="y.disabled" class="nxg-chip ml-2">Disabled</span></span></li>
							<li v-if="!org.state.data.fiscal_years.length" class="px-3 py-4 text-nxg-text-2">No fiscal years.</li>
						</ul>
					</div>
					<div>
						<h3 class="mb-2 nxg-micro">Regional settings</h3>
						<dl class="divide-y divide-nxg-border rounded-nxg border border-nxg-border text-[13px]">
							<div v-for="[k, v] in regionalRows" :key="k" class="flex justify-between px-3 py-2"><dt class="text-nxg-text-2">{{ k }}</dt><dd>{{ v || "—" }}</dd></div>
							<div class="flex justify-between px-3 py-2"><dt class="text-nxg-text-2">Enabled currencies</dt><dd class="nxg-tnum">{{ org.state.data.currencies_enabled ?? "—" }}</dd></div>
						</dl>
						<a href="/desk/system-settings" class="nxg-btn nxg-btn-ghost mt-2">Edit in System Settings<Icon name="external-link" :size="13" /></a>
					</div>
				</div>
			</div>
		</template>
	</div>
</template>
