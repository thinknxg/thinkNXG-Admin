<script setup lang="ts">
import { computed } from "vue";
import Icon from "@/components/ui/Icon.vue";
import NxgPanel from "@/components/ui/NxgPanel.vue";
import { getCenter, getModule } from "@/data/boot";
import { usePanel } from "@/data/api";
import { fmtNumber } from "@/composables/format";

/** /<center>/<module>: a module's home inside its command center. Every
 *  DocType and report the user may open, with live counts read under their
 *  permissions; nothing links to the Desk. */
const props = defineProps<{ center: string; module: string }>();
const mod = computed(() => getModule(props.center, props.module));
const center = computed(() => getCenter(props.center));
const overview = usePanel<{ doctypes: { doctype: string; slug: string; total: number; drafts?: number }[] }>("thinknxg_admin.api.docs.get_module_overview", () => ({ center: props.center, module: props.module }));
const counts = computed(() => Object.fromEntries((overview.state.data?.doctypes || []).map((d) => [d.doctype, d])));
const base = computed(() => `/thinknxg/${props.center}/${props.module}`);
</script>

<template>
	<div v-if="mod" class="mx-auto w-full max-w-[1480px] px-4 pb-10 pt-6 sm:px-6">
		<div class="mb-5 flex flex-wrap items-end justify-between gap-3">
			<div class="flex items-center gap-3">
				<span class="flex h-10 w-10 items-center justify-center rounded-nxg border border-nxg-border bg-nxg-surface"><Icon :name="mod.icon" :size="19" /></span>
				<div>
					<p class="text-[12.5px] text-nxg-text-2">{{ center?.label }}</p>
					<h1 class="text-[22px] font-semibold leading-8">{{ mod.label }}</h1>
				</div>
			</div>
			<button class="nxg-btn nxg-btn-secondary" :disabled="overview.state.loading" @click="overview.load(true)"><Icon name="refresh-cw" :size="14" :class="overview.state.loading && 'animate-spin'" />Refresh</button>
		</div>

		<div class="grid gap-4 xl:grid-cols-3">
			<div class="space-y-4 xl:col-span-2">
				<NxgPanel v-for="g in mod.groups" :key="g.label" :title="g.label" :error="overview.state.error" @retry="overview.load(true)">
					<div class="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
						<div v-for="d in g.items" :key="d.doctype" class="group relative flex flex-col rounded-nxg border border-nxg-border px-3 py-2.5 transition-colors hover:border-nxg-border-strong">
							<a :href="`${base}/${d.slug}`" class="text-[13.5px] font-medium after:absolute after:inset-0 group-hover:underline">{{ d.doctype }}</a>
							<div class="mt-1 flex items-center gap-2 text-[12px] text-nxg-text-2">
								<span v-if="overview.state.loading && !counts[d.doctype]" class="nxg-skeleton h-3 w-16" />
								<template v-else-if="counts[d.doctype]">
									<span class="nxg-tnum">{{ fmtNumber(counts[d.doctype].total) }} record{{ counts[d.doctype].total === 1 ? "" : "s" }}</span>
									<span v-if="counts[d.doctype].drafts" class="nxg-tnum rounded-full bg-[var(--nxg-warning-soft)] px-1.5 text-nxg-warning">{{ fmtNumber(counts[d.doctype].drafts) }} draft</span>
								</template>
							</div>
							<a v-if="d.create" :href="`${base}/${d.slug}/new`" class="relative z-10 mt-2 inline-flex w-fit items-center gap-1 text-[12px] font-medium text-nxg-text-2 hover:text-nxg-text"><Icon name="plus" :size="12" />New</a>
						</div>
					</div>
				</NxgPanel>
			</div>
			<NxgPanel title="Reports" :empty="!mod.reports.length" empty-text="No reports in this module for your role">
				<ul class="divide-y divide-nxg-border">
					<li v-for="r in mod.reports" :key="r">
						<a :href="`/thinknxg/${center?.key}/reports/${encodeURIComponent(r)}`" class="group flex items-center gap-2.5 py-2.5 text-[13px]">
							<Icon name="chart-column" :size="15" class="text-nxg-text-2" /><span class="flex-1 group-hover:underline">{{ r }}</span><Icon name="chevron-right" :size="14" class="text-nxg-text-3" />
						</a>
					</li>
				</ul>
			</NxgPanel>
		</div>
	</div>
	<div v-else class="px-6 py-16 text-center text-nxg-text-2">This module isn't available to you.</div>
</template>
