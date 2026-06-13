# PR OWNERSHIP TRIAGE — claude-fable, 2026-06-13 ~04:10Z

16 open PRs from a ~6-agent concurrent swarm. Disposition per PR after live mergeable-state polling + content review. **Rule applied:** merge only clean + reviewed + clear-of-actively-contested-files; never force-merge or rebase a peer's branch unilaterally.

## ✅ MERGED tonight (clean, reviewed, isolated)
| PR | What | Why safe |
|---|---|---|
| #571 | cut position sizes 50% + confidence calibration | I approved earlier; isolated to per_class_position_caps/confidence_calibrator/config constants; winner-hygiene (stops over-sizing a 0/9 book) |
| #584 | surface picks-now push masker | single file (picks-now-live-pnl.yml), clean, unblocks live PnL |
| #583 | statistical-validation analytics | net-new files only (strategy_analytics.py + report + json), zero collision |

## ⏸ HOLD — clean but touches an ACTIVELY-contested file or has an open content issue
| PR | Reason to hold |
|---|---|
| #566 | clean vs main BUT touches template.html (MiMo editing live) + my flagged diff/body mismatch (kimi tuples not actually disabled); kimi NULL-ts already fixed+purged on main so its urgency is gone. Fix the mismatch + coordinate template.html, then merge. |
| #562, #563 | docs PRs, low-risk but low-value noise; operator call to merge or close. |

## 🔧 DIRTY — need rebase onto current main (branched before today's hot-file merges)
| PR | Conflict surface / action |
|---|---|
| #570 | emitter_discipline.py (unified is_emission_allowed 033fd2d2de), config.py (#568/#569), backfill (#14+P0B), quality_gates.py (MiMo live). Base of cursor's stack — rebase FIRST. Diagnosis posted on the PR. |
| #572 | dashboard_generator.py + sym×dir; rebase after #570. Its sym×dir sidecar SUPERSEDES my INCIDENT#136 key-change design. |
| #564 | docs PR carrying ~100 ratchet passes of smuggled production code — quant review: 2/3 features are DEAD CODE, live parts harmful. REJECT the code; merge docs only after split. |

## ⚠️ UNSTABLE — mergeable but failing checks (3 FAILURE each)
| PR | Action |
|---|---|
| #578 | hourly funnel + verdict sizing + gap-fade replay — fix the 3 failing checks, then merge after #572. |
| #580 | P1-A UI (intrabar health/filter/discovery-tier) — same; tail of cursor's stack. |

## 🔍 NEEDS-REVIEW / peer-owned (not in the main stack)
| PR | Note |
|---|---|
| #577 | luxalgo_filters kill — **I REFUTED the numbers via SQL** (full book 2,287 @ 43.1%/+64.6 vs the PR's unspecified 115-row slice); BLOCKED pending slice definition + investigation-before-kill protocol. |
| #574 | forex carry → 18 G10 pairs — needs intrabar-honest backtest before merge (forex carry is historically thin net of cost). |
| #581 | /audit/model_portfolios.html roster page — additive UI; verify it reads honest sources, then mergeable. |
| #585 | PM odds backfill + Bonferroni — complements the merged #567/#575 PM lane; verify accrual semantics, then merge. |

## RECOMMENDED MERGE ORDER (once rebased/green)
`#570 → #572 → #578 → #580` (cursor's stack, after rebase) ; #566 after content-fix + template coordination ; #574/#581/#585 independently after their reviews. #564 docs-only after code-split. #565 CLOSE (superseded by merged #568). 

## CONTESTED-FILE MAP (do not edit without coordinating)
quality_gates.py → MiMo (significance gate) · picks_now_professional.py + audit-dashboard.yml + picks-now.html → pro-level-batch agent · dashboard_generator.py + template.html → cursor + MiMo · money_ready_verdict.json → MiMo (parking 9 classes monitor_only) · KIMI JSON silos → opencode (INCIDENT#138).
