# Branch-Split Recommendation: feat/ship-week-integrations-2026-04-21

**Date:** 2026-04-22
**Author:** Claude (Agent 2)
**For:** User triage of the 21-commit shared branch

## TL;DR

**Don't split after-the-fact.** Open ONE PR with detailed commit-group notes (below). The commits are clean, all tests pass, zero production wiring, and splitting adds friction for marginal gain.

If you MUST split (CI has a per-PR size cap, or review bandwidth requires it), use the 5 groups below — they're orthogonal.

## Current state

- 21 functional commits on `origin/feat/ship-week-integrations-2026-04-21` (excludes auto-scanner `[skip ci]` noise)
- Authored across 5 agents (ChatGPT sidecar, Agent 1, Agent 2/me, nuedxoi6, peer fixes)
- Full suite: **1,198 passed / 4 skipped / 0 regression** (per Agent 1)
- **Zero production wire-ins** — every commit is either a sidecar module, a doc, a test, or a gitignore change
- Sole HC-gate code change is the FOREX 40/55 revert (`ad81be33a2`) which already has a companion parity fix (`4c7e67d438`) and is the foundation for everything that came after

## Suggested PR groups (if splitting)

### PR-A (ship first — foundational bugfix)
Fixes the HC gate FOREX regression that blocked CI Tests on 2026-04-21.
| Commit | Title |
|---|---|
| `ad81be33a2` | fix(hc-gate): revert FOREX to 40/55 (hybrid calibration) |
| `4c7e67d438` | Fix FOREX HC fallback parity and add regression guard |

### PR-B — ChatGPT-sidecar integrations batch (2 new providers + 1 analysis doc)
| Commit | Title |
|---|---|
| `e39354a369` | feat(vectorized-backtest): Numba JIT + numpy fallback |
| `e8f5a9ea6c` | feat(ml): FinGPT-style sentiment feature |
| `afd3e21b12` | feat(bridges): OpenBB provider + Hummingbot/Freqtrade exports |
| `e2eb99e616` | Add suggested enhancements report |
| `9462bad044` | Add recent commit review mapping |

### PR-C — Agent 2 standalone tools (6 tools + reports)
Independently-callable audit/scoring primitives with 50+ passing tests. No HC-path changes.
| Commit | Title |
|---|---|
| `7cee235d8e` | feat(tools): Monte Carlo robustness analyzer |
| `fac8c8db97` | feat(tools): account-DD circuit breaker |
| `274f6318a9` | feat(alpha_engine): OpenBB earnings catalyst filter |
| `3537a1e867` | feat(tools): purged K-fold feature stability audit |
| `0b330ca896` | feat(tools): Optuna HC threshold sweep |
| `a6201c6652` | feat(alpha_engine): drift-aware scoring primitives |

### PR-D — 8-module integration pack + 70 unit tests
Landed the market_making / hifi_backtest / multi_exchange_executor / finrl_agent scaffolds. All sidecars, no prod wiring.
| Commit | Title |
|---|---|
| `e4b8052d0d` | test: add 70 unit tests for 8 integration modules (Phase 2 QA) |
| `630e1b5a59` | feat(alpha_engine): land remaining 4 of 8 integration modules |

### PR-E — Docs + infra guides + housekeeping
| Commit | Title |
|---|---|
| `fa24ef10cf` | infrastructure: Multi-asset prediction pipeline guide (docs-only per audit) |
| `8610db7ce2` | feat(monitoring): Edge monitoring & alerting implementation guide |
| `30795a41d3` | docs(analysis): Quantitative trading repo analysis |
| `41856ceed6` | chore(gitignore): suppress inflated trading-tools scaffold |
| `5ac13769b3` | docs(pr-review): Test coverage analysis & AutoHedge confidence≠edge |
| `ff0818ea71` | Add PR review recommendations for #311, #294, #288 |

## Why I recommend NOT splitting

1. **Review friction**: 5 small PRs require 5 round-trips with the same reviewer. One PR with 5 logically-grouped commits lets the reviewer choose depth.
2. **Merge order dependency**: PR-A must land first (it's a bugfix), then the rest can land in any order. A single PR makes this trivially clear.
3. **Zero shared state**: every commit touches different files except `41856ceed6` (.gitignore). No merge conflicts between the groups.
4. **Tests already passing**: the "Full suite 1198 passed / 0 regression" verdict is on the combined branch. Splitting and re-verifying each split adds risk of a split introducing a regression that the combined form doesn't have.

## If user wants to split anyway

Each group above maps to a fresh branch via `git cherry-pick` — zero conflicts. Say the word and I'll push 5 branches + open 5 PRs.

## Related

- Inherited from Agent 1's TODO list ([HIGH] Split feat/ship-week-integrations)
- User decision needed on PR #301 merge (separate branch, flat-close detector)
- PR #320 (fix/reject-exempt-safety-gate) is the priority merge target
