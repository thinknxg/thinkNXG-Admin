# Changelog

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
