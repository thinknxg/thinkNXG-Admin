<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import { ToastProvider } from "frappe-ui";
import AppSidebar from "@/components/shell/AppSidebar.vue";
import TopBar from "@/components/shell/TopBar.vue";
import CommandPalette from "@/components/shell/CommandPalette.vue";
import ShortcutsDialog from "@/components/shell/ShortcutsDialog.vue";
import NxgConfirm from "@/components/ui/NxgConfirm.vue";
import Icon from "@/components/ui/Icon.vue";
import { allNavItems, boot, getCenter, type CenterKey } from "@/data/boot";
import { entryRoute } from "@/data/centers";
import { shell } from "@/data/shell";
import { useShortcuts } from "@/composables/useShortcuts";

const router = useRouter();
const preview = import.meta.env.VITE_MOCK === "1";
const logoUrl = "/assets/frappe/images/thinkNXG-favicon.png";
const canSee = (route: string) => allNavItems().some((i) => i.route === route && !i.href);
const goCenter = (key: CenterKey) => {
	const c = getCenter(key);
	if (c) router.push(entryRoute(c));
};

useShortcuts({
	"mod+k": () => (shell.paletteOpen = !shell.paletteOpen),
	"/": () => (shell.paletteOpen = true),
	"?": () => (shell.shortcutsOpen = true),
	"[": () => (shell.collapsed = !shell.collapsed),
	"g a": () => goCenter("admin"),
	"g e": () => goCenter("erp"),
	"g h": () => goCenter("hr"),
	"g c": () => canSee("/admin") && router.push("/admin"),
	"g s": () => canSee("/admin/system-health") && router.push("/admin/system-health"),
	"g u": () => canSee("/admin/users") && router.push("/admin/users"),
});
const ready = computed(() => boot.ready && boot.data);
</script>

<template>
	<div v-if="!boot.ready" class="flex h-full items-center justify-center" aria-busy="true">
		<img :src="logoUrl" alt="" class="h-10 w-10 animate-pulse rounded-nxg-lg" />
	</div>
	<div v-else-if="boot.error" class="flex h-full flex-col items-center justify-center gap-3 px-6 text-center">
		<Icon name="circle-alert" :size="22" class="text-nxg-danger" />
		<p class="max-w-md text-[14px]">{{ boot.error }}</p>
		<button class="nxg-btn nxg-btn-secondary" onclick="location.reload()">Try again</button>
	</div>
	<div v-else-if="ready" class="flex h-full overflow-hidden">
		<!-- Desktop sidebar -->
		<div class="hidden h-full shrink-0 lg:block"><AppSidebar /></div>
		<!-- Mobile / tablet drawer -->
		<transition enter-active-class="transition duration-150" enter-from-class="opacity-0" leave-active-class="transition duration-100" leave-to-class="opacity-0">
			<div v-if="shell.mobileOpen" class="fixed inset-0 z-40 flex lg:hidden">
				<div class="absolute inset-0 bg-[rgba(28,10,8,0.5)]" @click="shell.mobileOpen = false" />
				<div class="relative h-full shadow-e3"><AppSidebar /></div>
			</div>
		</transition>

		<div class="flex min-w-0 flex-1 flex-col">
			<div v-if="preview" class="bg-nxg-warning px-4 py-1 text-center text-[12px] font-medium text-white">Preview build with sample data - not connected to a site</div>
			<TopBar />
			<main id="main" class="nxg-scroll min-h-0 flex-1 overflow-y-auto">
				<RouterView :key="$route.path" />
			</main>
		</div>
		<CommandPalette />
		<ShortcutsDialog />
		<NxgConfirm />
		<ToastProvider />
	</div>
</template>
