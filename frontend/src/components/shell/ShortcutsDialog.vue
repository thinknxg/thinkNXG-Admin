<script setup lang="ts">
import { shell } from "@/data/shell";
import Icon from "@/components/ui/Icon.vue";
const rows = [
	["Ctrl / ⌘ K", "Open the command palette"],
	["/", "Search"],
	["G then A", "Open the Admin Command Center"],
	["G then E", "Open the ERP Command Center"],
	["G then H", "Open the HR Command Center"],
	["G then S", "Go to System Health"],
	["G then U", "Go to Users & Access"],
	["[", "Collapse or expand the sidebar"],
	["?", "Show this list"],
];
</script>

<template>
	<Teleport to="body">
		<div v-if="shell.shortcutsOpen" class="fixed inset-0 z-[60] flex items-center justify-center bg-[rgba(28,10,8,0.45)] px-3" @mousedown.self="shell.shortcutsOpen = false" @keydown.esc="shell.shortcutsOpen = false">
			<div role="dialog" aria-modal="true" aria-label="Keyboard shortcuts" class="w-full max-w-md rounded-nxg-lg border border-nxg-border bg-nxg-surface p-5 shadow-e3">
				<div class="mb-3 flex items-center justify-between">
					<h2 class="text-[15px] font-semibold">Keyboard shortcuts</h2>
					<button class="nxg-icon-btn" aria-label="Close" @click="shell.shortcutsOpen = false"><Icon name="x" /></button>
				</div>
				<dl class="divide-y divide-nxg-border">
					<div v-for="[k, d] in rows" :key="k" class="flex items-center justify-between py-2 text-[13px]">
						<dt class="text-nxg-text-2">{{ d }}</dt>
						<dd><kbd class="rounded-1 border border-nxg-border bg-nxg-surface-2 px-1.5 py-0.5 text-[12px] font-medium">{{ k }}</kbd></dd>
					</div>
				</dl>
			</div>
		</div>
	</Teleport>
</template>
