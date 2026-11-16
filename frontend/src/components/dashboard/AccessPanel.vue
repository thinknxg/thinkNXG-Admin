<script setup lang="ts">
import { computed } from "vue";
import NxgPanel from "@/components/ui/NxgPanel.vue";
import BarList from "@/components/ui/BarList.vue";
import type { PanelState } from "@/data/api";
import { fmtNumber, timeAgo } from "@/composables/format";

const props = defineProps<{ state: PanelState<any> }>();
defineEmits<{ retry: [] }>();
const rows = computed(() => {
	const d = props.state.data || {};
	return [
		{ label: "Active users", value: d.active, href: "/desk/user?enabled=1&user_type=System%20User" },
		{ label: "Inactive (disabled)", value: d.disabled, href: "/desk/user?enabled=0" },
		{ label: "Dormant 90+ days", value: d.dormant_90d, href: "/desk/user?enabled=1" },
		{ label: "Never signed in", value: d.never_logged_in, href: "/desk/user?enabled=1" },
		{ label: "Pending invitations", value: d.pending_invitations, href: "/desk/user-invitation?status=Pending" },
		{ label: "Failed sign-ins (24 h)", value: d.failed_logins_24h, href: "/desk/activity-log?operation=Login&status=Failed", hint: "Lock state is held only in cache by the framework, so failed sign-ins are shown instead of a locked-user count." },
	];
});
const roles = computed(() => (props.state.data?.role_distribution || []).map((r: any) => ({ label: r.role, value: r.users, href: `/desk/role/${encodeURIComponent(r.role)}` })));
</script>

<template>
	<NxgPanel title="Users & access" :subtitle="state.data?.total_roles ? `${state.data.total_roles} roles defined` : 'Accounts, roles, permissions'" :loading="state.loading && !state.data" :error="state.error" :href="$href('/desk/user')" href-label="Users" :skeleton-rows="7" @retry="$emit('retry')">
		<ul class="mb-3 grid grid-cols-2 gap-x-4">
			<li v-for="r in rows" :key="r.label">
				<a :href="r.href" class="flex items-center justify-between gap-2 border-b border-nxg-border py-1.5 text-[12.5px] hover:text-nxg-text" :title="r.hint">
					<span class="truncate text-nxg-text-2">{{ r.label }}</span>
					<span class="nxg-tnum font-semibold" :class="r.value === null || r.value === undefined ? 'font-normal text-nxg-text-3' : ''">{{ r.value === null || r.value === undefined ? "n/a" : fmtNumber(r.value) }}</span>
				</a>
			</li>
		</ul>
		<div v-if="roles.length" class="mb-3">
			<div class="mb-1.5 nxg-micro">Role distribution · users per role</div>
			<BarList :items="roles" unit="users" />
		</div>
		<div>
			<div class="mb-1 nxg-micro">Recent permission changes</div>
			<p v-if="!state.data?.recent_permission_changes?.length" class="py-2 text-[12.5px] text-nxg-text-2">No permission changes in this period.</p>
			<ul v-else class="divide-y divide-nxg-border">
				<li v-for="c in state.data.recent_permission_changes" :key="c.id" class="py-1.5 text-[12.5px]">
					<a :href="c.route" class="block hover:underline"><span class="font-medium">{{ c.actor_name }}</span> <span class="text-nxg-text-2">{{ c.action.charAt(0).toLowerCase() + c.action.slice(1) }}</span> <span class="font-medium">{{ c.docname }}</span></a>
					<span class="text-[11.5px] text-nxg-text-3">{{ c.doctype }} · {{ timeAgo(c.timestamp) }}</span>
				</li>
			</ul>
		</div>
	</NxgPanel>
</template>
