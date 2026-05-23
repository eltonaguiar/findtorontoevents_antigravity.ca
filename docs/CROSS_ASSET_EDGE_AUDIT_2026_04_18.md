# Cross-Asset Edge Audit — 2026-04-18

**Scope:** Verify the user's claim that stocks/ETFs are outperforming crypto, and audit cross-asset strategy applicability.
**Primary data:** `alpha_engine/data/closed_picks.json` (4,391 CLOSED rows) and `audit_dashboard/data/dashboard_data.json` (`summary.non_crypto_performance`).
**Window:** trailing 90 days ending 2026-04-18.
**Rule:** every number below is cited to a row-count and file. Anything not reproducible from closed_picks is flagged.

---

## Executive summary (read this first)

1. **The user's belief is partially supported, but NOT by `closed_picks.json`.** The canonical alpha_engine closed-picks store is effectively 100% crypto (4,386 / 4,391 = 99.89% of rows). There are **zero** CLOSED equity or ETF rows in that file inside the 90-day window. The claim "stocks/ETFs are beating crypto" is *only* visible on the /audit dashboard, which is fed from a **different** pipeline (`compute_non_crypto_performance(active, closed)` at `audit_trail/dashboard_generator.py:10591`) that never reads `alpha_engine/data/closed_picks.json`.
2. **Dashboard numbers, taken at face value, DO show EQUITY and ETF beating CRYPTO on realized PnL.** `summary.non_crypto_performance` reports EQUITY n=347 closed, WR=49.6%, total_pnl_pct=+218.09 and ETF n=70, WR=48.6%, total_pnl_pct=+4.54, vs. CRYPTO (from `closed_picks.json`) n=4,386, WR=29.0%, total_pnl_pct=-680.4%. If both numbers are valid, equities win by ~900pp of total PnL on 1/12 the sample.
3. **Two winners are inversion candidates.** `quan_engine_scalp` (n=448, WR=25.2%, total=-77.7%) mirrored to SHORT would yield WR=74.8%, total=+77.7%. The repo already has inversion infrastructure (`alpha_engine/quan_engine_scalp_hybrid_inverse.py`, `inverse_strategies.py`, `inverse_edge_system.py`, `inverse_loser_mutations.py`, `kimi_inverse_scanner.py`, `inverse_contrarian_analysis.py`) — this is a *deployable* finding, not a theoretical one.

---

## Task 1 — Realized performance by asset class (90d)

Source: `alpha_engine/data/closed_picks.json`, all 4,391 rows (`status == 'CLOSED'`). 100% of them fall inside the 90-day window ending 2026-04-18 (file does not retain older history).

Classifier (as specified):
- **crypto** = suffix USDT / USDC / BUSD / USD (non-FX)
- **forex** = six-letter FX pairs (EURUSD etc.)
- **etf** = known tickers list (SPY, QQQ, IWM, TQQQ, SQQQ, XLE, XLF, ARKK, …)
- **commodity** = GLD, USO, UNG, SLV, DBA, DBC, IAU
- **equity** = 1–5 letter alpha ticker not in ETF/commodity sets

### Realized table (from closed_picks.json)

| asset class | n | WR | avg_pnl% | total_pnl% | Wilson 95% LB | avg hold (h) |
|---|---:|---:|---:|---:|---:|---:|
| crypto | 4,386 | 29.0% | -0.155 | **-680.4** | 27.7% | 7.0 |
| unknown | 5 | 0.0% | 0.00 | 0.0 | 0.0% | 0.0 |
| equity | **0** | — | — | — | — | — |
| etf | **0** | — | — | — | — | — |
| forex | **0** | — | — | — | — | — |
| commodity | **0** | — | — | — | — | — |

**Ranking from closed_picks: there is only one asset class with data (crypto), and it is losing money.** The 5 "unknown" rows are malformed symbols (not a sample worth interpreting).

### Top strategies inside crypto (90d, n>=5 only — few strategies have large n on this feed)

| strategy | n | WR | total_pnl% |
|---|---:|---:|---:|
| rsi_overbought | 5 | 60.0% | +6.2 |
| quan_engine_swing | 34 | 32.4% | +0.1 |
| quan_engine_position | 11 | 0.0% | -0.4 |
| macd_crossover | 16 | 68.8% | -1.7 (high WR, negative PnL = asymmetric R:R) |
| rsi_bounce | 11 | 36.4% | -2.5 |
| quan_engine_scalp | 448 | 25.2% | **-77.7** |
| (blank strategy, bucket "unknown") | 3,780 | 29.4% | **-501.3** |

The bulk of the crypto loss comes from the ~3,780 rows where `strategy` is null/missing; these are `source_system='quan_engine'` scalp-style trades that never got a `strategy` tag. That is a data-hygiene issue in its own right — cited from rows where `strategy` is absent but `source_system` is populated.

---

## Task 2 — Dashboard tile verification (and the data-source delta)

Dashboard file: `audit_dashboard/data/dashboard_data.json`, key path `summary.non_crypto_performance`.

### What the dashboard shows

| category | active | closed | wins | losses | flat | WR | total_pnl% |
|---|---:|---:|---:|---:|---:|---:|---:|
| EQUITY | 4 | 347 | 172 | 162 | 13 | **49.6%** | **+218.09** |
| ETF | 0 | 70 | 34 | 33 | 3 | 48.6% | +4.54 |
| COMMODITY | 1 | 475 | 120 | 134 | 221 | 25.3% | +23.84 |
| FOREX | 3 | 823 | 215 | 231 | 377 | 26.1% | -12.90 |
| BOND | 0 | 17 | 8 | 8 | 1 | 47.1% | +2.84 |
| FUTURES | 0 | 0 | — | — | — | — | 0.0 |
| STOCK | 0 | 0 | — | — | — | — | 0.0 |
| **aggregate** | 8 | 1,732 | 549 | 568 | 615 | 31.7% | **+236.41** |

### Delta vs. closed_picks.json

| category | closed_picks n | dashboard n | delta |
|---|---:|---:|---:|
| EQUITY | 0 | 347 | **+347** |
| ETF | 0 | 70 | **+70** |
| COMMODITY | 0 | 475 | **+475** |
| FOREX | 0 | 823 | **+823** |
| BOND | 0 | 17 | **+17** |

**Every single non-crypto row on the dashboard is invisible to `closed_picks.json`.** That's not a >5pp/>$10 discrepancy — it's a 100% source divergence.

### Where the dashboard's numbers actually come from

`audit_trail/dashboard_generator.py:10591` defines `compute_non_crypto_performance(active, closed)`. It is called at line 12487 with `final_active_picks` and `resolved_closed`, and again at line 13197 (post-gate re-compute). Neither call reads `alpha_engine/data/closed_picks.json`. The closed feed is built earlier in the generator from multiple per-system closed files — e.g. `copy_trader_intel/data/closed_trades.json`, `multi_asset/data/active_picks.json` (for actives), `audit_trail/data/non_crypto_pick_audit.json`, plus the various per-system `closed_picks.json` files under `battleground/`, `mercury2/`, `genome/`, `KIMI_RISEOFTHECLAW/`, `crypto_signal_engine/`, `ml_battleground/system_a_filter/`, etc.

The bucketing itself uses `nc_asset_category_for_pick` (caps each pick at +/-500% via `max(-500, min(500, pnl))`), filters with `_outcome_bucket_from_pnl` (wins/losses/flat), and rounds to 1-2 dp. No further time-window filter is applied — it is **all resolved closed** from whatever feeders were loaded, not 90d. That, plus the separate feed, fully explains the delta.

**Verdict for Task 2:** the dashboard tiles are not reproducible from `closed_picks.json`. The delta is driven by (a) different source files, (b) no 90-day window on the dashboard side, (c) different outcome bucketing (flat vs. win/loss via `_outcome_bucket_from_pnl`, not raw sign-of-pnl). This is not a "bug" in the >5pp/$10 sense — it is *by design*, but the design is confusing: the /audit page is comparing apples (multi-feed all-time non-crypto) to oranges (alpha_engine-only 90d crypto), and the user's "stocks beat crypto" read is real only under that cross-feed comparison.

---

## Task 3 — Symbol-lockdown audit

Strategies in `closed_picks.json` with n >= 30 inside the 90-day window:

| strategy | n | unique_symbols | name-locked? | per-symbol WR std-dev | top symbols (count) |
|---|---:|---:|---|---:|---|
| (null strategy, source=quan_engine) | 3,780 | 20 | n/a | 0.124 | MATICUSDT 786, BTCUSDT 421, KASUSDT 398 |
| quan_engine_scalp | 448 | 19 | No | **0.196** | MATICUSDT 103, TRXUSDT 66, HYPEUSDT 51 |
| volume_spike_breakout | 39 | 19 | No | 0.000 | UUSDT 18, TAOUSDT 4, JTOUSDT 1 |
| quan_engine_swing | 34 | 2 | No | 0.008 | TAOUSDT 28, HYPEUSDT 6 |

**None of the n>=30 strategies are name-locked** (no `ml_enhanced_RENDERUSDT_*` or `ml_enhanced_FETUSDT_*` pattern appears in `closed_picks.json` at n>=30; those rows exist only in forward-validator / genome feeds not merged into this file at that scale).

**High-variance flags (symbol-WR std-dev > 0.15, candidate for symbol-specific tuning):**
- `quan_engine_scalp` — std = 0.196 across 19 symbols. WR varies dramatically symbol-by-symbol; top-3 concentration (MATICUSDT/TRXUSDT/HYPEUSDT) matches the concentration penalty already embedded in elite_breakdown (`source_concentration_penalty: -18` visible on sample rows). This strategy should be symbol-gated, not globally demoted.
- `quan_engine_swing` (n=34) has std=0.008 but only covers 2 symbols, so std is not meaningful.

The 3,780 "null-strategy" rows are structurally `quan_engine` scalp trades. std=0.124 across 20 symbols is moderate; concentrated in MATIC/BTC/KAS.

**Note:** symbols like `ml_enhanced_FETUSDT_1h_D_ensemble_stack` DO exist in the codebase (see `alpha_engine/forward_validator.py`, `genome/seed_strategies.py`) but do not appear at n>=30 in this closed-picks snapshot — they are tracked in forward-validation feeds, not here.

---

## Task 4 — Inversion / DNA-mutation candidates

Filter: n >= 50, WR < 40%, total_pnl < 0, invert pnl_pct sign (proxy for flipping LONG↔SHORT on same entries/exits):

| strategy | n | orig WR | orig total% | inv WR | inv total% | candidate? |
|---|---:|---:|---:|---:|---:|---|
| quan_engine_scalp | 448 | 25.2% | -77.7 | **74.8%** | **+77.7** | **YES** (WR>55, PnL>0) |
| (null strategy / quan_engine bulk) | 3,780 | 29.4% | -501.3 | 70.6% | +501.3 | YES (but needs strategy-tagging cleanup first) |

**Caveat on the inversion math:** flipping `pnl_pct` sign is a first-order proxy. It ignores that the SHORT entry would face different slippage, the TP/SL would swap asymmetrically (current take_profit/stop_loss widths are not symmetric around entry for most rows — sample row shows entry 0.3794, TP 0.38506, SL 0.37657 → RR≈2.0 LONG would be RR≈0.5 if naively inverted). So the +77.7% upper bound is optimistic. The real deployment path is the existing `quan_engine_scalp_hybrid_inverse` module, which applies KEEP_LONG / INVERT / BLOCK per-symbol overrides instead of a blanket flip.

### Existing inversion machinery in the repo (confirmed present, not theoretical)

- `alpha_engine/quan_engine_scalp_hybrid_inverse.py` — symbol-level override matrix with execution guards (max-slippage, max-fill-rate) and symmetric TP/SL for the inverted side. Integration test at `tests/test_quan_engine_scalp_hybrid_inverse.py` asserts WR ≈ 71%, PF ≈ 2.89 on a synthetic 414-trade M_HYBRID slice — directly consistent with the 74.8% inv WR computed above.
- `alpha_engine/inverse_strategies.py`
- `alpha_engine/inverse_edge_system.py`
- `alpha_engine/inverse_loser_mutations.py`
- `alpha_engine/inverse_contrarian_analysis.py`
- `alpha_engine/kimi_inverse_scanner.py`

**Recommendation:** the loss on `quan_engine_scalp` is already being addressed by `quan_engine_scalp_hybrid_inverse`. Verify it is wired into the live scanner (not just the test harness) before expanding.

---

## Task 5 — Cross-symbol transplantation candidates

Filter: n >= 30, Wilson LB > 50%, avg_pnl > 0.

**Result from closed_picks.json: zero strategies pass.** `rsi_overbought` has WR=60% but n=5 (below threshold). `macd_crossover` has WR=68.8% but total PnL negative (asymmetric R:R — wins are small, losses are big). `quan_engine_swing` at n=34 has WR=32.4%, Wilson LB well under 50%.

That means the question "can `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` be transplanted to FETUSDT/AVAXUSDT/INJUSDT?" **cannot be answered from `closed_picks.json`** — that strategy is not present at n>=30 in this file. Those models live in the forward-validator pipeline and genome catalog (`genome/data/unified_strategy_catalog.json`, `alpha_engine/forward_validator.py`).

**What the backtest would need (documented, not executed):**
1. Per-symbol ATR% history and dollar-volume liquidity for the candidate universe (FETUSDT, AVAXUSDT, INJUSDT) over the training window used for RENDER's ensemble stack.
2. The serialized ensemble model weights (currently keyed by symbol in `alpha_engine/ml_enhanced_*`).
3. A cross-sectional similarity score on (ATR%, funding rate behavior, listing age, dominant venue). RENDER and FET are both mid-cap AI-narrative alts; AVAX is L1, INJ is appchain — feature drift is non-trivial.
4. Walk-forward OOS with the same TP/SL/max_hold_bars config as the RENDER incumbent.

---

## Task 6 — Stock/ETF paper-trade recommendation

Filter: strategy × symbol × direction in EQUITY or ETF class, n >= 30, Wilson LB > 50%, from `closed_picks.json`.

**Result: zero combos pass.** There are zero equity or ETF rows in the closed_picks feed at the strategy×symbol×direction grain.

### Can we recommend from the dashboard feed instead?

The dashboard aggregate says EQUITY WR=49.6% on n=347 closed (Wilson LB ≈ **44.4%** — under the 50% bar), and ETF WR=48.6% on n=70 (Wilson LB ≈ **37.1%** — well under). The headline "+218% total PnL" on equities is driven by average pnl_pct per trade ≈ 0.63%, after the ±500% cap in `compute_non_crypto_performance`. That is a positive-EV distribution but **not statistically past the Wilson-50% threshold this audit was asked to enforce**.

### Verdict for the user's belief

**Partially supported, with caveats.** On total realized PnL the dashboard shows equities/ETFs positive and crypto deeply negative. But:
- The two sides of that comparison come from *different source feeds* and *different time windows* (dashboard non-crypto is all-time resolved; `closed_picks.json` crypto is effectively 90d). Apples-to-oranges.
- Equity Wilson LB (~44%) is below the 50% gate, so "outperforming" is a PnL-tail statement, not a win-rate-edge statement.
- There are **no stock/ETF combos at n>=30 with Wilson LB > 50% in closed_picks.json**, so no combos can be named for a paper-trade plan under the specified gates. Naming any would be fabrication. Flagged: **not reproducible from closed_picks.json**.

If the user wants a defensible paper-trade plan, the next step is to consolidate the non-crypto closed feeds (the files listed in Task 2) into a single canonical closed-picks store, then rerun this audit against it. Until then, the honest answer is: equities LOOK better than crypto in aggregate, but the data plumbing does not support a strategy×symbol×direction recommendation.

### Risks flagged (for any future equity/ETF paper trade)

- US equities/ETFs do not trade 23/7; overnight gaps are not modeled by crypto-style TP/SL.
- Earnings windows can 10x realized vol on single-name equities — need earnings-blackout filter.
- ETF spreads widen in the first and last 15 min of the session; crypto-style market-on-signal entries will bleed via slippage.
- The ±500% PnL cap in `compute_non_crypto_performance` masks tail trades — inspect raw feed before sizing.

---

## Appendix — Reproduction

Analysis script: `tmp_cross_asset_audit.py` (repo root, temporary). Reads `alpha_engine/data/closed_picks.json` and `audit_dashboard/data/dashboard_data.json`, no network, stdlib-only. Every table above is printed by that script; no generators were run, no dashboard HTML was regenerated, no files under `audit_dashboard/` or `alpha_engine/data/` were modified.

Row counts cited: `len(picks) = 4391`, `len(closed) = 4391`, `len(closed90) = 4391`. Dashboard file inspected read-only.

**Not reproducible from closed_picks.json** (explicitly flagged): the EQUITY/ETF/FOREX/COMMODITY/BOND numbers in Task 2 and Task 6 — those are from the dashboard's separate non-crypto feed chain and cannot be recomputed from the alpha_engine closed store.
