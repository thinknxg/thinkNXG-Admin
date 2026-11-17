app_name = "thinknxg_admin"
app_title = "thinkNXG Admin"
app_publisher = "Kreatao"
app_description = "Premium Admin Command Center for thinkNXG Core, thinkNXG ERP and thinkNXG HR (V16)"
app_email = "sales@kreatao.com"
app_license = "mit"
# The official mark ships with thinkNXG Core, so it exists on every thinkNXG site.
app_logo_url = "/assets/thinknxg_admin/images/brand/thinknxg-logo.png"
after_install = "thinknxg_admin.install.after_install"

# ERP and HR are optional: every ERP/HR-specific query is guarded.
required_apps = ["frappe"]

# Tile on the V16 apps screen (/desk)
add_to_apps_screen = [
	{
		"name": "thinknxg_admin",
		"logo": "/assets/thinknxg_admin/images/brand/thinknxg-logo.png",
		"title": "Command Center",
		"route": "/thinknxg",
		"has_permission": "thinknxg_admin.api.boot.has_app_permission",
	}
]

# The SPA owns every path under /thinknxg (same pattern as /banking and /hrms).
website_route_rules = [
	{"from_route": "/thinknxg/<path:app_path>", "to_route": "thinknxg"},
]

# Keep dashboard figures fresh when the things they count change.
_clear = "thinknxg_admin.api.cache.clear_dashboard_cache"
doc_events = {
	"User": {"on_update": _clear, "after_insert": _clear, "on_trash": [_clear, "thinknxg_admin.api.centers.on_user_trash"]},
	"Role": {"on_update": _clear, "on_trash": _clear},
	"Workspace": {"on_update": _clear, "on_trash": _clear},
	"Company": {"after_insert": _clear, "on_trash": _clear},
	"thinkNXG Admin Settings": {"on_update": _clear},
}

# Deliberately absent: app_include_js / app_include_css.
# The classic Desk at /desk is not restyled or patched in any way.
