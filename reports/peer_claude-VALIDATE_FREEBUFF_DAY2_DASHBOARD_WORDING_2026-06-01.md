# Validate Freebuff Day-2 Dashboard Wording Branch — 2026-06-01

**Branch:** `fix/dashboard-wording-2026-05-31` commit `e6398e352`
**File touched:** `audit_dashboard/template.html` (+9 / -3)
**Author:** Freebuff (DeepSeek V4 Pro), day 2

## Verification Table (5 data-quality claims)

| # | Claim | Verdict | Reasoning |
|---|---|---|---|
| 1 | Ghost rows: 0 (was 22,947) | **DOESNT_REPRODUCE** | Live `db_health.json` (`/audit/data/db_health.json`) still reports `total_ghost_rows: 22947` across 10 cohorts (top: MEMECOIN/meta_strategy/DOGEUSDT n=3,569). The `at_raw_picks` zero-pnl count is 11,581. NULL-pnl-only in at_raw_picks IS 0, but canonical "ghost rows" per `tools/db_health_check.py:check_ghost_rows()` lives in `bt_backtest_trades` and is unchanged. |
| 2 | Status-PnL mismatches: 0 | **VERIFIED** | `(status='WON' AND pnl<0) OR (status='LOST' AND pnl>0)` = 0 in `at_raw_picks`. Also `pnl_integrity` live check shows `sign_mismatch: 130 / 24,158 sampled (0.54%)` — under the green tier threshold. |
| 3 | Non-canonical statuses 0 (WON/CLOSED_SL/CLOSED_TP/FLAT) | **VERIFIED** | Live `status_standardization` check: `n_non_canonical: 0`. SQL probe of CLOSED_SL/CLOSED_TP/FLAT in `trading_picks` and `at_raw_picks` = 0 rows each. |
| 4 | Backup tables removed | **VERIFIED** | `SHOW TABLES LIKE '%backup%2026%05%31%'` returns empty in `ejaguiar1_stocks`. No `at_raw_picks*backup*` tables exist. |
| 5 | BOND at_raw_picks: 78 (was 0-2) | **VERIFIED** | `SELECT COUNT(*) FROM at_raw_picks WHERE asset_class='BOND'` = **78**. Matches claim exactly. |

**Bonus:** "at_raw_picks UNKNOWN: 3 (was thousands)" — SQL returns 21 UNKNOWN/NULL. Close-ish; not 3 but materially down. Minor inaccuracy.

## Collision Check vs My Work Today

- **Main HEAD** (`6fca7d786`): `feat(audit): dashboard freshness panel + MC edge audit + shadow pilot verdicts` — added `<script src="dashboard_freshness.js"></script>` near line 18567.
- **Freebuff branch** forked from earlier (`941a81d61` based on diff) and its merge would **drop the dashboard_freshness.js script tag** (visible in `git diff 6fca7d786 e6398e352`).
- **Verdict: COLLISION = TRUE.** A direct merge of `e6398e352` would undo the freshness-panel wire-up. The text-update portion is clean, but the script tag removal is destructive collateral damage from being branched before main's freshness panel landed.

## Recommendation

- **Do NOT merge as-is** — would silently strip `dashboard_freshness.js`.
- **Path forward (low risk):** Cherry-pick the +9-line additive block (DATA QUALITY IMPROVEMENTS div) and the FOREX/BOND/as-of-date text updates, but skip the script-tag deletion. OR have Freebuff rebase on current `main`.
- **Per-claim fix:** Ghost row claim (#1) is overstated — the 22,947 baseline is `bt_backtest_trades`, not `at_raw_picks`, and is still 22,947 live. Text should say "at_raw_picks NULL-pnl ghosts: 0" or revert.
- **Branch status: FIX** (rebase + correct claim #1 wording).
- Operator decides tomorrow per directive.

## Sources

- Live: `https://findtorontoevents.ca/audit/data/db_health.json` (generated_at fresh)
- SQL: `mysql.50webs.com` `ejaguiar1_stocks` direct probe 2026-05-31
- Diff: `git diff 6fca7d786 e6398e352 -- audit_dashboard/template.html`
- Canonical defn: `tools/db_health_check.py:check_ghost_rows()` lines 173-240
