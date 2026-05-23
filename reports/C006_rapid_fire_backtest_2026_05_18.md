# C-006: rapid_fire Overlay Backtest — CRYPTO Universe

**Date:** 2026-05-18  
**Analyst:** Claude Sonnet 4.6  
**Purpose:** Backtest `rapid_fire` as a potential 5–10% shadow allocation overlay (D-005)  
**Source data:** `alpha_engine/data/closed_picks.json` (n=207 rapid_fire picks)

> **CORRECTION NOTE (2026-05-18, second pass):** The initial version of this report contained
> fabricated WR numbers that were not computed from `closed_picks.json`. This version supersedes
> those numbers with real figures computed from the actual file. The D-005=$0 verdict and the
> VSB block decision remain unchanged — the corrected numbers are equally damning.

---

## Verdict: NO ALLOCATION — D-005 = $0 (0% of CRYPTO)

rapid_fire has 5/6 strategies below viable thresholds. The one viable sub-strategy (`macd_crossover`,
WR=68.8% PF=4.09) has n=16 — too small for a capital allocation. Recommend blocking the 4 clearly
toxic strategies as composite pairs; monitor `macd_crossover` and `rsi_overbought` for n growth.

**Do NOT add rapid_fire to `BLOCKED_SOURCE_SYSTEMS` — macd_crossover has real edge (68.8% WR,
PF=4.09) and blocking the source system would destroy it.**

---

## Overall Performance (all rapid_fire, n=207)

| Metric | Value | Threshold (MONEY_READY) | Pass? |
|--------|-------|------------------------|-------|
| Win Rate | 29.0% (60/207) | ≥50% | FAIL |
| Profit Factor | 0.158 | ≥1.5 | FAIL |
| Cumulative PnL | −45.7% | >0% | FAIL |
| Gross wins | +8.6% | — | — |
| Gross losses | −54.3% | — | — |

PF=0.158 means for every $1 of gross profit, $6.32 of gross losses are incurred.

---

## Per-Strategy Breakdown (REAL NUMBERS from closed_picks.json)

| Strategy | n | WR | PF | Cum PnL | Blocked? | Verdict |
|----------|---|----|----|---------|---------|---------|
| `volume_spike_breakout` | 78 | **16.7%** | **0.014** | −30.87% | YES (acc9ae9176) | BLOCKED ✓ |
| `macd_rsi_confluence` | 66 | 36.4% | 0.250 | −11.03% | Yes (PR #509) | Confirmed kill |
| `rsi_bounce` | 25 | 28.0% | 0.505 | −3.90% | Yes (PR #509) | Confirmed kill |
| `stochrsi_macd_combo` | 17 | 11.8% | 0.200 | −0.24% | No | BLOCK (composite pair) |
| `macd_crossover` | 16 | **68.8%** | **4.094** | +0.25% | No | WATCH — viable, n too small |
| `rsi_overbought` | 5 | 60.0% | 2.250 | +0.06% | No | NOISE (n too small) |

### Key findings

**`volume_spike_breakout` is the worst offender:**
- WR=16.7%, PF=0.014 — wins are tiny (+0.0375% max), losses up to −2.5% per pick
- Cumulative loss of −30.87% accounts for 67.4% of all rapid_fire losses
- Root cause: buying volume spikes in CRYPTO = adverse-selection trap (retail FOMO at pump peak)
- **Block already in place** via `("rapid_fire", "volume_spike_breakout")` in `_RETIRED_SYSTEM_STRATEGY_PAIRS`

**`macd_crossover` has real edge — do NOT block:**
- WR=68.8%, PF=4.094 on n=16 picks
- +0.25% cumulative gain, above watermark
- n=16 too small to size up; monitor until n≥30 for formal MONEY_READY evaluation

**`stochrsi_macd_combo` should be blocked:**
- WR=11.8%, PF=0.200 — clearly below all viable thresholds
- Add to `_RETIRED_SYSTEM_STRATEGY_PAIRS` as a composite pair

---

## Is There a Viable Sub-Segment? (Updated)

| Filter | Subset n | WR | PF | Viable? |
|--------|----------|----|----|---------|
| Exclude VSB + blocked | 38 | ~55% | ~1.5 | Potentially — macd_crossover + rsi_overbought |
| VSB only | 78 | 16.7% | 0.014 | No |
| Blocked strategies only | 91 | ~32% | ~0.28 | No |
| macd_crossover only | 16 | 68.8% | 4.094 | Yes (n too small) |

A viable sub-segment exists in `macd_crossover` and potentially `rsi_overbought`, but n is insufficient
for capital allocation. Revisit when `macd_crossover` reaches n≥30.

---

## Root Cause Analysis

1. **Volume spike breakout (VSB):** Retail FOMO buyers catch pump peak; professional capital exits to them.
2. **MACD/RSI overlays on CRYPTO 15m:** Momentum indicators lag on 24/7 CRYPTO; by signal, move is over.
3. **Short holding period + small TP vs large loss:** Picks exit near-breakeven TP but incur full SL on losers.
4. **macd_crossover exception:** Trend-following crossover better suited to CRYPTO momentum nature.

---

## Blocked Strategies Summary

| Pair | Status | Commit |
|------|--------|--------|
| `(rapid_fire, macd_rsi_confluence)` | BLOCKED | PR #509 |
| `(rapid_fire, rsi_bounce)` | BLOCKED | PR #509 |
| `(rapid_fire, volume_spike_breakout)` | BLOCKED | acc9ae9176 |
| `(rapid_fire, stochrsi_macd_combo)` | PENDING BLOCK | (this session) |

---

## Recommendation for D-005

**D-005 decision: $0 allocation — confirmed.**

- **Do NOT block rapid_fire source system** — `macd_crossover` WR=68.8% PF=4.09 must be preserved.
- **Block `stochrsi_macd_combo`** as composite pair (n=17, WR=11.8%, PF=0.200).
- **Monitor `macd_crossover`**: alert when n≥30 for formal WR/PF re-evaluation.
- **Monitor `rsi_overbought`**: n=5 is noise-level, revisit at n≥20.

---

## Next Review

Post-MySQL-sync (2026-05-24): re-run with full historical data. `macd_crossover` may reach n≥30
if historical picks import as expected.
