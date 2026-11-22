# "Best possible usage of our money" — the documented verdict, 2026-11-22

**Question:** if the desk cannot prove an edge in a class, what should the money
actually do? This is the answer we can defend from measurement, plus an explicit
list of what would change it. It is a research conclusion, not personal financial
advice; a human decides their own risk capacity.

---

## 1. What we can prove today

**No trading strategy in this repo has forward evidence.** 34 pre-registered
cells across 10 classes: one (EQUITY `xsmom_top3_6m`, H-201) clears every backtest
gate, and it has **zero closed forward trades**. G8 requires n ≥ 100. COMMODITY is
unmeasurable (roll-contaminated series); PEAD is under-powered (13 events).

**Buy-and-hold beat everything we could construct**, on the same 20-year window
(2006-11-22 → 2026-11-20, yfinance auto-adjusted closes, my own run):

| allocation | window | CAGR | max drawdown | $10k becomes |
|---|---|---|---|---|
| SPY buy & hold | 20.0 y | **10.27 %** | −55.2 % | **$70,557** |
| AOA (80/20 global) | 18.0 y (2008 start) | 9.79 % | −28.4 % | $53,815 |
| 60/40 SPY-AGG, monthly | 20.0 y | 7.79 % | −34.7 % | $44,839 |
| SPY + 200-day trend overlay | 20.0 y | 8.37 % | **−20.5 %** | $49,879 |
| GIC 3.5 % guaranteed | 20.0 y | 3.50 % | 0 % | $19,894 |

The trend overlay costs **1.9 points of CAGR** and removes **35 points of drawdown**.
That is the only trade in the table with a measured justification: it is paid for
in return, not hoped for.

## 2. Reconciliation with the peer verdict (Mercury3, 2026-11-22)

Their headline — *GIC $19,826 vs SPY $64,237 vs SPY+10m-SMA $59,923 (MaxDD −19.5 %
vs −50.8 %); AOA 10.33 % > SPY 10.01 %; NO alpha in any class; 0 forward obs, so
nothing sanctioned* — **agrees with ours in direction and in the GIC number**
(3.5 % over 20 y = $19.9k either way). Three specifics do not reproduce exactly:

| claim | theirs | mine | note |
|---|---|---|---|
| SPY terminal value | $64,237 | $70,557 | different end date/adjustment; direction same |
| SPY max drawdown | −50.8 % | −55.2 % | daily close vs month-end |
| SPY + trend | $59,923 / −19.5 % | $49,879 / −20.5 % | 10-month SMA vs my 200-day; their version is better, worth checking |
| 60/40 + trend leg | Sharpe 1.011 / −11.3 % | plain 60/40 is **−34.7 %** | their −11.3 % must include the trend leg; plain 60/40 does not do that |
| AOA vs SPY CAGR | 10.33 vs 10.01 | 9.79 vs 10.27 | AOA series starts 2008, so it never eats the GFC drop in its own history — window artifact |

None of these change the conclusion; two of them (the trend-overlay result and the
60/40 claim) should be re-derived on one shared script before anyone repeats them.

## 3. The decision framework

Three buckets, each with a stated cost:

1. **Guaranteed (GIC / T-bills).** 3.5 % nominal, zero drawdown, inflation risk.
   This is the floor, not a strategy. Over 20 years it finishes at ~28 % of SPY's
   terminal value.
2. **Broad beta (SPY / AOA / 60-40).** Highest measured terminal value. The price
   is a drawdown the holder must actually survive: −55 % for SPY, −28 % for AOA.
   AOA is the better *risk-adjusted* default for someone who cannot sit through
   −55 %, but its "beats SPY" claim is window-dependent.
3. **Beta + trend overlay.** ~8.4 % CAGR with ~−20 % drawdown. The only
   risk-reduction we can defend with numbers, and it is honest about its cost.

**Our answer, stated plainly:** with zero forward evidence, the defensible default
is *broad beta sized to the holder's drawdown tolerance*, with a trend overlay if
−55 % is unacceptable, and a guaranteed bucket for money that cannot be drawn down.
**No desk strategy is sanctioned for real capital today** — including H-201, which
is a promising backtest and nothing more until it has 100 closed forward trades.

## 4. What would change this verdict

- **H-201 forward pod** (live since 2026-11-22, AAPL/MSFT/JNJ, SPY leg): if it
  reaches n ≥ 100 closed with net PF ≥ 1.1, CI-LB > 0 and positive excess vs SPY,
  it earns a **satellite** allocation, not a replacement of beta. Its backtest
  excess was +5.78 bps/day over SPY — large enough to matter, unproven.
- **Commodity repair** (roll-adjusted continuous contracts): currently the class
  is unmeasurable, so "0.165 PF" must not be quoted either way.
- **PEAD with 40+ quarters of surprises** (SEC XBRL): our proxy fails on a regime
  artifact, not on the anomaly.
- **Anything with n ≥ 196 and μ ≥ 0.2 R gross** that clears G2+G3 — the project
  plan's concession clause.

## 5. Text > brain

The failure mode this document exists to prevent: inventing a reason to trade
because the desk exists. Twenty years of data say the market pays ~10 % a year for
sitting still and surviving a −55 % drawdown. Until something here beats that with
forward evidence, the correct action is to hold the index (or the GIC), keep the
research running, and say so out loud.
