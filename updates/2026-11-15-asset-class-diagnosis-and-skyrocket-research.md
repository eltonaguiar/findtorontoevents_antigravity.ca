# 2026-11-15 — Why the audit shows no profitable asset class, and what actually predicts winners

Three analyses, all with code and numbers:

| Tool | Question | Output |
|---|---|---|
| `tools/asset_class_forensics.py` | Is any class profitable, and is the headline honest? | per-class ledger stats, last-100 window, exit/direction breakdown |
| `tools/weekly_winner_reverse_engineer.py` | Can anything known on Friday rank next week's winners? | `reports/weekly_winners_2026-11-15.md` |
| `tools/hours_skyrocket_reverse_engineer.py` | Can anything known at an hourly bar precede a move within 4 hours? | `reports/skyrocket_patterns_2026-11-15.md` |

---

## 1. The headline is not the ledger

`dashboard_data.json` summary says `total_pnl_pct = -11.96` next to `total_pnl_pct_sum_raw = 1653.11`.
`data/dashboard_payload.json` shows it explicitly:

```
total_pnl_pct                    : -45.04
total_pnl_pct_sum_raw            : 1035.25
total_pnl_pct_compounded_ew      : 1631.88   <- whole ledger
total_pnl_pct_compounded_rolling_100 : -45.04  <- what the dashboard displays
```

`audit_trail/dashboard_generator.py:16911` sets `"total_pnl_pct": total_pnl_pct_compounded_rolling_100`.
**The headline number on the dashboard is the last 100 trades**, not the strategy's history. A good system that just had
a bad week reads as "no profitable asset class". This alone explains most of the impression.

## 2. When it *is* the ledger, the losses have a mechanism

Forensics on the largest closed ledger with numeric P&L (`ai_tournament_picks_latest.json`, 2,242 picks):
overall **WR 46.3%, mean −0.94%/trade, PF 0.77, compound −99.7%**.

| class | n | WR | mean | PF | last-100 compound | last-100 WR |
|---|---|---|---|---|---|---|
| CRYPTO | 637 | 37.5% | −4.15% | 0.57 | **−98.4%** | 25% |
| BOND | 546 | 56.0% | +0.88% | **1.79** | **+3,955%** | 72% |
| EQUITY | 288 | 36.8% | −0.36% | 0.89 | +26.9% | 42% |
| COMMODITY | 262 | 48.1% | +0.86% | 1.38 | −5.9% | 42% |
| FOREX | 262 | 50.8% | −0.10% | 0.87 | +31.5% | 64% |
| ETF | 191 | 55.5% | +0.61% | 1.46 | +140.1% | 62% |
| PENNY | 38 | 34.2% | −4.16% | 0.62 | −69.6% | 34% |

Four concrete causes:

1. **Stop losses are 3x wider than they look.** Crypto `SL_HIT_REPLAY` n=373 mean **−16.0%**, `TP_HIT_REPLAY` n=230 mean
   **+14.8%** — and the worst recent trades are −43% to −49% (NEARUSDT, SOLUSDT, LINKUSDT). With a ~16% average loss vs a
   ~15% average win, a 38% win rate cannot survive.
2. **The direction model is inverted in two classes.** CRYPTO **LONG hit 27.0% vs SHORT 60.9%**; ETF **LONG 84.5% vs
   SHORT 10.7%**. Both are one-line fixes worth more than any new strategy: stop crypto longs in a down-trending tape, and
   stop ETF shorts entirely.
3. **The one profitable class is already there.** BOND: 546 picks, 56% WR, PF 1.79, +480 raw, last-100 **+573%**. It is
   excluded from the "look at our trading" conversation because bond returns are unexciting, but it is the only class with
   a positive expectancy large enough to survive costs.
4. **Two thirds of the closed ledger never reaches the stats.** `total_closed_picks 14,627` but `valid_closed_picks 7,547`,
   with `integrity_excluded 6,126` and `auto_expired_excluded 7,338`. Whatever those filters remove is not random, and
   nothing on the dashboard says which side of the ledger they came from.

Also: CRYPTO P&L is concentrated — `honest_label` in the payload reads *"CRYPTO edge = luxalgo_confluence on JUPUSDT
(11% of class PnL)"*, with the top strategy at 55.5% of class P&L. When that one strategy cools, the class reads dead.

## 3. This week's real winners, per class

Crypto (CoinGecko top-250 mcap, 7d): **AKE +78.3%, OZO +65.0%, PIEVERSE +26.6%, KITE +24.2%, NIGHT +24.0%**.
Equity: **ABNB +15.6%, JD +13.4%, RIVN +11.9%, BABA +11.6%, AMZN +7.9%**.
ETF: **GDX +13.6%, GDXJ +13.5%, TAN +13.4%, KWEB +9.4%, ICLN +7.4%**.
Commodity: **PL +7.0%, SI +5.5%, GC +4.5%, NG +3.5%, PA +3.0%**.
FX: **USDCHF +2.5%, USDCAD +1.7%, USDJPY +1.5%**. Bond: **MUB +1.0%, ZB +0.8%, BNDX +0.7%**.

The winners are *not* the names the audit holds — the audit's crypto book was long alts (ICP, FET, ARB), the week's
leaders were small caps and a fresh listing. That gap is the actual product problem, not a modelling one.

## 4. Weekly horizon: what has real lift (104 weeks, walk-forward)

Model = z-score sum of the two most stable features, fitted on the first 52 weeks, scored on the next 52 unseen weeks.

| class | model | test precision (top 5) | base rate | lift |
|---|---|---|---|---|
| **ETF** | `sma200_dist` + `ret3m` | 38.8% | 21.6% | **1.80x** |
| **BOND** | `dollar_vol` + `sma200_dist` | 29.6% | 23.1% | **1.28x** |
| **COMMODITY** | `vol1m` + `dist52` | 29.6% | 23.8% | **1.24x** |
| EQUITY | `dollar_vol` + `volratio` | 21.9% | 20.3% | 1.08x |
| CRYPTO | `dollar_vol` + `vol1m` | 21.5% | 21.6% | 1.00x |
| FOREX | `ret1m` + `ret1w` | 25.0% | 27.3% | 0.92x |

Read: **trend persistence works where the universe is slow** (sector/thematic ETFs above their 200-day, long-horizon
winners) and **nowhere else**. Crypto weekly momentum is a coin flip, and FX momentum is worse than a coin flip. It also
means the ETF book should be the flagship, and the forex book is a cost sink.

## 5. Hours horizon: the honest answer is "not from technicals"

324,581 hourly bars, 46 tickers, 2 years. Label: 4-hour forward move ≥ 1.5x the ATR% at the signal bar. Base rate 14.5%.

| pattern | test precision | lift |
|---|---|---|
| breakout + ATR squeeze | 17.9% | 1.33x |
| oversold snap (RSI<30) | 17.7% | 1.32x |
| 20-bar breakout | 17.2% | 1.28x |
| breakout + volume >1.5x | 16.4% | 1.22x |
| gap up >1% | 8.9% | **0.66x** |
| pullback in uptrend | 10.6% | 0.79x |

Logistic model on 12 features: **test AUC 0.542**, top-1% precision 14.4% vs 13.4% base (**1.07x**). Weights are tiny
(|w| ≤ 0.10) and half have the "wrong" sign. Translation: **generic OHLCV technicals barely rank hours-scale spikes.**
Chasing gap-ups is actively bad. The only durable effects are volatility contraction before expansion, and oversold
mean-reversion.

What is *not* in the feature set — and almost certainly where the signal lives: catalyst events (news, filings, offering
completions, halt resumptions), unusual options flow, short interest / borrow availability, float rotation, social
velocity, and level-2 imbalance. No amount of feature engineering on hourly candles substitutes for those.

## 6. Can REA reverse-engineer stock skyrockets?

No. REA (`morluto/rea`) is an MCP for reverse-engineering **software**: native binaries, Electron/JavaScript, .NET
assemblies, websites. It answers "how does this app's feature work", not "which stock goes up". Price series are data, not
programs, so there is nothing for it to disassemble.

Where it *is* useful for this project: pointing it at a scanner platform or a broker app to learn which fields and screens
produce their momentum lists, and at your own dashboard bundles when the JS does something you can't explain. That is
debugging infrastructure, not alpha.

Repos that genuinely target the hours-scale problem (verified from search, not memory):

- **tradytics/surpriver** — anomaly detection + ML on volume/price to find big movers *before* they move. Closest match to
  the ask; 1.9k stars, includes feature generator and detection engine.
- **VladPetrariu/Qullamaggie-breakout-scanner** — pre-market scan of ~2,300 NYSE/NASDAQ names: ATR compression, volume
  burst half-life, relative strength vs universe, breakout-level classification. Free data, no keys.
- **abdza/momentumscreener** — TradingView screener API, re-scans every 2 minutes for volume climbers and price spikes
  (real-time rather than backtest-only).
- **sam-bateman/trading-orb** — ORB on 10 years of 5-minute bars; the finding worth stealing is that a 1.2x relative-volume
  filter on the breakout bar was the single most important component.
- **solste7en/strategy-research** — intraday framework with ORB / VWAP / volume-surge strategies and walk-forward.
- **dng-nguyn/mnq-intraday-momentum-backtest** — a clean negative result on the Gao et al. intraday momentum paper; useful
  as a methodological counterweight to anyone promising a 4-hour edge.

## 7. What to do next, in order of expected value

1. Show the whole-ledger compound next to the rolling-100 headline, so a bad week can't masquerade as a dead system.
2. Fix the two inverted direction books (crypto longs, ETF shorts) — measurable within days, no new research.
3. Promote BOND to a first-class book (it is the only class with PF > 1.7 and a positive last-100), and keep ETF trend as
   the second.
4. Retire FOREX (0.92x, worse than chance) and PENNY (−4.16%/trade).
5. Only then chase hours-scale spikes — with catalyst/flow data, not more candle features.
