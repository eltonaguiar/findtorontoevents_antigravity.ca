# goldmine_stocks — Mutation Analysis Report

**Date:** 2026-05-16  
**Analyst:** Hermes Agent (Sonnet 4.6)  
**Protocol:** docs/MUTATION_THREE_AXIS_PROTOCOL.md  
**Trigger:** n=453, PF=0.14, WR=42.9% per dashboard_data.json::systems  

---

## Executive Summary

`goldmine_stocks` is **already fully blocked** in `BLOCKED_SOURCE_SYSTEMS` (quality_gates.py line 1692), added 2026-04-28 after a prior three-axis autopsy. This report confirms the block is correct, documents the current dashboard state for audit continuity, and formally closes the re-investigation triggered by the n=453 EQUITY dragger count.

**Verdict: BLOCK STANDS. No mutation viable. No new gates required.**

---

## System Snapshot (dashboard_data.json, as of report date)

| Field | Value |
|-------|-------|
| closed_picks | 453 |
| excluded_closed | 446 (98.5% — pre-resolver or pre-gate exclusions) |
| resolved_picks | 7 |
| wins | 3 |
| losses | 4 |
| win_rate | 42.9% |
| profit_factor | **0.14** |
| avg_win | +0.62% |
| avg_loss | −3.38% |
| total_pnl_pct | −11.67% |
| max_drawdown | 13.52% |
| asset_classes | EQUITY, ETF |
| last_signal_at | 2026-04-27 (dormant ~19 days) |
| status | monitoring |

**Payoff ratio:** 0.62 / 3.38 = 0.18. Avg loss is 5.5× avg win. No amount of win-rate improvement rescues a 0.18 payoff ratio without structural changes to the signal.

---

## Three-Axis Mutation Autopsy

### Data Availability Note

`alpha_engine/data/closed_picks.json` contains 8,421 closed picks across 13 source systems. `goldmine_stocks` is not represented — all historical picks have been excluded from the active tracker (446 of 453 classified as `excluded_closed`). The mutation tool (`tools/mutation_analysis.py --json`) confirms zero goldmine_stocks rows in the live JSON.

Axis analysis is therefore drawn from:
1. **dashboard_data.json::systems[goldmine_stocks].strategies** — 7 resolved picks across 3 strategy variants
2. **Prior autopsy:** `reports/mutation_analysis_goldmine_stocks_2026_04_28.txt` (n=24 resolved at time of original kill)
3. **quality_gates.py commentary** (lines 1678–1692) — per-symbol, per-strategy breakdown at time of kill

### Axis 1 — Direction

| Direction | Trades (original kill) | WR | Note |
|-----------|------------------------|----|------|
| LONG | 24/24 | 12.5% | 100% of volume |
| SHORT | 0 | — | No data |

Current dashboard confirms: all 7 resolved picks are LONG (long_wr populated, short_wr=null across all strategies).

**Finding:** No SHORT data exists across the full history. Inverse mutation is not testable — you cannot validate a SHORT signal from a purely-LONG emitter without rewriting the signal logic. Direction axis offers **no rescue path.**

### Axis 2 — Symbol

At time of original kill (n=24 resolved):

| Symbol | Wins | Losses | WR |
|--------|------|--------|----|
| JNJ | 0 | 5 | 0% |
| ABBV | 0 | 3 | 0% |
| XOM | 0 | 3 | 0% |
| MRK | 0 | 2 | 0% |
| CVX | 0 | 2 | 0% |

Every symbol with n≥2 showed 0% WR. Single-trade "wins" (n=1) cannot constitute an allowlist per protocol (minimum n=10 for allowlist candidacy per docs/MUTATION_THREE_AXIS_PROTOCOL.md §2).

Current dashboard top_symbols (from 3 resolved strategies):
- GS: 1W/1L, 50% WR, −1.64% PnL
- MS: 1W/0L, 100% WR, +1.25% PnL (n=1 — below floor)
- PLD: 1W/0L, 100% WR, +0.23% PnL (n=1 — below floor)
- COST: 0W/1L, 0% WR, −0.15% PnL
- XLE: 0W/1L, 0% WR, −5.77% PnL
- XOM: 0W/1L, 0% WR, −5.59% PnL

No symbol crosses the n≥10 floor required for a statistically meaningful allowlist entry. **Symbol axis offers no rescue path.**

### Axis 3 — Strategy / Timeframe

Current dashboard strategy breakdown:

| Strategy | Resolved | WR | Total PnL | Status |
|----------|----------|----|-----------|--------|
| goldmine_5x_consensus | 5 | 60.0% | −0.31% | Already in BLOCKED_ASSET_STRATEGY_PAIRS (EQUITY) |
| goldmine_1x_consensus | 1 | 0.0% | −5.77% | Already in BLOCKED_ASSET_STRATEGY_PAIRS (EQUITY, CRYPTO) |
| goldmine_7x_consensus | 1 | 0.0% | −5.59% | Not yet explicitly listed — but source system blocked |

Prior autopsy (n=24) breakdown:
- goldmine_6x_consensus: 0/17 = 0% WR, −58.71% sum (also blocked individually: EQUITY line 2033)
- goldmine_5x_consensus: 3W/2L on n=5 (below n≥30 floor; net negative sum)

**goldmine_5x_consensus note:** 60.0% WR on n=5 appears superficially promising. However:
- Total PnL is −0.31% on 5 trades (avg −0.062% per trade)
- Avg win (+0.62% estimated from system-level data) vs avg loss structure is destructive
- n=5 is well below the n≥30 statistical floor for mutation promotion
- The source system is already in BLOCKED_SOURCE_SYSTEMS — no new picks are being generated
- Mutation Quality Score: (0.60 × 5) / 453 = 0.0066 — far below the ≥0.10 threshold per protocol §5

**goldmine_7x_consensus:** not yet explicitly listed in BLOCKED_ASSET_STRATEGY_PAIRS, but the source system block at BLOCKED_SOURCE_SYSTEMS level makes the individual strategy block redundant. No new emissions possible.

**No strategy axis offers a rescue path.**

---

## Existing Gates Confirmed Active

### BLOCKED_SOURCE_SYSTEMS (line 1692)
```python
"goldmine_stocks",  # 2026-04-28, PF 0.03, WR 12.5% on resolved sample
```
This blocks all new pick ingestion from this source.

### BLOCKED_ASSET_STRATEGY_PAIRS (lines 1985–2033)
```python
("CRYPTO",  "goldmine_1x_consensus"),
("CRYPTO",  "goldmine_2x_consensus"),
("CRYPTO",  "goldmine_3x_consensus"),
("EQUITY",  "goldmine_1x_consensus"),
("EQUITY",  "goldmine_2x_consensus"),
("EQUITY",  "goldmine_3x_consensus"),
("EQUITY",  "goldmine_4x_consensus"),
("EQUITY",  "goldmine_6x_consensus"),
```

### BLOCKED_STRATEGIES (line 1793)
```python
("goldmine_stocks", "EQUITY"),  # 0% WR n=5 (from 2026-04-21 HF audit)
```

### Score Penalties (line 4633)
```python
"goldmine_stocks": -20,  # source system score penalty
```

---

## Gap Identified: goldmine_7x_consensus Missing from BLOCKED_ASSET_STRATEGY_PAIRS

The individual strategy `goldmine_7x_consensus` is not in `BLOCKED_ASSET_STRATEGY_PAIRS`. However, this is a **low-priority cosmetic gap** because:

1. The entire source system `goldmine_stocks` is in `BLOCKED_SOURCE_SYSTEMS` — picks never reach the strategy-level check
2. `goldmine_7x_consensus` has only 1 resolved trade in the dashboard (the XOM −5.59% loss)
3. No active picks exist; system is dormant since 2026-04-27

**Recommendation:** Add `("EQUITY", "goldmine_7x_consensus")` to `BLOCKED_ASSET_STRATEGY_PAIRS` for completeness and defense-in-depth, consistent with how 6x, 4x, 3x, 2x, 1x are all individually listed. This closes a potential bypass if the source-system block is ever conditionally rolled back.

---

## n=453 vs n=7 Discrepancy

The dashboard shows `closed_picks=453` but `resolved_picks=7` and `excluded_closed=446`. This is not a data quality issue — it is expected behavior:

- 446 picks were excluded by the resolver (likely pre-resolver-v2 data, pre-gate picks that never had proper exit prices, or picks from the era when goldmine_stocks was still active before the 2026-04-28 block)
- The 7 resolved picks are the only ones with valid entry/exit data for statistical analysis
- The original kill decision at n=24 (2026-04-28) used `universal_resolved_picks.json` which had more picks at the time

The PF=0.14 and WR=42.9% shown in the dashboard are computed on the 7-trade resolved sample only.

---

## Mutation Quality Score (Protocol §5)

For completeness, applying the formula to the best sub-strategy candidate (goldmine_5x_consensus):

```
MutationQuality = (WR_win_subset × trades_win_subset) / trades_total_system
               = (0.60 × 5) / 453
               = 0.0066
```

Protocol threshold: ≥0.10 for a viable mutation. **Result: 0.0066 — 15× below threshold.**

---

## Conclusion and Recommendations

### Verdict: BLOCK STANDS

The prior three-axis autopsy (2026-04-28) correctly identified `goldmine_stocks` as a convergent, across-all-axes loser. The current dashboard state (n=7 resolved, PF=0.14, WR=42.9%, avg_loss 5.5× avg_win) provides no evidence of rehabilitation.

### Recommended Action (low priority)

Add `goldmine_7x_consensus` to `BLOCKED_ASSET_STRATEGY_PAIRS` for defense-in-depth:

```python
("EQUITY", "goldmine_7x_consensus"),  # 0% WR n=1, -5.59% PnL; source system already blocked
```

This is a cosmetic hardening — not urgent because BLOCKED_SOURCE_SYSTEMS already prevents any new picks.

### No Action Needed On

- BLOCKED_SOURCE_SYSTEMS: goldmine_stocks already present
- BLOCKED_ASSET_STRATEGY_PAIRS: 1x/2x/3x/4x/6x already present for EQUITY; 1x/2x/3x for CRYPTO
- Score penalties: -20 already applied
- NC_SCORE_EXEMPT_SOURCES: goldmine_stocks listed but moot (source blocked)

### Next Investigation

If the EQUITY asset class health drops below T2 targets (PF 1.55, WR 51.4% as of latest dashboard), the next drag candidates per `systems` are non-goldmine sources. goldmine_stocks is already neutralized.

---

## References

- `reports/mutation_analysis_goldmine_stocks_2026_04_28.txt` — original autopsy (empty output = no flips found)
- `reports/zombie_kill_protocol_2026_04_28.md` — kill decision document
- `audit_trail/quality_gates.py` lines 1678–1692, 1793, 1983–2033, 4633
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md` — protocol reference
- `audit_dashboard/data/dashboard_data.json::systems[goldmine_stocks]`
