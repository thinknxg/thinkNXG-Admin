import { ref } from "vue";
import { readPref, writePref } from "./storage";

export interface RecentEntry {
	label: string;
	route: string;
	icon?: string;
	external?: boolean;
}

export const recent = ref<RecentEntry[]>(readPref("recent", []));
export const favorites = ref<RecentEntry[]>(readPref("favorites", []));

export function pushRecent(entry: RecentEntry) {
	recent.value = [entry, ...recent.value.filter((r) => r.route !== entry.route)].slice(0, 8);
	writePref("recent", recent.value);
}
export function isFavorite(route: string) {
	return favorites.value.some((f) => f.route === route);
}
export function toggleFavorite(entry: RecentEntry) {
	favorites.value = isFavorite(entry.route) ? favorites.value.filter((f) => f.route !== entry.route) : [entry, ...favorites.value].slice(0, 12);
	writePref("favorites", favorites.value);
}
