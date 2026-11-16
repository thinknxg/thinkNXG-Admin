<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { call, toast } from "frappe-ui";
import PageHeader from "@/components/ui/PageHeader.vue";
import NxgAvatar from "@/components/ui/NxgAvatar.vue";
import NxgSwitch from "@/components/ui/NxgSwitch.vue";
import NxgDrawer from "@/components/ui/NxgDrawer.vue";
import NxgEmpty from "@/components/ui/NxgEmpty.vue";
import NxgTabs from "@/components/ui/NxgTabs.vue";
import Icon from "@/components/ui/Icon.vue";
import { errorMessage, runAction } from "@/data/api";
import { fmtDateTime, parseFrappe, timeAgo } from "@/composables/format";

const API = "thinknxg_admin.api.notifications.";
const CORE = "frappe.desk.doctype.notification_log.notification_log.";
const type = ref("");
const category = ref("");
const categoryTabs = computed(() => [
	{ key: "", label: "All", count: meta.value?.unread || null },
	...(meta.value?.categories || ["Approvals", "Finance", "Operations", "People", "System"]).map((c: string) => ({ key: c, label: c, count: meta.value?.unread_by_category?.[c] || null })),
]);
const unreadOnly = ref(false);
const rows = ref<any[]>([]);
const meta = ref<any>(null);
const loading = ref(false);
const error = ref<string | null>(null);
const start = ref(0);
const PAGE = 30;

async function load(append = false) {
	loading.value = true;
	error.value = null;
	try {
		const res: any = await call(API + "list_notifications", { type: type.value, category: category.value || null, unread_only: unreadOnly.value ? 1 : 0, start: append ? start.value : 0, page_length: PAGE });
		if (res === null) {
			meta.value = { unavailable: true };
			return;
		}
		if (!append) start.value = 0;
		rows.value = append ? [...rows.value, ...res.rows] : res.rows;
		meta.value = res;
	} catch (e) {
		error.value = errorMessage(e);
	} finally {
		loading.value = false;
	}
}
watch([type, category, unreadOnly], () => load());
onMounted(() => load());
function more() {
	start.value += PAGE;
	load(true);
}

/** Group by Today / Yesterday / date for scanning. */
const groups = computed(() => {
	const out: { label: string; items: any[] }[] = [];
	const today = new Date();
	today.setHours(0, 0, 0, 0);
	for (const r of rows.value) {
		const d = parseFrappe(r.creation);
		const day = d ? new Date(d.getFullYear(), d.getMonth(), d.getDate()) : today;
		const diff = Math.round((today.getTime() - day.getTime()) / 86400000);
		const label = diff <= 0 ? "Today" : diff === 1 ? "Yesterday" : day.toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "short" });
		let g = out.find((x) => x.label === label);
		if (!g) out.push((g = { label, items: [] }));
		g.items.push(r);
	}
	return out;
});

async function markRead(r: any) {
	if (r.read) return;
	r.read = 1;
	try {
		await call(CORE + "mark_as_read", { docname: r.name });
		if (meta.value) meta.value.unread = Math.max(0, meta.value.unread - 1);
	} catch (e) {
		r.read = 0;
		toast.error(errorMessage(e));
	}
}
async function open(r: any) {
	await markRead(r);
	if (r.route) window.location.href = r.route;
}
async function markAll() {
	if (await runAction(CORE + "mark_all_as_read", {}, "All notifications marked as read")) load();
}
const typeIcon: Record<string, string> = { Mention: "user", Assignment: "list-checks", Share: "users", Alert: "bell", "Energy Point": "sparkles" };

// Settings
const settingsOpen = ref(false);
const settings = ref<any>(null);
async function openSettings() {
	settingsOpen.value = true;
	try {
		settings.value = await call(API + "get_settings");
	} catch (e) {
		toast.error(errorMessage(e));
	}
}
async function saveSettings() {
	const res = await runAction(API + "update_settings", { values: settings.value }, "Notification settings saved");
	if (res) settings.value = res;
}
const settingRows = [
	["enabled", "Notifications", "Receive in-app notifications"],
	["enable_email_notifications", "Email notifications", "Also send notifications by email"],
	["enable_email_mention", "Mentions", "Email me when someone mentions me"],
	["enable_email_assignment", "Assignments", "Email me when a document is assigned to me"],
	["enable_email_share", "Shares", "Email me when a document is shared with me"],
	["enable_email_event_reminders", "Event reminders", "Email reminders for calendar events"],
	["enable_email_threads_on_assigned_document", "Threads on assigned documents", "Email replies on documents assigned to me"],
];
</script>

<template>
	<div class="mx-auto w-full max-w-[960px] px-4 pb-10 pt-6 sm:px-6">
		<PageHeader title="Notifications" description="Approvals, mentions, assignments and alerts from every command center, sent to you.">
			<button class="nxg-btn nxg-btn-secondary" :disabled="!meta?.unread" @click="markAll"><Icon name="check" :size="14" />Mark all read</button>
			<button class="nxg-btn nxg-btn-secondary" @click="openSettings"><Icon name="settings" :size="14" />Settings</button>
		</PageHeader>

		<div v-if="meta?.unavailable" class="nxg-panel p-8 text-center text-[13px] text-nxg-text-2">Notifications are not available on this site.</div>
		<div v-else class="nxg-panel">
			<div class="px-3 pt-1"><NxgTabs :tabs="categoryTabs" :model-value="category" @update:model-value="(v: string) => (category = v)" /></div>
			<div class="flex flex-wrap items-center gap-2 border-b border-nxg-border p-3">
				<div class="flex flex-wrap gap-1" role="group" aria-label="Notification type">
					<button class="h-7 rounded-nxg-sm px-2.5 text-[12.5px] font-medium" :class="!type ? 'bg-nxg-primary text-nxg-primary-fg' : 'text-nxg-text-2 hover:bg-nxg-surface-2'" @click="type = ''">All<span v-if="meta?.unread" class="nxg-tnum ml-1 opacity-80">{{ meta.unread }}</span></button>
					<button v-for="t in meta?.types || []" :key="t" class="inline-flex h-7 items-center gap-1 rounded-nxg-sm px-2.5 text-[12.5px] font-medium" :class="type === t ? 'bg-nxg-primary text-nxg-primary-fg' : 'text-nxg-text-2 hover:bg-nxg-surface-2'" @click="type = t">
						<Icon :name="typeIcon[t] || 'bell'" :size="13" />{{ t }}<span v-if="meta?.unread_by_type?.[t]" class="nxg-tnum opacity-80">{{ meta.unread_by_type[t] }}</span>
					</button>
				</div>
				<label class="ml-auto flex items-center gap-2 text-[12.5px] text-nxg-text-2"><NxgSwitch v-model="unreadOnly" label="Unread only" />Unread only</label>
			</div>
			<div v-if="error" class="p-4 text-[13px] text-nxg-danger">{{ error }} <button class="nxg-btn nxg-btn-secondary ml-2 h-7" @click="load()">Retry</button></div>
			<div v-else-if="loading && !rows.length" class="space-y-3 p-4"><div v-for="i in 6" :key="i" class="nxg-skeleton h-12" /></div>
			<NxgEmpty v-else-if="!rows.length" :text="unreadOnly ? 'No unread notifications' : 'No notifications yet'" icon="bell" />
			<div v-else>
				<section v-for="g in groups" :key="g.label">
					<h2 class="sticky top-0 z-[1] border-b border-nxg-border bg-nxg-surface-2/80 px-4 py-1.5 backdrop-blur nxg-micro">{{ g.label }}</h2>
					<ul class="divide-y divide-nxg-border">
						<li v-for="n in g.items" :key="n.name" class="group flex items-start gap-3 px-4 py-3 transition-colors hover:bg-nxg-surface-2/60">
							<div class="relative">
								<NxgAvatar :name="n.from_name" :image="n.from_image" :size="32" />
								<span class="absolute -bottom-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-nxg-surface ring-1 ring-nxg-border"><Icon :name="typeIcon[n.type] || 'bell'" :size="10" /></span>
							</div>
							<button class="min-w-0 flex-1 text-left" @click="open(n)">
								<p class="text-[13.5px] leading-5" :class="n.read ? 'text-nxg-text-2' : 'font-medium text-nxg-text'">{{ n.subject }}</p>
								<p class="mt-0.5 text-[12px] text-nxg-text-3"><span v-if="n.category && !category">{{ n.category }} · </span><span v-if="n.type">{{ n.type }} · </span><span v-if="n.document_type">{{ n.document_type }} {{ n.document_name }} · </span><span :title="fmtDateTime(n.creation)">{{ timeAgo(n.creation) }}</span></p>
							</button>
							<button v-if="!n.read" class="nxg-btn nxg-btn-ghost h-7 shrink-0 px-2 text-[12px] opacity-0 group-hover:opacity-100 focus:opacity-100" @click="markRead(n)">Mark read</button>
							<span v-if="!n.read" class="mt-2 h-2 w-2 shrink-0 rounded-full bg-nxg-red" aria-label="Unread" />
						</li>
					</ul>
				</section>
				<div v-if="meta && rows.length < meta.total" class="border-t border-nxg-border p-3 text-center"><button class="nxg-btn nxg-btn-secondary" :disabled="loading" @click="more">{{ loading ? "Loading…" : "Load more" }}</button></div>
			</div>
		</div>

		<NxgDrawer :open="settingsOpen" title="Notification settings" subtitle="Applies to your account only" width="max-w-[480px]" @close="settingsOpen = false">
			<div v-if="!settings" class="space-y-3 p-5"><div v-for="i in 6" :key="i" class="nxg-skeleton h-10" /></div>
			<div v-else class="space-y-2 p-5">
				<div v-for="[key, label, hint] in settingRows" :key="key" class="flex items-center justify-between gap-3 rounded-nxg border border-nxg-border px-3 py-2.5" :class="key !== 'enabled' && key !== 'enable_email_notifications' && !settings.enable_email_notifications && 'opacity-50'">
					<div><div class="text-[13px] font-medium">{{ label }}</div><div class="text-[12px] text-nxg-text-2">{{ hint }}</div></div>
					<NxgSwitch :model-value="!!settings[key]" :label="label" @update:model-value="(v) => (settings[key] = v ? 1 : 0)" />
				</div>
			</div>
			<template #footer><button class="nxg-btn nxg-btn-secondary" @click="settingsOpen = false">Close</button><button class="nxg-btn nxg-btn-primary" :disabled="!settings" @click="saveSettings">Save</button></template>
		</NxgDrawer>
	</div>
</template>
