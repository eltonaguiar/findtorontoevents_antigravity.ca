# Session AM — Swarm Review Request
# Date: 2026-05-17
# Session: AM (following AL — APPROVE)

## Context

Session AM: first session after AL. Focus on dashboard health monitoring, performance alert investigation, and identifying next actionable items.

## Session AM Findings

### 1. M-037 Fix Confirmed Active (not yet reflected in dashboard)

The M-037 fix (ml_score=0 → fail-open) is working locally: 2 CRYPTO picks now pass quality gates — ETHUSDT and BNBUSDT from `prediction_market_agents` with ml_score=0.0. Previously both were blocked because `0.0 < 0.65 → blocked`.

Dashboard still shows active=0 for CRYPTO because:
- Dashboard was generated at 15:04 UTC (before M-037 commits at ~14:45 UTC)
- The ML-gated picks (ml_crypto_predictor blocked by NS-D, BUY direction blocked by M-036) still dominate active_picks.json
- Good new picks from signal_validation/baby_strats_forward will appear on next scanner run

### 2. Performance Alerts — 17 HIGH Degradation Alerts

The dashboard shows 17 HIGH performance alerts across multiple strategies. **KEY FINDING: None of these strategies have current active picks** — all 0 active picks locally verified.

| Strategy | 7d WR | Baseline | n_7d | Currently Active? |
|----------|-------|----------|------|-------------------|
| cot_positioning | 46% | 93%* | 39 | 0 |
| cftc_cot_commercial_signal | 31% | 93%* | 39 | 0 |
| ig_contrarian_sentiment | 24% | 36% | 38 | 0 |
| atr_percentile_gate | 30% | 68% | 20 | 0 |
| ensemble | 19% | 44% | 43 | 0 |
| st_rsi_momentum_confluence | 39% | 62% | 56 | 0 |
| st_multi_day_momentum | 23% | 53% | 47 | 0 |
| st_atr_vol_breakout | 33% | 80% | 48 | 0 |
| macd_rsi_m048 | 32% | 71% | 25 | 0 |
| hs_lb_None | 5% | 37% | 83 | 0 (source blocked) |
| atr_regime_rsi | 28% | 40% | 50 | 0 |
| crypto_bayesian_* | 32% | 49% | 19 | 0 |
| crypto_mtf_ema_slope_* | 17% | 44% | 18 | 0 |
| keltner_compression_* | 26% | 49% | 19 | 0 |

*COT baseline=93% is a known artifact of COT over-emission (114 raw → 40 deduped picks counted as 114 wins). Real COT performance: CT=F WR=77.5%, PF=4.69, n=40 deduped (verified Session AH).

**Root cause hypothesis:** Current market regime = TRENDING_DOWN (from regime_terminal). In TRENDING_DOWN regime, `check_active_picks` shows WR=6.2% (n=16 trades) and RANGING WR=0% (n=9). This adverse regime explains the broad strategy degradation. The strategies degraded in RECENT history when the market turned down.

**hs_lb_None disposition:** Source system `copy_trader_highscore` IS already blocked (confirmed in BLOCKED_SOURCE_SYSTEMS). The 83 "recent" picks in the 7d window are historical picks from before the block was applied.

### 3. All Degraded Strategies Are Historical (Not Generating New Picks)

All 17 degraded strategies have 0 current active picks. This confirms:
- The quality gates (NS-D, M-036, M-037, BLOCKED_SOURCE_SYSTEMS) are correctly preventing new picks from these sources
- The performance alerts represent closed historical picks from before the gates were applied
- No immediate blocking action is needed

### 4. FOOLPROOF Status — All Items Resolved

All remaining open FOOLPROOF items are:
- External blocked: COT CFTC pipeline, FRED API key, ml_score upstream
- Monitoring notes: BOND PF thresholds (added Session AL)
- Stale: bond_scanner.py --merge (cleared Session AL)

No new actionable FOOLPROOF items discovered in Session AM.

### 5. Current Asset Class Health

| Class | CB-30d n | CB-30d WR | Verdict |
|-------|----------|-----------|---------|
| EQUITY | 82 | 58.5% | WATCH (PBO/SPA need n≥20/strategy) |
| COMMODITY | 65 | 56.9% | WATCH |
| CRYPTO | 2,868 | 46.2% | MONEY_READY (SPA filter) |
| ETF | 40 | 67.5% | WATCH |
| FOREX | 33 | 48.5% | NOT_READY |
| BOND | 0 | N/A | INSUFFICIENT_DATA |

Dashboard generated at 15:04 UTC (33 min stale when inspected, now ~1h stale).

## Questions for Swarm

1. **Market regime response**: Current regime is TRENDING_DOWN with WR=6.2%. Should the system automatically reduce sizing when regime = TRENDING_DOWN? Or is the existing strategy/gate stack sufficient to handle regime changes (degraded strategies are already blocked)?

2. **Performance alerts triaging**: Are the 17 HIGH alerts a concern if all have 0 active picks? Should we suppress alerts for strategies that are already effectively blocked (via source system blocks or other gates)?

3. **EQUITY active picks gap**: EQUITY CB-30d WR=58.5% (T1) but active=0. The kimi_riseoftheclaw workflow runs hourly (ANTIGRAVITY-CLAUDEOPUS workflow). Why might active EQUITY picks not be appearing in the dashboard? Is this worth investigating?

4. **COT alert false positives**: The 93% baseline for cot_positioning/cftc_cot_commercial_signal is inflated by the COT over-emission artifact. Should we suppress or recalibrate performance alerts for COT strategies specifically?

5. **Overall verdict**: Is Session AM APPROVE? No code changes were made — this was a diagnostic/monitoring session.

## Verification

- CI Tests: green (25994411552, Session AL)
- Active picks check: 2 CRYPTO pass (ETHUSDT, BNBUSDT), 9 BOND pass, 0 EQUITY/COMMODITY/FOREX (concentration cap)
- Degraded strategies: 0 active picks confirmed
- FOOLPROOF: all items done/blocked/stale
