<script setup lang="ts">
defineProps<{ title: string; description?: string }>();
</script>

<template>
	<div class="mb-5 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
		<div class="min-w-0">
			<h1 class="text-[20px] font-semibold leading-7">{{ title }}</h1>
			<p v-if="description" class="text-[13.5px] text-nxg-text-2">{{ description }}</p>
		</div>
		<div class="flex flex-wrap items-center gap-2"><slot /></div>
	</div>
</template>
