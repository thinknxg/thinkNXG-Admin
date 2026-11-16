"""Notification center data. Mark-as-read uses Core's own whitelisted methods
(frappe.desk.doctype.notification_log.notification_log.mark_as_read / mark_all_as_read)."""

import frappe

from thinknxg_admin.api.utils import desk_route, doctype_exists, require_login


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
	items = [
		{
			**r,
			"subject": frappe.utils.strip_html(r.subject or ""),
			"from_name": names.get(r.from_user) or r.from_user,
			"route": desk_route(r.document_type, r.document_name) if r.document_type and r.document_name else None,
		}
		for r in rows
	]
	unread = frappe.db.count("Notification Log", {"for_user": user, "read": 0})
	todo = frappe.db.count("ToDo", {"allocated_to": user, "status": "Open"}) if doctype_exists("ToDo") else 0
	return {"items": items, "unread": unread, "open_todos": todo}
