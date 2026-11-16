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
