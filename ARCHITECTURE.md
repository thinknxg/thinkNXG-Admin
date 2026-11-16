# Architecture notes (Phases 4–8)

Full audit and plan: "thinkNXG Admin Command Center — Audit & Architecture" (Claude doc).

- **One app, no core changes.** `thinknxg_admin` sits on top of thinkNXG Core; ERP and HR are read
  through standard DocTypes and hooks only (no imports from `erpnext.*` / `hrms.*`).
- **SPA pattern** identical to ERP Banking and the HRMS PWA: Vite builds to `public/frontend`,
  `index.html` is copied to `www/thinknxg.html`, `website_route_rules` sends `/thinknxg/<path>` to it.
  `www/thinknxg.py` embeds boot JSON (escaped) and the CSRF token.
- **Navigation** is a server registry (`api/navigation.py`) filtered by admin role and
  `frappe.has_permission`; the app switcher reads each installed app's `add_to_apps_screen`.
- **Brand**: espresso working colour, signal-red signature (logo, active marker, focus ring, unread
  dot). Status colours are separate from brand red and always carry an icon and a label.
- **Charts** follow single-hue magnitude rules: one series, 2 px line, recessive grid,
  hover crosshair and tooltip; brand red is never a series colour.
- **Decisions taken with defaults** (change any time): failed sign-ins shown instead of a locked-user
  count (lock state is cache-only in V16); business units need a source chosen in settings;
  `gwm` branches not targeted.

## Phase 6 decisions

- **Permission rules are edited through Core.** The matrix calls
  `frappe.core.page.permission_manager.permission_manager.{get_permissions, add, update, remove, reset}`;
  no permission logic is reimplemented.
- **Sidebars use the V16 layer model.** In this Core release `Workspace Sidebar` is a read-only
  archive. The builder edits the site-wide `Custom Sidebar` layer through
  `frappe.desk.doctype.custom_sidebar.custom_sidebar.{get_site_sidebar_layer, save_site_sidebar,
  reset_site_sidebar}`, which gate on the Workspace Manager role and keep the merge rules intact.
- **Invitations use `User Invitation`** (app `frappe`, so any role may be granted); Core sends the email.
- **Own table and form components** in thinkNXG styling (DataTable, Drawer, Dialog, MultiSelect).
  `@framework/ui` ListView/Filter stay available through `vite.config.ts` for later adoption; they
  were not used here so the build does not depend on a bench checkout of Core's UI source.

## Phase 7 decisions

- **Audit reuses Core's records only**: Activity Log, Permission Log (`{"from", "to"}` diffs), Version,
  Access Log and API Request Log are merged at read time; nothing is logged twice. The default feed
  covers administration; business-document history is a separate "Documents" category because of volume.
  Paging merges at most 2,000 events per query window.
- **Integrations never select secret columns** (webhook secret/headers, OAuth and connected-app secrets,
  tokens, email passwords, API secrets). Endpoint URLs are reduced to scheme, host, port and path.
- **Automation switches** go through each document's save (e.g. Core deactivates other workflows for the
  same DocType). "Run now" uses `Scheduled Job Type.enqueue(force=True)`, the same as Desk's Execute.
- **Developer Tools are read-only**: no console, no script bodies, no site config values. The only writes are
  marking Error Logs seen and Core's own RQ `stop_job` / `remove_failed_jobs`.
- **Notifications** read `Notification Log` for the session user only; `type` is a Link to
  `Notification Type` in this Core release, so type filters are discovered from the data.

## Phase 8 decisions

- **Configuration edits an allow-list**, not the whole System Settings form: unknown keys are refused,
  saves go through the Single's own `save()` (its validation runs), and a `modified` check prevents
  overwriting someone else's change. Security-weakening values are flagged by the server for confirmation.
- **Report visibility mirrors Core**: report roles when set, otherwise read access to the reference DocType;
  administrators see all. Usage = Access Log exports (30 days) + the user's own Route History opens.
- **My Workspace is strictly personal**: own ToDos, Workflow Actions addressed to the user or their roles,
  own Version and Route History, workspaces filtered by role and blocked modules. Preference saves touch
  a fixed list of fields on the user's own record (language, time zone, theme, default workspace / app).
- Non-admin desk users land on My Workspace; the Command Center stays admin-only.

## Unified command centers — Phase A (shared foundation)

Blueprint and approved checklist: "thinkNXG Unified Enterprise Command Center — Audit, Shared
Architecture & ERP/HR Blueprint" (approved 16 Nov 2026).

- **One SPA, many centers.** `api/centers.py` declares Admin, ERP and HR once each (label, route,
  filters, navigation, quick actions, docs link). Boot sends only the centers the server grants,
  so the switcher, palette and landing cannot offer anything the server would refuse.
  Admin keeps every existing route; ERP owns `/erp/*`, HR owns `/hr/*`; Notifications,
  My Workspace and Reports are shared and show the last center's sidebar.
- **Gates are ours, not the apps' launcher checks.** `erpnext.check_app_permission` admits every desk
  user and `hrms.hr.utils.check_app_permission` admits any employee who can read their own record.
  ERP needs read on GL Entry, Sales Order, Purchase Order or Stock Ledger Entry ("limited" when any
  KPI DocType is unreadable). HR needs HR User / HR Manager / roles from settings; otherwise a user
  whose Employee record has active direct reports gets "team" access (direct reports only).
- **Payroll** needs read on Payroll Entry (HR Manager by default) or a role in the new
  "Payroll Roles" setting; HR User alone can read every slip, so it is not enough.
- **Filters** (company, branch, department, fiscal year, date range) are declared per center and their
  option lists come from `get_filter_options` via `frappe.get_list`, so User Permissions apply.
  Companies are re-checked with `validate_company`. The ERP branch filter appears only when Branch is
  an active Accounting Dimension.
- **Preferences** (default center, last center, per-center filters and last page) live in
  `thinkNXG User Preference`, one row per user, written only by `save_preferences` for the session
  user; values are cleaned to a fixed key list. A local copy makes switching instant.
- **Default landing**: the user's own choice, else the first matching "Default Landing by Role" row
  (lower priority first), else Admin for administrators, else the first granted center, else
  My Workspace. It applies only when `/thinknxg` itself is opened.
- `admin_roles()` now filters by `parentfield`, because Admin Settings has several role tables.
- ERP and HR homes show no figures yet; KPIs and sections land in Phases B–E.

## Unified command centers — Phase B (ERP figures and approvals)

- **Every ERP figure goes through `frappe.qb.get_query(..., ignore_permissions=False)`**, the core
  query builder with permissions on. Role permissions and User Permissions (company, warehouse,
  customer…) narrow every count and SUM; nothing bypasses them. Account and Warehouse *names* are
  read without permission checks only to pick which rows to sum — they carry no balances.
- **Withheld, not zero**: a figure whose source the user cannot read returns `{"restricted": true}`
  and no number; a source that is not installed returns `value: null` ("Not available").
- **Sources**: revenue and gross profit from GL Entry (Income minus Cost of Goods Sold accounts),
  cash/bank from GL balances, receivables/payables and ageing from Payment Ledger Entry (`amount` is in
  company currency, positive for outstanding on both sides), inventory from Bin `stock_value` in the
  company's warehouses, orders and invoices from submitted documents.
- **A company is always resolved** (the chosen one, else the user's default, else the first they may
  see), because money is only summed in one currency. Fiscal years and branches are re-validated on
  the server; the branch filter needs Branch as an active Accounting Dimension.
- **Approvals use the core workflow engine.** `apply_approval` checks the ERP center, that the DocType
  belongs to thinkNXG ERP, read access and company, then calls `frappe.model.workflow.apply_workflow`,
  which enforces the transition's role, condition, self-approval and write/submit permission and
  records the action in the document's history. The list shows only documents the user can read and
  only transitions `get_transitions` offers them.
- Panels are cached for the settings TTL per user and filter set; an approval clears the cache.

## Unified command centers — Phase D/E (HR figures, approvals, My Team)

- **HR roles ("full"/"limited")**: every figure goes through the permission-aware query builder
  (shared helpers in `api/figures.py`), so Employee/Company/Department User Permissions narrow every
  count. Department filters use each DocType's own `department` field; branch exists only on
  Employee, so other records are matched through the employees of that branch.
- **Managers ("team")**: rows are limited on the server to the manager's active direct reports
  (`reports_to`) and to `TEAM_DOCTYPES` (Employee, Attendance, Leave Application, Employee Checkin,
  Expense Claim, Shift Request). Because thinkNXG HR normally hides other people's Employee records
  from a non-HR user, team queries run without the framework's record permissions but always with
  the direct-report filter. Payroll, recruitment, performance and lifecycle are never sent to them.
- **Payroll** needs `can_view_payroll()` *and* read access to Payroll Entry / Salary Slip. Only totals
  (latest run, net pay per pay period, slips by status) are sent — never an individual's pay.
- **Approvals without a workflow** (Leave Application, Expense Claim, Shift Request): only the named
  approver (`leave_approver`, `expense_approver`, `approver`) may act; the outcome field is set and the
  document submitted under the user's own submit permission, so thinkNXG HR's validation runs exactly
  as in the Desk (leave balances, expense accounting, shift assignment creation). With an active
  workflow, the core workflow engine decides, as for ERP. Attendance and Compensatory Leave Requests
  have no approver field, so they appear as HR to-dos linking to the Desk.
- The ERP and HR approval screens are one shared page (`ApprovalsPage.vue`).

## 16.5 — complete internal navigation

- **One registry** (`api/routes.py`) maps every ERP and HR module, DocType and report to an internal
  route; `internal_route()` builds addresses on the server (and `desk_route()` now delegates to it),
  `toInternal()` in `lib/links.ts` does the same in the browser, and `from_desk_path()` /
  `docs.resolve` translate any old `/desk` or `/app` address.
- **Link layer**: a document-level click handler routes every internal `<a>` through the router
  without a reload and rewrites Desk hrefs on mousedown/focus, so new tabs stay inside too; templates
  use `$href()`. `data-desk` marks the few deliberate Desk links (Classic Desk, developer tools).
- **Route guards are UX, not security**: modules and DocTypes must be in the user's registry, otherwise
  Access denied. Every list and form call is checked again on the server.
- **Document engine** (`components/doc`): `DocList` reads rows through `docs.get_list` (frappe.get_list
  and a permission-aware count; filters limited to readable fields). `DocForm` lays out fields from
  `docs.get_form_meta` (field-level read and write permissions applied) and uses only core methods to
  load, save, submit, cancel, run workflow actions, comment, attach, delete and print. Required-field
  and depends-on rules are evaluated like the Desk; the server still decides.
- **Not carried over**: browser-side form scripts of thinkNXG ERP/HR and site Client Scripts. Values
  they compute on the fly are computed by the server on save (e.g. `set_missing_values`, totals in
  `validate`). Report filters are read from each report's script with a tolerant stand-in for the Desk
  globals; when a script cannot be read, company and date filters are offered.
