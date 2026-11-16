import { reactive, watch } from "vue";
import { call } from "frappe-ui";

export function errorMessage(e: any): string {
	const raw = e?.messages?.[0] || e?._server_messages || e?.message || "Request failed";
	return String(raw).replace(/<[^>]+>/g, "").slice(0, 300);
}

export interface PanelState<T> {
	data: T | null;
	loading: boolean;
	error: string | null;
	loadedAt: Date | null;
	/** Browser-measured round-trip of the last successful call, in ms. */
	ms: number | null;
}

/** A dashboard panel bound to a whitelisted method. Re-fetches when params change.
 *  `refresh` bypasses the short server-side cache. */
export function usePanel<T = any>(method: string, params: () => Record<string, unknown> = () => ({})) {
	const state = reactive<PanelState<T>>({ data: null, loading: false, error: null, loadedAt: null, ms: null }) as PanelState<T>;
	let seq = 0;
	async function load(refresh = false) {
		const mine = ++seq;
		state.loading = true;
		state.error = null;
		const t0 = performance.now();
		try {
			const res = await call(method, { ...params(), ...(refresh ? { refresh: 1 } : {}) });
			if (mine !== seq) return;
			state.data = res as T;
			state.loadedAt = new Date();
			state.ms = Math.round(performance.now() - t0);
		} catch (e) {
			if (mine === seq) state.error = errorMessage(e);
		} finally {
			if (mine === seq) state.loading = false;
		}
	}
	watch(params, () => load(), { deep: true, immediate: true });
	return { state, load };
}

import { call as frappeCall, toast } from "frappe-ui";

/** Run a write with toast feedback. Returns the result, or undefined on failure. */
export async function runAction<T = any>(method: string, args: Record<string, unknown> = {}, success?: string): Promise<T | undefined> {
	try {
		const res = (await frappeCall(method, args)) as T;
		if (success) toast.success(success);
		return res;
	} catch (e) {
		toast.error(errorMessage(e));
		return undefined;
	}
}

export function downloadCsv(filename: string, header: string[], rows: (string | number | null | undefined)[][]) {
	const esc = (v: unknown) => {
		const s = v === null || v === undefined ? "" : String(v);
		// Neutralise spreadsheet formula injection, then quote.
		const safe = /^[=+\-@\t\r]/.test(s) ? "'" + s : s;
		return `"${safe.replace(/"/g, '""')}"`;
	};
	const csv = [header, ...rows].map((r) => r.map(esc).join(",")).join("\r\n");
	const url = URL.createObjectURL(new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" }));
	const a = Object.assign(document.createElement("a"), { href: url, download: filename });
	a.click();
	URL.revokeObjectURL(url);
}
