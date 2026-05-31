# EQUITY Pipeline Diagnosis (2026-05-31)

## Symptom: only 169 outcomes in `at_signal_outcomes` vs CRYPTO 53,480, FOREX 35,978

Peer `zoocode` DB query against `ejaguiar1_stocks.at_signal_outcomes` (grouped
by `asset_class`) confirms severe EQUITY emission shortfall:

| asset_class | rows in at_signal_outcomes |
|-------------|---------------------------:|
| CRYPTO      | 53,480 |
| FOREX       | 35,978 |
| EQUITY      | **169** |

This is a direct Goal #1 blocker: EQUITY currently sits at FAIL+INSUFF-N
(PF 0.90 / WR 33% / n=33 in `money_ready_verdict.json` 2026-05-24). With this
emission rate we cannot accumulate the n>=100 clean trades required to verify a
T2 verdict, regardless of whether the underlying strategies have edge.

## Architecture recap (where outcomes come from)

`at_signal_outcomes` is **not** written directly by the scanner. It is a
**mirror** populated by the outcome-resolver workflow:

1. Scanner (`alpha_engine/production_scanner.py` + `alpha_engine/scanner.py`)
   generates picks across CRYPTO/FOREX/EQUITY/COMMODITY/ETF/BOND universes
   and writes them to JSON ledgers (`alpha_engine/data/active_picks.json`,
   `closed_picks.json`, `expired_picks_archive.json`) and to MySQL
   `trading_picks` via `alpha_engine.outcome_resolver._sync_resolved_to_mysql_trading_picks`.
2. `alpha_engine/outcome_resolver.py` resolves TP/SL/EXPIRED outcomes against
   live prices, classifies them via `classify_outcome(pnl_pct, asset_class)`
   using `PNL_WIN_THRESHOLD_BY_CLASS` (CRYPTO 0.1bp, EQUITY/FOREX/COMMODITY
   5bp — alpha_engine/outcome_resolver.py:115-126).
3. `.github/workflows/outcome-resolver.yml` then runs
   `audit_trail/backfill_local_sources.py` to **mirror** resolved closed picks
   from JSON ledgers + other MySQL sources into `at_signal_outcomes` (INC #10
   fix, 2026-05-26, lines 132-158 of the workflow).

The 169 vs 53,480 split is therefore a question of **(a) how many EQUITY picks
the scanner actually emits and reaches resolution**, and **(b) how many of
those the mirror tags with `asset_class='EQUITY'`**.

## Findings (per-strategy emission audit)

### Finding 1 — Mirror's `derive_asset_class()` only recognizes 13 equity symbols (PRIMARY ROOT CAUSE)

`audit_trail/backfill_local_sources.py:45-60`:

```python
def derive_asset_class(s):
    s = s.upper().replace("-", "")
    equity = {"SPY", "QQQ", "IWM", "TLT", "GLD", "SLV", "COPX", "VIX",
              "DIA", "AAPL", "MSFT", "TSLA", "NVDA"}
    ...
    if any(s.startswith(e) for e in equity) or s in equity:
        return "EQUITY"
    ...
    if s.endswith("USDT") or s.endswith("USD") or s.endswith("BTC"):
        return "CRYPTO"
    return "UNKNOWN"
```

The function is called **for every mirrored row** at lines 144-171 and 262-344
to populate the `asset_class` column on `at_local_picks` and `at_signal_outcomes`.

Problems:
1. **Universe mismatch.** `alpha_engine/config.py:719` `EQUITY_SYMBOLS` contains
   ~35 names (AAPL/MSFT/NVDA/TSLA/AMZN/GOOGL/META/AMD/SPY/QQQ/… plus the
   penny/meme/gap-risk additions in `GAP_RISK_EQUITY_SYMBOLS`). `LARGE_CAP_EQUITY_SYMBOLS`
   (line 770) is a larger frozenset still. The mirror knows about **13** of those.
   `AMZN`, `GOOGL`, `META`, `AMD`, plus every breakout-scanner universe symbol
   (`alpha-equity-breakout.yml` scans top-N S&P names) and every `equity_strategies.py`
   ticker outside the 13 falls through to **`UNKNOWN`** in the mirror.
2. **CRYPTO catch-all collision.** The `if s.endswith("USD")` branch immediately
   below the equity check catches anything ending in "USD" — but more importantly,
   any equity-strategy pick whose JSON ledger did not embed `asset_class`
   gets re-derived here from symbol alone. The mirror does **not** read
   `pick["asset_class"]` from the source JSON when one is present (it always
   re-derives from `symbol`). See call site at line 151 and again at line 171:
   ```python
   derive_asset_class(symbol)
   ```
   regardless of any `asset_class` field already on the source row.
3. **`startswith` is dangerous.** `"AAPL220121C00100000"` (an option symbol that
   could leak in) would match `"AAPL"` and be tagged EQUITY — but `"GOOGL"` (a
   real equity universe member) does **not** start with any of the 13 equity
   names, so it lands as UNKNOWN.

**Hypothesis:** EQUITY picks ARE being emitted by the scanner at a healthy rate,
but the mirror mis-tags them as UNKNOWN or CRYPTO because the `derive_asset_class`
allowlist is stale. A quick verification query:

```sql
SELECT asset_class, COUNT(*) FROM at_signal_outcomes
WHERE symbol IN ('AMZN','GOOGL','META','AMD','NFLX','COST','AVGO','LLY',…)
GROUP BY asset_class;
```

should show those rows as `UNKNOWN` or `CRYPTO`, not `EQUITY`.

### Finding 2 — Bond emitter is in chronic failure

`gh run list --workflow alpha-engine-bond.yml --limit 3` shows 3-for-3 failures
(2026-05-28/29/30, ~17 min runtime each). BOND emission is broken, which
explains BOND n=8. While not directly about EQUITY, this confirms the pattern
that non-crypto emitters are silently underperforming and nobody has been
auditing emission counts per class until now.

### Finding 3 — Equity breakout scanner mostly green but rate-limited

`alpha-equity-breakout.yml` is weekdays 22:30 UTC only (~5 runs/week), vs the
crypto scanners which run hourly. Even if every breakout pick resolved cleanly,
the temporal cadence alone caps EQUITY n at roughly 1-2 orders of magnitude
below CRYPTO. Two recent runs (2026-05-26/27 03:12 cron) failed — secondary
emission gap.

### Finding 4 — PEAD equity is gated OFF in production

`alpha_engine/production_scanner.py:3987`:
```python
_PEAD_ENABLED = os.environ.get("PEAD_EQUITY_ENABLED", "0") == "1"
```
PEAD is shadow-only (default OFF). Per the comment block at lines 3975-3986,
this is intentional ("shadow PnL must validate against live EQUITY cohort for
>=4 weeks before promotion"). But with only 169 EQUITY outcomes, the live
cohort cannot validate the shadow — circular dependency.

### Finding 5 — Production scanner equity gating IS active

`production_scanner.py:2585-2655` shows the macro gate and the per-strategy
EQUITY blocklist (`yahoo_analyst_consensus`, `claude_gainer_ml`,
`value_quality_factor`, `consecutive_beats`, `earnings_drift`,
`dividend_aristocrats`, `penny_deep_oversold`, `extreme_oversold_bounce`,
`goldmine_1x/2x/3x/4x_consensus`) are blocked at Gate 0. That's **13 strategies
killed** before they can emit, all of which are EQUITY-tagged. The
`equity_strategies.EQUITY_STRATEGIES` registry (production_scanner imports at
line 289) ships 12 + 2 community strategies; the blocklist takes out the
historically negative-edge ones, which is correct, but it leaves only ~3-5
strategies actually able to emit EQUITY picks.

### Finding 6 — EQUITY conf floor 0.90 in macro-stressed regimes

`production_scanner.py:3815-3818` sets `_macro_equity_conf_floor = 0.90` when
the yield curve is inverted + Fed hiking. Combined with `MIN_ELITE_SCORE_BY_CLASS`
(line 2728) this further suppresses EQUITY emission during the macro regimes
we have been in. Not a bug per se, but it compounds Finding 5.

## Root Causes (specific file/line citations)

| # | File:line | Root cause | Magnitude |
|---|-----------|-----------|-----------|
| **1** | `audit_trail/backfill_local_sources.py:45-60, 151, 171` | `derive_asset_class()` allowlist contains 13 hard-coded tickers; mirror always re-derives from symbol and never reads source `asset_class` field. Equity picks for AMZN/GOOGL/META/AMD/NFLX/AVGO/LLY/COST/etc. mirror in as `UNKNOWN`. | PRIMARY |
| 2 | `.github/workflows/alpha-engine-bond.yml` | 3-for-3 failures last 3 days (sibling issue, confirms emitter neglect pattern) | High (BOND-only) |
| 3 | `.github/workflows/alpha-equity-breakout.yml` cron `30 22 * * 1-5` | EQUITY breakout scanner runs 5x/week vs CRYPTO scanners hourly | Medium |
| 4 | `production_scanner.py:3987 PEAD_EQUITY_ENABLED=0` | PEAD equity strategy default-off; chicken-and-egg with live cohort validation | Medium |
| 5 | `production_scanner.py:2641-2655` | 13 EQUITY strategies in Gate-0 blocklist — leaves ~3-5 active emitters | Medium (correct but compounds) |
| 6 | `production_scanner.py:3815-3818` macro_equity_conf_floor=0.90 | EQUITY confidence floor in inverted-yield-curve regime | Low |

## Fix Plan (concrete steps to bring EQUITY emission online)

### P0 — Fix the mirror's asset-class derivation (1-2 hours)

1. In `audit_trail/backfill_local_sources.py`, change `derive_asset_class()` to
   **prefer the source row's `asset_class` field** when present and non-empty,
   and only fall back to symbol-based inference otherwise:
   ```python
   def derive_asset_class(symbol, source_asset_class=None):
       if source_asset_class:
           ac = str(source_asset_class).upper().strip()
           if ac and ac != "UNKNOWN":
               return ac
       # ... existing symbol-based fallback ...
   ```
   Update both call sites (lines 151 and 171, plus the 262-344 closed-pick path).
2. Import `EQUITY_SYMBOLS` and `LARGE_CAP_EQUITY_SYMBOLS` from `alpha_engine.config`
   instead of hard-coding the 13-name allowlist. This makes the mirror's universe
   stay in sync with the scanner's universe.
3. Once shipped, run the mirror against the existing JSON closed_picks ledger
   (it uses `INSERT IGNORE` per the workflow comment; safe to backfill historic).
   This should re-tag thousands of misclassified rows.

**Acceptance criterion:** after P0 + one mirror re-run,
`SELECT COUNT(*) FROM at_signal_outcomes WHERE asset_class='EQUITY'` returns
>=1,000 (rough estimate; the JSON ledger is known to hold ~44+ EQUITY closed
picks per `tools/equity_mysql_edge_test.py:7`, plus thousands more should be
re-categorized from UNKNOWN/CRYPTO).

### P1 — Fix the bond emitter (separate, but same neglect pattern)

Triage `alpha-engine-bond.yml` failures. 17-minute runtime suggests it's
running to completion then erroring on commit or write — typical patterns are
DB password env mismatch or a schema column missing. (Note: 2026-05-30
commit `92c466bd6` added BOND to the `asset_class` ENUM; verify that DDL has
been applied to live MySQL — see `tools/migrations/20260530_add_bond_asset_class.sql`.)

### P1 — Increase EQUITY scan cadence

Change `alpha-equity-breakout.yml` cron from `30 22 * * 1-5` (5x/week) to at
least `0 */6 * * 1-5` (every 6 hours during weekdays) **after** the macro gate
+ confidence floor are tuned to avoid emission spam.

### P2 — Enable PEAD shadow → live promotion

Once EQUITY mirror data is healthy and we have 4 weeks of clean live cohort
data, promote PEAD per the existing wiring plan
(`reports/equity_walkforward_validation_2026-05-16.md`,
`updates/index.html 2026-05-17`). Toggle `PEAD_EQUITY_ENABLED=1` in the
production scanner env.

### P2 — Re-audit the EQUITY Gate-0 blocklist quarterly

The 13 blocked strategies were demoted on historical (possibly pre-resolver-fix)
data. Per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`, the right protocol is
mutate-before-kill: export closed CSV → `tools/mutation_analysis.py` → see if
any of the blocked strategies recover under tighter symbol/regime constraints
before keeping them in the blocklist.

## Risk

- **Mirror change is low-risk** because the mirror uses `INSERT IGNORE` and
  re-running it is idempotent (per the workflow comment block at lines 134-135).
  The only failure mode is mis-tagging in the **opposite** direction — e.g. if
  a CRYPTO pick somehow has an `asset_class='EQUITY'` field in JSON. Mitigate
  with a safety check: if symbol matches CRYPTO suffix pattern (USDT/BTC), keep
  the symbol-based class regardless of the source field.
- **Don't size-up EQUITY** off the back of the corrected count alone. Per
  CLAUDE.md ("never size up on historical numbers without verifying the
  14d/48h panels first"), the corrected mirror must be cross-checked against
  `audit_dashboard/data/pick_summary_stats_14d.json` (EQUITY 37→67% WR
  improving) before any allocation change.
- **PEAD promotion is gated by a separate validation report**; do not bypass.

## Sources

- Peer `zoocode` DB query against `ejaguiar1_stocks.at_signal_outcomes`
  (2026-05-31, grouped by `asset_class`): CRYPTO 53,480 / FOREX 35,978 / EQUITY 169.
- `audit_trail/backfill_local_sources.py` (INC #10 mirror, lines 45-60, 144-171, 262-344).
- `alpha_engine/outcome_resolver.py:115-126` (PNL_WIN_THRESHOLD_BY_CLASS).
- `alpha_engine/production_scanner.py` (lines 2585-2655 EQUITY blocklist;
  3815-3818 macro conf floor; 3975-3990 PEAD shadow gate).
- `alpha_engine/scanner.py:1113-1145, 2070-2191, 4117-4155` (EQUITY strategy registration + emission path).
- `alpha_engine/config.py:719-790` (EQUITY_SYMBOLS, LARGE_CAP_EQUITY_SYMBOLS).
- `.github/workflows/outcome-resolver.yml:132-158` (mirror invocation).
- `.github/workflows/alpha-engine-bond.yml` 3-for-3 failures last 3 days.
- `tools/equity_mysql_edge_test.py:1-19` (prior context: "JSON ledger holding only ~44 EQUITY closed picks").
- `money_ready_verdict.json` 2026-05-24 (EQUITY FAIL+INSUFF-N PF 0.90 / WR 33% / n=33).
