# 03 — Peer `final_v4` Cross-Check

**Compared (repo-root):** `final_v4/04_synthesis/SYNTHESIS.md`, `final_v4/05_final_summary/00_FINAL_SUMMARY.md`, `final_v4/finpredict_2026-11-14T215013Z/*`, `final_v4/flaxen-hair_2026-11-14T2200/*`, `final_v4/childlike-airport-20261114-215046Z/*`, `final_v4/01_peer_final_v3_review/*`, `final_v4/03_remote_github/*` (spot).

## Agreements (high confidence)
| Theme | Peer evidence | Assessment |
|---|---|---|
| Not money-ready / not proven profitable | Synthesis “not profitable today, testable”; 05_final “No”; childlike-airport “not money-ready”; finpredict/flaxen-hair converge | **Accept.** Consistent with money-ready verdicts (CRYPTO negative expectancy, ETF insufficient), stale DB, reconciliation gaps. |
| 1–2 validation candidates only | CRYPTO + EQUITY/crypto-trend prioritized across peers | **Accept, as candidates only.** Require frozen net, benchmark-relative, paper proof. |
| Integrity/measurement is primary blocker | PnL units, stop/fill (B3/B4), stale/unquoted, reconciliation, single-source, multi-testing | **Accept.** P0 before any performance claim. |
| VWAP not money-ready | Synthesis “REJECTED”; finpredict “DISPROVEN (Sharpe ~1.18)”; flaxen-hair blocked | **Accept as not deployable now.** v12 shows basic-pass but PBO 0.489 / n limits / falsification history — treat as research, not proof. |
| ETF/FOREX/BOND/FUTURES/COMMODITY blocked or diversifier-only | All peers block or restrict | **Accept.** |
| MF = baseline/ballast, not trading edge (by default) | Synthesis/05_final/childlike-airport | **Accept** pending wired, net-of-fee, benchmark-relative evidence. |

## Conflicts / divergences and adjudication
| Conflict | Positions | Adjudication (conservative) |
|---|---|---|
| Slot 1: CRYPTO vs EQUITY | quant-audit/synthesis favor CRYPTO evidence/position bucket or split; finpredict/flaxen-hair favor EQUITY cost-clearing | **No promotion either way.** Run both as pre-registered slots (A/B/C framing) after integrity fixes; compare net, benchmark-relative, forward. |
| VWAP status | “REJECTED/refuted” vs childlike-airport v12 “profitable basic, needs more data (PBO fail)” | **Unproven.** Keep in research queue; cannot pass strict PBO<0.3 today. |
| Peer metric reproducibility | Various replay/Sharpe/PF figures cited | **Do not adopt unreproduced numbers as truth.** Use `EVIDENCE_INDEX`/source files; require rerun from canonical data. |
| MF availability in system | childlike-airport notes low-fee subset infra; subagent reported absent/misaligned in inspected state | **Build/validate required.** Treat MF as viability-to-prove, not ready. |

## Gaps in peer packages (to close in v5)
- Explicit **0% PnL market-data reasonableness** and **blank/null field** QA for open & recently closed picks — addressed in `05_qa_plan/QA_PLAN.md`.
- MF/ETF **probability-of-success, risk, risk-adjusted, methodology** per pick/sleeve — addressed in `06_picks_probability_risk/MF_ETF_PICKS.md`.
- Standalone **risk-management webpage** — delivered as `07_risk_management_web/index.html`.
- Clear adjudication of **validated vs suspect zero PnL** (flat vs stale vs bug) — included in QA plan.

## Proposed edits to peer conclusions
1. Reframe “testable” claims to “testable **after Phase 0 integrity + QA pass** on a reconciled cohort.”
2. Require every cited metric to carry `n`, window, gross/net, benchmark, and data-hash/source; downgrade uncited/reproduced-only-once metrics.
3. Treat all “REJECTED/DISPROVEN/PROFITABLE BASIC” labels as **stateful to dataset/window** until independently reproduced on canonical, net, benchmark-relative data.
