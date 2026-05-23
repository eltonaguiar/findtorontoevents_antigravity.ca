# Forex Strategy Implementation & Scoring Fix

## Session Summary (March 16, 2026)

### 1. New Forex Strategies Deployed

Added 4 new strategies + COT positioning + carry trade enhancement to `alpha_engine/forex_strategies.py`. Total forex strategies: **16** (12 core + 3 community + COT).

| Strategy | Type | Research Basis | Status |
|----------|------|----------------|--------|
| `sunday_night_gap_trade` | Mean-reversion | Nassir & Mohamad 2007 (65% gap-fill rate) | Waiting (needs Monday) |
| `session_volatility_expansion` | Breakout | Lien 2008 session transitions | Waiting (needs ATR compression) |
| `forex_tsmom_12m` | Momentum | Moskowitz et al. 2012 JFE (Sharpe 0.60-0.90) | **LIVE — 2 picks** |
| `forex_logistic_direction` | ML-lite | Wang 2025 + Hansen SPA test | **LIVE — 3 picks** |
| `carry_trade_momentum` (enhanced) | Carry | Koijen et al. 2018 vol-timing | LIVE (existing, now with vol gate) |
| `cot_positioning` | Sentiment | CFTC commercial hedger data | Waiting (needs COT module) |

### 2. Files Modified

- `alpha_engine/forex_strategies.py` — 4 new strategy functions + carry trade vol-timing gate (+517 lines)
- `alpha_engine/config.py` — STRATEGY_FAMILIES entries for new strategies (+11 lines)
- `alpha_engine/scanner.py` — STRATEGY_REGIME_MAP entries + COT import (+38 lines)
- `audit_dashboard/index.html` — Per-strategy trust tier scoring (v96)

### 3. Audit Dashboard Scoring Fix (v96): Per-Strategy Trust

**Problem:** Alpha engine's system-level WR is 41.1% (96 trades), which puts it in SANDBOX tier (0.40x multiplier). This crushed ALL alpha_engine picks to scores of 9-24 regardless of individual strategy quality.

**Root cause:** The trust system evaluated the entire system as one unit. Winning strategies (fractal_sr_bounce 71% WR, cumulative_delta_divergence 67%) were penalized for sharing a system with losers (london_breakout 0% WR).

**Fix:** Added per-strategy trust tier evaluation (step 4 in `getTrustTier`):
- Strategies with 5+ closed trades get scored on their OWN win rate and profit factor
- Strategies with 3-4 trades get partial credit
- Strategies with <3 trades fall back to system-level trust (unchanged behavior)

**Trust tier thresholds (per-strategy):**

| WR | PF | Tier | Weight |
|----|-----|------|--------|
| 65%+ | 2.0+ | PROVEN | 0.95x |
| 55%+ | 1.5+ | RELIABLE | 0.85x |
| 50%+ | 1.0+ | RELIABLE | 0.75x |
| 45%+ | any | WATCH | 0.60x |
| 35%+ | any | SANDBOX | 0.40x |
| <35% | any | SANDBOX | 0.25x |

**Impact (simulated):**

| Strategy | Old Score | New Score | Change |
|----------|-----------|-----------|--------|
| fractal_sr_bounce (71% WR, 7 trades) | 20 | 48 | +28 |
| cumulative_delta_divergence (67% WR) | 19 | 40 | +21 |
| widened_tp_momentum_carry (67% WR, 3t) | 20 | 30 | +10 |
| community_london_breakout (0% WR, 6t) | 19 | 12 | -7 |
| hurst_regime_adaptive (20% WR, 5t) | 19 | 12 | -7 |
| forex_tsmom_12m (0 trades, new) | 18 | 18 | 0 |
| forex_logistic_direction (0 trades, new) | 18 | 18 | 0 |

**Scope:** Affects ALL systems, not just forex. Any strategy with enough trades gets scored independently.

### 4. Forward Test Status

**Current forex performance (all systems combined):**
- 86 closed forex trades: 14W / 55L / 17 expired = 20.3% WR, -19.54% PnL
- Best: `adaptive_vr_confluence` (75% WR, +3.44%) and `widened_tp_momentum_carry` (100% WR, +3.34%)
- Worst: `community_london_breakout_v2_forex` (0% WR, -6.06%)

**New strategy picks need time to resolve** — first results expected within 7-14 days (forex max_hold = 14 days).

### 5. Pipeline Verification

- Alpha engine workflow runs every 15 min (confirmed working)
- New picks flow: scanner → active_picks.json → dashboard_generator → audit payload → live dashboard
- Verified 5 new forex picks reached active_picks.json on GitHub
- Audit dashboard deployed to all 3 FTP targets (findtorontoevents.ca, torontoevent.net, tdotevent.ca)
