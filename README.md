# thinkNXG Admin — Command Center

Premium administration shell for **thinkNXG Core**, **thinkNXG ERP** and **thinkNXG HR** (V16).
It opens at **`/thinknxg`**, next to the classic Desk at `/desk`, which it leaves untouched.

Release 16.3: application shell, Command Center and System Health (Phases 4–5); Users & Access, Roles & Permissions, Organization, Workspaces and Apps & Modules (Phase 6); Integrations, Automation, Audit & Compliance, Developer Tools and the Notification Center (Phase 7); System Configuration, Reports & Analytics and My Workspace (Phase 8). Every menu item is now a working screen.

## Install

```bash
cd ~/frappe-bench
bench get-app /path/to/thinknxg_admin      # or the Git URL of thinknxg/thinkNXG-Admin
bench --site <site> install-app thinknxg_admin
bench build --app thinknxg_admin           # optional: prebuilt assets are included
bench --site <site> clear-cache
```

Open `https://<site>/thinknxg`, or use the **Command Center** tile on the `/desk` apps screen.

Requirements: thinkNXG Framework (Frappe) 16.x. ERP and HR are optional; every ERP/HR figure
shows "Not available" when that app is not installed.

## What's included

| Area | Details |
| --- | --- |
| Shell | Espresso sidebar with brand-red active marker, collapsible sections, nested items, app switcher (from each app's `add_to_apps_screen`), help/docs/what's-new, profile menu, collapse to icons, mobile drawer |
| Top bar | Breadcrumbs, search pill, quick-create (only DocTypes you may create), organisation selector, notifications (Notification Log + open ToDos, mark read via Core methods), help, light/dark/system theme (saved to `User.desk_theme`) |
| Command palette | Ctrl/⌘ K or `/`; pages, favourites, recents, actions, permission-checked server search of DocTypes, users, reports and workspaces |
| Command Center | 8 KPIs, system activity chart, live health, users & access, organisation, pending actions, administrative activity timeline; 7/30/90-day range; company scope; Customize (per-user section visibility); Refresh |
| System Health | Live checks (DB, Redis, queues, workers, scheduler, storage, errors, API round-trip), queue table, storage meter, on-demand V16 System Health Report |
| Settings | `thinkNXG Admin Settings`: extra admin roles, cache seconds, business-unit source, product name, classic-Desk link |
| Users & Access | Directory with search, status / user type / role / company filters (saved per browser), sorting, pagination, bulk enable / disable / add role / remove role, CSV export (needs export permission). User panel: enable, user type, role profiles, roles, default workspace and app, module profile, User Permission restrictions, password reset email, API key generation (secret shown once), sign-in history, recent changes. Create user. Invitations via the V16 User Invitation flow (invite, cancel). Site-wide User Permissions list |
| Roles & Permissions | Role directory (users, DocTypes, workspaces per role), create, duplicate (copies every permission rule, optionally its users), role panel with users add/remove, level-0 permission summary, where it is used, settings (desk access, 2FA, disabled, home page). Role Profiles editor. Permission Matrix by DocType or by role, including custom permission types, through Core's Role Permission Manager methods; add / remove rules; reset to standard |
| Organization | Company cards with employee, department, cost-center and warehouse counts; collapsible department hierarchy with head counts; branches; designations; fiscal years; regional settings; follows the company selector |
| Workspaces | Workspace pages (roles, hidden, reorder), visual Sidebar builder for each module's site-wide layer (drag or keyboard reorder, rename, hide, nest, add links and section headings, reset) through Core's Custom Sidebar endpoints, Desktop icons (show/hide, roles) |
| Apps & Modules | Installed apps with version and branch, modules with DocType counts and visibility, Module Profiles editor; explains install vs visibility vs role access vs launcher |
| Integrations | Webhooks with 7-day delivery health and enable switch, delivery log per webhook (errors only filter); email accounts with sent / error / pending counts and queue status; OAuth clients with active tokens, connected apps with connected users, social sign-in providers (enable switch); users holding API keys with last logged request; webhook delivery and Integration Request logs. Secrets, header values and URL query strings are never returned |
| Automation | Workflows (activate; open actions), Notifications, Assignment Rules, Scheduled Jobs (7-day runs and failures, run now, stop/start, run log), Server Scripts (no script bodies; warns when server scripts are disabled for the bench), Auto Repeat, Document Naming Rules, Milestone Trackers; scheduler status. Every switch saves through the document so its validation runs |
| Audit & Compliance | One timeline over Activity Log, Permission Log, Version, Access Log and API Request Log: categories (sign-ins, permissions, users & roles, configuration, data exports, documents, API), actor / result / date / text filters (saved per browser), expandable before → after values, summary tiles, most-failed users and IPs, CSV export (needs export permission on Activity Log; the export itself is written to the Access Log) |
| Developer Tools | Overview (apps and versions, DocType and customisation counts, developer mode, server-script flag), DocType explorer with field / permission / customisation detail, custom fields / property setters / client and server scripts lists, Error Log reader (mark seen), background jobs by state (stop running jobs, clear failed). System Manager only; nothing executes code |
| Notification Center | `/thinknxg/notifications` for every desk user: type filters with unread counts, unread-only switch, day grouping, mark read / mark all read through Core, open the related document, personal notification and email settings |
| System Configuration | System Manager only. Allow-listed System Settings fields grouped as General & regional, Sign-in & sessions, Passwords, Two-factor, Email, Files, System; setting search; unsaved-changes bar; security-weakening changes need confirmation (disabling password sign-in needs typing CONFIRM); stale-edit protection; log retention (Log Settings); product name and Classic Desk link |
| Reports & Analytics | Every user sees the reports they may open (report roles, else DocType read access): search, module / type filters, favourites, most used (your opens + 30-day exports), dashboards with chart and card counts, scheduled email reports with on/off |
| My Workspace | Landing page for every desk user (non-admins are sent here instead of the Command Center): open tasks with one-click done and undo, approvals waiting for your roles, workspaces your roles can open, records you changed recently, recently visited Desk pages, favourites; preferences drawer for theme, language, time zone, default workspace and default app |

Keyboard: `Ctrl/⌘ K` palette · `/` search · `G` `C` Command Center · `G` `H` Health · `G` `U` Users · `[` sidebar · `?` help.

## Safety rails

- You cannot disable your own account or remove System Manager from yourself.
- The last enabled System Manager can never be disabled or lose the role.
- Bulk disable / remove-role on 10+ users requires typing the count; resetting a DocType's permissions requires typing RESET.
- Every write goes through the document (or Core's own endpoint), so validation, Version history and the Permission Log keep working.
- Site-wide navigation changes need the Workspace Manager role, as the framework requires; the Workspaces screen offers to add it to your own account (recorded like any role change).

## Security model

- Native Frappe session only; Guests are redirected to `/login`, Website Users to `/me`.
- Every API checks permissions on the server (`require_admin()`: System Manager, Administrator,
  or a role listed in thinkNXG Admin Settings). Record lists use `frappe.get_list` /
  `frappe.has_permission`. Menu visibility is convenience, never enforcement.
- No secrets are returned. No `app_include_*` hooks: Desk is not restyled or patched.
- No figure is invented: a missing source returns `null` and the UI says "Not available".

## Data sources

| Widget | Source |
| --- | --- |
| Total / active users | `User`; distinct successful logins in `Activity Log` (vs previous period) |
| Companies, workspaces, apps, modules | `Company`; public non-hidden `Workspace`; `frappe.get_installed_apps()`; `Module Def` |
| Pending approvals | `Workflow Action` (Open) + your open `ToDo` + alerts (unseen `Error Log`, scheduler state, failed RQ jobs) |
| Background jobs / health | RQ queues and workers, `frappe.db`, `frappe.cache`, scheduler helpers, disk usage, `System Health Report` |
| Permission changes / timeline | `Permission Log` and `Version` on admin DocTypes, failed logins from `Activity Log` |
| Invitations | `User Invitation` (Pending) |

Dashboard panels are cached per user for 60 s (configurable) and cleared when User, Role,
Workspace or Company records change. **Refresh** bypasses the cache.

## Development

```bash
cd apps/thinknxg_admin/frontend
yarn install
yarn dev                       # http://localhost:8090/thinknxg, proxies /api to FRAPPE_URL (default :8000)
VITE_MOCK=1 yarn dev           # UI preview with sample data, labelled with a banner; never in production builds
yarn build                     # writes public/frontend and www/thinknxg.html
```

Stack: Vue 3 + TypeScript + frappe-ui 1.2 + Tailwind 3 (frappe-ui preset + thinkNXG tokens in
`src/styles/tokens.css`). Inside a bench, Core's `@framework/ui` (apps/frappe/ui) is wired in
`vite.config.ts` for the Phase 6 screens.

## Tests

```bash
bench --site <test-site> run-tests --app thinknxg_admin
```

Covers: every dashboard, Phase 6 and Phase 7 endpoint allowed for admins and refused for plain users and
Guests, navigation filtering, KPI count matches a direct query, missing DocType returns `None`,
the last System Manager guard, secrets never present in integration payloads, URL credential
stripping, notifications scoped to their owner, configuration allow-list and System Manager gate,
preferences that cannot change roles or user type.

## License

MIT · © 2026 Kreatao · https://thinknxg.com
