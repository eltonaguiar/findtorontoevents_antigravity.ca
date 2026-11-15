# final_v001 — Proof Plan for Profitable Strategies per Asset Class

**Worktree:** `wire-fix-ghactions-pr-issues-v2`
**Stamp:** 2026-11-15T07:41Z
**Owner input:** review all `WIRED_IN/` work + 48h of `main` changes + strategy
catalogs, then produce a finalized strategy to *find and prove* profitable
strategies per asset class that feed `findtorontoevents.ca/audit`.
**Companion audit:** `GHACTIONS_PR_ISSUES/2026-11-15T0738Z_gha-pr-issues-audit/`
(workflow / PR / issue health).

---

## Verdict in one paragraph

We do **not** currently have a single proven, cost-adjusted, out-of-sample,
forward-verified edge in any asset class. `money_ready` is empty for all classes.
The live books are net losers after honest accounting (CRYPTO PF 0.92 / WR 35.9%
n=3,705; EQUITY PF 0.94; ETF PF 0.02–0.76; FOREX PF 0.66; BOND n=1; PENNY n=4).
The *measurement apparatus that could prove an edge is built but not wired*: the
benchmark-aware forward ledger exists on `main` but has **zero** workflow callers
and **zero** ledger rows; `pick_excess.py`, `build_benchmark_prices.py`, the
forward clock, and the "vs Bench" dashboard column live only in an unmerged PR
(#785) and would 404 in production even if merged (the FTP upload list omits
them). Two data-integrity bugs (flat `exit_price=0.0`, frozen-price PF=120
artifacts) poison every statistic. This folder is the plan to fix that sequence
and prove (or kill) an edge, class by class.

The one candidate worth pushing to a real forward test first is **ETF H-103
cross-asset dual momentum** (backtest PF 3.57, bootstrap CI [1.64, 9.69], alpha
t 2.36, cost-robust to 20 bps) — but it has **0 of 100 required forward trades**,
so it is a hypothesis, not a result. Second is **BTC trend (SMA200)** on wealth,
which is asserted but has no reproducible artifact.

## The one-sentence strategy

**Fix the ledger, make the clock run, then promote only what survives a single
10-gate proof standard on a live, net-of-cost forward ledger against the right
benchmark — publish every verdict to `/audit`, and kill everything that fails.**

---

## How to read this folder

| File | What it settles |
|------|-----------------|
| `01_PROOF_PROTOCOL.md` | The **single canonical 10-gate ladder** (kills the "0/10 vs 0/11 vs 9-gate" drift). Promotion = pass all gates on the forward ledger. |
| `02_CURRENT_STATE_EVIDENCE.md` | What is actually proven vs asserted, per class, with numbers and file evidence. Includes the measurement-apparatus audit. |
| `03_MEASUREMENT_WIRING.md` | Exact steps/files/workflows to make the forward clock and "vs Bench" column real and live on `/audit`. |
| `04_PER_ASSET_CLASS_PLAYBOOK.md` | Per class: benchmark, data source, best hypothesis, cost model, kill rules, current verdict. |
| `05_RESEARCH_QUEUE.md` | Ranked next hypotheses to test, with priors and expected effect size. |
| `06_AUDIT_PUBLISH_CONTRACT.md` | The data contract so every pick/verdict renders correctly at `findtorontoevents.ca/audit`. |
| `07_EXECUTION_ROADMAP.md` | 0–3 day / 1–3 week / 1–3 month plan with exit criteria and owners. |
| `08_ELIMINATION_REGISTER.md` | What is dead and why — stop relitigating. |
| `manifest.json` | Machine-readable gates, thresholds, per-class benchmark map, statuses. |
| `prompts/MASTER_PROMPT.md` | A single-agent prompt to execute this plan end to end. |

## Non-negotiables encoded throughout

1. **No promotion without a forward ledger.** Backtests are priors, never proof.
2. **Net of per-class costs, vs the right same-window benchmark.** A drawdown
   reduction is not alpha.
3. **Trial accounting.** Every tested variant counts; DSR/PBO against the true
   trial count.
4. **Data integrity precedes every claim.** Fix #748 and the flat/frozen-price
   pollution first.
5. **Kill fast and record it.** A killed hypothesis is a result.
6. **Publish or it didn't happen.** Every verdict lands in a `/audit` sidecar and
   column; links must not 404.
