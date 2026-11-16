<script setup lang="ts">
import { computed, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import DocList from "@/components/doc/DocList.vue";
import { getModule } from "@/data/boot";

/** /<center>/<module>/<doctype> and /<center>/doc/<doctype>: a document list
 *  inside the command center shell. */
const props = defineProps<{ center: string; module?: string; slug: string }>();
const base = computed(() => (props.module ? `/${props.center}/${props.module}/${props.slug}` : `/${props.center}/doc/${props.slug}`));
const mod = computed(() => (props.module ? getModule(props.center, props.module) : undefined));
const canCreate = computed(() => listMeta.value?.perms?.create && !listMeta.value?.issingle);
const listMeta = ref<any>(null);
</script>

<template>
	<div class="mx-auto w-full max-w-[1480px] px-4 pb-10 pt-6 sm:px-6">
		<div class="mb-4 flex flex-wrap items-end justify-between gap-3">
			<div class="min-w-0">
				<p v-if="mod" class="mb-0.5 text-[12.5px] text-nxg-text-2">{{ mod.label }}</p>
				<h1 class="text-[22px] font-semibold leading-8">{{ listMeta?.doctype || "…" }}</h1>
				<p v-if="listMeta?.description" class="max-w-3xl text-[13px] text-nxg-text-2">{{ String(listMeta.description).replace(/<[^>]+>/g, "") }}</p>
			</div>
			<a v-if="canCreate" :href="`/thinknxg${base}/new`" class="nxg-btn nxg-btn-primary h-8"><Icon name="plus" :size="14" />New {{ listMeta.doctype }}</a>
		</div>
		<DocList :slug="slug" :base="base" @meta="(m) => (listMeta = m)" />
	</div>
</template>
