# Peer Coordination Status — 2026-03-24 03:15 UTC

## Completed Work (This Session)

### Forex Deadlock Fix (DEPLOYED — commit 5f708ab)
**Problem:** `production_scanner.py` Gate 3 had a catch-22:
- Blocked ALL forex when < 10 closed trades existed
- But forex couldn't accumulate trades because the gate blocked them
- Result: forex permanently dead-locked out of the pipeline

**Fix (3 parts):**
1. **Gate 3 logic** (`production_scanner.py:1191-1205`): Changed from "block when insufficient data" to "pass through when insufficient data". Forex only gets blocked if 10+ trades prove WR < 30%.
2. **core_whitelist.json**: Cleared `kill_categories` (was `["forex"]`), removed 6 forex strategies from kill_list that were killed by category not by individual performance. London_breakout (0/7) stays killed.
3. **auto_tuner.py**: Already had `HARD_DISABLED_CATEGORIES = set()` — no change needed.

**Strategies un-killed:**
- `community_ema_8_21_scalp_forex`
- `community_forex_zscore_mean_reversion`
- `forex_logistic_direction`
- `forex_mean_reversion_200d`
- `forex_rsi2_mean_reversion`
- `forex_tsmom_12m`
- `multi_asset::bb_mean_reversion_forex`

**Strategies still killed (proven losers):**
- `community_london_breakout_v2_forex` (0/7 WR)
- `alpha_engine_fast::community_london_breakout_v2_forex` (0/7 WR)

### Pylance OOM Fix (LOCAL)
- Created `pyrightconfig.json` excluding 22 directories (`.venv`, `.venv312`, `tmp`, `incubator`, etc.)
- Reduced Pylance's scan from 2700+ files to ~500 active source files
- Prevents the JavaScript heap OOM crash at ~2.86 GB

---

## Active Peers & Their Work (as of 03:13 UTC)

| Peer ID | Task | Relevance to Forex/WR |
|---------|------|-----------------------|
| `9rt4epgl` | Wiring indicator correlation into elite_scorer + production_scanner | HIGH — Technical Confirmation scoring affects all picks including forex |
| `owxe9ty8` | Clone A/B testing framework — 12 variation portfolios | MEDIUM — Could include forex-specific parameter variations |
| `fbrhpad4` | Win rate analysis by strategy category | HIGH — Need forex WR breakdown to guide next steps |
| `fcc1gex2` | 8 audits, A/B framework, MTF gate, SHORT engine | MEDIUM — Forex shorts (carry trade) need different treatment than crypto |
| `8lhtfz7w` | Quality gates, indicator correlation tracker, strategy tiers | HIGH — Indicator tracker should include DXY/interest rate differentials |
| `vm1ur9f9` | Orchestrator — fixing GH Actions, non-crypto price feeds | CRITICAL — Non-crypto price feeds must work for forex picks to validate |
| `xu5ybg81` | Updating docs, deploying quant strategies | LOW — Documentation |

---

## Future Plans & Recommendations

### Immediate (Next 24h)
1. **Monitor forex pick flow**: After next alpha-engine-live.yml run (~30 min cycle), verify forex picks appear in `active_picks.json` with proper prices
2. **Non-crypto price feed**: `vm1ur9f9` (orchestrator) is fixing this — forex symbols need yfinance or alternative price source since Binance doesn't cover FX
3. **Forex indicator integration**: Ask `9rt4epgl` to add DXY correlation, interest rate differentials, and carry spread to the Technical Confirmation scoring for forex picks

### Short-term (This Week)
4. **Forex-specific Smart Pick weights**: Current formula gives forex `regime_match * 0.20` + `elite_quality * 0.30` — this is good but should also factor in:
   - DXY trend alignment (strong USD = favor USD longs)
   - Interest rate differential direction (carry)
   - Session timing (London/NY overlap = best forex liquidity)
5. **Separate forex SL/TP logic**: Forex moves in pips, not percentages. ATR-based SL should use forex-specific ATR multipliers (0.5x vs 1.0x for crypto)
6. **Clone A/B test for forex**: Ask `owxe9ty8` to add a forex-focused variation testing carry_trade + connors_rsi2 + mean_reversion strategies

### Medium-term (Next 2 Weeks)
7. **Forex data accumulation target**: Need 20+ closed forex trades to make data-driven decisions. At current rate (~2-3 forex picks/day), should have enough data by April 5
8. **Proven forex strategies to prioritize** (from academic research):
   - Carry trade (Sharpe 2.0-3.0, Moskowitz et al. 2012)
   - Connors RSI2 mean reversion (62-68% WR on majors)
   - Asian range breakout (55-60% WR during London session)
9. **Kill london_breakout permanently**: 0/7 with zero MFE — this strategy never even approaches profit on forex

### Integration with Grok's non_crypto_agent
- Grok deployed `non_crypto_agent/main.py` with 6 forex strategies: carry_trade, asian_range_breakout, orb_breakout, connors_rsi2_forex, cross_sectional_momentum_forex, cot_positioning_forex
- These output to `non_crypto_agent/picks.json` — NOT yet integrated into main alpha_engine pipeline
- **TODO**: Wire non_crypto_agent output into production_scanner or create a merge step in the workflow

---

## Key Files Modified

| File | Change | Status |
|------|--------|--------|
| `alpha_engine/production_scanner.py` | Gate 3 forex deadlock fix | DEPLOYED |
| `alpha_engine/data/core_whitelist.json` | Cleared kill_categories, un-killed 7 forex strats | DEPLOYED |
| `pyrightconfig.json` | Pylance OOM fix (exclude 22 dirs) | LOCAL ONLY |

---

## Coordination Requests Sent

Messages sent to: `9rt4epgl`, `owxe9ty8`, `vm1ur9f9`, `fbrhpad4`, `fcc1gex2`, `8lhtfz7w`

All peers asked to:
1. Pull latest before editing production_scanner.py
2. Include forex in their respective analyses/frameworks
3. Share findings relevant to forex/non-crypto WR improvement
