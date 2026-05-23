# perf-review: 8h cycle 2026-04-21 (cycle 8)

**Author:** Claude Opus 4.7 (1M context)
**Generated:** 2026-04-21 04:13 UTC
**Source:** `audit_trail/data/dashboard_payload.json` (3500 closed, 50 active picks)
**Tracking:** `alpha_engine/data/strategy_performance.json` (184 keys)
**Cycle:** 8 of recurring 8-hour perf-review series
**Related:** PR #272 (cycle 4), #277 (cycle 5), #278 (cycle 6), #282 (cycle 7)

---

## TL;DR

Cycle 8 surfaces **3 actionable issues**, all of which are **regressions / persistent leaks** from prior cycles:

1. **Zombie strategies still emit closed picks despite blocklist retirement.** `copy_hl_lb_None` (n=278, WR 32.0%, **cum −806% PnL**) and `st_fear_greed_contrarian` (n=621, WR 23.8%, **cum −365% PnL**) and `st_obv_support_divergence` (n=90, WR 28.9%, **cum −75% PnL**) are all in `_RETIRED_STRATEGIES` (`alpha_engine/strategy_blocklist.py:27-42`) yet account for **−1247% cum PnL across the closed-trade dataset**. Retirement gate is leaking somewhere.
2. **High-conviction picks still placed on bottom-quartile symbols.** 2 of 26 active HC picks are on symbols with WR ≤ 22.1% on n ≥ 68. Both are "super signal (super)" composites at confidence 0.99: AVAXUSDT (WR 14.7%) and DOGEUSDT (WR 22.1%). PR #294's confidence dead-zone gate (0.65 ≤ conf < 0.75) does not catch these because they're at conf 0.99.
3. **Strategy-name tracking gap remains huge.** 167 of 192 closed strategies are not in `strategy_performance.json` (87% silent failure). PR #289's diagnostic still applies — naming domains are disjoint between dashboard display names and tracking IDs. Already documented.

Combined drag from mutation candidates: **−1298% cum PnL** across 12 strategies (n ≥ 20, WR < 35%).
Combined drag from symbol blocklist candidates: **−534% cum PnL** across 23 symbols (n ≥ 30, WR < 30%).

---

## §1 — Per-strategy mutation candidates (n ≥ 20, WR < 35%)

12 strategies meet the mutation-candidate threshold. **Bold** entries are net-negative cum-PnL contributors that warrant immediate kill-or-mutate.

| Strategy | n closed | WR | PF | mean PnL% | cum PnL% | Status |
|---|---|---|---|---|---|---|
| **`copy_hl_lb_None`** | 278 | 32.0% | 0.56 | −2.901% | **−806.39%** | ZOMBIE — already in `_RETIRED_STRATEGIES`, still emitting |
| **`st_fear_greed_contrarian`** | 621 | 23.8% | 0.36 | −0.587% | **−364.51%** | ZOMBIE — same |
| **`st_obv_support_divergence`** | 90 | 28.9% | 0.23 | −0.836% | **−75.20%** | ZOMBIE — same |
| **`kimi_signal_tracking`** | 29 | 34.5% | 0.56 | −2.190% | **−63.52%** | needs investigation |
| **`st_atr_vol_breakout`** | 27 | 22.2% | 0.27 | −0.798% | **−21.55%** | mutate or kill |
| **`atr_regime_rsi`** | 29 | 17.2% | 0.26 | −0.358% | **−10.38%** | mutate (regime-gate sweep) |
| **`ensemble`** | 24 | 16.7% | 0.64 | −0.376% | **−9.02%** | unbranded — likely dispatcher mislabel |
| **`cta_commodity_momentum_term`** | 43 | 9.3% | 0.01 | −0.100% | **−4.30%** | mutate (commodity regime gate) |
| `non_crypto_consensus` | 87 | 0.0% | 0.0 | 0.0% | +0.01% | **broken** — flat closes, see §6 |
| `cta_cross_asset_tsmom` | 57 | 12.3% | 1.23 | +0.019% | +1.07% | low WR but positive — TP:SL skew working |
| `futures_momentum` | 436 | 24.5% | 1.38 | +0.048% | +20.83% | low WR but positive — TP:SL skew |
| `forex_rsi2_mean_reversion` | 522 | 28.4% | 3.71 | +0.066% | +34.56% | low WR but positive — TP:SL skew (PF 3.71!) |

**Observation:** The 4 net-positive entries at low WR (PF ≥ 1.23) confirm that **WR-only filtering is misleading on TP-skewed strategies**. The mutation-candidate definition (n ≥ 20, WR < 35%) over-includes legitimate TP:SL-leveraged strategies. Recommend the gate logic also check `cum_pnl < 0` AND `pf < 1.0` before flagging for mutation.

## §2 — Per-symbol block candidates (n ≥ 30, WR < 30%)

23 symbols meet the block threshold. Concentration: **9 crypto USDT, 10 forex (=X), 4 futures (=F)**. Aggregate cum drag: **−534% PnL**.

Top 15 worst:

| Symbol | Class | n closed | WR | mean PnL% | cum PnL% |
|---|---|---|---|---|---|
| `EURJPY=X` | FOREX | 42 | 7.1% | −0.327% | −13.72% |
| `AVAXUSDT` | CRYPTO | 68 | **14.7%** | −0.816% | **−55.49%** |
| `HG=F` | FUTURES | 118 | 15.3% | +0.056% | +6.64% (positive despite low WR) |
| `OPUSDT` | CRYPTO | 64 | 15.6% | −2.013% | **−128.82%** ⚠️ worst by abs cum |
| `USDJPY=X` | FOREX | 71 | 18.3% | +0.338% | +24.03% |
| `LINKUSDT` | CRYPTO | 54 | 18.5% | −0.678% | −36.64% |
| `EURUSD=X` | FOREX | 70 | 18.6% | −0.151% | −10.57% |
| `SUIUSDT` | CRYPTO | 80 | 18.8% | −1.151% | **−92.09%** |
| `AUDJPY=X` | FOREX | 78 | 19.2% | −0.021% | −1.65% |
| `DOGEUSDT` | CRYPTO | 68 | 22.1% | −0.750% | −51.03% |
| `SI=F` | FUTURES | 174 | 22.4% | −0.028% | −4.79% |
| `PL=F` | FUTURES | 115 | 22.6% | +0.046% | +5.24% |
| `ADAUSDT` | CRYPTO | 62 | 22.6% | −0.615% | −38.15% |
| `APTUSDT` | CRYPTO | 66 | 22.7% | **−1.251%** | **−82.58%** |
| `GBPJPY=X` | FOREX | 77 | 23.4% | +0.083% | +6.41% |

**Observation:** Same TP:SL-skew confound on per-symbol — `HG=F`, `USDJPY=X`, `PL=F`, `GBPJPY=X` are net-positive cum despite WR < 25%. Symbol blocklist should use `cum_pnl < 0 AND mean_pnl < −0.20%` filter, not raw WR.

**True symbol kill list (cum PnL < −30%):** `OPUSDT (−128.82%)`, `SUIUSDT (−92.09%)`, `APTUSDT (−82.58%)`, `AVAXUSDT (−55.49%)`, `DOGEUSDT (−51.03%)`, `LINKUSDT (−36.64%)`, `ADAUSDT (−38.15%)`. **All 7 are crypto altcoins.**

## §3 — High-conviction cross-reference (elite_score ≥ 70 OR confidence ≥ 0.80)

26 active picks meet the high-conviction threshold. **2 are flagged as placed on bottom-quartile symbols:**

| Symbol | Strategy | elite_score | confidence | Flag |
|---|---|---|---|---|
| `AVAXUSDT` | `super signal (super) via claude_gainer_st` | 52 | **0.99** | sym-block-cand WR=14.7% n=68 |
| `DOGEUSDT` | `super signal (super) via rapid_fire` | 52 | **0.99** | sym-block-cand WR=22.1% n=68 |

**Pattern:** Both flagged HC picks are `super signal (super)` composites with conf=0.99 but elite_score=52 (well below the standard 70 floor). This is the **same low-elite/high-confidence bypass pattern** that PR #285 / #284 / #287 attempted to close. The confidence dead-zone gate (PR #294, 0.65 ≤ conf < 0.75) does not cover the conf ≥ 0.95 band where these live.

**Recommended additional gate (proposal):** `if asset_class == CRYPTO and confidence >= 0.95 and elite_score < 70 and symbol_historical_wr < 0.30: reject`. This closes the super-signal high-conf / low-elite bypass for known-bad symbols while leaving high-elite high-conf picks untouched.

## §4 — Data-flow gap (closed picks vs strategy_performance.json)

| Metric | Count |
|---|---|
| Closed strategies in `recent_closed` | 192 |
| Tracked strategies in `strategy_performance.json` | 184 |
| **Closed strategies missing from tracking** | **167 (87%)** |
| Tracked strategies that never close picks | 159 |

**Sample missing-from-tracking** (closed but no tracking row):
- Display-named: `Bollinger MR`, `Breakout Momentum`, `Classic Momentum`, `Extreme Fear Contrarian Buy`, `MeanReversionBB`, `Multi-Timeframe Trend Alignment`, `Quality Compounders`, `VWAP Deviation Scalp`, `Whale Accumulation Proxy`
- Snake-cased: `adaptive_vr_confluence`, `adx-trend-scout`, `aroon-trend-scout`, `atr_percentile_gate`, `atr_regime_rsi`, `autocorrelation_exploiter`, `battleground_rsi_no_regime_mut`, `bb_mean_reversion_forex`, `betting-against-beta`, `breakout_c_spike`

**Sample sp-only orphans** (tracked, never close picks): predominantly `ml_enhanced_<SYMBOL>_<TF>_<TIER>_<MODEL>` per-symbol ML model snapshots that the dashboard never aggregates back into a single strategy display name.

**Diagnosis:** Tracking file is built around per-symbol ML model snapshots, dashboard groups by strategy family — there's no aliasing layer that joins them. `STRATEGY_TRACK_ALIASES` in `alpha_engine/config.py:1817` only has 8 entries (vs 192 dashboard strategies). Already documented in **PR #289**; this cycle confirms the leak is unchanged.

## §5 — DNA mutation suggestions (per docs/MUTATION_THREE_AXIS_PROTOCOL.md)

The full per-candidate proposal block is in the companion file `mutations/proposed_2026-04-21.yaml`. Summary:

| Strategy | Sweep axes | Regime axes | Inverse |
|---|---|---|---|
| `copy_hl_lb_None` | already retired — see §6 | — | — |
| `st_fear_greed_contrarian` | already retired — see §6 | — | — |
| `st_obv_support_divergence` | already retired — see §6 | — | — |
| `atr_regime_rsi` | RSI len 14→{7,21,28}; OS/OB 30/70→{20/80, 25/75}; SMA→EMA | BTC 4h trend filter; ATR%-percentile gate | invert direction |
| `st_atr_vol_breakout` | breakout mult; ATR len; entry threshold | session filter (drop 8-11, 16-21 UTC) | invert |
| `cta_commodity_momentum_term` | term-structure window; rebal freq | commodity regime gate (contango/backwardation); softs vs metals filter | invert |
| `kimi_signal_tracking` | min sub-signal threshold; weighting; expiry horizon | asset-class scoping; ToD filter | invert |
| `non_crypto_consensus` | **broken (flat-close bug)** — see §6 | — | — |

**Mutation skeleton applied per protocol:** sweep (3-5 param variants), regime gate (1-2 contextual filters), inverse (1 directional flip). Each mutation gets a paper-only run for 7 days before promotion to baby strategies.

## §6 — Action items

### P0 — Plug the zombie leak (highest cum drag)

`copy_hl_lb_None` + `st_fear_greed_contrarian` + `st_obv_support_divergence` are in `alpha_engine/strategy_blocklist.py:27-42::_RETIRED_STRATEGIES` but still emitting closed picks (combined n=989, cum drag −1245%). Plug:

- Find every code path that opens a pick. Confirm it imports `is_strategy_blocked()` AND short-circuits emission when True.
- Audit cron-driven emitters separately — they may bypass the in-process gate.
- Audit forward-validator and backfill scripts — they may re-tag old picks under different (still-emitting) strategy names.
- Ship a CI test: `tests/test_blocklist_no_emission.py` that fails the build if any retired strategy appears in `recent_closed` opened after retirement date.

### P1 — Investigate `non_crypto_consensus` flat-close bug

n=87 with WR=0%, mean PnL exactly 0%, cum PnL +0.01%. Every closed pick had pnl_pct = 0.0. This is not a strategy that loses — it's a strategy that closes flat (FORCE_CLOSED at entry price, no SL/TP triggered, no resolution). Likely a resolver bug or a strategy that emits picks with no actionable TP/SL. Trace to source.

### P2 — Tighten conf-0.99 super-signal gate

Add the proposed `confidence ≥ 0.95 + elite_score < 70 + symbol_historical_wr < 0.30 → reject` filter to `audit_trail/quality_gates.py::passes_active_gate`, scoped to CRYPTO. Rejects the AVAXUSDT and DOGEUSDT picks flagged in §3.

### P3 — Symbol-level cum-PnL kill list

Add 7 crypto altcoins to a soft block (allow only one active per symbol at any time, require elite_score ≥ 75, conf ≥ 0.85): `OPUSDT, SUIUSDT, APTUSDT, AVAXUSDT, DOGEUSDT, LINKUSDT, ADAUSDT`. Combined cum drag −485%.

### P4 — Continue PR #289 alias backfill

87% of closed strategies have no tracking row. Until `STRATEGY_TRACK_ALIASES` is expanded (proposal: auto-generate from observed strategy names → canonical tracking IDs in a nightly job), the entire `strat_fwd_wr` HC-filter chain is fail-open for 167 strategies. PR #289 documents the path forward.

### P5 — Refine mutation-candidate gate

Current gate (n ≥ 20, WR < 35%) over-includes `forex_rsi2_mean_reversion` (PF 3.71, +34.56% cum) and `futures_momentum` (PF 1.38, +20.83% cum). Add `cum_pnl < 0 AND pf < 1.0` to the criteria so TP:SL-skewed positive strategies aren't flagged.

## §7 — Reproduce

```bash
python /tmp/cycle8/analyze.py
# or with the in-repo path
python -c "exec(open('.planning/cycle8/analyze.py').read())"  # if checked in
```

Inputs:
- `audit_trail/data/dashboard_payload.json` (snapshot at cycle-8 fire time)
- `alpha_engine/data/strategy_performance.json`

Output: `.planning/cycle8/results.json` (machine-readable findings) and this report.

## §8 — Cycle 7 → Cycle 8 delta

| Metric | Cycle 7 (PR #282) | Cycle 8 | Δ |
|---|---|---|---|
| Mutation candidates (n≥20, WR<35) | not directly comparable | 12 | — |
| `copy_hl_lb_None` cum PnL | flagged in cycles 3-7 | −806% | unchanged |
| `non_crypto_consensus` n=87 WR=0% | flagged in cycle 7 | n=87 WR=0% | unchanged |
| Naming-mismatch silent failure rate | 87% (PR #289) | 87% | unchanged |
| HC picks flagged on bottom-quartile sym | 3 (cycle 7) | 2 | −1 |

**Net assessment:** Cycle 8 confirms cycles 3-7 leaks are still live. The recently-merged calibration PRs (#284, #285, #287, #294, Kimi #292) tightened the active gate but did not address the closed-trade emission leak from retired strategies, which is the single largest remaining drag.

**Nothing in this PR modifies production files.**
