# Changelog

## 16.5.2 — 17 November 2026

### Fixed
- New-document forms failed with `ImportError: workspace` (and the same for any one-word DocType such
  as customer or item): the slug matched case-insensitively and was used as the DocType name.
  `resolve_doctype()` now always returns the stored name.

### Changed
- One brand module (`api/brand.py`) holds every thinkNXG product name and link. App titles,
  descriptions, app-screen entries and notification subjects pass through it, so Frappe, ERPNext,
  Frappe HR / hrms, Frappe Cloud, Frappe CRM, Raven, Helpdesk, Frappe Insights and Frappe Cloud
  Marketplace show as their thinkNXG names.
- Help is now a menu: the active center's documentation and thinkNXG Support first, then thinkNXG ERP,
  HR, Framework, CRM, Raven, thinkDesk and Cloud documentation, thinkNXG Cloud and thinkNXG Insights.
- The Apps page links each app to its thinkNXG documentation.

## 16.5.1 — 17 November 2026

### Fixed
- `/thinknxg` failed to open with `AttributeError: __dict__`: per-request caches used
  `frappe.local.__dict__`, which the framework's `Local` object does not have. They now use
  `request_cache()` (getattr/setattr on `frappe.local`).

## 16.5.0 — 16 November 2026

Complete internal navigation: ERP and HR modules, documents and reports open inside their command
center. Normal navigation no longer leads to the Desk.

### Added
- **Central route registry** (`api/routes.py`): ERP modules (Accounting, Selling, Buying, Stock,
  Manufacturing, CRM, Projects, Assets, Quality, Support) and HR modules (Employees, Attendance, Leave,
  Payroll, Recruitment, Performance, Training, Lifecycle, Expenses), each with their DocTypes and
  reports. Boot sends each user only what they may read.
- **Internal router**: `/thinknxg/<center>/<module>`, `/<doctype>`, `/<doctype>/new`, `/<doctype>/<name>`,
  `/<center>/reports/<report>`, `/<center>/doc/<doctype>` for any other DocType; Access denied and
  Not found pages inside the shell; route-level checks against the registry.
- **Reusable document list** (search, standard filters, saved views, sorting, pagination, column
  choice, bulk submit / cancel / delete, CSV export, status) and **document form** built from DocType
  metadata (tabs, sections, columns, child tables, depends-on rules, fetch-from, attachments, comments,
  timeline, workflow actions, Save / Submit / Cancel / Amend / Duplicate / Delete, print preview).
  All reads and writes use the core methods (`getdoc`, `savedocs`, `cancel`, `apply_workflow`…).
- **Report runner** through `frappe.desk.query_report.run`, with each report's own filters.
- **Module pages** with record and draft counts per DocType and the module's reports.
- **Legacy address resolver**: `/desk/…` and `/app/…` links anywhere (notifications, favourites,
  links inside documents) open the matching internal page.
- Automated navigation check: `frontend/e2e/navigation_check.py`.

### Changed
- Admin pages moved under `/thinknxg/admin/…`; old addresses redirect.
- Every link the server builds (`desk_route`, KPI drill-downs, search, notifications, approvals, My
  Workspace, report catalogue) now returns an internal address.
- ERP and HR sidebars list their modules from the registry; the switcher no longer offers the thinkNXG
  ERP / HR / Framework Desk tiles. Classic Desk remains for administrators only.

### Stays in the Desk (System Managers)
DocType editor, Customize Form, Print Format builder, Server and Client Scripts, Web Forms, and the
workspace block editor.


## 16.4.0 — 16 November 2026

Unified Enterprise Command Center: the Admin Command Center is extended to thinkNXG ERP and thinkNXG HR
with the same shell, tokens and components.

### Added
- **Command center registry** (`api/centers.py`) and **switcher**: Admin, ERP and HR; only centers the
  server grants are listed, with an access label. Each center has its own navigation, filters and
  quick actions. No page reloads.
- **ERP Command Center** (`/thinknxg/erp`): 10 KPIs, 7 intelligence sections, needs-your-attention list,
  and **Approvals** (`/thinknxg/erp/approvals`) through the core workflow engine.
- **HR Command Center** (`/thinknxg/hr`): 10 KPIs, 7 sections, payroll totals for payroll roles only,
  **My team** view for managers with direct reports, and **HR Approvals** (`/thinknxg/hr/approvals`) for
  leave, expense and shift requests.
- **Search across centers**: ERP and HR records in the command palette, grouped by center.
- **Notification categories**: Approvals, Finance, Operations, People, System, with unread counts.
- **Role-based default landing** and per-user preferences (`thinkNXG User Preference`).
- Settings: extra HR Command Center roles, payroll roles, default landing by role.

### Changed
- `admin_roles()` reads only the Admin Roles table (settings now hold several role tables).
- Shared chart sizes its axis to the widest label; KPI tiles support "Restricted", money and suffixes.
- Keyboard: G then S opens System Health (G then H now opens the HR Command Center).

### Upgrade
`bench --site <site> migrate` (two new DocTypes), then `bench --site <site> clear-cache`.

## 16.3.0
Phases 4–8 of the Admin Command Center.
