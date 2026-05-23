# Empty Asset Class Root Cause — 2026-04-22

**Status.** Dashboard shows 11 active picks: 6 CRYPTO / 3 FOREX / 2 COMMODITY / **0 EQUITY / 0 ETF / 0 BOND**.
Upstream emission across 35 `active_picks*.json` files (472 rows): 331 CRYPTO / 72 FOREX / 36 EQUITY / 26 COMMODITY / **0 ETF / 0 BOND**.

## Per-class root cause

### EQUITY — gate-too-strict (supply present, filtered downstream)
- **Emitters.** `multi_asset_copytrader`, `ml_gatekeeper`, `alpha_engine/smart_picks_engine.py` all produce EQUITY candidates (36 upstream rows).
- **Kill gate.** `audit_trail/quality_gates.py:211` — `SMART_PICKS_MIN_SCORE_EQUITY = 70` (RAISED 50→70 on 2026-04-21). Config comment at `alpha_engine/config.py:212` acknowledges EQUITY median closed-pick elite_score is **36** and pct ≥ 70 is **0.0%** → the 70 floor mathematically kills 100% of EQUITY picks.
- **Irony.** The newer per-class dict `MIN_ELITE_SCORE_BY_CLASS` (`alpha_engine/config.py:219`) correctly sets EQUITY=50, but the legacy `SMART_PICKS_MIN_SCORE_EQUITY=70` in `quality_gates.py` is the gate actually enforced at `quality_gates.py:4159`.
- **Classification.** **Gate-too-strict.** Mercury 2's recommendation is correct.

### ETF — emitter-missing (zero supply)
- **Strategy file exists.** `alpha_engine/etf_strategies.py` defines `ETF_STRATEGIES = {etf_dual_momentum, etf_sector_momentum, etf_risk_parity_rotation, etf_trend_following}`.
- **Wire-up exists in scanner.** `alpha_engine/scanner.py:242` imports `ETF_STRATEGIES`; `scanner.py:1988` registers them when `strategy_filter in ("all", "etf")`.
- **But** no live workflow runs the scanner with the ETF slice enabled to write picks tagged `asset_class=ETF`. The ETF watchlist (`config.py:634 ETF_SYMBOLS`) is large (~25 symbols) and clean, but nothing is *emitting* picks tagged ETF. `EQUITY_SYMBOLS` double-lists SPY/QQQ as `cat="stock"` — so even when those symbols trade, picks are tagged EQUITY, not ETF.
- **Classification.** **Emitter-missing.** Need a scanner entrypoint that runs `etf_strategies` against `ETF_SYMBOLS` and tags `asset_class="ETF"` before handoff to quality gates.

### BOND — emitter-missing (zero supply)
- **Strategy file exists.** `alpha_engine/bond_strategies.py` → `BOND_STRATEGIES = {bond_yield_momentum, bond_duration_rotation, bond_mean_reversion}`.
- **Data pipe exists.** `alpha_engine/bond_data_fred.py::fetch_bond_bundle` is already integrated.
- **Wire-up in scanner.** `scanner.py:243` imports `BOND_STRATEGIES`; `scanner.py:1991` registers them when `strategy_filter in ("all", "bond")`.
- **But** no scheduled job invokes the scanner with the bond slice → 0 upstream emission. `TLT/HYG` moved to `BOND_SYMBOLS` but no strategy writes `asset_class="BOND"` picks to any active_picks*.json.
- **Classification.** **Emitter-missing.** Same shape as ETF — registration is wired, invocation is not.

## Score × PnL quadrant analysis (n=3,500 recent_closed)

| class | hi_score_lo_PnL (FP) | lo_score_hi_PnL (FN) | top FN strategies |
|-------|---|---|---|
| CRYPTO | 25 | **287** | st_fear_greed_contrarian (58), luxalgo_confluence (52), ml consensus (39) |
| FOREX  | **43** | 9 | *(all 43 FPs from a single strategy: `non_crypto_consensus`)* |
| EQUITY | 7 | **68** | Classic Momentum (10), vol-contraction-scout (7), Bollinger MR (7) |
| COMMODITY | 0 | 8 | futures_momentum (6) |
| ETF | 0 | **17** | intermarket-flow-scout (6), quality-minus-junk (3) |
| BOND | 0 | 1 | futures_momentum (1) |

**Read.** The scoring model systematically *under-scores* winning picks in EQUITY / ETF / CRYPTO contrarian setups. EQUITY has 68 low-score closed winners (avg +6.2% PnL) — raising, not lowering, the EQUITY floor was precisely backwards. FOREX has a single-strategy false-positive concentration (`non_crypto_consensus` produces 43 high-score losers); this is a strategy-level problem, not a floor problem.

## Filter-edge exploration

RSI / volume_ratio are **not populated** in `recent_closed` rows (missing fields across all classes) — those filter tests returned empty sets and are inconclusive without backfilling indicators on closed picks.

**RR-ratio edge (rr ≥ 1.5) did show:**

| class | base WR | fWR | base PF | fPF | n_base | n_filt |
|---|---|---|---|---|---|---|
| CRYPTO | 37.6% | 36.4% | 0.88 | 0.89 | 1650 | 1543 |
| EQUITY | 53.0% | 52.5% | 1.44 | 1.56 | 355 | 305 |
| ETF | 51.9% | 52.1% | 1.10 | 1.18 | 77 | 71 |
| FOREX | 49.7% | 50.7% | 0.97 | 0.84 | 809 | 69 |
| COMMODITY | 42.6% | 28.6% | 1.09 | 1.55 | 589 | 7 |

Edge from `rr_ratio ≥ 1.5` is **mild (+0.1 PF for EQUITY/ETF)** and FOREX actually gets worse. Not strong enough to rewrite gates.

## Fix proposal

1. **EQUITY — gate tweak (out of scope for this PR; Mercury 2 flagged risk).**
   File:line to change: `audit_trail/quality_gates.py:211–213`, lower `SMART_PICKS_MIN_SCORE_EQUITY` from 70 → 50 (match `alpha_engine/config.py:221`). **Deferred to a review-gated PR.**
2. **ETF — emitter spike (THIS PR).** Proof-of-concept `tools/etf_emitter_spike.py` that calls `etf_strategies.ETF_STRATEGIES` against `ETF_SYMBOLS` and writes a *draft* `alpha_engine/data/active_picks_etf_draft.json`. **Not wired to dashboard ingest.** Proposed prod path: new GitHub Actions workflow `.github/workflows/alpha-engine-etf.yml` invoking `scanner.py --strategy-filter=etf` daily.
3. **BOND — emitter spike (THIS PR).** Same shape. `tools/bond_emitter_spike.py` uses `bond_data_fred.fetch_bond_bundle` → `bond_strategies.BOND_STRATEGIES` → `active_picks_bond_draft.json`. Prod path: `.github/workflows/alpha-engine-bond.yml` on daily cadence (bonds don't need intraday).

## What this PR does

- Adds the two emitter spike scripts (draft-only, never ingested).
- Adds this diagnosis doc.
- Does **not** modify `config.py`, `quality_gates.py`, or `feed_hygiene.py`.
- Does **not** expand `BLOCKED_SOURCE_SYSTEMS` or any strategy demotion.

Follow-up PR will lower `SMART_PICKS_MIN_SCORE_EQUITY` (bounded, reversible, 1-line change) after Mercury 2 review sign-off.
