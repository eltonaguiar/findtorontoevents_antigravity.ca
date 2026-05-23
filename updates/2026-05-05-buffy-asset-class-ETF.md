# ETF Asset Class Audit — Buffy
**Agent:** Buffy (Codebuff) | **Date:** 2026-05-05  
**Class Status:** CANDIDATE (WR 53.5% | PF 1.20 | n=86 recent | +19.05% cum PnL)

---

## Health Summary

ETF is small (86 recent trades) but net profitable (+19.05%) with acceptable WR (53.5%). Carried by kimi_riseoftheclaw (76 of 86 trades). IWM and GLD are confirmed drags.

## Winners

| Strategy | WR | n | Cum PnL |
|----------|-----|---|---------|
| kimi_riseoftheclaw | 52.6% | 76 | +27.44% |

## Drags (Blacklisted per Phase 2-E panel)

| Symbol | WR | n | Cum PnL | Status |
|--------|-----|---|---------|--------|
| IWM (Russell 2000) | 43.8% | 16 | -11.67% | BLACKLISTED |
| GLD (Gold) | 36.4% | 11 | -6.23% | BLACKLISTED |
| XLF (Financials) | 33.3% | 3 | -1.54% | KEEP (small n) |

## Keepers

| Symbol | WR | n | Cum PnL |
|--------|-----|---|---------|
| XLK (Tech) | 71.4% | 7 | +14.55% |
| XLE (Energy) | 56.2% | 16 | +7.91% |
| QQQ (Tech) | 61.5% | 13 | +5.24% |
| SPY (Broad) | 50.0% | 10 | -0.09% |

## Specific Fixes

1. **Verify ETF_BLACKLIST (IWM, GLD) is enforced** — check `ETF_IWM_GLD_KILL_DISABLED` env var
2. **Build trade volume** — n=86 is too thin for statistical confidence. Need 200+ closed before promoting from CANDIDATE.
3. **Score floor at 40** — appropriate for ETF. Don't lower further.
4. **kimi_riseoftheclaw is the sole carrier** — same single-point-of-failure risk as EQUITY. Diversify ETF strategy sources.

## Risk

Thin book (86 trades) means all metrics have wide confidence intervals. Single strategy dependency. ETF should remain CANDIDATE tier until n >= 200.
