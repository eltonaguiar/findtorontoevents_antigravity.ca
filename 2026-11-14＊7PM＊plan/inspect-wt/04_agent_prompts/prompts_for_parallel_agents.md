# Prompts for parallel AI coding agents — "find us something that REALLY works"

> Give each agent ONE prompt block below (they are in different worktrees/machines).
> Every prompt shares the same hard frame so parallel agents cannot talk themselves into
> fake wins: **pre-register → out-of-sample → cost-adjusted → benchmark-relative →
> forward paper-trading → only then capital.** Prompts are written to be pasted verbatim.
> Companion docs: `../01_plan_per_asset_class/` (per-class plan), `../08_key_metrics_by_perspective/`
> (the bar each prompt's gates are drawn from).

---

## PROMPT 0 — the universal frame (prepend to every agent)

```text
You are one of several agents working INDEPENDENTLY on different asset classes to find a
strategy that is genuinely profitable after costs. Context: this repo has failed for years
to show profit in ANY asset class; prior audits found (a) PnL fields showing 0% for 81% of
open picks, (b) stop-fill slippage eating most of crypto's losses, (c) 170 ledgers where
4 passed vs 8.5 expected by chance, (d) multiple-testing everywhere.

HARD RULES (violating any = your result is void):
1. PRE-REGISTER before you compute: write hypotheses_<yourclass>.md with exact rules,
   universe, timeframe, costs, sample-size floor, and kill criteria. Commit it BEFORE
   running the backtest. No editing after seeing results (record any change as a NEW
   pre-registration with a trial ID).
2. BENCHMARK-RELATIVE: you do not beat "0%". You must beat (a) buy-and-hold SPY total
   return and (b) 60/40, risk-adjusted (Sharpe/Sortino/maxDD/Calmar), over 24+ months
   forward. A strategy with Sharpe 1.0 that loses to SPY's Sharpe ~0.9 with 1/3 the
   drawdown may still be worth it — state WHICH benchmark you're beating and why.
3. COSTS are part of the hypothesis: per-trade round-trip cost (commission + spread +
   slippage + borrow) must be in the backtest. Report PF and expectancy BOTH gross and net.
4. CORRECT FOR MULTIPLE TESTING: report total trials (all agents, all versions), apply
   Bonferroni or deflated Sharpe. n≥100 trades for any claim; Wilson CI on hit rate.
5. SPLIT-SAMPLE + WALK-FORWARD ONLY. No full-sample tuning. Report the worst regime
   (2022 bear, COVID crash, latest 6 months) separately.
6. PAPER-TRADE FORWARD for 8-12 weeks on real quotes before asking for capital. Kill
   criteria stated up front (e.g., 2 consecutive PF<0.5 months, or drawdown >15%).
7. Report FAILURES as clearly as wins. A clean kill is a success. Never massage thresholds.
Output: one verdict line first — VERDICT: PASS-GATE | FAIL-GATE | INCONCLUSIVE — then evidence.
```

---

## PROMPT 1 — CRYPTO (conditional candidate; measurement first)

```text
Asset class: CRYPTO. Your job in order:
(1) Verify the fill model before any signal work: re-run tools/stop_fill_replay.py with
    --truncate-at-exit on closed picks; quantify planned vs realized stop slippage per
    strategy. If a strategy's edge is smaller than its fill error, it is dead — say so.
(2) Only then: test whether the "elite" strategies (PF 2.3–4 historically) survive
    forward paper-trading when entries are copied AT THE CANDLE, not at signal time.
(3) Candidate hypothesis (pre-register it): vol-targeted trend on BTC/ETH only, position
    horizon 1–5 days, 0.15% round-trip cost, gate = forward PF ≥ 1.3, WR ≥ 55%, n ≥ 100,
    dual data source (Binance + KuCoin), AND must beat B&H BTC risk-adjusted (Sharpe).
Kill triggers: fill model unfixable, gate miss at n=100, or benchmark miss.
Do NOT touch FOREX-style mutation-before-kill paths; do not re-enable VETOED strategies.
```

## PROMPT 2 — EQUITY (only class with a cost margin; benchmark test is the gate)

```text
Asset class: US EQUITY. Current evidence: class mean +0.323%/trade after 3× cost screen
(n=738) but t=1.52 (p=0.12) and a benchmark test FAILED (median pick −0.57% vs SPY).
Your job:
(1) Do not re-run the same test with new thresholds — that is the multiple-testing trap.
    Pre-register ONE new hypothesis with a trial ID: e.g. "mean-reversion RSI(2) on
    S&P500 constituents, held 1–5 days, vs SPY, n≥500, cost 0.10% round-trip."
(2) Benchmark-relative gates: excess Sharpe vs SPY ≥ 0.3 over 24mo forward, maxDD ≤ 12%,
    hit-rate Wilson CI above 50%, net-of-cost PF ≥ 1.15 every month-cluster (not just total).
(3) Capacity check: can it absorb $50k–$250k without >0.10% impact?
(4) Survivorship: use the point-in-time constituent list (CRSP/Compustat or the repo's
    existing universe) — never today's list applied to history.
Output verdict per PROMPT 0 rules.
```

## PROMPT 3 — MUTUAL FUNDS + ETF (the "boring wins" track — user's priority)

```text
Asset classes: MUTUAL FUNDS and ETFs. The thesis: with enough time, low-cost fund
allocation should be the highest-probability positive-return path; the prediction system
does not need to work for this to make money — it needs to not destroy beta.
Two deliverables:
(A) DEPLOYMENT SLEEVE (works regardless of alpha): monthly top-2 momentum rotation across
    broad MF/ETF share classes (VTI/VEA/BND/TIP-class funds with ER ≤ 0.20%, AUM threshold),
    12-1 momentum, absolute-momentum filter vs 3-month T-bill, inverse-vol weights.
    Gate: net Sharpe ≥ 0.7, maxDD ≤ 15%, Calmar ≥ 0.7, and — critically — beat 60/40 and
    be within 0.5 Sharpe of SPY while cutting drawdown ≥ 30%. Backtest on point-in-time
    NAVs with fees; then paper-trade monthly for 3 months.
(B) SELECTION RESEARCH (only if A passes): can active fund selection beat the sleeve?
    Pre-register: style/sector rotation lag risk, survivorship-corrected fund database,
    after-cost drag. Null hypothesis = "active does not beat the index after fees" —
    the burden of proof is on rejecting it.
Infrastructure to build first: NAV cache (daily), fund metadata (ER, AUM, inception),
    share-class dedup (same fund, multiple classes), point-in-time universe.
```

## PROMPT 4 — COMMODITY/FUTURES + BOND (low-frequency, data-gated)

```text
Asset classes: COMMODITY/FUTURES and BOND.
COMMODITY: historical PF ~1.78 but execution/cost issues and n-thin per instrument.
Test ONE pre-registered low-frequency hypothesis: CTA-style trend on 8–12 liquid futures
(monthly rebalance, Donchian/200-day hybrid), costs from actual roll schedules,
gate = PF ≥ 1.3 net, n ≥ 100 trades across instruments, beats B&H commodity index AND
has Sharpe ≥ 0.6. COT data may be used only as a documented feature with its own
pre-registered test (a prior COT test failed 4/4 — do not silently re-test it).
BOND: n is far below floor (18–35). Your job is NOT strategy research yet: build the
sample. Extend bond_strategies.py + FRED feeds, define what a bond pick even is
(duration bucket? curve trade? fund NAV?), and accumulate n under QA gates until
n ≥ 100, THEN pre-register. FRED data is free and point-in-time — use it.
```

## PROMPT 5 — FOREX (weakest class: honest kill-or-cure)

```text
Asset class: FOREX. Reality: sub-floor PF, high n (so the sample is honest but the
edge is absent). Per policy this class is on mutation-before-kill.
Your job is a bounded experiment: pre-register at most TWO mutations (e.g. session-filtered
carry-aware trend; or kill the class). Gates: net PF ≥ 1.3, n ≥ 150, both-halves PF > 1.0,
spread cost from real brokers (not 0), and benchmark = cash + a spot-futures carry proxy.
If both mutations fail: recommend FORMAL CLASS KILL (stop emitting forex picks) —
a documented kill is a deliverable.
```

## PROMPT 6 — MEASUREMENT/QA (no strategy; the class that unblocks everything)

```text
No new signals. Implement final_v4/inspect-wt/02_qa/QA_PLAN.md: (1) PnL=0 validator —
recompute stored 0%-PnL rows against real market data over open→closed AND open→current
windows, reasonability band max(0.25%, 3σ of same-class residuals), reasons
ZERO_PNL_OK/ZERO_PNL_MISMATCH/TIME_ANOMALY/STALE_OPEN; (2) blank-field flagger for OPEN
and recently-closed rows, never coerce to 0; (3) exit-reasonableness replay with
--truncate-at-exit. Verdict = the MISMATCH rate. This agent's success is measured by
other agents being able to trust their PnL fields.
```

---

## Why these prompts are shaped this way (for the orchestrator)

- **Every prompt has a numeric gate written into it** — agents cannot lower thresholds
  after seeing results because the gate was in the prompt (pre-registration by the orchestrator).
- **Benchmark-relative is explicit** (SPY / 60/40 / B&H) — the missing piece the user named.
- **One prompt is a kill prompt** (FOREX) — parallel agents must be allowed to conclude "dead";
  otherwise they will always produce something that looks alive.
- **QA agent exists** — until PnL fields are trustworthy, every other agent's output is
  measured with a broken ruler.
- Run agents on **different machines/worktrees but same gate definitions**; merge only at
  verdict level, never pool trials without counting them in the multiple-testing budget.
