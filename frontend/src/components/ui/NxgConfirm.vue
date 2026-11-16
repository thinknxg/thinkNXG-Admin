<script setup lang="ts">
import { ref, computed } from "vue";
import NxgDialog from "./NxgDialog.vue";
import { confirmState, resolveConfirm } from "@/composables/useConfirm";
const typed = ref("");
const blocked = computed(() => !!confirmState.typeToConfirm && typed.value.trim() !== confirmState.typeToConfirm);
function done(ok: boolean) {
	typed.value = "";
	resolveConfirm(ok);
}
</script>

<template>
	<NxgDialog :open="confirmState.open" :title="confirmState.title" :description="confirmState.message" @close="done(false)">
		<div v-if="confirmState.typeToConfirm" class="pb-1">
			<label class="mb-1 block text-[12.5px] text-nxg-text-2">Type <b class="text-nxg-text">{{ confirmState.typeToConfirm }}</b> to confirm</label>
			<input v-model="typed" class="nxg-input" autofocus />
		</div>
		<template #footer>
			<button class="nxg-btn nxg-btn-secondary" @click="done(false)">Cancel</button>
			<button class="nxg-btn" :class="confirmState.danger ? 'bg-nxg-danger text-white hover:opacity-90' : 'nxg-btn-primary'" :disabled="blocked" @click="done(true)">{{ confirmState.confirmLabel }}</button>
		</template>
	</NxgDialog>
</template>
