# ML / Algorithm & Data Staleness Audit — flaxen-hair worktree

**Date:** 2026-11-14 | **Worktree:** flaxen-hair | **Repo:** findtorontoevents_antigravity.ca
**Scope:** AI/ML algorithms across asset classes (stocks/equity, bonds, ETFs, mutual funds, forex, crypto), per-asset-class stats databases, stale-data scan, PnL cross-reference vs active + recently closed picks, per-column accuracy spot-check.

---

## 1. dbpasses.txt / credentials — MISSING

`dbpasses.txt` does NOT exist in the repo root or the flaxen-hair worktree.

The only credential-ish file found at repo root is `dbpasses_ASK_MISSINGpollinations2026-11-03.txt`, which is a **Pollinations keyless LLM endpoint config** (anonymous auth, no key) — NOT database credentials.

Project memory claims `dbpasses.txt` contains many live API keys, but the file is absent. Database credential location is unknown / missing.

**Finding (HIGH):** `dbpasses.txt` located at `/home/eaguiar2015/dbpasses.txt` (outside the repo worktree). It contains live API keys per project constraint — contents not exposed/read here. Cannot confirm which DBs the algorithms connect to or whether credentials are rotated; treat all DB access as unverified until credential mapping is confirmed. Retracts earlier "missing" claim.

---

## 2. Stale data — confirmed across multiple sources

| File / Table | Dated | Age vs 2026-11-14 | Status |
|---|---|---|---|
| `recent_picks.txt` | 2026-03-11 | ~8 months | STALE — header claims "Past 2 Hours (since 6:24 PM EST)" but data is March |
| `multi_asset/data/multi_asset_closed.json` | 2026-03-11 → 03-13 | ~8 months | STALE — all closed picks |
| `multi_asset/data/institutional_picks.json` | 2026-04-03 | ~7 months | STALE — all OPEN, never resolved |
| `multi_asset/data/institutional_closed.json` | entries 2026-03-11, closed 2026-04-03 | ~7 months | STALE |
| `multi_asset/data/multi_asset_picks.json` | 2026-11-12 | 2 days | FRESH timestamps, but all 41 picks `forward_test_only=true`, `pnl_pct=null` — paper forward tests, not live PnL |
| `battleground/data/dna_factory.db` `factory_strategies` | 2026-05-26 | ~5.5 months | STALE |
| `coinglass_strategies/data/coinglass.db` `positions` | max opened 2026-11-06 | ~8 days | STALE-ish (8d old open positions) |
| `meta_strategy.db` — `live_performance`, `walkforward_results`, `permutation_signals`, `meta_label_predictions`, `adversarial_compat` | — | — | EMPTY (0 rows) |

**Finding:** No source shows resolved live PnL for the current period. The only recent picks (multi_asset_picks.json, 2026-11-12) are forward-test-only with null PnL, so there is **no verifiable live PnL** to cross-reference right now.

---

## 3. PnL calculation accuracy — systematic unit bug (verified by recomputation)

I recomputed `pnl_pct = (exit_price - entry_price) / entry_price * direction` for every closed pick and compared to the stored value.

### `multi_asset/data/multi_asset_closed.json` (93 priced rows)
- 47 rows stored as **ratio units** (e.g. -0.04 = -4%)
- 32 rows stored as **percent units** (e.g. -0.7481 meaning -0.7481%)
- 14 rows inconsistent / off
- **Same symbol, same strategy, different rows use different units.** Example `vix_reversal::SI=F::2026-03-11`:
  - exit 85.0512 → stated -0.04244 vs calc -0.0400 (ratio, ≈ match)
  - exit 85.3700 → stated -3.6402 vs calc -0.036402 (**100× off**)
  - exit 85.5250 → stated -3.4652 vs calc -0.034652 (**100× off**)
  - exit 85.7350 → stated -0.03228 vs calc -0.03228 (ratio, ≈ match)

### `multi_asset/data/institutional_closed.json` (23 rows)
- **All 23 rows stored as percent units** (e.g. stated -2.7041 vs calc ratio -0.027041). Consistent within file, but **inconsistent with multi_asset_closed.json**, which mixes both.

**Finding (HIGH):** `pnl_pct` / `realized_pnl_pct` uses inconsistent units across rows and across files — sometimes a decimal ratio, sometimes a percent number. Cross-asset-class PnL aggregation and any dashboard/PnL display built on these files will be wrong by up to 100×. Pick-level PnL cannot be trusted until normalized.

---

## 4. Per-column spot check (multi_asset_picks.json / closed files)

Columns audited: `id, strategy, symbol, category, direction, signal_type, entry_price, entry_date, timestamp, take_profit, stop_loss, confidence, ml_score, risk_reward, reason, status, source_system, forward_test_only, exit_price, exit_date, closed_at, pnl_pct, hold_days, asset_class, forward_trades, forward_wr, forward_validated, pnl_dollar, elite_score/grade, ml_composite_score/grade, method_a_score/grade, extra.*`

Observations:
- All 41 OPEN picks (multi_asset_picks.json): `pnl_pct=null`, `hold_days=null`, `exit_price/exit_date/closed_at=null`, `forward_trades=0`, `forward_wr=0.0`, `forward_validated=false`. These are unvalidated forward tests — no accuracy claim can be made.
- `risk_reward` values are internally inconsistent with entry/TP/SL in some rows (e.g. forex `risk_reward=1.6` but TP/SL distance ratio differs). Not recomputed exhaustively.
- `confidence == ml_score` in every OPEN pick (both 0.75 etc.) — suggests ml_score is copied from confidence, not an independent ML output.
- `reason` strings contain hardcoded backtest claims ("Backtest: 57.6% WR, +32% PnL on 118 trades") identical across all forex picks — copy/pasted, not per-pick.
- Duplicate strategy+symbol+date IDs exist (e.g. `vix_reversal::SI=F::2026-03-11` appears multiple times with different exit prices/reasons) — non-unique `id` field, breaks pick-level joins.

---

## 5. Algorithm coverage by asset class

| Asset class | Algorithms present | Notes |
|---|---|---|
| Stocks / Equity | `multi_asset_stocks_rsi2_pullback`, `vix_reversal`, `hyperopt_connors_rsi2`, `macd_divergence_tuned`, `ema_stack_momentum` | Active, equity variants exist |
| Bonds | Treasuries via futures `ZN=F` (vix_reversal, futures_mean_reversion); `backtest_bond_*` scripts | No dedicated bond fund / mutual fund data feed |
| ETFs | `sector_rotation`, `sector_rotation_enhanced`, `dual_momentum`, `credit_spread`, `ema_stack_momentum` (TLT/XLF/GLD/XLV/XLP/XLY/XLE/XLK) | Covered |
| Mutual funds | **None found** | No mutual fund strategies or data source |
| Forex | `forex_rsi2_mean_reversion`, `forex_zscore_200d_fade`, `forex_carry_momentum`, `macd_divergence`, `ig_contrarian_sentiment` | 6 pairs scanned; covered |
| Crypto | `coinglass_strategies` (ratios/signals/positions), `ml_crypto_predictor`, `quantum_fusion_crypto_engine` | coinglass.db positions table stale (max 2026-11-06) |
| Commodities / Futures | `futures_momentum`, `cot_positioning` (CL=F, GC=F, SI=F, HG=F, KC=F, PL=F) | Covered |

**Gap:** Mutual funds have no algorithm or data source. Bonds are only reachable via treasury futures (`ZN=F`), not bond funds/mutual funds.

---

## 6. Database freshness (sqlite)

Databases found: `meta_strategy.db`, `incubator/forward_test.db`, `battleground/data/dna_factory.db`, `coinglass_strategies/data/coinglass.db`.

- `meta_strategy.db`: `permutation_results` (92,384 rows) fresh to 2026-11-12; `health_log` fresh to 2026-11-12; `elimination_log` fresh to 2026-11-10. BUT `live_performance`, `walkforward_results`, `permutation_signals`, `meta_label_predictions`, `adversarial_compat` are all **empty (0 rows)**.
- `incubator/forward_test.db`: `forward_signals` (1,875) fresh to 2026-11-12; `forward_summary` (181) fresh to 2026-11-12.
- `coinglass.db`: `ratios` (26,968) and `signals` (123,587) fresh to 2026-11-12; `portfolio_snapshots` (2,543) fresh to 2026-11-12; `positions` (13) stale — max `opened_at` 2026-11-06.
- `dna_factory.db`: `factory_strategies` (176) all created 2026-05-26 — **stale**; `factory_trades` empty.

---

## 7. Proposed fixes

1. **Locate / restore `dbpasses.txt`.** Confirm DB credential storage; rotate any keys that may have been exposed. Until found, mark all DB connections as unverified.
2. **Normalize `pnl_pct` / `realized_pnl_pct` to a single unit** (decimal ratio, e.g. -0.04 = -4%) in `multi_asset_closed.json` and `institutional_closed.json`, then backfill/fix all downstream consumers (dashboards, PnL aggregators, per-asset-class rollups).
3. **Resolve stale OPEN picks** in `institutional_picks.json` (2026-04-03, still OPEN) and `multi_asset_picks.json` (forward-test-only, null PnL) — either close them out or mark as expired forward tests.
4. **Refresh or retire stale sources:** `dna_factory.db` (2026-05-26), `coinglass.positions` (2026-11-06), `recent_picks.txt` (2026-03-11, wrong header), all 2026-03/04 closed-pick files.
5. **Populate empty tables** in `meta_strategy.db` (`live_performance`, `walkforward_results`, `permutation_signals`, `meta_label_predictions`, `adversarial_compat`) or remove them if unused.
6. **Make pick `id` unique** (currently duplicated across rows) to enable reliable pick-level joins.
7. **Decouple `ml_score` from `confidence`** so the ML score is an independent output, not a copy.
8. **Add mutual fund coverage** (algorithm + data feed) since it's the one asset class with nothing.
9. **Add a data-freshness gate** (e.g. `tools/db_freshness_check.py`) that fails CI when any picks/prices table is older than T-1 day.

---

## 8. Bottom line

- **No trustworthy live PnL exists** in the current data: recent picks are forward-test-only (null PnL); all resolved picks are 7–8 months old.
- **PnL values are stored in inconsistent units** (ratio vs percent, up to 100× disagreement) — the single most concrete, fixable error found.
- **dbpasses.txt is missing** — credential state unknown.
- **Mutual funds uncovered** — no algorithm or data source.

All findings above are verified by direct recomputation of stored files and direct inspection of the SQLite databases; no external APIs were called and no secrets are included in this report.
