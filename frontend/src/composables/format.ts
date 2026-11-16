export function fmtNumber(n: number | null | undefined) {
	if (n === null || n === undefined) return "—";
	return new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 }).format(n);
}

/** Money in the company's currency. Compact (12.4K) for tiles, full for tables. */
export function fmtMoney(n: number | null | undefined, currency?: string | null, compact = false) {
	if (n === null || n === undefined) return "—";
	const num = new Intl.NumberFormat(undefined, compact ? { notation: "compact", maximumFractionDigits: 1 } : { minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(n);
	return currency ? `${currency} ${num}` : num;
}

export function fmtBytes(b: number | null | undefined) {
	if (b === null || b === undefined) return "—";
	const u = ["B", "KB", "MB", "GB", "TB"];
	let i = 0;
	let v = b;
	while (v >= 1024 && i < u.length - 1) {
		v /= 1024;
		i++;
	}
	return `${v.toFixed(v >= 10 || i === 0 ? 0 : 1)} ${u[i]}`;
}

/** Offset between the browser clock and the site's system-timezone clock. */
let skewMs = 0;
export function setServerNow(serverNow: string) {
	const d = new Date(String(serverNow).replace(" ", "T"));
	if (!isNaN(d.getTime())) skewMs = Date.now() - d.getTime();
}

/** Frappe datetimes arrive as "YYYY-MM-DD HH:mm:ss(.ffffff)" in system time. */
export function parseFrappe(dt: string | null | undefined): Date | null {
	if (!dt) return null;
	const d = new Date(String(dt).replace(" ", "T"));
	return isNaN(d.getTime()) ? null : d;
}

export function timeAgo(dt: string | null | undefined) {
	const d = parseFrappe(dt);
	if (!d) return "";
	const s = Math.round((Date.now() - skewMs - d.getTime()) / 1000);
	if (s < 45) return "just now";
	const m = Math.round(s / 60);
	if (m < 60) return `${m}m ago`;
	const h = Math.round(m / 60);
	if (h < 24) return `${h}h ago`;
	const days = Math.round(h / 24);
	if (days < 30) return `${days}d ago`;
	return d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

export function fmtDateTime(dt: string | null | undefined) {
	const d = parseFrappe(dt);
	return d ? d.toLocaleString(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "";
}

export function initials(name?: string | null) {
	if (!name) return "?";
	const parts = name.replace(/@.*/, "").split(/[\s._-]+/).filter(Boolean);
	return ((parts[0]?.[0] || "") + (parts[1]?.[0] || "")).toUpperCase() || "?";
}

export function isExternal(route?: string) {
	return !!route && (/^https?:\/\//.test(route) || route.startsWith("/desk") || route.startsWith("/app"));
}
