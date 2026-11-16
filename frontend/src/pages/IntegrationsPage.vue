<script setup lang="ts">
import { nav } from "@/lib/links";
import { computed, ref, watch } from "vue";
import { call } from "frappe-ui";
import PageHeader from "@/components/ui/PageHeader.vue";
import NxgTabs from "@/components/ui/NxgTabs.vue";
import DataTable from "@/components/ui/DataTable.vue";
import NxgStatus from "@/components/ui/NxgStatus.vue";
import NxgSwitch from "@/components/ui/NxgSwitch.vue";
import NxgDrawer from "@/components/ui/NxgDrawer.vue";
import NxgEmpty from "@/components/ui/NxgEmpty.vue";
import Icon from "@/components/ui/Icon.vue";
import { errorMessage, runAction, usePanel } from "@/data/api";
import { confirmAction } from "@/composables/useConfirm";
import { fmtDateTime, fmtNumber, timeAgo } from "@/composables/format";

const API = "thinknxg_admin.api.integrations.";
const ov = usePanel<any>(API + "get_overview");
const tab = ref("webhooks");
const d = computed(() => ov.state.data || {});

function health(h: any) {
	if (!h.enabled) return { s: "unknown", l: "Disabled" };
	if (h.failed_24h) return { s: "critical", l: `${h.failed_24h} failed (24 h)` };
	if (h.failed_7d) return { s: "warning", l: `${h.failed_7d} failed (7 d)` };
	if (!h.calls_7d) return { s: "info", l: "No calls (7 d)" };
	return { s: "ok", l: "Delivering" };
}
async function toggleWebhook(h: any, on: boolean) {
	if (!on && !(await confirmAction({ title: `Disable webhook for ${h.webhook_doctype}?`, message: "Events stop being sent to this endpoint until it is enabled again.", confirmLabel: "Disable", danger: true }))) return;
	const prev = h.enabled;
	h.enabled = on ? 1 : 0;
	if (!(await runAction(API + "set_webhook_enabled", { name: h.name, enabled: h.enabled }, on ? "Webhook enabled" : "Webhook disabled"))) h.enabled = prev;
}
async function toggleSocial(s: any, on: boolean) {
	const prev = s.enable_social_login;
	s.enable_social_login = on ? 1 : 0;
	if (!(await runAction(API + "set_social_login_enabled", { name: s.name, enabled: s.enable_social_login }, on ? "Sign-in provider enabled" : "Sign-in provider disabled"))) s.enable_social_login = prev;
}

// Logs drawer / tab
const logsFor = ref<string | null>(null);
const onlyErrors = ref(false);
const logs = ref<any>(null);
const logsLoading = ref(false);
async function loadLogs() {
	logsLoading.value = true;
	try {
		logs.value = await call(API + "list_webhook_logs", { webhook: logsFor.value || undefined, only_errors: onlyErrors.value ? 1 : 0 });
	} catch (e) {
		logs.value = { error: errorMessage(e) };
	} finally {
		logsLoading.value = false;
	}
}
watch([logsFor, onlyErrors], () => (logsFor.value !== null || tab.value === "logs") && loadLogs());
watch(tab, (t) => {
	if (t === "logs") {
		logsFor.value = null;
		loadLogs();
		loadIR();
	}
});
const ir = ref<any>(null);
const irStatus = ref("");
async function loadIR() {
	try {
		ir.value = await call(API + "list_integration_requests", { status: irStatus.value || undefined });
	} catch (e) {
		ir.value = { error: errorMessage(e) };
	}
}
watch(irStatus, loadIR);
const irSummary = computed(() => {
	const out: Record<string, Record<string, number>> = {};
	for (const r of d.value.integration_requests || []) (out[r.service] ||= {})[r.status || "Unknown"] = r.n;
	return out;
});
function openEmail(r: any) {
	nav(`/desk/email-account/${encodeURIComponent(r.name)}`);
}
const statusTone: Record<string, string> = { Completed: "success", Authorized: "success", Queued: "info", Failed: "failed", Cancelled: "unknown" };
</script>

<template>
	<div class="mx-auto w-full max-w-[1480px] px-4 pb-10 pt-6 sm:px-6">
		<PageHeader title="Integrations" description="Webhooks, email, OAuth and connected apps, API keys and integration traffic. Secrets are never shown here.">
			<a :href="$href('/desk/webhook/new')" class="nxg-btn nxg-btn-secondary"><Icon name="plus" :size="14" />Webhook</a>
			<button class="nxg-icon-btn" aria-label="Reload" @click="ov.load(true)"><Icon name="refresh-cw" :size="15" :class="ov.state.loading && 'animate-spin'" /></button>
		</PageHeader>

		<NxgTabs v-model="tab" class="mb-4" :tabs="[{ key: 'webhooks', label: 'Webhooks', count: d.webhooks?.length }, { key: 'email', label: 'Email', count: d.email_accounts?.length }, { key: 'oauth', label: 'OAuth & connected apps' }, { key: 'api', label: 'API access', count: d.api_users?.length }, { key: 'logs', label: 'Request logs' }]" />
		<div v-if="ov.state.error" class="nxg-panel p-4 text-[13px] text-nxg-danger">{{ ov.state.error }} <button class="nxg-btn nxg-btn-secondary ml-2 h-7" @click="ov.load(true)">Retry</button></div>
		<div v-else-if="ov.state.loading && !ov.state.data" class="space-y-2"><div v-for="i in 5" :key="i" class="nxg-skeleton h-12" /></div>

		<div v-else-if="tab === 'webhooks'" class="nxg-panel">
			<NxgEmpty v-if="!d.webhooks?.length" :text="d.webhooks === null ? 'Webhooks are not available on this site' : 'No webhooks configured'" icon="plug" />
			<DataTable v-else :columns="[{ key: 'webhook_doctype', label: 'Trigger' }, { key: 'request_url', label: 'Endpoint' }, { key: 'calls_7d', label: 'Calls (7 d)', align: 'right' }, { key: 'last_call', label: 'Last call' }, { key: 'health', label: 'Health' }, { key: 'enabled', label: 'Enabled', align: 'right' }]" :rows="d.webhooks" clickable @row-click="(r) => (logsFor = r.name)">
				<template #cell-webhook_doctype="{ row }"><span class="font-medium">{{ row.webhook_doctype }}</span> <span class="text-nxg-text-2">· {{ row.webhook_docevent }}</span></template>
				<template #cell-request_url="{ row }"><span class="flex items-center gap-1.5"><span class="nxg-chip">{{ row.request_method }}</span><span class="max-w-[280px] truncate font-mono text-[12px]" :title="row.request_url">{{ row.request_url || "—" }}</span><Icon v-if="row.enable_security" name="shield-check" :size="13" class="text-nxg-success" title="Signed with a secret" /></span></template>
				<template #cell-calls_7d="{ row }"><span class="nxg-tnum">{{ row.calls_7d }}</span></template>
				<template #cell-last_call="{ row }"><span class="text-nxg-text-2">{{ row.last_call ? timeAgo(row.last_call) : "—" }}</span></template>
				<template #cell-health="{ row }"><NxgStatus :status="health(row).s" :label="health(row).l" /></template>
				<template #cell-enabled="{ row }"><span @click.stop><NxgSwitch :model-value="!!row.enabled" :label="`Enable webhook ${row.name}`" @update:model-value="(v) => toggleWebhook(row, v)" /></span></template>
			</DataTable>
		</div>

		<div v-else-if="tab === 'email'" class="space-y-4">
			<div class="grid grid-cols-3 gap-3">
				<div class="nxg-panel px-4 py-3"><div class="text-[12px] text-nxg-text-2">Sent (24 h)</div><div class="nxg-tnum text-[20px] font-semibold">{{ fmtNumber(d.email_queue?.sent_24h) }}</div></div>
				<div class="nxg-panel px-4 py-3"><div class="text-[12px] text-nxg-text-2">Waiting to send</div><div class="nxg-tnum text-[20px] font-semibold">{{ fmtNumber(d.email_queue?.pending) }}</div></div>
				<a :href="$href('/desk/email-queue?status=Error')" class="nxg-panel px-4 py-3 hover:border-nxg-border-strong"><div class="text-[12px] text-nxg-text-2">Errors (24 h)</div><div class="nxg-tnum text-[20px] font-semibold" :class="d.email_queue?.errors_24h && 'text-nxg-danger'">{{ fmtNumber(d.email_queue?.errors_24h) }}</div></a>
			</div>
			<div class="nxg-panel">
				<NxgEmpty v-if="!d.email_accounts?.length" text="No email accounts" icon="inbox"><a :href="$href('/desk/email-account/new')" class="nxg-btn nxg-btn-secondary mt-2 h-7">Add email account</a></NxgEmpty>
				<DataTable v-else :columns="[{ key: 'email_account_name', label: 'Account' }, { key: 'service', label: 'Service' }, { key: 'flow', label: 'Direction' }, { key: 'sent_7d', label: 'Sent (7 d)', align: 'right' }, { key: 'errors_7d', label: 'Errors (7 d)', align: 'right' }, { key: 'pending', label: 'Pending', align: 'right' }]" :rows="d.email_accounts" clickable @row-click="openEmail">
					<template #cell-email_account_name="{ row }"><span class="font-medium">{{ row.email_account_name || row.name }}</span><span class="block text-[12px] text-nxg-text-2">{{ row.email_id }}</span></template>
					<template #cell-flow="{ row }"><span class="flex flex-wrap gap-1"><span v-if="row.enable_incoming" class="nxg-chip">Incoming{{ row.default_incoming ? " · default" : "" }}</span><span v-if="row.enable_outgoing" class="nxg-chip">Outgoing{{ row.default_outgoing ? " · default" : "" }}</span><span v-if="!row.enable_incoming && !row.enable_outgoing" class="text-nxg-text-3">Inactive</span></span></template>
					<template #cell-errors_7d="{ row }"><span class="nxg-tnum" :class="row.errors_7d && 'font-medium text-nxg-danger'">{{ row.errors_7d }}</span></template>
				</DataTable>
			</div>
		</div>

		<div v-else-if="tab === 'oauth'" class="grid grid-cols-1 gap-4 xl:grid-cols-2">
			<section class="nxg-panel">
				<header class="flex items-center justify-between border-b border-nxg-border px-4 py-3"><div><h2 class="text-[15px] font-semibold">OAuth clients</h2><p class="text-[12.5px] text-nxg-text-2">Apps allowed to sign in users of this site and call its API</p></div><a :href="$href('/desk/oauth-client/new')" class="nxg-btn nxg-btn-ghost h-7">New</a></header>
				<NxgEmpty v-if="!d.oauth_clients?.length" text="No OAuth clients" icon="key-round" />
				<ul v-else class="divide-y divide-nxg-border"><li v-for="c in d.oauth_clients" :key="c.name" class="flex items-center gap-3 px-4 py-2.5 text-[13px]"><a :href="$href(`/desk/oauth-client/${encodeURIComponent(c.name)}`)" class="min-w-0 flex-1"><span class="block truncate font-medium hover:underline">{{ c.app_name }}</span><span class="block truncate text-[12px] text-nxg-text-2">{{ c.grant_type }} · {{ c.scopes.join(", ") || "no scopes" }} · {{ c.redirect || "no redirect" }}</span></a><span class="nxg-tnum text-[12px] text-nxg-text-2">{{ c.active_tokens }} active token{{ c.active_tokens === 1 ? "" : "s" }}</span></li></ul>
			</section>
			<section class="nxg-panel">
				<header class="flex items-center justify-between border-b border-nxg-border px-4 py-3"><div><h2 class="text-[15px] font-semibold">Connected apps</h2><p class="text-[12.5px] text-nxg-text-2">External services this site signs in to</p></div><a :href="$href('/desk/connected-app/new')" class="nxg-btn nxg-btn-ghost h-7">New</a></header>
				<NxgEmpty v-if="!d.connected_apps?.length" text="No connected apps" icon="plug" />
				<ul v-else class="divide-y divide-nxg-border"><li v-for="a in d.connected_apps" :key="a.name" class="flex items-center gap-3 px-4 py-2.5 text-[13px]"><a :href="$href(`/desk/connected-app/${encodeURIComponent(a.name)}`)" class="min-w-0 flex-1"><span class="block truncate font-medium hover:underline">{{ a.provider_name || a.name }}</span><span class="block truncate text-[12px] text-nxg-text-2">{{ a.authorization_uri || "—" }}</span></a><span class="nxg-tnum text-[12px] text-nxg-text-2">{{ a.connected_users }} user{{ a.connected_users === 1 ? "" : "s" }} connected</span></li></ul>
			</section>
			<section class="nxg-panel xl:col-span-2">
				<header class="border-b border-nxg-border px-4 py-3"><h2 class="text-[15px] font-semibold">Social sign-in providers</h2></header>
				<NxgEmpty v-if="!d.social_logins?.length" text="No sign-in providers configured" icon="user" />
				<ul v-else class="divide-y divide-nxg-border"><li v-for="s in d.social_logins" :key="s.name" class="flex items-center gap-3 px-4 py-2.5 text-[13px]"><span class="flex-1 font-medium">{{ s.provider_name || s.social_login_provider }}</span><span class="text-[12px] text-nxg-text-2">{{ s.sign_ups || "Allow sign-ups: default" }}</span><NxgSwitch :model-value="!!s.enable_social_login" :label="`Enable ${s.provider_name}`" @update:model-value="(v) => toggleSocial(s, v)" /></li></ul>
			</section>
		</div>

		<div v-else-if="tab === 'api'" class="nxg-panel">
			<div class="border-b border-nxg-border px-4 py-3 text-[12.5px] text-nxg-text-2">Users holding an API key. Issue or rotate keys from the user's Security tab in <RouterLink to="/users" class="nxg-link">Users</RouterLink>. {{ d.api_requests_24h !== null ? `${fmtNumber(d.api_requests_24h)} logged API requests in the last 24 h.` : "" }}</div>
			<NxgEmpty v-if="!d.api_users?.length" text="No users have API keys" icon="key-round" />
			<DataTable v-else :columns="[{ key: 'full_name', label: 'User' }, { key: 'api_key', label: 'API key' }, { key: 'last_request', label: 'Last logged request' }, { key: 'enabled', label: 'Account' }]" :rows="d.api_users" clickable @row-click="(r) => $router.push({ path: '/users', query: { user: r.name } })">
				<template #cell-full_name="{ row }"><span class="font-medium">{{ row.full_name }}</span><span class="block text-[12px] text-nxg-text-2">{{ row.name }}</span></template>
				<template #cell-api_key="{ row }"><code class="text-[12px]">{{ row.api_key }}</code></template>
				<template #cell-last_request="{ row }"><span class="text-nxg-text-2">{{ row.last_request ? timeAgo(row.last_request) : "—" }}</span></template>
				<template #cell-enabled="{ row }"><NxgStatus :status="row.enabled ? 'ok' : 'warning'" :label="row.enabled ? 'Enabled' : 'Disabled user with key'" /></template>
			</DataTable>
		</div>

		<div v-else class="space-y-4">
			<section class="nxg-panel">
				<header class="flex flex-wrap items-center gap-3 border-b border-nxg-border px-4 py-3"><h2 class="flex-1 text-[15px] font-semibold">Webhook deliveries</h2><label class="flex items-center gap-2 text-[12.5px] text-nxg-text-2"><NxgSwitch v-model="onlyErrors" label="Errors only" />Errors only</label></header>
				<div v-if="logsLoading && !logs" class="space-y-2 p-4"><div v-for="i in 5" :key="i" class="nxg-skeleton h-8" /></div>
				<NxgEmpty v-else-if="logs === null" text="Webhook logs are not available" />
				<DataTable v-else :columns="[{ key: 'creation', label: 'When' }, { key: 'webhook', label: 'Webhook' }, { key: 'reference_document', label: 'Document' }, { key: 'url', label: 'Endpoint' }, { key: 'result', label: 'Result' }]" :rows="logs?.rows || []" empty-text="No deliveries recorded">
					<template #cell-creation="{ row }"><span class="whitespace-nowrap text-nxg-text-2" :title="fmtDateTime(row.creation)">{{ timeAgo(row.creation) }}</span></template>
					<template #cell-reference_document="{ row }"><span class="text-nxg-text-2">{{ row.reference_doctype }}</span> {{ row.reference_document }}</template>
					<template #cell-url="{ row }"><span class="block max-w-[260px] truncate font-mono text-[12px]">{{ row.url }}</span></template>
					<template #cell-result="{ row }"><a :href="row.route" class="flex items-center gap-2"><NxgStatus :status="row.error ? 'failed' : 'success'" :label="row.error ? 'Failed' : 'Delivered'" /><span v-if="row.error" class="max-w-[260px] truncate text-[12px] text-nxg-text-2" :title="row.error">{{ row.error }}</span></a></template>
				</DataTable>
			</section>
			<section class="nxg-panel">
				<header class="flex flex-wrap items-center gap-3 border-b border-nxg-border px-4 py-3"><h2 class="flex-1 text-[15px] font-semibold">Integration requests</h2><select v-model="irStatus" class="nxg-input w-auto" aria-label="Status"><option value="">Any status</option><option v-for="s in ['Queued', 'Authorized', 'Completed', 'Cancelled', 'Failed']" :key="s">{{ s }}</option></select></header>
				<div v-if="Object.keys(irSummary).length" class="flex flex-wrap gap-2 border-b border-nxg-border px-4 py-2.5 text-[12.5px]"><span v-for="(st, svc) in irSummary" :key="svc" class="rounded-nxg border border-nxg-border px-2 py-1"><b>{{ svc }}</b> <span class="text-nxg-text-2">{{ Object.entries(st).map(([k, v]) => `${v} ${k.toLowerCase()}`).join(" · ") }}</span> <span class="text-nxg-text-3">(7 d)</span></span></div>
				<NxgEmpty v-if="ir === null" text="Integration Request is not available" />
				<DataTable v-else :columns="[{ key: 'creation', label: 'When' }, { key: 'integration_request_service', label: 'Service' }, { key: 'reference', label: 'Document' }, { key: 'status', label: 'Status' }]" :rows="ir?.rows || []" empty-text="No integration requests">
					<template #cell-creation="{ row }"><span class="whitespace-nowrap text-nxg-text-2">{{ timeAgo(row.creation) }}</span></template>
					<template #cell-reference="{ row }"><a :href="row.route" class="nxg-link">{{ row.reference_doctype }} {{ row.reference_docname }}</a></template>
					<template #cell-status="{ row }"><span class="flex items-center gap-2"><NxgStatus :status="statusTone[row.status] || 'unknown'" :label="row.status || '—'" /><span v-if="row.error" class="max-w-[300px] truncate text-[12px] text-nxg-text-2" :title="row.error">{{ row.error }}</span></span></template>
				</DataTable>
			</section>
		</div>

		<NxgDrawer :open="!!logsFor && tab === 'webhooks'" :title="`Deliveries · ${logsFor}`" subtitle="Most recent first. Request headers are never shown." width="max-w-[720px]" @close="logsFor = null">
			<div class="flex items-center gap-2 border-b border-nxg-border px-5 py-2.5"><label class="flex items-center gap-2 text-[12.5px] text-nxg-text-2"><NxgSwitch v-model="onlyErrors" label="Errors only" />Errors only</label><a :href="$href(`/desk/webhook/${encodeURIComponent(logsFor || '')}`)" class="nxg-btn nxg-btn-ghost ml-auto h-7">Edit webhook<Icon name="external-link" :size="12" /></a></div>
			<div v-if="logsLoading" class="space-y-2 p-5"><div v-for="i in 6" :key="i" class="nxg-skeleton h-10" /></div>
			<NxgEmpty v-else-if="!logs?.rows?.length" text="No deliveries recorded" />
			<ul v-else class="divide-y divide-nxg-border">
				<li v-for="l in logs.rows" :key="l.name" class="px-5 py-2.5 text-[13px]">
					<div class="flex items-center gap-2"><NxgStatus :status="l.error ? 'failed' : 'success'" :label="l.error ? 'Failed' : 'Delivered'" /><span class="text-nxg-text-2">{{ l.reference_doctype }} {{ l.reference_document }}</span><span class="ml-auto text-[12px] text-nxg-text-3" :title="fmtDateTime(l.creation)">{{ timeAgo(l.creation) }}</span></div>
					<p v-if="l.error" class="mt-1 font-mono text-[12px] text-nxg-danger">{{ l.error }}</p>
					<p v-else-if="l.response" class="mt-1 truncate font-mono text-[12px] text-nxg-text-2">{{ l.response }}</p>
				</li>
			</ul>
		</NxgDrawer>
	</div>
</template>
