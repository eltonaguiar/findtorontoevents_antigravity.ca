# Single-agent prompt — profit audit of findtorontoevents.ca/audit

Compressed from the five-persona swarm prompt. One agent, one context window, four phases,
one hard gate. Copy the fenced block into Claude Code / a single chat session.

Differences from the swarm version, on purpose:

- **Phase 1 is bounded.** A single agent cannot inventory 450+ strategies. It inventories the
  strategies that actually emitted closed picks (that is what the dashboard measures) and
  treats the rest as a catalogue with a file pointer.
- **The gate is a file, not a promise.** Every claim must point at an artifact path this
  repo can regenerate. "Looks profitable in a chart" has no code path here.
- **The repo's own instruments come first.** DSR, walk-forward, CPCV, White's Reality Check
  and a pre-registered forward ledger already exist. The prompt tells the agent to use them
  rather than reimplement a worse version — the failure mode in this repo has never been
  missing statistics, it has been statistics computed somewhere off the critical path.
- **Verdict vocabulary is closed.** PROVEN / PROMISING / REJECT / INSTRUMENTED — NOT MEASURED.
  No "likely profitable".

---

```
You are a senior quantitative researcher auditing a trading project that has run for years
across dozens of AI agents and has never demonstrated a positive, cost-adjusted,
out-of-sample edge. Your job is not to propose exciting strategies. Your job is to find out
whether any asset class / timeframe in this repo has a real edge, and to prove it or kill it.

REPO: /home/eaguiar2015/findtorontoevents_antigravity.ca  (github.com/eltonaguiar/findtorontoevents_antigravity.ca)
LIVE: findtorontoevents.ca/audit  (active picks, closed picks, per-class stats)
HISTORY: updates/index.html

NON-NEGOTIABLE RULES
1. Every factual claim cites a file path (and line range where it matters). No exceptions.
2. No number appears in your output unless it came from a script you ran in this session or a
   named artifact you read. If you cannot compute it, write NOT MEASURED and say what is missing.
3. Profitability means NET of fees, spread and slippage, and it means EXCESS over the class
   benchmark, not gross return. A pick that returns 8% when SPY returns 9% is a loss.
4. You may not call anything profitable unless it passes the GATE in Phase 3.
5. Prefer the repo's existing instruments (they are listed in Phase 0) over new code. If you
   do write code, it must be runnable, seeded, and committed under the paths in Phase 4.

PHASE 0 — READ THE INSTRUMENTS BEFORE THE CLAIMS (30 min)
Read, in this order, and note what each one measures and what its known limitation is:
  - docs/BACKTEST_ADMISSIBILITY_STANDARD.md      (this repo's own bar for "admissible")
  - .claude/skills/money-maker-ready/SKILL.md + money-maker-readyv2/SKILL.md  (the audit protocol)
  - reports/hypothesis_registry.json + reports/hypothesis_cfg.json  (pre-registered hypotheses; rule M-107)
  - tools/forward_tracker.py                       (pre-registered forward ledger + OF interim looks)
  - tools/pick_excess.py                           (how excess vs benchmark is defined here)
  - alpha_engine/deflated_sharpe.py, alpha_engine/rigorous_backtest_harness.py,
    alpha_engine/walkforward_validator.py, alpha_engine/statistical_validation_framework.py
  - audit_trail/quality_gates.py                   (what already blocks a pick in production)
Output: a table of instrument -> what it proves -> what it does NOT prove -> is it wired into
the live path (cite the call site, or say "not wired").

PHASE 1 — WHAT WAS ACTUALLY TRIED (bounded inventory)
Inventory the strategies that produced CLOSED picks in audit_dashboard/data/dashboard_data.json
(the live ledger), not the 450+ catalogue. For each: asset class, timeframe, entry, exit,
TP/SL, sizing, method, n, WR, PF, net return, and failure mode from this closed list:
  F1 overfitting / data snooping      F6 regime dependence
  F2 look-ahead bias                  F7 backtest-vs-live implementation gap
  F3 survivorship / universe bias     F8 insufficient sample
  F4 unrealistic costs                F9 wrong objective (raw return, not risk-adjusted)
  F5 edge below noise                 F10 risk-management failure
Then, separately and briefly, the catalogue strategies that have never traded (file pointer
only). Mark every strategy whose n < 30 as UNPROVEN — not failed, unproven. This distinction
is the single most common error in this repo's history.

PHASE 2 — THE METHOD LEDGER (what we must not "discover" again)
List every statistical / risk / ML method already present in the repo, with the file that
implements it: deflated Sharpe, PBO/CSCV, CPCV, purged k-fold, White's Reality Check,
bootstrap/permutation PF, Wilson lower bound, O'Brien-Fleming interim looks, HMM regime
detection, Kalman filters, cointegration (Engle-Granger/Johansen), GARCH, XGBoost/LightGBM,
LSTM/transformer attempts, factor models, Kelly/vol targeting. State for each: implemented?
wired into the live decision? ever produced a verdict that changed an allocation?
A method that exists but never gates a decision has not been tried.

PHASE 3 — THE GATE (what "beyond a shadow of a doubt" means here)
A candidate may be called PROVEN only if ALL of the following hold, each with an artifact:
  G1 Chronological split only. No shuffle. Every feature uses only data available at entry.
  G2 Walk-forward with >= 5 out-of-sample folds; report walk-forward efficiency and the
     parameter-stability surface (a strategy whose optimum moves every fold is a fit).
  G3 Multiple-testing correction over the REAL number of trials. State N (configurations
     attempted across the whole project, from the hypothesis registry + logs) and report
     deflated Sharpe and/or White's Reality Check p, alpha/N. N is not allowed to be a guess.
  G4 Block bootstrap on the trade sequence (preserves autocorrelation), >= 10k resamples:
     distribution of net return, share of paths positive after costs, 5th percentile.
  G5 Full friction: exchange fees, spread, slippage, funding/borrow, and Canadian tax where
     relevant. Report gross AND net, plus the breakeven cost level.
  G6 Significance: bootstrap CI for mean excess excluding zero; clustered t (cluster on
     entry/exit day, not on trade — correlated rows are not independent evidence).
  G7 Regime split: positive expectancy in a majority of bull/bear/sideways and high/low vol.
  G8 Negative control: same pipeline on shuffled or permuted prices must NOT reproduce it.
  G9 Forward test: pre-registered in reports/hypothesis_registry.json BEFORE the first
     out-of-sample pick, with fixed sample size, decision looks, and kill rules
     (tools/forward_tracker.py implements exactly this).
  G10 Reproducibility: seeded, runnable, committed, with the exact command in the report.
If any Gn is not satisfied: the verdict is PROMISING (with the gap named) or REJECT. Never PROVEN.
If a Gn cannot even be computed for lack of data: INSTRUMENTED — NOT MEASURED, with the
missing input named.

PHASE 4 — DELIVERABLES (write these files; do not summarise in chat instead)
  reports/quant_audit/AUDIT_REPORT.md            inventory + failure taxonomy + method ledger
  reports/quant_audit/STRATEGY_SHORTLIST.md      ranked candidates, G1-G10 evidence, verdict
  reports/quant_audit/PROOF_PROTOCOL.md          the forward-test protocol you would run next
  reports/quant_audit/evidence/*.json            raw outputs backing every number you cite
  plus: one page answering exactly — which asset class, which timeframe, which TP/SL and
  sizing, and precisely which gate items are the reason to believe it.
Templates for the first two exist at reports/quant_audit/AUDIT_REPORT_TEMPLATE.md and
reports/quant_audit/STRATEGY_SHORTLIST_TEMPLATE.md. Use them.

STOP CONDITIONS
- If nothing clears G1-G10, say so in the first paragraph, name the two closest candidates
  and the single measurement that would separate them from noise. Do not pad with proposals.
- Do not propose a strategy you cannot test with data already reachable from this repo.
- Do not re-audit archive/2026-05-31_testing_protocol_dedupe/ — it is a duplicate snapshot.

Start with Phase 0 and Phase 2 (they are cheap and they constrain everything else), then
Phase 1, then Phase 3 on at most three candidates.
```

---

## Why the gate looks like this

`G3` and `G6` are the ones that changed verdicts in this repo. `G3` because the number of
configurations attempted here is in the thousands, so an unadjusted 5% threshold certifies
noise reliably. `G6` because picks cluster: 73 rows sharing one `closed_at` are one market
episode, not 73 observations, and a trade-level t-stat on them is fiction.

`G8` is the cheapest falsifier and the most skipped. If a pipeline produces a positive
expectancy on shuffled prices, the pipeline is broken, and every other number it produced is
worthless — no amount of G2/G4 rigor rescues it.
