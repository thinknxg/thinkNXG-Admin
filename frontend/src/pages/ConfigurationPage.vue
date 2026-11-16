<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { call, toast } from "frappe-ui";
import PageHeader from "@/components/ui/PageHeader.vue";
import NxgSwitch from "@/components/ui/NxgSwitch.vue";
import Icon from "@/components/ui/Icon.vue";
import { errorMessage, runAction, usePanel } from "@/data/api";
import { confirmAction } from "@/composables/useConfirm";

const API = "thinknxg_admin.api.configuration.";
const cfg = usePanel<any>(API + "get_configuration");
const active = ref("general");
const draft = reactive<Record<string, any>>({});
const saving = ref(false);
const search = ref("");

const groups = computed(() => cfg.state.data?.groups || []);
const sections = computed(() => [...groups.value.map((g: any) => ({ key: g.key, label: g.label })), { key: "logs", label: "Log retention" }, { key: "branding", label: "Branding" }]);
const current = computed(() => groups.value.find((g: any) => g.key === active.value));
const allFields = computed(() => groups.value.flatMap((g: any) => g.fields.map((f: any) => ({ ...f, group: g.label, groupKey: g.key }))));
const searchResults = computed(() => (search.value ? allFields.value.filter((f: any) => `${f.label} ${f.description || ""} ${f.fieldname}`.toLowerCase().includes(search.value.toLowerCase())) : []));

function val(f: any) {
	return f.fieldname in draft ? draft[f.fieldname] : f.value;
}
function set(f: any, v: any) {
	const same = String(v ?? "") === String(f.value ?? "") || (["Check"].includes(f.fieldtype) && Number(v || 0) === Number(f.value || 0));
	if (same) delete draft[f.fieldname];
	else draft[f.fieldname] = v;
}
const changes = computed(() => Object.keys(draft));
watch(() => cfg.state.data, () => Object.keys(draft).forEach((k) => delete draft[k]));

async function save() {
	const risky = allFields.value.filter((f: any) => f.risk && f.fieldname in draft && String(Number(draft[f.fieldname] || 0)) === String(f.risk.value));
	if (risky.length) {
		const ok = await confirmAction({ title: "Save security-sensitive changes?", message: risky.map((f: any) => `${f.label}: ${f.risk.message}`).join("  "), confirmLabel: "Save anyway", danger: true, typeToConfirm: risky.some((f: any) => f.fieldname === "disable_user_pass_login") ? "CONFIRM" : "" });
		if (!ok) return;
	}
	saving.value = true;
	try {
		cfg.state.data = await call(API + "save_configuration", { values: { ...draft }, modified: cfg.state.data.modified });
		toast.success(`Saved ${changes.value.length || ""} setting${changes.value.length === 1 ? "" : "s"}`.replace("  ", " "));
	} catch (e) {
		toast.error(errorMessage(e));
	} finally {
		saving.value = false;
	}
}
function discard() {
	Object.keys(draft).forEach((k) => delete draft[k]);
}

// Logs
const logDraft = ref<any[]>([]);
watch(() => cfg.state.data?.logs, (l) => (logDraft.value = (l || []).map((r: any) => ({ ...r }))), { immediate: true });
const logsDirty = computed(() => JSON.stringify(logDraft.value) !== JSON.stringify(cfg.state.data?.logs || []));
async function saveLogs() {
	const res = await runAction(API + "save_log_retention", { rows: logDraft.value }, "Log retention saved");
	if (res) cfg.state.data.logs = res;
}

// Branding
const brand = reactive({ product_name: "", show_classic_desk_link: true });
watch(() => cfg.state.data?.branding, (b) => b && Object.assign(brand, { product_name: b.product_name || "", show_classic_desk_link: !!b.show_classic_desk_link }), { immediate: true });
async function saveBrand() {
	if (await runAction(API + "save_branding", { product_name: brand.product_name, show_classic_desk_link: brand.show_classic_desk_link ? 1 : 0 }, "Branding saved. Reload to see it everywhere.")) cfg.load(true);
}
</script>

<template>
	<div class="mx-auto w-full max-w-[1280px] px-4 pb-24 pt-6 sm:px-6">
		<PageHeader title="System Configuration" description="Site-wide settings, grouped by purpose. Saved through System Settings, so the framework's own validation applies.">
			<div class="relative w-64"><Icon name="search" :size="15" class="pointer-events-none absolute left-2.5 top-2 text-nxg-text-3" /><input v-model="search" class="nxg-input pl-8" placeholder="Find a setting" aria-label="Find a setting" /></div>
			<a href="/desk/system-settings" class="nxg-btn nxg-btn-ghost">All settings<Icon name="external-link" :size="13" /></a>
		</PageHeader>

		<div v-if="cfg.state.error" class="nxg-panel p-4 text-[13px] text-nxg-danger">{{ cfg.state.error }} <button class="nxg-btn nxg-btn-secondary ml-2 h-7" @click="cfg.load(true)">Retry</button></div>
		<div v-else-if="cfg.state.loading && !cfg.state.data" class="grid grid-cols-[220px_1fr] gap-4"><div class="nxg-skeleton h-80" /><div class="nxg-skeleton h-[520px]" /></div>

		<div v-else class="grid grid-cols-1 gap-4 lg:grid-cols-[230px_1fr]">
			<nav class="nxg-panel h-fit p-1.5 lg:sticky lg:top-4" aria-label="Setting groups">
				<button v-for="s in sections" :key="s.key" class="flex h-9 w-full items-center justify-between rounded-nxg px-3 text-left text-[13px]" :class="active === s.key && !search ? 'bg-nxg-surface-2 font-medium' : 'text-nxg-text-2 hover:bg-nxg-surface-2 hover:text-nxg-text'" @click="active = s.key; search = ''">
					{{ s.label }}
					<span v-if="groups.find((g: any) => g.key === s.key)?.fields.some((f: any) => f.fieldname in draft)" class="h-1.5 w-1.5 rounded-full bg-nxg-red" aria-label="Unsaved changes" />
				</button>
			</nav>

			<section class="nxg-panel min-w-0">
				<template v-if="search || current">
					<header class="border-b border-nxg-border px-5 py-4">
						<h2 class="text-[16px] font-semibold">{{ search ? `Results for “${search}”` : current.label }}</h2>
						<p class="text-[13px] text-nxg-text-2">{{ search ? `${searchResults.length} setting${searchResults.length === 1 ? "" : "s"}` : current.description }}</p>
					</header>
					<div class="divide-y divide-nxg-border">
						<div v-for="f in search ? searchResults : current.fields" :key="f.fieldname" class="grid grid-cols-1 gap-2 px-5 py-3.5 md:grid-cols-[1fr_320px] md:items-center">
							<div class="min-w-0">
								<label :for="`cfg-${f.fieldname}`" class="flex items-center gap-2 text-[13.5px] font-medium">{{ f.label }}<span v-if="f.fieldname in draft" class="nxg-chip">Changed</span><span v-if="search" class="text-[11.5px] font-normal text-nxg-text-3">{{ f.group }}</span></label>
								<p v-if="f.description" class="mt-0.5 text-[12.5px] text-nxg-text-2">{{ f.description }}</p>
								<p v-if="f.risk && String(Number(val(f) || 0)) === String(f.risk.value)" class="mt-1 flex items-start gap-1.5 text-[12px] text-nxg-warning"><Icon name="triangle-alert" :size="13" class="mt-0.5" />{{ f.risk.message }}</p>
							</div>
							<div class="md:justify-self-end md:w-full">
								<div v-if="f.fieldtype === 'Check'" class="flex md:justify-end"><NxgSwitch :model-value="!!Number(val(f) || 0)" :label="f.label" @update:model-value="(v) => set(f, v ? 1 : 0)" /></div>
								<select v-else-if="f.fieldtype === 'Select'" :id="`cfg-${f.fieldname}`" class="nxg-input" :value="val(f) ?? ''" @change="set(f, ($event.target as HTMLSelectElement).value)"><option v-for="o in f.options" :key="o" :value="o">{{ o || "—" }}</option></select>
								<textarea v-else-if="f.fieldtype === 'Small Text' || f.fieldtype === 'Text'" :id="`cfg-${f.fieldname}`" class="nxg-input h-auto py-2" rows="2" :value="val(f) ?? ''" @input="set(f, ($event.target as HTMLTextAreaElement).value)" />
								<input v-else-if="f.fieldtype === 'Int'" :id="`cfg-${f.fieldname}`" type="number" min="0" class="nxg-input" :value="val(f) ?? ''" @input="set(f, ($event.target as HTMLInputElement).value === '' ? null : Number(($event.target as HTMLInputElement).value))" />
								<input v-else :id="`cfg-${f.fieldname}`" class="nxg-input" :placeholder="f.fieldname === 'session_expiry' ? 'HH:mm, e.g. 06:00' : ''" :value="val(f) ?? ''" @input="set(f, ($event.target as HTMLInputElement).value)" />
							</div>
						</div>
						<p v-if="search && !searchResults.length" class="px-5 py-8 text-center text-[13px] text-nxg-text-2">No setting matches. Try <a href="/desk/system-settings" class="nxg-link">all System Settings</a>.</p>
					</div>
				</template>

				<template v-else-if="active === 'logs'">
					<header class="border-b border-nxg-border px-5 py-4"><h2 class="text-[16px] font-semibold">Log retention</h2><p class="text-[13px] text-nxg-text-2">How many days each log is kept before the framework clears it. Audit evidence lives in these logs, so check your retention policy before shortening.</p></header>
					<div class="divide-y divide-nxg-border">
						<div v-for="r in logDraft" :key="r.ref_doctype" class="flex items-center justify-between gap-3 px-5 py-2.5 text-[13.5px]"><span>{{ r.ref_doctype }}</span><span class="flex items-center gap-2"><input v-model.number="r.days" type="number" min="1" class="nxg-input w-24 text-right" :aria-label="`Days to keep ${r.ref_doctype}`" /><span class="text-[12.5px] text-nxg-text-2">days</span></span></div>
						<p v-if="!logDraft.length" class="px-5 py-6 text-[13px] text-nxg-text-2">No log types configured in Log Settings.</p>
					</div>
					<div class="flex justify-end gap-2 border-t border-nxg-border px-5 py-3"><button class="nxg-btn nxg-btn-primary" :disabled="!logsDirty" @click="saveLogs">Save retention</button></div>
				</template>

				<template v-else>
					<header class="border-b border-nxg-border px-5 py-4"><h2 class="text-[16px] font-semibold">Branding</h2><p class="text-[13px] text-nxg-text-2">How the Command Center names this product. The thinkNXG mark comes from thinkNXG Core.</p></header>
					<div class="space-y-4 px-5 py-4">
						<div class="flex items-center gap-3"><img :src="cfg.state.data?.branding?.app_logo || '/assets/frappe/images/thinkNXG-favicon.png'" alt="" class="h-12 w-12 rounded-nxg border border-nxg-border" /><div class="text-[12.5px] text-nxg-text-2">Desk logo is set in <a href="/desk/navbar-settings" class="nxg-link">Navbar Settings</a>.</div></div>
						<div class="max-w-md"><label class="nxg-label" for="brand-name">Product name</label><input id="brand-name" v-model="brand.product_name" class="nxg-input" placeholder="thinkNXG ERP" /></div>
						<div class="flex max-w-md items-center justify-between rounded-nxg border border-nxg-border px-3 py-2.5"><div><div class="text-[13px] font-medium">Show “Classic Desk” link</div><div class="text-[12px] text-nxg-text-2">In the app switcher and command palette.</div></div><NxgSwitch v-model="brand.show_classic_desk_link" label="Show Classic Desk link" /></div>
						<button class="nxg-btn nxg-btn-primary" @click="saveBrand">Save branding</button>
					</div>
				</template>
			</section>
		</div>

		<transition enter-active-class="transition duration-150" enter-from-class="translate-y-4 opacity-0" leave-active-class="transition duration-100" leave-to-class="translate-y-4 opacity-0">
			<div v-if="changes.length" class="fixed inset-x-0 bottom-4 z-40 mx-auto flex w-fit items-center gap-3 rounded-nxg-lg border border-nxg-border bg-nxg-surface px-4 py-2.5 shadow-e3" role="status">
				<span class="text-[13px]"><b>{{ changes.length }}</b> unsaved change{{ changes.length === 1 ? "" : "s" }}</span>
				<button class="nxg-btn nxg-btn-ghost" @click="discard">Discard</button>
				<button class="nxg-btn nxg-btn-primary" :disabled="saving" @click="save">{{ saving ? "Saving…" : "Save changes" }}</button>
			</div>
		</transition>
	</div>
</template>
