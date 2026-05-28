# Data-Quality Audit — Events + /audit Stocks (2026-05-28)

Two parallel read-only audits (events homepage, /audit EQUITY) plus the fixes that came out of them.

## Goal #3 — Events homepage: NOT SOLID

Live `events.json` (14,307 events) carries **5,277 quality violations (36.9%)**:

| Issue | Count | Examples |
|---|---|---|
| Stale (past-dated, non-recurring) | 5,255 | dating-events frozen at 2026-01-29; "Memory Work" (2022) |
| Missing thumbnails | 617 | "FREE KFC", "FREE AGO Wednesdays", "Winterlicious 2026" |
| Cancelled but `status:"upcoming"` | 22 | "CANCELLED: STEM Sundays" (title-prefix only, 21 of 22) |
| Placeholder text (TBD/TBA) | 11 | "***DATE TBD*** Disassemble a PC" |
| Title+venue+date duplicates | 4 | Summerlicious 2026, Nuit Blanche 2026 |

Venue/address/category/URL fields are clean.

### Root cause of the stale backlog (the dominant defect)

The **daily Scrape-events workflow has been failing every run since 2026-05-26**
(`gh run` 26449170700 → 26512711366). The failing step is "Validate JSON
outputs before commit": it asserted `metadata.totalEvents == len(events.json)`,
but `add_missing_events.py` and the date-outlier cull step both mutate
`events.json` *after* the scraper finalizes `metadata.json`. The mismatch fails
the assertion → no commit → `deploy-fte-events-json` finds no fresh
`next/events.json` → the live page keeps serving the stale cohort.

**Fix (commit `0eab0b31f`, branch `fix/audit-tier0-edge-pgates`):**
- Drop the premature equality assert in the validate step (`totalEvents` is
  derived data, not a source-of-truth integrity check).
- Add a "Resync metadata totalEvents" step after the cull that authors
  `totalEvents` from the final `events.json` across all 4 metadata files.
- **Requires merge to `main` to take effect** (workflow runs on `main`'s schedule).

### Secondary fix

`fix_event_data.py` cancelled-event detection was status-only (caught 1 of 22).
Now catches the title prefix `CANCELLED:` / `**CANCELLED**` and normalizes
`status` → `cancelled`.

### Still open

- Scraper DB-sync also reports `Access denied for user ejaguiar1_events@localhost`
  (separate P0 from the validate failure).
- The 5,255 stale events won't clear until the scrape workflow runs green on
  `main` and re-publishes; the `index.html:96` comment intentionally retains
  ~4,400 past events for title-lookup, so a blanket past-date purge is wrong.

## Goal #1 — /audit EQUITY stocks: live page was showing stale/fabricated data

EQUITY had **four divergent narratives** differing by ~3 orders of magnitude:

| Source | n | WR | PF |
|---|---|---|---|
| money_ready_verdict | 3 | 0% | 0.0 |
| pf_registry policy-clean-net (canonical) | 9 | 22.2% | 0.021 |
| raw-DB 2w summary | 8,249 | 66.7% | 5.55 |
| **live /audit HTML (stale)** | **426** | **51.4%** | **1.55 "T2 candidate – scale"** |

The live page's "T2-candidate-scale" text was hardcoded fallback rendered
because `dashboard_data.json.asset_class_health` is empty `{}`. The DB-Health
panel also cited 5 remediation commit hashes that **do not exist in git
history**. Both addressed by a concurrent peer commit (`f6333ce64`): DISPUTED
banner + "DATA INTEGRITY FAILURE" warning. **Note:** `template.html` /
`dashboard_enhancements.js` are NOT in `deploy_audit_files.py` UPLOADS — the
main `/audit` page needs a separate generate+deploy to go live (peer's lane).

The "EQUITY 14d improving to 67% WR" claim is a **measurement artifact** —
raw-DB read bypassing flicker-dedup, with `smart_money` source concentration at
61.6%. Canonical view is n=9 / 22% WR / PF 0.021. **EQUITY is FAIL, not Tier 2.**
