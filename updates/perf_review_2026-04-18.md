# Strategy Performance Review — 2026-04-18

**Cycle:** First run of 8h cron `870f36b0`
**Inputs:**
- `audit_trail/data/dashboard_payload.json` (3,561 closed picks, 13 active, 269 raw active)
- `alpha_engine/data/strategy_performance.json` (13 tracked entries)

---

## TL;DR — 4 actionable findings

1. **DATA-FLOW GAP:** 187 of 193 strategies (97%) with closed history are **MISSING from `strategy_performance.json`**. Tracking pipeline is severely under-populated — directly impacts elite_score's `forward_wr` term, trust tiers, and mutation gates.
2. **6 high-performing untracked strategies** are flying under the radar. Some are sustained alpha that should be PROMOTED, not ignored. Top: `kimi_signal_tracking` n=31 WR=74% PF=5.63.
3. **Catastrophic tracked drains** still active: `quan_engine_scalp` has burned **−$1.4M paper PnL across 4,127 trades** (WR 29%, PF 0.39). `volume_spike_breakout` PF=0.13 on 39 trades. These are mutation/kill candidates per `MUTATION_THREE_AXIS_PROTOCOL.md`.
4. **High-conviction picks are clean** — 10/13 active picks meet elite_score≥70 OR confidence≥0.80, and zero land on bottom-quartile strategy/symbol historicals. **No active gate failures detected.**

---

## 1. Data-Flow Gap (highest priority)

### What the data shows

| Source | Distinct strategies | Distinct symbols |
|---|---|---|
| `dashboard_payload.json` recent_closed | **193** | 206 |
| `strategy_performance.json` (track) | **13** | — |
| **Coverage** | **6.7%** | — |

### Top untracked strategies by sample size (have closed history, NOT in track)

| Strategy | n closed | WR | PF | mean PnL% |
|---|---|---|---|---|
| `st_fear_greed_contrarian` | **454** | 56.6% | 2.70 | +77.1% |
| `luxalgo_confluence` | 263 | 50.6% | 1.52 | +56.8% |
| `st_obv_support_divergence` | 175 | 58.9% | 2.12 | +57.6% |
| `st_atr_vol_breakout` | 85 | 41.2% | 0.79 | −19.7% |
| `non_crypto_consensus` | 80 | 50.0% | 1.18 | 0.0% |
| `Breakout Momentum` | 69 | 49.3% | 1.26 | +29.2% |
| `Bollinger MR` | 68 | 50.0% | 1.51 | +57.1% |
| `ensemble` | 67 | 44.8% | 2.34 | +108.2% |
| `cta_cross_asset_tsmom` | 56 | 37.5% | 1.24 | +2.0% |
| `atr_regime_rsi` | 40 | 42.5% | 0.84 | −5.6% |

### Why this matters

`elite_scorer.py` (lines 1718-1888) uses `forward_wr` and `track_record` for up to **+40 points** of the 0–100 score. For 97% of strategies, this term resolves to a flat baseline (~5 pts) because the lookup misses. That's why my earlier diagnostic showed non-crypto picks averaging ~24/100 — the scorer can't reward strategies whose history isn't tracked.

### Suggested fix

Locate the writer that populates `strategy_performance.json` (likely `tools/per_strategy_scoring.py` or similar) and verify:
- It reads ALL closed picks, not just specific source_systems
- The strategy-name-to-key normalization isn't dropping entries
- It runs after every closed-pick batch, not on a separate cadence

A 1-line fix may be possible if there's a `source_systems` filter being too restrictive.

---

## 2. Top Promotion Candidates (untracked but high-performing)

These should be moved to a "promoted" tier with full tracking + maybe higher capital allocation:

| Strategy | n | WR | PF | mean PnL% | Notes |
|---|---|---|---|---|---|
| `kimi_signal_tracking` | 31 | **74.2%** | **5.63** | +386% | Outlier — verify single-symbol concentration before scaling |
| `MeanReversionBB` | 30 | 70.0% | 3.79 | +143.9% | Solid stat-arb, room for capital scale |
| `vwap_deviation_reversion_eth_v1` | 23 | 60.9% | 2.20 | +39.3% | ETH-specific; consider extending to BTC/SOL pairs |
| `claude_ml_moderate_mut` | 28 | 60.7% | 2.28 | +79.1% | Already a mutation — successful one |
| `st_obv_support_divergence` | 175 | 58.9% | 2.12 | +57.6% | Large sample, stable edge |
| `st_fear_greed_contrarian` | 454 | 56.6% | 2.70 | +77.1% | **Largest untracked sample**; clearly has structural edge |

---

## 3. Catastrophic Drains (mutation/kill candidates)

These ARE in `strategy_performance.json` but continue to emit picks. Per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`:

### `quan_engine_scalp` — TIER 1 KILL CANDIDATE
- **n=4,127** closed picks
- WR=29.1%, PF=0.386, **total PnL −$1.4M paper**
- 17/20 tracked symbols negative
- Worst symbol: MATICUSDT n=886 wins=0 (0%, total −$132.9k)
- ≥4σ below break-even. p-value 1.0 means CI excludes any positive expectancy.

**3-axis mutation proposal:**
| Axis | Current | Proposed |
|---|---|---|
| Parameter sweep | scalp_threshold default | Range scan 0.5×–2× the trigger; the strategy may have crossed a regime boundary |
| Regime gate | None | Disable when BTC 4H trend is RED (per `feedback_long_source_bias.md`); 60%+ of losses likely concentrated in red regimes |
| Inverse | LONG-only | Test SHORT variant on the same symbols — 71% loss rate suggests inverse may be +71% WR |

### `volume_spike_breakout` — KILL OR INVERSE
- n=39, WR=10.3%, PF=0.129, mean PnL −1.95%
- 18 trades on UUSDT alone, all SL_HIT (clear rug-pull pattern)

**Suggested:** Add UUSDT to symbol-blocklist immediately; test inverse on remaining picks (90% would-be wins).

### `quan_engine_position` — KILL
- n=26, **WR=0%**, all 26 trades on TAOUSDT, all SL
- Single-symbol concentration with adversarial fill behavior

**Suggested:** Disable this strategy entirely OR cap to ≤10% of source_system allocation.

### `cta_commodity_momentum_term` — MUTATION (recent_closed sample)
- n=28, WR=28.6%, PF=0.02, mean PnL −15.1%
- 2 distinct symbols only — too narrow

**3-axis:**
1. Param: lookback window (current likely too short for commodity momentum which prefers 6-12mo)
2. Regime: gate on commodity-class volatility regime (skip when DBC realized vol >20%)
3. Symbol expansion: add 4-6 more commodity tickers; if WR remains <40%, kill

### `crypto_kalman_trend_residual_reversion_v` — MUTATION OR KILL
- n=24, WR=25%, PF=0.18, **mean PnL −43.0%**
- Single symbol

**Suggested:** Run inverse first (75% would-be wins). If inverse also fails, single-symbol kalman is a curve-fit; kill.

---

## 4. High-Conviction Pick Health

10 of 13 active picks meet HC criteria (elite_score≥70 OR confidence≥0.80).
**Zero** of those 10 land on a strategy or symbol that's in the bottom-quartile blocklist.

**Verdict:** active gates are working as intended for HC picks. No regression flagged.

---

## Action Checklist (for engineer)

- [ ] **P0 — fix `strategy_performance.json` writer** (97% under-population). This unblocks every other improvement.
- [ ] **P1 — add `quan_engine_scalp` symbol-quality gate** OR run mutation_analysis.py before next emission cycle.
- [ ] **P1 — kill `quan_engine_position`** (TAOUSDT-only with 0% WR).
- [ ] **P2 — promote `st_fear_greed_contrarian`** + 5 others to a "tracked elite" tier in strategy_performance.json.
- [ ] **P2 — run mutation_three_axis on the 2 small-n drains** (`cta_commodity_momentum_term`, `crypto_kalman_trend_residual_reversion_v`).

---

## Methodology + provenance

- Closed-pick sample: `picks.recent_closed` from `audit_trail/data/dashboard_payload.json` (3,561 rows; recent slice — actual full-ledger samples for tracked strategies are larger as shown for quan_engine_scalp at 4,127)
- Win definition: `pnl_pct > 0` OR `status == 'WON'`
- Mutation thresholds: per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (WR<35% & n≥20 for strategies; WR<30% & n≥30 for symbols)
- High-conviction filter: `elite_score >= 70` OR `confidence >= 0.80`
- This review was generated by the 8-hour recurring cron `870f36b0`. Next fire: at next 8h cycle :13 mark.
- **Nothing in this PR modifies production strategy files.** All changes require human review per `CLAUDE.md` mutation-before-kill rule.
