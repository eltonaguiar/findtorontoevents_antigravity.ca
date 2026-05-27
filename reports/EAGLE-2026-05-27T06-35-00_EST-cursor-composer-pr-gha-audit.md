# EAGLE PR + GHA Audit — 2026-05-27 06:35 EST (Cursor Composer)

## Open PRs reviewed (6)

Comments posted on GitHub:

| PR | Title | Verdict |
|----|-------|---------|
| [#9](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/9) | CRYPTO confidence weight zero | **Superseded on main** — cherry-pick `signal_time` only after rebase |
| [#10](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/10) | Gatekeeper leakage purge | **Approve** — merge when CI green |
| [#11](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/11) | forex_carry_ppp + SL cap | **Approve** — rebase for config.py |
| [#13](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/13) | Bond scanner wiring | **Approve** — rebase after #11 |
| [#14](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/14) | trust_score NULL fix | **Approve** — fix HC parity test first |
| [#15](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/15) | WON/LOST relabel in dedup | **Approve** — complements hourly audit_won_picks_auto |

## GHA health summary (main, 2026-05-27 ~06:35 UTC)

### Stale failures (latest completed run failed — no subsequent success yet)

| Workflow | Latest run | Root cause (from logs) |
|----------|------------|------------------------|
| CI Tests | 26494657798 (new run in_progress 26495040522) | 4 pytest failures; primary: `strategy_performance.json` not git-tracked |
| DNA Mutation Cycle | 26494861980 | Git commit mutation data exit 1 |
| Deploy Competition to Live Site | 26494967890 | FTP put missing `claudes_test_state.json` |
| Audit Hourly Update | 26493315264 | Missing `claudes_test_state.json` + pipeline stale 33h |
| Mercury 2 Signal Scanner | 26493849748 | Scanner exit 1 |
| Claude Gainer ML Live Scanner | 26493348067 | Scanner exit 1 (2 consecutive) |
| Claude Code Gainer ML Tracker | 26493245187 | Live predictions step exit 1 |
| Sports endpoint smoke + Playwright | 26493202620 | Live prod: `Sports DB connection failed` |
| Claude's Test Portfolio Manager | 26492942212 | Exit 1 after stale/inverted picks |
| Forward Test Daily | 26492723980 | Needs log triage |
| [torontoevent.net] Forward Test Daily | 26492844571 | Needs log triage |
| Fast Trading Variants Master Scheduler | 26492672876 | Needs log triage |
| FINDTORONTOEVENTS.CA Database Backups | 26492629394 | Email relay 550 (backup file OK at 5.5M) |
| Pick Monitor & Price Validator (30min) | 26492622894 | Needs log triage |

### In progress (check prior run when complete)

- Copy Trader Intelligence — 26494445746
- DNA Strategy Pipeline — 26493149255
- CI Tests — 26495040522 (prior: FAIL 26494657798)
- Regime Terminal HMM — 26495047481
- Specialized Scanners — 26494972376

### Stale schedules (>48h without run)

None in the last-250-runs sample — all active workflows ran within ~2h.

### Deep scan artifact

Full log excerpts: `docs/GHA_DEEP_SCAN_LATEST_PRIOR.md` (80 workflows, latest + prior on failure).

## P0 cross-cutting fix

**`audit_dashboard/data/claudes_test_state.json`** missing from repo blocks:
- Deploy Competition FTP
- Audit Hourly Update generator

Add committed seed file or make generator fail-open when absent.

## Recommended merge stack

1. Fix CI on main (`strategy_performance.json` tracking)
2. PR #15 → #14 (with hc-parity fix) → #10 → #11 → #13
3. PR #9: close or cherry-pick `signal_time` only
