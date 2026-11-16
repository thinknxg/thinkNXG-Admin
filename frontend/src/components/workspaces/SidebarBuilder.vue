<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { call, toast } from "frappe-ui";
import Icon from "@/components/ui/Icon.vue";
import NxgDialog from "@/components/ui/NxgDialog.vue";
import NxgEmpty from "@/components/ui/NxgEmpty.vue";
import { errorMessage } from "@/data/api";
import { confirmAction } from "@/composables/useConfirm";

/** Visual editor for a module's site-wide sidebar layer (V16 Custom Sidebar).
 *  Reads and writes through Core's endpoints, so the layer merge rules, permission
 *  filtering and boot cache invalidation stay exactly as the framework defines them. */
const CS = "frappe.desk.doctype.custom_sidebar.custom_sidebar.";
const props = defineProps<{ modules: { name: string; app_name: string; site_layer: boolean }[]; canEdit: boolean }>();
const emit = defineEmits<{ saved: [] }>();

const module = ref("");
const items = ref<any[]>([]);
const original = ref("");
const loading = ref(false);
const saving = ref(false);
const error = ref<string | null>(null);
const dragIndex = ref<number | null>(null);
const moduleSearch = ref("");

const grouped = computed(() => {
	const out: Record<string, typeof props.modules> = {};
	for (const m of props.modules) if (!moduleSearch.value || m.name.toLowerCase().includes(moduleSearch.value.toLowerCase())) (out[m.app_name] ||= []).push(m);
	return out;
});
watch(() => props.modules, (m) => { if (!module.value && m.length) module.value = (m.find((x) => x.name === "Selling") || m[0]).name; }, { immediate: true });

async function load() {
	if (!module.value || !props.canEdit) return;
	loading.value = true;
	error.value = null;
	try {
		const res: any[] = await call(CS + "get_site_sidebar_layer", { module: module.value });
		items.value = res.map((r, i) => ({ ...r, _id: `${i}-${r.key || r.link_to || r.label}` }));
		original.value = JSON.stringify(items.value);
	} catch (e) {
		error.value = errorMessage(e);
	} finally {
		loading.value = false;
	}
}
watch([module, () => props.canEdit], load, { immediate: true });
const dirty = computed(() => JSON.stringify(items.value) !== original.value);

function move(i: number, d: number) {
	const j = i + d;
	if (j < 0 || j >= items.value.length) return;
	const arr = [...items.value];
	[arr[i], arr[j]] = [arr[j], arr[i]];
	items.value = arr;
}
function onDrop(i: number) {
	if (dragIndex.value === null || dragIndex.value === i) return;
	const arr = [...items.value];
	const [it] = arr.splice(dragIndex.value, 1);
	arr.splice(i, 0, it);
	items.value = arr;
	dragIndex.value = null;
}
function removeAdded(i: number) {
	items.value = items.value.filter((_, k) => k !== i);
}

const add = ref({ open: false, type: "Link", link_type: "DocType", link_to: "", url: "", label: "", icon: "" });
function addItem() {
	const a = add.value;
	const row: any = { type: a.type, label: a.label || a.link_to, icon: a.icon || null, added: 1, hidden: 0, child: 0, _id: `new-${Date.now()}` };
	if (a.type === "Link") Object.assign(row, { link_type: a.link_type, link_to: a.link_type === "URL" ? null : a.link_to, url: a.link_type === "URL" ? a.url : null });
	items.value = [...items.value, row];
	add.value = { open: false, type: "Link", link_type: "DocType", link_to: "", url: "", label: "", icon: "" };
}

async function save() {
	saving.value = true;
	try {
		const payload = items.value.map(({ _id, ...r }) => r);
		await call(CS + "save_site_sidebar", { module: module.value, items: JSON.stringify(payload) });
		toast.success(`${module.value} sidebar saved for everyone`);
		emit("saved");
		await load();
	} catch (e) {
		toast.error(errorMessage(e));
	} finally {
		saving.value = false;
	}
}
async function reset() {
	if (!(await confirmAction({ title: `Reset the ${module.value} sidebar?`, message: "Removes the site-wide arrangement. Everyone sees the app's standard sidebar again (personal arrangements are kept).", confirmLabel: "Reset", danger: true }))) return;
	try {
		await call(CS + "reset_site_sidebar", { module: module.value });
		toast.success("Sidebar reset to standard");
		emit("saved");
		await load();
	} catch (e) {
		toast.error(errorMessage(e));
	}
}
const kindIcon = (r: any) => (r.type === "Section Break" ? "layers" : r.type === "Spacer" ? "circle" : r.link_type === "Report" ? "chart-column" : r.link_type === "Workspace" ? "panels-top-left" : r.link_type === "URL" ? "external-link" : "file-text");
</script>

<template>
	<div class="grid grid-cols-1 gap-4 lg:grid-cols-[260px_1fr]">
		<aside class="nxg-panel flex max-h-[640px] flex-col">
			<div class="border-b border-nxg-border p-2"><input v-model="moduleSearch" class="nxg-input" placeholder="Find module" aria-label="Find module" /></div>
			<div class="nxg-scroll min-h-0 flex-1 overflow-y-auto p-1.5">
				<div v-for="(mods, app) in grouped" :key="app" class="mb-2">
					<div class="px-2 pb-1 pt-1.5 nxg-micro">{{ app }}</div>
					<button v-for="m in mods" :key="m.name" class="flex h-8 w-full items-center gap-2 rounded-nxg-sm px-2 text-left text-[13px]" :class="module === m.name ? 'bg-nxg-surface-2 font-medium' : 'hover:bg-nxg-surface-2'" @click="module = m.name">
						<span class="min-w-0 flex-1 truncate">{{ m.name }}</span>
						<span v-if="m.site_layer" class="h-1.5 w-1.5 rounded-full bg-nxg-red" title="Customised for the site" />
					</button>
				</div>
			</div>
		</aside>

		<section class="nxg-panel min-w-0">
			<header class="flex flex-wrap items-center gap-2 border-b border-nxg-border px-4 py-3">
				<div class="min-w-0 flex-1"><h2 class="truncate text-[15px] font-semibold">{{ module }} sidebar</h2><p class="text-[12.5px] text-nxg-text-2">Site-wide layer: applies to everyone unless they arranged their own. Permissions still decide what each person sees.</p></div>
				<template v-if="canEdit">
					<button class="nxg-btn nxg-btn-secondary" @click="add.open = true"><Icon name="plus" :size="14" />Add item</button>
					<button class="nxg-btn nxg-btn-ghost" @click="reset">Reset</button>
					<button class="nxg-btn nxg-btn-primary" :disabled="!dirty || saving" @click="save">{{ saving ? "Saving…" : "Save for everyone" }}</button>
				</template>
			</header>
			<div v-if="!canEdit" class="p-6 text-[13px] text-nxg-text-2">The framework requires the Workspace Manager role to change navigation for everyone.</div>
			<div v-else-if="error" class="p-4 text-[13px] text-nxg-danger">{{ error }}</div>
			<div v-else-if="loading" class="space-y-2 p-4"><div v-for="i in 8" :key="i" class="nxg-skeleton h-9" /></div>
			<NxgEmpty v-else-if="!items.length" text="This module has no sidebar items" icon="layers" />
			<ul v-else class="p-2" aria-label="Sidebar items (drag to reorder)">
				<li
					v-for="(r, i) in items"
					:key="r._id"
					draggable="true"
					class="group flex items-center gap-2 rounded-nxg px-2 py-1.5 transition-colors"
					:class="[dragIndex === i ? 'opacity-40' : 'hover:bg-nxg-surface-2', r.type === 'Section Break' && 'mt-2']"
					:style="{ paddingLeft: r.child && r.type !== 'Section Break' ? '30px' : undefined }"
					@dragstart="dragIndex = i"
					@dragover.prevent
					@drop="onDrop(i)"
					@dragend="dragIndex = null"
				>
					<Icon name="menu" :size="14" class="cursor-grab text-nxg-text-3" aria-hidden="true" />
					<Icon :name="kindIcon(r)" :size="14" class="text-nxg-text-2" />
					<input v-model="r.label" class="h-7 min-w-0 flex-1 rounded border border-transparent bg-transparent px-1.5 text-[13px] hover:border-nxg-border focus:border-nxg-border-strong focus:outline-none focus:ring-0" :class="[r.hidden && 'text-nxg-text-3 line-through', r.type === 'Section Break' && 'font-semibold uppercase tracking-wide text-[11.5px]']" :aria-label="`Label for ${r.label}`" />
					<span class="hidden max-w-[180px] truncate text-[11.5px] text-nxg-text-3 md:inline">{{ r.type === "Link" ? `${r.link_type}${r.link_to ? ": " + r.link_to : ""}` : r.type }}</span>
					<span v-if="r.added" class="nxg-chip">Added</span>
					<div class="flex items-center">
						<button v-if="r.type !== 'Section Break'" class="nxg-icon-btn h-7 w-7" :title="r.child ? 'Move out of section' : 'Nest under section'" :aria-label="r.child ? 'Outdent' : 'Indent'" @click="r.child = r.child ? 0 : 1"><Icon :name="r.child ? 'outdent' : 'indent'" :size="14" /></button>
						<button class="nxg-icon-btn h-7 w-7" :aria-label="`Move ${r.label} up`" @click="move(i, -1)"><Icon name="chevron-right" :size="14" class="-rotate-90" /></button>
						<button class="nxg-icon-btn h-7 w-7" :aria-label="`Move ${r.label} down`" @click="move(i, 1)"><Icon name="chevron-right" :size="14" class="rotate-90" /></button>
						<button class="nxg-btn nxg-btn-ghost h-7 px-2 text-[12px]" :aria-pressed="!r.hidden" @click="r.hidden = r.hidden ? 0 : 1">{{ r.hidden ? "Hidden" : "Visible" }}</button>
						<button v-if="r.added" class="nxg-icon-btn h-7 w-7" :aria-label="`Delete ${r.label}`" @click="removeAdded(i)"><Icon name="x" :size="14" /></button>
					</div>
				</li>
			</ul>
		</section>

		<NxgDialog :open="add.open" title="Add sidebar item" @close="add.open = false">
			<div class="space-y-3 pb-2">
				<div><label class="nxg-label">Kind</label><select v-model="add.type" class="nxg-input"><option value="Link">Link</option><option value="Section Break">Section heading</option></select></div>
				<template v-if="add.type === 'Link'">
					<div class="grid grid-cols-3 gap-3">
						<div><label class="nxg-label">Opens</label><select v-model="add.link_type" class="nxg-input"><option>DocType</option><option>Report</option><option>Workspace</option><option>Page</option><option>Dashboard</option><option>URL</option></select></div>
						<div class="col-span-2"><label class="nxg-label">{{ add.link_type === "URL" ? "URL" : "Name" }}</label><input v-if="add.link_type === 'URL'" v-model="add.url" class="nxg-input" placeholder="https://…" /><input v-else v-model="add.link_to" class="nxg-input" :placeholder="`${add.link_type} name`" /></div>
					</div>
				</template>
				<div><label class="nxg-label">Label</label><input v-model="add.label" class="nxg-input" /></div>
			</div>
			<template #footer><button class="nxg-btn nxg-btn-secondary" @click="add.open = false">Cancel</button><button class="nxg-btn nxg-btn-primary" :disabled="add.type === 'Link' ? !(add.link_to || add.url) : !add.label" @click="addItem">Add</button></template>
		</NxgDialog>
	</div>
</template>
