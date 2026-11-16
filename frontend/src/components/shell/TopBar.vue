<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { call, toast } from "frappe-ui";
import Icon from "@/components/ui/Icon.vue";
import NxgMenu from "@/components/ui/NxgMenu.vue";
import MenuItem from "@/components/ui/MenuItem.vue";
import NxgAvatar from "@/components/ui/NxgAvatar.vue";
import ContextFilters from "@/components/shell/ContextFilters.vue";
import { allNavItems, boot, findNavByRoute } from "@/data/boot";
import { activeCenter } from "@/data/centers";
import { shell } from "@/data/shell";
import { setTheme, themeMode, type ThemeMode } from "@/composables/useTheme";
import { timeAgo } from "@/composables/format";
import { errorMessage } from "@/data/api";

const route = useRoute();
const b = computed(() => boot.data!);

const crumbs = computed(() => {
	const c = activeCenter.value;
	const home = c ? { label: c.label, to: c.route } : { label: "My Workspace", to: "/my-workspace" };
	const out: { label: string; to?: string }[] = [home];
	const item = findNavByRoute(route.path);
	if (item && item.route !== home.to) {
		const parent = allNavItems().find((i) => i.children?.some((ch) => ch.key === item.key));
		if (parent && parent.route !== item.route) out.push({ label: parent.label, to: parent.route });
		out.push({ label: item.label });
	} else if (!item && route.path !== home.to) {
		out.push({ label: (route.meta.title as string) || "Not found" });
	}
	return out;
});

const quick = computed(() => {
	const c = activeCenter.value;
	const mine = c?.quick_create || [];
	const seen = new Set(mine.map((q) => q.doctype));
	const others = b.value.centers
		.filter((o) => o.key !== c?.key)
		.map((o) => ({ label: `More · ${o.short}`, items: o.quick_create.filter((q) => !seen.has(q.doctype) && (seen.add(q.doctype), true)) }))
		.filter((g) => g.items.length);
	return { mine, others };
});

// Notifications ------------------------------------------------------------
interface Notif { name: string; subject: string; from_name?: string; read: number; creation: string; route?: string | null; type?: string }
const notifs = ref<{ items: Notif[]; unread: number; open_todos: number } | null>(null);
const notifError = ref<string | null>(null);
async function loadNotifications() {
	try {
		notifs.value = await call("thinknxg_admin.api.notifications.get_notifications", { limit: 20 });
		notifError.value = null;
	} catch (e) {
		notifError.value = errorMessage(e);
	}
}
async function markAllRead() {
	try {
		await call("frappe.desk.doctype.notification_log.notification_log.mark_all_as_read");
		await loadNotifications();
	} catch (e) {
		toast.error(errorMessage(e));
	}
}
async function openNotification(n: Notif) {
	if (!n.read) call("frappe.desk.doctype.notification_log.notification_log.mark_as_read", { docname: n.name }).catch(() => {});
	if (n.route) window.location.href = n.route;
}
let timer: number | undefined;
onMounted(() => {
	loadNotifications();
	timer = window.setInterval(loadNotifications, 60_000);
});
onBeforeUnmount(() => window.clearInterval(timer));

// Theme ----------------------------------------------------------------------
const themes: { mode: ThemeMode; label: string; icon: string }[] = [
	{ mode: "light", label: "Light", icon: "sun" },
	{ mode: "dark", label: "Dark", icon: "moon" },
	{ mode: "system", label: "System", icon: "monitor" },
];
const themeIcon = computed(() => themes.find((t) => t.mode === themeMode.value)?.icon || "monitor");

const isMac = typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.platform);
</script>

<template>
	<header class="sticky top-0 z-30 flex h-14 shrink-0 items-center gap-2 border-b border-nxg-border bg-nxg-surface/90 px-3 backdrop-blur sm:px-5">
		<button class="nxg-icon-btn lg:hidden" aria-label="Open navigation" @click="shell.mobileOpen = true"><Icon name="menu" :size="18" /></button>

		<nav aria-label="Breadcrumb" class="hidden min-w-0 items-center gap-1 text-[13px] md:flex">
			<template v-for="(c, i) in crumbs" :key="i">
				<Icon v-if="i" name="chevron-right" :size="13" class="text-nxg-text-3" />
				<RouterLink v-if="c.to && i < crumbs.length - 1" :to="c.to" class="truncate text-nxg-text-2 hover:text-nxg-text">{{ c.label }}</RouterLink>
				<span v-else class="truncate font-medium" aria-current="page">{{ c.label }}</span>
			</template>
		</nav>

		<button
			class="ml-0 flex h-8 min-w-0 flex-1 items-center gap-2 rounded-nxg border border-nxg-border bg-nxg-surface-2/60 px-2.5 text-[13px] text-nxg-text-3 transition-colors hover:border-nxg-border-strong md:ml-4 md:max-w-[380px]"
			aria-label="Search or jump to (command palette)"
			@click="shell.paletteOpen = true"
		>
			<Icon name="search" :size="15" />
			<span class="flex-1 truncate text-left">Search or jump to…</span>
			<kbd class="hidden rounded-1 border border-nxg-border bg-nxg-surface px-1.5 text-[11px] font-medium text-nxg-text-2 sm:inline">{{ isMac ? "⌘" : "Ctrl" }} K</kbd>
		</button>

		<div class="ml-auto flex items-center gap-0.5">
			<!-- Quick create: the active center's actions first; only DocTypes the user may create -->
			<NxgMenu v-if="quick.mine.length || quick.others.length" align="right" width="w-60">
				<template #trigger="{ toggle }">
					<button class="nxg-btn nxg-btn-primary h-8 px-2.5" aria-label="Create new" @click="toggle"><Icon name="plus" :size="15" /><span class="hidden sm:inline">New</span></button>
				</template>
				<div class="nxg-scroll max-h-[420px] overflow-y-auto">
					<div class="px-2 pb-1 pt-1.5 nxg-micro">{{ activeCenter ? `Create in ${activeCenter.short}` : "Create" }}</div>
					<MenuItem v-for="q in quick.mine" :key="q.doctype" :label="q.doctype" :icon="q.icon" :href="q.route" />
					<template v-for="g in quick.others" :key="g.label">
						<div class="my-1 border-t border-nxg-border" />
						<div class="px-2 pb-1 pt-1.5 nxg-micro">{{ g.label }}</div>
						<MenuItem v-for="q in g.items" :key="q.doctype" :label="q.doctype" :icon="q.icon" :href="q.route" />
					</template>
				</div>
			</NxgMenu>

			<!-- Context filters declared by the active center -->
			<ContextFilters />

			<!-- Notifications + approvals -->
			<NxgMenu align="right" width="w-[360px]">
				<template #trigger="{ toggle }">
					<button class="nxg-icon-btn relative" :aria-label="`Notifications${notifs?.unread ? `, ${notifs.unread} unread` : ''}`" @click="toggle(); loadNotifications()">
						<Icon name="bell" :size="17" />
						<span v-if="notifs?.unread" class="nxg-tnum absolute right-0.5 top-0.5 min-w-[16px] rounded-full bg-nxg-red px-1 text-center text-[10px] font-semibold leading-4 text-white">{{ notifs.unread > 99 ? "99+" : notifs.unread }}</span>
					</button>
				</template>
				<div class="flex items-center justify-between px-2 pb-1.5 pt-1">
					<span class="text-[13px] font-semibold">Notifications</span>
					<button v-if="notifs?.unread" class="text-[12px] text-nxg-text-2 hover:text-nxg-text" @click.stop="markAllRead">Mark all read</button>
				</div>
				<a v-if="notifs?.open_todos" href="/desk/todo?status=Open" class="mb-1 flex items-center gap-2 rounded-nxg-sm bg-nxg-surface-2 px-2 py-1.5 text-[12.5px]" data-close>
					<Icon name="list-checks" :size="14" class="text-nxg-text-2" /><span class="flex-1">{{ notifs.open_todos }} open task{{ notifs.open_todos === 1 ? "" : "s" }} assigned to you</span><Icon name="chevron-right" :size="13" />
				</a>
				<div class="nxg-scroll max-h-[380px] overflow-y-auto">
					<div v-if="notifError" class="px-2 py-3 text-[12.5px] text-nxg-danger">{{ notifError }}</div>
					<div v-else-if="!notifs" class="space-y-2 p-2"><div v-for="i in 3" :key="i" class="nxg-skeleton h-8" /></div>
					<div v-else-if="!notifs.items.length" class="px-2 py-6 text-center text-[12.5px] text-nxg-text-2">You're all caught up</div>
					<button v-for="n in notifs?.items || []" :key="n.name" data-close class="flex w-full items-start gap-2.5 rounded-nxg-sm px-2 py-2 text-left hover:bg-nxg-surface-2" @click="openNotification(n)">
						<NxgAvatar :name="n.from_name" :size="24" />
						<span class="min-w-0 flex-1">
							<span class="line-clamp-2 text-[12.5px]" :class="n.read ? 'text-nxg-text-2' : 'text-nxg-text'">{{ n.subject }}</span>
							<span class="text-[11.5px] text-nxg-text-3">{{ timeAgo(n.creation) }}</span>
						</span>
						<span v-if="!n.read" class="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-nxg-red" aria-label="Unread" />
					</button>
				</div>
				<div class="mt-1 border-t border-nxg-border pt-1"><MenuItem label="Open Notification Center" href="/thinknxg/notifications" icon="inbox" /></div>
			</NxgMenu>

			<a :href="b.brand.docs_url" target="_blank" rel="noopener" class="nxg-icon-btn hidden sm:inline-flex" aria-label="Help and documentation" title="Help"><Icon name="circle-help" :size="17" /></a>

			<NxgMenu align="right" width="w-40">
				<template #trigger="{ toggle }">
					<button class="nxg-icon-btn" aria-label="Theme" title="Theme" @click="toggle"><Icon :name="themeIcon" :size="17" /></button>
				</template>
				<MenuItem v-for="t in themes" :key="t.mode" :label="t.label" :icon="t.icon" :active="themeMode === t.mode" @click="setTheme(t.mode)" />
			</NxgMenu>

			<NxgMenu align="right" width="w-56" class="lg:hidden">
				<template #trigger="{ toggle }">
					<button class="ml-1 rounded-full" aria-label="Account" @click="toggle"><NxgAvatar :name="b.user.full_name" :image="b.user.image" :size="28" /></button>
				</template>
				<div class="px-2 py-1.5"><div class="truncate text-[13px] font-medium">{{ b.user.full_name }}</div><div class="truncate text-[12px] text-nxg-text-2">{{ b.user.email }}</div></div>
				<MenuItem label="My profile" icon="user" :href="`/desk/user/${encodeURIComponent(b.user.name)}`" />
				<MenuItem label="Log out" icon="log-out" href="/api/method/logout" />
			</NxgMenu>
		</div>
	</header>
</template>
