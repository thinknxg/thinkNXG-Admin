import { call } from "frappe-ui";
import { boot } from "@/data/boot";

/** Report filters are defined in each report's JavaScript (frappe.query_reports[name].filters).
 *  This evaluates that script with a small, tolerant stand-in for the Desk globals
 *  it touches, only to read the filter definitions: their fieldnames, labels, types,
 *  options and defaults. Behaviour hooks (get_query, on_change) are ignored. */
export interface ReportFilter { fieldname: string; label?: string; fieldtype: string; options?: any; default?: any; reqd?: number; depends_on?: string; hidden?: number }

const iso = (d: Date) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
const parse = (s: string) => new Date(String(s).slice(0, 10) + "T00:00:00");
const datetime = {
	get_today: () => iso(new Date()),
	nowdate: () => iso(new Date()),
	now_date: () => iso(new Date()),
	add_days: (d: string, n: number) => { const x = parse(d); x.setDate(x.getDate() + Number(n)); return iso(x); },
	add_months: (d: string, n: number) => { const x = parse(d); x.setMonth(x.getMonth() + Number(n)); return iso(x); },
	month_start: () => { const x = new Date(); return iso(new Date(x.getFullYear(), x.getMonth(), 1)); },
	month_end: () => { const x = new Date(); return iso(new Date(x.getFullYear(), x.getMonth() + 1, 0)); },
	year_start: () => iso(new Date(new Date().getFullYear(), 0, 1)),
	year_end: () => iso(new Date(new Date().getFullYear(), 11, 31)),
	str_to_obj: (s: string) => parse(s),
	obj_to_str: (d: Date) => iso(d),
	user_to_str: (s: string) => s,
	str_to_user: (s: string) => s,
	get_datetime_as_string: () => new Date().toISOString(),
};

function tolerant(): any {
	const fn = function () {
		return undefined;
	};
	return new Proxy(fn, {
		get: (t: any, p) => (p === Symbol.toPrimitive ? () => "" : p === "then" ? undefined : p in t ? t[p] : tolerant()),
		apply: () => undefined,
	});
}
function lenient<T extends object>(obj: T): T {
	return new Proxy(obj, { get: (t: any, p) => (p in t ? t[p] : tolerant()), set: (t: any, p, v) => ((t[p] = v), true) });
}
function deepExtend(target: any, ...sources: any[]) {
	for (const s of sources) {
		if (!s) continue;
		for (const [k, v] of Object.entries(s)) target[k] = Array.isArray(v) ? v.map((x) => (x && typeof x === "object" ? { ...x } : x)) : v && typeof v === "object" && typeof v !== "function" ? deepExtend({}, v) : v;
	}
	return target;
}

const cache = new Map<string, string>();
async function fetchText(url: string) {
	if (cache.has(url)) return cache.get(url)!;
	const res = await fetch(url, { credentials: "same-origin" });
	const text = res.ok ? await res.text() : "";
	cache.set(url, text);
	return text;
}

export async function reportFilters(report: string): Promise<{ filters: ReportFilter[]; parsed: boolean; meta: any }> {
	const meta: any = await call("frappe.desk.query_report.get_script", { report_name: report });
	const defaults = {
		get_user_default: (k: string) => (String(k).toLowerCase() === "company" ? boot.data?.default_company : undefined),
		get_default: (k: string) => (String(k).toLowerCase() === "company" ? boot.data?.default_company : undefined),
		get_user_defaults: () => [],
		get_global_default: () => undefined,
	};
	const frappe: any = lenient({ query_reports: {} as Record<string, any>, defaults: lenient(defaults), datetime: lenient(datetime), provide: () => undefined, boot: lenient({ sysdefaults: {} }), session: { user: boot.data?.user.name }, user: lenient({}), sys_defaults: {} });
	const erpnext: any = lenient({ utils: lenient({ get_fiscal_year: () => undefined, add_dimensions: () => undefined }) });
	const $ = lenient({ extend: (...args: any[]) => deepExtend(args[0] === true ? args[1] : args[0], ...(args[0] === true ? args.slice(2) : args.slice(1))) });
	const run = (code: string) => {
		// eslint-disable-next-line no-new-func
		new Function("frappe", "erpnext", "hrms", "__", "$", "jQuery", "moment", code)(frappe, erpnext, lenient({}), (s: string) => s, $, $, tolerant());
	};
	try {
		const script = meta?.script || "";
		if (/erpnext\.financial_statements/.test(script)) run(await fetchText("/assets/erpnext/js/financial_statements.js"));
		run(script);
	} catch {
		/* fall back below */
	}
	const raw = frappe.query_reports?.[report]?.filters;
	const list: ReportFilter[] = Array.isArray(raw)
		? raw
				.filter((f: any) => f && f.fieldname && f.fieldtype)
				.map((f: any) => ({
					fieldname: f.fieldname,
					label: f.label,
					fieldtype: f.fieldtype,
					options: Array.isArray(f.options) ? f.options.map((o: any) => (typeof o === "object" ? o.value : o)).join("\n") : typeof f.options === "string" ? f.options : undefined,
					default: typeof f.default === "function" ? undefined : f.default,
					reqd: f.reqd ? 1 : 0,
					depends_on: typeof f.depends_on === "string" ? f.depends_on : undefined,
					hidden: f.hidden ? 1 : 0,
				}))
		: [];
	if (list.length) return { filters: list, parsed: true, meta };
	// Fallback: the filters nearly every business report takes.
	return {
		parsed: false,
		meta,
		filters: [
			{ fieldname: "company", label: "Company", fieldtype: "Link", options: "Company", default: boot.data?.default_company, reqd: 1 },
			{ fieldname: "from_date", label: "From date", fieldtype: "Date", default: datetime.add_months(datetime.get_today(), -1) },
			{ fieldname: "to_date", label: "To date", fieldtype: "Date", default: datetime.get_today() },
		],
	};
}
