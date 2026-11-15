# Elimination Log — how each rule and class was removed

**Agent:** buffy (Codebuff) · **Date:** 2026-11-15

---

## 1. Method: eliminate in the backtest, not in the forward account

The expensive part of strategy research is not the backtest — it is the year you spend forward-testing
something that arithmetic would have killed in an afternoon. So the order is deliberate:

1. **Stage 0 — backtest with costs and a matched-exposure benchmark.** Kill here unless the rule clears
   the gates. This is free.
2. **Stage 1 — forward test only survivors**, on a pre-registered ledger, with kill rules written before
   the first trade.

Gate order (all from `BENCHMARK_GATES.md`):

```text
1. beats_matched_benchmark   excess_ann > 0
2. ir_positive               IR > 0
3. dsr_ge_95                 deflated Sharpe >= 0.95 at the true trial count
4. oos_positive              out-of-sample excess > 0
5. is_positive               in-sample excess > 0
```

N = 8 trials declared. A rule that fails gate 1 cannot rescue itself with a good Sharpe.

---

## 2. The eight rules

| # | Rule | Result | Gate that killed it | Disposition |
|---|---|---|---|---|
| 1 | `BH_SPY` | 10.76% CAGR, DSR 0.99 | 1 (excess −0.00% — it *is* the benchmark) | **KEPT** as the baseline, not as alpha |
| 2 | `SIXTY_FORTY` | 8.11%, DSR 0.99, MDD −28.5% | 1 (−3.03%), 4 (OOS **−5.90%**) | **ELIMINATED as alpha**; legitimate as a lower-risk allocation |
| 3 | `FABER10_SPY` | 8.33%, Sharpe 0.66, MDD −21.8%, DSR 0.99 | 1 (−0.09% = its own trading cost) | **SURVIVOR** — promoted for the drawdown property, not the excess |
| 4 | `DUALMOM_2` | 7.59%, Sharpe 0.50 | 1 (−2.57%), 4 (−4.25%) | **ELIMINATED** |
| 5 | `DUALMOM_3` | 8.13%, Sharpe 0.45 | 1 (−1.88%), 3 (DSR 0.94), 4 (**+2.55% IS → −6.34% OOS**) | **ELIMINATED** — regime overfit |
| 6 | `RSI2_SPY` | 0.21%, Sharpe −0.64, exposure 0.02 | **0/5**; and −0.34% at 2× costs | **ELIMINATED** — cheapest kill in the study |
| 7 | `BTC_BH` | 51.04%, MDD −83.0% | 3 (DSR 0.65) | **ELIMINATED as a method** (it is the asset) |
| 8 | `BTC_TREND200` | 58.62%, Sharpe 1.10, MDD −63.6% | 3 (DSR 0.84) only | **SURVIVOR (conditional)** — forward-tested, not funded |

### The four equity/ETF eliminations, in one line each

- **`SIXTY_FORTY`** — profitable, Sharpe-equal to SPY, smaller drawdown; but it is a lower-beta portfolio
  measured against its own exposure, and its OOS excess is −5.90%. It is an allocation, not a strategy.
- **`DUALMOM_2`** — the 12-month SPY-vs-TLT switch has an IR of −0.177 and loses 4.25%/yr OOS. The TLT
  leg helped in 2008 and hurt in 2022; 12-month momentum cannot tell those apart.
- **`DUALMOM_3`** — the sign flip is the whole story: +2.55% IS, −6.34% OOS. Adding GLD to the menu did
  not diversify, it added a third concentrated bet.
- **`RSI2_SPY`** — 2% average exposure, 117 round trips, 0.21%/yr. It never had enough gross edge to
  cover its own carry.

### Why `BTC_BH` is not a strategy

51% CAGR over 12 years is a property of the asset, not of a method. It has a −83% drawdown and DSR 0.65.
It is the **benchmark** against which any crypto rule must justify itself, and it stays in the study only
in that role.

---

## 3. Classes eliminated before any signal was tested

| Class | Eliminated at | Reason | Re-admission condition |
|---|---|---|---|
| **FOREX** | **Data stage** | No interest-rate differentials and no swap/rollover model. Without them a "carry" backtest is spot momentum relabelled. | Supply G10 rate series + signed swap cost model; then run with cash as benchmark |
| **PREDICTION** | **Class + fee stage** | No `PREDICTION` class in the ledger (rows filed as CRYPTO), binary settlement has no TP/SL, and the taker fee is **3.5% of stake at 50¢ / 6.3% at 10¢**, peaking exactly where edge is claimed | Add `PREDICTION` class + settlement resolver + calibration capture; then maker-only, ≥200 resolved contracts |
| **COMMODITY** (as tested) | **Sample stage** | Only GLD tested, inside a 3-asset menu. A single-instrument gold timing bet is not a commodity strategy | Cross-sectional basket of 10–15 commodity instruments with roll yield modelled |
| **EQUITY** (as tested) | **Instrument stage** | Measured an index swing rule (SPY), not single-stock picks. No point-in-time universe exists here | Survivorship-free universe, 10–20 bps/side, delisting returns |
| **FUTURES** | **Scope** | No roll-yield model; a futures backtest without roll is a cash-index backtest with extra steps | Add continuous-contract construction with roll cost |
| **SPORTS** | **Scope** | 2 ledger rows; not a market with a tradable series in this repo | Not attempted |
| **MUTUAL FUND** | **Scope** | A wrapper, not a rule — SPIVA's question (does the average manager beat the index) is separate from a trading algorithm | Use fund NAV series with expense ratios included |

---

## 4. What each elimination bought

| Eliminated | Cost to eliminate | Cost if forward-tested instead |
|---|---|---|
| `RSI2_SPY` | one afternoon | ~2.5 years to reach 20 trades, at 4.5 trades/yr |
| `DUALMOM_3` | one afternoon | ~8 years at 2.49 trades/yr |
| `SIXTY_FORTY` | one afternoon | ~1 trade/yr — the forward test would *never* resolve |
| FOREX | inspected the data inventory | a year before discovering the swap model was the whole P&L |
| PREDICTION | fee arithmetic | unbounded — the class has no measurement path at all |

**The sample-size arithmetic that makes this concrete** — trades needed for a 95%-confident conclusion:

| True per-trade Sharpe | Closed trades needed |
|---:|---:|
| 0.40 | 39 |
| 0.30 | 69 |
| 0.20 | 155 |
| 0.15 | 275 |
| 0.10 | 619 |

At 1.49 trades/yr (`FABER10_SPY`), 39 trades is 26 years. **This is why the backtest is not optional**:
for slow rules, a forward test alone cannot ever conclude. Elimination must happen where the sample is
free.

---

## 5. What survives, and on what clock

| Pick | Why it survives | Forward clock | Kill rule |
|---|---|---|---|
| `FABER10_SPY` | Same Sharpe as buy-and-hold, **−21.8% vs −50.8% drawdown**, cost-pure (0.09%/yr) | slow — 1.49 trades/yr | 180d n≥8 PF<1.00 · 365d n≥20 PF<1.05 · breaker n≥10 PF<0.75 |
| `BTC_TREND200` | +7.58pp CAGR **and** +19.4pp drawdown vs BTC hold | slow — 2.47 trades/yr | same, plus target: BTC_BH drawdown −15pp at ≥80% of its return |

Full protocol: `2026-11-15_1233AM_winning-strategies/buffy/10_simulations/FORWARD_PROTOCOL.md`;
rule self-test 8/8 in `tools/forward_tracker.py`.

---

## 6. The elimination I did *not* make

I did **not** eliminate the repo's live picks. They remain `unknown`, not `rejected`: no excess-return
number has ever been computed for them, so there is no gate to fail. Calling them eliminated would be as
dishonest as calling them winners. The first thing anyone should do with the 933 EQUITY / 616 ETF /
5,584 CRYPTO rows is compute the excess column — that single field would resolve most of this study's
open questions.
