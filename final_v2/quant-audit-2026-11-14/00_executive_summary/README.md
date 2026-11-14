# Executive summary — per-asset-class profitability, final pass

**Verdict: FAIL for every asset class.** No class clears its own breakeven win rate after costs, no
class is sizing-allowed in the system's own readiness gate, and the strongest per-class result
(EQUITY, +238.3pp over 9 months) is not statistically distinguishable from zero (t=1.52, p=0.12).

## The measured table (3,500 closed picks, 2026-02-21 → 2026-11-14)

| Class | n | WR | PF | mean/trade | total | t | splithalf PF |
|---|---:|---:|---:|---:|---:|---:|---|
| CRYPTO | 1,966 | 39.3% | **0.768** | −0.426 | **−837.8** | −4.84 | 0.952 → 0.608 |
| EQUITY | 738 | 47.0% | **1.154** | +0.323 | **+238.3** | 1.52 | 1.342 → 0.977 |
| ETF | 567 | 44.3% | 1.036 | +0.040 | +22.9 | 0.34 | 1.090 → 0.971 |
| FOREX | 187 | 39.0% | **0.634** | −0.155 | −29.0 | −2.29 | 0.931 → 0.507 |
| BOND | 35 | 37.1% | 0.586 | −0.221 | −7.7 | −1.47 | — |
| COMMODITY | 7 | 42.9% | 0.604 | −0.598 | −4.2 | −0.53 | — |
| **ALL** | 3,500 | 41.7% | **0.895** | −0.176 | **−617.5** | −2.53 | — |

Every class decays from its first half to its second. None improves.

## Why each class loses — stated as a win-rate gap, not a PF

PF hides the mechanism. The binding number is the win rate each class needs versus the one it has:

| Class | avg win | avg loss | breakeven WR | after cost | actual WR | margin |
|---|---:|---:|---:|---:|---:|---:|
| CRYPTO | 3.58 | 3.02 | 45.8% | 48.8% | 39.3% | **−9.5pp** |
| EQUITY | 5.15 | 3.97 | 43.5% | 44.1% | 47.0% | **+2.9pp** |
| ETF | 2.64 | 2.02 | 43.4% | 44.5% | 44.3% | **−0.2pp** |
| FOREX | 0.69 | 0.76 | 52.5% | 55.3% | 39.0% | **−16.2pp** |
| BOND | 0.84 | 0.85 | 50.2% | 53.2% | 37.1% | **−16.0pp** |

One class is above the line (EQUITY), one sits exactly on it (ETF, −0.2pp is a coin toss), and four
are 9–16pp short. Those four cannot be fixed by better signal selection alone; their reward-to-risk
is wrong at the design level — FOREX and BOND risk more than they stand to make (avg loss > avg win).

## The one fix that moves the most money

Crypto's stops do not fill where they are placed.

- Planned risk (|entry − stop|): mean **1.919%**
- Realized loss on the same stopped trades: mean **2.990%**
- Overshoot: **+1.071pp per stopped trade**, total **+828.0pp**
- Crypto class total PnL: **−837.8pp** → the overshoot is **98.8% of the entire class loss**

`exit_price` differs from `stop_loss` in 703 of 773 stopped trades (median gap 0.324%, p90 4.43%), and
`pnl_pct` always matches one of the two (633 exit, 140 stop, 0 neither) — so this is not a formula
bug. The resolver detects the breach after the fact and records the price it found, which is a
faithful simulation of polling a stop rather than resting one at the exchange.

That fidelity is the problem: it means **every strategy's risk model is wrong by a factor of 1.56.**
A planned R:R of 1.69 becomes an effective 1.08, which raises the required win rate from 37.2% to
48.0%. Crypto's actual 39.3% would have been *profitable* against the planned R:R and is *not*
against the realized one.

Consequence, stated honestly: fixing fills does not make crypto profitable. It moves PF 0.768 →
**≈1.00** (−838pp → ≈−10pp on the same signals). Breakeven is the ceiling of that fix. Signal
selection has to do the rest.

## What the system says about itself

The payload's own honest gates agree, and are harsher:

- `readiness.by_class`: **`sizing_allowed: false` for all nine classes.**
- CRYPTO / EQUITY / FOREX status = **stressed**; ETF / COMMODITY / FUTURES / MEME = thin sample;
  BOND / PENNY_STOCK = insufficient data.
- `money_ready_verdicts` intrabar truth: CRYPTO n=3,705 PF **0.9196** WR 35.87%; EQUITY n=250 PF 0.9392;
  FOREX n=612 PF 0.6596; ETF n=45 PF **0.0216** against a daily PF of 1.8358 — an **85× inflation**.
- `slippage_validation`: average slippage as a share of average PnL — CRYPTO **39.7%**, EQUITY 16.0%,
  ETF **267%**, COMMODITY **422%**, FUTURES 72%. Three classes flagged CRITICAL.

## Bottom line for allocation

Nothing here is investable. The correct next actions are, in order: fix stop fills (moves crypto to
breakeven), impose a cost gate that kills any class whose average PnL is under 3× round-trip cost
(kills ETF and commodity intraday outright), and then run one pre-registered forward test per class
on the survivors. See `03_ideas_ranked/RANKED_IDEAS.md`.
