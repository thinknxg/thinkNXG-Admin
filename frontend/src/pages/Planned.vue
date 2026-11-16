<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { findNavByRoute } from "@/data/boot";
import { isFavorite, toggleFavorite } from "@/composables/useRecent";

/** Roadmap page for sections not built yet. It says so plainly and gives a working
 *  route to the native Desk screen, so no visible control is a dead end. */
const route = useRoute();
const item = computed(() => findNavByRoute(route.path));
const external = computed(() => item.value?.desk?.startsWith("http"));
</script>

<template>
	<div v-if="item" class="mx-auto w-full max-w-[880px] px-4 pb-10 pt-8 sm:px-6">
		<div class="mb-6 flex items-start justify-between gap-4">
			<div class="flex items-start gap-3">
				<span class="flex h-10 w-10 items-center justify-center rounded-nxg border border-nxg-border bg-nxg-surface"><Icon :name="item.icon" :size="19" /></span>
				<div>
					<div class="mb-1 flex items-center gap-2">
						<h1 class="text-[20px] font-semibold leading-7">{{ item.label }}</h1>
						<span class="rounded-full border border-nxg-border-strong px-2 py-0.5 text-[11.5px] font-medium text-nxg-text-2">Planned · Phase {{ item.phase }}</span>
					</div>
					<p class="text-[14px] text-nxg-text-2">{{ item.description }}</p>
				</div>
			</div>
			<button class="nxg-icon-btn" :aria-label="isFavorite(route.path) ? 'Remove from favorites' : 'Add to favorites'" @click="toggleFavorite({ label: item.label, route: route.path, icon: item.icon })">
				<Icon name="star" :size="16" :class="isFavorite(route.path) && 'fill-current text-nxg-warning'" />
			</button>
		</div>

		<div class="nxg-panel p-5">
			<p class="mb-4 text-[13.5px]">
				This screen is on the roadmap and not built yet. Until then, the same records are managed in the classic Desk, with the same permissions.
			</p>
			<a v-if="item.desk" :href="item.desk" :target="external ? '_blank' : undefined" :rel="external ? 'noopener' : undefined" class="nxg-btn nxg-btn-primary">
				{{ external ? "Open documentation" : `Open ${item.label} in Desk` }}<Icon name="external-link" :size="14" />
			</a>
			<div v-if="item.capabilities?.length" class="mt-6">
				<h2 class="mb-2 nxg-micro">What this screen will include</h2>
				<ul class="space-y-1.5">
					<li v-for="c in item.capabilities" :key="c" class="flex items-start gap-2 text-[13.5px]"><Icon name="check" :size="15" class="mt-0.5 text-nxg-text-3" />{{ c }}</li>
				</ul>
			</div>
			<div v-if="item.children?.length" class="mt-6">
				<h2 class="mb-2 nxg-micro">Related screens in Desk</h2>
				<div class="flex flex-wrap gap-2">
					<a v-for="c in item.children" :key="c.key" :href="c.desk" class="nxg-btn nxg-btn-secondary h-7">{{ c.label }}<Icon name="external-link" :size="12" /></a>
				</div>
			</div>
		</div>
	</div>
	<div v-else class="px-6 py-16 text-center text-nxg-text-2">This page isn't available to you.</div>
</template>
