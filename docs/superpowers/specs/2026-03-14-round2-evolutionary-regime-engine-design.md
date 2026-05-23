# Round 2: Evolutionary Regime Engine — Design Spec

**Date:** 2026-03-14
**Status:** Approved (user approved Approach C and delegated implementation)
**Scope:** All trading systems — fc_crypto_pro, conviction_picks, blueprint_generator, claude_pick_generator

## Problem Statement

Round 1 of the 5-AI Paper Trading Tournament (18 picks) revealed a critical architectural flaw:
- **Direction selection explains ~80% of outcome variance** (Moskowitz 2012 TSMOM)
- All 7 winners were SHORT; 10 of 11 losers were LONG
- Scanners generated 65 BUY and 0 SELL signals — regime-blind architecture
- Winners: Avg P/L +0.29%, 100% WR | Losers: Avg P/L -0.73%, 8% WR

**Root causes** identified by 3 AIs (Grok, Mercury, Antigravity):
1. **Regime ignorance** — No BTC trend filter; longs issued in bearish regime
2. **Volume neglect** — Low-vol picks trapped in illiquidity (RENDER $35M → SL hit)
3. **ADX blindness** — ADX<15 picks had no directional edge (RENDER ADX=3)
4. **Oversold traps** — Williams %R/RSI oversold signals fail in downtrends (Lo 2000)
5. **R:R mismatch** — 1.33-1.67x R:R too ambitious for ranging market

## Design

### Component 1: Enhanced Scoring in fc_crypto_pro.py

Add regime, volume, and ADX multipliers to the main scoring formula.

**Current:** `score = effective_wr * (1 - entry_room_used)`

**New:**
```python
base_score = effective_wr * (1 - entry_room_used) * conf_boost
# Regime multiplier (from regime_router)
regime_mult = 1.2 if direction_aligned else 0.7 if direction_opposed else 1.0
# Volume multiplier
vol_mult = 1.2 if vol_24h >= 50M else 1.0 if vol_24h >= 10M else 0.7
# ADX gate for longs
adx_mult = 1.0 if adx >= 15 else 0.7 (longs only; shorts exempt)
# Oversold kill: block standalone oversold signals in downtrend
oversold_kill = True if strategy in OVERSOLD_STRATEGIES and regime == TRENDING_DOWN

final_score = base_score * regime_mult * vol_mult * adx_mult
```

**New gates added BEFORE scoring:**
- Oversold strategies killed when BTC in downtrend (Williams %R, RSI bounce standalone)
- Dynamic R:R: cap at 1.2 in RANGE_BOUND regime, require 1.5 in trending

### Component 2: Enhanced Scoring in conviction_picks.py

Apply same multipliers to conviction picks pipeline:
- Regime multiplier from `get_current_regime()`
- Volume gate: $50M minimum for LONG conviction picks
- ADX gate: >= 15 for LONGs
- Oversold kill in downtrend

### Component 3: Claude Pick Generator (NEW)

**File:** `cross_aggregation/claude_pick_generator.py`

Auto-generates Claude's tournament picks by:
1. Pulling current regime from `regime_router`
2. Scanning all systems' active picks (same sources as fc_crypto_pro)
3. Applying enhanced scoring with regime/vol/ADX multipliers
4. Selecting top 3 picks with highest composite score
5. Writing to `audit_dashboard/data/claude_top_picks.json`
6. Supporting both LONG and SHORT directions
7. Preferring 60% SHORT / 40% LONG mix in bearish regime

**Scoring formula:**
```python
base = 0.30 * effective_wr + 0.20 * min(rr/3, 1.0) + 0.25 * conf + 0.15 * vol_score + 0.10 * adx_score
final = base * regime_mult * health_mult * agreement_boost
```

### Component 4: DNA Mutation of Round 1 Results

Feed Round 1 winners/losers into the mutation lab:
- **Type A (Amplify):** Grok/Mercury SHORT strategies (Keltner, momentum breakout)
- **Type B (Invert):** KIMI LONG losers (Williams %R, mean reversion) → flip to SHORT
- **Type C (Hybrid):** Cross-breed winner entry logic + loser exit logic

Create a Round 1 mutation seed file that the mutation lab can consume.

### Component 5: Dynamic R:R

Add to regime_router.py:
```python
def get_regime_rr_cap(regime: str) -> float:
    if regime == "RANGE_BOUND": return 1.2
    if regime == "TRENDING_DOWN": return 2.0  # wider for shorts
    if regime == "TRENDING_UP": return 1.5
    return 1.5  # default
```

Picks with R:R above cap get their TP tightened automatically.

## Files Changed

| File | Change |
|------|--------|
| `cross_aggregation/fc_crypto_pro.py` | Add regime/vol/ADX/oversold scoring multipliers |
| `cross_aggregation/conviction_picks.py` | Same multipliers + volume gate |
| `cross_aggregation/regime_router.py` | Add `get_regime_rr_cap()`, `get_market_context()` |
| `cross_aggregation/claude_pick_generator.py` | NEW — auto-generate Claude tournament picks |
| `audit_dashboard/blueprint_generator.py` | Already done (deployed) |
| `genome/mutation_lab/round1_seeds.json` | NEW — Round 1 winners/losers for mutation |
| `tests/verify_round2_scoring.spec.ts` | NEW — Playwright tests for dashboard |

## Success Criteria

1. All systems produce regime-aware picks (SHORT in bearish, LONG in bullish)
2. No standalone oversold signals in downtrend
3. Volume and ADX gates active
4. Claude picks auto-generated with enhanced scoring
5. Dashboard shows correct rankings by avg P/L%
6. Playwright tests pass
7. Expected improvement: WR 50% → 65%, avg P/L +0.4% → +0.7%

## Testing Plan

1. Unit validation: Run `fc_crypto_pro.py` locally, verify regime multipliers apply
2. Playwright: Verify AI Battle tab loads, all 5 agents show, rankings sort correctly
3. Live validation: Monitor Round 2 picks for 24h, compare to Round 1 patterns
