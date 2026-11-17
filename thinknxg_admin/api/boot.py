import frappe

from thinknxg_admin import __version__
from thinknxg_admin.api.centers import center_levels, default_center, get_centers, get_preferences, personal_navigation
from thinknxg_admin.api.routes import get_registry
from thinknxg_admin.api.brand import DOCS, SUPPORT_URL, boot_links
from thinknxg_admin.api.navigation import get_app_launcher
from thinknxg_admin.api.utils import doctype_exists, has_field, is_admin, require_login

BRAND = {
	"name": "thinkNXG",
	"product": "thinkNXG ERP",
	"logo": "/assets/thinknxg_admin/images/brand/thinknxg-logo.png",
	"favicon": "/assets/thinknxg_admin/images/brand/favicon-32.png",
	"docs_url": DOCS["erp"],
	"support_url": SUPPORT_URL,
	"whats_new_url": DOCS["erp"],
	**boot_links(),
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


def build_boot() -> dict:
	user = frappe.session.user
	info = frappe.db.get_value("User", user, ["full_name", "user_image", "email", "desk_theme"], as_dict=True) or {}
	companies = _companies()
	default_company = frappe.defaults.get_user_default("Company")
	if default_company not in [c["name"] for c in companies]:
		default_company = companies[0]["name"] if companies else None
	settings = _settings()
	levels = center_levels()
	registry = get_registry([{"key": k, "access": v} for k, v in levels.items()])
	centers = get_centers(levels, registry)
	prefs = get_preferences()
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
		# Only the command centers the server grants; each carries its own
		# navigation and quick actions, already filtered by permission.
		"centers": centers,
		# Modules, DocTypes and reports this user may open (the route registry).
		"registry": registry,
		"default_center": default_center(centers, prefs),
		"preferences": prefs,
		# Shown when the user has no command center at all.
		"personal_navigation": personal_navigation(),
		"apps": get_app_launcher(),
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
