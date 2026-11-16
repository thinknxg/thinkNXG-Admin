<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { call } from "frappe-ui";
import PageHeader from "@/components/ui/PageHeader.vue";
import NxgDialog from "@/components/ui/NxgDialog.vue";
import NxgMultiSelect from "@/components/ui/NxgMultiSelect.vue";
import Icon from "@/components/ui/Icon.vue";
import { errorMessage, runAction } from "@/data/api";
import { confirmAction } from "@/composables/useConfirm";

const profiles = ref<any[] | null>(null);
const unavailable = ref(false);
const error = ref<string | null>(null);
const loading = ref(false);
const roles = ref<string[]>([]);
async function load() {
	loading.value = true;
	try {
		const res = (await call("thinknxg_admin.api.roles.list_role_profiles")) as any[] | null;
		unavailable.value = res === null;
		profiles.value = res || [];
	} catch (e) {
		error.value = errorMessage(e);
	} finally {
		loading.value = false;
	}
}
onMounted(async () => {
	load();
	try {
		roles.value = ((await call("thinknxg_admin.api.users.get_form_options")) as any).roles.map((r: any) => r.name);
	} catch {
		/* ignore */
	}
});
const edit = reactive({ open: false, create: false, name: "", roles: [] as string[], users: 0, saving: false });
function openEdit(p?: any) {
	Object.assign(edit, p ? { open: true, create: false, name: p.name, roles: [...p.roles], users: p.users } : { open: true, create: true, name: "", roles: [], users: 0 });
}
async function save() {
	if (!edit.create && edit.users) {
		const ok = await confirmAction({ title: `Update ${edit.name}?`, message: `The framework re-applies this profile's roles to its ${edit.users} user${edit.users === 1 ? "" : "s"}.`, confirmLabel: "Save and apply" });
		if (!ok) return;
	}
	edit.saving = true;
	const res = await runAction("thinknxg_admin.api.roles.save_role_profile", { name: edit.name, roles: edit.roles, create: edit.create ? 1 : 0 }, edit.create ? "Profile created" : "Profile saved");
	edit.saving = false;
	if (res) {
		edit.open = false;
		load();
	}
}
</script>

<template>
	<div class="mx-auto w-full max-w-[1200px] px-4 pb-10 pt-6 sm:px-6">
		<PageHeader title="Role Profiles" description="Named bundles of roles. Assign a profile to a user and they get every role in it, kept in sync when the profile changes.">
			<button class="nxg-btn nxg-btn-primary" :disabled="unavailable" @click="openEdit()"><Icon name="plus" :size="14" />New profile</button>
		</PageHeader>
		<div v-if="error" class="nxg-panel p-4 text-[13px] text-nxg-danger">{{ error }}</div>
		<div v-else-if="unavailable" class="nxg-panel p-6 text-[13px] text-nxg-text-2">Role Profile is not available on this site.</div>
		<div v-else-if="loading && !profiles" class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3"><div v-for="i in 6" :key="i" class="nxg-skeleton h-32" /></div>
		<div v-else-if="!profiles?.length" class="nxg-panel p-10 text-center text-[13px] text-nxg-text-2">No role profiles yet. Create one, for example "Sales Team", to assign several roles at once.</div>
		<div v-else class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
			<button v-for="p in profiles" :key="p.name" class="nxg-panel flex flex-col gap-2 p-4 text-left transition-colors hover:border-nxg-border-strong" @click="openEdit(p)">
				<div class="flex items-center justify-between gap-2"><span class="truncate text-[14px] font-semibold">{{ p.name }}</span><span class="nxg-tnum shrink-0 text-[12px] text-nxg-text-2">{{ p.users }} user{{ p.users === 1 ? "" : "s" }}</span></div>
				<div class="flex flex-wrap gap-1"><span v-for="r in p.roles.slice(0, 8)" :key="r" class="nxg-chip">{{ r }}</span><span v-if="p.roles.length > 8" class="nxg-chip">+{{ p.roles.length - 8 }}</span><span v-if="!p.roles.length" class="text-[12.5px] text-nxg-text-3">No roles</span></div>
			</button>
		</div>

		<NxgDialog :open="edit.open" :title="edit.create ? 'New role profile' : edit.name" width="max-w-[560px]" @close="edit.open = false">
			<div class="space-y-3 pb-2">
				<div v-if="edit.create"><label class="nxg-label">Profile name</label><input v-model="edit.name" class="nxg-input" placeholder="e.g. Sales Team" /></div>
				<div><label class="nxg-label">Roles</label><NxgMultiSelect v-model="edit.roles" :options="roles" placeholder="Add role" /></div>
			</div>
			<template #footer>
				<a v-if="!edit.create" :href="`/desk/role-profile/${encodeURIComponent(edit.name)}`" class="nxg-btn nxg-btn-ghost mr-auto">Open in Desk<Icon name="external-link" :size="13" /></a>
				<button class="nxg-btn nxg-btn-secondary" @click="edit.open = false">Cancel</button>
				<button class="nxg-btn nxg-btn-primary" :disabled="!edit.name.trim() || edit.saving" @click="save">{{ edit.saving ? "Saving…" : "Save" }}</button>
			</template>
		</NxgDialog>
	</div>
</template>
