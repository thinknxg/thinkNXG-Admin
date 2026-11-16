<script setup lang="ts">
import { computed, ref, watch } from "vue";
import Icon from "@/components/ui/Icon.vue";
import NxgKpi from "@/components/ui/NxgKpi.vue";
import NxgPanel from "@/components/ui/NxgPanel.vue";
import NxgTabs from "@/components/ui/NxgTabs.vue";
import NxgEmpty from "@/components/ui/NxgEmpty.vue";
import HrSection from "@/components/hr/HrSection.vue";
import { boot, getCenter } from "@/data/boot";
import { peekState } from "@/data/centers";
import { usePanel } from "@/data/api";
import { fmtNumber } from "@/composables/format";
import { readPref, writePref } from "@/composables/storage";

/** thinkNXG HR Command Center, in the Admin Command Center's design language.
 *  HR roles see the whole workforce they may read; managers without an HR role
 *  see their direct reports only ("My team"). Payroll appears only for roles the
 *  server allows, and only as totals. */
const center = computed(() => getCenter("hr")!);
const team = computed(() => center.value.access === "team");
const payroll = computed(() => center.value.access === "full");
const filters = computed(() => {
	const s = peekState("hr");
	return { company: s.company || null, department: s.department || null, branch: s.branch || null, days: s.days || 30 };
});
const kpis = usePanel<Record<string, any>>("thinknxg_admin.api.hr.get_kpis", () => filters.value);
const pending = usePanel<{ items: any[] }>("thinknxg_admin.api.hr.get_pending", () => ({ company: filters.value.company }));

const sections = computed(() =>
	team.value
		? [{ key: "team", label: "My team" }, { key: "attendance", label: "Attendance" }, { key: "leave", label: "Leave" }]
		: [
				{ key: "employee", label: "Employees" },
				{ key: "attendance", label: "Attendance" },
				{ key: "leave", label: "Leave" },
				...(payroll.value ? [{ key: "payroll", label: "Payroll" }] : []),
				{ key: "recruitment", label: "Recruitment" },
				{ key: "performance", label: "Performance" },
				{ key: "lifecycle", label: "Lifecycle" },
			],
);
const saved = readPref<string>("hr-tab", "");
const tab = ref<string>(sections.value.some((s) => s.key === saved) ? saved : sections.value[0].key);
const section = usePanel<any>("thinknxg_admin.api.hr.get_section", () => ({ section: tab.value, ...filters.value }));
const shownTab = ref<string | null>(null);
watch(() => section.state.data, () => (shownTab.value = tab.value));
function setTab(t: string) {
	tab.value = t;
	writePref("hr-tab", t);
}

const k = computed(() => kpis.state.data || {});
const ctx = computed(() => k.value._context as { level: string; company: string | null; start: string; end: string; team_size: number | null } | undefined);
const loading = computed(() => kpis.state.loading && !kpis.state.data);
const anyLoading = computed(() => [kpis, pending, section].some((p) => p.state.loading));
const firstName = computed(() => (boot.data?.user.full_name || "").split(" ")[0]);
const periodLabel = computed(() => {
	if (!ctx.value) return "";
	const f = (d: string) => new Date(d + "T00:00:00").toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
	return `${f(ctx.value.start)} – ${f(ctx.value.end)}`;
});
const show = (key: string) => !k.value[key]?.hidden;
const kp = (key: string) => ({ value: k.value[key]?.value, restricted: !!k.value[key]?.restricted, delta: k.value[key]?.delta, href: k.value[key]?.route || undefined });
function refreshAll() {
	kpis.load(true);
	pending.load(true);
	section.load(true);
}
</script>

<template>
	<div class="mx-auto w-full max-w-[1480px] px-4 pb-10 pt-6 sm:px-6">
		<div class="mb-5 flex flex-col gap-4 2xl:flex-row 2xl:items-end 2xl:justify-between">
			<div class="min-w-0">
				<p class="mb-1 text-[12.5px] font-medium text-nxg-text-2">Good to see you{{ firstName ? `, ${firstName}` : "" }}</p>
				<h1 class="text-[24px] font-semibold leading-8 tracking-[-0.02em] sm:text-[28px] sm:leading-9">{{ center.title }}</h1>
				<p class="mt-1 text-[14px] text-nxg-text-2">{{ center.subtitle }}</p>
			</div>
			<div class="flex flex-wrap items-center gap-2 text-[12.5px]">
				<span v-if="team" class="inline-flex items-center gap-1.5 rounded-nxg border border-nxg-border bg-nxg-surface px-2.5 py-1.5"><Icon name="users-round" :size="13" class="text-nxg-text-2" /><span class="font-medium">My team</span><span v-if="ctx?.team_size != null" class="text-nxg-text-3">· {{ ctx.team_size }} direct report{{ ctx.team_size === 1 ? "" : "s" }}</span></span>
				<span v-else-if="ctx?.company" class="inline-flex items-center gap-1.5 rounded-nxg border border-nxg-border bg-nxg-surface px-2.5 py-1.5"><Icon name="building-2" :size="13" class="text-nxg-text-2" /><span class="font-medium">{{ ctx.company }}</span></span>
				<span v-if="ctx" class="inline-flex items-center gap-1.5 rounded-nxg border border-nxg-border bg-nxg-surface px-2.5 py-1.5"><Icon name="calendar-range" :size="13" class="text-nxg-text-2" />{{ periodLabel }}</span>
				<span v-if="center.access === 'limited'" class="inline-flex items-center gap-1.5 rounded-nxg border border-nxg-border bg-nxg-surface px-2.5 py-1.5 text-nxg-text-2"><Icon name="lock" :size="13" />Payroll is restricted for your role</span>
				<button class="nxg-btn nxg-btn-secondary" :disabled="anyLoading" aria-label="Refresh all panels" @click="refreshAll"><Icon name="refresh-cw" :size="14" :class="anyLoading && 'animate-spin'" /><span class="hidden sm:inline">Refresh</span></button>
			</div>
		</div>

		<section aria-label="Key figures" class="mb-4">
			<div v-if="kpis.state.error" class="nxg-panel mb-3 flex items-center justify-between gap-3 px-4 py-3 text-[13px]">
				<span class="flex items-center gap-2 text-nxg-danger"><Icon name="circle-alert" :size="15" />Key figures couldn't load: {{ kpis.state.error }}</span>
				<button class="nxg-btn nxg-btn-secondary h-7" @click="kpis.load(true)">Retry</button>
			</div>
			<div class="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
				<NxgKpi v-if="show('total_employees')" label="Total employees" icon="users" :loading="loading" v-bind="kp('total_employees')" hint="Employee records of every status" />
				<NxgKpi v-if="show('active_employees')" :label="team ? 'Team members' : 'Active employees'" icon="user-round" :loading="loading" v-bind="kp('active_employees')" hint="Employees with status Active" />
				<NxgKpi v-if="show('new_joiners')" label="New joiners" icon="user-plus" :loading="loading" v-bind="kp('new_joiners')" delta-label="vs prev. period" hint="Date of joining within the period" />
				<NxgKpi v-if="show('on_leave_today')" label="On leave today" icon="plane" :loading="loading" v-bind="kp('on_leave_today')" hint="Approved leave covering today" />
				<NxgKpi v-if="show('present_today')" label="Present today" icon="calendar-check" :loading="loading" v-bind="kp('present_today')" hint="Submitted attendance today: Present or Work From Home" />
				<NxgKpi v-if="show('absent_today')" label="Absent today" icon="circle-x" :loading="loading" v-bind="kp('absent_today')" invert hint="Submitted attendance today marked Absent" />
				<NxgKpi v-if="show('attendance_rate')" label="Attendance rate" icon="activity" :loading="loading" v-bind="kp('attendance_rate')" suffix="%" delta-label="pts vs prev. period" hint="Present ÷ (Present + Absent) over the period" />
				<NxgKpi v-if="show('pending_leave')" label="Pending leave" icon="clock" :loading="loading" v-bind="kp('pending_leave')" hint="Leave applications still Open" />
				<NxgKpi v-if="show('open_positions')" label="Open positions" icon="briefcase" :loading="loading" v-bind="kp('open_positions')" :secondary="k.open_positions?.secondary ? `${k.open_positions.secondary} job openings` : null" hint="Planned vacancies on open job openings" />
				<NxgKpi v-if="show('pending_approvals')" label="Pending HR approvals" icon="stamp" :loading="loading" v-bind="kp('pending_approvals')" href="/thinknxg/hr/approvals" hint="Requests where you are the approver" />
			</div>
		</section>

		<div class="grid grid-cols-1 gap-4 xl:grid-cols-3">
			<section class="nxg-panel min-w-0 px-4 pb-4 pt-3 xl:col-span-2" aria-label="Workforce intelligence">
				<NxgTabs :tabs="sections" :model-value="tab" @update:model-value="setTab" />
				<div class="pt-4">
					<div v-if="section.state.error" class="flex items-center justify-between gap-3 py-4 text-[13px]">
						<span class="flex items-center gap-2 text-nxg-danger"><Icon name="circle-alert" :size="15" />{{ section.state.error }}</span>
						<button class="nxg-btn nxg-btn-secondary h-7" @click="section.load(true)">Retry</button>
					</div>
					<div v-else-if="!section.state.data || shownTab === null" class="space-y-3"><div class="nxg-skeleton h-40" /><div class="nxg-skeleton h-24" /></div>
					<HrSection v-else :section="shownTab" :data="section.state.data" :class="(section.state.loading || shownTab !== tab) && 'opacity-60'" />
				</div>
			</section>

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
				<NxgPanel v-if="center.quick_create.length" title="Create">
					<div class="flex flex-wrap gap-2">
						<a v-for="q in center.quick_create" :key="q.doctype" :href="q.route" class="nxg-btn nxg-btn-secondary h-8"><Icon :name="q.icon" :size="14" />{{ q.doctype }}</a>
					</div>
				</NxgPanel>
			</div>
		</div>
	</div>
</template>
