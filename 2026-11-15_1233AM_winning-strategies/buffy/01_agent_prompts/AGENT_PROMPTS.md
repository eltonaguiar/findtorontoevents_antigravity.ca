# Agent Prompt Pack — Finding a Strategy That Actually Wins

**Date:** 2026-11-15 · **Author:** Buffy
**Use:** one prompt per agent, one machine/worktree each. Copy the **preamble** into every prompt, then
append the agent's assignment. They are written to be self-contained — an agent on another machine
cannot see this conversation.

---

## 0. Before you dispatch anything

Read this once. It is the difference between eight agents producing a verdict and eight agents producing
eight more dashboards.

| Problem | Rule that prevents it |
|---|---|
| Every agent re-tests the same idea | **One assignment per agent, non-overlapping.** A1–A5 are 5 different classes/mechanisms |
| Multiple testing inflates results | **One pre-registered hypothesis per agent.** Declare the trial count |
| Agents "improve" shared code and collide | Agents write **only** under `results/<agent_id>/` and their own new files |
| Everyone reports PF and calls it profit | **Every result must beat a matched-exposure benchmark, net of costs** |
| Unmarked ledger produces fake edges | Agent **A6 must land before A1–A5 report numbers** |
| Nobody believes the winners | Agent **A7 red-teams** every claimed win |

---

## 1. The bar: what "REALLY works" means

A strategy is a **WIN** only if all ten hold. Anything less is a candidate, not a win.

1. **Beats its benchmark**, at matched exposure, **net of costs** (`EDGE > 0`).
2. `verified_n ≥ 100`, across **≥3 distinct months**.
3. **Intrabar-validated** outcomes (not daily-close optimism).
4. **Out-of-sample**: two disjoint halves, both positive.
5. **Deflated Sharpe ≥ 0.95** at the true trial count.
6. **Kelly > 0** and risk of ruin **< 5%** at intended size.
7. **Down-capture < 100** and capture ratio > 1.0.
8. Robust to **2× assumed costs**.
9. **Forward paper**: ≥30 round trips or ≥90 days, live prices, before any capital.
10. **A pre-committed kill rule** written *before* the test.

> "If I gave you money and paper traded, you'd win again and again" = items 9 + 10, not a backtest.

---

## 2. Shared preamble — paste at the top of every agent prompt

```text
ROLE
You are a quantitative research agent. Your job is to determine whether ONE specific
strategy has a real, after-cost, benchmark-relative edge - and to say NO clearly if it
does not. A well-evidenced NO is a successful outcome. A false YES is the worst possible
outcome and will be treated as a failure.

REPO
findtorontoevents_antigravity.ca. Work in your OWN worktree/branch. Never edit files
outside results/<your_agent_id>/ unless your assignment explicitly names them. Never
`git push` files you did not create. Never run git reset --hard, git clean -fd, or
git push --force.

READ FIRST (in this order)
1. docs/STRATEGY_FAILURE_ANALYSIS_FRAMEWORK.md  - the five failure pillars
2. 2026-11-15_1227AM_profitability/buffy/01_plan/PER_ASSET_CLASS_PLAN.md
3. 2026-11-15_1233AM_winning-strategies/buffy/03_benchmark_relative/BENCHMARK_GATES.md
4. 2026-11-15_1233AM_winning-strategies/buffy/01_agent_prompts/results_schema.json

HARD RULES
- Do NOT trust the existing ledger. It is 48.1% forged: 3,350 of 6,968 closed rows have
  exit_price == entry_price. Any number computed over unmarked rows is invalid.
- Do NOT compute a win rate on `status IN ('WON','LOST')` alone. TIME_EXIT and EXPIRED
  are non-wins. TP_HIT counts as a win only if pnl_pct > 0.
- Do NOT add strategies to test. You are testing ONE hypothesis.
- Do NOT tune parameters after seeing out-of-sample results. If you tune, that is a new
  trial - increment the trial count and say so.
- Do NOT report PF or Sharpe without also reporting the benchmark comparison.
- Do NOT report a result computed on fewer than 100 verified marks as a WIN.

DEFINITION OF DONE
Either (a) a WIN meeting all ten gates in BENCHMARK_GATES.md section 6, with the
artefacts to prove it, or (b) a NO with the specific gate that failed and the number
that failed it. Both must be written to results/<agent_id>/REPORT.md and
results/<agent_id>/result.json matching results_schema.json.

KILL RULE
Before you start, write the falsifier: "This is dead if <metric> < <threshold> at
n >= <N>." Put it at the top of REPORT.md. Do not change it afterwards. If the test
fails the falsifier, declare NO and stop - do not continue looking for a variant that
passes. That is how false positives are manufactured.
```

---

## 3. Coordination map

```
        A6  LEDGER REPAIR  ──────────────► must land first (blocks A1–A5)
                    │
        A0  BENCHMARK HARNESS ───────────► build once, shared by A1–A5
                    │
   ┌────────┬───────┴───────┬──────────┬─────────────┐
   A1       A2              A3         A4            A5
 EQUITY    ETF            CRYPTO     FOREX      PREDICTION MKTS
   └────────┴───────┬───────┴──────────┴─────────────┘
                    ▼
        A7  RED TEAM ──► attacks every claimed WIN, tries to falsify it
```

Dispatch order: **A6 and A0 in parallel → then A1–A5 in parallel → then A7.**
Do not run A1–A5 before A0 exists, or five agents will each build an incompatible benchmark.

---

## 4. A6 — Ledger repair (blocking)

```text
ASSIGNMENT A6 - LEDGER REPAIR (BLOCKING; the other agents depend on this)

Fix the outcome resolver so a closed row always carries a real mark.

1. In alpha_engine/outcome_resolver.py, find the TIME_EXIT branch that writes
   exit_price = entry_price and pnl_pct = 0. Replace it with: fetch the close at
   t_exit (intraday first for futures, daily close otherwise), compute
   pnl_pct = direction_sign * (exit - entry) / entry * 100, set exit_price,
   set closed_at. If price data is unavailable, set status='EXPIRED' - never 0.
2. Promote TP_HIT -> WON and SL_HIT -> LOST at resolve time, so aggregates that filter
   status IN ('WON','LOST') stop silently dropping wins. Note: this may surface 100+
   hidden wins; report the count before and after.
3. Write a one-shot backfill: tools/backfill_time_exit_marks.py with --dry-run default.
   Target the 3,350 rows where exit_price = entry_price. Report how many were repairable
   vs had no price data.
4. Verify with tools/pnl_zero_validator.py (already exists; it exits 1 today) and
   tools/asset_class_measurability.py. Target: <1% forged rows per class.
5. Add pnl_zero_validator to a GitHub Actions workflow as a blocking check.

OUTPUT: results/A6/REPORT.md with before/after counts per class, and the dry-run CSV diff.
ACCEPTANCE: forged rows drop from 3,350 to under 1% of closed rows; no class loses marks.
```

---

## 5. A0 — Benchmark harness (build once)

```text
ASSIGNMENT A0 - BENCHMARK HARNESS

Build ONE reusable module that computes benchmark-relative performance, so A1–A5 do not
each reinvent it.

1. New file: tools/benchmark_relative.py
   - Input: a returns series (list of period returns) + benchmark returns + avg net exposure.
   - Output JSON with: annualised return, benchmark return at MATCHED exposure, excess,
     beta, Jensen's alpha + t-stat, information ratio, tracking error, up-capture,
     down-capture, capture ratio, batting average, M-squared, max drawdown (compounded).
2. Benchmark series: SPY total return (monthly) for EQUITY/ETF; BTC for CRYPTO; T-bill
   (13-week) for FOREX; AGG for BOND. Fetch from Yahoo chart API (already used elsewhere in
   this repo) and cache to data/benchmarks/*.csv with a date stamp.
3. Matched exposure: compute mean(abs(weight)) over the series; build the benchmark as
   exposure*benchmark + (1-exposure)*cash. Print both matched and unmatched numbers so the
   difference is visible.
4. Unit-test it: tools/tests/test_benchmark_relative.py, 6+ deterministic cases including
   a strategy identical to the benchmark (must return excess ~0, IR ~0, beta ~1).

OUTPUT: results/A0/REPORT.md + the module + tests passing.
ACCEPTANCE: `python3 -m pytest tools/tests/test_benchmark_relative.py -q` passes.
```

---

## 6. A1 — EQUITY: RSI-2 vs SPY

```text
ASSIGNMENT A1 - EQUITY MEAN REVERSION vs SPY

Hypothesis (pre-register in reports/hypothesis_registry.json before any backtest, rule M-107):
"Connors RSI-2 pullback on large-cap US equities produces positive excess return versus
SPY total return at matched exposure, net of 8 bps round-trip cost."

1. Strategy already exists: alpha_engine (stocks_rsi2_pullback). Do NOT rewrite it. Read it.
2. Universe: liquid US large caps, point-in-time, survivorship-free. State exactly how you
   handled delisted names - if you did not, say so and treat results as optimistic.
3. Ledger: 738 verified EQUITY marks exist. Use ONLY rows with a real mark (exit != entry).
4. Run the A0 harness: excess vs SPY, IR, alpha t-stat, down-capture, capture ratio.
5. Cost sensitivity: rerun at 8 bps and at 16 bps. If it dies at 16, say so.
6. Intrabar check: use tools/reresolve_intrabar.py; report how many TP_HIT become SL_HIT.

FALSIFIER (write it first): dead if excess <= 0 at n >= 100 verified, or IR < 0.5.
OUTPUT: results/A1/REPORT.md + result.json.
NOTE: this class was killed once at n=10 and revived at n=78. n=10 is not evidence - do not
repeat that error in either direction.
```

---

## 7. A2 — ETF: 200-day trend vs buy-and-hold

```text
ASSIGNMENT A2 - ETF TREND vs BUY AND HOLD

Hypothesis (pre-register): "A 10-month/200-day SMA trend rule on a small set of broad ETFs
beats buy-and-hold of the same ETFs net of 3 bps, with lower max drawdown, over 2010-2026."

This rule does NOT exist in this repo (361 strategies, none implement it). You are adding one.

1. Universe: SPY, QQQ, IWM, TLT, GLD. Monthly bars, 2010-2026.
2. Rule: hold when close > 200-day SMA, else cash. Rebalance monthly. No parameter search -
   if you try other lookbacks, that is a new trial and you must report all of them.
3. Benchmark: buy-and-hold the SAME basket at matched average exposure, via A0 harness.
4. Report: excess, IR, max drawdown vs benchmark, down-capture, turnover, and the 2008-style
   stress (use 2020 COVID crash as the in-sample stress event).
5. Also test the honest null: equal-weight buy-and-hold. If trend only wins by taking less
   risk, say that - it is a real finding, not a failure.

FALSIFIER: dead if excess <= 0 at matched exposure, or max drawdown is not lower than
buy-and-hold's.
NOTE: ETF has the cleanest ledger in the system (2% contamination, 566 verified marks) and
still shows PF 1.04. That is the strongest negative in the repo - respect it.
OUTPUT: results/A2/REPORT.md + result.json + the new strategy file with a Wiring Plan.
```

---

## 8. A3 — CRYPTO: funding carry vs BTC hold

```text
ASSIGNMENT A3 - CRYPTO FUNDING CARRY vs BTC

Hypothesis (pre-register): "Perp funding-rate carry (short perp / long spot when funding is
in the top decile) produces positive excess return versus BTC buy-and-hold, net of 25 bps
round-trip and funding P&L."

1. Data: funding rates + spot/perp prices. The repo has alpha_engine/funding_rate_arb.py -
   read it first; do not duplicate its logic, reuse and audit it.
2. Benchmark: BTC buy-and-hold (the honest alternative). ALSO report versus T-bill cash,
   because a market-neutral carry trade should be judged against cash, not BTC.
3. CRITICAL: net funding P&L must be included, not just price P&L. A carry trade that
   ignores funding is meaningless.
4. Ledger caution: CRYPTO is 59% forged (3,021 of 5,135 rows). Do not validate against the
   existing CRYPTO PF. Recompute outcomes from exchange data.
5. Report: excess vs BTC, excess vs cash, Sharpe at both, and how much of the return is beta.

FALSIFIER: dead if excess vs cash <= 0 after 25 bps costs at n >= 100 funding events.
OUTPUT: results/A3/REPORT.md + result.json.
WARNING: the Nov-14 review estimated the known stop-fill fix moves CRYPTO PF to ~1.00, i.e.
break-even. Expect to find no edge. That expectation is the hypothesis, not a conclusion.
```

---

## 9. A4 — FOREX: carry vs cash

```text
ASSIGNMENT A4 - FOREX CARRY vs CASH

Hypothesis (pre-register): "G10 carry (long high-yield, short low-yield) beats 13-week
T-bill cash net of 15 bps round-trip over 2015-2026, after removing outlier fills."

1. Only 158 FOREX marks are verified (56% forged). Recompute from price data; do not trust
   the ledger PF.
2. First quarantine known-bad rows: CADJPY exit 611.23 vs entry 115.77, USDJPY exit 1.358 vs
   entry 158.58. These inflate PF massively. Report the effect of removing them.
3. Benchmark: T-bill cash. FX has no natural long-only premium - cash is the null.
4. Model spread explicitly per pair (JPY pairs ~1.0-1.5 pips, majors 0.3-0.8). If the edge
   is smaller than the spread, that is the answer.
5. Report: excess vs cash, IR, max drawdown, and the breakeven spread in bps.

FALSIFIER: dead if excess vs cash <= 0 at n >= 100 after realistic spread.
OUTPUT: results/A4/REPORT.md + result.json.
NOTE: measured Sharpe/trade for FOREX is the best in the system (0.061) but the cost ratio is
the worst. Resolve that tension explicitly.
```

---

## 10. A5 — Prediction markets: calibration and maker economics

```text
ASSIGNMENT A5 - PREDICTION MARKETS: IS THERE ANY VIABLE EDGE?

Read 2026-11-15_1233AM_winning-strategies/buffy/02_prediction_markets/WHY_NO_WINNERS.md first.

1. FIRST, fix the recording gap: the ledger has NO prediction class. Add a PREDICTION asset
   class (or a pm_* category excluded from CRYPTO aggregates) so outcomes can be verdicted at
   all. Without this nothing else matters.
2. Record per contract: price_at_entry, settled_outcome, timestamp, venue, side.
3. Compute CALIBRATION, not just PnL: Brier score and a reliability curve per model/agent.
   A well-calibrated model that loses money to fees is still a finding.
4. Fee-aware economics: for each trade compute the Kalshi/Polymarket fee
   (0.07 * P * (1-P) per contract) and solve for the edge needed to break even at that price.
   Report the fee as % of stake per trade - it is 6.3% at 10 cents and 3.5% at 50 cents.
5. Test the ONLY structurally sound path: MAKER fills (zero fee, 15-25% rebate). Estimate
   what share of fills are achievable as a maker, and whether the rebate covers adverse
   selection. Do not assume it does.
6. Copy-trading: quantify the double-fee + mirror delay cost. Show the arithmetic for one
   real leader's history if you can obtain it.

FALSIFIER: dead if required edge to break even exceeds the measured calibration edge at every
price bucket. Report the fee-inclusive breakeven edge regardless of outcome.
OUTPUT: results/A5/REPORT.md + result.json + the calibration table as CSV.
HONEST EXPECTATION: taker-side PM trading is expected to fail on fees. Maker-side is the only
open question. Say which one you actually tested.
```

---

## 11. A7 — Red team

```text
ASSIGNMENT A7 - RED TEAM (runs after A1–A5)

Your job is to FALSIFY the claimed wins. You are not a cheerleader and you get no credit for
agreeing.

For each result in results/A*/result.json where verdict == "WIN":
1. Recompute the headline metric independently. If you cannot reproduce it, it is not a win.
2. Look for the five failure pillars: statistical (parameter sensitivity, DSR), structural
   (regime concentration), execution (costs/slippage realism), data (lookahead, survivorship,
   timestamp errors), risk (concentration, Kelly, ruin).
3. Try to break it in the cheapest way first:
   - double the costs;
   - shift entry by one bar (the 2-day-lag proxy);
   - remove the best 5 trades and recompute;
   - split by year and see if it is one year carrying everything.
4. Check the trial count. If the agent tested 20 variants and reported the best, the DSR must
   use N=20. If they tuned after OOS, mark it INVALID.
5. Write results/A7/REDTEAM.md: for each claim, VERDICT = CONFIRMED / WEAKENED / FALSIFIED,
   with the specific test that decided it.

RULES: do not "fix" their work. Do not tune. Report numbers, not opinions.
OUTPUT: results/A7/REDTEAM.md. If you confirm every claim, say why you believe it - a red team
with a 100% confirmation rate has usually not tried.
```

---

## 12. Output contract

Every agent writes, under `results/<agent_id>/`:

- `REPORT.md` — falsifier at the top, method, cohort definition, results, gate table, verdict
- `result.json` — matching `results_schema.json`
- any CSVs/plots needed to reproduce

Nothing else. No shared-file edits except where the assignment names a file, and those changes go on
the agent's own branch with a note in `REPORT.md`.

## 13. What "NO" looks like (and why it is fine)

> **A1 — NO.** Excess vs SPY at matched exposure: −1.1%/yr, IR −0.32, alpha t-stat 0.8.
> Fails gate 1. Tested 1 hypothesis, n=738 verified. Artifacts in `results/A1/`.

That is a **successful** agent run. Eight of those tells you where not to spend money — which is
strictly more valuable than eight optimistic backtests. The failure mode to avoid is not "we found
nothing"; it is "we found something" that evaporates on contact.
