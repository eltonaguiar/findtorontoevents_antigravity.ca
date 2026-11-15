# 02 — Open Pull Requests Triage (35 open)

Sorted by action. `mergeable` reflects GitHub's merge state at review time.

## A. Merge now (actionable, unblocking)

| PR | Title | Branch | Why |
|---|---|---|---|
| **#713** | fix(ci): backup-verify false failures + issue spam; speed up dup-guard scan | `fix/ci-backup-verify-and-dupguard` | Kills the 42-issue spam and the broken backup-verify check. Open 6 weeks — merge now. |
| **#786** | fix(ci): restore QA price validation, snapshot pushes, and sports smoke | `wired-in/buffy-gh-actions-fix-2026-11-15` | Fixes sports-smoke (ubuntu pin), QA validation (API keys), and snapshot-push rebase. **Precondition:** confirm `FINNHUB_API_KEY`/`TIINGO_API_KEY`/`TWELVE_DATA_API_KEY`/`ALPHA_VANTAGE_API_KEY`/`FMP_API_KEY` are actually set as repo secrets. |
| **#785** | Restore audit page script tags lost on main + tracker horizon fix | `wired-in/buffy-2026-11-15-final` | Delta-only; restores `excess_column.js`/`forward_clock.js` tags and fixes naive/aware timestamp TypeError. CI already green on it. |

## B. Rebase then merge

| PR | Title | Branch | Note |
|---|---|---|---|
| **#758** | Fix BTC evaluator daily drawdown and unsupported gate passes | `fix/ghcopilot-btc-mtm-guard` | `mergeable=CONFLICTING` — rebase onto current `main`, then merge. |

## C. Review before merge (higher scrutiny)

| PR | Title | Branch | Note |
|---|---|---|---|
| **#761** | fix: rotated FTP credentials, no embedded password defaults, verified FTPS | `fix/ghcopilot-ftp-credential-loading` | Security-sensitive (credential rotation). 21 tests pass. Needs a second pair of eyes on the loader before merge. |
| **#756** | Fix DSR>1 + resolver batch-close/flat-exit bugs | `fix/grok-quickfixes-dsr-resolver` | Touches resolver; relates to open issue **#748** (flat-close bug). |
| **#749** | fix(resolver): true TP/SL exit time + UNRESOLVED_NO_PRICE | `buffy/batch-close-rootcause` | Also relates to #748 — coordinate with #756 to avoid resolver conflicts. |

## D. Close stale / abandon (no longer relevant)

Docs-only or research that predates the current `WIRED_IN/` profitability conclusion:

| PR | Title | Age |
|---|---|---|
| #562, #564, #581, #595, #600, #657 | edge-hunt / audit docs (June 2026) | ~5 months |
| #665, #666, #667 | stalled-producer / B1 backfill / forward-track cell (June 2026) | ~5 months |
| #696, #700, #701 | discord webhook / LLM routing / pick rationale (Oct 3–4) | stale |
| #711, #735, #736 | staleness / asset-class cache / fc-weather (Oct) | stale |
| #744, #745, #746, #747, #750, #751 | blacklist / audit-empty / KPI spec / crypto money-ready / bond yield / GHA health | stale |
| #757, #759 | scorecard / 95-fund durability | stale |
| #760 | fund walk-forward review fixes (research, FXAIX vs SPY) | research only — fold conclusions into docs, close PR |
| #762, #763, #765, #766 | job scans / weather watchlist / skills docs | content only — merge-or-close at owner discretion |

## E. Summary

- **Merge now:** #713, #786, #785
- **Rebase + merge:** #758
- **Review + merge (coordinate resolver):** #761, #756, #749
- **Close/abandon:** ~20 PRs (June–Oct, superseded by the `WIRED_IN/` profitability work)

The overwhelming pattern: **35 PRs with ~4 real fixes and ~20 stale research branches.** PR backlog is itself a liability — a scheduled `stale-branch-cleanup` pass would prevent this from recurring.
