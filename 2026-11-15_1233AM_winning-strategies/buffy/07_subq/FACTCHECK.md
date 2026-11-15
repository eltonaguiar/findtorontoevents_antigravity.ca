# 07 — SubQ Run 2: Prediction Markets, Benchmarks, and Fees

**Date:** 2026-11-15 · **Endpoint:** `POST api.subq.ai/v1/systemone` · **Model:** `subq-snap-1.2`
**Arms:** 2 × 8 questions = 16 decisions, both HTTP 200
**Raw:** `subq_run_20261115T003430Z.json` · **Reproduce:** `python3 tools/subq_consult.py --questions ...`

---

## 1. Results

| Question | Prior | With evidence | Δ | My position | Verdict |
|---|---|---|---|---|---|
| `prediction_market_viable_class` | 0.029 | 0.036 | +0.007 | Not viable as a taker class | Grounded (prior already right) |
| `pm_copy_trading_wins` | 0.0071 | **0.0015** | −0.0056 | Structurally negative | **Strongly grounded** |
| `pm_should_be_own_class` | 0.990 | **0.9995** | +0.009 | Yes — no class exists today | **Confirms my diagnosis** |
| `benchmark_gate_required` | 0.979 | **0.992** | +0.013 | Yes, mandatory | **Confirms your gap** |
| `active_mf_beats_index_20y` | 0.0036 | 0.0016 | −0.002 | SPIVA: 92.89% trail | Grounded |
| `low_cost_fund_allocation_wins` | 0.9986 | 0.9992 | +0.001 | ~90% of 10y windows positive | Grounded |
| `fee_kills_coinflip_edge` | 0.994 | 0.996 | +0.002 | 3.5% of stake at 50¢ | Grounded |
| `best_next_target` | NONE 0.651 | NONE 0.460, **FOREX 0.303**, EQUITY 0.190 | — | **I say EQUITY first** | **Disagreement** |

---

## 2. What this run establishes

**2.1 It confirms the prediction-market diagnosis, including the part I derived independently.**
`pm_should_be_own_class` at **0.9995** is the strongest single probability in either SubQ run. The model
agrees that a class which is never recorded can never be verdicted — the structural reason there are no
winners.

**2.2 It confirms your benchmark critique.** `benchmark_gate_required` at **0.992** endorses making
"beat buy-and-hold net of costs" a mandatory gate, which is exactly the gap you identified in my previous
metrics doc.

**2.3 It separates the two mutual-fund claims correctly** — and this is the cleanest result of the run:

- `active_mf_beats_index_20y` = **0.0016** (will not beat the index)
- `low_cost_fund_allocation_wins` = **0.9992** (allocation will be positive)

Those two numbers side by side *are* the answer to "mutual funds would be winners given enough time":
the wrapper wins, the active manager does not. The model reproduced the distinction without being told
which answer I preferred.

**2.4 Fee arithmetic is decisive.** `fee_kills_coinflip_edge` = **0.996**: at 3.5–6.3% of stake, small
forecasting edges do not survive as a taker.

---

## 3. The disagreement — and why I keep my position

With evidence, SubQ shifts the "best next target" from `NONE` toward **FOREX (0.303) above EQUITY
(0.190)**. Confidence also *fell* (0.58 → 0.35), which is at least honest behaviour: more data made it
less decisive.

**Why I still put EQUITY first:**

| | EQUITY | FOREX |
|---|---|---|
| Verified marks | **738** | 158 |
| Contamination | 12% | 56% |
| Round-trip cost | 5–10 bps | 10–20 bps |
| Measured PF | 1.15 | 1.16 |
| Sharpe/trade | 0.054 | **0.061** |

SubQ is likely weighting the better per-trade Sharpe. I weight **sample size and cost ratio**: 738
verified marks vs 158, and FX needs to overcome a 10–20 bps spread with an edge measured in single-digit
bps. More importantly, EQUITY has a named benchmark (SPY) and a pre-existing strategy, so the test is
cheap.

**This is a genuine disagreement, not a rounding difference.** If FOREX's known-bad rows are quarantined
and PF survives above 1.3 net, SubQ was right and I was wrong — that is precisely the test A4 is
assigned to run.

---

## 4. Method limits (unchanged from run 1)

- Decisions API returns **no reasoning text**; only behavioural deltas are checkable.
- On 5 of 8 questions the prior was already the correct answer, so agreement is weak evidence.
- Two arms, not three — the pressure/sycophancy test was run in the previous package and is not repeated
  here. The known finding stands: assertion moves `equity_reliably_profitable` ~2.5× while
  `deploy_today` stays flat.
- SubQ **cannot** discover the 48% forged rows or the missing PREDICTION class; it can only agree once
  told. It is a cheap second opinion with a documented bias, not evidence.

---

## 5. Bottom line

**SubQ independently lands on: prediction markets need their own class (0.9995), copy trading loses
(0.0015), benchmarks must be mandatory (0.992), active funds lose to the index (0.0016) while low-cost
allocation wins (0.9992), and fees kill coin-flip edges (0.996).** It disagrees with me on whether FOREX
or EQUITY should be attempted first — and that disagreement is now a scheduled experiment (A4 vs A1),
which is the correct way to resolve it.
