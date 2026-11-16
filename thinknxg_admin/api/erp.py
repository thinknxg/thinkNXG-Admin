"""ERP Command Center data.

Every figure is read from submitted thinkNXG ERP records through the core query
builder with permissions on (``frappe.qb.get_query(..., ignore_permissions=False)``),
so role permissions and User Permissions (company, warehouse, customer...) apply
to every count and total. Nothing here is estimated or hard-coded.

Per figure:
  restricted  the user cannot read the source DocType; no number is sent
  value=None  the source DocType is not installed ("Not available")

Monetary totals are in the selected company's default currency, which is why a
company is always resolved (the user's default, else the first they may see).
"""

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, flt, getdate, today

from thinknxg_admin.api.cache import cached_panel
from thinknxg_admin.api.centers import permitted_companies, require_center, validate_company
from thinknxg_admin.api.figures import Missing, Restricted, _between, _check, _count, _figure, _one, _part, _q, _quiet
from thinknxg_admin.api.utils import delta, desk_route, doctype_exists, has_field, slug

SECTIONS = ("sales", "finance", "purchase", "inventory", "manufacturing", "projects", "crm")
OPEN_SO = ["To Deliver and Bill", "To Bill", "To Deliver"]
OPEN_PO = ["To Receive and Bill", "To Bill", "To Receive"]
DONE_WO = ["Completed", "Stopped", "Closed", "Cancelled"]
DONE_TASK = ["Completed", "Cancelled", "Template"]


# Context ------------------------------------------------------------------------

def _context(company=None, fiscal_year=None, days=None, branch=None) -> frappe._dict:
	require_center("erp")
	company = validate_company(company)
	if not company:
		allowed = permitted_companies()
		preferred = frappe.defaults.get_user_default("Company")
		company = preferred if preferred in allowed else (allowed[0] if allowed else None)
	if not company:
		frappe.throw(_("You do not have access to any company."), frappe.PermissionError)

	if fiscal_year:
		fy = frappe.get_list("Fiscal Year", filters={"name": fiscal_year, "disabled": 0}, fields=["year_start_date", "year_end_date"], limit=1)
		if not fy:
			frappe.throw(_("Fiscal year {0} is not available to you.").format(fiscal_year), frappe.PermissionError)
		start, end = getdate(fy[0].year_start_date), getdate(fy[0].year_end_date)
	else:
		try:
			n = max(1, min(int(days or 30), 366))
		except (TypeError, ValueError):
			n = 30
		end = getdate(today())
		start = add_days(end, -(n - 1))
	length = date_diff(end, start) + 1
	prev_end = add_days(start, -1)
	prev_start = add_days(prev_end, -(length - 1))

	dim = None
	if branch:
		dim = frappe.db.get_value("Accounting Dimension", {"document_type": "Branch", "disabled": 0}, "fieldname") if doctype_exists("Accounting Dimension") else None
		if not dim:
			frappe.throw(_("Branch is not set up as an accounting dimension."))
		if branch not in frappe.get_list("Branch", pluck="name", limit_page_length=1000):
			frappe.throw(_("You do not have access to branch {0}.").format(branch), frappe.PermissionError)

	return frappe._dict(
		company=company,
		currency=frappe.get_cached_value("Company", company, "default_currency"),
		start=start, end=end, prev_start=prev_start, prev_end=prev_end,
		today=getdate(today()), branch=branch, dim=dim,
		fiscal_year=fiscal_year,
	)


def _f(ctx, doctype: str, extra: dict | None = None, company=True) -> dict:
	"""Base filters: company and (when chosen) the branch dimension."""
	f = {}
	if company and has_field(doctype, "company"):
		f["company"] = ctx.company
	if ctx.dim and ctx.branch and has_field(doctype, ctx.dim):
		f[ctx.dim] = ctx.branch
	f.update(extra or {})
	return f


def _accounts(ctx, **filters) -> list[str]:
	"""Account names for the company by type. Names only (chart metadata), no balances."""
	return frappe.get_all("Account", filters={"company": ctx.company, "is_group": 0, **filters}, pluck="name")


def _list_route(doctype, **params):
	from urllib.parse import urlencode

	q = urlencode({k: v for k, v in params.items() if v is not None})
	return f"/desk/{slug(doctype)}" + (f"?{q}" if q else "")


# KPIs -------------------------------------------------------------------------------

def _gl_sum(ctx, accounts, start, end, sign=1):
	"""Credit minus debit (sign=1) or debit minus credit (sign=-1) on the accounts."""
	if not accounts:
		return 0.0
	r = _one("GL Entry", [{"SUM": "debit", "as": "dr"}, {"SUM": "credit", "as": "cr"}],
		_f(ctx, "GL Entry", {"account": ["in", accounts], "is_cancelled": 0, "posting_date": _between(start, end)}))
	return sign * (flt(r.cr) - flt(r.dr))


def kpi_revenue(ctx):
	_check("GL Entry")
	income = _accounts(ctx, root_type="Income")
	cur = _gl_sum(ctx, income, ctx.start, ctx.end)
	prev = _gl_sum(ctx, income, ctx.prev_start, ctx.prev_end)
	return {"value": cur, "delta": delta(cur, prev), "currency": ctx.currency, "route": "/desk/query-report/Profit and Loss Statement"}


def kpi_gross_profit(ctx):
	_check("GL Entry")
	income = _accounts(ctx, root_type="Income")
	cogs = _accounts(ctx, account_type="Cost of Goods Sold")
	cur = _gl_sum(ctx, income, ctx.start, ctx.end) - _gl_sum(ctx, cogs, ctx.start, ctx.end, sign=-1)
	prev = _gl_sum(ctx, income, ctx.prev_start, ctx.prev_end) - _gl_sum(ctx, cogs, ctx.prev_start, ctx.prev_end, sign=-1)
	rev = _gl_sum(ctx, income, ctx.start, ctx.end)
	margin = round(cur * 100.0 / rev, 1) if rev else None
	return {"value": cur, "delta": delta(cur, prev), "secondary": margin, "currency": ctx.currency, "route": "/desk/query-report/Gross Profit"}


def kpi_cash_bank(ctx):
	_check("GL Entry")
	accounts = _accounts(ctx, account_type=["in", ["Cash", "Bank"]])
	if not accounts:
		return {"value": 0.0, "currency": ctx.currency}
	r = _one("GL Entry", [{"SUM": "debit", "as": "dr"}, {"SUM": "credit", "as": "cr"}],
		_f(ctx, "GL Entry", {"account": ["in", accounts], "is_cancelled": 0, "posting_date": ["<=", ctx.end]}))
	return {"value": flt(r.dr) - flt(r.cr), "currency": ctx.currency, "secondary": len(accounts), "route": "/desk/query-report/General Ledger"}


def _ple_balance(ctx, account_type):
	r = _one("Payment Ledger Entry", [{"SUM": "amount", "as": "amt"}],
		_f(ctx, "Payment Ledger Entry", {"account_type": account_type, "delinked": 0, "posting_date": ["<=", ctx.end]}))
	return flt(r.amt)


def kpi_receivables(ctx):
	_check("Payment Ledger Entry")
	return {"value": _ple_balance(ctx, "Receivable"), "currency": ctx.currency, "route": "/desk/query-report/Accounts Receivable"}


def kpi_payables(ctx):
	_check("Payment Ledger Entry")
	return {"value": _ple_balance(ctx, "Payable"), "currency": ctx.currency, "route": "/desk/query-report/Accounts Payable"}


def _open_orders(ctx, doctype, statuses):
	_check(doctype)
	r = _one(doctype, [{"COUNT": "*", "as": "n"}, {"SUM": "base_grand_total", "as": "amt"}],
		_f(ctx, doctype, {"docstatus": 1, "status": ["in", statuses]}))
	new = _count(doctype, _f(ctx, doctype, {"docstatus": 1, "transaction_date": _between(ctx.start, ctx.end)}))
	prev = _count(doctype, _f(ctx, doctype, {"docstatus": 1, "transaction_date": _between(ctx.prev_start, ctx.prev_end)}))
	return {"value": int(r.n or 0), "amount": flt(r.amt), "currency": ctx.currency, "new": new, "delta": delta(new, prev),
		"route": _list_route(doctype, company=ctx.company, docstatus=1)}


def kpi_sales_orders(ctx):
	return _open_orders(ctx, "Sales Order", OPEN_SO)


def kpi_purchase_orders(ctx):
	return _open_orders(ctx, "Purchase Order", OPEN_PO)


def kpi_inventory(ctx):
	_check("Bin")
	warehouses = frappe.get_all("Warehouse", filters={"company": ctx.company, "is_group": 0}, pluck="name")
	if not warehouses:
		return {"value": 0.0, "currency": ctx.currency}
	r = _one("Bin", [{"SUM": "stock_value", "as": "v"}], {"warehouse": ["in", warehouses]})
	return {"value": flt(r.v), "currency": ctx.currency, "secondary": len(warehouses), "route": "/desk/query-report/Stock Balance"}


def kpi_outstanding(ctx):
	_check("Sales Invoice")
	base = _f(ctx, "Sales Invoice", {"docstatus": 1, "outstanding_amount": [">", 0]})
	n = _count("Sales Invoice", base)
	overdue = _count("Sales Invoice", {**base, "due_date": ["<", ctx.today]})
	return {"value": n, "secondary": overdue, "route": _list_route("Sales Invoice", company=ctx.company, docstatus=1, status="Overdue")}


def kpi_approvals(ctx):
	items = _approval_rows(ctx.company, limit=200, with_actions=False)
	return {"value": len(items), "route": "/thinknxg/erp/approvals"}


KPIS = {
	"total_revenue": kpi_revenue,
	"sales_orders": kpi_sales_orders,
	"purchase_orders": kpi_purchase_orders,
	"receivables": kpi_receivables,
	"payables": kpi_payables,
	"cash_bank": kpi_cash_bank,
	"inventory_valuation": kpi_inventory,
	"outstanding_invoices": kpi_outstanding,
	"gross_profit": kpi_gross_profit,
	"pending_approvals": kpi_approvals,
}


@frappe.whitelist()
@cached_panel
def get_kpis(company=None, fiscal_year=None, days=None, branch=None):
	ctx = _context(company, fiscal_year, days, branch)
	out = {key: _figure(fn, ctx) for key, fn in KPIS.items()}
	out["_context"] = _ctx_out(ctx)
	return out


def _ctx_out(ctx):
	return {"company": ctx.company, "currency": ctx.currency, "start": str(ctx.start), "end": str(ctx.end), "branch": ctx.branch, "fiscal_year": ctx.fiscal_year}


# Sections -------------------------------------------------------------------------

def _top(rows, key, value, n=6):
	rows = [r for r in rows if r.get(key)]
	rows.sort(key=lambda r: flt(r.get(value)), reverse=True)
	return [{"label": r[key], "value": flt(r[value])} for r in rows[:n]]


def section_sales(ctx):
	_check("Sales Invoice")
	period = {"posting_date": _between(ctx.start, ctx.end), "docstatus": 1}
	series = _q("Sales Invoice", ["posting_date", {"SUM": "base_net_total", "as": "value"}], _f(ctx, "Sales Invoice", period), group_by="posting_date")
	by_day = {str(r.posting_date): flt(r.value) for r in series}
	trend = [{"date": str(add_days(ctx.start, i)), "value": by_day.get(str(add_days(ctx.start, i)), 0.0)} for i in range(date_diff(ctx.end, ctx.start) + 1)]
	customers = _q("Sales Invoice", ["customer", {"SUM": "base_net_total", "as": "value"}], _f(ctx, "Sales Invoice", period), group_by="customer", limit=5000)

	def funnel():
		stages = []
		for label, dt, field in (("Quotations", "Quotation", "transaction_date"), ("Sales orders", "Sales Order", "transaction_date"), ("Sales invoices", "Sales Invoice", "posting_date")):
			if not doctype_exists(dt):
				continue
			_check(dt)
			stages.append({"label": label, "value": _count(dt, _f(ctx, dt, {"docstatus": 1, field: _between(ctx.start, ctx.end)})), "route": _list_route(dt, company=ctx.company)})
		return {"stages": stages}

	return {
		"trend": trend,
		"total": sum(p["value"] for p in trend),
		"top_customers": _top(customers, "customer", "value"),
		"funnel": _part(funnel),
		"currency": ctx.currency,
	}


def _ageing(ctx, account_type):
	_check("Payment Ledger Entry")
	rows = _q("Payment Ledger Entry",
		["against_voucher_no", {"SUM": "amount", "as": "amt"}, {"MAX": "due_date", "as": "due"}],
		_f(ctx, "Payment Ledger Entry", {"account_type": account_type, "delinked": 0, "posting_date": ["<=", ctx.end]}),
		group_by="against_voucher_no", limit=20000)
	buckets = [["Not due", 0.0], ["1-30 days", 0.0], ["31-60 days", 0.0], ["61-90 days", 0.0], ["Over 90 days", 0.0]]
	for r in rows:
		amt = flt(r.amt)
		if amt <= 0.005:
			continue
		age = date_diff(ctx.end, r.due) if r.due else 0
		i = 0 if age <= 0 else 1 if age <= 30 else 2 if age <= 60 else 3 if age <= 90 else 4
		buckets[i][1] += amt
	return [{"label": label, "value": value} for label, value in buckets]


def section_finance(ctx):
	def overdue():
		_check("Sales Invoice")
		rows = frappe.get_list("Sales Invoice",
			filters=_f(ctx, "Sales Invoice", {"docstatus": 1, "outstanding_amount": [">", 0], "due_date": ["<", ctx.today]}),
			fields=["name", "customer_name", "due_date", "outstanding_amount", "currency"], order_by="due_date asc", limit_page_length=8)
		return [{**r, "days": date_diff(ctx.today, r.due_date), "route": desk_route("Sales Invoice", r.name)} for r in rows]

	def cash_trend():
		_check("GL Entry")
		accounts = _accounts(ctx, account_type=["in", ["Cash", "Bank"]])
		if not accounts:
			return []
		opening = _one("GL Entry", [{"SUM": "debit", "as": "dr"}, {"SUM": "credit", "as": "cr"}],
			_f(ctx, "GL Entry", {"account": ["in", accounts], "is_cancelled": 0, "posting_date": ["<", ctx.start]}))
		bal = flt(opening.dr) - flt(opening.cr)
		moves = _q("GL Entry", ["posting_date", {"SUM": "debit", "as": "dr"}, {"SUM": "credit", "as": "cr"}],
			_f(ctx, "GL Entry", {"account": ["in", accounts], "is_cancelled": 0, "posting_date": _between(ctx.start, ctx.end)}), group_by="posting_date")
		by_day = {str(m.posting_date): flt(m.dr) - flt(m.cr) for m in moves}
		out = []
		for i in range(date_diff(ctx.end, ctx.start) + 1):
			d = str(add_days(ctx.start, i))
			bal += by_day.get(d, 0.0)
			out.append({"date": d, "value": bal})
		return out

	return {
		"receivable_ageing": _part(lambda: _ageing(ctx, "Receivable")),
		"payable_ageing": _part(lambda: _ageing(ctx, "Payable")),
		"overdue_invoices": _part(overdue),
		"cash_trend": _part(cash_trend),
		"currency": ctx.currency,
	}


def section_purchase(ctx):
	def open_pos():
		_check("Purchase Order")
		rows = _q("Purchase Order", ["status", {"COUNT": "*", "as": "n"}], _f(ctx, "Purchase Order", {"docstatus": 1, "status": ["in", OPEN_PO]}), group_by="status")
		return [{"label": r.status, "value": int(r.n)} for r in rows]

	def suppliers():
		_check("Purchase Invoice")
		rows = _q("Purchase Invoice", ["supplier", {"SUM": "base_net_total", "as": "value"}],
			_f(ctx, "Purchase Invoice", {"docstatus": 1, "posting_date": _between(ctx.start, ctx.end)}), group_by="supplier", limit=5000)
		return _top(rows, "supplier", "value")

	def requests():
		_check("Material Request")
		rows = _q("Material Request", ["material_request_type", {"COUNT": "*", "as": "n"}],
			_f(ctx, "Material Request", {"docstatus": 1, "status": ["in", ["Pending", "Partially Ordered", "Partially Received"]]}), group_by="material_request_type")
		return [{"label": r.material_request_type, "value": int(r.n)} for r in rows]

	return {"open_orders": _part(open_pos), "top_suppliers": _part(suppliers), "open_requests": _part(requests), "currency": ctx.currency}


def section_inventory(ctx):
	_check("Bin")
	warehouses = frappe.get_all("Warehouse", filters={"company": ctx.company, "is_group": 0}, pluck="name")
	by_wh = _q("Bin", ["warehouse", {"SUM": "stock_value", "as": "value"}], {"warehouse": ["in", warehouses or [""]]}, group_by="warehouse", limit=2000)

	def below_reorder():
		_check("Item")
		levels = frappe.get_list("Item Reorder", parent_doctype="Item",
			filters={"warehouse": ["in", warehouses or [""]], "warehouse_reorder_level": [">", 0]},
			fields=["parent", "warehouse", "warehouse_reorder_level"], limit_page_length=2000)
		if not levels:
			return {"count": 0, "items": []}
		bins = _q("Bin", ["item_code", "warehouse", "projected_qty"], {"item_code": ["in", list({l.parent for l in levels})], "warehouse": ["in", warehouses]}, limit=5000)
		qty = {(b.item_code, b.warehouse): flt(b.projected_qty) for b in bins}
		low = [
			{"item": l.parent, "warehouse": l.warehouse, "projected": qty.get((l.parent, l.warehouse), 0.0), "reorder_level": flt(l.warehouse_reorder_level), "route": desk_route("Item", l.parent)}
			for l in levels if qty.get((l.parent, l.warehouse), 0.0) < flt(l.warehouse_reorder_level)
		]
		low.sort(key=lambda x: x["projected"] - x["reorder_level"])
		return {"count": len(low), "items": low[:8]}

	return {"by_warehouse": _top(by_wh, "warehouse", "value", 8), "below_reorder": _part(below_reorder), "currency": ctx.currency}


def section_manufacturing(ctx):
	_check("Work Order")
	status = _q("Work Order", ["status", {"COUNT": "*", "as": "n"}], _f(ctx, "Work Order", {"docstatus": ["<", 2], "status": ["not in", ["Cancelled", "Closed"]]}), group_by="status")
	late = frappe.get_list("Work Order",
		filters=_f(ctx, "Work Order", {"docstatus": 1, "status": ["not in", DONE_WO], "planned_end_date": ["<", ctx.today]}),
		fields=["name", "production_item", "qty", "produced_qty", "planned_end_date"], order_by="planned_end_date asc", limit_page_length=8)

	def job_cards():
		_check("Job Card")
		rows = _q("Job Card", ["status", {"COUNT": "*", "as": "n"}], _f(ctx, "Job Card", {"docstatus": 0, "status": ["in", ["Open", "Work In Progress", "On Hold", "Material Transferred"]]}), group_by="status")
		return [{"label": r.status, "value": int(r.n)} for r in rows]

	return {
		"by_status": [{"label": r.status, "value": int(r.n)} for r in status],
		"late": [{**w, "route": desk_route("Work Order", w.name)} for w in late],
		"late_count": _count("Work Order", _f(ctx, "Work Order", {"docstatus": 1, "status": ["not in", DONE_WO], "planned_end_date": ["<", ctx.today]})),
		"job_cards": _part(job_cards),
	}


def section_projects(ctx):
	_check("Project")
	active = frappe.get_list("Project", filters=_f(ctx, "Project", {"status": "Open"}),
		fields=["name", "project_name", "percent_complete", "expected_end_date"], order_by="expected_end_date asc", limit_page_length=8)

	def tasks():
		_check("Task")
		return _count("Task", _f(ctx, "Task", {"status": ["not in", DONE_TASK], "exp_end_date": ["<", ctx.today]}))

	def timesheets():
		_check("Timesheet")
		return _count("Timesheet", _f(ctx, "Timesheet", {"docstatus": 1, "status": ["in", ["Submitted", "Partially Billed"]], "total_billable_amount": [">", 0]}))

	return {
		"active_count": _count("Project", _f(ctx, "Project", {"status": "Open"})),
		"active": [{**p, "route": desk_route("Project", p.name)} for p in active],
		"overdue_tasks": _part(tasks),
		"unbilled_timesheets": _part(timesheets),
	}


def section_crm(ctx):
	def leads():
		_check("Lead")
		rows = _q("Lead", ["status", {"COUNT": "*", "as": "n"}], _f(ctx, "Lead", {"creation": _between(f"{ctx.start} 00:00:00", f"{ctx.end} 23:59:59")}), group_by="status")
		return [{"label": r.status, "value": int(r.n)} for r in rows]

	def opportunities():
		_check("Opportunity")
		base = _f(ctx, "Opportunity", {"status": ["in", ["Open", "Replied", "Quotation"]]})
		r = _one("Opportunity", [{"COUNT": "*", "as": "n"}, {"SUM": "base_opportunity_amount", "as": "amt"}], base)
		stages = _q("Opportunity", ["sales_stage", {"SUM": "base_opportunity_amount", "as": "value"}, {"COUNT": "*", "as": "n"}], base, group_by="sales_stage")
		return {"count": int(r.n or 0), "amount": flt(r.amt), "by_stage": [{"label": s.sales_stage or "No stage", "value": flt(s.value), "count": int(s.n)} for s in stages]}

	return {"leads_by_status": _part(leads), "opportunities": _part(opportunities), "currency": ctx.currency}


SECTION_FNS = {
	"sales": section_sales, "finance": section_finance, "purchase": section_purchase, "inventory": section_inventory,
	"manufacturing": section_manufacturing, "projects": section_projects, "crm": section_crm,
}


@frappe.whitelist()
@cached_panel
def get_section(section, company=None, fiscal_year=None, days=None, branch=None):
	if section not in SECTION_FNS:
		frappe.throw(_("Unknown section."))
	ctx = _context(company, fiscal_year, days, branch)
	try:
		data = SECTION_FNS[section](ctx)
	except Missing:
		return {"available": False}
	except (Restricted, frappe.PermissionError) as exc:
		_quiet(exc)
		return {"restricted": True}
	if data is None:
		return {"available": False}
	return data


# Pending actions -------------------------------------------------------------------

@frappe.whitelist()
@cached_panel
def get_pending(company=None):
	ctx = _context(company)
	items = []

	def add(key, label, icon, fn):
		res = _figure(fn, ctx)
		if res.get("restricted") or not res.get("value"):
			return
		items.append({"key": key, "label": label, "icon": icon, **res})

	add("approvals", "Approvals waiting for you", "stamp", lambda c: {"value": len(_approval_rows(c.company, limit=200, with_actions=False)), "route": "/thinknxg/erp/approvals"})
	add("overdue", "Overdue sales invoices", "receipt", lambda c: _check("Sales Invoice") and {
		"value": _count("Sales Invoice", _f(c, "Sales Invoice", {"docstatus": 1, "outstanding_amount": [">", 0], "due_date": ["<", c.today]})),
		"route": _list_route("Sales Invoice", company=c.company, status="Overdue")})
	add("mr_to_order", "Material requests waiting for a purchase order", "clipboard-list", lambda c: _check("Material Request") and {
		"value": _count("Material Request", _f(c, "Material Request", {"docstatus": 1, "material_request_type": "Purchase", "status": ["in", ["Pending", "Partially Ordered"]]})),
		"route": _list_route("Material Request", company=c.company, material_request_type="Purchase", docstatus=1)})
	add("late_wo", "Work orders past their planned end", "factory", lambda c: _check("Work Order") and {
		"value": _count("Work Order", _f(c, "Work Order", {"docstatus": 1, "status": ["not in", DONE_WO], "planned_end_date": ["<", c.today]})),
		"route": _list_route("Work Order", company=c.company, docstatus=1)})
	add("so_to_bill", "Sales orders to bill", "shopping-cart", lambda c: _check("Sales Order") and {
		"value": _count("Sales Order", _f(c, "Sales Order", {"docstatus": 1, "status": ["in", ["To Bill", "To Deliver and Bill"]]})),
		"route": _list_route("Sales Order", company=c.company, status="To Bill")})
	return {"items": items, "company": ctx.company}


# Approvals ---------------------------------------------------------------------------

def app_doctypes(app: str) -> set[str]:
	"""Non-child DocTypes that belong to one installed app (cached per request)."""
	cache = frappe.local.__dict__.setdefault("_nxg_app_doctypes", {})
	if app not in cache:
		modules = frappe.get_all("Module Def", filters={"app_name": app}, pluck="name")
		cache[app] = set(frappe.get_all("DocType", filters={"module": ["in", modules or [""]], "istable": 0}, pluck="name"))
	return cache[app]


def erp_doctypes() -> set[str]:
	return app_doctypes("erpnext")


def _open_actions(limit=200, doctypes=None):
	if not doctype_exists("Workflow Action"):
		return []
	roles = tuple(frappe.get_roles()) or ("",)
	doctypes = tuple(doctypes if doctypes is not None else erp_doctypes()) or ("",)
	return frappe.db.sql(
		"""select wa.name, wa.reference_doctype, wa.reference_name, wa.workflow_state, wa.creation
		from `tabWorkflow Action` wa
		where wa.status = 'Open' and wa.reference_doctype in %(doctypes)s
		and (wa.user = %(user)s or exists (
			select 1 from `tabWorkflow Action Permitted Role` r where r.parent = wa.name and r.role in %(roles)s))
		order by wa.creation desc limit %(limit)s""",
		{"user": frappe.session.user, "roles": roles, "doctypes": doctypes, "limit": int(limit)},
		as_dict=True,
	)


def _approval_rows(company=None, limit=50, with_actions=True, doctypes=None, check_company=True):
	from frappe.model.workflow import WorkflowStateError, get_transitions

	allowed_companies = set(permitted_companies()) if check_company else set()
	out, seen = [], set()
	for a in _open_actions(doctypes=doctypes):
		key = (a.reference_doctype, a.reference_name)
		if key in seen:
			continue
		seen.add(key)
		try:
			if not frappe.has_permission(a.reference_doctype, "read", doc=a.reference_name):
				continue
			doc = frappe.get_doc(a.reference_doctype, a.reference_name)
		except (frappe.DoesNotExistError, frappe.PermissionError) as exc:
			_quiet(exc)
			continue
		doc_company = doc.get("company")
		if doc_company and ((check_company and doc_company not in allowed_companies) or (company and doc_company != company)):
			continue
		row = {
			"doctype": doc.doctype, "name": doc.name, "title": doc.get_title() or doc.name,
			"state": a.workflow_state, "creation": a.creation, "company": doc_company,
			"date": doc.get("posting_date") or doc.get("transaction_date") or doc.get("schedule_date"),
			"amount": doc.get("base_grand_total") if doc.meta.has_field("base_grand_total") else None,
			"currency": frappe.get_cached_value("Company", doc_company, "default_currency") if doc_company else None,
			"owner": frappe.utils.get_fullname(doc.owner),
			"route": desk_route(doc.doctype, doc.name),
		}
		if with_actions:
			try:
				row["actions"] = list(dict.fromkeys(t["action"] for t in get_transitions(doc, raise_exception=True)))
			except WorkflowStateError:
				row["actions"] = []  # state not set yet; raised without a message
			except (frappe.ValidationError, frappe.PermissionError):
				frappe.clear_last_message()  # raised through frappe.throw
				row["actions"] = []
			if not row["actions"]:
				continue  # nothing this user may do on it right now
		out.append(row)
		if len(out) >= limit:
			break
	return out


@frappe.whitelist()
def get_approvals(company=None, limit=50):
	require_center("erp")
	company = validate_company(company)
	try:
		limit = max(1, min(int(limit), 100))
	except (TypeError, ValueError):
		limit = 50
	return {"items": _approval_rows(company, limit=limit)}


@frappe.whitelist(methods=["POST"])
def apply_approval(doctype, name, action):
	"""Run one workflow action through the core workflow engine.

	Core decides: the user's read access, the workflow's allowed role for the
	transition, its condition, self-approval, and write/submit permission on save.
	The document's own history records who acted and when.
	"""
	from frappe.model.workflow import apply_workflow

	require_center("erp")
	if doctype not in erp_doctypes():
		frappe.throw(_("This document is not part of thinkNXG ERP."), frappe.PermissionError)
	if not frappe.has_permission(doctype, "read", doc=name):
		frappe.throw(_("You do not have access to this document."), frappe.PermissionError)
	company = frappe.db.get_value(doctype, name, "company") if has_field(doctype, "company") else None
	if company:
		validate_company(company)
	from frappe.model.workflow import get_workflow_name, get_workflow_state_field

	from thinknxg_admin.api.cache import clear_dashboard_cache

	if not get_workflow_name(doctype):
		frappe.throw(_("{0} has no active workflow.").format(_(doctype)))
	doc = apply_workflow({"doctype": doctype, "name": name}, action)
	clear_dashboard_cache()
	return {"name": doc.name, "doctype": doc.doctype, "docstatus": int(doc.docstatus), "state": doc.get(get_workflow_state_field(get_workflow_name(doctype)))}
