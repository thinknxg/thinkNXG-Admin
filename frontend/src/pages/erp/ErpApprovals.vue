<script setup lang="ts">
import { computed, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import PageHeader from "@/components/ui/PageHeader.vue";
import NxgEmpty from "@/components/ui/NxgEmpty.vue";
import NxgAvatar from "@/components/ui/NxgAvatar.vue";
import { peekState } from "@/data/centers";
import { runAction, usePanel } from "@/data/api";
import { confirmAction } from "@/composables/useConfirm";
import { fmtMoney, timeAgo } from "@/composables/format";

/** ERP documents waiting for the user. The server lists only documents they can
 *  read and only the workflow actions the workflow allows them; each action is
 *  confirmed here and then run by the core workflow engine. */
interface Row { doctype: string; name: string; title: string; state: string; creation: string; company?: string; date?: string; amount?: number | null; currency?: string | null; owner: string; route: string; actions: string[] }
const params = computed(() => ({ company: peekState("erp").company || null }));
const list = usePanel<{ items: Row[] }>("thinknxg_admin.api.erp.get_approvals", () => params.value);
const busy = ref<string | null>(null);
const q = ref("");
const dt = ref("");
const doctypes = computed(() => [...new Set((list.state.data?.items || []).map((r) => r.doctype))].sort());
const rows = computed(() => {
	const s = q.value.trim().toLowerCase();
	return (list.state.data?.items || []).filter((r) => (!dt.value || r.doctype === dt.value) && (!s || `${r.name} ${r.title} ${r.owner}`.toLowerCase().includes(s)));
});
const negative = (a: string) => /reject|cancel|decline|return|send back/i.test(a);

async function act(r: Row, action: string) {
	const ok = await confirmAction({
		title: `${action}: ${r.doctype} ${r.name}?`,
		message: `${r.title}${r.amount != null ? ` · ${fmtMoney(r.amount, r.currency)}` : ""}. The workflow moves this document from "${r.state}" and records your action in its history.`,
		confirmLabel: action,
		danger: negative(action),
	});
	if (!ok) return;
	busy.value = `${r.doctype}:${r.name}`;
	const res = await runAction("thinknxg_admin.api.erp.apply_approval", { doctype: r.doctype, name: r.name, action }, `${r.name}: ${action} done`);
	busy.value = null;
	if (res) list.load(true);
}
</script>

<template>
	<div class="mx-auto w-full max-w-[1180px] px-4 pb-10 pt-6 sm:px-6">
		<PageHeader title="Approvals" description="ERP documents waiting for an action you are allowed to take.">
			<button class="nxg-btn nxg-btn-secondary" :disabled="list.state.loading" @click="list.load(true)"><Icon name="refresh-cw" :size="14" :class="list.state.loading && 'animate-spin'" />Refresh</button>
		</PageHeader>

		<div class="nxg-panel">
			<div class="flex flex-wrap items-center gap-2 border-b border-nxg-border px-4 py-3">
				<label class="relative min-w-[220px] flex-1">
					<Icon name="search" :size="14" class="pointer-events-none absolute left-2.5 top-2 text-nxg-text-3" />
					<input v-model="q" class="nxg-input h-8 w-full pl-8" placeholder="Search by document, title or author" aria-label="Search approvals" />
				</label>
				<select v-model="dt" class="nxg-input h-8 w-auto" aria-label="Document type">
					<option value="">All document types</option>
					<option v-for="d in doctypes" :key="d" :value="d">{{ d }}</option>
				</select>
			</div>

			<div v-if="list.state.error" class="flex items-center justify-between gap-3 px-4 py-4 text-[13px]">
				<span class="flex items-center gap-2 text-nxg-danger"><Icon name="circle-alert" :size="15" />{{ list.state.error }}</span>
				<button class="nxg-btn nxg-btn-secondary h-7" @click="list.load(true)">Retry</button>
			</div>
			<div v-else-if="list.state.loading && !list.state.data" class="space-y-2 p-4"><div v-for="i in 4" :key="i" class="nxg-skeleton h-12" /></div>
			<NxgEmpty v-else-if="!rows.length" :text="list.state.data?.items.length ? 'No approvals match your search' : 'Nothing is waiting for your approval'" icon="circle-check" />
			<ul v-else class="divide-y divide-nxg-border">
				<li v-for="r in rows" :key="r.doctype + r.name" class="flex flex-col gap-3 px-4 py-3 md:flex-row md:items-center">
					<div class="min-w-0 flex-1">
						<div class="flex flex-wrap items-center gap-2">
							<a :href="r.route" class="truncate text-[13.5px] font-medium hover:underline">{{ r.title }}</a>
							<span class="rounded-full border border-nxg-border px-2 text-[11.5px] leading-5 text-nxg-text-2">{{ r.state }}</span>
						</div>
						<div class="mt-0.5 flex flex-wrap items-center gap-x-2 text-[12px] text-nxg-text-2">
							<span>{{ r.doctype }} · {{ r.name }}</span>
							<span v-if="r.company">· {{ r.company }}</span>
							<span class="inline-flex items-center gap-1">· <NxgAvatar :name="r.owner" :size="16" />{{ r.owner }}</span>
							<span>· {{ timeAgo(r.creation) }}</span>
						</div>
					</div>
					<div v-if="r.amount != null" class="nxg-tnum shrink-0 text-[13.5px] font-medium md:w-40 md:text-right">{{ fmtMoney(r.amount, r.currency) }}</div>
					<div class="flex shrink-0 flex-wrap gap-2 md:justify-end">
						<button
							v-for="a in r.actions"
							:key="a"
							class="nxg-btn h-8"
							:class="negative(a) ? 'nxg-btn-secondary' : 'nxg-btn-primary'"
							:disabled="busy === `${r.doctype}:${r.name}`"
							@click="act(r, a)"
						>{{ a }}</button>
					</div>
				</li>
			</ul>
		</div>
		<p class="mt-3 text-[12px] text-nxg-text-3">Only actions your workflow allows for your role are shown. Rules such as "no self-approval" are still enforced when you act.</p>
	</div>
</template>
