# CRM Dashboard Audit - 2026-05-24

## Fixed In This Pass

- Replaced the flat 17-item primary dashboard navigation with 5 operator workspaces: Journeys, People, Messaging, Intelligence, and Ops.
- Removed first-class navigation for nonfunctional/low-confidence surfaces: the temporary Solutions placeholder and the test-style Abandoned Lead Recovery panel.
- Kept fast access to high-use surfaces with quick links for Timeline, WhatsApp, Email, and Health.
- Removed the hardcoded Email Workspace admin secret and standardized protected promo API calls on the shared `anu_admin_secret` browser key.
- Added guarded Email Workspace error handling so missing or invalid admin access no longer appears as a raw red `HTTP 403` dashboard failure.
- Normalized the React entry point so `main.jsx` renders `App`, and `App` renders a single dashboard shell without a duplicate external-tools bar.

## Blockers Found

- Email promo endpoints can return 401/403 when the browser does not have the correct `anu_admin_secret`; this was the visible blocker in the Email dashboard.
- The old navigation mixed core workflows, diagnostics, external launchers, placeholders, and test tools at the same level, making the app feel broken even when individual panels worked.
- `SolutionsShowcase` is explicitly temporary and should not be a primary production destination.
- `AbandonedLeadPanel` is currently a manual/test lead creation surface, not a polished production recovery workflow.
- Several panels still each implement their own API/auth helper. Email is fixed, but the app should eventually move to one shared request client for all protected dashboard calls.

## Remaining Product/Backend Gaps

- Add feature flags or health-aware disabled states for panels whose backend dependencies are unavailable.
- Update Playwright UI tests to match the new grouped navigation model before relying on them for regression gating.
- Code-split heavy workspaces such as WhatsApp and charts; the Vite build still warns that one chart chunk is over 500 kB.
- Decide whether Abandoned Lead Recovery belongs inside the CRM, the paid-media service, or should be replaced with a real cart recovery workflow.
- Centralize admin access handling across Contacts, Campaigns, Shopify, Analytics, AI Brain, Journey Builder, and Email.

## Verification

- `npm run build` passes.
- VS Code static error check reports no errors in `src`.
- Local review server is available at `http://127.0.0.1:5173/`.
- Live deployment to `ai.pureleven.com` is pending because key-based SSH to `root@192.46.213.140` is denied in this session, and stored passwords should not be placed into commands.