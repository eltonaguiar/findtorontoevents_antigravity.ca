# FUTURES Asset Class Audit — Buffy
**Agent:** Buffy (Codebuff) | **Date:** 2026-05-05  
**Class Status:** DEAD (WR 6.3% | n=17 total | n=2 recent)

---

## Health Summary

FUTURES is functionally dead. Only 2 recent trades (both multi_asset_copytrader, both profitable at 100% WR — meaningless at n=2). The 6.3% total WR comes from killed strategies that are already blocked.

## What's Killed (quality_gates.py BLOCKED_STRATEGIES)

| Strategy | Status |
|----------|--------|
| connors_rsi2 | 0/2/3 = 0% WR n=5 |
| hyperopt_connors_rsi2 | 0/1/0 n=1 |
| mean_reversion_bollinger | 0/2/0 n=2 |
| extreme_oversold_bounce | 0/1/1 n=2 |
| vix_reversal | 0/2/2 n=4 |
| futures_mean_reversion | 0/1/0 (catastrophic -88.8% single pick) |
| ema_stack_momentum | 1/1/0 marginal |

## The One Hope

**futures_momentum**: 4W/3L/1F = 57.1% WR, +4.94% on n=8 (tiny sample). Currently the only viable FUTURES strategy. Being drowned by the killed strategies above.

## Specific Fixes

1. **Keep FUTURES blocked at class level** — not enough data to justify active trading
2. **Unblock futures_momentum specifically** — let it build history. 57.1% WR on 8 trades is promising.
3. **Score floor at 35** (2026-05-03) — verify picks are flowing after lowering from 45
4. **Re-evaluate at n=50 closed** — minimum for any capital allocation decision

## Risk

Negligible — n=2 recent trades. FUTURES can't hurt the portfolio. The real risk is the single catastrophic -88.8% trade pattern recurring if futures_mean_reversion leaks through the kill list.
