# Banner True State — phantom_expired & lm_signals_resolver characterized

Date: 2026-05-31
Author: Claude Opus 4.7 (banner-true-state subagent)

## TL;DR

- **Live banner is honestly GREEN.** `https://findtorontoevents.ca/audit/data/db_health.json` shows `overall.any_red=false`, only 5 Tier‑1 checks ran, all pass (one yellow for ghost_rows).
- **Zoo is also right.** When the FULL suite is run (`--check phantom_expired --check lm_signals_resolver`), two REDs appear:
  - `phantom_expired` Tier 2 → `worst_phantom_pct=100.0` (FOREX, EQUITY, FUTURES, ETF, PENNY_STOCK every single expired row is a phantom).
  - `lm_signals_resolver` Tier 3 → `no_resolve_pct=96.48` (34,796/36,066 expired lm_signals have exit_price IS NULL or 0).
- **Why both are true:** the cron in `.github/workflows/audit-dashboard.yml:229` runs `db_health_check.py --quick`, and `QUICK_CHECKS` only contains 5 Tier‑1 names. The 6 Tier‑2/3 checks (`phantom_expired`, `outcome_coverage`, `ml_feature_store`, `signal_tier_writer`, `lm_signals_resolver`, `won_pnl_contradiction`) never execute on the production pipeline.
- **Neither RED is a check bug.** Both are class **(b) FIX THE DATA** — they touch the resolver / sync pipeline.
- **Action:** docs PR + operator escalation. No autonomous-safe code fix shipped.

## Hard verification (verbatim)

```
curl -sL https://findtorontoevents.ca/audit/data/db_health.json | jq ...
{
  "gen": "2026-05-31T06:41:42.122077+00:00",
  "any_red": false,
  "checks": [
    {"name":"status_standardization","tier":"green","threshold_pass":true},
    {"name":"open_bloat","tier":"green","threshold_pass":true},
    {"name":"won_pnl_contradiction","tier":"green","threshold_pass":true},
    {"name":"ghost_rows","tier":"yellow","threshold_pass":true},
    {"name":"pnl_integrity","tier":"green","threshold_pass":true}
  ]
}
```

Then locally `python3 tools/db_health_check.py --check phantom_expired --check lm_signals_resolver --json`:

```
phantom_expired.by_class:
  CRYPTO        14764  phantoms=0       0.00 %
  MEMECOIN       1202  phantoms=0       0.00 %
  FOREX          6072  phantoms=6072  100.00 %
  EQUITY         4416  phantoms=4416  100.00 %
  FUTURES        5520  phantoms=5520  100.00 %
  ETF            1104  phantoms=1104  100.00 %
  PENNY_STOCK     552  phantoms=552   100.00 %
worst_phantom_pct = 100.0  → tier=RED  threshold_pass=false

lm_signals_resolver:
  expired_n     = 36,066
  no_resolve_n  = 34,796
  no_resolve_pct= 96.48  → tier=RED  threshold_pass=false
```

## Definitions

### `check_phantom_expired` (tools/db_health_check.py:387-419)
- Query: per `asset_class` on `bt_backtest_trades USE INDEX (idx_bt_status) WHERE status='expired'`.
- "Phantom" = `pnl_pct=0 AND exit_price=entry_price` on an expired row. Means the resolver never wrote a real intrabar exit, just left a breakeven placeholder.
- Thresholds: green <10 %, yellow <50 %, red ≥50 %.

### `check_lm_signals_resolver` (tools/db_health_check.py:523-543)
- Query: `lm_signals WHERE status='expired'`.
- "No resolve" = `exit_price=0 OR exit_price IS NULL`.
- Thresholds: green <5 %, yellow <30 %, red ≥30 %.

## Diagnosis

### phantom_expired — class (b) DATA pipeline
- CRYPTO/MEMECOIN: 0 % phantoms across 15,966 expired rows → the CRYPTO resolver path writes real exit_price.
- All five non‑crypto classes: **exactly 100 %** phantoms. Not a sampling artifact — every single expired row was written with `exit_price=entry_price, pnl_pct=0`.
- Writer is `sync_all_picks_to_mysql.py` / `audit-daily.py` (not `outcome_resolver.py`, which writes to `trading_picks`).
- The non‑crypto backtest sync path is timing out picks at expiry and persisting a breakeven placeholder rather than fetching the bar at `expiry_ts`. This silently inflates the non-crypto sample with WR-neutral, PF-neutral rows.
- **Production impact:** any analysis that groups by status='expired' on non-crypto in `bt_backtest_trades` is reading 17,664 rows of structurally false data. The CRYPTO path remains trustworthy. This contradicts the "post-fix asset_class_health is trustworthy" claim in CLAUDE.md for non-crypto if any non-crypto class consumer is reading expired rows from bt.
- **NOT autonomous-safe:** touches the backtest sync writer; needs operator sign-off and a price-path fetch (Binance/yfinance/IBKR/etc.) per the SL-optimization rule (`reference-sl-optimization-needs-pricepath`).

### lm_signals_resolver — class (b) DATA pipeline
- 96.48 % of expired `lm_signals` carry no exit_price.
- This is the `lm_signals` table specifically (LM = language-model signal source). The `lm_signals` resolver wire-up never wrote exit_price on expiry; entries time out and stay zero.
- **Production impact:** the `lm_signals` source contributes garbage rows to any pf/wr aggregation that joins on `lm_signals`. If a strategy registry consumer reads `lm_signals` expired rows, it sees 36k breakeven non-events.
- **NOT autonomous-safe:** needs the lm_signals expiry resolver to fetch a real exit price. Production scoring path.

### Why this is NOT a check bug (vs PR #208 pnl_integrity)
- PR #208 fixed a false-positive in `check_pnl_integrity` (the check itself was wrong).
- Here the SQL is correct, the thresholds are reasonable industry hygiene (≥50 % phantoms = systemic), and the numbers reproduce against live MySQL. The check is honest.

## Why the live banner stayed GREEN

`.github/workflows/audit-dashboard.yml:229` runs:

```bash
python tools/db_health_check.py --quick
```

`QUICK_CHECKS = {"pnl_integrity", "ghost_rows", "open_bloat", "status_standardization", "won_pnl_contradiction"}` (tools/db_health_check.py:629).

So `phantom_expired` and `lm_signals_resolver` never run on cron → never appear in the published `db_health.json` → banner has no signal. The `overall.any_red` field also references `--quick`'s 5-check run, so it's structurally Tier‑1 only in production output.

This is arguably a design choice (banner = Tier‑1 only, intentional). It is also a transparency gap when Tier‑2 systemic damage exists.

## Recommendations (operator decisions)

1. **Resolver fix #1 — bt_backtest_trades non-crypto sync.** Locate the writer in `sync_all_picks_to_mysql.py` / `audit-daily.py` that finalizes expired rows for non-crypto classes. Replace the breakeven placeholder with a price fetch at `expiry_ts ± 1bar` (Binance/CCXT for FX synthetic, yfinance/Polygon for equity/etf/penny, CME/yfinance for futures). Then rerun the sync for the affected ~17,664 rows.
2. **Resolver fix #2 — lm_signals.** Audit the lm_signals expiry path. If no resolver wire-up exists, add one (read `entry_ts`, `expiry_ts`, `symbol`, fetch close at `expiry_ts`, write `exit_price` + recompute `pnl_pct`).
3. **Banner transparency tweak (optional, low risk).** Either (a) run `tools/db_health_check.py` without `--quick` on a longer cadence (e.g. daily instead of every audit cycle), emitting to a separate `db_health_full.json`; or (b) keep `--quick` for the banner but surface a Tier‑2/3 sub-panel on `/audit/dbhealth.html` so phantom_expired + lm_signals_resolver aren't invisible.
4. **DO NOT raise the phantom threshold.** 100 % across five classes is not a sample-size artifact.

## Autonomous classification

| Check | Class | Autonomous-safe? | Reason |
| --- | --- | --- | --- |
| `phantom_expired` | (b) DATA | NO | Backtest-sync writer change, ~17,664 rows backfill |
| `lm_signals_resolver` | (b) DATA | NO | Resolver wire-up on production signal source |

No code/check fix is shippable from this seat. Escalating via docs PR.

## Deliverables

- This report: `reports/peer_claude-banner-true-state_2026-05-31.md`
- Server-side docs PR (no code): characterization + operator action list.
