<script setup lang="ts">
import Icon from "@/components/ui/Icon.vue";
</script>

<template>
	<div class="flex flex-col items-center justify-center gap-3 px-6 py-24 text-center">
		<span class="flex h-11 w-11 items-center justify-center rounded-full bg-nxg-surface-2"><Icon name="search" :size="20" /></span>
		<h1 class="text-[18px] font-semibold">Page not found</h1>
		<p class="max-w-sm text-[13.5px] text-nxg-text-2">This page doesn't exist, or you don't have permission to open it.</p>
		<RouterLink to="/" class="nxg-btn nxg-btn-primary">Back to Command Center</RouterLink>
	</div>
</template>
