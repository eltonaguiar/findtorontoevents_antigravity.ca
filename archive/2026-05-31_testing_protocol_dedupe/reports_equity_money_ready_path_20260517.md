# EQUITY MONEY_READY Path Analysis — 2026-05-17

## Current Status
| Metric | Value | Target | Gap |
|--------|-------|--------|-----|
| n (resolved) | 240 (dashboard fallback) | ≥50 | ✅ |
| WR | 53.3% | ≥52% (MIN_WR_BY_CLASS) | ✅ |
| PF | 1.97 | ≥1.5 | ✅ |
| DSR | N/A | ≥0.95 | ❌ (needs ≥2 strategies) |
| SPA | N/A | p≤0.10 | ❌ (needs ≥2 testable strategies) |
| Verdict | **WATCH** | MONEY_READY | Blocked by DSR/SPA |

## Root Cause: DSR/SPA Require ≥2 Testable Strategies

DSR (Deflated Sharpe Ratio) corrects for multiple testing across strategies.
SPA (Superior Predictive Ability) tests family-wide edge across strategies.
Both require ≥2 strategies with n≥20 each.

**Current:** Only `stocks_rsi2_pullback` has n≥20 (n=44 WON/LOST in closed_picks.json).
**Needed:** A second EQUITY strategy with n≥20 resolved picks.

## Available EQUITY Strategies (wired but no live picks)

| Strategy | Backtest (walk_forward_gate.py) | n live | Path to n≥20 |
|----------|--------------------------------|--------|--------------|
| `stocks_rsi2_pullback` | Primary strategy, n=240 in dashboard | 44 WON/LOST | ✅ Already there |
| `connors_rsi2_scanner` | n=74, WR=75.7%, Sharpe=4.84, validated 2026-03-16 | 0 | Need to enable |
| `connors_rsi2_short_scanner` | SHORT mirror of above | 0 | Need to enable |
| `triple_rsi_scanner` | In equity_strategies.py | 0 | Not validated |
| `vix_spike_reversal_scanner` | n=50, WR=72.0%, validated | 0 | Secondary candidate |

## Fastest Path: Enable connors_rsi2_scanner

`connors_rsi2_scanner` is:
- In `EQUITY_STRATEGIES` dict (equity_strategies.py:1331)
- In `walk_forward_gate.py` with validated backtest (WR=75.7%, n=74, Sharpe=4.84)
- In `scanner.py` REGIME_FILTER at line 1058 (compatible with "ranging" regime)
- NOT currently generating live picks

### Why No Live Picks?
Most likely cause: **elite_score gate ≥55** (quality_gates.py line 6477).
EQUITY picks have a wide score distribution (median ~36); only picks with elite_score≥55 
pass through. connors_rsi2_scanner picks likely cluster around 40-50.

### Recommended Action
1. **Shadow mode for connors_rsi2_scanner**: Enable emission with a lower elite_score 
   floor (≥40 instead of ≥55) under a separate `CONNORS_SHADOW_ENABLED=1` flag.
   Log signals to `data/connors_shadow_log.jsonl` — do NOT add to active_picks.
2. **After 30 days**: If shadow picks show WR≥55% and PF≥1.5 on n≥30, promote to live.
3. **DSR/SPA enabled**: Once connors_rsi2_scanner has n≥20 live resolved picks, 
   money_ready_verdict can compute DSR/SPA across 2 strategies.

## Alternative Path: Leverage Existing Strategies

The `scores_rsi2_pullback` sub-variants already exist:
- `stocks_rsi2_pullback_tight` (n=1 WON/LOST)
- `stocks_rsi2_pullback_wide` (n=1 WON/LOST)

If these are enabled in production and reach n≥20 each, they count as separate 
strategies for DSR/SPA. Check if they're wired in the production scanner.

## Current EQUITY Score Gate Analysis

From quality_gates.py line 6477, EQUITY requires elite_score≥55:
- elite_score <40: n=9 WON/LOST, WR=22.2%
- elite_score 40-54: n=33 WON/LOST, WR=36.4%
- elite_score 55+: n=2 WON/LOST, WR=100.0%

The gate is correct in filtering low-score picks. For DSR/SPA, we need a different 
strategy (not just higher scores from the same strategy).

## Walk-Forward Evidence for connors_rsi2_scanner

```
Strategy: connors_rsi2_scanner
Backtest: n=74, WR=75.7%, avg_win=3.0%, avg_loss=-2.5%
Expectancy per trade: 1.65%
Validated: 2026-03-16
Asset class: equity
Notes: Connors RSI2 on SPY/QQQ/NVDA
```

This is sufficient evidence to enable shadow emission.

## Timeline Estimate

| Milestone | ETA | Condition |
|-----------|-----|-----------|
| connors shadow wired | Next session | claude-code |
| n=20 shadow picks | +2-3 weeks | Market + scanner runs |
| DSR/SPA computable | +3 weeks | Need ≥2 strategies at n≥20 |
| EQUITY MONEY_READY | +4-6 weeks | DSR≥0.95, SPA p≤0.10 |

## Action Items

1. **[P1, claude-code]** Wire `connors_rsi2_scanner` shadow mode with elite_score≥40 floor
   - New env var: `CONNORS_SHADOW_ENABLED=1`
   - Log to `data/connors_shadow_log.jsonl`
   - Review gate: 2026-06-14 (same as PEAD)
   - File: `alpha_engine/equity_strategies.py`, `audit_trail/quality_gates.py`

2. **[P2, claude-code]** Enable `stocks_rsi2_pullback_tight` and `stocks_rsi2_pullback_wide` 
   in production (they already exist in equity_strategies.py but may not be emitting).

3. **[P3, wait]** Once n≥20 for 2 strategies, money_ready_verdict DSR/SPA will run automatically.

## Files to Change (P1)

- `audit_trail/quality_gates.py` — add CONNORS_SHADOW_ENABLED shadow path (fail-open)
- `alpha_engine/equity_strategies.py` — verify connors_rsi2_scanner is correctly parameterized
- `updates/index.html` — document the shadow start

## Swarm Recommendation (2026-05-17)
Grade A swarm Q1 verdict: "Accept EQUITY as WATCH. Begin development of second EQUITY strategy 
(mean-reversion or momentum variant, targeting n≥50 and WR≥55%). 
Do NOT force-scale stocks_rsi2_pullback alone."
