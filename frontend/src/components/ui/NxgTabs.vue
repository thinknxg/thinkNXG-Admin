<script setup lang="ts">
defineProps<{ tabs: { key: string; label: string; count?: number | null }[]; modelValue: string }>();
defineEmits<{ "update:modelValue": [string] }>();
</script>

<template>
	<div role="tablist" class="flex gap-1 overflow-x-auto border-b border-nxg-border">
		<button
			v-for="t in tabs"
			:key="t.key"
			role="tab"
			:aria-selected="modelValue === t.key"
			class="relative -mb-px flex h-9 shrink-0 items-center gap-1.5 border-b-2 px-2.5 text-[13px] font-medium transition-colors"
			:class="modelValue === t.key ? 'border-nxg-red text-nxg-text' : 'border-transparent text-nxg-text-2 hover:text-nxg-text'"
			@click="$emit('update:modelValue', t.key)"
		>
			{{ t.label }}<span v-if="t.count !== undefined && t.count !== null" class="nxg-tnum rounded-full bg-nxg-surface-2 px-1.5 text-[11px] text-nxg-text-2">{{ t.count }}</span>
		</button>
	</div>
</template>
