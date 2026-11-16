<script setup lang="ts">
/** Native select in thinkNXG styling - keeps full keyboard and screen-reader support. */
defineProps<{ modelValue: string | null | undefined; options: (string | { label: string; value: string })[]; placeholder?: string; label?: string }>();
defineEmits<{ "update:modelValue": [string] }>();
</script>

<template>
	<select class="nxg-input h-8 w-auto min-w-[140px] pr-8" :aria-label="label || placeholder" :value="modelValue ?? ''" @change="$emit('update:modelValue', ($event.target as HTMLSelectElement).value)">
		<option v-if="placeholder !== undefined" value="">{{ placeholder }}</option>
		<option v-for="o in options" :key="typeof o === 'string' ? o : o.value" :value="typeof o === 'string' ? o : o.value">{{ typeof o === "string" ? o : o.label }}</option>
	</select>
</template>
