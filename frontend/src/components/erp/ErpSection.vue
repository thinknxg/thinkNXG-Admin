<script setup lang="ts">
import { computed } from "vue";
import AreaChart from "@/components/ui/AreaChart.vue";
import BarList from "@/components/ui/BarList.vue";
import NxgEmpty from "@/components/ui/NxgEmpty.vue";
import NxgRestricted from "@/components/ui/NxgRestricted.vue";
import Icon from "@/components/ui/Icon.vue";
import { fmtMoney, fmtNumber } from "@/composables/format";

/** One ERP intelligence section. Each part may come back restricted (the user
 *  cannot read its source) or unavailable (not installed); both are shown as such. */
const props = defineProps<{ section: string; data: any }>();
const cur = computed(() => props.data?.currency as string | undefined);
const money = (v: number) => fmtMoney(v, cur.value, true);
const moneyFull = (v: number) => fmtMoney(v, cur.value);
const blocked = (part: any) => part && !Array.isArray(part) && (part.restricted || part.available === false);
const blockText = (part: any) => (part?.restricted ? "Restricted for your role" : "Not available on this site");
const day = (d: string) => new Date(d + "T00:00:00").toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
</script>

<template>
	<div v-if="data?.restricted" class="py-2"><NxgRestricted /></div>
	<div v-else-if="data?.available === false" class="py-2"><NxgEmpty text="This area is not installed on this site." /></div>
	<div v-else-if="data" class="grid min-w-0 grid-cols-1 gap-6 pt-1 lg:grid-cols-2 [&>*]:min-w-0">
		<!-- Sales -->
		<template v-if="section === 'sales'">
			<div class="lg:col-span-2">
				<div class="mb-2 flex items-baseline justify-between"><h3 class="text-[13px] font-medium">Net sales per day</h3><span class="nxg-tnum text-[13px] text-nxg-text-2">{{ moneyFull(data.total) }} in period</span></div>
				<AreaChart :points="data.trend" value-key="value" value-label="Net sales" />
			</div>
			<div>
				<h3 class="mb-2 text-[13px] font-medium">Top customers</h3>
				<BarList v-if="data.top_customers.length" :items="data.top_customers" :format="money" />
				<NxgEmpty v-else text="No invoices in this period" />
			</div>
			<div>
				<h3 class="mb-2 text-[13px] font-medium">Quotation to invoice, documents in period</h3>
				<NxgRestricted v-if="blocked(data.funnel)" :text="blockText(data.funnel)" />
				<BarList v-else :items="data.funnel.stages.map((s: any) => ({ label: s.label, value: s.value, href: s.route }))" :format="fmtNumber" />
			</div>
		</template>

		<!-- Finance -->
		<template v-else-if="section === 'finance'">
			<div>
				<h3 class="mb-2 text-[13px] font-medium">Receivables by age</h3>
				<NxgRestricted v-if="blocked(data.receivable_ageing)" :text="blockText(data.receivable_ageing)" />
				<BarList v-else :items="data.receivable_ageing" :format="money" />
			</div>
			<div>
				<h3 class="mb-2 text-[13px] font-medium">Payables by age</h3>
				<NxgRestricted v-if="blocked(data.payable_ageing)" :text="blockText(data.payable_ageing)" />
				<BarList v-else :items="data.payable_ageing" :format="money" />
			</div>
			<div class="lg:col-span-2">
				<h3 class="mb-2 text-[13px] font-medium">Cash and bank balance</h3>
				<NxgRestricted v-if="blocked(data.cash_trend)" :text="blockText(data.cash_trend)" />
				<AreaChart v-else-if="data.cash_trend.length" :points="data.cash_trend" value-key="value" value-label="Balance" />
				<NxgEmpty v-else text="No cash or bank accounts for this company" />
			</div>
			<div class="lg:col-span-2">
				<h3 class="mb-2 text-[13px] font-medium">Most overdue sales invoices</h3>
				<NxgRestricted v-if="blocked(data.overdue_invoices)" :text="blockText(data.overdue_invoices)" />
				<NxgEmpty v-else-if="!data.overdue_invoices.length" text="Nothing overdue" />
				<table v-else class="w-full text-[13px]">
					<thead><tr class="text-left text-[12px] text-nxg-text-2"><th class="py-1.5 font-medium">Invoice</th><th class="font-medium">Customer</th><th class="font-medium">Due</th><th class="text-right font-medium">Outstanding</th></tr></thead>
					<tbody class="divide-y divide-nxg-border">
						<tr v-for="r in data.overdue_invoices" :key="r.name">
							<td class="py-2"><a :href="r.route" class="font-medium hover:underline">{{ r.name }}</a></td>
							<td class="truncate">{{ r.customer_name }}</td>
							<td class="text-nxg-text-2">{{ day(r.due_date) }} · {{ r.days }}d late</td>
							<td class="nxg-tnum text-right">{{ fmtMoney(r.outstanding_amount, r.currency) }}</td>
						</tr>
					</tbody>
				</table>
			</div>
		</template>

		<!-- Purchase -->
		<template v-else-if="section === 'purchase'">
			<div>
				<h3 class="mb-2 text-[13px] font-medium">Open purchase orders by status</h3>
				<NxgRestricted v-if="blocked(data.open_orders)" :text="blockText(data.open_orders)" />
				<BarList v-else-if="data.open_orders.length" :items="data.open_orders" :format="fmtNumber" />
				<NxgEmpty v-else text="No open purchase orders" />
			</div>
			<div>
				<h3 class="mb-2 text-[13px] font-medium">Top suppliers, invoiced in period</h3>
				<NxgRestricted v-if="blocked(data.top_suppliers)" :text="blockText(data.top_suppliers)" />
				<BarList v-else-if="data.top_suppliers.length" :items="data.top_suppliers" :format="money" />
				<NxgEmpty v-else text="No purchase invoices in this period" />
			</div>
			<div>
				<h3 class="mb-2 text-[13px] font-medium">Open material requests by type</h3>
				<NxgRestricted v-if="blocked(data.open_requests)" :text="blockText(data.open_requests)" />
				<BarList v-else-if="data.open_requests.length" :items="data.open_requests" :format="fmtNumber" />
				<NxgEmpty v-else text="No open material requests" />
			</div>
		</template>

		<!-- Inventory -->
		<template v-else-if="section === 'inventory'">
			<div>
				<h3 class="mb-2 text-[13px] font-medium">Stock value by warehouse</h3>
				<BarList v-if="data.by_warehouse.length" :items="data.by_warehouse" :format="money" />
				<NxgEmpty v-else text="No stock in this company's warehouses" />
			</div>
			<div>
				<h3 class="mb-2 text-[13px] font-medium">Below reorder level <span v-if="!blocked(data.below_reorder)" class="nxg-tnum text-nxg-text-2">· {{ data.below_reorder.count }}</span></h3>
				<NxgRestricted v-if="blocked(data.below_reorder)" :text="blockText(data.below_reorder)" />
				<NxgEmpty v-else-if="!data.below_reorder.items.length" text="Every item with a reorder level is above it" />
				<ul v-else class="divide-y divide-nxg-border text-[13px]">
					<li v-for="r in data.below_reorder.items" :key="r.item + r.warehouse" class="flex items-center justify-between gap-2 py-2">
						<span class="min-w-0"><a :href="r.route" class="block truncate font-medium hover:underline">{{ r.item }}</a><span class="block truncate text-[12px] text-nxg-text-2">{{ r.warehouse }}</span></span>
						<span class="nxg-tnum shrink-0 text-right text-[12.5px]">{{ fmtNumber(r.projected) }} <span class="text-nxg-text-3">/ {{ fmtNumber(r.reorder_level) }}</span></span>
					</li>
				</ul>
			</div>
		</template>

		<!-- Manufacturing -->
		<template v-else-if="section === 'manufacturing'">
			<div>
				<h3 class="mb-2 text-[13px] font-medium">Work orders by status</h3>
				<BarList v-if="data.by_status.length" :items="data.by_status" :format="fmtNumber" />
				<NxgEmpty v-else text="No work orders" />
			</div>
			<div>
				<h3 class="mb-2 text-[13px] font-medium">Open job cards</h3>
				<NxgRestricted v-if="blocked(data.job_cards)" :text="blockText(data.job_cards)" />
				<BarList v-else-if="data.job_cards.length" :items="data.job_cards" :format="fmtNumber" />
				<NxgEmpty v-else text="No open job cards" />
			</div>
			<div class="lg:col-span-2">
				<h3 class="mb-2 text-[13px] font-medium">Past planned end <span class="nxg-tnum text-nxg-text-2">· {{ data.late_count }}</span></h3>
				<NxgEmpty v-if="!data.late.length" text="No late work orders" />
				<ul v-else class="divide-y divide-nxg-border text-[13px]">
					<li v-for="w in data.late" :key="w.name" class="flex items-center justify-between gap-2 py-2">
						<span class="min-w-0"><a :href="w.route" class="font-medium hover:underline">{{ w.name }}</a> <span class="text-nxg-text-2">· {{ w.production_item }}</span></span>
						<span class="nxg-tnum shrink-0 text-[12.5px] text-nxg-text-2">{{ fmtNumber(w.produced_qty) }} of {{ fmtNumber(w.qty) }} · due {{ day(String(w.planned_end_date).slice(0, 10)) }}</span>
					</li>
				</ul>
			</div>
		</template>

		<!-- Projects -->
		<template v-else-if="section === 'projects'">
			<div class="grid grid-cols-3 gap-3 lg:col-span-2">
				<div class="rounded-nxg bg-nxg-surface-2 px-3 py-2.5"><div class="text-[12px] text-nxg-text-2">Active projects</div><div class="nxg-tnum text-[20px] font-semibold">{{ fmtNumber(data.active_count) }}</div></div>
				<div class="rounded-nxg bg-nxg-surface-2 px-3 py-2.5">
					<div class="text-[12px] text-nxg-text-2">Overdue tasks</div>
					<div v-if="blocked(data.overdue_tasks)" class="flex items-center gap-1 pt-1 text-[13px] text-nxg-text-3"><Icon name="lock" :size="13" />{{ data.overdue_tasks.restricted ? "Restricted" : "Not available" }}</div>
					<div v-else class="nxg-tnum text-[20px] font-semibold">{{ fmtNumber(data.overdue_tasks) }}</div>
				</div>
				<div class="rounded-nxg bg-nxg-surface-2 px-3 py-2.5">
					<div class="text-[12px] text-nxg-text-2">Timesheets to bill</div>
					<div v-if="blocked(data.unbilled_timesheets)" class="flex items-center gap-1 pt-1 text-[13px] text-nxg-text-3"><Icon name="lock" :size="13" />{{ data.unbilled_timesheets.restricted ? "Restricted" : "Not available" }}</div>
					<div v-else class="nxg-tnum text-[20px] font-semibold">{{ fmtNumber(data.unbilled_timesheets) }}</div>
				</div>
			</div>
			<div class="lg:col-span-2">
				<h3 class="mb-2 text-[13px] font-medium">Active projects by end date</h3>
				<NxgEmpty v-if="!data.active.length" text="No open projects" />
				<ul v-else class="divide-y divide-nxg-border text-[13px]">
					<li v-for="p in data.active" :key="p.name" class="flex items-center gap-3 py-2">
						<a :href="p.route" class="min-w-0 flex-1 truncate font-medium hover:underline">{{ p.project_name || p.name }}</a>
						<div class="hidden h-1.5 w-32 rounded-full bg-nxg-surface-2 sm:block"><div class="h-1.5 rounded-full bg-[var(--nxg-chart-1)]" :style="{ width: `${Math.min(100, p.percent_complete || 0)}%` }" /></div>
						<span class="nxg-tnum w-10 text-right text-[12.5px]">{{ Math.round(p.percent_complete || 0) }}%</span>
						<span class="w-28 text-right text-[12px] text-nxg-text-2">{{ p.expected_end_date ? day(p.expected_end_date) : "No end date" }}</span>
					</li>
				</ul>
			</div>
		</template>

		<!-- CRM -->
		<template v-else-if="section === 'crm'">
			<div>
				<h3 class="mb-2 text-[13px] font-medium">New leads by status</h3>
				<NxgRestricted v-if="blocked(data.leads_by_status)" :text="blockText(data.leads_by_status)" />
				<BarList v-else-if="data.leads_by_status.length" :items="data.leads_by_status" :format="fmtNumber" />
				<NxgEmpty v-else text="No new leads in this period" />
			</div>
			<div>
				<h3 class="mb-2 text-[13px] font-medium">Open pipeline by sales stage</h3>
				<NxgRestricted v-if="blocked(data.opportunities)" :text="blockText(data.opportunities)" />
				<template v-else>
					<p class="mb-2 text-[12.5px] text-nxg-text-2"><span class="nxg-tnum font-medium text-nxg-text">{{ fmtNumber(data.opportunities.count) }}</span> open opportunities · <span class="nxg-tnum font-medium text-nxg-text">{{ moneyFull(data.opportunities.amount) }}</span></p>
					<BarList v-if="data.opportunities.by_stage.length" :items="data.opportunities.by_stage" :format="money" />
				</template>
			</div>
		</template>
	</div>
</template>
