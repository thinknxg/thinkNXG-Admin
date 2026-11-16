import { onBeforeUnmount, onMounted } from "vue";

type Handler = (e: KeyboardEvent) => void;

function typing(e: KeyboardEvent) {
	const t = e.target as HTMLElement | null;
	return !!t && (t.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(t.tagName));
}

/** Register global shortcuts. Keys: "mod+k", "/", "?", or sequences "g u". */
export function useShortcuts(map: Record<string, Handler>) {
	let pending: string | null = null;
	let timer: number | undefined;
	const onKey = (e: KeyboardEvent) => {
		const mod = e.metaKey || e.ctrlKey;
		const key = e.key.toLowerCase();
		if (mod && map["mod+" + key]) {
			e.preventDefault();
			map["mod+" + key](e);
			return;
		}
		if (mod || e.altKey || typing(e)) return;
		if (pending) {
			const seq = `${pending} ${key}`;
			pending = null;
			window.clearTimeout(timer);
			if (map[seq]) {
				e.preventDefault();
				map[seq](e);
			}
			return;
		}
		if (Object.keys(map).some((k) => k.startsWith(key + " "))) {
			pending = key;
			timer = window.setTimeout(() => (pending = null), 900);
			return;
		}
		const single = e.key === "?" ? "?" : key;
		if (map[single]) {
			e.preventDefault();
			map[single](e);
		}
	};
	onMounted(() => window.addEventListener("keydown", onKey));
	onBeforeUnmount(() => window.removeEventListener("keydown", onKey));
}
