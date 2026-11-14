# Final V3 independent review

**Review date:** 2026-11-14
**Worktree:** `feat/stop-fill-cost-gate-final-v3`
**Purpose:** adjudicate local peer reports, remote GitHub reports, financial backtest code, and the proposed path to a measurable asset-class edge.

## Bottom line

No asset class is established as reliably profitable by the evidence reviewed here. Prioritize **EQUITY** and **CRYPTO** as research tracks, not as proven money-making sleeves:

1. **EQUITY:** test a diversified, point-in-time factor portfolio against a risk-matched total-return benchmark. Positive results reported in one closed-pick cohort do not override conflicting official and registry metrics.
2. **CRYPTO:** first establish valid prices, fills, and cohort definitions. Then test trend and funding carry as separate pre-registered hypotheses. The stop-fill correction may improve measurement; it does not create alpha.
3. Keep **FUTURES** as a later candidate only after obtaining a real continuous-contract/roll-adjusted feed.

Treat mutual funds as a passive allocation or benchmark sleeve, not a prediction class. Low investor minimum, expense ratio, fund AUM, and capital needed are different things.

## Coverage and limitations

- Reviewed key local `final_v3` reports, the six-file remote `final_v3/finpredict` package at commit `d18adb510ab1`, selected remote `final_v2` / `final_2026_11_14` decision reports, and a read-only source audit of the listed backtest and mutual-fund modules.
- Local dated report scan at the final scan: 140 Markdown paths, 135 byte-unique documents, 5 duplicate paths suppressed.
- Remote `final_v2` + `final_2026_11_14` tree at main `086f410713ecd6cb3feec2735b224670418c0588`: 470 Markdown paths, 309 unique Git blob SHAs. The remote peer review skimmed selected decision-bearing documents, not all 309 unique documents. Raw/generated artifacts and most source/data files were not individually read.
- No tests, model training, backtests, scanners, dashboard generators, or database writes were run. Performance and replay figures attributed to peer reports are labeled as reported, not independently reproduced.
- No verifiable SubQ invocation or response artifact was available. See `04-subq/STATUS_AND_COVERAGE.md`.

At the final check, the shared worktree had 602 dirty paths and this branch was 234 commits behind / 3 commits ahead of its local `origin/main` reference. The worktree was changing concurrently; this review added 11 report files and did not pull, reset, clean, or alter existing peer files.

## Package map

- `00-common-themes/ADJUDICATION.md` - shared findings, conflicts, and confidence labels.
- `01-inventory/SCOPE_AND_COVERAGE.md` - local and remote inventory, source code reviewed, and gaps.
- `02-improvement-plan/` - prioritized general, GitHub Actions, asset-class, and simulation todos.
- `03-focus/` - focus decision and mutual-fund screening criteria.
- `04-subq/STATUS_AND_COVERAGE.md` - what was and was not compared with SubQ.
- `05-evidence/INDEX.md` - source paths, snapshot identifiers, and verification limits.

