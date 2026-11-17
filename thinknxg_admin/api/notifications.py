"""Notification center data. Mark-as-read uses Core's own whitelisted methods
(frappe.desk.doctype.notification_log.notification_log.mark_as_read / mark_all_as_read)."""

import frappe

from thinknxg_admin.api.brand import rebrand
from thinknxg_admin.api.utils import desk_route, doctype_exists, require_login

# Unified categories, decided on the server from each notification's document
# type. First match wins, in this order.
CATEGORIES = ("Approvals", "Finance", "Operations", "People", "System")
APPROVAL_DOCTYPES = {"Workflow Action", "Leave Application", "Expense Claim", "Shift Request", "Attendance Request", "Compensatory Leave Request"}
FINANCE_MODULES = {"Accounts", "Assets", "Budget", "Banking"}
PEOPLE_EXTRA = {"Employee", "Department", "Designation", "Branch", "Holiday List", "Employee Group", "Employee Grade"}
_CACHE_KEY = "thinknxg_admin:notification_categories"


def category_sets() -> dict[str, set[str]]:
	"""DocType sets per category (cached for 10 minutes; built from module/app metadata)."""
	cached = frappe.cache.get_value(_CACHE_KEY)
	if cached:
		return {k: set(v) for k, v in cached.items()}
	apps = dict(frappe.get_all("Module Def", fields=["name", "app_name"], as_list=True))
	approvals = set(APPROVAL_DOCTYPES)
	if doctype_exists("Workflow"):
		approvals |= set(frappe.get_all("Workflow", filters={"is_active": 1}, pluck="document_type"))
	finance, operations, people = set(), set(), set(PEOPLE_EXTRA)
	for name, module in frappe.get_all("DocType", fields=["name", "module"], as_list=True):
		app = apps.get(module)
		if app == "hrms":
			people.add(name)
		elif app == "erpnext" and name not in PEOPLE_EXTRA:
			(finance if module in FINANCE_MODULES else operations).add(name)
	out = {"Approvals": approvals, "People": people - approvals, "Finance": finance - approvals - people, "Operations": operations - approvals - people}
	frappe.cache.set_value(_CACHE_KEY, {k: sorted(v) for k, v in out.items()}, expires_in_sec=600)
	return out


def category_of(document_type, sets=None) -> str:
	sets = sets or category_sets()
	for name in ("Approvals", "People", "Finance", "Operations"):
		if document_type and document_type in sets[name]:
			return name
	return "System"


@frappe.whitelist()
def get_notifications(limit: int = 20):
	require_login()
	user = frappe.session.user
	if not doctype_exists("Notification Log"):
		return {"items": [], "unread": 0}
	limit = max(1, min(int(limit or 20), 50))
	rows = frappe.get_list(
		"Notification Log",
		filters={"for_user": user},
		fields=["name", "subject", "type", "document_type", "document_name", "from_user", "read", "creation"],
		order_by="creation desc",
		limit=limit,
	)
	senders = {r.from_user for r in rows if r.from_user}
	names = dict(frappe.get_all("User", filters={"name": ["in", list(senders)]}, fields=["name", "full_name"], as_list=True)) if senders else {}
	sets = category_sets()
	items = [
		{
			**r,
			"category": category_of(r.document_type, sets),
			"subject": rebrand(frappe.utils.strip_html(r.subject or "")),
			"from_name": names.get(r.from_user) or r.from_user,
			"route": desk_route(r.document_type, r.document_name) if r.document_type and r.document_name else None,
		}
		for r in rows
	]
	unread = frappe.db.count("Notification Log", {"for_user": user, "read": 0})
	todo = frappe.db.count("ToDo", {"allocated_to": user, "status": "Open"}) if doctype_exists("ToDo") else 0
	return {"items": items, "unread": unread, "open_todos": todo}


def _route(r):
	link = (r.get("link") or "").strip()
	if link.startswith("/") and not link.startswith("//"):
		from thinknxg_admin.api.routes import from_desk_path

		return from_desk_path(link) if link.startswith(("/app", "/desk")) else link
	if r.get("document_type") and r.get("document_name"):
		return desk_route(r.document_type, r.document_name)
	return None


@frappe.whitelist()
def list_notifications(type: str | None = None, unread_only: int = 0, start: int = 0, page_length: int = 30, category: str | None = None):
	"""The current user's notifications for the Notification Center. Only ever their own."""
	require_login()
	if not doctype_exists("Notification Log"):
		return None
	from frappe.utils import cint

	user = frappe.session.user
	filters = {"for_user": user}
	if type:
		filters["type"] = type
	if cint(unread_only):
		filters["read"] = 0
	sets = category_sets()
	if category in ("Approvals", "People", "Finance", "Operations"):
		filters["document_type"] = ["in", sorted(sets[category]) or [""]]
	elif category == "System":
		known = sorted(set().union(*sets.values()))
		filters["document_type"] = ["not in", known or [""]]
	fields = ["name", "subject", "type", "document_type", "document_name", "from_user", "read", "creation"]
	meta = frappe.get_meta("Notification Log")
	for f in ("link", "title"):
		if meta.has_field(f):
			fields.append(f)
	rows = frappe.get_list("Notification Log", filters=filters, fields=fields, order_by="creation desc",
		start=cint(start), page_length=max(10, min(cint(page_length) or 30, 100)))
	senders = {r.from_user for r in rows if r.from_user}
	names = dict(frappe.get_all("User", filters={"name": ["in", list(senders)]}, fields=["name", "full_name"], as_list=True)) if senders else {}
	images = dict(frappe.get_all("User", filters={"name": ["in", list(senders)]}, fields=["name", "user_image"], as_list=True)) if senders else {}
	for r in rows:
		r["subject"] = rebrand(frappe.utils.strip_html(r.get("subject") or r.get("title") or ""))
		r["from_name"] = names.get(r.from_user) or r.from_user
		r["from_image"] = images.get(r.from_user)
		r["route"] = _route(r)
		r["category"] = category_of(r.document_type, sets)
	by_category = dict.fromkeys(CATEGORIES, 0)
	for doctype, n in frappe.db.sql("select document_type, count(*) from `tabNotification Log` where for_user = %s and `read` = 0 group by document_type", user):
		by_category[category_of(doctype, sets)] += n
	counts = {
		t or "Other": n
		for t, n in frappe.db.sql("select type, count(*) from `tabNotification Log` where for_user = %s and `read` = 0 group by type", user)
	}
	return {
		"rows": rows,
		"total": frappe.db.count("Notification Log", filters),
		"unread_by_type": counts,
		"unread_by_category": by_category,
		"categories": list(CATEGORIES),
		"unread": sum(counts.values()),
		"types": [t for (t,) in frappe.db.sql("select distinct type from `tabNotification Log` where for_user = %s and ifnull(type, '') != '' order by type", user)],
	}


SETTING_FIELDS = ("enabled", "enable_email_notifications", "enable_email_mention", "enable_email_assignment", "enable_email_share",
	"enable_email_event_reminders", "enable_email_threads_on_assigned_document")


@frappe.whitelist()
def get_settings():
	require_login()
	if not doctype_exists("Notification Settings"):
		return None
	name = frappe.session.user
	if not frappe.db.exists("Notification Settings", name):
		return {f: 1 for f in SETTING_FIELDS} | {"subscribed_documents": []}
	doc = frappe.get_doc("Notification Settings", name)
	out = {f: doc.get(f) for f in SETTING_FIELDS if doc.meta.has_field(f)}
	out["subscribed_documents"] = [r.document for r in (doc.get("subscribed_documents") or []) if r.get("document")]
	return out


@frappe.whitelist(methods=["POST"])
def update_settings(values):
	"""Update the session user's own Notification Settings."""
	require_login()
	values = frappe.parse_json(values) or {}
	name = frappe.session.user
	if frappe.db.exists("Notification Settings", name):
		doc = frappe.get_doc("Notification Settings", name)
	else:
		doc = frappe.new_doc("Notification Settings")
		doc.name = name
	for f in SETTING_FIELDS:
		if f in values and doc.meta.has_field(f):
			doc.set(f, 1 if values[f] else 0)
	if "subscribed_documents" in values and doc.meta.has_field("subscribed_documents"):
		doc.set("subscribed_documents", [{"document": d} for d in values["subscribed_documents"] or []])
	if doc.is_new():
		doc.insert(ignore_permissions=True)  # a user's own settings record, named after them
	else:
		doc.save(ignore_permissions=doc.name == frappe.session.user)
	return get_settings()
