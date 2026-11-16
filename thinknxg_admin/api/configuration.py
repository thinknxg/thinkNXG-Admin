"""System Configuration Center.

Edits a curated, explicitly allow-listed set of System Settings fields grouped by
purpose, plus log retention (Log Settings) and the Command Center's own branding.
Everything is saved through the Single DocType's own save, so System Settings
validation (session expiry format, password policy, 2FA method ...) still runs.
Fields that weaken security are flagged so the UI asks for confirmation.
"""

import frappe
from frappe import _
from frappe.utils import cint

from thinknxg_admin.api.utils import doctype_exists, require_admin

GROUPS = [
	("general", "General & regional", "Organisation name, language, time zone, currency and formats.", [
		"app_name", "country", "language", "time_zone", "currency", "first_day_of_the_week", "date_format", "time_format",
		"number_format", "use_number_format_from_currency", "float_precision", "currency_precision", "rounding_method",
	]),
	("security", "Sign-in & sessions", "How people sign in and how long sessions last.", [
		"session_expiry", "deny_multiple_sessions", "allow_login_using_mobile_number", "allow_login_using_user_name",
		"login_with_email_link", "login_with_email_link_expiry", "disable_user_pass_login", "allow_consecutive_login_attempts",
		"allow_login_after_fail", "logout_on_password_reset", "apply_strict_user_permissions", "disable_document_sharing",
		"document_share_key_expiry", "allow_error_traceback", "show_external_link_warning",
	]),
	("password", "Passwords", "Password strength, expiry and reset links.", [
		"enable_password_policy", "minimum_password_score", "force_user_to_reset_password", "password_reset_limit",
		"reset_password_link_expiry_duration",
	]),
	("two_factor", "Two-factor authentication", "Second factor for sign-in. Roles can require it individually.", [
		"enable_two_factor_auth", "two_factor_method", "otp_issuer_name", "lifespan_qrcode_image",
		"bypass_2fa_for_retricted_ip_users", "bypass_restrict_ip_check_if_2fa_enabled",
	]),
	("email", "Email", "Footer, templates and delivery retries. Accounts are managed in Integrations.", [
		"email_footer_address", "disable_standard_email_footer", "hide_footer_in_auto_email_reports", "attach_view_link",
		"email_retry_limit", "welcome_email_template", "reset_password_template", "max_auto_email_report_per_user",
	]),
	("files", "Files & uploads", "Upload limits and who may upload public files.", [
		"max_file_size", "allowed_file_extensions", "allow_guests_to_upload_files", "only_allow_system_managers_to_upload_public_files",
		"strip_exif_metadata_from_uploaded_images", "max_zip_extract_size",
	]),
	("system", "System", "Scheduler, backups, logging, limits and update notices.", [
		"enable_scheduler", "backup_limit", "encrypt_backup", "log_api_requests", "dormant_days", "max_report_rows",
		"link_field_results_limit", "delete_background_exported_reports_after", "enable_onboarding", "enable_telemetry",
		"disable_system_update_notification", "disable_change_log_notification",
	]),
]
ALLOWED = {f for _key, _label, _desc, fields in GROUPS for f in fields}

# Field -> (value that is risky, explanation). The UI confirms before saving these.
RISKY = {
	"disable_user_pass_login": (1, "Users can no longer sign in with a password. Make sure another sign-in method works first."),
	"enable_scheduler": (0, "Scheduled jobs, emails and automations stop running."),
	"allow_error_traceback": (1, "Full server tracebacks are shown to users, which can reveal internals."),
	"enable_password_policy": (0, "Weak passwords will be accepted."),
	"enable_two_factor_auth": (0, "Second-factor sign-in is switched off for everyone."),
	"allow_guests_to_upload_files": (1, "Visitors who are not signed in can upload files."),
	"bypass_2fa_for_retricted_ip_users": (1, "Users on restricted IPs skip two-factor authentication."),
	"apply_strict_user_permissions": (1, "Records with empty link fields are hidden from restricted users; review User Permissions first."),
}
LINK_OPTIONS = {
	"country": ("Country", {}),
	"language": ("Language", {"enabled": 1}),
	"currency": ("Currency", {"enabled": 1}),
	"welcome_email_template": ("Email Template", {}),
	"reset_password_template": ("Email Template", {}),
}


def _field(meta, doc, fieldname):
	df = meta.get_field(fieldname)
	if not df:
		return None
	out = {
		"fieldname": fieldname, "label": df.label or frappe.unscrub(fieldname), "fieldtype": df.fieldtype,
		"description": frappe.utils.strip_html(df.description or "")[:240] or None, "value": doc.get(fieldname),
	}
	if df.fieldtype == "Select":
		out["options"] = [o for o in (df.options or "").split("\n")]
	if fieldname == "time_zone":
		from frappe.core.doctype.user.user import get_timezones

		out["fieldtype"] = "Select"
		out["options"] = [""] + get_timezones()["timezones"]
	if df.fieldtype == "Link" and fieldname in LINK_OPTIONS:
		dt, filters = LINK_OPTIONS[fieldname]
		if doctype_exists(dt):
			filters = {k: v for k, v in filters.items() if frappe.get_meta(dt).has_field(k)}
			out["fieldtype"] = "Select"
			out["options"] = [""] + frappe.get_all(dt, filters=filters, pluck="name", order_by="name asc", limit=500)
	if fieldname in RISKY:
		out["risk"] = {"value": RISKY[fieldname][0], "message": RISKY[fieldname][1]}
	return out


@frappe.whitelist()
def get_configuration():
	require_admin()
	frappe.only_for("System Manager")
	doc = frappe.get_single("System Settings")
	meta = doc.meta
	groups = []
	for key, label, description, fields in GROUPS:
		rows = [r for r in (_field(meta, doc, f) for f in fields) if r]
		if rows:
			groups.append({"key": key, "label": label, "description": description, "fields": rows})

	logs = []
	if doctype_exists("Log Settings"):
		ls = frappe.get_single("Log Settings")
		logs = [{"ref_doctype": r.ref_doctype, "days": r.days} for r in (ls.get("logs_to_clear") or [])]

	branding = {}
	if doctype_exists("thinkNXG Admin Settings"):
		s = frappe.get_single("thinkNXG Admin Settings")
		branding = {"product_name": s.get("product_name"), "show_classic_desk_link": s.get("show_classic_desk_link")}
	if doctype_exists("Navbar Settings"):
		branding["app_logo"] = frappe.db.get_single_value("Navbar Settings", "app_logo")
	return {"groups": groups, "logs": logs, "branding": branding, "modified": doc.modified}


@frappe.whitelist(methods=["POST"])
def save_configuration(values, modified: str | None = None):
	"""Save allow-listed System Settings fields. Unknown keys are refused, not ignored."""
	require_admin()
	frappe.only_for("System Manager")
	values = frappe.parse_json(values) or {}
	unknown = set(values) - ALLOWED
	if unknown:
		frappe.throw(_("These settings can't be changed here: {0}").format(", ".join(sorted(unknown))))
	doc = frappe.get_single("System Settings")
	if modified and str(doc.modified) != str(modified):
		frappe.throw(_("System Settings were changed by someone else. Reload and try again."), frappe.TimestampMismatchError)
	for key, value in values.items():
		if doc.meta.get_field(key):
			doc.set(key, value)
	doc.save()
	frappe.clear_cache()
	return get_configuration()


@frappe.whitelist(methods=["POST"])
def save_log_retention(rows):
	"""Change how many days each existing log type is kept (Log Settings)."""
	require_admin()
	frappe.only_for("System Manager")
	wanted = {r["ref_doctype"]: cint(r["days"]) for r in (frappe.parse_json(rows) or []) if r.get("ref_doctype")}
	doc = frappe.get_single("Log Settings")
	for row in doc.get("logs_to_clear") or []:
		if row.ref_doctype in wanted:
			if wanted[row.ref_doctype] < 1:
				frappe.throw(_("Keep {0} for at least 1 day.").format(row.ref_doctype))
			row.days = wanted[row.ref_doctype]
	doc.save()
	return get_configuration()["logs"]


@frappe.whitelist(methods=["POST"])
def save_branding(product_name: str | None = None, show_classic_desk_link: int | None = None):
	require_admin()
	frappe.only_for("System Manager")
	doc = frappe.get_single("thinkNXG Admin Settings")
	if product_name is not None:
		doc.product_name = product_name.strip()[:60] or "thinkNXG ERP"
	if show_classic_desk_link is not None:
		doc.show_classic_desk_link = cint(show_classic_desk_link)
	doc.save()
	return True
