<script setup lang="ts">
import NxgEmpty from "./NxgEmpty.vue";
import Icon from "./Icon.vue";

defineProps<{ title: string; subtitle?: string; loading?: boolean; error?: string | null; empty?: boolean; emptyText?: string; href?: string; hrefLabel?: string; skeletonRows?: number }>();
defineEmits<{ retry: [] }>();
</script>

<template>
	<section class="nxg-panel flex min-w-0 flex-col">
		<header class="flex items-start justify-between gap-3 px-4 pb-2 pt-3.5">
			<div class="min-w-0">
				<h2 class="truncate text-[15px] font-semibold leading-[22px]">{{ title }}</h2>
				<p v-if="subtitle" class="truncate text-[12.5px] text-nxg-text-2">{{ subtitle }}</p>
			</div>
			<div class="flex shrink-0 items-center gap-1">
				<slot name="actions" />
				<a v-if="href" :href="href" class="nxg-btn nxg-btn-ghost h-7 px-2 text-[12.5px]">{{ hrefLabel || "View all" }}<Icon name="arrow-up-right" :size="14" /></a>
			</div>
		</header>
		<div class="min-h-0 flex-1 px-4 pb-4">
			<div v-if="loading && !error" class="space-y-2.5 pt-1" aria-busy="true">
				<div v-for="i in skeletonRows || 4" :key="i" class="nxg-skeleton h-4" :style="{ width: `${90 - i * 9}%` }" />
			</div>
			<div v-else-if="error" class="flex flex-col items-start gap-2 rounded-nxg border border-dashed border-nxg-border-strong p-3 text-[13px]">
				<span class="flex items-center gap-1.5 font-medium text-nxg-danger"><Icon name="circle-alert" :size="14" />Couldn't load this panel</span>
				<span class="text-nxg-text-2">{{ error }}</span>
				<button class="nxg-btn nxg-btn-secondary h-7" @click="$emit('retry')"><Icon name="refresh-cw" :size="13" />Retry</button>
			</div>
			<NxgEmpty v-else-if="empty" :text="emptyText || 'Nothing here yet'" />
			<slot v-else />
		</div>
	</section>
</template>
