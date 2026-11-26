# Audit dashboard fix batch C — dead system/doc links (2026-11-16)

**What was broken** (found by the read-only live-asset sweep of `https://findtorontoevents.ca/audit/`, 89 local URLs probed, 82 OK / 5 genuinely broken):

1. **ML Gatekeeper design-doc link 404** — `dashboard_enhancements.js:654` injected `<a href="/reports/ml_gatekeeper_ab_sleeve_design_2026-05-12.md">`. Root `/reports/` is **never deployed to any site** (no deploy mapping exists; the file exists in the repo at `reports/…`, 4 KB). Same bug in `money_ready_filter.js:210` → `reports/supreme_edge_5agent_synthesis_2026-05-12.md`.
2. **`smart_money` system deep-link 404** — `sysLinks` map (`template.html:4020`) had `'smart_money': 'smart_money/'`, the only **relative** entry in the map (all others root-absolute `/…` or full URLs). Resolves to `/audit/smart_money/` (404); no `smart_money` page exists anywhere (dir only holds `scanner.py`).

**What changed:**

| File | Change |
|---|---|
| `audit_dashboard/dashboard_enhancements.js` | design-doc href → GitHub blob URL (repo is **public**), `target="_blank" rel="noopener"` + dated comment |
| `audit_dashboard/money_ready_filter.js` | 5-agent-synthesis href → same treatment |
| `audit_dashboard/template.html` | `sysLinks['smart_money']` → `/findcryptopairs/audit-trail.html` following the map's own documented convention (`// Redirected: dead pages → closest living alternative`) + comment |

**Why GitHub links instead of deploying `/reports/`:** deploying to root `/reports/` would require new mappings in `tools/deploy_audit_files.py` **and** the inline 3-site FTP lists in `audit-dashboard.yml` (which batch B was concurrently editing — conflict risk), for two static docs. The repo is public, so blob links work on every site with zero deploy surface. If you'd rather keep readers on-site, the alternative is adding both `.md` files to the three FTP lists — revert this doc's changes and do that instead.

**How verified:**
1. `node --check` on both JS files → OK
2. Zero remaining `href="/references/"` (root) across `audit_dashboard/*.js` + `template.html`
3. `html.parser` pass on `template.html` → OK
4. All other root links (`/audit/*`, `/updates/*`) confirmed 200 by the sweep

**Rollback:** `git checkout -- audit_dashboard/dashboard_enhancements.js audit_dashboard/money_ready_filter.js audit_dashboard/template.html` (note: each file may also carry batch A/B edits — revert hunks selectively, not whole files, once committed).

**Post-deploy check:** click the ML-Gatekeeper "design doc" link, the money-ready banner "5-agent synthesis →" link, and a `smart_money` system card's detail link; none should 404.

## Batch C restoration (2026-11-25)

Working-tree edits lost between sessions (see batch-a doc restoration note);
re-applied against current main where still broken:

- **gatekeeper design-doc link** — still root `/reports/...` (404) in
  `dashboard_enhancements.js` → repointed to the GitHub blob URL (repo is
  public) + `target="_blank" rel="noopener"`, as originally specified. Verified
  `node --check` OK.
- **`smart_money` sysLink** — still relative `'smart_money/'` in
  `template.html:4042` → `/findcryptopairs/audit-trail.html` per the map's
  dead-page convention + dated comment.
- **money_ready_filter 5-agent-synthesis link** — *moot*: the reference no
  longer exists in that file (rewritten upstream); nothing to fix.

Live re-check 2026-11-25: root `/reports/...` still 404, `/audit/smart_money/`
still 404 → both restorations correct; `/audit/forward_clock.js` and
`/audit/excess_column.js` now 200 (batch A's deploy wiring did land).
