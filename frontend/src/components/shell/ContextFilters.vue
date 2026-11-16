<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { call } from "frappe-ui";
import Icon from "@/components/ui/Icon.vue";
import NxgMenu from "@/components/ui/NxgMenu.vue";
import NxgSelect from "@/components/ui/NxgSelect.vue";
import { boot, type CenterKey } from "@/data/boot";
import { activeCenter, peekState, stateFor } from "@/data/centers";
import { shell } from "@/data/shell";
import { errorMessage } from "@/data/api";

/** Header filters for the active center. Each center declares which it shows;
 *  every option list comes from the server, read under the user's permissions. */
const b = computed(() => boot.data!);
const center = computed(() => activeCenter.value);
const has = (f: string) => !!center.value?.filters.includes(f as any);
const isAdmin = computed(() => center.value?.key === "admin" || !center.value);

// Admin pages keep reading shell.company; ERP and HR keep their own state.
const company = computed({
	get: () => (isAdmin.value ? shell.company : peekState(center.value!.key).company) ?? "",
	set: (v: string) => {
		if (isAdmin.value) shell.company = v || null;
		else {
			const s = stateFor(center.value!.key);
			s.company = v || undefined;
			s.department = undefined; // departments belong to a company
		}
	},
});
function field(key: "branch" | "department" | "fiscal_year") {
	return computed({
		get: () => (center.value && !isAdmin.value ? peekState(center.value.key)[key] ?? "" : ""),
		set: (v: string) => {
			if (center.value && !isAdmin.value) stateFor(center.value.key)[key] = v || undefined;
		},
	});
}
const branch = field("branch");
const department = field("department");
const fiscalYear = field("fiscal_year");
const days = computed({
	get: () => String((center.value && !isAdmin.value ? peekState(center.value.key).days : shell.days) ?? 30),
	set: (v: string) => {
		if (center.value && !isAdmin.value) stateFor(center.value.key).days = Number(v);
		else shell.days = Number(v);
	},
});
const dayOptions = [
	{ label: "Today", value: "1" },
	{ label: "Last 7 days", value: "7" },
	{ label: "Last 30 days", value: "30" },
	{ label: "Last 90 days", value: "90" },
	{ label: "Last 12 months", value: "365" },
];

interface Options { branches: string[] | null; departments: { name: string; department_name?: string }[] | null; fiscal_years: { name: string }[] | null }
const options = ref<Options | null>(null);
const loadError = ref<string | null>(null);
async function load(key: CenterKey, comp: string) {
	try {
		options.value = await call("thinknxg_admin.api.centers.get_filter_options", { center: key, company: comp || null });
		loadError.value = null;
		// Forget saved values the user can no longer pick.
		const s = stateFor(key);
		if (s.branch && !options.value?.branches?.includes(s.branch)) s.branch = undefined;
		if (s.department && !options.value?.departments?.some((d) => d.name === s.department)) s.department = undefined;
		if (s.fiscal_year && !options.value?.fiscal_years?.some((y) => y.name === s.fiscal_year)) s.fiscal_year = undefined;
	} catch (e) {
		options.value = null;
		loadError.value = errorMessage(e);
	}
}
watch(
	() => [center.value?.key, company.value] as const,
	([key, comp]) => {
		options.value = null;
		if (key && key !== "admin") load(key, comp);
	},
	{ immediate: true },
);

const summary = computed(() => {
	const parts = [company.value || "All companies"];
	if (!isAdmin.value) {
		if (fiscalYear.value) parts.push(`FY ${fiscalYear.value}`);
		else parts.push(dayOptions.find((d) => d.value === days.value)?.label || `${days.value} days`);
		if (department.value) parts.push(department.value);
		if (branch.value) parts.push(branch.value);
	}
	return parts.join(" · ");
});
const activeCount = computed(() => [branch.value, department.value, fiscalYear.value].filter(Boolean).length);
</script>

<template>
	<NxgMenu v-if="b.companies.length || !isAdmin" align="right" width="w-[min(300px,calc(100vw-24px))]">
		<template #trigger="{ toggle }">
			<button class="nxg-btn nxg-btn-ghost h-8 max-w-[300px] px-2" :title="`Filters: ${summary}`" aria-label="Filters" @click="toggle">
				<Icon :name="isAdmin ? 'building-2' : 'filter'" :size="15" />
				<span class="hidden truncate md:inline">{{ summary }}</span>
				<span v-if="activeCount" class="nxg-tnum rounded-full bg-nxg-surface-2 px-1.5 text-[11px] font-medium">{{ activeCount }}</span>
				<Icon name="chevron-down" :size="13" class="hidden md:inline" />
			</button>
		</template>
		<div class="space-y-3 p-2" @click.stop>
			<div class="nxg-micro">{{ isAdmin ? "Organisation" : `${center?.short} filters` }}</div>
			<label v-if="has('company') || isAdmin" class="block">
				<span class="mb-1 block text-[12px] text-nxg-text-2">Company</span>
				<NxgSelect v-model="company" class="w-full" label="Company" placeholder="All companies" :options="b.companies.map((c) => ({ label: c.abbr ? `${c.name} (${c.abbr})` : c.name, value: c.name }))" />
			</label>
			<template v-if="!isAdmin">
				<label v-if="has('department') && options?.departments" class="block">
					<span class="mb-1 block text-[12px] text-nxg-text-2">Department</span>
					<NxgSelect v-model="department" class="w-full" label="Department" placeholder="All departments" :options="options.departments.map((d) => ({ label: d.department_name || d.name, value: d.name }))" />
				</label>
				<label v-if="has('branch') && options?.branches" class="block">
					<span class="mb-1 block text-[12px] text-nxg-text-2">Branch</span>
					<NxgSelect v-model="branch" class="w-full" label="Branch" placeholder="All branches" :options="options.branches" />
				</label>
				<label v-if="has('fiscal_year') && options?.fiscal_years" class="block">
					<span class="mb-1 block text-[12px] text-nxg-text-2">Fiscal year</span>
					<NxgSelect v-model="fiscalYear" class="w-full" label="Fiscal year" placeholder="Use the date range" :options="options.fiscal_years.map((y) => y.name)" />
				</label>
				<label v-if="has('date_range')" class="block">
					<span class="mb-1 block text-[12px] text-nxg-text-2">Date range</span>
					<NxgSelect v-model="days" class="w-full" label="Date range" :options="dayOptions" :disabled="!!fiscalYear" />
					<span v-if="fiscalYear" class="mt-1 block text-[11.5px] text-nxg-text-3">The fiscal year sets the period while it is selected.</span>
				</label>
				<p v-if="loadError" class="text-[12px] text-nxg-danger">{{ loadError }}</p>
				<p v-else-if="has('branch') && options && !options.branches && center?.key === 'erp'" class="text-[11.5px] text-nxg-text-3">Branch filtering appears once Branch is set up as an accounting dimension.</p>
			</template>
		</div>
	</NxgMenu>
</template>
