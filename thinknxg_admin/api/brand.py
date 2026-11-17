"""thinkNXG brand names and links: the single source for every product name and
documentation, support and cloud link the Command Center shows.

Text that comes from other apps (app titles, descriptions, app-screen entries)
passes through ``rebrand()`` before it reaches the browser, so upstream names
never appear in the interface. Never link to the original Frappe documentation.
"""

import re

DOCS = {
	"crm": "https://docs.thinknxg.com/thinknxgcrm",
	"raven": "https://docs.thinknxg.com/thinknxgraven",
	"hr": "https://docs.thinknxg.com/thinknxghr",
	"erp": "https://docs.thinknxg.com/thinknxgerp",
	"framework": "https://docs.thinknxg.com/thinknxgframework",
	"cloud": "https://docs.thinknxg.com/thinknxgcloud",
	"thinkdesk": "https://docs.thinknxg.com/thinkdesk",
}
SUPPORT_URL = "https://thinknxg.com/thinkdesk"
CLOUD_URL = "https://thinknxgcloud.com/"
INSIGHTS_URL = "https://thinknxg.com/insights"

# Help menu entries, in order.
HELP_LINKS = [
	{"key": "erp", "label": "thinkNXG ERP documentation", "url": DOCS["erp"]},
	{"key": "hr", "label": "thinkNXG HR documentation", "url": DOCS["hr"]},
	{"key": "framework", "label": "thinkNXG Framework documentation", "url": DOCS["framework"]},
	{"key": "crm", "label": "thinkNXG CRM documentation", "url": DOCS["crm"]},
	{"key": "raven", "label": "thinkNXG Raven documentation", "url": DOCS["raven"]},
	{"key": "thinkdesk", "label": "thinkDesk documentation", "url": DOCS["thinkdesk"]},
	{"key": "cloud", "label": "thinkNXG Cloud documentation", "url": DOCS["cloud"]},
]

# Installed app -> its documentation.
APP_DOCS = {
	"frappe": DOCS["framework"], "thinknxg_admin": DOCS["framework"], "erpnext": DOCS["erp"], "hrms": DOCS["hr"],
	"crm": DOCS["crm"], "raven": DOCS["raven"], "helpdesk": DOCS["thinkdesk"], "lending": DOCS["erp"], "payments": DOCS["erp"],
	"insights": INSIGHTS_URL,
}
APP_TITLES = {
	"frappe": "thinkNXG Framework", "erpnext": "thinkNXG ERP", "hrms": "thinkNXG HR", "crm": "thinkNXG CRM",
	"raven": "thinkNXG Raven", "helpdesk": "thinkDesk", "insights": "thinkNXG Insights",
}

# Longest names first, so "Frappe Cloud Marketplace" wins over "Frappe Cloud" and "Frappe".
_NAMES = [
	("https://frappe.io/insights", INSIGHTS_URL),
	("frappe.io/insights", "thinknxg.com/insights"),
	("Frappe Cloud Marketplace", "thinkNXG Cloud Marketplace"),
	("Frappe Framework", "thinkNXG Framework"),
	("Frappe Insights", "thinkNXG Insights"),
	("Frappe Cloud", "thinkNXG Cloud"),
	("Frappe CRM", "thinkNXG CRM"),
	("Frappe HR", "thinkNXG HR"),
	("ERPNext", "thinkNXG ERP"),
	("Helpdesk", "thinkDesk"),
	("Raven", "thinkNXG Raven"),
	("Frappe", "thinkNXG"),
]
_PATTERN = re.compile("|".join(r"(?<![\w./-])" + re.escape(a) + r"(?![\w])" for a, _ in _NAMES))
_MAP = dict(_NAMES)
_HRMS = re.compile(r"(?<![\w./-])(hrms|HRMS)(?![\w./-])")


def rebrand(text):
	"""Replace upstream product names in display text. Leaves code-like tokens
	(module paths, URLs other than the Insights page, ``frappe.``) alone."""
	if not text or not isinstance(text, str):
		return text
	out = _PATTERN.sub(lambda m: _MAP[m.group(0)], text)
	out = out.replace("thinkNXG thinkNXG", "thinkNXG")
	return _HRMS.sub("thinkNXG HR", out)


def app_title(app: str, title: str | None = None) -> str:
	return APP_TITLES.get(app) or rebrand(title) or app


def boot_links() -> dict:
	return {"docs": DOCS, "help": HELP_LINKS, "support_url": SUPPORT_URL, "cloud_url": CLOUD_URL, "insights_url": INSIGHTS_URL}
