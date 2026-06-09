---
tags: [strategy, picks-now, ready-to-trade]
created: 2026-06-06
status: active
---

# Ready-to-Trade — Best Strategies Now

> Source: `reports/REAL_MONEY_MASTER_2026-06-05.md` + `reports/PICKS_NOW_2026-06-06.md`
> NFA — Research/Paper Only

> [!warning] SUPERSEDED by the 2026-06-09 audit — DO NOT trade on these
> Clean cohort + intrabar replay (2026-06-09): **0 confirmed money-ready survivors** across all classes. CRYPTO class true WR **39.7%** after intrabar (15k picks). FOREX clean 14d WR **5.0%**. See `reports/OBS_FINDING_JUNE8.MD`, `reports/reresolve_intrabar_latest.json`, `updates/2026-06-09-ohlcv-deep-backfill.md`.

> Prior warning (2026-06-06) still applies: production resolver does not replay intrabar OHLC.

## Why these qualify

Every pick here passed:
1. OHLCV backtest with **intrabar-aware fills** (conservative SL-first)
2. **2+ independent source agreement**
3. No single-day concentration (max_day_count < 35% of n)
4. Explicit disconfirmation check

---

## CRYPTO — mega_mutation sleeve (T1 confirmed)

| Symbol | Dir | Entry | TP | SL | WR | n | Conf |
|--------|-----|-------|----|----|-----|---|------|
| NEARUSDT | LONG | 2.156 | +7.5% | -5.6% | 90.9% | 11 | HIGH |
| INJUSDT | LONG | 5.189 | +5.9% | -4.4% | 90.5% | 21 | MED |
| ATOMUSDT | LONG | 1.749 | +5.0% | -3.0% | 75.8% | 33 | MED (wait RSI<35) |

- mega_mutation PF=2.86 / WR=63.9% / n=204 — **sole confirmed T1**
- Sizing: 1% per mega_mutation sleeve, 0.5% per alpha sleeve
- ⚠️ last10_WR dropped to 20% — monitor

## EQUITY — earnings-beat consensus

| Ticker | Dir | Entry | TP | SL | Beats | Conf |
|--------|-----|-------|----|----|-------|------|
| MSFT | LONG | 428.08 | 465 | 410 | 7/7 | MED |
| GOOGL | LONG | 372.33 | 405 | 355 | 7/7 | MED |
| GS | LONG | 1092.74 | 1185 | 1040 | 7/7 | LOW-MED |
| AMZN | LONG | 253.91 | 275 | 240 | 6/7 | LOW-MED |

- Hold 30-60d into next earnings
- Today picks-now screener: AMZN (score 133), AVGO (128), GOOGL (121)

## ETF — dual momentum

| Ticker | Dir | Sector | 12m vs SPY | Conf |
|--------|-----|--------|-----------|------|
| XBI | LONG | Biotech | +30pp | MED |
| XLE | LONG | Energy | +20pp | MED |
| EEM | LONG | EM | +16pp | LOW-MED |

- Pilot wired: [[strategies/etf_verified_dual_momentum]] (cron 06:15Z)
- Today screener: QQQ, IWM, VGT all STRONG_BUY

## FOREX — carry + momentum

| Symbol | Dir | Entry | Conf |
|--------|-----|-------|------|
| GBPUSD | LONG | 1.33 | MED (DB_WR=59% n=114) |
| EURUSD | LONG | 1.15 | MED (RSI=33) |
| USDJPY | BUY | — | LOW-MED |

- [[strategies/fx_smart_carry_trade_momentum]] — T2 candidate (n=25, OOS-robust)

## BOND — macro + momentum

| Ticker | Dir | Conf | Notes |
|--------|-----|------|-------|
| MUB | LONG | MED | |
| EMB | LONG | MED | |
| TLT | LONG | LOW | 1.5% asymmetric bet only |

## COMMODITY — OHLCV z-score (no SHORTS)

| Symbol | Dir | Score | Conf |
|--------|-----|-------|------|
| ZC=F | LONG | 81 | RSI=28 |
| ZS=F | LONG | 81 | RSI=30 |

---

## Total Portfolio (2026-06-05 master)

19 picks / ~20.5% gross exposure (conservative book)

- 3 HIGH confidence picks
- 11 MED
- 4 LOW-MED
- 1 LOW

## Related

- [[strategies/FORWARD-TEST-QUEUE]]
- [[strategies/mega_mutation]]
- [[asset-classes/CRYPTO]]
- [[reference/performance-tiers]]
