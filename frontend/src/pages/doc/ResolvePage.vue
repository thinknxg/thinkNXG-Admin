<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { call } from "frappe-ui";
import Icon from "@/components/ui/Icon.vue";
import { toInternal } from "@/lib/links";

/** Translates an old Desk address (from a notification, a saved favourite or a
 *  link inside a document) into its internal page, using the server's route
 *  registry. Unmapped addresses get a controlled page, never a Desk redirect. */
const route = useRoute();
const router = useRouter();
const failed = ref(false);
onMounted(async () => {
	try {
		const target: string = await call("thinknxg_admin.api.docs.resolve", { path: String(route.query.path || "") });
		const internal = toInternal(target);
		if (internal && !internal.startsWith("/resolve")) router.replace(internal);
		else failed.value = true;
	} catch {
		failed.value = true;
	}
});
</script>

<template>
	<div v-if="!failed" class="flex items-center justify-center gap-2 py-24 text-[13px] text-nxg-text-2"><Icon name="refresh-cw" :size="15" class="animate-spin" />Opening…</div>
	<div v-else class="mx-auto flex max-w-lg flex-col items-center px-6 py-20 text-center">
		<span class="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-nxg-surface-2"><Icon name="compass" :size="20" /></span>
		<h1 class="mb-1 text-[20px] font-semibold">This page isn't part of the Command Center yet</h1>
		<p class="mb-5 break-all text-[13px] text-nxg-text-2">{{ route.query.path }}</p>
		<RouterLink to="/" class="nxg-btn nxg-btn-primary">Back to my command center</RouterLink>
	</div>
</template>
