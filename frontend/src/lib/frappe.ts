/** Raw calls to thinkNXG's own whitelisted methods, returning the whole response.
 *  Needed where the Desk methods answer in `docs` / `docinfo` rather than
 *  `message` (load, save, submit). Errors carry the server's own message. */
export class FrappeError extends Error {
	exc_type?: string;
	status?: number;
	constructor(message: string, exc_type?: string, status?: number) {
		super(message);
		this.exc_type = exc_type;
		this.status = status;
	}
}

function serverMessage(body: any): string | null {
	try {
		const msgs = JSON.parse(body?._server_messages || "[]").map((m: string) => {
			try {
				return JSON.parse(m).message;
			} catch {
				return m;
			}
		});
		const text = msgs.filter(Boolean).join("\n");
		return text ? text.replace(/<[^>]+>/g, "") : null;
	} catch {
		return null;
	}
}

export async function frappeRaw<T = any>(method: string, args: Record<string, unknown> = {}, httpMethod: "GET" | "POST" = "POST"): Promise<T> {
	const headers: Record<string, string> = { Accept: "application/json", "X-Frappe-CSRF-Token": window.csrf_token || "" };
	let url = `/api/method/${method}`;
	let body: string | undefined;
	if (httpMethod === "GET") {
		const q = new URLSearchParams();
		for (const [k, v] of Object.entries(args)) if (v !== undefined && v !== null) q.set(k, typeof v === "object" ? JSON.stringify(v) : String(v));
		url += "?" + q.toString();
	} else {
		headers["Content-Type"] = "application/json";
		body = JSON.stringify(args);
	}
	const res = await fetch(url, { method: httpMethod, headers, body, credentials: "same-origin" });
	let data: any = {};
	try {
		data = await res.json();
	} catch {
		/* empty body */
	}
	if (!res.ok || data.exc) {
		throw new FrappeError(serverMessage(data) || data.exception?.split(":").slice(1).join(":").trim() || `Request failed (${res.status})`, data.exc_type, res.status);
	}
	return data as T;
}

/** Upload a file through the core upload method; returns the File record. */
export async function uploadFile(file: File, opts: { doctype?: string; docname?: string; fieldname?: string; isPrivate?: boolean } = {}) {
	const form = new FormData();
	form.append("file", file, file.name);
	form.append("is_private", opts.isPrivate === false ? "0" : "1");
	if (opts.doctype && opts.docname) {
		form.append("doctype", opts.doctype);
		form.append("docname", opts.docname);
	}
	if (opts.fieldname) form.append("fieldname", opts.fieldname);
	const res = await fetch("/api/method/upload_file", { method: "POST", body: form, headers: { "X-Frappe-CSRF-Token": window.csrf_token || "", Accept: "application/json" }, credentials: "same-origin" });
	const data: any = await res.json().catch(() => ({}));
	if (!res.ok || data.exc) throw new FrappeError(data._server_messages ? JSON.parse(JSON.parse(data._server_messages)[0]).message : `Upload failed (${res.status})`);
	return data.message as { name: string; file_url: string; file_name: string };
}
