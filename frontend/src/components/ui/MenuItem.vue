<script setup lang="ts">
import Icon from "./Icon.vue";
defineProps<{ icon?: string; label: string; href?: string; hint?: string; active?: boolean; external?: boolean }>();
</script>

<template>
	<component
		:is="href ? 'a' : 'button'"
		:href="href"
		:target="external ? '_blank' : undefined"
		:rel="external ? 'noopener' : undefined"
		role="menuitem"
		data-close
		class="flex h-8 w-full items-center gap-2 rounded-nxg-sm px-2 text-left text-[13px] text-nxg-text hover:bg-nxg-surface-2"
	>
		<Icon v-if="icon" :name="icon" :size="15" class="text-nxg-text-2" />
		<span class="min-w-0 flex-1 truncate">{{ label }}</span>
		<span v-if="hint" class="text-[11.5px] text-nxg-text-3">{{ hint }}</span>
		<Icon v-if="active" name="check" :size="14" class="text-nxg-text" />
		<Icon v-if="external" name="external-link" :size="13" class="text-nxg-text-3" />
	</component>
</template>
