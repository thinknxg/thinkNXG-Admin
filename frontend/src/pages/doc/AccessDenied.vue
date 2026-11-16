<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { landingRoute } from "@/router";

/** Shown inside the shell when a route needs access the user doesn't have.
 *  The server would refuse the data anyway; this explains it instead. */
const route = useRoute();
const reasons: Record<string, string> = {
	admin: "This page is part of the Admin Command Center, which needs an administrator role.",
	center: "You don't have access to this command center.",
	module: "This module isn't available for your role, or isn't installed on this site.",
	doctype: "You don't have permission to open these records.",
	create: "You don't have permission to create this kind of record.",
};
const text = computed(() => reasons[String(route.query.reason || "")] || "You don't have access to this page.");
</script>

<template>
	<div class="mx-auto flex max-w-lg flex-col items-center px-6 py-20 text-center">
		<span class="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-nxg-surface-2"><Icon name="lock" :size="20" /></span>
		<h1 class="mb-1 text-[20px] font-semibold">Access denied</h1>
		<p class="mb-1 text-[14px] text-nxg-text-2">{{ text }}</p>
		<p v-if="route.query.from" class="mb-5 break-all text-[12px] text-nxg-text-3">{{ route.query.from }}</p>
		<p class="mb-5 text-[13px] text-nxg-text-2">If you need it, ask your administrator to grant the right role.</p>
		<RouterLink :to="landingRoute()" class="nxg-btn nxg-btn-primary">Go to my command center</RouterLink>
	</div>
</template>
