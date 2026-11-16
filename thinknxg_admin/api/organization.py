"""Organization structure: companies, department hierarchy, branches, designations,
fiscal years. Read-only here; records are created and edited in their own forms,
so ERPNext's validations (chart of accounts, defaults) always run."""

import frappe

from thinknxg_admin.api.utils import doctype_exists, has_field, require_admin


def _count_by(doctype, field, filters=None):
	"""{value: count} grouped by `field`. Doctype/field names come from this module only;
	filter values are bound parameters."""
	if not (doctype_exists(doctype) and has_field(doctype, field)):
		return {}
	where, params = [], []
	for key, value in (filters or {}).items():
		if not has_field(doctype, key):
			continue
		if isinstance(value, (list, tuple)) and value and value[0] == "in":
			vals = [v for v in value[1] if v not in (None, "")]
			where.append(f"`{key}` in ({', '.join(['%s'] * len(vals))})" if vals else "1=0")
			params += vals
		else:
			where.append(f"`{key}` = %s")
			params.append(value)
	sql = f"select `{field}`, count(*) from `tab{doctype}`" + (f" where {' and '.join(where)}" if where else "") + f" group by `{field}`"
	return dict(frappe.db.sql(sql, params))


@frappe.whitelist()
def get_organization(company: str | None = None):
	require_admin()
	out = {"available": doctype_exists("Company")}
	if not out["available"]:
		return out

	cfields = ["name", "abbr"] + [f for f in ("company_name", "default_currency", "country", "parent_company", "is_group", "tax_id") if has_field("Company", f)]
	companies = frappe.get_list("Company", fields=cfields, order_by="name asc", limit_page_length=500)
	emp_filters = {"status": "Active"} if doctype_exists("Employee") and has_field("Employee", "status") else {}
	per_company = {
		"departments": _count_by("Department", "company", {"is_group": 0} if has_field("Department", "is_group") else None),
		"cost_centers": _count_by("Cost Center", "company", {"is_group": 0}),
		"warehouses": _count_by("Warehouse", "company", {"is_group": 0}),
		"employees": _count_by("Employee", "company", emp_filters),
	}
	for c in companies:
		c["counts"] = {k: v.get(c.name, 0) if v else None for k, v in per_company.items()}
	out["companies"] = companies

	# Department tree (ERPNext stores it as a nested set with parent_department)
	out["departments"] = []
	if doctype_exists("Department"):
		dfields = ["name", "department_name", "parent_department", "is_group"] + (["company"] if has_field("Department", "company") else [])
		depts = frappe.get_list("Department", fields=dfields, order_by="lft asc" if has_field("Department", "lft") else "name asc", limit_page_length=2000)
		if company and has_field("Department", "company"):
			depts = [d for d in depts if not d.get("company") or d.get("company") == company]
		emp_by_dept = _count_by("Employee", "department", {**emp_filters, **({"company": company} if company else {})})
		for d in depts:
			d["employees"] = emp_by_dept.get(d.name, 0) if emp_by_dept else None
		out["departments"] = depts

	emp_scope = {**emp_filters, **({"company": company} if company else {})}
	out["branches"] = []
	if doctype_exists("Branch"):
		by_branch = _count_by("Employee", "branch", emp_scope)
		out["branches"] = [{"name": b, "employees": by_branch.get(b, 0) if by_branch else None} for b in frappe.get_list("Branch", pluck="name", order_by="name asc", limit_page_length=1000)]
	out["designations"] = []
	if doctype_exists("Designation"):
		by_desig = _count_by("Employee", "designation", emp_scope)
		out["designations"] = sorted(
			[{"name": d, "employees": by_desig.get(d, 0) if by_desig else None} for d in frappe.get_list("Designation", pluck="name", limit_page_length=2000)],
			key=lambda r: (-(r["employees"] or 0), r["name"]),
		)
	out["fiscal_years"] = frappe.get_list("Fiscal Year", fields=["name", "year_start_date", "year_end_date", "disabled"], order_by="year_start_date desc", limit_page_length=20) if doctype_exists("Fiscal Year") else []
	out["currencies_enabled"] = frappe.db.count("Currency", {"enabled": 1}) if doctype_exists("Currency") else None
	sys = frappe.get_cached_doc("System Settings")
	out["regional"] = {f: sys.get(f) for f in ("country", "time_zone", "language", "date_format", "time_format", "number_format", "currency", "first_day_of_the_week")}
	return out
