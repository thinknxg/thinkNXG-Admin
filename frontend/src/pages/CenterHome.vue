<script setup lang="ts">
import { computed } from "vue";
import Icon from "@/components/ui/Icon.vue";
import NxgPanel from "@/components/ui/NxgPanel.vue";
import { getCenter, type CenterKey } from "@/data/boot";
import { peekState } from "@/data/centers";

/** Home of the ERP and HR command centers, in the Admin Command Center's exact
 *  design language. The KPI grid and intelligence sections plug in here as
 *  they are built; until then the page offers only real, permission-checked
 *  routes and never shows a figure. */
const props = defineProps<{ centerKey: CenterKey }>();
const center = computed(() => getCenter(props.centerKey));
const state = computed(() => peekState(props.centerKey));
const destinations = computed(() => (center.value?.navigation || []).filter((s) => s.section !== "Overview").flatMap((s) => s.items.map((i) => ({ ...i, section: s.section }))));
const accessNote = computed(() => {
	switch (center.value?.access) {
		case "limited":
			return props.centerKey === "hr" ? "Payroll figures are restricted for your role." : "Some figures are restricted by your permissions.";
		case "team":
			return "You see your direct reports only.";
		default:
			return null;
	}
});
const greeting = computed(() => {
	const h = new Date().getHours();
	return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
});
const period = computed(() => (state.value.fiscal_year ? `Fiscal year ${state.value.fiscal_year}` : `Last ${state.value.days ?? 30} days`));
</script>

<template>
	<div v-if="center" class="mx-auto w-full max-w-[1280px] px-4 pb-10 pt-6 sm:px-6">
		<div class="mb-6 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
			<div class="min-w-0">
				<p class="mb-1 text-[12.5px] text-nxg-text-2">{{ greeting }}</p>
				<h1 class="text-[22px] font-semibold leading-8">{{ center.title }}</h1>
				<p class="text-[13.5px] text-nxg-text-2">{{ center.subtitle }}</p>
			</div>
			<div class="flex flex-wrap items-center gap-2 text-[12.5px] text-nxg-text-2">
				<span class="inline-flex items-center gap-1.5 rounded-full border border-nxg-border bg-nxg-surface px-2.5 py-1"><Icon name="building-2" :size="13" />{{ state.company || "All companies" }}</span>
				<span class="inline-flex items-center gap-1.5 rounded-full border border-nxg-border bg-nxg-surface px-2.5 py-1"><Icon name="calendar-range" :size="13" />{{ period }}</span>
				<span v-if="accessNote" class="inline-flex items-center gap-1.5 rounded-full border border-nxg-border bg-nxg-surface px-2.5 py-1"><Icon name="lock" :size="13" />{{ accessNote }}</span>
			</div>
		</div>

		<NxgPanel title="Dashboard" class="mb-5">
			<div class="flex items-start gap-3 py-1">
				<span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-nxg border border-nxg-border bg-nxg-surface-2"><Icon name="layout-dashboard" :size="17" /></span>
				<div class="text-[13.5px]">
					<p class="font-medium">KPIs and intelligence sections are being added to this center.</p>
					<p class="text-nxg-text-2">Every figure will be counted from your own records, under your permissions. Nothing on this page is estimated. Until then, open any area below.</p>
				</div>
			</div>
		</NxgPanel>

		<div class="grid gap-5 lg:grid-cols-3">
			<NxgPanel title="Go to" class="lg:col-span-2">
				<div v-if="destinations.length" class="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
					<component
						:is="d.href ? 'a' : 'RouterLink'"
						v-for="d in destinations"
						:key="d.key"
						:href="d.href"
						:to="d.href ? undefined : d.route"
						class="group flex items-center gap-2.5 rounded-nxg border border-nxg-border px-3 py-2.5 transition-colors hover:border-nxg-border-strong hover:bg-nxg-surface-2"
					>
						<Icon :name="d.icon" :size="16" class="text-nxg-text-2" />
						<span class="min-w-0 flex-1">
							<span class="block truncate text-[13px] font-medium">{{ d.label }}</span>
							<span class="block truncate text-[11.5px] text-nxg-text-3">{{ d.status === "planned" ? "Coming to this center" : d.href ? "Opens in Desk" : d.section }}</span>
						</span>
						<Icon :name="d.href ? 'arrow-up-right' : 'chevron-right'" :size="14" class="text-nxg-text-3 group-hover:text-nxg-text" />
					</component>
				</div>
				<p v-else class="text-[13px] text-nxg-text-2">No areas of this center are open to your role.</p>
			</NxgPanel>

			<NxgPanel title="Create">
				<div v-if="center.quick_create.length" class="flex flex-wrap gap-2">
					<a v-for="q in center.quick_create" :key="q.doctype" :href="q.route" class="nxg-btn nxg-btn-secondary h-8"><Icon :name="q.icon" :size="14" />{{ q.doctype }}</a>
				</div>
				<p v-else class="text-[13px] text-nxg-text-2">Your role cannot create records here.</p>
			</NxgPanel>
		</div>
	</div>
	<div v-else class="px-6 py-16 text-center text-nxg-text-2">This command center isn't available to you.</div>
</template>
