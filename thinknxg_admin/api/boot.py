import frappe

from thinknxg_admin import __version__
from thinknxg_admin.api.navigation import get_app_launcher, get_navigation
from thinknxg_admin.api.utils import doctype_exists, has_field, is_admin, require_login

BRAND = {
	"name": "thinkNXG",
	"product": "thinkNXG ERP",
	"logo": "/assets/frappe/images/thinkNXG-favicon.png",
	"docs_url": "https://docs.thinknxg.com/thinknxgerp",
	"support_url": "https://thinknxg.com/thinkdesk",
	"whats_new_url": "https://docs.thinknxg.com/thinknxgerp",
}


def has_app_permission() -> bool:
	if frappe.session.user == "Guest":
		return False
	return frappe.db.get_value("User", frappe.session.user, "user_type") == "System User"


def _settings() -> dict:
	out = {"product_name": None, "show_classic_desk_link": 1}
	if doctype_exists("thinkNXG Admin Settings"):
		try:
			s = frappe.get_cached_doc("thinkNXG Admin Settings")
			out["product_name"] = s.get("product_name")
			out["show_classic_desk_link"] = s.get("show_classic_desk_link")
		except Exception:
			pass
	return out


def _companies():
	if not doctype_exists("Company"):
		return []
	try:
		fields = ["name"] + [f for f in ("abbr", "default_currency") if has_field("Company", f)]
		return frappe.get_list("Company", fields=fields, order_by="name asc", limit_page_length=500)
	except frappe.PermissionError:
		return []


def _quick_create():
	"""New-record shortcuts, only for DocTypes the user may create."""
	candidates = [("User", "user"), ("Role", "role"), ("Company", "building-2"), ("Workspace", "panels-top-left"), ("Workflow", "workflow"), ("Webhook", "plug")]
	return [
		{"doctype": dt, "icon": icon, "route": f"/desk/{dt.lower().replace(' ', '-')}/new"}
		for dt, icon in candidates
		if doctype_exists(dt) and frappe.has_permission(dt, "create")
	]


def build_boot() -> dict:
	user = frappe.session.user
	info = frappe.db.get_value("User", user, ["full_name", "user_image", "email", "desk_theme"], as_dict=True) or {}
	companies = _companies()
	default_company = frappe.defaults.get_user_default("Company")
	if default_company not in [c["name"] for c in companies]:
		default_company = companies[0]["name"] if companies else None
	settings = _settings()
	brand = dict(BRAND)
	if settings.get("product_name"):
		brand["product"] = settings["product_name"]
	return {
		"user": {
			"name": user,
			"full_name": info.get("full_name") or user,
			"email": info.get("email"),
			"image": info.get("user_image"),
			"theme": info.get("desk_theme") or "Light",
			"roles": frappe.get_roles(user),
			"is_admin": is_admin(user),
		},
		"brand": brand,
		"version": __version__,
		"navigation": get_navigation(),
		"apps": get_app_launcher(),
		"quick_create": _quick_create(),
		"companies": companies,
		"default_company": default_company,
		"show_classic_desk_link": bool(settings.get("show_classic_desk_link", 1)),
		"site": frappe.local.site,
		# System-timezone "now", so the browser can show relative times correctly
		# even when its own timezone differs from the site's.
		"server_now": frappe.utils.now(),
	}


@frappe.whitelist()
def get_boot():
	require_login()
	return build_boot()
