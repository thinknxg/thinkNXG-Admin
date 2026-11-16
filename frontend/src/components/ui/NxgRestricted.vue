<script setup lang="ts">
import Icon from "./Icon.vue";
/** Shown where the server withheld data the user's role may not see. */
defineProps<{ text?: string }>();
</script>

<template>
	<div class="flex items-center gap-2 rounded-nxg border border-dashed border-nxg-border px-3 py-3 text-[12.5px] text-nxg-text-2">
		<Icon name="lock" :size="14" class="text-nxg-text-3" />{{ text || "Restricted for your role" }}
	</div>
</template>
