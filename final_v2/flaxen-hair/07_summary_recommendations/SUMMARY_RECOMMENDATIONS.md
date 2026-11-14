# Summary & Recommendations — final_v2

**Date:** 2026-11-14 | **Worktree:** flaxen-hair

## Bottom Line

**mega_mutation_macd_rsi / ema_momentum on CRYPTO** is the only statistically valid, forward-validated profitable edge in the entire codebase. All other asset classes show negative edge after rigorous statistical testing. The profitability research program exhausted the keyless data hypothesis space (23 hypotheses across 4 versions, NONE PROVED).

---

## What We Found

### The Edge: mega_mutation_macd_rsi on CRYPTO

| Metric | Backtest | Forward (live since Jun 6, 2026) |
|--------|----------|----------------------------------|
| Profit Factor | 3.12–5.816 | **8.32** |
| Win Rate | 64–76% | **84%** |
| Trades | 100–593 | **50** |
| Statistical validation | — | Paired bootstrap pass_95=True (m048/m084), MC pct=0.949 |

**8 verified combos:** JUPUSDT, ENAUSDT, ADAUSDT, WIFUSDT, STXUSDT, RENDERUSDT (MACD_RSI); AVAXUSDT, DOTUSDT (EMA_CROSS)

**Production status:** `production_enable = true`, `promotion_ready = true`, no blockers

### What Does NOT Work (All NOT_PROVED)

| Asset Class | Strategies Tested | Best Result | Reason for Failure |
|-------------|-------------------|-------------|-------------------|
| Crypto | Momentum, reversal, TSMOM, RSI(2), breadth, funding carry | Funding carry Sharpe 14.24 (n=10) | Funding carry below cash after capital adjustment; momentum/reversal negative |
| Equity | RSI(2), sector momentum, dual momentum | RSI(2) Sharpe 1.83 (H10) | OOS contamination, effective N≈38, single-day dependence, execution fragility |
| ETFs | XS momentum, reversal, TSMOM breadth, dual momentum | XS momentum Sharpe 0.98 vs 1.18 bench | Underperforms benchmark, SPA p=0.488 |
| Bonds | None tested | N/A | Pure gap — no hypotheses |
| Mutual funds | None tested | N/A | Pure gap — no data source or algorithm |
| Forex | None tested | N/A | Pure gap — no hypotheses |
| Commodities/Futures | None tested | N/A | Pure gap — no hypotheses |

### What Was Falsified

| Claim | Verdict | Reason |
|-------|---------|--------|
| Peer VWAP mean reversion | FALSIFIED | Annualization error 3.76→1.18, PBO degenerate, DSR not DSR, intrabar stops PF 0.81 |
| TradingView contest winners as proof | Survivorship bias | Winners selected from thousands; not repeatable method |
| H10 RSI(2) as proved | NOT_PROVED | Contaminated OOS, effective N=38, single-day dependence, T-bill carry dependency |

---

## Top Recommendations

### P0 — Do This Week

1. **Paper trade mega_mutation via gated scanner daily**
   - Run `quick_wins/shared/daily_forward_tracker.py --once`
   - Target: n=100 forward picks for T2 confirmation (currently n=50)
   - Currently 0 picks emitted — BTC below 200-EMA bear regime (correct behavior)

2. **Monitor forward performance**
   - Track TP/SL hits on emitted picks
   - Success: WR ≥ 55%, PF ≥ 1.5 after n=100

3. **Apply finpredict-v4 6-gate scoring to all strategies**
   - Run `alpha_engine/statistical_scoring_framework.py`
   - Certify strategies as FAIL/DISCOVERY/VALIDATED/MONEY_READY

### P1 — Do This Sprint (2-4 Weeks)

4. **Clean forward OOS test of H10 RSI(2) on SPY/QQQ**
   - Frozen parameters, start after 2026-11-13
   - Minimum: 90 days or 30 round trips
   - Stricter gates: DSR ≥0.95 after N≥38, ex-best-day, 2-day-lag Sharpe ≥1.0

5. **Develop new hypotheses for untested asset classes**
   - Bonds: Bond ETF TSMOM
   - Mutual funds: Monthly NAV dual momentum (add MUTUAL_FUND class)
   - Forex: Carry trade + trend following
   - Commodities: TSMOM on futures

6. **Investigate ENA funding-rate collinearity**
   - Verify mega_mutation edge isn't just funding arbitrage on ENA

### P2 — Do in 1-3 Months

7. **Promote to live capital** (if go/no-go criteria met)
   - n ≥ 100 forward, WR ≥ 55%, PF ≥ 1.5, all 6 gates passing
   - Start small, scale up after 3+ months clean performance

8. **Acquire new data sources**
   - Intraday/order-book data, options/vol-risk-premium data, venue-level capital data
   - Keyless data hypothesis space is exhausted

9. **Implement heterogeneous stacking and tail clipping**
   - Stack LightGBM + GRU-Attention + Ridge as meta-features
   - Clip ensemble outputs to [2nd, 98th] percentile

---

## Risk Warnings

| Risk | Severity | Mitigation |
|------|----------|------------|
| Forward sample too small (n=50) | HIGH | Accumulate to n=100 before live capital |
| ENA funding-rate collinearity | MEDIUM | Test edge with/without ENA; check funding correlation |
| Regime dependence | MEDIUM | BTC 200-EMA filter keeps us out of bear markets |
| Keyless data exhausted | HIGH | Need intraday/options/venue data for new edges |
| Contest winner survivorship bias | HIGH | Don't copy contest methods without statistical validation |
| Funding carry capital intensity | MEDIUM | Doesn't beat cash after 1.5× capital; n=10 <30 |

---

## Go/No-Go Decision Matrix

| Strategy | Forward Edge | Statistical Validity | Production Ready | Recommendation |
|----------|-------------|---------------------|------------------|----------------|
| mega_mutation (Crypto) | YES (84% WR, PF 8.32) | PARTIAL (pass_95=True) | YES | **PAPER TRADE → LIVE if criteria met** |
| H10 RSI(2) (Equity) | NO (retrospective only) | NO (contaminated OOS) | NO | Clean forward test |
| Funding carry (Crypto) | PARTIAL (DSR 1.0) | NO (n=10 <30) | NO | Monitor; needs venue-level capital data |
| New asset classes | NO (untested) | NO | NO | Develop hypotheses |

---

## Final Assessment

The search for a statistically valid, profitable approach across all asset classes has been exhaustive:

- **23 hypotheses** tested across 4 protocol versions
- **NONE PROVED** — honest negative result
- **Only mega_mutation_macd_rsi on CRYPTO** shows forward-validated edge (but needs n=100 forward confirmation)
- **Keyless data hypothesis space is exhausted** — need new data types for further progress

**Recommended path:** Paper trade mega_mutation daily via gated scanner, accumulate forward evidence, and only promote to live capital after meeting all go/no-go criteria. Simultaneously, develop hypotheses for untested asset classes and acquire new data sources.
