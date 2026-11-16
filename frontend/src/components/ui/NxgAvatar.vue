<script setup lang="ts">
import { ref } from "vue";
import { initials } from "@/composables/format";
const props = withDefaults(defineProps<{ name?: string | null; image?: string | null; size?: number }>(), { size: 28 });
const broken = ref(false);
</script>

<template>
	<span class="inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full bg-nxg-surface-2 font-semibold text-nxg-text-2 ring-1 ring-nxg-border" :style="{ width: `${props.size}px`, height: `${props.size}px`, fontSize: `${Math.round(props.size * 0.38)}px` }">
		<img v-if="image && !broken" :src="image" :alt="name || ''" class="h-full w-full object-cover" @error="broken = true" />
		<template v-else>{{ initials(name) }}</template>
	</span>
</template>
