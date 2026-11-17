"""Site setup: point the classic Desk and website brand images at thinkNXG.

Website Settings and Navbar Settings are site data, so the app sets them on
install and through a one-time patch. A field is only changed when it is
empty or still holds a stock framework image; a logo an administrator
uploaded on purpose is kept.
"""

import frappe

BRAND_DIR = "/assets/thinknxg_admin/images/brand"
LOGO = f"{BRAND_DIR}/thinknxg-logo.png"
FAVICON = f"{BRAND_DIR}/favicon-32.png"

# (doctype, field, value)
TARGETS = (
	("Website Settings", "favicon", FAVICON),
	("Website Settings", "app_logo", LOGO),
	("Website Settings", "splash_image", LOGO),
	("Navbar Settings", "app_logo", LOGO),
)


def _is_stock(value: str | None) -> bool:
	"""Empty, or an image shipped by the framework (not uploaded by a user)."""
	if not value or value == "attach_files:":
		return True
	return value.startswith("/assets/frappe/")


def apply_brand_images(force: bool = False) -> list[str]:
	changed = []
	for doctype, field, value in TARGETS:
		if not frappe.db.exists("DocType", doctype):
			continue
		current = frappe.db.get_single_value(doctype, field)
		if current == value or not (force or _is_stock(current)):
			continue
		frappe.db.set_single_value(doctype, field, value)
		changed.append(f"{doctype}.{field}")
	if changed:
		frappe.clear_cache()
	return changed


def after_install():
	apply_brand_images()
