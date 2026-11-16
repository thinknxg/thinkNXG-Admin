"""Metadata and list data for the thinkNXG document list and form.

Reads only. Loading, saving, submitting, cancelling and workflow actions use
thinkNXG's own whitelisted methods directly from the browser
(frappe.desk.form.load.getdoc, frappe.desk.form.save.savedocs / cancel,
frappe.model.workflow.apply_workflow ...), so every validation, controller hook,
workflow rule and permission runs unchanged.

Every method here checks read permission on the DocType, and list rows come
from frappe.get_list / the permission-aware query builder, so User Permissions
and record-level rules always apply on the server.
"""

import json

import frappe
from frappe import _
from frappe.utils import cint

from thinknxg_admin.api.routes import internal_route, slug
from thinknxg_admin.api.utils import doctype_exists, require_login

LAYOUT = {"Section Break", "Column Break", "Tab Break"}
NO_VALUE = LAYOUT | {"HTML", "Button", "Heading", "Fold", "Image"}
FIELD_KEYS = (
	"fieldname", "label", "fieldtype", "options", "reqd", "read_only", "hidden", "default", "depends_on",
	"mandatory_depends_on", "read_only_depends_on", "in_list_view", "in_standard_filter", "bold", "collapsible",
	"collapsible_depends_on", "description", "fetch_from", "fetch_if_empty", "allow_on_submit", "precision",
	"length", "no_copy", "permlevel", "columns", "non_negative", "set_only_once", "translatable", "placeholder",
)
PTYPES = ("read", "write", "create", "delete", "submit", "cancel", "amend", "print", "email", "export", "report", "import", "share")


def resolve_doctype(value: str) -> str:
	"""A DocType name from its name or URL slug ("sales-invoice", "bom")."""
	if value and doctype_exists(value):
		return value
	guess = (value or "").replace("-", " ").strip()
	name = frappe.db.get_value("DocType", {"name": ["like", guess]}, "name") if guess else None
	if not name:
		frappe.throw(_("{0} is not available on this site.").format(value or ""), frappe.DoesNotExistError)
	return name


def _need_read(doctype: str) -> str:
	require_login()
	doctype = resolve_doctype(doctype)
	if not frappe.has_permission(doctype, "read"):
		frappe.throw(_("You do not have access to {0}.").format(_(doctype)), frappe.PermissionError)
	return doctype


def _perms(doctype: str) -> dict:
	return {p: bool(frappe.has_permission(doctype, p)) for p in PTYPES}


def _fields(meta, parenttype=None) -> list[dict]:
	permitted = set(meta.get_permitted_fieldnames(parenttype=parenttype))
	write = set(meta.get_permitted_fieldnames(parenttype=parenttype, permission_type="write"))
	out = []
	for df in meta.fields:
		if df.fieldtype not in LAYOUT and df.fieldname not in permitted and df.fieldtype not in NO_VALUE:
			continue
		row = {k: df.get(k) for k in FIELD_KEYS if df.get(k) not in (None, "", 0)}
		row["fieldtype"] = df.fieldtype
		if df.fieldname and df.fieldtype not in NO_VALUE and df.fieldname not in write:
			row["no_write"] = 1
		out.append(row)
	return out


def _status_field(meta):
	for f in ("status", "workflow_state", "approval_status"):
		if meta.has_field(f):
			return f
	return None


@frappe.whitelist()
def get_list_meta(doctype: str):
	doctype = _need_read(doctype)
	meta = frappe.get_meta(doctype)
	permitted = set(meta.get_permitted_fieldnames())
	columns = [
		{"fieldname": df.fieldname, "label": df.label, "fieldtype": df.fieldtype, "options": df.options}
		for df in meta.fields
		if df.in_list_view and df.fieldname in permitted and df.fieldtype not in NO_VALUE and df.fieldtype not in ("Table", "Table MultiSelect", "Text Editor", "Long Text")
	][:6]
	filters = [
		{"fieldname": df.fieldname, "label": df.label, "fieldtype": df.fieldtype, "options": df.options}
		for df in meta.fields
		if df.in_standard_filter and df.fieldname in permitted and df.fieldtype in ("Link", "Select", "Data", "Date", "Check", "Dynamic Link")
	]
	status = _status_field(meta)
	if status and status not in [f["fieldname"] for f in filters]:
		df = meta.get_field(status)
		filters.insert(0, {"fieldname": status, "label": df.label, "fieldtype": df.fieldtype, "options": df.options})
	title = meta.get_title_field()
	return {
		"doctype": doctype,
		"slug": slug(doctype),
		"title_field": title if title != "name" and title in permitted else None,
		"status_field": status if status in permitted else None,
		"image_field": meta.image_field if meta.image_field in permitted else None,
		"is_submittable": cint(meta.is_submittable),
		"issingle": cint(meta.issingle),
		"is_tree": cint(meta.is_tree),
		"columns": columns,
		"filters": filters,
		"sort_field": meta.sort_field or "creation",
		"sort_order": meta.sort_order or "DESC",
		"perms": _perms(doctype),
		"description": meta.description,
		"route": internal_route(doctype),
	}


def _clean_filters(doctype, filters):
	"""Accept {field: value} or [[field, op, value]] for fields the user may read."""
	if isinstance(filters, str):
		filters = json.loads(filters or "[]")
	meta = frappe.get_meta(doctype)
	permitted = set(meta.get_permitted_fieldnames()) | {"name", "docstatus", "owner", "creation", "modified", "_assign"}
	allowed_ops = {"=", "!=", ">", "<", ">=", "<=", "like", "not like", "in", "not in", "between", "is", "descendants of (inclusive)"}
	out = []
	items = filters.items() if isinstance(filters, dict) else []
	for k, v in items:
		out.append([k, "in", v] if isinstance(v, list) else [k, "=", v])
	if isinstance(filters, list):
		out += [list(f[-3:]) for f in filters if isinstance(f, (list, tuple)) and len(f) >= 3]
	clean = []
	for field, op, value in out:
		if field in permitted and str(op).lower() in allowed_ops:
			clean.append([doctype, field, op, value])
	return clean


@frappe.whitelist()
def get_list(doctype: str, filters=None, search: str | None = None, order_by: str | None = None, start: int = 0, page_length: int = 20, fields=None):
	"""One page of rows plus the total, both under the user's permissions."""
	doctype = _need_read(doctype)
	meta = frappe.get_meta(doctype)
	permitted = set(meta.get_permitted_fieldnames())
	if isinstance(fields, str):
		fields = json.loads(fields or "[]")
	base = ["name", "docstatus", "modified", "owner"]
	extra = [f for f in (fields or []) if f in permitted]
	for f in (meta.get_title_field(), _status_field(meta), meta.image_field):
		if f and f in permitted:
			extra.append(f)
	select = list(dict.fromkeys(base + extra))
	flt = _clean_filters(doctype, filters or [])
	or_filters = None
	if search and search.strip():
		like = f"%{search.strip()}%"
		search_fields = [f for f in ["name", meta.get_title_field(), *(meta.search_fields or "").split(",")] if f and f.strip() in permitted | {"name"}]
		or_filters = [[doctype, f.strip(), "like", like] for f in dict.fromkeys(search_fields)]
	parts = (order_by or "").split()
	sort_field = parts[0] if parts else (meta.sort_field or "creation")
	sort_dir = parts[1] if len(parts) > 1 else (meta.sort_order or "desc")
	if sort_field not in permitted | {"name", "creation", "modified"}:
		sort_field = "creation"
	sort_dir = "asc" if str(sort_dir).lower() == "asc" else "desc"
	page_length = max(1, min(cint(page_length) or 20, 500))
	start = max(0, cint(start))
	rows = frappe.get_list(doctype, fields=select, filters=flt, or_filters=or_filters, order_by=f"{sort_field} {sort_dir}",
		start=start, page_length=page_length)
	total = start + len(rows) if (not start and len(rows) < page_length) else _count(doctype, flt, or_filters)
	return {"rows": rows, "total": total}


@frappe.whitelist()
def get_form_meta(doctype: str):
	"""Everything the form needs to lay out one DocType, with its child tables."""
	doctype = _need_read(doctype)
	meta = frappe.get_meta(doctype)
	children = {}
	for df in meta.get_table_fields():
		cm = frappe.get_meta(df.options)
		children[df.options] = {"fields": _fields(cm, parenttype=doctype), "istable": 1}
	workflow = None
	from frappe.model.workflow import get_workflow_name

	wf_name = get_workflow_name(doctype)
	if wf_name:
		workflow = {"name": wf_name, "state_field": frappe.db.get_value("Workflow", wf_name, "workflow_state_field")}
	return {
		"doctype": doctype,
		"slug": slug(doctype),
		"fields": _fields(meta),
		"children": children,
		"title_field": meta.get_title_field(),
		"image_field": meta.image_field,
		"is_submittable": cint(meta.is_submittable),
		"issingle": cint(meta.issingle),
		"istable": cint(meta.istable),
		"autoname": meta.autoname,
		"naming_prompt": (meta.autoname or "").lower() == "prompt",
		"track_changes": cint(meta.track_changes),
		"allow_rename": cint(meta.allow_rename),
		"workflow": workflow,
		"perms": _perms(doctype),
		"route": internal_route(doctype),
		"description": meta.description,
	}


@frappe.whitelist()
def get_new_doc(doctype: str):
	"""Defaults for a new document, the way the Desk computes them on the server."""
	require_login()
	doctype = resolve_doctype(doctype)
	if not frappe.has_permission(doctype, "create"):
		frappe.throw(_("You cannot create {0}.").format(_(doctype)), frappe.PermissionError)
	doc = frappe.new_doc(doctype)
	return doc.as_dict()


@frappe.whitelist()
def get_module_overview(center: str, module: str):
	"""Counts for a module page: total, drafts and (submittable) to submit, per DocType the user may read."""
	from thinknxg_admin.api.centers import require_center
	from thinknxg_admin.api.routes import MODULES

	require_center(center)
	mod = next((m for m in MODULES.get(center, []) if m["key"] == module), None)
	if not mod:
		frappe.throw(_("Unknown module."), frappe.DoesNotExistError)
	out = []
	seen = set()
	for _label, doctypes in mod["groups"]:
		for dt in doctypes:
			if dt in seen or not doctype_exists(dt) or not frappe.has_permission(dt, "read"):
				continue
			seen.add(dt)
			meta = frappe.get_meta(dt)
			row = {"doctype": dt, "slug": slug(dt), "total": _count(dt, {})}
			if meta.is_submittable:
				row["drafts"] = _count(dt, {"docstatus": 0})
			out.append(row)
	return {"doctypes": out}


def _count(doctype, filters, or_filters=None):
	rows = frappe.qb.get_query(doctype, fields=[{"COUNT": "*", "as": "n"}], filters=filters, or_filters=or_filters, ignore_permissions=False).run(as_dict=True)
	return int(rows[0].n or 0) if rows else 0


@frappe.whitelist()
def resolve(path: str):
	"""Translate an old Desk address (from a saved favourite, a notification, a
	link in a document) into its internal route."""
	from thinknxg_admin.api.routes import from_desk_path

	require_login()
	return from_desk_path(path or "")
