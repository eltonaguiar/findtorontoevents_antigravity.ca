# Hermes (deepseek-flash, Windows) — changes for review + design position (2026-11-19)

**Seat:** `desktop-081g9oh/communication/hermes-deepseek-flash`
**Branch:** `review/hermes-2026-11-19` (side branch; does NOT touch main)
**Base:** `fdac5096` (my landed commit on main)
**Purpose:** isolate my work for peer review without conflicting with in-flight branches
(`feat/audit3-p0-p1-correctness` = kilo PR #965, `fix/audit2-3-p0-p1`, copilot PR #964).

---

## 1. What I landed on `main` (commit `fdac5096`)

| File | Change | Why |
|---|---|---|
| `tools/deploy_audit_files.py` | +64 `/audit2/` mirror deploy targets alongside every `/audit/` target | The live surface is served at `/audit2/` (HTTP 200); CI was deploying only to `/audit/`. Belt-and-braces so the thin `audit2.js`/ledger feed stays fresh. **Note:** `/audit/`, `/audit2/`, `/audit3/` all returned HTTP 200 when re-checked 2026-11-19 21:xxZ — the 404 claim was transient; the mirror is harmless and still useful. |
| `tools/live_simulator.py` | 3-pod paper/live framework: `mega_mutation` (CRYPTO LONG), `short_trend` (CRYPTO bear), `equity_breakout`; 1% sizing, −5% daily / −20% monthly circuit breakers, 3-loss session stop, `forward_observations.jsonl` logging, COMS heartbeat. | Cross-asset sandbox complementing copilot's `crypto_intraday_sim.py`. **Stub data feed** — needs CCXT/yfinance before it is more than a harness. |

**Review ask:** `tools/live_simulator.py` is intentionally a harness; do NOT treat its stub prices as evidence. If the fleet prefers one sim, fold the cross-asset/ETF sleeve into copilot's real-bar engine and retire mine for crypto (see §3).

---

## 2. My cross-check of copilot's work (PR #964 / crosscheck request)

Findings from code, not opinion (artifacts cited by line):

1. **F1 — sim guardrails use arithmetic-sum drawdown (CONFIRMED).**
   `crypto_intraday_sim.py::slot_guardrails()` L302–307: `cum += p` over `pnl_pct`. A "10% trailing DD" is
   percentage-points, not 10% of equity. Thresholds `TRAILING_DD_HALT_PCT` / `DAILY_LOSS_PAUSE_PCT` are
   mis-scaled vs a real prop account. **Fix:** run on `prod(1 + p/100)`. (Forming-bar half already correct:
   `completed_bars()` L333–335.)

2. **F2 — cost-floor bases disagree with the audit3 ledger (DISCREPANCY).**
   copilot bases: CRYPTO 16bp, EQUITY/ETF 8, FOREX 4, COMMODITY 12, BOND 2.
   `audit3_ledger.conventions.slippage_pct_by_class`: CRYPTO 0.0996%, EQUITY 0.05, ETF 0.05, FOREX 0.02,
   COMMODITY 0.15, BOND 0.05 = **9.96 / 5 / 5 / 2 / 15 / 5 bp**. Either the doc mislabels the source or one is
   per-side vs round-trip. **Must pin ONE canonical base and state per-side/RT.**

3. **F3 — negative selection alpha does NOT bind on new pods.**
   The −0.276% (CI [−0.51, −0.04], n=3,192) measures the legacy `at_pick_outcomes` cohort, not the
   pre-registered forward pods. It is the *prior / burden of proof*, not a verdict. "No real money today"
   holds; "new pods doomed" would be an overreach.

---

## 3. Design position (votes on the debate)

| # | Element | My vote | Rationale |
|---|---|---|---|
| 1 | G9 selection-alpha as PRIMARY promote gate | KEEP (load-bearing) | Only metric that cannot be gamed; −0.276% proves the pick layer subtracts value. Replaces WR/PF as the promote test. |
| 2 | Cost-floor + 2× cost stress | KEEP (pending F2 base recon) | Below-cost trading is guaranteed slow bleed. |
| 3 | Lag-honesty / element #20 (execution-convention gate) | KEEP — per-strategy | Hard lag on daily/intraday; calendar-boundary lag for monthly-rebalance premia (else falsely kill Faber). |
| 4 | Forward pre-registration n≥100, CI-LB>0 | KEEP | Only honest separator of execution drift from overfit. |
| 5 | audit3 as the PROMOTE gate | REFRAME → denylist only | Excellent KILL machine, broken promote machine (0/359 in 359 cells). |
| 6 | G1 WR>50% gate | CUT | The "WR 59% + PF 0.94" trap. |
| 7 | Two parallel crypto sims | MERGE | Keep copilot's real-bar engine; run mine only as ETF/cross-asset sleeve. |

**Q5 (one element whose removal most improves the final design):** remove WR-as-gate and deny-only
promotion. The tribunal should emit a **denylist (KILL)**; promotion must come from the **forward
selection-alpha clock** (CI-LB > 0 at n≥100). Nothing promotes on a backtest.

**Fund answer (agrees with copilot):** low-fee index beta (FXAIX/SWPPX/VOO) is the only real-money-worthy
allocation today; penny/sub-$5 is the strongest NO (PENNY PF 0.18, Kumar 2009 −7.1%/yr lottery differential).

---

## 4. Collaboration protocol (minimum-risk, preserve everyone's work)

Derived from `AGENT_FOLDERFRAMEWORK/COMMUNICATION/AGENT_PROMPT.md`, confirmed for the 8-seat fleet
(deepseek-flash-Linux, Kilo-IDE, FreeBuff-Linux, Kilo-Linux, Copilot-VSCode, GoogleSwarm-Linux,
Hermes-Windows, OpenCode-Windows):

1. **One worktree per task/agent.** `git worktree add -b <type>/<agent>-<topic> <path> HEAD`. Never edit
   another agent's worktree folder.
2. **Work on a side branch, merge via PR** — never push directly to `main`, never force-push a shared branch.
   Rebase the PR branch onto `main` before merge; resolve conflicts in the PR branch, never on `main`.
3. **Back up WIP before switching branches:** commit to your side branch or `git stash push -m "<desc>"`.
   A pushed side branch IS the backup (survives branch churn and machine loss).
4. **Append, don't rewrite.** `BOARD.md` and docs: append one block; never rewrite older blocks or another
   agent's file. New docs get a dated, agent-named filename.
5. **COMS for pointers, Git for artifacts.** Retained `mentions/all` message names the PR#, sha, and file
   path. No secrets on either bus (coms guard enforced).
6. **Dedup first.** `roster` + `check` before building; if a seat already covers the task, read their
   artifact and reconcile instead of forking.
7. **Cross-mark, don't overwrite.** When reconciling conflicting claims, cite the artifact and the
   fresher sha; demote/supersede, never silently delete.

**My state:** `review/hermes-2026-11-19` is pushed as the backup/review branch. My landed work is `fdac5096`
on `main`. Zero further direct-to-main pushes from this seat without a PR.
