import { fmtMoney, fmtNumber } from "@/composables/format";

/** Field metadata as sent by thinknxg_admin.api.docs (a subset of DocField). */
export interface Field {
	fieldname?: string;
	label?: string;
	fieldtype: string;
	options?: string;
	reqd?: number;
	read_only?: number;
	hidden?: number;
	default?: string;
	depends_on?: string;
	mandatory_depends_on?: string;
	read_only_depends_on?: string;
	in_list_view?: number;
	bold?: number;
	collapsible?: number;
	description?: string;
	fetch_from?: string;
	fetch_if_empty?: number;
	allow_on_submit?: number;
	precision?: string;
	no_write?: number;
	columns?: number;
	placeholder?: string;
	non_negative?: number;
	set_only_once?: number;
}
export interface FormMeta {
	doctype: string;
	slug: string;
	fields: Field[];
	children: Record<string, { fields: Field[] }>;
	title_field?: string;
	image_field?: string;
	is_submittable: number;
	issingle: number;
	naming_prompt: boolean;
	workflow: { name: string; state_field: string } | null;
	perms: Record<string, boolean>;
	description?: string;
}
export type Doc = Record<string, any>;

export const LAYOUT = new Set(["Section Break", "Column Break", "Tab Break"]);
export const NO_VALUE = new Set([...LAYOUT, "HTML", "Button", "Heading", "Fold", "Image"]);
export const TABLES = new Set(["Table", "Table MultiSelect"]);
export const NUMERIC = new Set(["Int", "Float", "Currency", "Percent", "Duration"]);

/** Evaluate a DocField condition the way the Desk does: "eval:<expr>" with doc
 *  (and parent for child rows) in scope, or a bare fieldname meaning "is set".
 *  The expressions are part of the DocType definition on this site. */
export function evalCondition(cond: string | undefined, doc: Doc, parent?: Doc): boolean {
	if (!cond) return true;
	const c = cond.trim();
	try {
		if (c.startsWith("eval:")) {
			// eslint-disable-next-line no-new-func
			return !!new Function("doc", "parent", "frappe", `return (${c.slice(5)});`)(doc, parent || {}, frappeShim);
		}
		if (c.startsWith("fn:")) return true; // form-script functions are not available outside the Desk
		const v = doc[c];
		return Array.isArray(v) ? v.length > 0 : !!v;
	} catch {
		return true;
	}
}
// The few helpers DocField conditions commonly use.
const frappeShim = {
	user: { has_role: (r: string | string[]) => [].concat(r as any).some((x) => (window as any).__nxgRoles?.includes(x)) },
	session: { get user() { return (window as any).__nxgUser; } },
	datetime: { get_today: () => new Date().toISOString().slice(0, 10), now_date: () => new Date().toISOString().slice(0, 10) },
	boot: { sysdefaults: {} },
};

export function docStatus(doc: Doc, statusField?: string | null): { label: string; tone: "neutral" | "success" | "warning" | "danger" | "info" } {
	const s = statusField ? doc[statusField] : null;
	const tone = (v: string): any => {
		const k = String(v || "").toLowerCase();
		if (/(cancel|reject|lost|overdue|absent|fail|stopped|closed lost|expired)/.test(k)) return "danger";
		if (/(draft|open|pending|to |hold|unpaid|partially|not started|awaiting|requested)/.test(k)) return "warning";
		if (/(paid|completed|approved|active|submitted|delivered|received|present|converted|accepted|done|cleared|billed|resolved)/.test(k)) return "success";
		return "info";
	};
	if (s) return { label: String(s), tone: tone(String(s)) };
	if (doc.docstatus === 2) return { label: "Cancelled", tone: "danger" };
	if (doc.docstatus === 1) return { label: "Submitted", tone: "success" };
	return { label: "Draft", tone: "warning" };
}

export function displayValue(value: any, field: { fieldtype: string; options?: string }, doc?: Doc): string {
	if (value === null || value === undefined || value === "") return "";
	switch (field.fieldtype) {
		case "Check":
			return value ? "Yes" : "No";
		case "Currency": {
			const cur = field.options && doc ? doc[field.options] || (field.options.includes(":") ? "" : field.options) : "";
			return fmtMoney(Number(value), cur || null);
		}
		case "Float":
		case "Int":
			return fmtNumber(Number(value));
		case "Percent":
			return `${fmtNumber(Number(value))}%`;
		case "Date":
			return new Date(String(value).slice(0, 10) + "T00:00:00").toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
		case "Datetime":
			return new Date(String(value).replace(" ", "T")).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
		default:
			return String(value).replace(/<[^>]+>/g, "");
	}
}

/** Tabs -> sections -> columns, the way the DocType lays them out. */
export interface Section { label?: string; collapsible?: number; depends_on?: string; columns: Field[][]; key: string }
export interface Tab { label: string; key: string; sections: Section[]; depends_on?: string }
export function layout(fields: Field[]): Tab[] {
	const tabs: Tab[] = [{ label: "Details", key: "tab-0", sections: [] }];
	let section: Section | null = null;
	const newSection = (f?: Field) => {
		section = { label: f?.label, collapsible: f?.collapsible, depends_on: f?.depends_on, columns: [[]], key: f?.fieldname || `s-${tabs.length}-${tabs[tabs.length - 1].sections.length}` };
		tabs[tabs.length - 1].sections.push(section);
	};
	for (const f of fields) {
		if (f.fieldtype === "Tab Break") {
			tabs.push({ label: f.label || "More", key: f.fieldname || `tab-${tabs.length}`, sections: [], depends_on: f.depends_on });
			section = null;
		} else if (f.fieldtype === "Section Break") {
			newSection(f);
		} else if (f.fieldtype === "Column Break") {
			if (!section) newSection();
			section!.columns.push([]);
		} else {
			if (!section) newSection();
			section!.columns[section!.columns.length - 1].push(f);
		}
	}
	return tabs
		.map((t) => ({ ...t, sections: t.sections.map((s) => ({ ...s, columns: s.columns.filter((c) => c.length) })).filter((s) => s.columns.length) }))
		.filter((t) => t.sections.length);
}

export function slugOf(doctype: string) {
	return doctype.toLowerCase().replace(/ /g, "-");
}
