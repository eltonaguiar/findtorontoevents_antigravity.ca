---
tags: [strategy, forward-test, paper-pilot]
created: 2026-06-06
status: active
---

# Forward-Test Queue — Strategies Needing Paper Pilot

Strategies with promising backtests but **insufficient live data** (n<100 or OOS not confirmed).
Do NOT size real money until they graduate from this list.

## Tier: Strong Candidates (clear shape, just need n)

| Strategy | Class | PF (lab) | WR | n now | n needed | ETA |
|----------|-------|----------|----|-------|---------|-----|
| [[strategies/fx_smart_carry_trade_momentum]] | FOREX | 1.85 | TBD | 25 | 100 | ~5-6wk |
| `crypto_liquidity_wick_reversal_v1` | CRYPTO | 1.55 | 60% | 30 | 100 | ~8wk |
| [[strategies/etf_verified_dual_momentum]] | ETF | 1.60 | 50% | 0 fwd | 150 | pilot active |
| `RENDER_ensemble` | CRYPTO | T2 shape | — | 30 | 100 | ~8wk |

### What's blocking each

| Strategy | Blocker |
|----------|---------|
| `fx_smart_carry_trade_momentum` | n=25 only; live accumulation in progress |
| `crypto_liquidity_wick_reversal_v1` | Single-source artifact suspected — verify multi-source first |
| `etf_verified_dual_momentum` | No forward trades yet (pilot just started 2026-06-02) |
| `RENDER_ensemble` | n=30, needs fill validation |

---

## Tier: Needs Investigation First

| Strategy | Class | Issue |
|----------|-------|-------|
| `cta_cross_asset_tsmom` SHORT | FOREX | PF 0.87 — below T2 bar despite n=151 |
| `etf_dual_momentum` (backtest) | ETF | No production wire-up yet |
| Any EQUITY momentum strategy | EQUITY | Category column case-mess; needs cleanup first |
| Any BOND strategy | BOND | n=8, no meaningful stats yet |
| Any COMMODITY strategy | COMMODITY | CT=F 57% concentration, n=28 |

---

## Graduated / Promoted

| Strategy | Class | Graduated | How |
|----------|-------|-----------|-----|
| [[strategies/mega_mutation]] | CRYPTO | ✅ T1 live | n=204, PF 2.86, 3-reviewer verified |

---

## Graduation Criteria (to move from queue → READY-TO-TRADE)

1. n≥100 clean trades (post-dedup, post-resolver)
2. PF≥1.5 (T2) in walk-forward OOS
3. Intrabar fill validated via `tools/validate_intrabar_fills.py`
4. 14d recency panel: WR non-declining
5. No single-source concentration (HHI<0.30)

## Related

- [[strategies/READY-TO-TRADE-NOW]]
- [[reference/data-quality-checklist]]
- [[incidents/resolver-intrabar-blocker]]
