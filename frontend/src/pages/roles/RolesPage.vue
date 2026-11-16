<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { call } from "frappe-ui";
import PageHeader from "@/components/ui/PageHeader.vue";
import DataTable from "@/components/ui/DataTable.vue";
import NxgDrawer from "@/components/ui/NxgDrawer.vue";
import NxgDialog from "@/components/ui/NxgDialog.vue";
import NxgTabs from "@/components/ui/NxgTabs.vue";
import NxgStatus from "@/components/ui/NxgStatus.vue";
import NxgSwitch from "@/components/ui/NxgSwitch.vue";
import NxgAvatar from "@/components/ui/NxgAvatar.vue";
import NxgMultiSelect from "@/components/ui/NxgMultiSelect.vue";
import Icon from "@/components/ui/Icon.vue";
import { errorMessage, runAction } from "@/data/api";
import { confirmAction } from "@/composables/useConfirm";
import { timeAgo } from "@/composables/format";

const API = "thinknxg_admin.api.roles.";
const route = useRoute();
const router = useRouter();
const roles = ref<any[] | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);
const search = ref("");
const show = ref<"all" | "custom" | "standard" | "disabled">("all");

async function load() {
	loading.value = true;
	error.value = null;
	try {
		roles.value = await call(API + "list_roles", { include_disabled: 1 });
	} catch (e) {
		error.value = errorMessage(e);
	} finally {
		loading.value = false;
	}
}
onMounted(load);
const visible = computed(() => (roles.value || []).filter((r) => {
	if (search.value && !r.name.toLowerCase().includes(search.value.toLowerCase())) return false;
	if (show.value === "custom") return r.is_custom;
	if (show.value === "standard") return !r.is_custom;
	if (show.value === "disabled") return r.disabled;
	return true;
}));

// Detail
const open = ref<string | null>((route.query.open as string) || (route.query.role as string) || null);
const detail = ref<any>(null);
const dLoading = ref(false);
const tab = ref("users");
const settings = reactive({ desk_access: true, disabled: false, two_factor_auth: false, home_page: "" });
const addUsers = ref<string[]>([]);
const userOptions = ref<string[]>([]);
watch(open, async (name) => {
	router.replace({ query: name ? { role: name } : {} });
	detail.value = null;
	tab.value = "users";
	addUsers.value = [];
	if (!name) return;
	dLoading.value = true;
	try {
		detail.value = await call(API + "get_role", { name });
		syncSettings();
		if (!userOptions.value.length) {
			const res: any = await call("thinknxg_admin.api.users.list_users", { status: "Active", user_type: "", page_length: 200 });
			userOptions.value = res.rows.map((r: any) => r.name);
		}
	} catch (e) {
		detail.value = { error: errorMessage(e) };
	} finally {
		dLoading.value = false;
	}
}, { immediate: true });
function syncSettings() {
	const r = detail.value.role;
	Object.assign(settings, { desk_access: !!r.desk_access, disabled: !!r.disabled, two_factor_auth: !!r.two_factor_auth, home_page: r.home_page || "" });
}
async function saveSettings() {
	const res = await runAction(API + "update_role", { name: open.value, values: { ...settings, desk_access: settings.desk_access ? 1 : 0, disabled: settings.disabled ? 1 : 0, two_factor_auth: settings.two_factor_auth ? 1 : 0 } }, "Role updated");
	if (res) {
		detail.value = res;
		syncSettings();
		load();
	}
}
async function addSelectedUsers() {
	const res = await runAction(API + "set_role_users", { role: open.value, add: addUsers.value }, `Added ${addUsers.value.length} user(s)`);
	if (res) {
		detail.value = res;
		addUsers.value = [];
		load();
	}
}
async function removeUser(u: any) {
	if (!(await confirmAction({ title: `Remove ${open.value} from ${u.full_name}?`, confirmLabel: "Remove role", danger: true }))) return;
	const res = await runAction(API + "set_role_users", { role: open.value, remove: [u.name] }, "Role removed");
	if (res) {
		detail.value = res;
		load();
	}
}
const PT = ["read", "write", "create", "delete", "submit", "cancel", "report", "export", "import", "share", "print", "email"];
const permSearch = ref("");
const permRows = computed(() => (detail.value?.permissions || []).filter((p: any) => !permSearch.value || p.doctype.toLowerCase().includes(permSearch.value.toLowerCase())));

// Create / duplicate
const create = reactive({ open: false, role_name: "", desk_access: true, two_factor_auth: false });
async function createRole() {
	const name = await runAction<string>(API + "create_role", { role_name: create.role_name, desk_access: create.desk_access ? 1 : 0, two_factor_auth: create.two_factor_auth ? 1 : 0 }, "Role created");
	if (name) {
		Object.assign(create, { open: false, role_name: "" });
		await load();
		open.value = name;
	}
}
const dup = reactive({ open: false, source: "", new_name: "", copy_users: false });
function startDuplicate(src: string) {
	Object.assign(dup, { open: true, source: src, new_name: `${src} (Copy)`, copy_users: false });
}
async function duplicate() {
	const res = await runAction<any>(API + "duplicate_role", { source: dup.source, new_name: dup.new_name, copy_users: dup.copy_users ? 1 : 0 });
	if (res) {
		dup.open = false;
		await load();
		open.value = res.name;
		const { toast } = await import("frappe-ui");
		toast.success(`Created ${res.name} with ${res.rules} permission rule${res.rules === 1 ? "" : "s"}${res.users ? ` and ${res.users} users` : ""}`);
	}
}
</script>

<template>
	<div class="mx-auto w-full max-w-[1480px] px-4 pb-10 pt-6 sm:px-6">
		<PageHeader title="Roles" description="What each role can do, who holds it and where it is used. Permission rules are edited in the matrix.">
			<RouterLink to="/roles/matrix" class="nxg-btn nxg-btn-secondary"><Icon name="layout-grid" :size="14" />Permission matrix</RouterLink>
			<button class="nxg-btn nxg-btn-primary" @click="create.open = true"><Icon name="plus" :size="14" />New role</button>
		</PageHeader>
		<div class="nxg-panel">
			<div class="flex flex-wrap items-center gap-2 border-b border-nxg-border p-3">
				<div class="relative min-w-[220px] flex-1 sm:max-w-xs"><Icon name="search" :size="15" class="pointer-events-none absolute left-2.5 top-2 text-nxg-text-3" /><input v-model="search" class="nxg-input pl-8" placeholder="Search roles" aria-label="Search roles" /></div>
				<div class="inline-flex rounded-nxg border border-nxg-border p-0.5" role="group" aria-label="Filter roles">
					<button v-for="o in ['all', 'custom', 'standard', 'disabled']" :key="o" class="h-7 rounded-[6px] px-2.5 text-[12.5px] font-medium capitalize" :class="show === o ? 'bg-nxg-primary text-nxg-primary-fg' : 'text-nxg-text-2 hover:text-nxg-text'" @click="show = o as any">{{ o }}</button>
				</div>
				<span class="nxg-tnum ml-auto text-[12.5px] text-nxg-text-2">{{ visible.length }} roles</span>
			</div>
			<div v-if="error" class="p-4 text-[13px] text-nxg-danger">{{ error }}</div>
			<DataTable v-else :columns="[{ key: 'name', label: 'Role' }, { key: 'users', label: 'Users', align: 'right' }, { key: 'doctypes', label: 'DocTypes', align: 'right' }, { key: 'workspaces', label: 'Workspaces', align: 'right' }, { key: 'desk_access', label: 'Desk access' }, { key: 'state', label: 'Status' }, { key: 'actions', label: '', align: 'right' }]" :rows="visible" :loading="loading" clickable @row-click="(r) => (open = r.name)">
				<template #cell-name="{ row }"><span class="flex items-center gap-2"><span class="font-medium">{{ row.name }}</span><span v-if="row.is_custom" class="nxg-chip">Custom</span><span v-if="row.two_factor_auth" class="nxg-chip" title="Two-factor authentication required">2FA</span></span></template>
				<template #cell-users="{ row }"><span class="nxg-tnum">{{ row.users }}</span></template>
				<template #cell-doctypes="{ row }"><span class="nxg-tnum">{{ row.doctypes }}</span></template>
				<template #cell-workspaces="{ row }"><span class="nxg-tnum">{{ row.workspaces }}</span></template>
				<template #cell-desk_access="{ row }"><span :class="!row.desk_access && 'text-nxg-text-3'">{{ row.desk_access ? "Yes" : "No (portal)" }}</span></template>
				<template #cell-state="{ row }"><NxgStatus :status="row.disabled ? 'unknown' : 'ok'" :label="row.disabled ? 'Disabled' : 'Active'" /></template>
				<template #cell-actions="{ row }"><button class="nxg-btn nxg-btn-ghost h-7" @click.stop="startDuplicate(row.name)">Duplicate</button></template>
			</DataTable>
		</div>

		<NxgDrawer :open="!!open" :title="open || ''" :subtitle="detail?.role ? `${detail.users.length} user${detail.users.length === 1 ? '' : 's'} · ${detail.permissions.length} DocType${detail.permissions.length === 1 ? '' : 's'}` : ''" width="max-w-[720px]" @close="open = null">
			<div v-if="dLoading" class="space-y-3 p-5"><div v-for="i in 6" :key="i" class="nxg-skeleton h-6" /></div>
			<div v-else-if="detail?.error" class="p-5 text-[13px] text-nxg-danger">{{ detail.error }}</div>
			<template v-else-if="detail">
				<div class="px-5 pt-3"><NxgTabs v-model="tab" :tabs="[{ key: 'users', label: 'Users', count: detail.users.length }, { key: 'perms', label: 'Permissions', count: detail.permissions.length }, { key: 'usage', label: 'Used in' }, { key: 'settings', label: 'Settings' }]" /></div>
				<div v-if="tab === 'users'" class="space-y-3 p-5">
					<div class="flex items-start gap-2"><NxgMultiSelect v-model="addUsers" :options="userOptions.filter((u) => !detail.users.some((x: any) => x.name === u))" placeholder="Choose users" class="flex-1" /><button class="nxg-btn nxg-btn-primary" :disabled="!addUsers.length" @click="addSelectedUsers">Add</button></div>
					<ul class="divide-y divide-nxg-border rounded-nxg border border-nxg-border">
						<li v-for="u in detail.users" :key="u.name" class="flex items-center gap-2.5 px-3 py-2 text-[13px]">
							<NxgAvatar :name="u.full_name" :image="u.user_image" :size="26" />
							<span class="min-w-0 flex-1"><RouterLink :to="{ path: '/users', query: { user: u.name } }" class="block truncate font-medium hover:underline">{{ u.full_name || u.name }}</RouterLink><span class="block truncate text-[12px] text-nxg-text-2">{{ u.name }} · {{ u.last_login ? `signed in ${timeAgo(u.last_login)}` : "never signed in" }}</span></span>
							<NxgStatus v-if="!u.enabled" status="unknown" label="Disabled" />
							<button class="nxg-btn nxg-btn-ghost h-7" @click="removeUser(u)">Remove</button>
						</li>
						<li v-if="!detail.users.length" class="px-3 py-5 text-center text-[12.5px] text-nxg-text-2">No users hold this role.</li>
					</ul>
				</div>
				<div v-else-if="tab === 'perms'" class="p-5">
					<div class="mb-3 flex items-center gap-2"><input v-model="permSearch" class="nxg-input max-w-xs" placeholder="Filter DocTypes" /><RouterLink :to="{ path: '/roles/matrix', query: { role: open } }" class="nxg-btn nxg-btn-secondary ml-auto">Edit in matrix</RouterLink></div>
					<p class="mb-2 text-[12px] text-nxg-text-2">Level-0 rules this role grants. A dot means allowed.</p>
					<div class="-mx-5 overflow-x-auto">
						<table class="w-full min-w-[640px] text-[12.5px]">
							<thead><tr class="border-b border-nxg-border"><th class="px-5 py-1.5 text-left nxg-micro">DocType</th><th v-for="p in PT" :key="p" class="px-1 py-1.5 text-center nxg-micro" :title="p">{{ p.slice(0, 3) }}</th></tr></thead>
							<tbody class="divide-y divide-nxg-border">
								<tr v-for="r in permRows" :key="r.doctype">
									<td class="px-5 py-1.5"><span class="font-medium">{{ r.doctype }}</span> <span class="text-nxg-text-3">{{ r.module }}</span><span v-if="r.if_owner" class="nxg-chip ml-1" title="Only documents this user created">Own only</span></td>
									<td v-for="p in PT" :key="p" class="px-1 text-center"><span v-if="r[p]" class="inline-block h-2 w-2 rounded-full bg-[var(--nxg-chart-1)]" :aria-label="`${p} allowed`" /><span v-else class="sr-only">{{ p }} not allowed</span></td>
								</tr>
							</tbody>
						</table>
					</div>
				</div>
				<div v-else-if="tab === 'usage'" class="space-y-4 p-5 text-[13px]">
					<div><h3 class="mb-1.5 nxg-micro">Workspaces restricted to this role</h3><div class="flex flex-wrap gap-1.5"><span v-for="w in detail.workspaces" :key="w" class="nxg-chip">{{ w }}</span><span v-if="!detail.workspaces.length" class="text-nxg-text-2">None</span></div></div>
					<div><h3 class="mb-1.5 nxg-micro">Role profiles that include it</h3><div class="flex flex-wrap gap-1.5"><span v-for="p in detail.role_profiles" :key="p" class="nxg-chip">{{ p }}</span><span v-if="!detail.role_profiles.length" class="text-nxg-text-2">None</span></div></div>
				</div>
				<div v-else class="space-y-3 p-5">
					<div class="flex items-center justify-between rounded-nxg border border-nxg-border px-3 py-2.5"><div><div class="text-[13px] font-medium">Desk access</div><div class="text-[12px] text-nxg-text-2">Off for portal-only roles.</div></div><NxgSwitch v-model="settings.desk_access" label="Desk access" /></div>
					<div class="flex items-center justify-between rounded-nxg border border-nxg-border px-3 py-2.5"><div><div class="text-[13px] font-medium">Require two-factor authentication</div><div class="text-[12px] text-nxg-text-2">Applies when 2FA is enabled in System Settings.</div></div><NxgSwitch v-model="settings.two_factor_auth" label="Require 2FA" /></div>
					<div class="flex items-center justify-between rounded-nxg border border-nxg-border px-3 py-2.5"><div><div class="text-[13px] font-medium">Disabled</div><div class="text-[12px] text-nxg-text-2">A disabled role grants nothing, even to users who hold it.</div></div><NxgSwitch v-model="settings.disabled" label="Disabled" :disabled="open === 'System Manager'" /></div>
					<div><label class="nxg-label">Home page</label><input v-model="settings.home_page" class="nxg-input" placeholder="e.g. desk/home" /></div>
					<div class="flex justify-end gap-2"><button class="nxg-btn nxg-btn-ghost" @click="syncSettings">Discard</button><button class="nxg-btn nxg-btn-primary" @click="saveSettings">Save</button></div>
				</div>
			</template>
			<template v-if="detail?.role" #footer>
				<button class="nxg-btn nxg-btn-ghost mr-auto" @click="startDuplicate(open!)">Duplicate role</button>
				<a :href="`/thinknxg/admin/doc/role/${encodeURIComponent(open || '')}`" class="nxg-btn nxg-btn-ghost">Open full record<Icon name="chevron-right" :size="13" /></a>
			</template>
		</NxgDrawer>

		<NxgDialog :open="create.open" title="New role" @close="create.open = false">
			<div class="space-y-3 pb-2">
				<div><label class="nxg-label">Role name</label><input v-model="create.role_name" class="nxg-input" placeholder="e.g. Payroll Manager" /></div>
				<label class="flex items-center gap-2 text-[13px]"><input v-model="create.desk_access" type="checkbox" class="rounded border-nxg-border-strong text-nxg-espresso focus:ring-0" />Desk access</label>
				<label class="flex items-center gap-2 text-[13px]"><input v-model="create.two_factor_auth" type="checkbox" class="rounded border-nxg-border-strong text-nxg-espresso focus:ring-0" />Require two-factor authentication</label>
				<p class="text-[12px] text-nxg-text-2">A new role grants nothing until you add permission rules in the matrix, or duplicate an existing role instead.</p>
			</div>
			<template #footer><button class="nxg-btn nxg-btn-secondary" @click="create.open = false">Cancel</button><button class="nxg-btn nxg-btn-primary" :disabled="!create.role_name.trim()" @click="createRole">Create role</button></template>
		</NxgDialog>

		<NxgDialog :open="dup.open" :title="`Duplicate ${dup.source}`" description="Copies every DocType permission rule (all levels) to a new role." @close="dup.open = false">
			<div class="space-y-3 pb-2">
				<div><label class="nxg-label">New role name</label><input v-model="dup.new_name" class="nxg-input" /></div>
				<label class="flex items-center gap-2 text-[13px]"><input v-model="dup.copy_users" type="checkbox" class="rounded border-nxg-border-strong text-nxg-espresso focus:ring-0" />Also give it to everyone who holds {{ dup.source }}</label>
			</div>
			<template #footer><button class="nxg-btn nxg-btn-secondary" @click="dup.open = false">Cancel</button><button class="nxg-btn nxg-btn-primary" :disabled="!dup.new_name.trim()" @click="duplicate">Duplicate</button></template>
		</NxgDialog>
	</div>
</template>
