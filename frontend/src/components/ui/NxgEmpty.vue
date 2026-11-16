<script setup lang="ts">
import Icon from "./Icon.vue";
defineProps<{ text: string; icon?: string }>();
</script>

<template>
	<div class="flex flex-col items-center justify-center gap-1.5 py-6 text-center text-[13px] text-nxg-text-2">
		<span class="flex h-8 w-8 items-center justify-center rounded-full bg-nxg-surface-2"><Icon :name="icon || 'inbox'" :size="16" /></span>
		{{ text }}
		<slot />
	</div>
</template>
