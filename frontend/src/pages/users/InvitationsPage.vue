<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { call } from "frappe-ui";
import PageHeader from "@/components/ui/PageHeader.vue";
import DataTable from "@/components/ui/DataTable.vue";
import NxgStatus from "@/components/ui/NxgStatus.vue";
import NxgTabs from "@/components/ui/NxgTabs.vue";
import NxgDialog from "@/components/ui/NxgDialog.vue";
import NxgMultiSelect from "@/components/ui/NxgMultiSelect.vue";
import Icon from "@/components/ui/Icon.vue";
import { errorMessage, runAction } from "@/data/api";
import { confirmAction } from "@/composables/useConfirm";
import { fmtDateTime, timeAgo } from "@/composables/format";

const API = "thinknxg_admin.api.users.";
const rows = ref<any[] | null>(null);
const unavailable = ref(false);
const loading = ref(false);
const error = ref<string | null>(null);
const status = ref("Pending");
const roles = ref<string[]>([]);

async function load() {
	loading.value = true;
	error.value = null;
	try {
		const res = (await call(API + "list_invitations", {})) as any[] | null;
		unavailable.value = res === null;
		rows.value = res || [];
	} catch (e) {
		error.value = errorMessage(e);
	} finally {
		loading.value = false;
	}
}
onMounted(async () => {
	load();
	try {
		roles.value = ((await call(API + "get_form_options")) as any).roles.map((r: any) => r.name);
	} catch {
		/* ignore */
	}
});
const counts = computed(() => {
	const c: Record<string, number> = {};
	for (const r of rows.value || []) c[r.status] = (c[r.status] || 0) + 1;
	return c;
});
const visible = computed(() => (rows.value || []).filter((r) => !status.value || r.status === status.value));
const tone: Record<string, string> = { Pending: "warning", Accepted: "success", Expired: "unknown", Cancelled: "unknown" };

const form = reactive({ open: false, emails: "", roles: [] as string[], sending: false, results: [] as any[] });
async function send() {
	form.sending = true;
	const emails = form.emails.split(/[\s,;]+/).filter(Boolean);
	const res = await runAction<any[]>(API + "invite_users", { emails, roles: form.roles, redirect_to_path: "/desk" });
	form.sending = false;
	if (res) {
		form.results = res;
		if (res.every((r) => r.ok)) {
			Object.assign(form, { open: false, emails: "", roles: [], results: [] });
		}
		load();
	}
}
async function cancel(r: any) {
	if (!(await confirmAction({ title: `Cancel the invitation to ${r.email}?`, message: "The link in their email will stop working.", confirmLabel: "Cancel invitation", danger: true }))) return;
	if (await runAction(API + "cancel_invitation", { name: r.name }, "Invitation cancelled")) load();
}
</script>

<template>
	<div class="mx-auto w-full max-w-[1200px] px-4 pb-10 pt-6 sm:px-6">
		<PageHeader title="Invitations" description="People invited by email to create their own account. Invitations use the framework's User Invitation flow.">
			<button class="nxg-btn nxg-btn-primary" :disabled="unavailable" @click="form.open = true"><Icon name="plus" :size="14" />Invite people</button>
		</PageHeader>
		<div v-if="unavailable" class="nxg-panel p-6 text-[13px] text-nxg-text-2">User Invitation is not available on this site.</div>
		<div v-else class="nxg-panel">
			<div class="px-3 pt-1"><NxgTabs v-model="status" :tabs="[{ key: 'Pending', label: 'Pending', count: counts.Pending || 0 }, { key: 'Accepted', label: 'Accepted', count: counts.Accepted || 0 }, { key: 'Expired', label: 'Expired', count: counts.Expired || 0 }, { key: 'Cancelled', label: 'Cancelled', count: counts.Cancelled || 0 }, { key: '', label: 'All' }]" /></div>
			<div v-if="error" class="p-4 text-[13px] text-nxg-danger">{{ error }}</div>
			<DataTable v-else :columns="[{ key: 'email', label: 'Email' }, { key: 'roles', label: 'Roles' }, { key: 'invited_by', label: 'Invited by' }, { key: 'creation', label: 'Sent' }, { key: 'status', label: 'Status' }, { key: 'actions', label: '', align: 'right' }]" :rows="visible" :loading="loading" empty-text="No invitations in this list">
				<template #cell-email="{ row }"><span class="font-medium">{{ row.email }}</span></template>
				<template #cell-roles="{ row }"><span class="flex flex-wrap gap-1"><span v-for="r in row.roles" :key="r" class="nxg-chip">{{ r }}</span><span v-if="!row.roles.length" class="text-nxg-text-3">—</span></span></template>
				<template #cell-creation="{ row }"><span class="text-nxg-text-2" :title="fmtDateTime(row.creation)">{{ timeAgo(row.creation) }}</span></template>
				<template #cell-status="{ row }"><NxgStatus :status="tone[row.status]" :label="row.status" /></template>
				<template #cell-actions="{ row }"><button v-if="row.status === 'Pending'" class="nxg-btn nxg-btn-ghost h-7" @click.stop="cancel(row)">Cancel</button></template>
			</DataTable>
		</div>

		<NxgDialog :open="form.open" title="Invite people" description="Each person gets an email with a link to create their account with these roles." width="max-w-[540px]" @close="form.open = false">
			<div class="space-y-3 pb-2">
				<div><label class="nxg-label">Email addresses</label><textarea v-model="form.emails" rows="3" class="nxg-input h-auto py-2" placeholder="name@company.com, another@company.com" /></div>
				<div><label class="nxg-label">Roles</label><NxgMultiSelect v-model="form.roles" :options="roles" placeholder="Add role" /></div>
				<ul v-if="form.results.length" class="space-y-1 text-[12.5px]">
					<li v-for="r in form.results" :key="r.email" class="flex items-start gap-2"><NxgStatus :status="r.ok ? 'success' : 'failed'" :label="r.ok ? 'Sent' : 'Failed'" /><span class="font-medium">{{ r.email }}</span><span v-if="!r.ok" class="text-nxg-text-2">{{ r.error }}</span></li>
				</ul>
			</div>
			<template #footer>
				<button class="nxg-btn nxg-btn-secondary" @click="form.open = false">Close</button>
				<button class="nxg-btn nxg-btn-primary" :disabled="!form.emails.trim() || form.sending" @click="send">{{ form.sending ? "Sending…" : "Send invitations" }}</button>
			</template>
		</NxgDialog>
	</div>
</template>
