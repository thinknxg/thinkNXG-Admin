<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import Icon from "@/components/ui/Icon.vue";
import NxgKpi from "@/components/ui/NxgKpi.vue";
import NxgStatus from "@/components/ui/NxgStatus.vue";
import NxgMenu from "@/components/ui/NxgMenu.vue";
import HealthPanel from "@/components/dashboard/HealthPanel.vue";
import ActivityPanel from "@/components/dashboard/ActivityPanel.vue";
import AccessPanel from "@/components/dashboard/AccessPanel.vue";
import OrgPanel from "@/components/dashboard/OrgPanel.vue";
import PendingPanel from "@/components/dashboard/PendingPanel.vue";
import AdminTimeline from "@/components/dashboard/AdminTimeline.vue";
import { usePanel } from "@/data/api";
import { boot } from "@/data/boot";
import { shell } from "@/data/shell";
import { readPref, writePref } from "@/composables/storage";

const API = "thinknxg_admin.api.";
const days = computed(() => shell.days);
const company = computed(() => shell.company);

const kpis = usePanel<any>(API + "dashboard.get_kpis", () => ({ days: days.value, company: company.value }));
const activity = usePanel<any>(API + "dashboard.get_activity", () => ({ days: days.value }));
const access = usePanel<any>(API + "dashboard.get_access_overview", () => ({ days: days.value }));
const org = usePanel<any>(API + "dashboard.get_organization_overview", () => ({ company: company.value }));
const pending = usePanel<any>(API + "dashboard.get_pending_actions");
const timeline = usePanel<any[]>(API + "dashboard.get_admin_timeline", () => ({ days: days.value, limit: 15 }));

// Health: also measure the browser round-trip of the call itself (honest API latency signal).
const health = usePanel<any>(API + "health.get_live_health");
const roundTrip = computed(() => health.state.ms);

function refreshAll() {
	[kpis, activity, access, org, pending, timeline, health].forEach((p) => p.load(true));
}

// Customize: per-user section visibility
const sectionDefs = [
	{ key: "kpis", label: "KPI overview" },
	{ key: "activity", label: "System activity" },
	{ key: "health", label: "System health" },
	{ key: "access", label: "Users & access" },
	{ key: "org", label: "Organization" },
	{ key: "pending", label: "Pending actions" },
	{ key: "timeline", label: "Administrative activity" },
];
const visible = reactive<Record<string, boolean>>(Object.assign(Object.fromEntries(sectionDefs.map((s) => [s.key, true])), readPref("cc-sections", {})));
watch(visible, (v) => writePref("cc-sections", { ...v }), { deep: true });

const k = computed(() => kpis.state.data || {});
const trend = computed(() => (k.value.login_series || []).map((p: any) => p.users));
const ranges = [7, 30, 90];
const firstName = computed(() => (boot.data?.user.full_name || "").split(" ")[0]);
const updated = computed(() => (kpis.state.loadedAt ? kpis.state.loadedAt.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" }) : null));
const anyLoading = computed(() => [kpis, activity, access, org, pending, timeline, health].some((p) => p.state.loading));
</script>

<template>
	<div class="mx-auto w-full max-w-[1480px] px-4 pb-10 pt-6 sm:px-6">
		<!-- Header -->
		<div class="mb-5 flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
			<div class="min-w-0">
				<p class="mb-1 text-[12.5px] font-medium text-nxg-text-2">Good to see you{{ firstName ? `, ${firstName}` : "" }}</p>
				<h1 class="text-[24px] font-semibold leading-8 tracking-[-0.02em] sm:text-[28px] sm:leading-9">Welcome to thinkNXG Command Center</h1>
				<p class="mt-1 text-[14px] text-nxg-text-2">Your centralized control center for enterprise operations.</p>
			</div>
			<div class="flex flex-wrap items-center gap-2">
				<a href="/thinknxg/system-health" class="mr-1 inline-flex items-center gap-2 rounded-nxg border border-nxg-border bg-nxg-surface px-2.5 py-1.5 text-[12.5px] hover:border-nxg-border-strong" :title="health.state.data?.summary">
					<span class="relative flex h-2 w-2">
						<span v-if="health.state.data?.status === 'ok'" class="absolute inline-flex h-full w-full animate-ping rounded-full bg-nxg-success opacity-40" />
						<span class="relative inline-flex h-2 w-2 rounded-full" :class="{ 'bg-nxg-success': health.state.data?.status === 'ok', 'bg-nxg-warning': ['warning', 'unknown'].includes(health.state.data?.status), 'bg-nxg-danger': health.state.data?.status === 'critical', 'bg-nxg-text-3': !health.state.data }" />
					</span>
					<span class="font-medium">{{ health.state.data?.summary || (health.state.error ? "Health check failed" : "Checking systems…") }}</span>
				</a>
				<div class="inline-flex rounded-nxg border border-nxg-border bg-nxg-surface p-0.5" role="group" aria-label="Date range">
					<button v-for="r in ranges" :key="r" class="h-7 rounded-[6px] px-2.5 text-[12.5px] font-medium transition-colors" :class="shell.days === r ? 'bg-nxg-primary text-nxg-primary-fg' : 'text-nxg-text-2 hover:text-nxg-text'" :aria-pressed="shell.days === r" @click="shell.days = r">{{ r }}d</button>
				</div>
				<NxgMenu v-if="boot.data?.companies.length" width="w-60" class="md:hidden">
					<template #trigger="{ toggle }"><button class="nxg-btn nxg-btn-secondary" @click="toggle"><Icon name="building-2" :size="14" />{{ shell.company || "All companies" }}</button></template>
					<button class="flex h-8 w-full items-center rounded-nxg-sm px-2 text-left text-[13px] hover:bg-nxg-surface-2" data-close @click="shell.company = null">All companies</button>
					<button v-for="c in boot.data?.companies" :key="c.name" class="flex h-8 w-full items-center rounded-nxg-sm px-2 text-left text-[13px] hover:bg-nxg-surface-2" data-close @click="shell.company = c.name">{{ c.name }}</button>
				</NxgMenu>
				<NxgMenu align="right" width="w-56">
					<template #trigger="{ toggle }"><button class="nxg-btn nxg-btn-secondary" @click="toggle"><Icon name="sliders-horizontal" :size="14" />Customize</button></template>
					<div class="px-2 pb-1 pt-1.5 nxg-micro">Show sections</div>
					<label v-for="s in sectionDefs" :key="s.key" class="flex h-8 cursor-pointer items-center gap-2 rounded-nxg-sm px-2 text-[13px] hover:bg-nxg-surface-2">
						<input v-model="visible[s.key]" type="checkbox" class="rounded-1 border-nxg-border-strong text-nxg-espresso focus:ring-0" />{{ s.label }}
					</label>
				</NxgMenu>
				<button class="nxg-btn nxg-btn-secondary" :disabled="anyLoading" aria-label="Refresh all panels" @click="refreshAll"><Icon name="refresh-cw" :size="14" :class="anyLoading && 'animate-spin'" /><span class="hidden sm:inline">Refresh</span></button>
			</div>
		</div>

		<!-- KPIs -->
		<section v-if="visible.kpis" aria-label="Key figures" class="mb-4">
			<div v-if="kpis.state.error" class="nxg-panel mb-3 flex items-center justify-between gap-3 px-4 py-3 text-[13px]">
				<span class="flex items-center gap-2 text-nxg-danger"><Icon name="circle-alert" :size="15" />Key figures couldn't load: {{ kpis.state.error }}</span>
				<button class="nxg-btn nxg-btn-secondary h-7" @click="kpis.load(true)">Retry</button>
			</div>
			<div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
				<NxgKpi label="Total users" icon="users" :loading="kpis.state.loading && !kpis.state.data" :value="k.total_users?.value" :delta="k.total_users?.delta" delta-label="new vs prev." :secondary="k.total_users?.secondary != null ? `${k.total_users.secondary} new` : null" :href="$href('/desk/user?enabled=1')" hint="Enabled System Users, excluding Administrator and Guest" />
				<NxgKpi label="Active users" icon="activity" :loading="kpis.state.loading && !kpis.state.data" :value="k.active_users?.value" :delta="k.active_users?.delta" delta-label="vs prev. period" :trend="trend" :href="$href('/desk/activity-log?operation=Login')" :hint="`Distinct people who signed in during the last ${shell.days} days`" />
				<NxgKpi label="Companies" icon="building-2" :loading="kpis.state.loading && !kpis.state.data" :value="k.companies?.value" :href="$href('/desk/company')" />
				<NxgKpi label="Active workspaces" icon="panels-top-left" :loading="kpis.state.loading && !kpis.state.data" :value="k.workspaces?.value" :href="$href('/desk/workspace')" hint="Public, not hidden" />
				<NxgKpi label="Installed apps" icon="blocks" :loading="kpis.state.loading && !kpis.state.data" :value="k.installed_apps?.value" :secondary="k.installed_apps?.items?.slice(0, 3).join(', ')" :href="$href('/desk/installed-applications')" />
				<NxgKpi label="Enabled modules" icon="layers" :loading="kpis.state.loading && !kpis.state.data" :value="k.modules?.value" secondary="across installed apps" :href="$href('/desk/module-def')" />
				<NxgKpi label="Pending approvals" icon="circle-check" :loading="kpis.state.loading && !kpis.state.data" :value="k.pending_approvals?.value" :secondary="k.pending_approvals?.secondary ? `${k.pending_approvals.secondary} older than ${shell.days}d` : null" :href="$href('/desk/workflow-action?status=Open')" hint="Open Workflow Actions" />
				<NxgKpi label="Background jobs" icon="list-checks" :loading="kpis.state.loading && !kpis.state.data" :value="k.background_jobs?.value" :secondary="k.background_jobs?.secondary != null ? `${k.background_jobs.secondary} failed` : null" :href="$href('/desk/rq-job')" hint="Queued + running jobs in RQ" />
			</div>
		</section>

		<!-- Activity + Health -->
		<div v-if="visible.activity || visible.health" class="mb-4 grid grid-cols-1 gap-4 xl:grid-cols-3">
			<ActivityPanel v-if="visible.activity" :class="visible.health ? 'xl:col-span-2' : 'xl:col-span-3'" :state="activity.state" :series="k.login_series" :series-loading="kpis.state.loading" :days="shell.days" @retry="activity.load(true)" />
			<HealthPanel v-if="visible.health" :class="!visible.activity && 'xl:col-span-3'" :state="health.state" :round-trip="roundTrip" @retry="health.load(true)" />
		</div>

		<!-- Access + Org + Pending -->
		<div v-if="visible.access || visible.org || visible.pending" class="mb-4 grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-3">
			<AccessPanel v-if="visible.access" :state="access.state" @retry="access.load(true)" />
			<OrgPanel v-if="visible.org" :state="org.state" :company="shell.company" @retry="org.load(true)" />
			<PendingPanel v-if="visible.pending" :state="pending.state" @retry="pending.load(true)" />
		</div>

		<AdminTimeline v-if="visible.timeline" :state="timeline.state" :days="shell.days" @retry="timeline.load(true)" />

		<p class="mt-6 text-center text-[12px] text-nxg-text-3">
			Figures come from this site's own records<span v-if="updated"> · updated {{ updated }}</span> · thinkNXG Admin {{ boot.data?.version }}
		</p>
	</div>
</template>
