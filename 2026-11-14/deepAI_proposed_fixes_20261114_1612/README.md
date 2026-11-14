# deepAI — Proposed fixes for the /audit prediction system (2026-11-14 16:12 UTC)

Author: DeepAI Code audit agent (branch `audit/live-audit-2026-11-14`, worktree `.inspect-wt`).
This folder contains **suggestions only** — no core files were modified. Companion evidence:
`2026-11-14/inspect-wt_20261114_1058/` (findings) and `reports/live_audit_2026-11-14/`.

Patches are unified diffs against base `f54efb3b4a` (the worktree's HEAD). Origin/main has moved
since June; expect to rebase. Apply with `git apply` or cherry-pick manually.

## Peer cross-check (2026-11-14) — read `cross_check_and_merge.md` first

Reviewed peer work in `reports/` (1,689 files), `docs/`, `updates/`, `.planning/`. Three
corrections to my original audit, now applied to the fixspecs:
1. **Zero-PnL root cause** = `TIME_EXPIRED` resolver writing pnl=0 in `backfill_widened/updated`
   (peer `zero_pnl_data_pipeline_audit_2026-06-05.md`), not "spot flicker". Fix = re-resolve that
   cohort + compute close-vs-entry.
2. **Surface disagreement** = `NOMINAL_TP_LEGACY` (clean TP assumption) vs intrabar-truth replay
   (28–100% of TPs were actually SLs, peer `PAPER_PILOT_RESOLVER_FAIL_2026-06-05.md`). Intrabar is
   authoritative.
3. **MISSED EDGE** = `mega_mutation::crypto` is the one T1-confirmed edge (peer n=295 WR 64.1%
   PF 3.16; my Nov data confirms PF 3.20 in-window / 1.58 last-30d). Must be the pilot candidate.
Plus: peer-specified source bans are still unenforced (live check finds `luxalgo_filter`,
`prediction_market*` still emitting); `trading_picks` 2026-06-04 backfill caveat applies to my
registry numbers; Playwright found 3 live bugs (`strategy_tribunal_latest.json` 404, brand-new
CORS failures, funds.html stuck "Prices: Loading...").
New files: `cross_check_and_merge.md`, `playwright_live_js_report.md`,
`per_asset_class/crypto/quick_wins_and_proposed_fix.md`.

## Priority order

### P0 — silent-data breaks (user sees wrong numbers today)
1. **hyro_pick_performance.json 157h stale while "Hyro daily" reports success.**
   Fix: patch `0001-hyro-pick-perf-freshness-tripwire.patch` adds a freshness tripwire entry.
   Plus investigate (needs admin log): does `tools/hyro_pick_performance_validator.py --save`
   actually write `audit_dashboard/data/hyro_pick_performance.json`, and does the FTP glob
   upload it? (fixspec_actions_remediation.md §1)
2. **pick_funnel_snapshot.json serves a 404 HTML page on the live site.**
   Any panel sourcing it is broken. Fix spec: ensure the file is generated each run and added to
   the FTP deploy list; add to tripwire. (fixspec_actions_remediation.md §2)
3. **Garbage entry prices emitted live** (BTCUSDT entry=0.3322/1.334; XRPUSDT entry=0.0 by
   `prediction_market_consensus` 90 min before fetch). Ingest-side guard spec:
   fixspec_garbage_price_ingest_guard.md
4. **Zombie re-emission flood**: 2,262 EXPIRED pnl-0 rows from `inverse_mutations` alone;
   79% of active_raw is dead. Fix spec: fixspec_zombie_purge_and_reemission_guard.md

### P1 — stats credibility (surfaces disagree 2–4x per class)
5. **Single canonical ledger**: one dedup'd closed-trade table feeding pf_registry,
   money_ready_verdict, surface_truth, hf_stats — currently each computes its own.
   Fix spec: fixspec_single_canonical_ledger.md
6. **Spot-flicker artifacts**: 3,872/28,719 closed rows were |pnl|<0.02bps zero-delta artifacts.
   Don't count them as closed; re-price instead. Fix spec: fixspec_spot_flicker_resolver.md
7. **Surface-disagreement banner** on the dashboard: show registry-vs-money_ready PF per class
   side by side; block "best strategy" highlights for classes with >2x spread.
   Fix spec: fixspec_surface_disagreement_banner.md

### P2 — validation integrity
8. **Reality Check never runs** (`arch` package missing) and PBO is computed on 21 observations;
   69/80 strategies OVERFIT_LIKELY. Fix spec: fixspec_antioverfit_arch_dep.md
9. **Walk-forward by_class panel**: was MISSING (April–June INCIDENT #45). Validator ordering was
   fixed in the workflow; verify by_class is emitted and make the tripwire blocking for it.

### P3 — honesty of scope
10. **Mutual funds are vaporware** (no live picks, no ranker file). Either remove the claim from
    the page or build `alpha_engine/mutual_fund_ranker.py`. Fix spec: fixspec_mutual_fund_vaporware.md
11. **Failing workflows**: Alpha Engine Live (full-cycle step), Daily Prices yfinance (2 nights),
    CI Tests, audit-dashboard queue-cancel cadence. Fix spec: fixspec_actions_remediation.md §3–5
12. **Regime layer empty**: with_regime_data=0 / 8,538 closed rows without regime. Backfill or
    drop regime-conditioned claims from the UI.

## Folder structure
```
deepAI_proposed_fixes_20261114_1612/
├── README.md                      ← this file
├── patches/                       ← apply-able unified diffs (anchor-verified @ f54efb3b4a)
│   └── 0001-hyro-pick-perf-freshness-tripwire.patch
├── fixspecs/                      ← cross-asset fix specs
│   ├── fixspec_actions_remediation.md
│   ├── fixspec_antioverfit_arch_dep.md
│   ├── fixspec_garbage_price_ingest_guard.md
│   ├── fixspec_mutual_fund_vaporware.md
│   ├── fixspec_single_canonical_ledger.md
│   ├── fixspec_spot_flicker_resolver.md
│   ├── fixspec_surface_disagreement_banner.md
│   └── fixspec_zombie_purge_and_reemission_guard.md
└── per_asset_class/
    ├── _overall_dashboard/quick_wins_and_proposed_fix.md   ← cross-asset quick wins A–F
    ├── crypto/                    ← subagent output (quick wins + proposed fix)
    ├── equity_etf_bond/           ← subagent output
    └── forex_futures_commodity/quick_wins_and_proposed_fix.md  ← main-agent (anchors verified)
```

## Deliberately NOT done here
- No core-file edits (per instruction).
- No strategy-code changes: the master-plan agent should decide which of the 6 EDGE_LIKELY_REAL
  strategies survive before any per-strategy patching.
