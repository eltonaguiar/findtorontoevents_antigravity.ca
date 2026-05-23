# EQUITY Pick Generation Bottleneck — Swarm Validation Request

## Context

The `findtorontoevents.ca/audit` dashboard shows EQUITY at n=5 resolved picks with
WR=20%, PF=0.253 (insufficient_data tier). This is NOT a signal quality problem — the
circuit_breaker reads 55.1% WR on n=89 picks from the closed ledger.

**Autopsy report:** `reports/equity_pick_generation_autopsy_2026_05_19.md`

## Root cause identified

**Primary:** `("EQUITY", "stocks_rsi2_pullback")` is in `BLOCKED_ASSET_STRATEGY_PAIRS`
in `audit_trail/quality_gates.py` (line 2707). This causes `_is_historical_blocked_pick()`
to exclude 54 of 68 EQUITY closed picks from the dashboard aggregate, leaving n=5.

**The block was added 2026-05-16 citing:** n=37, WR=38%, PF=0.97 (below 45% WR floor)

**Current MySQL data (2026-05-19):** n=73, WON=37, LOST=36, WR=50.7%
- WR has crossed the 45% charter floor
- The strategy is still actively emitting: 90 new picks on 2026-05-19 alone
- 1,157 OPEN picks (39–53 days old) are sitting unresolved in trading_picks

**Secondary:** Consensus pipeline has produced 0 EQUITY picks since May 13 (top rejection
reason: `no_consensus`). The aggregator runs are completing but no EQUITY consensus forms
because the dominant strategy (stocks_rsi2_pullback) is in the allowlist block and the
regime_* strategies (27+18+13=58 picks/week) are not in the EQUITY allowlist.

## Proposed Fix A: Lift the stocks_rsi2_pullback EQUITY historical block

**File:** `audit_trail/quality_gates.py`  
**Line:** 2707 — delete or comment out `("EQUITY", "stocks_rsi2_pullback")`

**Arguments FOR:**
1. WR=50.7% (n=73) now exceeds the 45% charter floor used to impose the block
2. Removing it immediately restores EQUITY n from 5 → 59 (thin_sample tier)
3. The strategy continues to be scored — it is ALREADY in the `smart_picks_engine.py`
   EQUITY allowlist (line 449) — the historical block is the only thing removing
   resolved picks from the dashboard aggregate
4. The block rationale (n=37, WR=38%) used data that was at the 30-pick kill threshold
   minimum; more data has arrived since then showing improvement

**Arguments AGAINST:**
1. WON=37 picks may all be from BEFORE the block was imposed; post-block WR unknown
2. At n=3 post-block resolved picks, the mutation protocol requires n≥30 before unblock
3. The -15 EQUITY confidence inversion penalty and the score gate (min_score=50) should
   handle quality filtering even if the historical block is lifted

**Question 1:** Should we lift the EQUITY historical block for stocks_rsi2_pullback now,
or add it to PENDING_UNBLOCK_REVIEW with a 2026-06-06 review date?

## Proposed Fix B: Add regime_* strategies to EQUITY allowlist

**File:** `alpha_engine/smart_picks_engine.py` lines 443–465  
**Change:** Add to EQUITY `allowlist`:
- `"regime_accumulation"` (143 raw picks/month, 5 stale)
- `"regime_mild_bull"` (112 raw picks/month)
- `"regime_strong_bull"` (53 raw picks/month)
- `"regime_mild_bear"` (51 raw picks/month)
- `"regime_strong_bear"` (48 raw picks/month)

Total additional volume: ~407 raw EQUITY picks/month entering scoring pipeline.

**Arguments FOR:**
1. These strategies exist and are emitting signals — currently 0% reach the score gate
2. Adding more source coverage increases consensus probability (multi-source agreement)
3. Regime-based strategies are intuitive (accumulation phase = buy signal)
4. No edge data exists (good or bad) because they've never been admitted

**Arguments AGAINST:**
1. Regime strategies may have built-in look-ahead bias in their labeling
2. Without historical validation, admitting them could flood the dashboard with
   low-quality picks that drag WR down before we have enough data to assess them
3. The EQUITY equity_allowlist was deliberately tight for quality control; widening it
   increases type-I error risk

**Question 2:** Should regime_* strategies enter as shadow mode (forward_test_only=True)
or full admission to the EQUITY scoring pipeline?

## Expected impact summary

| Scenario | EQUITY n | Status |
|---|---|---|
| Current | 5 | insufficient_data |
| Fix A only (lift block) | 59 | thin_sample |
| Fix A + B (both) | 75–90/month | thin_sample → candidate |
| Fix A + B + resolver (Fix C) | 500+ | candidate → stable |

## Verdict requested

For each proposed fix, please answer:
1. **APPROVE** (implement now) / **REJECT** (do not implement) / **DEFER** (implement after more data)
2. One-sentence rationale
3. Any modification to the proposed approach

Context: EQUITY WR=55.1% on the circuit_breaker's n=89 sample suggests genuine edge
exists; the bottleneck is infrastructure (blocked historical picks, missing allowlist
entries), not signal quality.
