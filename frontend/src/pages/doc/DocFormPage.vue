<script setup lang="ts">
import { computed } from "vue";
import DocForm from "@/components/doc/DocForm.vue";

/** /<center>/<module>/<doctype>/<name> and …/new: one document inside the shell. */
const props = defineProps<{ center: string; module?: string; slug: string; name: string | null }>();
const base = computed(() => (props.module ? `/${props.center}/${props.module}/${props.slug}` : `/${props.center}/doc/${props.slug}`));
</script>

<template>
	<div class="mx-auto w-full max-w-[1480px] px-4 pb-10 sm:px-6">
		<DocForm :slug="slug" :name="name || null" :base="base" />
	</div>
</template>
