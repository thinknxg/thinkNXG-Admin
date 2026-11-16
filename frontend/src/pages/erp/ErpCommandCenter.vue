<script setup lang="ts">
import { computed, ref, watch } from "vue";
import Icon from "@/components/ui/Icon.vue";
import NxgKpi from "@/components/ui/NxgKpi.vue";
import NxgPanel from "@/components/ui/NxgPanel.vue";
import NxgTabs from "@/components/ui/NxgTabs.vue";
import NxgEmpty from "@/components/ui/NxgEmpty.vue";
import ErpSection from "@/components/erp/ErpSection.vue";
import { boot, getCenter } from "@/data/boot";
import { peekState } from "@/data/centers";
import { usePanel } from "@/data/api";
import { fmtNumber } from "@/composables/format";
import { readPref, writePref } from "@/composables/storage";

/** thinkNXG ERP Command Center. Same shell, tokens and components as the Admin
 *  Command Center. Every figure comes from erp.py, which reads submitted records
 *  under the user's own permissions; a figure the user may not see is withheld. */
const center = computed(() => getCenter("erp")!);
const filters = computed(() => {
	const s = peekState("erp");
	return { company: s.company || null, fiscal_year: s.fiscal_year || null, days: s.days || 30, branch: s.branch || null };
});
const kpis = usePanel<Record<string, any>>("thinknxg_admin.api.erp.get_kpis", () => filters.value);
const pending = usePanel<{ items: any[]; company: string }>("thinknxg_admin.api.erp.get_pending", () => ({ company: filters.value.company }));

const sections = [
	{ key: "sales", label: "Sales" },
	{ key: "finance", label: "Finance" },
	{ key: "purchase", label: "Purchase" },
	{ key: "inventory", label: "Inventory" },
	{ key: "manufacturing", label: "Manufacturing" },
	{ key: "projects", label: "Projects" },
	{ key: "crm", label: "CRM" },
];
const tab = ref<string>(readPref("erp-tab", "sales"));
const section = usePanel<any>("thinknxg_admin.api.erp.get_section", () => ({ section: tab.value, ...filters.value }));
// The tab whose data is on screen. Responses for older tabs are discarded by
// usePanel, so data that arrives always belongs to the current tab.
const shownTab = ref<string | null>(null);
watch(() => section.state.data, () => (shownTab.value = tab.value));
function setTab(t: string) {
	tab.value = t;
	writePref("erp-tab", t);
}

const k = computed(() => kpis.state.data || {});
const ctx = computed(() => k.value._context as { company: string; currency: string; start: string; end: string } | undefined);
const loading = computed(() => kpis.state.loading && !kpis.state.data);
const anyLoading = computed(() => [kpis, pending, section].some((p) => p.state.loading));
const firstName = computed(() => (boot.data?.user.full_name || "").split(" ")[0]);
const periodLabel = computed(() => {
	if (!ctx.value) return "";
	const f = (d: string) => new Date(d + "T00:00:00").toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
	return `${f(ctx.value.start)} – ${f(ctx.value.end)}`;
});
const periodCompare = computed(() => (filters.value.fiscal_year ? "vs prev. year" : "vs prev. period"));
function refreshAll() {
	kpis.load(true);
	pending.load(true);
	section.load(true);
}
const kp = (key: string) => ({ value: k.value[key]?.value, restricted: !!k.value[key]?.restricted, delta: k.value[key]?.delta, href: k.value[key]?.route, currency: k.value[key]?.currency });
</script>

<template>
	<div class="mx-auto w-full max-w-[1480px] px-4 pb-10 pt-6 sm:px-6">
		<!-- Header -->
		<div class="mb-5 flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
			<div class="min-w-0">
				<p class="mb-1 text-[12.5px] font-medium text-nxg-text-2">Good to see you{{ firstName ? `, ${firstName}` : "" }}</p>
				<h1 class="text-[24px] font-semibold leading-8 tracking-[-0.02em] sm:text-[28px] sm:leading-9">{{ center.title }}</h1>
				<p class="mt-1 text-[14px] text-nxg-text-2">{{ center.subtitle }}</p>
			</div>
			<div class="flex flex-wrap items-center gap-2 text-[12.5px]">
				<span v-if="ctx" class="inline-flex items-center gap-1.5 rounded-nxg border border-nxg-border bg-nxg-surface px-2.5 py-1.5"><Icon name="building-2" :size="13" class="text-nxg-text-2" /><span class="font-medium">{{ ctx.company }}</span><span class="text-nxg-text-3">· {{ ctx.currency }}</span></span>
				<span v-if="ctx" class="inline-flex items-center gap-1.5 rounded-nxg border border-nxg-border bg-nxg-surface px-2.5 py-1.5"><Icon name="calendar-range" :size="13" class="text-nxg-text-2" />{{ periodLabel }}</span>
				<span v-if="center.access === 'limited'" class="inline-flex items-center gap-1.5 rounded-nxg border border-nxg-border bg-nxg-surface px-2.5 py-1.5 text-nxg-text-2"><Icon name="lock" :size="13" />Some figures are restricted for your role</span>
				<button class="nxg-btn nxg-btn-secondary" :disabled="anyLoading" aria-label="Refresh all panels" @click="refreshAll"><Icon name="refresh-cw" :size="14" :class="anyLoading && 'animate-spin'" /><span class="hidden sm:inline">Refresh</span></button>
			</div>
		</div>

		<!-- KPIs -->
		<section aria-label="Key figures" class="mb-4">
			<div v-if="kpis.state.error" class="nxg-panel mb-3 flex items-center justify-between gap-3 px-4 py-3 text-[13px]">
				<span class="flex items-center gap-2 text-nxg-danger"><Icon name="circle-alert" :size="15" />Key figures couldn't load: {{ kpis.state.error }}</span>
				<button class="nxg-btn nxg-btn-secondary h-7" @click="kpis.load(true)">Retry</button>
			</div>
			<div class="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
				<NxgKpi label="Total revenue" icon="landmark" :loading="loading" v-bind="kp('total_revenue')" :delta-label="periodCompare" hint="Income accounts in the general ledger: credits minus debits for the period" />
				<NxgKpi label="Gross profit" icon="chart-column" :loading="loading" v-bind="kp('gross_profit')" :delta-label="periodCompare" :secondary="k.gross_profit?.secondary != null ? `${k.gross_profit.secondary}% margin` : null" hint="Revenue minus Cost of Goods Sold accounts for the period" />
				<NxgKpi label="Receivables" icon="arrow-down-right" :loading="loading" v-bind="kp('receivables')" hint="Outstanding on receivable accounts at the end of the period (payment ledger)" />
				<NxgKpi label="Payables" icon="arrow-up-right" :loading="loading" v-bind="kp('payables')" hint="Outstanding on payable accounts at the end of the period (payment ledger)" />
				<NxgKpi label="Cash & bank" icon="banknote" :loading="loading" v-bind="kp('cash_bank')" :secondary="k.cash_bank?.secondary ? `${k.cash_bank.secondary} accounts` : null" hint="Balance of Cash and Bank accounts at the end of the period" />
				<NxgKpi label="Open sales orders" icon="shopping-cart" :loading="loading" v-bind="kp('sales_orders')" :currency="null" :delta="k.sales_orders?.delta" delta-label="new orders" :secondary="k.sales_orders?.amount != null ? `${fmtNumber(k.sales_orders.amount)} ${k.sales_orders.currency}` : null" hint="Submitted orders still to deliver or bill" />
				<NxgKpi label="Open purchase orders" icon="shopping-bag" :loading="loading" v-bind="kp('purchase_orders')" :currency="null" :delta="k.purchase_orders?.delta" delta-label="new orders" :secondary="k.purchase_orders?.amount != null ? `${fmtNumber(k.purchase_orders.amount)} ${k.purchase_orders.currency}` : null" hint="Submitted orders still to receive or bill" />
				<NxgKpi label="Inventory value" icon="package" :loading="loading" v-bind="kp('inventory_valuation')" :secondary="k.inventory_valuation?.secondary ? `${k.inventory_valuation.secondary} warehouses` : null" hint="Current stock value in this company's warehouses" />
				<NxgKpi label="Unpaid invoices" icon="receipt" :loading="loading" v-bind="kp('outstanding_invoices')" :secondary="k.outstanding_invoices?.secondary != null ? `${k.outstanding_invoices.secondary} overdue` : null" hint="Submitted sales invoices with an outstanding amount" />
				<NxgKpi label="Pending approvals" icon="stamp" :loading="loading" v-bind="kp('pending_approvals')" href="/thinknxg/erp/approvals" hint="ERP documents waiting for an action you can take" />
			</div>
		</section>

		<div class="grid grid-cols-1 gap-4 xl:grid-cols-3">
			<!-- Intelligence -->
			<section class="nxg-panel min-w-0 px-4 pb-4 pt-3 xl:col-span-2" aria-label="Business intelligence">
				<NxgTabs :tabs="sections" :model-value="tab" @update:model-value="setTab" />
				<div class="pt-4">
					<div v-if="section.state.error" class="flex items-center justify-between gap-3 py-4 text-[13px]">
						<span class="flex items-center gap-2 text-nxg-danger"><Icon name="circle-alert" :size="15" />{{ section.state.error }}</span>
						<button class="nxg-btn nxg-btn-secondary h-7" @click="section.load(true)">Retry</button>
					</div>
					<div v-else-if="!section.state.data || shownTab === null" class="space-y-3"><div class="nxg-skeleton h-40" /><div class="nxg-skeleton h-24" /></div>
					<ErpSection v-else :section="shownTab" :data="section.state.data" :class="(section.state.loading || shownTab !== tab) && 'opacity-60'" />
				</div>
			</section>

			<!-- Pending actions -->
			<div class="flex flex-col gap-4">
				<NxgPanel title="Needs your attention" :loading="pending.state.loading && !pending.state.data" :error="pending.state.error" @retry="pending.load(true)">
					<NxgEmpty v-if="pending.state.data && !pending.state.data.items.length" text="Nothing waiting on you" icon="circle-check" />
					<ul v-else class="divide-y divide-nxg-border">
						<li v-for="p in pending.state.data?.items || []" :key="p.key">
							<a :href="p.route" class="group flex items-center gap-3 py-2.5 text-[13px]">
								<span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-nxg bg-nxg-surface-2"><Icon :name="p.icon" :size="15" /></span>
								<span class="min-w-0 flex-1 truncate group-hover:underline">{{ p.label }}</span>
								<span class="nxg-tnum font-semibold">{{ fmtNumber(p.value) }}</span>
								<Icon name="chevron-right" :size="14" class="text-nxg-text-3" />
							</a>
						</li>
					</ul>
				</NxgPanel>
				<NxgPanel title="Create">
					<div v-if="center.quick_create.length" class="flex flex-wrap gap-2">
						<a v-for="q in center.quick_create" :key="q.doctype" :href="q.route" class="nxg-btn nxg-btn-secondary h-8"><Icon :name="q.icon" :size="14" />{{ q.doctype }}</a>
					</div>
					<p v-else class="text-[13px] text-nxg-text-2">Your role cannot create ERP records.</p>
				</NxgPanel>
			</div>
		</div>
	</div>
</template>
