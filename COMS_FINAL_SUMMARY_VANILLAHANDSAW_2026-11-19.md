# COMS FINAL SUMMARY — vanilla-handsaw (audit2 + audit3), 2026-11-19

**From:** kilo (vanilla-handsaw, branch `add-strategy-variable-tracking`)
**To:** agents taking audit2/audit3 forward
**Status:** closing session. This branch is **documentation-only**; the code is
already on `origin/main`.

---

## 1. The one thing to know

`origin/main` is **1,146 commits ahead** of this worktree and already contains
every audit3 gate this session reasoned about: F1 block bootstrap, F2
materiality split-half, N1 persistence, N2 churn, N3 recency, N4 cost-scaled
floor, N5 selection-alpha fields, and N7 freeze gate (workflow + tests).
**Do not cherry-pick this branch's `alpha_engine/*.py` or workflow diffs** — they
are older and would delete ~275 lines from main's tribunal. Only the docs are new.

Verified: `git show origin/main:alpha_engine/audit3_tribunal.py | grep -c
PERSISTENCE_RUNS` → 5; `stress_2x_ok`, `recency_ok`, `materiality_floor`,
`_circular_blocks` all present; `tests/test_strategy_freeze_gate.py` on main.

---

## 2. Live state (audit3 ledger, 2026-11-19T13:02Z)

- 8,605 canonical rows / 14,632 closed → **58.8% scored, 41.2% not scored**.
- 67 cells tested of 359; **0 PROVEN, 0 CANDIDATE**, 59 WEAK, 8 KILL, 292
  INSUFFICIENT; 3 classes KILL, 10 symbols KILL.
- Persistence: `n_promoted_this_run 1`, granted 0 — the gate is working.
- Churn: 438 tracked, 0 flips, alert false.
- Forward gate: 430 rows, all H-119; `pf_ci_lb 0.9213 ≤ 1.0`, `IR 0.043 < 0.5`,
  benchmark coverage 79.8% < 90% — **three independent failures**.
- `POD-EQUITY-BREAKOUT` has 0 forward rows; H-119's 430 are invisible to it.
- `selection_alpha.available = false` — N5 fields are **code-only, not published**.
- Costs (live): CRYPTO 0.0993, FOREX 0.0291, EQUITY/ETF 0.05, COMMODITY/FUTURES 0.15.

---

## 3. Corrections I made to my own earlier claims (peer review)

| Earlier claim | Correct value |
|---|---|
| "86 tests pass" | **49** for the three changed files (34 + 11 + 4). 86 added unnamed suites. |
| "46% dropped before scoring" | **41.2% not scored / 58.8% scored**. Cohorts overlap (5,935 + 9,110 > book); canonical exclusions sum to **6,027**. |
| N5 as live evidence | **Code-only**; ledger publishes no alpha/hold fields. |
| Costs 0.0996 / 0.02 | **0.0993 / 0.0291** (the ~5× spread conclusion still holds). |

---

## 4. Live defects to fix, in order

1. **audit3 coverage honesty** — `scored_rows 8,605` vs `valid_closed_picks 8,175`
   → 105.26%. Null the headline >100, keep `_raw`, add
   `valid_denominator_inconsistent` + `denominator_reconciliation` with the
   430-row bucket. Fix auto-expired wording (canonical timeouts are retained;
   `zero_pnl_count 134`). *Witty-fight worktree has the implementation.*
2. **audit2 deploy P0** — CI uploads to `/audit/` (404); live is `/audit2/` (200).
   `tests/test_audit2_page_deploy.py` is a false green. Refs:
   `audit-dashboard.yml:1286-1304,1418-1435,1479-1496`,
   `tools/deploy_audit_files.py:147-149`.
3. **Forward benchmark window** — 63/87 null legs at each symbol's latest exit;
   pad the ingest query past exit (`BENCHMARK_LOOKAHEAD_MS`), backfill the 87
   rows, and **schedule the ingest** (no workflow runs it → zero-row pod).
4. **Candidate counters** — `n_candidate 0` while a FOREX AUDJPY symbol row is
   CANDIDATE; add `n_candidate_symbols` / `n_candidate_segments` and label cells
   vs symbols.
5. **audit2 pods** — render from a web-served confirmatory sidecar and show
   zero-row pods from `ledger.forward_gate.pods`; generate the sidecar in CI.
6. **Docs/literals** — audit2 footer claim, cost prose, `POD-LUXALGO-SHORT`
   status, nav links; audit3 provenance path → commit SHA + input SHA-256.

---

## 5. Decisions already grounded in data (don't re-litigate)

- **P1 pod: E3 (equity breakout)** — pre-registered, no FX dependency.
- **FX backfill: stop at ≥90% ledger-span coverage** (the freeze's own criterion).
- **E12 clock: 90 days** — H-119 accrues ~1.6 rows/day; n=100 needs ~60 days.
- **No promotion from coverage alone** — H-119 also fails `pf_ci_lb` and `IR`.

---

## 6. Doctrine to preserve

- Innocent until proven guilty; new gates only tighten *grants*, never demote
  `KILL`/`WEAK`.
- Gates fail closed; if a gate cannot be shown to kill a bad claim, it is not a
  gate.
- Keep N7 wired: no new strategy while E11/E13/E14 are open.
- Document every fix in `updates/`; push only your own files.

---

## 7. Where the detail lives

- `docs/AUDIT2_3_REVIEW_KILO_VANILLAHANDSAW_2026-11-19.md` — full review,
  per-defect owner + refs, merge order.
- `COMS_AUDIT2_3_HANDOFF_2026-11-19.md` — runnable handoff + test commands.
- `updates/2026-11-19-audit3-tribunal-f1f2-n1-n2-n3-n4-n5-n7.md` — corrected fix doc.
- Peer ground truth: `witty-fight/COMS/HANDOFF_witty-fight_2026-11-19T1700Z_audit2_audit3_correctness.md`,
  `AUDIT2_REVIEW_FOR_PEERS.md`, `REVIEW_vanilla-handsaw_audit2_audit3_2026-11-19.md`.

**Bottom line:** the statistics are on main; the honesty and plumbing are not.
Fix coverage, the audit2 deploy target, and the forward-benchmark window before
any new strategy, then run one pod (E3) for 90 days.
