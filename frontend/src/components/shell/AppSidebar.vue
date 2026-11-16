<script setup lang="ts">
import { computed, reactive } from "vue";
import { useRoute } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import NxgMenu from "@/components/ui/NxgMenu.vue";
import MenuItem from "@/components/ui/MenuItem.vue";
import NxgAvatar from "@/components/ui/NxgAvatar.vue";
import CenterSwitcher from "@/components/shell/CenterSwitcher.vue";
import { boot, type NavItem } from "@/data/boot";
import { activeCenter, activeNavigation } from "@/data/centers";
import { shell } from "@/data/shell";
import { readPref, writePref } from "@/composables/storage";

const route = useRoute();
const b = computed(() => boot.data!);
const collapsed = computed(() => shell.collapsed && !shell.mobileOpen);
const closedSections = reactive<Record<string, boolean>>(readPref("closed-sections", {}));
const openItems = reactive<Record<string, boolean>>({});

function toggleSection(name: string) {
	closedSections[name] = !closedSections[name];
	writePref("closed-sections", closedSections);
}
const docsUrl = computed(() => activeCenter.value?.docs_url || b.value.brand.docs_url);
function isActive(item: NavItem) {
	if (item.href) return false;
	// Center homes are active only on their own page, not on every page below them.
	if (["/", "/admin", "/erp", "/hr"].includes(item.route)) return route.path === item.route;
	return route.path === item.route || route.path.startsWith(item.route + "/");
}
function childActive(item: NavItem) {
	return (item.children || []).some((c) => route.path === c.route || route.path.startsWith(c.route + "/"));
}
function expanded(item: NavItem) {
	return openItems[item.key] ?? (isActive(item) || childActive(item));
}
function onNavigate() {
	shell.mobileOpen = false;
}
async function logout() {
	await fetch("/api/method/logout", { method: "POST", headers: { "X-Frappe-CSRF-Token": window.csrf_token || "" } }).catch(() => {});
	window.location.href = "/login";
}
</script>

<template>
	<aside
		class="nxg-scroll flex h-full flex-col bg-nxg-sb-bg text-nxg-sb-text transition-[width] duration-150"
		:class="collapsed ? 'w-16' : 'w-[248px]'"
		aria-label="Main navigation"
	>
		<!-- Brand + command center switcher -->
		<div class="flex h-14 shrink-0 items-center gap-2.5 border-b border-[var(--nxg-sidebar-border)] px-3">
			<CenterSwitcher :collapsed="collapsed" />
		</div>

		<!-- Navigation -->
		<nav class="nxg-scroll min-h-0 flex-1 overflow-y-auto px-2 py-3">
			<div v-for="section in activeNavigation" :key="section.section" class="mb-3">
				<button
					v-if="!collapsed"
					class="mb-0.5 flex w-full items-center justify-between rounded-1 px-2 py-1 text-[11px] font-medium uppercase tracking-[0.06em] text-nxg-sb-muted hover:text-nxg-sb-text"
					:aria-expanded="!closedSections[section.section]"
					@click="toggleSection(section.section)"
				>
					{{ section.section }}
					<Icon :name="closedSections[section.section] ? 'chevron-right' : 'chevron-down'" :size="12" />
				</button>
				<div v-else class="mx-3 my-2 border-t border-[var(--nxg-sidebar-border)]" />
				<ul v-show="collapsed || !closedSections[section.section]" class="space-y-px">
					<li v-for="item in section.items" :key="item.key">
						<div class="relative">
							<span v-if="isActive(item) && !childActive(item)" class="absolute left-0 top-1.5 h-5 w-[2px] rounded-full bg-nxg-red" aria-hidden="true" />
							<a
								v-if="item.href"
								:href="item.href"
								class="group/desk flex h-8 items-center gap-2.5 rounded-nxg px-2.5 text-[13px] transition-colors hover:bg-[var(--nxg-sidebar-hover)] hover:text-white"
								:class="collapsed && 'justify-center px-0'"
								:title="collapsed ? item.label : undefined"
							>
								<Icon :name="item.icon" :size="16" />
								<span v-if="!collapsed" class="min-w-0 flex-1 truncate">{{ item.label }}</span>
								<Icon v-if="!collapsed" name="arrow-up-right" :size="13" class="text-nxg-sb-muted opacity-0 group-hover/desk:opacity-100" />
							</a>
							<RouterLink
								v-else
								:to="item.route"
								class="flex h-8 items-center gap-2.5 rounded-nxg px-2.5 text-[13px] transition-colors"
								:class="[isActive(item) ? 'bg-[var(--nxg-sidebar-active)] font-medium text-white' : 'hover:bg-[var(--nxg-sidebar-hover)] hover:text-white', collapsed && 'justify-center px-0', item.children && !collapsed && 'pr-8']"
								:title="collapsed ? item.label : undefined"
								:aria-current="isActive(item) ? 'page' : undefined"
								@click="onNavigate"
							>
								<Icon :name="item.icon" :size="16" />
								<span v-if="!collapsed" class="min-w-0 flex-1 truncate">{{ item.label }}</span>
								<span v-if="!collapsed && item.status === 'planned'" class="rounded-1 px-1 text-[10px] font-medium uppercase tracking-wide text-nxg-sb-muted ring-1 ring-[var(--nxg-sidebar-border)]" title="Planned - opens the roadmap page with a link to the classic Desk">Soon</span>
							</RouterLink>
							<button
								v-if="item.children && !collapsed"
								class="absolute right-1 top-1 flex h-6 w-6 items-center justify-center rounded-1 text-nxg-sb-muted hover:text-white"
								:aria-label="expanded(item) ? `Collapse ${item.label}` : `Expand ${item.label}`"
								@click="openItems[item.key] = !expanded(item)"
							>
								<Icon :name="expanded(item) ? 'chevron-down' : 'chevron-right'" :size="13" />
							</button>
						</div>
						<ul v-if="item.children && !collapsed && expanded(item)" class="mb-1 ml-[19px] mt-px space-y-px border-l border-[var(--nxg-sidebar-border)] pl-2">
							<li v-for="child in item.children" :key="child.key">
								<RouterLink
									:to="child.route"
									class="flex h-7 items-center rounded-nxg-sm px-2 text-[12.5px] transition-colors"
									:class="route.path === child.route || route.path.startsWith(child.route + '/') ? 'bg-[var(--nxg-sidebar-active)] font-medium text-white' : 'hover:bg-[var(--nxg-sidebar-hover)] hover:text-white'"
									@click="onNavigate"
								>{{ child.label }}</RouterLink>
							</li>
						</ul>
					</li>
				</ul>
			</div>
		</nav>

		<!-- Footer -->
		<div class="shrink-0 border-t border-[var(--nxg-sidebar-border)] p-2">
			<div v-if="!collapsed" class="mb-1 grid grid-cols-3 gap-1">
				<a :href="b.brand.support_url" target="_blank" rel="noopener" class="flex h-8 items-center justify-center gap-1.5 rounded-nxg text-[12px] hover:bg-[var(--nxg-sidebar-hover)] hover:text-white" title="Help Center (thinkDesk)"><Icon name="life-buoy" :size="14" />Help</a>
				<a :href="docsUrl" target="_blank" rel="noopener" class="flex h-8 items-center justify-center gap-1.5 rounded-nxg text-[12px] hover:bg-[var(--nxg-sidebar-hover)] hover:text-white" title="Documentation"><Icon name="book-open" :size="14" />Docs</a>
				<a :href="b.brand.whats_new_url" target="_blank" rel="noopener" class="flex h-8 items-center justify-center gap-1.5 rounded-nxg text-[12px] hover:bg-[var(--nxg-sidebar-hover)] hover:text-white" title="What's New"><Icon name="sparkles" :size="14" />New</a>
			</div>
			<NxgMenu placement="top" width="w-60">
				<template #trigger="{ toggle }">
					<button class="flex w-full items-center gap-2.5 rounded-nxg p-1.5 text-left hover:bg-[var(--nxg-sidebar-hover)]" :class="collapsed && 'justify-center'" @click="toggle">
						<NxgAvatar :name="b.user.full_name" :image="b.user.image" :size="28" />
						<span v-if="!collapsed" class="min-w-0 flex-1">
							<span class="block truncate text-[13px] font-medium text-white">{{ b.user.full_name }}</span>
							<span class="block truncate text-[11.5px] text-nxg-sb-muted">{{ b.user.email || b.user.name }}</span>
						</span>
						<Icon v-if="!collapsed" name="chevrons-up-down" :size="14" class="text-nxg-sb-muted" />
					</button>
				</template>
				<MenuItem label="My profile" icon="user" :href="$href(`/desk/user/${encodeURIComponent(b.user.name)}`)" />
				<MenuItem v-if="b.user.is_admin" label="Command Center settings" icon="settings" :href="$href('/desk/thinknxg-admin-settings')" />
				<MenuItem label="Keyboard shortcuts" icon="command" hint="?" @click="shell.shortcutsOpen = true" />
				<div class="my-1 border-t border-nxg-border" />
				<MenuItem label="Log out" icon="log-out" @click="logout" />
			</NxgMenu>
			<button
				class="mt-1 hidden h-7 w-full items-center gap-2 rounded-nxg px-2.5 text-[12px] text-nxg-sb-muted hover:bg-[var(--nxg-sidebar-hover)] hover:text-white lg:flex"
				:class="collapsed && 'justify-center px-0'"
				:aria-label="shell.collapsed ? 'Expand sidebar' : 'Collapse sidebar'"
				@click="shell.collapsed = !shell.collapsed"
			>
				<Icon name="panel-left" :size="14" /><span v-if="!collapsed">Collapse</span>
			</button>
		</div>
	</aside>
</template>
