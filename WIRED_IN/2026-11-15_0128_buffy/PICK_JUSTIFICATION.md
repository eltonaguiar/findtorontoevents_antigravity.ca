# Pick Justification

**Agent:** buffy (Codebuff) · **Date:** 2026-11-15
**Subject:** what I am picking, and why that and nothing else

---

## 1. The pick in one line

> **`FABER10_SPY` — hold SPY while the month-end close is above its 10-month SMA, otherwise hold T-bills.**
> It is the only rule in this study that survives with a defensible purpose. Its purpose is **drawdown
> reduction at approximately zero return cost**, not return enhancement.

Second, conditional and **not** recommended for capital:
**`BTC_TREND200` — hold BTC while it is above its 200-day SMA.** Best risk-adjusted result in the study,
but DSR 0.84 and 12 years of one asset is not enough evidence to fund it.

---

## 2. What I am explicitly NOT picking

| Thing | Why not |
|---|---|
| The repo's live picks (any asset class) | No excess-return number has ever been computed for them. Unknown ≠ positive. |
| `DUALMOM_2` / `DUALMOM_3` | Excess −2.57% / −1.88%; `DUALMOM_3` flips from +2.55% IS to −6.34% OOS |
| `SIXTY_FORTY` as a strategy | −3.03% excess, −5.90% OOS. It is a lower-beta portfolio, not alpha. |
| `RSI2_SPY` | −0.64 Sharpe, 2% average exposure, −0.34% CAGR at 2× costs |
| `BTC_BH` as an "edge" | 51% CAGR is the asset, not a method; −83% drawdown, DSR 0.65 |
| Prediction markets | Fee of 3.5–6.3% of stake as a taker, and no `PREDICTION` class to measure |
| FOREX | No rate-differential data and no swap model → not measurable honestly |

---

## 3. Why `FABER10_SPY` and not buy-and-hold

Buy-and-hold SPY has the higher CAGR — 10.76% vs 8.33%. On return alone, buy-and-hold wins and the
overlay loses. The case for the overlay rests on the shape of the path:

| Metric | BH_SPY | FABER10_SPY | Winner |
|---|---:|---:|---|
| CAGR | 10.76% | 8.33% | BH |
| Sharpe | 0.65 | **0.66** | FABER (tie, +0.01) |
| Max drawdown | −50.8% | **−21.8%** | **FABER, +29.0pp** |
| Return per unit of drawdown | 0.212 | **0.382** | **FABER, +80%** |
| Excess vs matched exposure | −0.00% | −0.09% | BH (by 9 bps) |
| DSR | 0.99 | 0.99 | tie |
| Max drawdown at 2× costs | −50.8% | −22.1% | FABER |

The 2.43pp CAGR gap is largely **cash drag by design**: the rule is out of the market 22% of the time
(average exposure 0.78). If you want buy-and-hold's return, hold buy-and-hold; if you cannot tolerate a
−50% drawdown, this rule converts it into a −22% drawdown for 0.09%/yr in trading costs. That is a real
trade, honestly priced, and it is the only thing in this study I would defend in front of someone
putting up money.

**The arithmetic that proves the cost is the only cost:** 33 switches × 6 bps = 1.98% total, ÷ 22.08
years = **0.0897%/yr** — exactly the −0.09% excess. Nothing else is being lost.

---

## 4. Why `BTC_TREND200` is second, and conditional

| Metric | BTC_BH | BTC_TREND200 |
|---|---:|---:|
| CAGR | 51.04% | **58.62%** |
| Sharpe | 0.93 | **1.10** |
| Max drawdown | −83.0% | **−63.6%** |
| DSR | 0.65 | 0.84 |
| Average exposure | 1.00 | 0.64 |

Higher return *and* 19.4pp less drawdown on two-thirds the exposure is the strongest single result here.
It is still conditional because:

1. **DSR 0.84 < 0.95** after correcting for 3 daily-frequency trials.
2. **12.13 years, one asset, one boom-bust cycle.** The bull leg dominates the result.
3. The excess vs SPY (+47.69%) is crypto beta and must never be quoted as skill.
4. 30 round trips over 12 years means the evidence rate is slow: proving it forward takes ~8 years at
   2.5 trades/yr.

If forced to choose one crypto position today, this is the rule I would use and `BTC_BH` is the
alternative I would benchmark it against — drawdown, not return.

---

## 5. Live parameters (copy-paste)

```text
FABER10_SPY
  universe:   SPY (adjusted close), monthly
  signal:     close > mean(close[-10:])   at month-end
  weight:     1.0 long / 0.0 T-bills
  rebalance:  month-end, act next month
  costs:      6 bps/side
  kill:       180d & n>=8 & PF<1.00 | 365d & n>=20 & PF<1.05 | breaker n>=10 & PF<0.75

BTC_TREND200
  universe:   BTC-USD daily
  signal:     close > SMA(200)
  weight:     1.0 long / 0.0 T-bills
  rebalance:  daily signal, at close
  costs:      15 bps/side
  kill:       same slow clock; target = BTC_BH drawdown −15pp at ≥80% of its return
```

```bash
python3 tools/forward_tracker.py log --strategy FABER10_SPY --symbol SPY \
  --entry 512.40 --exit 540.10 --qty 10 --fees 3.20 \
  --opened 2026-11-02 --closed 2027-01-04
python3 tools/forward_tracker.py status
```

---

## 6. What would falsify this pick

| Falsifier | Threshold |
|---|---|
| Forward drawdown reduction disappears | FABER forward MDD > 70% of BH's over ≥ 39 months |
| Cost per switch is higher than modelled | measured cost > 12 bps/side (would make excess ≈ −0.18%/yr) |
| The overlay stops tracking the signal | ≥ 2 missed monthly signals, or a switch executed > 5 trading days late |
| Whipsaw regime dominates | PF < 1.00 at 180 days with n ≥ 8 (pre-registered kill) |
| Tax drag | monthly switches in a taxable account make the 0.09% cost several times larger — this rule is only rational in a tax-sheltered account |

---

## 7. Allocation

**Now: 0%.** Nothing in this folder is forward-verified, and the repo's standing status is NO-GO for
real capital. The honest recommendation is that a person who wants exposure should buy a low-cost index
fund and, if they cannot tolerate the drawdown, apply the 10-month SMA overlay in a tax-sheltered
account as a *risk control* — with the expectation of tracking, not beating, the index over a full cycle.
