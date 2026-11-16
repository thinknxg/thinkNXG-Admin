<script setup lang="ts">
import { reactive, ref, watch } from "vue";
import { call } from "frappe-ui";
import PageHeader from "@/components/ui/PageHeader.vue";
import DataTable from "@/components/ui/DataTable.vue";
import NxgPagination from "@/components/ui/NxgPagination.vue";
import NxgDialog from "@/components/ui/NxgDialog.vue";
import Icon from "@/components/ui/Icon.vue";
import { errorMessage, runAction } from "@/data/api";
import { confirmAction } from "@/composables/useConfirm";

const API = "thinknxg_admin.api.users.";
const f = reactive({ user: "", allow: "" });
const start = ref(0);
const data = ref<any>(null);
const loading = ref(false);
const error = ref<string | null>(null);
let t: number | undefined;
async function load() {
	loading.value = true;
	error.value = null;
	try {
		data.value = await call(API + "list_user_permissions", { ...f, start: start.value, page_length: 50 });
	} catch (e) {
		error.value = errorMessage(e);
	} finally {
		loading.value = false;
	}
}
watch(() => ({ ...f }), () => { start.value = 0; window.clearTimeout(t); t = window.setTimeout(load, 250); }, { deep: true, immediate: true });
watch(start, load);

const form = reactive({ open: false, user: "", allow: "Company", for_value: "", is_default: false, apply_to_all_doctypes: true, applicable_for: "" });
async function add() {
	const ok = await runAction(API + "add_user_permission", { ...form, is_default: form.is_default ? 1 : 0, apply_to_all_doctypes: form.apply_to_all_doctypes ? 1 : 0 }, "Restriction added");
	if (ok) {
		Object.assign(form, { open: false, user: "", for_value: "", applicable_for: "" });
		load();
	}
}
async function remove(r: any) {
	if (!(await confirmAction({ title: "Remove restriction?", message: `${r.user} · ${r.allow}: ${r.for_value}`, confirmLabel: "Remove", danger: true }))) return;
	if (await runAction(API + "delete_user_permission", { name: r.name }, "Removed")) load();
}
</script>

<template>
	<div class="mx-auto w-full max-w-[1200px] px-4 pb-10 pt-6 sm:px-6">
		<PageHeader title="User Permissions" description="Record-level restrictions: limit users to specific companies, branches, territories or any other record.">
			<button class="nxg-btn nxg-btn-primary" @click="form.open = true"><Icon name="plus" :size="14" />Add restriction</button>
		</PageHeader>
		<div class="nxg-panel">
			<div class="flex flex-wrap gap-2 border-b border-nxg-border p-3">
				<input v-model="f.user" class="nxg-input max-w-xs" placeholder="Filter by user (email)" aria-label="Filter by user" />
				<select v-model="f.allow" class="nxg-input w-auto" aria-label="Restricted DocType"><option value="">Any DocType</option><option v-for="a in data?.allow_options || []" :key="a">{{ a }}</option></select>
			</div>
			<div v-if="error" class="p-4 text-[13px] text-nxg-danger">{{ error }}</div>
			<DataTable v-else :columns="[{ key: 'user', label: 'User' }, { key: 'allow', label: 'Restricted by' }, { key: 'for_value', label: 'Value' }, { key: 'scope', label: 'Applies to' }, { key: 'is_default', label: 'Default' }, { key: 'actions', label: '', align: 'right' }]" :rows="data?.rows || []" :loading="loading" empty-text="No restrictions. Users see records according to their roles.">
				<template #cell-user="{ row }"><span class="font-medium">{{ row.user }}</span></template>
				<template #cell-allow="{ row }"><span class="nxg-chip">{{ row.allow }}</span></template>
				<template #cell-scope="{ row }"><span class="text-nxg-text-2">{{ row.apply_to_all_doctypes ? "All documents" : row.applicable_for }}</span></template>
				<template #cell-is_default="{ row }"><span>{{ row.is_default ? "Yes" : "—" }}</span></template>
				<template #cell-actions="{ row }"><button class="nxg-btn nxg-btn-ghost h-7" @click="remove(row)">Remove</button></template>
			</DataTable>
			<NxgPagination v-if="data" :start="start" :page-length="50" :total="data.total" class="border-t border-nxg-border" @change="(s) => (start = s)" />
		</div>

		<NxgDialog :open="form.open" title="Add restriction" @close="form.open = false">
			<div class="space-y-3 pb-2">
				<div><label class="nxg-label">User (email)</label><input v-model="form.user" class="nxg-input" /></div>
				<div class="grid grid-cols-2 gap-3">
					<div><label class="nxg-label">Restrict by DocType</label><input v-model="form.allow" class="nxg-input" /></div>
					<div><label class="nxg-label">Value</label><input v-model="form.for_value" class="nxg-input" /></div>
				</div>
				<label class="flex items-center gap-2 text-[13px]"><input v-model="form.apply_to_all_doctypes" type="checkbox" class="rounded border-nxg-border-strong text-nxg-espresso focus:ring-0" />Apply to all documents</label>
				<div v-if="!form.apply_to_all_doctypes"><label class="nxg-label">Only for DocType</label><input v-model="form.applicable_for" class="nxg-input" /></div>
				<label class="flex items-center gap-2 text-[13px]"><input v-model="form.is_default" type="checkbox" class="rounded border-nxg-border-strong text-nxg-espresso focus:ring-0" />Use as default value</label>
			</div>
			<template #footer>
				<button class="nxg-btn nxg-btn-secondary" @click="form.open = false">Cancel</button>
				<button class="nxg-btn nxg-btn-primary" :disabled="!form.user || !form.allow || !form.for_value" @click="add">Add</button>
			</template>
		</NxgDialog>
	</div>
</template>
