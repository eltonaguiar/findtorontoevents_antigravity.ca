# Kimi Audit-Gap Review — 2026-05-04

**Reviewer:** Claude Opus 4.7 (1M ctx) — read-only investigation
**Source under review:** `reports/kimi_swarm_archive_2026_05_04/findtorontoevents_swarm/audit_gap_analysis.md` (lines 1-100)
**Cross-checked against:** live `audit_dashboard/data/dashboard_data.json`, `audit_dashboard/template.html`, `alpha_engine/`, branches `feat/rr-hard-gate-shadow-2026-05-04`, `fix/today-tomorrow-week-zero-events-2026-05-04`, `fix/sports-stale-data-hardening-2026-05-04`.

---

## Per-Gap Verdicts

### Gap 1 — FOREX headline PF 0.27 vs breakdown PF 1.41 (P0)
**Verdict: NEEDS-MORE-INFO.** The repo's `dashboard_data.json` only contains the post-resolver-v2 numbers (`asset_class_health.FOREX: PF 0.27, WR 46.3%, n=1176`, file `audit_dashboard/data/dashboard_data.json`). The "breakdown PF 1.41" Kimi cites comes from a live-rendered DOM panel; I cannot reproduce it from local JSON without scraping live HTML. **Missing evidence:** the JS path that produces the per-class breakdown PF (likely `template.html:4155-4445` non-crypto panel using raw `by_asset_class`, not `asset_class_health`). If confirmed, AGREE — `by_asset_class` is pre-resolver-v2 (CLAUDE.md line "Pre-fix data is preserved in `by_asset_class` (raw); use `asset_class_health` for verdict-grade numbers"), so the dashboard is rendering both side-by-side without a label clarifying which is post-fix.

### Gap 2 — EQUITY "T2 candidate" vs older "blacklist" (P0)
**Verdict: AGREE (not a code bug, doc-bridge gap).** Live `asset_class_health.EQUITY: PF 1.42, WR 53.0%, n=421` (`dashboard_data.json`); the 2026-04-06 deep-analysis report still exists with the "blacklist EQUITY" recommendation. No bridge study published. The improvement is plausibly real (resolver-v2 + scanner expansion) but undocumented.

### Gap 3 — BOND missing from walk-forward (P1)
**Verdict: AGREE.** `dashboard_data.json walkforward.by_class` keys = `['ETF','CRYPTO','FOREX','COMMODITY','EQUITY']`. BOND absent. BOND has n=18 in `asset_class_health` (below typical fold-floor) but the table omits BOND silently. `template.html:865` already has a graceful "no data" message; just needs BOND to render with an "insufficient folds" stub.

### Gap 4 — Negative OOS Sharpe with no halt action (P1)
**Verdict: AGREE.** `walkforward.by_class` shows COMMODITY/CRYPTO/FOREX with negative `oos_sharpe`. `template.html:838` color-codes red but no auto-recommendation. Grep for `negative.*sharpe|sharpe.*halt` returns no production handler.

### Gap 5 — Score 60-79 inversion never recalibrated (P1)
**Verdict: NEEDS-MORE-INFO.** No grep hit for `direction.*multiplier` or `SHORT.*bias` in `alpha_engine/`. Likely AGREE-not-fixed but I have no closed-pick re-cut to confirm the inversion still holds post-resolver-v2.

### Gap 6 — Phase 4 risk-adjusted metrics missing (P1)
**Verdict: AGREE.** No `regime_decomposition`, `block_bootstrap_pf`, or `net_of_cost_pf` keys in `dashboard_data.json`. `template.html` still shows the "pending" disclaimer.

### Gap 7 — TIER-2 PROVEN badge applied to n<100 strategies (P1)
**Verdict: AGREE.** `template.html:918` literal text `🏆 TIER-2 PROVEN`. CHARTER §2 floor n≥100. Renaming is a 1-line label change.

### Gap 8 — Trust scores inverted (P2)
**Verdict: NEEDS-MORE-INFO.** Source claim is from 2026-04-06 deep-analysis. No subsequent calibration study in `reports/`. Cannot verify current state without a re-cut over post-resolver-v2 closed picks.

### Gap 9 — MFE/MAE schema missing (P2)
**Verdict: AGREE.** Grep `max_favorable_excursion|max_adverse_excursion|MFE|MAE` over `alpha_engine/` returns zero hits in production code paths. Schema not plumbed.

### Gap 10 — Regime decomposition 3×3 grid missing (P2)
**Verdict: AGREE.** No regime-grid keys in `dashboard_data.json`. Not rendered on `/audit`.

### Gap 11 — HyroTrader `trading_days_logged = 0` (P0)
**Verdict: AGREE.** `audit_dashboard/data/hyrotrader_picks.json account_snapshot.trading_days_logged = 0`, `cumulative_pnl_usdt = -70.66`, `last_session_date = 2026-04-08`. Manual entry stale 26 days. `hyrotrader_journal.json` DOES exist (contradicting Gap 12) so trading-days could be inferred.

### Gap 12 — `hyrotrader_journal.json` missing (P1)
**Verdict: DISAGREE.** File exists at `audit_dashboard/data/hyrotrader_journal.json`. Kimi missed it. (May still be empty; not opened — partial AGREE if so.)

### Gap 13 — `largest_single_day_profit_usdt` null (P1)
**Verdict: AGREE.** Confirmed null in `account_snapshot`.

### Gap 14 — Hyro picks have null entry/SL/TP (P1)
**Verdict: AGREE.** All 7 picks in `hyrotrader_picks.json` have null price fields per inspection.

### Gap 15 — Hyro quan bridge truncated to 1 symbol (P0)
**Verdict: AGREE.** `hyro_quan_bridge.json generated_at = 2026-04-18T22:18Z` (16 days stale), `symbols = ['BTCUSDT']` only, `_repair_note` confirms ETH+13 dropped. Critical.

### Gap 16 — Stale-data quality gate too permissive (P1)
**Verdict: AGREE.** Watchdog workflows exist (`asset-class-freshness-watchdog.yml`, `ml-staleness-watchdog.yml`) but Gap 15 proves they are not catching the quan-bridge truncation in production.

### Gap 17 — FOREX has no remediation plan (P1)
**Verdict: ALREADY-PARTIALLY-ADDRESSED.** `updates/2026-04-25-forex-tpsl-review.md` and `reports/forex_resolver_ab_2026-02-01_2026-04-29.md` exist. No formal kill-date doc. CLAUDE.md mandates mutate-before-kill via `docs/MUTATION_THREE_AXIS_PROTOCOL.md`. AGREE that no consolidated remediation plan with kill-date is published.

### Gap 18 — `ASSET_CLASS_EDGE_ANALYSIS.json` stale (P2)
**Verdict: AGREE.** mtime = 2026-04-12 (22 days stale). Live n=8116 CRYPTO vs JSON n=2670 → ~3× drift confirmed.

---

## Branch Cross-Check (recently landed)
- `feat/rr-hard-gate-shadow-2026-05-04` (149fbacd375) — R:R 1.5–2.0 hard gate, shadow mode default-OFF. Does NOT address any of the 18 gaps directly.
- `fix/today-tomorrow-week-zero-events-2026-05-04` (d85e6fd6b6e) — homepage event chip bug, Goal #3, unrelated to /audit gaps.
- `fix/sports-stale-data-hardening-2026-05-04` (40f98fe0331) — sports per-card 24h stale gate. Tangentially related to Gap 16's stale-gate philosophy but does not touch Hyro pipeline.

**No landed branch fixes any of Gaps 1-18.**

---

## AGREE-not-fixed → Proposed PRs

### PR-A: `fix/hyro-quan-bridge-atomic-write-2026-05-04` (Gap 15, P0)
- Edit `tools/hyro_quan_bridge.py`: wrap final write in `tempfile.NamedTemporaryFile` + `os.replace`; assert `len(symbols) >= 15` before commit, raise on violation.
- Edit `.github/workflows/asset-class-freshness-watchdog.yml`: add explicit assertion step `python -c "import json; assert len(json.load(open('audit_dashboard/data/hyro_quan_bridge.json'))['symbols'])>=15"`.
- Manually regenerate `audit_dashboard/data/hyro_quan_bridge.json` (or trigger workflow).
- Add unit test `tests/test_hyro_quan_bridge_atomic.py` covering truncation rollback.

### PR-B: `fix/audit-dashboard-headline-source-clarity-2026-05-04` (Gap 1, P0)
- Edit `audit_dashboard/template.html` ~line 4155 (non-crypto panel): label per-class breakdown rows as "raw `by_asset_class` (pre-resolver-v2)" vs `asset_class_health` (post-fix).
- Add a banner row reconciling deltas where `|raw_pf - health_pf| > 0.5`.
- Edit `audit_trail/dashboard_generator.py` to compute & emit `asset_class_reconciliation` block to `dashboard_data.json`.

### PR-C: `chore/hyro-trading-days-from-journal-2026-05-04` (Gap 11+13, P0)
- Edit `tools/hyro_pick_performance_validator.py` (or appropriate writer) to derive `trading_days_logged` and `largest_single_day_profit_usdt` from `hyrotrader_journal.json` distinct dates / max daily PnL.
- Edit `audit_dashboard/template.html` (hyrotrader subpage): red banner when `trading_days_logged==0 && cumulative_pnl_usdt!=0`.
- Re-run validator to backfill `audit_dashboard/data/hyrotrader_picks.json`.

### PR-D: `feat/walkforward-bond-row-2026-05-04` (Gap 3, P1)
- Edit `alpha_engine/walkforward_validator.py walk_forward_by_class()` to emit BOND row with `status: "insufficient_folds", min_n_required: <n>` when sample is too small.
- Edit `audit_dashboard/template.html:862` renderer to display "insufficient data" stub instead of skipping the class.

### PR-E: `chore/tier2-proven-badge-honesty-2026-05-04` (Gap 7, P1)
- Edit `audit_dashboard/template.html:918` — change `🏆 TIER-2 PROVEN` to `🏆 TIER-2 CANDIDATES` while charter floor n=100 is unmet for any displayed strategy.
- Edit `audit_trail/dashboard_generator.py::_compute_tier2_proven_strategies` — auto-suppress strategies with n<100 from this hero panel; emit them in a separate "Building" tray.

### PR-F: `fix/edge-analysis-json-staleness-ci-2026-05-04` (Gap 18, P2)
- Add `tools/regen_asset_class_edge_analysis.py` (or wire existing).
- Add CI step that fails if `ASSET_CLASS_EDGE_ANALYSIS.json` mtime > 7 days older than newest closed pick.

### PR-G: `feat/oos-sharpe-halt-recommendation-2026-05-04` (Gap 4, P1)
- Edit `audit_trail/dashboard_generator.py` walkforward post-processor: when `oos_sharpe < 0`, set `recommendation: "halt-new-entries"` per class.
- Edit `audit_dashboard/template.html:838` to render alert banner inheriting summary-card severity.

---

## Top-3 PR Priority

1. **PR-A — Hyro quan bridge atomic write + 15-symbol assert (Gap 15).** Critical: 16-day staleness + truncation breaks `hyrotrader_live_freshness.spec.ts` and the consensus engine. Highest blast radius, smallest fix.
2. **PR-B — Headline-vs-breakdown reconciliation (Gap 1).** Credibility-critical. The same page contradicts itself; one PR ends the confusion by labeling sources and surfacing deltas.
3. **PR-C — Hyro trading-days + largest-day inference (Gaps 11, 13).** Compliance-critical (challenge consistency rule). Journal already exists (counter to Kimi Gap 12), so this is just plumbing.

PRs D-G are batched as a follow-up sprint (governance hygiene; not credibility-critical to /audit users this week).

---

## Notes / Assumptions
- All file paths are absolute under `c:/findtorontoevents_antigravity.ca/`.
- Did not run any generator or git mutating command per constraints.
- Gaps 5 and 8 marked NEEDS-MORE-INFO require a re-cut over post-resolver-v2 closed picks — recommend a separate read-only analysis spike before opening PRs.
- Gap 12 is DISAGREE — `audit_dashboard/data/hyrotrader_journal.json` is present in the tree.
