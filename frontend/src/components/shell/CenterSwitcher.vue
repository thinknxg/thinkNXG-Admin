<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import { toast } from "frappe-ui";
import Icon from "@/components/ui/Icon.vue";
import NxgMenu from "@/components/ui/NxgMenu.vue";
import MenuItem from "@/components/ui/MenuItem.vue";
import { boot, type Center } from "@/data/boot";
import { activeCenter, entryRoute, setDefaultCenter } from "@/data/centers";
import { shell } from "@/data/shell";
import { errorMessage } from "@/data/api";

/** Switches between the command centers the server granted. Same shell, same
 *  tokens; only the navigation, filters and quick actions change. No reload. */
defineProps<{ collapsed: boolean }>();
const router = useRouter();
const b = computed(() => boot.data!);
const list = computed(() => b.value.centers);
// Apps with their own interface (thinkNXG CRM, thinkDesk…). thinkNXG ERP and HR
// are the ERP and HR command centers, and the framework is the Admin center.
const otherApps = computed(() => b.value.apps.filter((a) => !["thinknxg_admin", "frappe", "erpnext", "hrms"].includes(a.app)));
const deskLink = computed(() => b.value.show_classic_desk_link && b.value.user.is_admin);
const hasMenu = computed(() => list.value.length > 1 || otherApps.value.length > 0 || deskLink.value);
const accessLabel: Record<Center["access"], string> = { full: "Full access", limited: "Limited", team: "My team" };
const accessHint: Record<Center["access"], string> = {
	full: "Every figure in this center is available to you",
	limited: "Some figures are restricted by your permissions",
	team: "Only your direct reports",
};
const isDefault = (c: Center) => b.value.default_center === c.key;

function open(c: Center) {
	shell.mobileOpen = false;
	if (activeCenter.value?.key === c.key && router.currentRoute.value.path === c.route) return;
	router.push(entryRoute(c));
}
async function makeDefault(c: Center) {
	try {
		await setDefaultCenter(c.key);
		toast.success(`${c.label} opens first when you sign in`);
	} catch (e) {
		toast.error(errorMessage(e));
	}
}
</script>

<template>
	<NxgMenu v-if="hasMenu" width="w-[300px]" class="min-w-0 flex-1">
		<template #trigger="{ toggle, open: isOpen }">
			<button
				class="flex w-full min-w-0 items-center gap-2.5 rounded-nxg p-1 text-left hover:bg-[var(--nxg-sidebar-hover)]"
				:title="collapsed ? activeCenter?.label || b.brand.product : 'Switch command center'"
				:aria-expanded="isOpen"
				aria-haspopup="menu"
				@click="toggle"
			>
				<img :src="b.brand.logo" alt="thinkNXG" class="h-8 w-8 shrink-0 rounded-[7px]" />
				<span v-if="!collapsed" class="min-w-0 flex-1">
					<span class="block truncate text-[13.5px] font-semibold leading-4 text-white">{{ b.brand.name }}</span>
					<span class="block truncate text-[11.5px] leading-4 text-nxg-sb-muted">{{ activeCenter?.label || "My Workspace" }}</span>
				</span>
				<Icon v-if="!collapsed" name="chevrons-up-down" :size="14" class="text-nxg-sb-muted" />
			</button>
		</template>

		<template v-if="list.length">
			<div class="px-2 pb-1 pt-1.5 nxg-micro">Command centers</div>
			<div v-for="c in list" :key="c.key" class="group relative">
				<button
					role="menuitem"
					data-close
					class="flex w-full items-start gap-2.5 rounded-nxg-sm px-2 py-2 text-left text-nxg-text hover:bg-nxg-surface-2"
					:aria-current="activeCenter?.key === c.key ? 'true' : undefined"
					@click="open(c)"
				>
					<span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-nxg border border-nxg-border bg-nxg-surface-2"><Icon :name="c.icon" :size="16" /></span>
					<span class="min-w-0 flex-1">
						<span class="flex items-center gap-1.5">
							<span class="truncate text-[13px] font-medium">{{ c.label }}</span>
							<Icon v-if="activeCenter?.key === c.key" name="check" :size="13" />
						</span>
						<span class="block truncate text-[12px] text-nxg-text-2">{{ c.description }}</span>
						<span class="mt-1 flex items-center gap-1.5 text-[11px] text-nxg-text-3">
							<span class="rounded-full border border-nxg-border px-1.5 leading-4" :title="accessHint[c.access]">{{ accessLabel[c.access] }}</span>
							<span v-if="isDefault(c)">Opens first</span>
						</span>
					</span>
				</button>
				<button
					v-if="!isDefault(c) && list.length > 1"
					class="absolute right-1.5 top-2 hidden rounded-1 px-1.5 text-[11px] text-nxg-text-2 hover:bg-nxg-surface hover:text-nxg-text focus:block group-hover:block"
					:aria-label="`Open ${c.label} first when I sign in`"
					@click.stop="makeDefault(c)"
				>Make default</button>
			</div>
		</template>
		<div v-else class="px-2 py-2 text-[12.5px] text-nxg-text-2">No command center is assigned to you yet. Ask your administrator if you need one.</div>

		<template v-if="otherApps.length">
			<div class="my-1 border-t border-nxg-border" />
			<div class="px-2 pb-1 pt-1.5 nxg-micro">Other apps</div>
			<MenuItem v-for="a in otherApps" :key="a.name" :label="a.title" :href="a.route" icon="layout-grid" />
		</template>
		<template v-if="deskLink">
			<div class="my-1 border-t border-nxg-border" />
			<MenuItem label="Classic Desk" href="/desk" icon="monitor" data-desk />
		</template>
	</NxgMenu>
	<div v-else class="flex min-w-0 flex-1 items-center gap-2.5 p-1">
		<img :src="b.brand.logo" alt="thinkNXG" class="h-8 w-8 shrink-0 rounded-[7px]" />
		<span v-if="!collapsed" class="min-w-0 flex-1">
			<span class="block truncate text-[13.5px] font-semibold leading-4 text-white">{{ b.brand.name }}</span>
			<span class="block truncate text-[11.5px] leading-4 text-nxg-sb-muted">{{ activeCenter?.label || "My Workspace" }}</span>
		</span>
	</div>
</template>
