// Browser storage can be unavailable (privacy modes, embedded contexts).
// Preferences are conveniences, so failures fall back silently.
export function readPref<T>(key: string, fallback: T): T {
	try {
		const raw = localStorage.getItem("nxg:" + key);
		return raw === null ? fallback : (JSON.parse(raw) as T);
	} catch {
		return fallback;
	}
}
export function writePref(key: string, value: unknown) {
	try {
		localStorage.setItem("nxg:" + key, JSON.stringify(value));
	} catch {
		/* ignore */
	}
}
