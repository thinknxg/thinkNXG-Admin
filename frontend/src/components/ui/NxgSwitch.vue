<script setup lang="ts">
defineProps<{ modelValue: boolean; label?: string; disabled?: boolean }>();
defineEmits<{ "update:modelValue": [boolean] }>();
</script>

<template>
	<button
		type="button"
		role="switch"
		:aria-checked="modelValue"
		:aria-label="label"
		:disabled="disabled"
		class="relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors disabled:opacity-50"
		:class="modelValue ? 'bg-nxg-primary' : 'bg-nxg-border-strong'"
		@click="$emit('update:modelValue', !modelValue)"
	>
		<span class="inline-block h-4 w-4 transform rounded-full bg-nxg-surface shadow transition-transform" :class="modelValue ? 'translate-x-[18px]' : 'translate-x-0.5'" />
	</button>
</template>
