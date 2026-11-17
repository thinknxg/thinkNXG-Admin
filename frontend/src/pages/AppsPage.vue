<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import PageHeader from "@/components/ui/PageHeader.vue";
import NxgTabs from "@/components/ui/NxgTabs.vue";
import NxgDialog from "@/components/ui/NxgDialog.vue";
import NxgMultiSelect from "@/components/ui/NxgMultiSelect.vue";
import Icon from "@/components/ui/Icon.vue";
import { runAction, usePanel } from "@/data/api";
import { confirmAction } from "@/composables/useConfirm";

const apps = usePanel<any>("thinknxg_admin.api.apps.get_apps");
const tab = ref("apps");
const open = ref<string | null>(null);
const allModules = computed(() => (apps.state.data?.apps || []).flatMap((a: any) => a.modules.map((m: any) => m.name)).sort());
const totals = computed(() => {
	const list = apps.state.data?.apps || [];
	return { apps: list.length, modules: list.reduce((s: number, a: any) => s + a.modules.length, 0), doctypes: list.reduce((s: number, a: any) => s + a.modules.reduce((t: number, m: any) => t + m.doctypes, 0), 0) };
});

const prof = reactive({ open: false, create: false, name: "", blocked: [] as string[], users: 0 });
function openProfile(p?: any) {
	Object.assign(prof, p ? { open: true, create: false, name: p.name, blocked: [...p.blocked_modules], users: p.users } : { open: true, create: true, name: "", blocked: [], users: 0 });
}
async function saveProfile() {
	if (!prof.create && prof.users && !(await confirmAction({ title: `Update ${prof.name}?`, message: `Module visibility changes for its ${prof.users} user${prof.users === 1 ? "" : "s"} on their next page load.`, confirmLabel: "Save" }))) return;
	if (await runAction("thinknxg_admin.api.apps.save_module_profile", { name: prof.name, blocked_modules: prof.blocked, create: prof.create ? 1 : 0 }, "Module profile saved")) {
		prof.open = false;
		apps.load(true);
	}
}
</script>

<template>
	<div class="mx-auto w-full max-w-[1480px] px-4 pb-10 pt-6 sm:px-6">
		<PageHeader title="Apps & Modules" description="What is installed, what each app contributes, and who sees which modules.">
			<button class="nxg-icon-btn" aria-label="Reload" @click="apps.load(true)"><Icon name="refresh-cw" :size="15" :class="apps.state.loading && 'animate-spin'" /></button>
		</PageHeader>

		<div class="mb-4 grid grid-cols-1 gap-2 rounded-nxg border border-nxg-border bg-nxg-surface p-3 text-[12.5px] text-nxg-text-2 md:grid-cols-4">
			<div><b class="text-nxg-text">Installed</b>: added to the site with bench. Not changed from here.</div>
			<div><b class="text-nxg-text">Module visibility</b>: Module Profiles hide modules for the users assigned to them.</div>
			<div><b class="text-nxg-text">Role access</b>: what a role may open or edit, set in the <RouterLink to="/roles/matrix" class="nxg-link">permission matrix</RouterLink>.</div>
			<div><b class="text-nxg-text">Launcher</b>: desktop icons can be hidden in <RouterLink to="/workspaces" class="nxg-link">Workspaces</RouterLink>; hiding never uninstalls.</div>
		</div>

		<NxgTabs v-model="tab" class="mb-4" :tabs="[{ key: 'apps', label: 'Installed apps', count: totals.apps }, { key: 'profiles', label: 'Module profiles', count: apps.state.data?.module_profiles?.length ?? null }]" />
		<div v-if="apps.state.error" class="nxg-panel p-4 text-[13px] text-nxg-danger">{{ apps.state.error }} <button class="nxg-btn nxg-btn-secondary ml-2 h-7" @click="apps.load(true)">Retry</button></div>
		<div v-else-if="apps.state.loading && !apps.state.data" class="grid grid-cols-1 gap-3 md:grid-cols-2"><div v-for="i in 4" :key="i" class="nxg-skeleton h-28" /></div>

		<div v-else-if="tab === 'apps'" class="space-y-3">
			<p class="nxg-tnum text-[12.5px] text-nxg-text-2">{{ totals.apps }} apps · {{ totals.modules }} modules · {{ totals.doctypes }} DocTypes</p>
			<div v-for="a in apps.state.data?.apps || []" :key="a.name" class="nxg-panel">
				<button class="flex w-full items-center gap-3 px-4 py-3 text-left" :aria-expanded="open === a.name" @click="open = open === a.name ? null : a.name">
					<img v-if="a.logo" :src="a.logo" alt="" class="h-9 w-9 rounded-nxg border border-nxg-border object-cover" />
					<span v-else class="flex h-9 w-9 items-center justify-center rounded-nxg bg-nxg-surface-2"><Icon name="blocks" :size="17" /></span>
					<span class="min-w-0 flex-1">
						<span class="flex items-center gap-2"><span class="truncate text-[14.5px] font-semibold">{{ a.title }}</span><code class="text-[11.5px] text-nxg-text-3">{{ a.name }}</code></span>
						<span class="block truncate text-[12.5px] text-nxg-text-2">{{ a.description || a.publisher }}<template v-if="a.docs_url"> · <a :href="a.docs_url" target="_blank" rel="noopener" class="hover:underline" @click.stop>Documentation</a></template></span>
					</span>
					<span class="hidden text-right text-[12px] text-nxg-text-2 sm:block"><span class="nxg-tnum block font-medium text-nxg-text">{{ a.version || "—" }}</span>{{ a.branch || "" }}</span>
					<span class="nxg-tnum hidden w-24 text-right text-[12px] text-nxg-text-2 md:block">{{ a.modules.length }} module{{ a.modules.length === 1 ? "" : "s" }}<br />{{ a.icons.total - a.icons.hidden }}/{{ a.icons.total }} icons shown</span>
					<Icon :name="open === a.name ? 'chevron-down' : 'chevron-right'" :size="16" class="text-nxg-text-3" />
				</button>
				<div v-if="open === a.name" class="border-t border-nxg-border">
					<table class="w-full text-[13px]">
						<thead><tr class="border-b border-nxg-border"><th class="px-4 py-2 text-left nxg-micro">Module</th><th class="px-3 py-2 text-right nxg-micro">DocTypes</th><th class="px-3 py-2 text-left nxg-micro">Hidden by profiles</th><th class="px-3 py-2 text-right nxg-micro">Users with module blocked</th><th class="px-4 py-2" /></tr></thead>
						<tbody class="divide-y divide-nxg-border">
							<tr v-for="m in a.modules" :key="m.name">
								<td class="px-4 py-2 font-medium">{{ m.name }}<span v-if="m.custom" class="nxg-chip ml-2">Custom</span></td>
								<td class="nxg-tnum px-3 text-right">{{ m.doctypes }}</td>
								<td class="px-3"><span class="flex flex-wrap gap-1"><span v-for="p in m.blocked_in_profiles" :key="p" class="nxg-chip">{{ p }}</span><span v-if="!m.blocked_in_profiles.length" class="text-nxg-text-3">—</span></span></td>
								<td class="nxg-tnum px-3 text-right" :class="m.blocked_users ? '' : 'text-nxg-text-3'">{{ m.blocked_users || "—" }}</td>
								<td class="px-4 text-right"><a :href="$href(`/desk/module-def/${encodeURIComponent(m.name)}`)" class="nxg-btn nxg-btn-ghost h-7">Open<Icon name="external-link" :size="12" /></a></td>
							</tr>
							<tr v-if="!a.modules.length"><td colspan="5" class="px-4 py-4 text-nxg-text-2">This app defines no modules.</td></tr>
						</tbody>
					</table>
				</div>
			</div>
		</div>

		<div v-else>
			<div v-if="apps.state.data?.module_profiles === null" class="nxg-panel p-6 text-[13px] text-nxg-text-2">Module Profile is not available on this site.</div>
			<template v-else>
				<div class="mb-3 flex justify-end"><button class="nxg-btn nxg-btn-primary" @click="openProfile()"><Icon name="plus" :size="14" />New module profile</button></div>
				<div v-if="!apps.state.data?.module_profiles?.length" class="nxg-panel p-10 text-center text-[13px] text-nxg-text-2">No module profiles. Create one to hide modules, for example everything except HR for an HR team.</div>
				<div v-else class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
					<button v-for="p in apps.state.data.module_profiles" :key="p.name" class="nxg-panel flex flex-col gap-2 p-4 text-left hover:border-nxg-border-strong" @click="openProfile(p)">
						<div class="flex justify-between gap-2"><span class="truncate text-[14px] font-semibold">{{ p.name }}</span><span class="nxg-tnum text-[12px] text-nxg-text-2">{{ p.users }} user{{ p.users === 1 ? "" : "s" }}</span></div>
						<div class="text-[12px] text-nxg-text-2">Hides {{ p.blocked_modules.length }} module{{ p.blocked_modules.length === 1 ? "" : "s" }}</div>
						<div class="flex flex-wrap gap-1"><span v-for="m in p.blocked_modules.slice(0, 8)" :key="m" class="nxg-chip">{{ m }}</span><span v-if="p.blocked_modules.length > 8" class="nxg-chip">+{{ p.blocked_modules.length - 8 }}</span></div>
					</button>
				</div>
			</template>
		</div>

		<NxgDialog :open="prof.open" :title="prof.create ? 'New module profile' : prof.name" description="Modules listed here are hidden for users assigned this profile. Their roles still decide what they can open." width="max-w-[600px]" @close="prof.open = false">
			<div class="space-y-3 pb-2">
				<div v-if="prof.create"><label class="nxg-label">Profile name</label><input v-model="prof.name" class="nxg-input" placeholder="e.g. HR team" /></div>
				<div><label class="nxg-label">Hidden modules</label><NxgMultiSelect v-model="prof.blocked" :options="allModules" placeholder="Hide module" /></div>
			</div>
			<template #footer><button class="nxg-btn nxg-btn-secondary" @click="prof.open = false">Cancel</button><button class="nxg-btn nxg-btn-primary" :disabled="!prof.name.trim()" @click="saveProfile">Save</button></template>
		</NxgDialog>
	</div>
</template>
