# IDEA-H (PM macro correlation) — Progress Tracker

Owner: claude-fable session 2026-06-12 (DAILY_IDEAS action-item sweep, isolated worktree).
Scope: the remaining open pieces of DAILY_IDEAS 2026-05-24 IDEA-H (highest-scored brainstorm idea, 7.5/10).
Peer lane (NOT tracked here): audit-surface review items — see the PEER COORDINATION block at the bottom of `DAILY_IDEAS.MD` (commit `5b393bc019`).

## Status board

| # | Item | Status | Evidence |
|---|------|--------|----------|
| 1 | DAILY_IDEAS staleness triage (pre-June items) | ✅ DONE 2026-06-12 | Nearly all stale/done: mysql-trading-sync `\|\| non-fatal` fixed; BOND universe already 14 symbols (`alpha_engine/config.py:1076`, since 2026-04-17); COMMODITY GC=F/SI=F/ZS=F added (CL=F deliberately killed, 3.8% WR); `growth_stock_screener.py` already built+wired; `/thingstocheck_June2026` skills exist; SPORTS class absent. Memory: `project-pm-leadlag-overlay-bug-2026-06-12` |
| 2 | PM odds history capture (`pm_odds_history.py`) | ✅ PR #567 | Daily Kalshi+Polymarket macro-odds snapshots → `prediction_market_agents/data/pm_odds_history.jsonl`; idempotent per (date, platform, market_id); 45 markets seeded 2026-06-12; persists via existing `git add prediction_market_agents/data/` in alpha-engine-live.yml |
| 3 | Lead/lag analyzer (`pm_lead_lag_analyzer.py`) | ✅ PR #567 | Pearson Δodds vs TLT/EURUSD=X returns, lags −3..+3, ≥20-day + ≥10-pair gates, \|r\|≥0.30; verdicts LEADING/COINCIDENT/REACTIVE/NO_SIGNAL; `--self-test` passes (synthetic 1-day-leading odds → LEADING lag=1 r=0.9993) |
| 4 | pm_macro_overlay fetcher fix (Phase 1 was a silent no-op) | ✅ PR #575 MERGED | Live-verified 2026-06-12 20:00Z: `Kalshi KXFEDDECISION-26JUN: cut=2.0% hike=2.0% hold=98.0%` + `Polymarket meeting 2026-06: cut=0.5% hike=0.9% hold=98.6%` → consensus HOLD, 0 picks (correct). Pre-fix: both fetchers returned None every run since 2026-06-06 |
| 4b | picks-now masking surface (CI unblock surfaced by #567) | ✅ PR #584 | `::warning` on the swallowed picks-now push; lint-masking back to 0 NEW silent maskers |
| 5 | First eligible lead/lag report (`status: OK`) | ✅ DONE EARLY 2026-06-13 | Skipped the ~3-week cron wait via historical **backfill** (`pm_odds_history.py --backfill`: Polymarket CLOB + Kalshi candlesticks, 20,958 daily rows, 149 markets eligible). Report is `status: OK`. See findings doc |
| 6 | Wire lead/lag verdicts into production | ❌ NO-EDGE — NOT pursued | `reports/PM_LEADLAG_FINDINGS_2026-06-13.md`: 20 raw-LEADING, **0 survive Bonferroni** (α=1.7e-4, 298 tests); the only correction-surviving correlations are COINCIDENT/REACTIVE (odds follow the market). No leading edge to wire. `pm_macro_overlay`'s contemporaneous-consensus design is vindicated. Analyzer now emits `best_p_uncorrected` + `bonferroni_significant` |
| 7 | Phase-1 60-day acceptance checkpoint | ⏳ ~2026-08-11 | Criteria (module docstring): PF≥1.25 AND WR≥50% on ≥30 resolved → promote; PF<1.0 OR n<10 → deactivate. **Clock restarts 2026-06-12** — the first day signals could actually flow (it was broken 06-06→06-12). Do NOT deactivate on the 06-06 clock |
| 8 | IDEA-H Phase 2 (election/geopolitical, ~200 LOC) | 🚫 GATED | Per the documented MVP-first plan: do not build until Phase 1 passes its paper-trade gate (#7) |

## Bug record (for anyone touching PM fetchers)

`pm_macro_overlay.py` emitted 0 signals from launch (2026-06-06) to fix (2026-06-12). Three causes, all API schema drift, all verified live:
1. Kalshi v2 markets report `status: "active"` — old code filtered for `"open"`, excluding everything.
2. Kalshi prices are string-dollar fields (`last_price_dollars`, `yes_bid_dollars`) + `volume_fp` — old code read legacy cent-int `yes_bid`/`last_price`/`volume`.
3. Polymarket `/markets?search=` ignores the search param (returns unrelated markets); the working endpoint is `/public-search?q=` (events with nested markets; filter `closed`; `endDate` unreliable — parse meeting month from question text).

Semantic upgrade in the fix: Kalshi `KXFEDDECISION` series has explicit per-meeting Cut/Hike/Hold legs (ticker suffix C25/C26/H0/H25/H26) — probabilities are summed per action instead of keyword-classifying market titles (the old approach mapped strike-threshold KXFED markets to "hold" unconditionally).

## Reproducers

```bash
# capture one day of odds snapshots (idempotent)
python3 prediction_market_agents/pm_odds_history.py

# lead/lag report (writes INSUFFICIENT_HISTORY until ~2026-07-03)
python3 prediction_market_agents/pm_lead_lag_analyzer.py
python3 prediction_market_agents/pm_lead_lag_analyzer.py --self-test  # no network

# fixed overlay — logs real per-platform cut/hike/hold probabilities
python3 prediction_market_agents/pm_macro_overlay.py
```

## Next-session checklist

- [ ] Merge PR #567 + the overlay-fix PR (independent; no file overlap).
- [ ] After ~2026-06-15: confirm `pm_odds_history.jsonl` is accruing rows from CI (3+ distinct dates).
- [ ] After ~2026-07-03: check `pm_leadlag_report.json` flips to `status: OK`; if any market is LEADING, open the wire-up PR (#6 above).
- [ ] 2026-08-11: run the Phase-1 acceptance checkpoint (#7) on the restarted clock.
