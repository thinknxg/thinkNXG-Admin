<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { call } from "frappe-ui";
import PageHeader from "@/components/ui/PageHeader.vue";
import DataTable from "@/components/ui/DataTable.vue";
import NxgPagination from "@/components/ui/NxgPagination.vue";
import NxgAvatar from "@/components/ui/NxgAvatar.vue";
import NxgStatus from "@/components/ui/NxgStatus.vue";
import NxgMenu from "@/components/ui/NxgMenu.vue";
import MenuItem from "@/components/ui/MenuItem.vue";
import NxgDialog from "@/components/ui/NxgDialog.vue";
import NxgMultiSelect from "@/components/ui/NxgMultiSelect.vue";
import Icon from "@/components/ui/Icon.vue";
import UserDetail from "@/components/users/UserDetail.vue";
import { downloadCsv, errorMessage, runAction } from "@/data/api";
import { confirmAction } from "@/composables/useConfirm";
import { readPref, writePref } from "@/composables/storage";
import { timeAgo } from "@/composables/format";
import { boot } from "@/data/boot";

const API = "thinknxg_admin.api.users.";
const route = useRoute();
const router = useRouter();

// Saved filters persist per user in this browser
const f = reactive(readPref("users-filters", { search: "", status: "", user_type: "System User", role: "", company: "", sort: "full_name", order: "asc" as "asc" | "desc" }));
const start = ref(0);
const pageLength = 25;
const data = ref<{ rows: any[]; total: number } | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);
const selected = ref<string[]>([]);
const options = ref<any>(null);
const openUser = ref<string | null>((route.query.open as string) || (route.query.user as string) || null);

let debounce: number | undefined;
async function load() {
	loading.value = true;
	error.value = null;
	try {
		data.value = await call(API + "list_users", { ...f, start: start.value, page_length: pageLength });
	} catch (e) {
		error.value = errorMessage(e);
	} finally {
		loading.value = false;
	}
}
watch(() => ({ ...f }), (v) => {
	writePref("users-filters", v);
	start.value = 0;
	window.clearTimeout(debounce);
	debounce = window.setTimeout(load, 250);
}, { deep: true });
watch(start, load);
watch(openUser, (u) => router.replace({ query: u ? { user: u } : {} }));
onMounted(async () => {
	load();
	try {
		options.value = await call(API + "get_form_options");
	} catch {
		/* options are only needed for editing */
	}
});

const columns = [
	{ key: "full_name", label: "User", sortable: true },
	{ key: "roles", label: "Roles" },
	{ key: "companies", label: "Organization" },
	{ key: "default_workspace", label: "Workspace" },
	{ key: "enabled", label: "Status", sortable: true },
	{ key: "last_login", label: "Last sign-in", sortable: true },
];
function onSort(key: string) {
	if (f.sort === key) f.order = f.order === "asc" ? "desc" : "asc";
	else Object.assign(f, { sort: key, order: key === "last_login" ? "desc" : "asc" });
}
function statusOf(r: any) {
	if (!r.enabled) return { s: "unknown", l: "Disabled" };
	if (!r.last_login) return { s: "info", l: "Never signed in" };
	return { s: "ok", l: "Active" };
}
const statusFilters = ["Active", "Disabled", "Never signed in", "Dormant"];
const activeFilterCount = computed(() => [f.status, f.role, f.company, f.user_type !== "System User" ? f.user_type : ""].filter(Boolean).length);
function clearFilters() {
	Object.assign(f, { search: "", status: "", user_type: "System User", role: "", company: "" });
}

// Bulk actions
const bulkRole = reactive({ open: false, action: "add_role" as "add_role" | "remove_role", role: "" });
async function bulk(action: string, role?: string) {
	const n = selected.value.length;
	const labels: Record<string, string> = { enable: "Enable", disable: "Disable", add_role: `Add role ${role}`, remove_role: `Remove role ${role}` };
	const ok = await confirmAction({
		title: `${labels[action]} for ${n} user${n === 1 ? "" : "s"}?`,
		message: action === "disable" ? "They will be unable to sign in until re-enabled." : undefined,
		confirmLabel: labels[action],
		danger: action === "disable" || action === "remove_role",
		typeToConfirm: n >= 10 && (action === "disable" || action === "remove_role") ? String(n) : "",
	});
	if (!ok) return;
	const res = await runAction<{ updated: number }>(API + "bulk_update", { names: selected.value, action, role }, `Updated ${n} user${n === 1 ? "" : "s"}`);
	if (res) {
		selected.value = [];
		bulkRole.open = false;
		load();
	}
}

async function exportCsv() {
	const rows: any[] | undefined = await runAction(API + "export_users", { ...f });
	if (!rows) return;
	downloadCsv(`users-${new Date().toISOString().slice(0, 10)}.csv`, ["User", "Full name", "Email", "Status", "User type", "Roles", "Role profiles", "Companies", "Default workspace", "Last sign-in"],
		rows.map((r) => [r.name, r.full_name, r.email, r.enabled ? "Enabled" : "Disabled", r.user_type, r.roles.join("; "), r.role_profiles.join("; "), r.companies.join("; "), r.default_workspace, r.last_login]));
}

// Create user
const create = reactive({ open: false, email: "", first_name: "", last_name: "", user_type: "System User", roles: [] as string[], role_profiles: [] as string[], send_welcome_email: true, saving: false });
async function createUser() {
	create.saving = true;
	const name = await runAction<string>(API + "create_user", { ...create, send_welcome_email: create.send_welcome_email ? 1 : 0 }, "User created");
	create.saving = false;
	if (name) {
		Object.assign(create, { open: false, email: "", first_name: "", last_name: "", roles: [], role_profiles: [] });
		load();
		openUser.value = name;
	}
}
const roleNames = computed(() => (options.value?.roles || []).map((r: any) => r.name));
const companies = computed(() => boot.data?.companies.map((c) => c.name) || []);
</script>

<template>
	<div class="mx-auto w-full max-w-[1480px] px-4 pb-10 pt-6 sm:px-6">
		<PageHeader title="Users" description="Everyone with an account on this site, their roles, organization and sign-in activity.">
			<RouterLink to="/users/invitations" class="nxg-btn nxg-btn-secondary"><Icon name="inbox" :size="14" />Invitations</RouterLink>
			<button class="nxg-btn nxg-btn-secondary" @click="exportCsv"><Icon name="file-text" :size="14" />Export</button>
			<button class="nxg-btn nxg-btn-primary" @click="create.open = true"><Icon name="plus" :size="14" />New user</button>
		</PageHeader>

		<div class="nxg-panel">
			<!-- Toolbar -->
			<div class="flex flex-wrap items-center gap-2 border-b border-nxg-border p-3">
				<div class="relative min-w-[220px] flex-1 sm:max-w-xs">
					<Icon name="search" :size="15" class="pointer-events-none absolute left-2.5 top-2 text-nxg-text-3" />
					<input v-model="f.search" class="nxg-input pl-8" placeholder="Search name or email" aria-label="Search users" />
				</div>
				<select v-model="f.status" class="nxg-input w-auto" aria-label="Status"><option value="">Any status</option><option v-for="s in statusFilters" :key="s">{{ s }}</option></select>
				<select v-model="f.user_type" class="nxg-input w-auto" aria-label="User type"><option value="">All user types</option><option>System User</option><option>Website User</option></select>
				<select v-model="f.role" class="nxg-input w-auto max-w-[200px]" aria-label="Role"><option value="">Any role</option><option v-for="r in roleNames" :key="r">{{ r }}</option></select>
				<select v-if="companies.length" v-model="f.company" class="nxg-input w-auto max-w-[200px]" aria-label="Company"><option value="">Any company</option><option v-for="c in companies" :key="c">{{ c }}</option></select>
				<button v-if="activeFilterCount || f.search" class="nxg-btn nxg-btn-ghost h-8" @click="clearFilters">Clear</button>
				<button class="nxg-icon-btn ml-auto" aria-label="Reload" @click="load"><Icon name="refresh-cw" :size="15" :class="loading && 'animate-spin'" /></button>
			</div>

			<!-- Bulk bar -->
			<div v-if="selected.length" class="flex flex-wrap items-center gap-2 border-b border-nxg-border bg-nxg-surface-2/60 px-3 py-2 text-[13px]">
				<span class="font-medium">{{ selected.length }} selected</span>
				<button class="nxg-btn nxg-btn-secondary h-7" @click="bulk('enable')">Enable</button>
				<button class="nxg-btn nxg-btn-secondary h-7" @click="bulk('disable')">Disable</button>
				<button class="nxg-btn nxg-btn-secondary h-7" @click="Object.assign(bulkRole, { open: true, action: 'add_role', role: '' })">Add role</button>
				<button class="nxg-btn nxg-btn-secondary h-7" @click="Object.assign(bulkRole, { open: true, action: 'remove_role', role: '' })">Remove role</button>
				<button class="nxg-btn nxg-btn-ghost h-7 ml-auto" @click="selected = []">Clear selection</button>
			</div>

			<div v-if="error" class="flex items-center justify-between gap-3 p-4 text-[13px]"><span class="text-nxg-danger">{{ error }}</span><button class="nxg-btn nxg-btn-secondary h-7" @click="load">Retry</button></div>
			<DataTable v-else v-model:selected="selected" :columns="columns" :rows="data?.rows || []" :loading="loading" selectable clickable :sort="f.sort" :order="f.order" @sort="onSort" @row-click="(r) => (openUser = r.name)">
				<template #cell-full_name="{ row }">
					<span class="flex items-center gap-2.5">
						<NxgAvatar :name="row.full_name" :image="row.user_image" :size="28" />
						<span class="min-w-0"><span class="block max-w-[220px] truncate font-medium">{{ row.full_name || row.name }}</span><span class="block max-w-[220px] truncate text-[12px] text-nxg-text-2">{{ row.email || row.name }}</span></span>
					</span>
				</template>
				<template #cell-roles="{ row }">
					<span class="flex max-w-[260px] flex-wrap gap-1">
						<span v-for="r in row.roles.slice(0, 3)" :key="r" class="nxg-chip">{{ r }}</span>
						<span v-if="row.roles.length > 3" class="nxg-chip" :title="row.roles.slice(3).join(', ')">+{{ row.roles.length - 3 }}</span>
						<span v-if="!row.roles.length" class="text-nxg-text-3">—</span>
					</span>
				</template>
				<template #cell-companies="{ row }"><span class="block max-w-[180px] truncate" :class="!row.companies.length && 'text-nxg-text-3'">{{ row.companies.join(", ") || "All" }}</span></template>
				<template #cell-default_workspace="{ row }"><span class="block max-w-[140px] truncate" :class="!row.default_workspace && 'text-nxg-text-3'">{{ row.default_workspace || "—" }}</span></template>
				<template #cell-enabled="{ row }"><NxgStatus :status="statusOf(row).s" :label="statusOf(row).l" /></template>
				<template #cell-last_login="{ row }"><span class="whitespace-nowrap text-nxg-text-2">{{ row.last_login ? timeAgo(row.last_login) : "Never" }}</span></template>
			</DataTable>
			<NxgPagination v-if="data" :start="start" :page-length="pageLength" :total="data.total" class="border-t border-nxg-border" @change="(s) => (start = s)" />
		</div>

		<UserDetail :name="openUser" :options="options" @close="openUser = null" @changed="load" />

		<NxgDialog :open="bulkRole.open" :title="bulkRole.action === 'add_role' ? 'Add a role' : 'Remove a role'" :description="`Applies to ${selected.length} selected user${selected.length === 1 ? '' : 's'}.`" @close="bulkRole.open = false">
			<select v-model="bulkRole.role" class="nxg-input"><option value="" disabled>Choose a role</option><option v-for="r in roleNames" :key="r">{{ r }}</option></select>
			<template #footer>
				<button class="nxg-btn nxg-btn-secondary" @click="bulkRole.open = false">Cancel</button>
				<button class="nxg-btn nxg-btn-primary" :disabled="!bulkRole.role" @click="bulk(bulkRole.action, bulkRole.role)">Continue</button>
			</template>
		</NxgDialog>

		<NxgDialog :open="create.open" title="New user" description="Creates the account now. To let someone set up their own account, send an invitation instead." width="max-w-[560px]" @close="create.open = false">
			<div class="grid grid-cols-1 gap-3 pb-2 sm:grid-cols-2">
				<div class="sm:col-span-2"><label class="nxg-label">Email</label><input v-model="create.email" type="email" class="nxg-input" autocomplete="off" /></div>
				<div><label class="nxg-label">First name</label><input v-model="create.first_name" class="nxg-input" /></div>
				<div><label class="nxg-label">Last name</label><input v-model="create.last_name" class="nxg-input" /></div>
				<div class="sm:col-span-2"><label class="nxg-label">User type</label><select v-model="create.user_type" class="nxg-input"><option>System User</option><option>Website User</option></select></div>
				<div class="sm:col-span-2"><label class="nxg-label">Role profiles</label><NxgMultiSelect v-model="create.role_profiles" :options="options?.role_profiles || []" placeholder="Add profile" /></div>
				<div class="sm:col-span-2"><label class="nxg-label">Roles</label><NxgMultiSelect v-model="create.roles" :options="roleNames" placeholder="Add role" /></div>
				<label class="flex items-center gap-2 text-[13px] sm:col-span-2"><input v-model="create.send_welcome_email" type="checkbox" class="rounded border-nxg-border-strong text-nxg-espresso focus:ring-0" />Send welcome email with a link to set a password</label>
			</div>
			<template #footer>
				<button class="nxg-btn nxg-btn-secondary" @click="create.open = false">Cancel</button>
				<button class="nxg-btn nxg-btn-primary" :disabled="!create.email || !create.first_name || create.saving" @click="createUser">{{ create.saving ? "Creating…" : "Create user" }}</button>
			</template>
		</NxgDialog>
	</div>
</template>
