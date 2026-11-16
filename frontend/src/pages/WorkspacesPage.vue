<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { call } from "frappe-ui";
import PageHeader from "@/components/ui/PageHeader.vue";
import NxgTabs from "@/components/ui/NxgTabs.vue";
import DataTable from "@/components/ui/DataTable.vue";
import NxgDialog from "@/components/ui/NxgDialog.vue";
import NxgSwitch from "@/components/ui/NxgSwitch.vue";
import NxgMultiSelect from "@/components/ui/NxgMultiSelect.vue";
import Icon from "@/components/ui/Icon.vue";
import SidebarBuilder from "@/components/workspaces/SidebarBuilder.vue";
import { errorMessage, runAction } from "@/data/api";
import { confirmAction } from "@/composables/useConfirm";

const API = "thinknxg_admin.api.workspaces.";
const data = ref<any>(null);
const loading = ref(false);
const error = ref<string | null>(null);
const tab = ref("pages");
const search = ref("");
const scope = ref<"public" | "private" | "all">("public");

async function load() {
	loading.value = true;
	error.value = null;
	try {
		data.value = await call(API + "get_overview");
	} catch (e) {
		error.value = errorMessage(e);
	} finally {
		loading.value = false;
	}
}
onMounted(load);
const pages = computed(() => (data.value?.workspaces || []).filter((w: any) => (scope.value === "all" || (scope.value === "public" ? w.public : !w.public)) && (!search.value || (w.label || w.name).toLowerCase().includes(search.value.toLowerCase()))));
const icons = computed(() => (data.value?.icons || []).filter((i: any) => !search.value || (i.label || "").toLowerCase().includes(search.value.toLowerCase())));

async function grant() {
	if (!(await confirmAction({ title: "Give yourself the Workspace Manager role?", message: "The framework requires it to change navigation for everyone. The change is recorded like any role change.", confirmLabel: "Add role" }))) return;
	if (await runAction(API + "grant_workspace_manager", {}, "Workspace Manager role added")) load();
}

const edit = reactive({ open: false, name: "", label: "", roles: [] as string[], is_hidden: false, isPublic: false });
function openEdit(w: any) {
	Object.assign(edit, { open: true, name: w.name, label: w.label || w.name, roles: [...w.roles], is_hidden: !!w.is_hidden, isPublic: !!w.public });
}
async function saveEdit() {
	if (await runAction(API + "update_workspace", { name: edit.name, values: { roles: edit.roles, is_hidden: edit.is_hidden ? 1 : 0 } }, "Workspace saved")) {
		edit.open = false;
		load();
	}
}

const order = reactive({ open: false, list: [] as any[] });
function openOrder() {
	order.list = (data.value?.workspaces || []).filter((w: any) => w.public && !w.parent_page);
	order.open = true;
}
function mv(i: number, d: number) {
	const j = i + d;
	if (j < 0 || j >= order.list.length) return;
	[order.list[i], order.list[j]] = [order.list[j], order.list[i]];
}
async function saveOrder() {
	if (await runAction(API + "reorder_workspaces", { names: order.list.map((w) => w.name) }, "Order saved")) {
		order.open = false;
		load();
	}
}

async function toggleIcon(i: any, hidden: boolean) {
	const prev = i.hidden;
	i.hidden = hidden ? 1 : 0;
	if (!(await runAction(API + "update_desktop_icon", { name: i.name, values: { hidden: i.hidden } }, hidden ? `${i.label} hidden` : `${i.label} shown`))) i.hidden = prev;
}
const iconEdit = reactive({ open: false, name: "", label: "", roles: [] as string[] });
async function saveIconRoles() {
	if (await runAction(API + "update_desktop_icon", { name: iconEdit.name, values: { roles: iconEdit.roles } }, "Icon roles saved")) {
		iconEdit.open = false;
		load();
	}
}
</script>

<template>
	<div class="mx-auto w-full max-w-[1480px] px-4 pb-10 pt-6 sm:px-6">
		<PageHeader title="Workspaces" description="Role-based workspaces, module sidebars and desktop icons: the navigation people see in thinkNXG.">
			<a href="/desk/workspace/new" class="nxg-btn nxg-btn-secondary"><Icon name="plus" :size="14" />New workspace</a>
		</PageHeader>

		<div v-if="data && !data.is_workspace_manager" class="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-nxg border border-[var(--nxg-warning)] bg-[var(--nxg-warning-soft)] px-4 py-3 text-[13px]">
			<span><b>Read-only for site-wide navigation.</b> The framework reserves public workspaces and sidebars for the Workspace Manager role.</span>
			<button class="nxg-btn nxg-btn-secondary h-7" @click="grant">Give me Workspace Manager</button>
		</div>

		<NxgTabs v-model="tab" class="mb-4" :tabs="[{ key: 'pages', label: 'Workspace pages', count: data?.workspaces?.length }, { key: 'sidebars', label: 'Sidebar builder' }, { key: 'icons', label: 'Desktop icons', count: data?.icons?.length }]" />
		<div v-if="error" class="nxg-panel p-4 text-[13px] text-nxg-danger">{{ error }} <button class="nxg-btn nxg-btn-secondary ml-2 h-7" @click="load">Retry</button></div>

		<div v-else-if="tab === 'pages'" class="nxg-panel">
			<div class="flex flex-wrap items-center gap-2 border-b border-nxg-border p-3">
				<input v-model="search" class="nxg-input max-w-xs" placeholder="Search workspaces" aria-label="Search workspaces" />
				<div class="inline-flex rounded-nxg border border-nxg-border p-0.5"><button v-for="s in ['public', 'private', 'all']" :key="s" class="h-7 rounded-[6px] px-2.5 text-[12.5px] font-medium capitalize" :class="scope === s ? 'bg-nxg-primary text-nxg-primary-fg' : 'text-nxg-text-2'" @click="scope = s as any">{{ s }}</button></div>
				<button class="nxg-btn nxg-btn-secondary ml-auto" :disabled="!data?.is_workspace_manager" @click="openOrder">Reorder</button>
			</div>
			<DataTable :columns="[{ key: 'label', label: 'Workspace' }, { key: 'module', label: 'Module · app' }, { key: 'roles', label: 'Visible to' }, { key: 'public', label: 'Type' }, { key: 'is_hidden', label: 'Status' }, { key: 'actions', label: '', align: 'right' }]" :rows="pages" :loading="loading" clickable @row-click="openEdit">
				<template #cell-label="{ row }"><span class="flex items-center gap-2"><span class="font-medium" :class="row.parent_page && 'pl-4'">{{ row.label || row.name }}</span><span v-if="row.parent_page" class="text-[11.5px] text-nxg-text-3">in {{ row.parent_page }}</span></span></template>
				<template #cell-module="{ row }"><span class="text-nxg-text-2">{{ row.module || "—" }}<span v-if="row.app"> · {{ row.app }}</span></span></template>
				<template #cell-roles="{ row }"><span class="flex max-w-[280px] flex-wrap gap-1"><span v-for="r in row.roles.slice(0, 3)" :key="r" class="nxg-chip">{{ r }}</span><span v-if="row.roles.length > 3" class="nxg-chip">+{{ row.roles.length - 3 }}</span><span v-if="!row.roles.length" class="text-nxg-text-2">Everyone with access</span></span></template>
				<template #cell-public="{ row }"><span class="text-nxg-text-2">{{ row.public ? "Public" : `Private · ${row.for_user}` }}</span></template>
				<template #cell-is_hidden="{ row }"><span :class="row.is_hidden ? 'text-nxg-text-3' : ''">{{ row.is_hidden ? "Hidden" : "Shown" }}</span></template>
				<template #cell-actions="{ row }"><a :href="`/desk/${encodeURIComponent((row.name || '').toLowerCase().replace(/ /g, '-'))}`" class="nxg-btn nxg-btn-ghost h-7" @click.stop>Open<Icon name="external-link" :size="12" /></a></template>
			</DataTable>
		</div>

		<SidebarBuilder v-else-if="tab === 'sidebars'" :modules="data?.modules || []" :can-edit="!!data?.is_workspace_manager" @saved="load" />

		<div v-else class="nxg-panel">
			<div class="flex items-center gap-2 border-b border-nxg-border p-3"><input v-model="search" class="nxg-input max-w-xs" placeholder="Search icons" aria-label="Search icons" /><span class="text-[12.5px] text-nxg-text-2">Hiding an icon removes it from the desktop; the app stays installed and its pages stay reachable by permission.</span></div>
			<DataTable :columns="[{ key: 'label', label: 'Icon' }, { key: 'app', label: 'App' }, { key: 'link', label: 'Opens' }, { key: 'roles', label: 'Roles' }, { key: 'hidden', label: 'Shown', align: 'right' }]" :rows="icons" :loading="loading">
				<template #cell-label="{ row }"><span class="flex items-center gap-2"><Icon :name="row.icon" :size="15" class="text-nxg-text-2" /><span class="font-medium">{{ row.label }}</span><span v-if="row.parent_icon" class="text-[11.5px] text-nxg-text-3">in {{ row.parent_icon }}</span></span></template>
				<template #cell-link="{ row }"><span class="text-nxg-text-2">{{ row.link_type }}{{ row.link_to ? `: ${row.link_to}` : "" }}</span></template>
				<template #cell-roles="{ row }"><button class="flex flex-wrap gap-1 text-left" @click="Object.assign(iconEdit, { open: true, name: row.name, label: row.label, roles: [...row.roles] })"><span v-for="r in row.roles.slice(0, 2)" :key="r" class="nxg-chip">{{ r }}</span><span v-if="row.roles.length > 2" class="nxg-chip">+{{ row.roles.length - 2 }}</span><span v-if="!row.roles.length" class="text-[12.5px] text-nxg-text-2 underline decoration-dotted">Any</span></button></template>
				<template #cell-hidden="{ row }"><NxgSwitch :model-value="!row.hidden" :label="`Show ${row.label}`" @update:model-value="(v) => toggleIcon(row, !v)" /></template>
			</DataTable>
		</div>

		<NxgDialog :open="edit.open" :title="edit.label" description="Who sees this workspace and whether it is listed." width="max-w-[540px]" @close="edit.open = false">
			<div class="space-y-3 pb-2">
				<div><label class="nxg-label">Restrict to roles <span class="font-normal text-nxg-text-3">· empty means everyone who can access its module</span></label><NxgMultiSelect v-model="edit.roles" :options="data?.roles || []" placeholder="Add role" /></div>
				<div class="flex items-center justify-between rounded-nxg border border-nxg-border px-3 py-2.5"><div><div class="text-[13px] font-medium">Hidden</div><div class="text-[12px] text-nxg-text-2">Hidden workspaces stay reachable by URL.</div></div><NxgSwitch v-model="edit.is_hidden" label="Hidden" /></div>
				<p v-if="edit.isPublic && !data?.is_workspace_manager" class="text-[12px] text-nxg-warning">Saving a public workspace needs the Workspace Manager role.</p>
			</div>
			<template #footer>
				<a :href="`/desk/workspace/${encodeURIComponent(edit.name)}`" class="nxg-btn nxg-btn-ghost mr-auto">Edit content in Desk<Icon name="external-link" :size="13" /></a>
				<button class="nxg-btn nxg-btn-secondary" @click="edit.open = false">Cancel</button>
				<button class="nxg-btn nxg-btn-primary" @click="saveEdit">Save</button>
			</template>
		</NxgDialog>

		<NxgDialog :open="order.open" title="Reorder public workspaces" description="Top-level public workspaces, in sidebar order." @close="order.open = false">
			<ul class="divide-y divide-nxg-border rounded-nxg border border-nxg-border">
				<li v-for="(w, i) in order.list" :key="w.name" class="flex items-center gap-2 px-3 py-1.5 text-[13px]">
					<span class="nxg-tnum w-6 text-nxg-text-3">{{ i + 1 }}</span><span class="flex-1 truncate">{{ w.label || w.name }}</span>
					<button class="nxg-icon-btn h-7 w-7" :aria-label="`Move ${w.label} up`" @click="mv(i, -1)"><Icon name="chevron-right" :size="14" class="-rotate-90" /></button>
					<button class="nxg-icon-btn h-7 w-7" :aria-label="`Move ${w.label} down`" @click="mv(i, 1)"><Icon name="chevron-right" :size="14" class="rotate-90" /></button>
				</li>
			</ul>
			<template #footer><button class="nxg-btn nxg-btn-secondary" @click="order.open = false">Cancel</button><button class="nxg-btn nxg-btn-primary" @click="saveOrder">Save order</button></template>
		</NxgDialog>

		<NxgDialog :open="iconEdit.open" :title="`Roles for ${iconEdit.label}`" description="Only these roles see the icon. Empty means everyone with access to what it opens." @close="iconEdit.open = false">
			<NxgMultiSelect v-model="iconEdit.roles" :options="data?.roles || []" placeholder="Add role" />
			<template #footer><button class="nxg-btn nxg-btn-secondary" @click="iconEdit.open = false">Cancel</button><button class="nxg-btn nxg-btn-primary" @click="saveIconRoles">Save</button></template>
		</NxgDialog>
	</div>
</template>
