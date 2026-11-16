import { reactive } from "vue";

export const confirmState = reactive({
	open: false,
	title: "",
	message: "",
	confirmLabel: "Confirm",
	danger: false,
	typeToConfirm: "" as string,
	resolve: null as null | ((ok: boolean) => void),
});

/** Promise-based confirmation dialog. Destructive bulk actions can require typing a word. */
export function confirmAction(opts: { title: string; message?: string; confirmLabel?: string; danger?: boolean; typeToConfirm?: string }) {
	return new Promise<boolean>((resolve) => {
		Object.assign(confirmState, { open: true, message: "", confirmLabel: "Confirm", danger: false, typeToConfirm: "", ...opts, resolve });
	});
}

export function resolveConfirm(ok: boolean) {
	confirmState.resolve?.(ok);
	confirmState.open = false;
	confirmState.resolve = null;
}
