<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { call, toast } from "frappe-ui";
import PageHeader from "@/components/ui/PageHeader.vue";
import NxgDialog from "@/components/ui/NxgDialog.vue";
import Icon from "@/components/ui/Icon.vue";
import { errorMessage } from "@/data/api";
import { confirmAction } from "@/composables/useConfirm";

/** Role x permission-type matrix for one DocType, or DocType x permission-type for one role.
 *  Every change goes through Core's Role Permission Manager methods, which enforce
 *  System Manager and keep the rules valid. */
const PM = "frappe.core.page.permission_manager.permission_manager.";
const route = useRoute();
const router = useRouter();
const mode = ref<"doctype" | "role">(route.query.role ? "role" : "doctype");
const meta = ref<{ doctypes: { value: string }[]; roles: { value: string }[]; doctype_ptype_map: Record<string, string[]> } | null>(null);
const doctype = ref<string>((route.query.doctype as string) || "");
const role = ref<string>((route.query.role as string) || "");
const rules = ref<any[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);
const pending = ref<Set<string>>(new Set());
const dtSearch = ref("");

const BASE: { key: string; label: string; hint: string; submit?: boolean }[] = [
	{ key: "select", label: "Select", hint: "Pick in link fields without opening" },
	{ key: "read", label: "Read", hint: "Open and view" },
	{ key: "write", label: "Write", hint: "Edit" },
	{ key: "create", label: "Create", hint: "Create new" },
	{ key: "delete", label: "Delete", hint: "Delete" },
	{ key: "submit", label: "Submit", hint: "Submit (submittable DocTypes)", submit: true },
	{ key: "cancel", label: "Cancel", hint: "Cancel submitted", submit: true },
	{ key: "amend", label: "Amend", hint: "Amend cancelled", submit: true },
	{ key: "report", label: "Report", hint: "Report view" },
	{ key: "export", label: "Export", hint: "Export data" },
	{ key: "import", label: "Import", hint: "Data Import" },
	{ key: "share", label: "Share", hint: "Share a document" },
	{ key: "print", label: "Print", hint: "Print / PDF" },
	{ key: "email", label: "Email", hint: "Send email" },
	{ key: "if_owner", label: "Own only", hint: "Applies only to documents the user created" },
];

onMounted(async () => {
	try {
		meta.value = await call(PM + "get_roles_and_doctypes");
		if (mode.value === "doctype" && !doctype.value) doctype.value = "User";
	} catch (e) {
		error.value = errorMessage(e);
	}
});

async function load() {
	const target = mode.value === "doctype" ? doctype.value : role.value;
	router.replace({ query: mode.value === "doctype" ? (doctype.value ? { doctype: doctype.value } : {}) : role.value ? { role: role.value } : {} });
	if (!target) {
		rules.value = [];
		return;
	}
	loading.value = true;
	error.value = null;
	try {
		rules.value = await call(PM + "get_permissions", mode.value === "doctype" ? { doctype: doctype.value } : { role: role.value });
	} catch (e) {
		error.value = errorMessage(e);
	} finally {
		loading.value = false;
	}
}
watch([mode, doctype, role], load, { immediate: true });

const submittable = computed(() => rules.value.some((r) => r.is_submittable));
const columns = computed(() => {
	const custom = mode.value === "doctype" ? meta.value?.doctype_ptype_map?.[doctype.value] || [] : [];
	const base = BASE.filter((c) => !c.submit || submittable.value || mode.value === "role");
	return [...base, ...custom.map((p) => ({ key: p, label: p.replace(/_/g, " "), hint: "Custom permission type" }))];
});
const rows = computed(() => [...rules.value].sort((a, b) => (mode.value === "doctype" ? a.role.localeCompare(b.role) : a.parent.localeCompare(b.parent)) || a.permlevel - b.permlevel));
const doctypeOptions = computed(() => (meta.value?.doctypes || []).map((d) => d.value).filter((d) => !dtSearch.value || d.toLowerCase().includes(dtSearch.value.toLowerCase())).slice(0, 200));

async function toggle(r: any, ptype: string) {
	const id = `${r.parent}|${r.role}|${r.permlevel}|${r.if_owner}|${ptype}`;
	if (pending.value.has(id)) return;
	const next = r[ptype] ? 0 : 1;
	if (ptype === "read" && !next && (r.write || r.create || r.delete)) {
		if (!(await confirmAction({ title: "Remove read access?", message: `${r.role} will also lose the ability to open ${r.parent} documents it can currently edit.`, confirmLabel: "Remove read", danger: true }))) return;
	}
	pending.value.add(id);
	const prev = r[ptype];
	r[ptype] = next; // optimistic
	try {
		const out = await call(PM + "update", { doctype: r.parent, role: r.role, permlevel: r.permlevel, ptype, value: String(next), if_owner: String(r.if_owner || 0) });
		if (out === "refresh") await load();
	} catch (e) {
		r[ptype] = prev;
		toast.error(errorMessage(e));
	} finally {
		pending.value.delete(id);
	}
}

const addDialog = ref({ open: false, role: "", doctype: "", permlevel: 0 });
async function addRule() {
	const a = addDialog.value;
	try {
		await call(PM + "add", { parent: mode.value === "doctype" ? doctype.value : a.doctype, role: mode.value === "doctype" ? a.role : role.value, permlevel: a.permlevel });
		toast.success("Rule added with read access");
		addDialog.value.open = false;
		await load();
	} catch (e) {
		toast.error(errorMessage(e));
	}
}
async function removeRule(r: any) {
	if (!(await confirmAction({ title: `Remove ${r.role} from ${r.parent}?`, message: `Deletes the level ${r.permlevel} rule${r.if_owner ? " (own documents only)" : ""}.`, confirmLabel: "Remove rule", danger: true }))) return;
	try {
		await call(PM + "remove", { doctype: r.parent, role: r.role, permlevel: r.permlevel, if_owner: r.if_owner || 0 });
		toast.success("Rule removed");
		await load();
	} catch (e) {
		toast.error(errorMessage(e));
	}
}
async function resetDoctype() {
	if (!(await confirmAction({ title: `Reset ${doctype.value} to standard permissions?`, message: "All customised rules for this DocType are deleted and the app's defaults apply again.", confirmLabel: "Reset", danger: true, typeToConfirm: "RESET" }))) return;
	try {
		await call(PM + "reset", { doctype: doctype.value });
		toast.success("Permissions reset to standard");
		await load();
	} catch (e) {
		toast.error(errorMessage(e));
	}
}
</script>

<template>
	<div class="mx-auto w-full max-w-[1480px] px-4 pb-10 pt-6 sm:px-6">
		<PageHeader title="Permission Matrix" description="DocType permission rules, edited through the framework's own Role Permission Manager. Changes apply immediately.">
			<a :href="$href('/desk/permission-manager')" class="nxg-btn nxg-btn-ghost">Classic manager<Icon name="external-link" :size="13" /></a>
		</PageHeader>

		<div class="nxg-panel">
			<div class="flex flex-wrap items-center gap-2 border-b border-nxg-border p-3">
				<div class="inline-flex rounded-nxg border border-nxg-border p-0.5" role="group" aria-label="Matrix view">
					<button class="h-7 rounded-[6px] px-2.5 text-[12.5px] font-medium" :class="mode === 'doctype' ? 'bg-nxg-primary text-nxg-primary-fg' : 'text-nxg-text-2'" @click="mode = 'doctype'">By DocType</button>
					<button class="h-7 rounded-[6px] px-2.5 text-[12.5px] font-medium" :class="mode === 'role' ? 'bg-nxg-primary text-nxg-primary-fg' : 'text-nxg-text-2'" @click="mode = 'role'">By role</button>
				</div>
				<template v-if="mode === 'doctype'">
					<input v-model="dtSearch" class="nxg-input w-44" placeholder="Find DocType…" aria-label="Find DocType" />
					<select v-model="doctype" class="nxg-input w-auto max-w-[260px]" aria-label="DocType"><option v-for="d in doctypeOptions" :key="d" :value="d">{{ d }}</option><option v-if="doctype && !doctypeOptions.includes(doctype)" :value="doctype">{{ doctype }}</option></select>
				</template>
				<select v-else v-model="role" class="nxg-input w-auto max-w-[260px]" aria-label="Role"><option value="" disabled>Choose a role</option><option v-for="r in meta?.roles || []" :key="r.value" :value="r.value">{{ r.value }}</option></select>
				<div class="ml-auto flex gap-2">
					<button class="nxg-btn nxg-btn-secondary" :disabled="mode === 'doctype' ? !doctype : !role" @click="addDialog = { open: true, role: '', doctype: '', permlevel: 0 }"><Icon name="plus" :size="14" />{{ mode === "doctype" ? "Add role" : "Add DocType" }}</button>
					<button v-if="mode === 'doctype'" class="nxg-btn nxg-btn-ghost" :disabled="!doctype" @click="resetDoctype">Reset to standard</button>
				</div>
			</div>

			<div v-if="error" class="p-4 text-[13px] text-nxg-danger">{{ error }}</div>
			<div v-else class="overflow-x-auto">
				<table class="w-full min-w-[980px] text-[13px]">
					<thead class="sticky top-0 bg-nxg-surface">
						<tr class="border-b border-nxg-border">
							<th class="sticky left-0 z-[1] bg-nxg-surface px-4 py-2 text-left nxg-micro">{{ mode === "doctype" ? "Role" : "DocType" }}</th>
							<th class="px-2 py-2 text-center nxg-micro" title="Permission level (field-level groups)">Lvl</th>
							<th v-for="c in columns" :key="c.key" class="px-1.5 py-2 text-center nxg-micro" :title="c.hint">{{ c.label }}</th>
							<th class="w-10" />
						</tr>
					</thead>
					<tbody class="divide-y divide-nxg-border">
						<tr v-if="loading && !rows.length"><td :colspan="columns.length + 3" class="p-4"><div class="nxg-skeleton h-24" /></td></tr>
						<tr v-else-if="!rows.length"><td :colspan="columns.length + 3" class="px-4 py-10 text-center text-nxg-text-2">No rules yet. Add a {{ mode === "doctype" ? "role" : "DocType" }} to grant access.</td></tr>
						<tr v-for="r in rows" :key="`${r.parent}|${r.role}|${r.permlevel}|${r.if_owner}`" class="hover:bg-nxg-surface-2/50" :class="loading && 'opacity-60'">
							<td class="sticky left-0 bg-nxg-surface px-4 py-1.5 font-medium">
								<RouterLink v-if="mode === 'doctype'" :to="{ path: '/roles', query: { role: r.role } }" class="hover:underline">{{ r.role }}</RouterLink>
								<span v-else>{{ r.parent }}</span>
							</td>
							<td class="nxg-tnum px-2 text-center text-nxg-text-2">{{ r.permlevel }}</td>
							<td v-for="c in columns" :key="c.key" class="px-1.5 py-1 text-center">
								<button
									class="inline-flex h-6 w-6 items-center justify-center rounded-nxg-sm border transition-colors disabled:cursor-not-allowed disabled:opacity-40"
									:class="r[c.key] ? 'border-transparent bg-nxg-primary text-nxg-primary-fg' : 'border-nxg-border-strong hover:border-nxg-text-2'"
									:aria-pressed="!!r[c.key]"
									:aria-label="`${c.label} for ${mode === 'doctype' ? r.role : r.parent}`"
									:disabled="(r.permlevel > 0 && !['read', 'write'].includes(c.key)) || (c.key === 'if_owner' && r.permlevel > 0)"
									@click="toggle(r, c.key)"
								><Icon v-if="r[c.key]" name="check" :size="13" :stroke-width="2.5" /></button>
							</td>
							<td class="px-2"><button class="nxg-icon-btn h-7 w-7" :aria-label="`Remove rule for ${r.role} on ${r.parent}`" @click="removeRule(r)"><Icon name="x" :size="14" /></button></td>
						</tr>
					</tbody>
				</table>
			</div>
			<p class="border-t border-nxg-border px-4 py-2.5 text-[12px] text-nxg-text-2">Levels above 0 control field groups and only take Read and Write. "Own only" limits the rule to documents the user created. Every change is recorded in the Permission Log.</p>
		</div>

		<NxgDialog :open="addDialog.open" :title="mode === 'doctype' ? `Add a role to ${doctype}` : `Add a DocType for ${role}`" description="Starts with read access; tick the rest in the matrix." @close="addDialog.open = false">
			<div class="grid grid-cols-3 gap-3 pb-2">
				<div class="col-span-2">
					<label class="nxg-label">{{ mode === "doctype" ? "Role" : "DocType" }}</label>
					<select v-if="mode === 'doctype'" v-model="addDialog.role" class="nxg-input"><option value="" disabled>Choose</option><option v-for="r in meta?.roles || []" :key="r.value">{{ r.value }}</option></select>
					<select v-else v-model="addDialog.doctype" class="nxg-input"><option value="" disabled>Choose</option><option v-for="d in meta?.doctypes || []" :key="d.value">{{ d.value }}</option></select>
				</div>
				<div><label class="nxg-label">Level</label><input v-model.number="addDialog.permlevel" type="number" min="0" max="9" class="nxg-input" /></div>
			</div>
			<template #footer><button class="nxg-btn nxg-btn-secondary" @click="addDialog.open = false">Cancel</button><button class="nxg-btn nxg-btn-primary" :disabled="mode === 'doctype' ? !addDialog.role : !addDialog.doctype" @click="addRule">Add rule</button></template>
		</NxgDialog>
	</div>
</template>
