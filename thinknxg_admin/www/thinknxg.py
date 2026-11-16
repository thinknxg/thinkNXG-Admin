"""Entry page for the thinkNXG Admin SPA (/thinknxg and every sub-path)."""

from urllib.parse import quote

import frappe
from frappe.sessions import get_csrf_token

from thinknxg_admin.api.boot import build_boot

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=" + quote(frappe.request.path if frappe.request else "/thinknxg")
		raise frappe.Redirect

	if frappe.db.get_value("User", frappe.session.user, "user_type") != "System User":
		frappe.local.flags.redirect_location = "/me"
		raise frappe.Redirect

	# json.dumps does not escape "</", which could close the script tag early.
	context.boot_json = frappe.as_json(build_boot(), indent=None).replace("</", "<\\/")
	context.csrf_token = get_csrf_token()
	context.no_cache = 1
	return context
