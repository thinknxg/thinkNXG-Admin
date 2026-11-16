<script setup lang="ts">
import { computed } from "vue";
import AreaChart from "@/components/ui/AreaChart.vue";
import BarList from "@/components/ui/BarList.vue";
import NxgEmpty from "@/components/ui/NxgEmpty.vue";
import NxgRestricted from "@/components/ui/NxgRestricted.vue";
import NxgAvatar from "@/components/ui/NxgAvatar.vue";
import Icon from "@/components/ui/Icon.vue";
import { fmtMoney, fmtNumber } from "@/composables/format";

/** One HR intelligence section. Parts the user may not see come back
 *  restricted; parts whose module is not installed come back unavailable. */
const props = defineProps<{ section: string; data: any }>();
const blocked = (part: any) => part !== null && typeof part === "object" && !Array.isArray(part) && (part.restricted || part.available === false);
const blockText = (part: any) => (part?.restricted ? "Restricted for your role" : "Not available on this site");
const day = (d: string) => (d ? new Date(String(d).slice(0, 10) + "T00:00:00").toLocaleDateString(undefined, { day: "numeric", month: "short" }) : "");
const cur = computed(() => props.data?.currency as string | undefined);
const money = (v: number) => fmtMoney(v, cur.value, true);
const days = (v: number) => `${fmtNumber(v)} day${v === 1 ? "" : "s"}`;
const tone: Record<string, string> = {
	Present: "text-nxg-success",
	"Work From Home": "text-nxg-success",
	Absent: "text-nxg-danger",
	"Half Day": "text-nxg-warning",
	"On Leave": "text-nxg-text-2",
	"Not marked": "text-nxg-text-3",
};
</script>

<template>
	<div v-if="data?.restricted" class="py-2"><NxgRestricted /></div>
	<div v-else-if="data?.available === false" class="py-2"><NxgEmpty text="This area is not installed on this site." /></div>
	<div v-else-if="data" class="grid gap-6 pt-1 lg:grid-cols-2">
		<!-- My team (managers) -->
		<template v-if="section === 'team'">
			<div class="lg:col-span-2">
				<h3 class="mb-2 text-[13px] font-medium">Your direct reports today</h3>
				<NxgEmpty v-if="!data.members.length" text="No direct reports match these filters" />
				<ul v-else class="grid gap-x-6 sm:grid-cols-2">
					<li v-for="m in data.members" :key="m.name" class="flex items-center gap-3 border-b border-nxg-border py-2.5">
						<NxgAvatar :name="m.employee_name" :image="m.image" :size="30" />
						<span class="min-w-0 flex-1">
							<span class="block truncate text-[13px] font-medium">{{ m.employee_name }}</span>
							<span class="block truncate text-[12px] text-nxg-text-2">{{ [m.designation, m.department].filter(Boolean).join(" · ") }}</span>
						</span>
						<span class="shrink-0 text-[12.5px] font-medium" :class="tone[m.today] || 'text-nxg-text-2'">{{ m.today }}</span>
					</li>
				</ul>
			</div>
		</template>

		<!-- Employee -->
		<template v-else-if="section === 'employee'">
			<div class="grid grid-cols-2 gap-3 lg:col-span-2">
				<div class="rounded-nxg bg-nxg-surface-2 px-3 py-2.5"><div class="text-[12px] text-nxg-text-2">Joined in period</div><div class="nxg-tnum text-[20px] font-semibold">{{ fmtNumber(data.joiners) }}</div></div>
				<div class="rounded-nxg bg-nxg-surface-2 px-3 py-2.5"><div class="text-[12px] text-nxg-text-2">Left in period</div><div class="nxg-tnum text-[20px] font-semibold">{{ fmtNumber(data.leavers) }}</div></div>
			</div>
			<div>
				<h3 class="mb-2 text-[13px] font-medium">Active headcount by department</h3>
				<BarList v-if="data.by_department.length" :items="data.by_department" :format="fmtNumber" />
				<NxgEmpty v-else text="No active employees" />
			</div>
			<div>
				<h3 class="mb-2 text-[13px] font-medium">Active headcount by designation</h3>
				<BarList v-if="data.by_designation.length" :items="data.by_designation" :format="fmtNumber" />
				<NxgEmpty v-else text="No active employees" />
			</div>
		</template>

		<!-- Attendance -->
		<template v-else-if="section === 'attendance'">
			<div class="lg:col-span-2">
				<h3 class="mb-2 text-[13px] font-medium">Present per day</h3>
				<AreaChart :points="data.trend" value-key="present" value-label="Present" secondary-key="absent" secondary-label="Absent" />
			</div>
			<div class="grid grid-cols-2 gap-3 lg:col-span-2 lg:grid-cols-4">
				<div class="rounded-nxg bg-nxg-surface-2 px-3 py-2.5"><div class="text-[12px] text-nxg-text-2">Late entries</div><div class="nxg-tnum text-[20px] font-semibold">{{ fmtNumber(data.late_entries) }}</div></div>
				<div class="rounded-nxg bg-nxg-surface-2 px-3 py-2.5"><div class="text-[12px] text-nxg-text-2">Early exits</div><div class="nxg-tnum text-[20px] font-semibold">{{ fmtNumber(data.early_exits) }}</div></div>
				<div class="rounded-nxg bg-nxg-surface-2 px-3 py-2.5"><div class="text-[12px] text-nxg-text-2">Half days</div><div class="nxg-tnum text-[20px] font-semibold">{{ fmtNumber(data.half_days) }}</div></div>
				<div class="rounded-nxg bg-nxg-surface-2 px-3 py-2.5">
					<div class="text-[12px] text-nxg-text-2">Check-ins today</div>
					<div v-if="blocked(data.checkins_today)" class="flex items-center gap-1 pt-1 text-[13px] text-nxg-text-3"><Icon name="lock" :size="13" />{{ data.checkins_today.restricted ? "Restricted" : "Not available" }}</div>
					<div v-else class="nxg-tnum text-[20px] font-semibold">{{ fmtNumber(data.checkins_today) }}</div>
				</div>
			</div>
		</template>

		<!-- Leave -->
		<template v-else-if="section === 'leave'">
			<div>
				<h3 class="mb-2 text-[13px] font-medium">Leave taken by type, starting in period</h3>
				<BarList v-if="data.by_type.length" :items="data.by_type" :format="days" />
				<NxgEmpty v-else text="No approved leave in this period" />
				<p class="mt-3 text-[12.5px] text-nxg-text-2"><span class="nxg-tnum font-medium text-nxg-text">{{ fmtNumber(data.open_requests) }}</span> leave requests still open</p>
			</div>
			<div>
				<h3 class="mb-2 text-[13px] font-medium">On leave now or in the next 14 days</h3>
				<NxgEmpty v-if="!data.upcoming.length" text="No one is on leave" />
				<ul v-else class="divide-y divide-nxg-border text-[13px]">
					<li v-for="u in data.upcoming" :key="u.name" class="flex items-center justify-between gap-2 py-2">
						<span class="min-w-0">
							<component :is="u.route ? 'a' : 'span'" :href="u.route" class="block truncate font-medium" :class="u.route && 'hover:underline'">{{ u.employee_name }}</component>
							<span class="block truncate text-[12px] text-nxg-text-2">{{ u.leave_type }}</span>
						</span>
						<span class="nxg-tnum shrink-0 text-[12.5px] text-nxg-text-2">{{ day(u.from_date) }} – {{ day(u.to_date) }}</span>
					</li>
				</ul>
			</div>
		</template>

		<!-- Payroll (restricted roles only) -->
		<template v-else-if="section === 'payroll'">
			<div class="lg:col-span-2">
				<h3 class="mb-2 text-[13px] font-medium">Latest payroll run</h3>
				<NxgEmpty v-if="!data.latest" text="No submitted payroll run yet" />
				<div v-else class="grid grid-cols-2 gap-3 lg:grid-cols-4">
					<a :href="data.latest.route" class="rounded-nxg bg-nxg-surface-2 px-3 py-2.5 hover:underline"><div class="text-[12px] text-nxg-text-2">Period</div><div class="text-[14px] font-semibold">{{ day(data.latest.start_date) }} – {{ day(data.latest.end_date) }}</div></a>
					<div class="rounded-nxg bg-nxg-surface-2 px-3 py-2.5"><div class="text-[12px] text-nxg-text-2">Salary slips</div><div class="nxg-tnum text-[20px] font-semibold">{{ fmtNumber(data.latest.slips) }}</div></div>
					<div class="rounded-nxg bg-nxg-surface-2 px-3 py-2.5"><div class="text-[12px] text-nxg-text-2">Gross pay</div><div class="nxg-tnum text-[20px] font-semibold">{{ money(data.latest.gross) }}</div></div>
					<div class="rounded-nxg bg-nxg-surface-2 px-3 py-2.5"><div class="text-[12px] text-nxg-text-2">Net pay</div><div class="nxg-tnum text-[20px] font-semibold">{{ money(data.latest.net) }}</div></div>
				</div>
			</div>
			<div>
				<h3 class="mb-2 text-[13px] font-medium">Net pay by pay period</h3>
				<BarList v-if="data.history.length" :items="data.history.map((h: any) => ({ label: day(h.label), value: h.net }))" :format="money" />
				<NxgEmpty v-else text="No submitted salary slips in the last year" />
			</div>
			<div>
				<h3 class="mb-2 text-[13px] font-medium">Salary slips in period by status</h3>
				<BarList v-if="data.slips_by_status.length" :items="data.slips_by_status" :format="fmtNumber" />
				<NxgEmpty v-else text="No salary slips in this period" />
			</div>
			<p class="text-[12px] text-nxg-text-3 lg:col-span-2">Totals only. Individual salaries are never shown here.</p>
		</template>

		<!-- Recruitment -->
		<template v-else-if="section === 'recruitment'">
			<div class="lg:col-span-2">
				<h3 class="mb-2 text-[13px] font-medium">Open positions</h3>
				<NxgEmpty v-if="!data.openings.length" text="No open positions" />
				<ul v-else class="divide-y divide-nxg-border text-[13px]">
					<li v-for="o in data.openings" :key="o.name" class="flex items-center justify-between gap-2 py-2">
						<span class="min-w-0"><a :href="o.route" class="block truncate font-medium hover:underline">{{ o.job_title || o.name }}</a><span class="block truncate text-[12px] text-nxg-text-2">{{ o.designation }}</span></span>
						<span class="nxg-tnum shrink-0 text-[12.5px] text-nxg-text-2">{{ o.planned_vacancies ? `${o.planned_vacancies} vacancies` : "" }}{{ o.closes_on ? ` · closes ${day(o.closes_on)}` : "" }}</span>
					</li>
				</ul>
			</div>
			<div>
				<h3 class="mb-2 text-[13px] font-medium">Applicants in period by status</h3>
				<NxgRestricted v-if="blocked(data.applicants_by_status)" :text="blockText(data.applicants_by_status)" />
				<BarList v-else-if="data.applicants_by_status.length" :items="data.applicants_by_status" :format="fmtNumber" />
				<NxgEmpty v-else text="No applicants in this period" />
			</div>
			<div>
				<h3 class="mb-2 text-[13px] font-medium">Interviews and offers</h3>
				<p class="mb-2 text-[12.5px] text-nxg-text-2">
					<template v-if="blocked(data.upcoming_interviews)">Interviews: {{ data.upcoming_interviews.restricted ? "restricted" : "not available" }}</template>
					<template v-else><span class="nxg-tnum font-medium text-nxg-text">{{ fmtNumber(data.upcoming_interviews) }}</span> interviews scheduled from today</template>
				</p>
				<NxgRestricted v-if="blocked(data.offers)" :text="blockText(data.offers)" />
				<BarList v-else-if="data.offers.length" :items="data.offers" :format="fmtNumber" />
				<NxgEmpty v-else text="No open offers" />
			</div>
		</template>

		<!-- Performance -->
		<template v-else-if="section === 'performance'">
			<div>
				<h3 class="mb-2 text-[13px] font-medium">Appraisal cycles in progress</h3>
				<NxgEmpty v-if="!data.cycles.length" text="No active appraisal cycles" />
				<ul v-else class="divide-y divide-nxg-border text-[13px]">
					<li v-for="c in data.cycles" :key="c.name" class="flex items-center justify-between gap-2 py-2">
						<span class="min-w-0"><a :href="c.route" class="block truncate font-medium hover:underline">{{ c.cycle_name || c.name }}</a><span class="block text-[12px] text-nxg-text-2">{{ c.status }} · {{ day(c.start_date) }} – {{ day(c.end_date) }}</span></span>
						<span v-if="c.appraisals !== null" class="nxg-tnum shrink-0 text-[12.5px] text-nxg-text-2">{{ fmtNumber(c.appraisals) }} appraisals</span>
					</li>
				</ul>
			</div>
			<div>
				<h3 class="mb-2 text-[13px] font-medium">Goals by status</h3>
				<NxgRestricted v-if="blocked(data.goals_by_status)" :text="blockText(data.goals_by_status)" />
				<BarList v-else-if="data.goals_by_status.length" :items="data.goals_by_status" :format="fmtNumber" />
				<NxgEmpty v-else text="No goals recorded" />
			</div>
		</template>

		<!-- Lifecycle -->
		<template v-else-if="section === 'lifecycle'">
			<div>
				<h3 class="mb-2 text-[13px] font-medium">Onboarding in progress</h3>
				<NxgRestricted v-if="blocked(data.onboarding)" :text="blockText(data.onboarding)" />
				<BarList v-else-if="data.onboarding.length" :items="data.onboarding" :format="fmtNumber" />
				<NxgEmpty v-else text="No onboarding in progress" />
			</div>
			<div>
				<h3 class="mb-2 text-[13px] font-medium">Separations in progress</h3>
				<NxgRestricted v-if="blocked(data.separation)" :text="blockText(data.separation)" />
				<BarList v-else-if="data.separation.length" :items="data.separation" :format="fmtNumber" />
				<NxgEmpty v-else text="No separations in progress" />
			</div>
			<div class="grid grid-cols-3 gap-3 lg:col-span-2">
				<div v-for="[key, label] in [['promotions', 'Promotions in period'], ['transfers', 'Transfers in period'], ['open_grievances', 'Open grievances']]" :key="key" class="rounded-nxg bg-nxg-surface-2 px-3 py-2.5">
					<div class="text-[12px] text-nxg-text-2">{{ label }}</div>
					<div v-if="blocked(data[key])" class="flex items-center gap-1 pt-1 text-[13px] text-nxg-text-3"><Icon name="lock" :size="13" />{{ data[key].restricted ? "Restricted" : "Not available" }}</div>
					<div v-else class="nxg-tnum text-[20px] font-semibold">{{ fmtNumber(data[key]) }}</div>
				</div>
			</div>
		</template>
	</div>
</template>
