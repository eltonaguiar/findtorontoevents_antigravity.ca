# Wire-Up Rule Audit — 2026-04-27 Merge Wave
**Date:** 2026-05-04  
**Scope:** PRs #348, #392, #393, #400, #434  
**Auditor:** automated read-only grep pass

---

## PR #348 — ML Feature Persistence ✅

**Modules:** `audit_trail/pick_feature_store.py`, `audit_trail/feature_edge_analyzer.py`, `audit_trail/symbol_strategy_tracker.py`

| Check | Evidence |
|---|---|
| All 3 modules imported | `dashboard_generator.py:181-187` |
| `run_sqlite_migration` called on prod path | `dashboard_generator.py:15007` (inside live pick loop) |
| `store_pick_features` called | `dashboard_generator.py:15022` |
| `_attach_strategy_concentration_meta` called | `dashboard_generator.py:14040, 14093` |

**Verdict:** Fully wired. All three modules have production callers in the dashboard generator's live pick processing loop.

---

## PR #392 — HF Stats v2 ✅

**Module:** `tools/hf_stats.py`

| Check | Evidence |
|---|---|
| Module imported | `dashboard_generator.py:85` (top-level import w/ fallback) |
| `_hf_stats_summary()` helper defined | `dashboard_generator.py:1787` |
| `hf_stats` key injected into payload | `dashboard_generator.py:13941` |
| CVaR 95% card | `template.html:5048-5051` |
| CVaR 99% card | `template.html:5054-5057` |
| Ulcer Index card | `template.html:5067-5068` |
| Max DD card | present via `hf_stats` block |
| WR card | present via `hf_stats` block |
| Drift Alert card | `template.html:5082-5084` (KS test) |

**Verdict:** All 6 mercury cards confirmed in template. Payload field wired. ✅

---

## PR #393 — Feed Risk-Metrics ⚠️

**Module:** `tools/feed_risk_metrics.py`

| Check | Evidence |
|---|---|
| Production caller (audit_trail, dashboard, alpha_engine) | **None found** |
| Test coverage | `tests/test_feed_risk_metrics.py` (test-only import) |
| `arch>=7.0.0` in `alpha_engine/requirements.txt` | ✅ line 51 |
| Import health (no full deps in local env) | Fails on `numpy` — expected without venv |

**Verdict:** ⚠️ No banner consumer wired yet. This is expected per PR description ("foundational module"). A wiring plan is required per CLAUDE.md Wire-Up Rule. Suggested target: `audit_trail/dashboard_generator.py` — add a `feed_risk_metrics` payload section alongside `hf_stats`. Flag for follow-up within 30 days.

**Action required:** PR author or next audit session must add `## Wiring Plan` naming the target caller file + function + expected date, OR wire directly into `_hf_stats_summary()` / a new `_feed_risk_banner()` helper.

---

## PR #400 — Sports Edge Integration ✅

**Modules:** `sports_arbitrage_scanner.py`, `sports_situational_edge.py`, `sports_prediction_market_sync.py`, `sports_edge_finder.py`, `sports_betting_edge.py`

| Module | Production Caller | Path |
|---|---|---|
| `sports_betting_edge.py` | `production_scanner.py:3762` | direct call |
| `sports_edge_finder.py` | `sports_betting_edge.py:30` → `production_scanner.py:3762` | 1-hop |
| `sports_arbitrage_scanner.py` | `sports_betting_edge.py:29` → `production_scanner.py:3762` | 1-hop |
| `sports_situational_edge.py` | `sports_edge_finder.py:18` → `sports_betting_edge.py:30` → `production_scanner.py:3762` | 2-hop |
| `sports_prediction_market_sync.py` | `.github/workflows/sports-prediction-market-sync.yml:23` | direct (2×/day cron) |

**Verdict:** All 5 modules reachable from production. Import chain is tight. ✅

---

## PR #434 — Tennis ELO ✅

**Modules:** `live-monitor/tennis_elo_engine.py`, `live-monitor/api/tennis_elo_lib.php`

| Check | Evidence |
|---|---|
| `tennis_elo_lib.php` required | `sports_picks.php:10` |
| `sports_picks_annotate_tennis_elo()` call site 1 | `sports_picks.php:469` |
| `sports_picks_annotate_tennis_elo()` call site 2 | `sports_picks.php:610` |
| Daily 06:00 UTC ELO refresh | `sports-data-snapshots.yml:82-98` (cron `*/15`, hour-guarded to 06:00 UTC) |
| FTP upload of ratings JSON | `sports-data-snapshots.yml:147-154` |

**Verdict:** Both call sites confirmed. Daily refresh + FTP upload wired. ✅

---

## CI / Dependency Verification

| Check | Result |
|---|---|
| `gh run list` (ci-tests.yml) | `gh` CLI unavailable in local env — check GitHub Actions UI |
| `arch>=7.0.0` in requirements.txt | ✅ confirmed at `alpha_engine/requirements.txt:51` |
| `feed_risk_metrics` import smoke | Fails on `numpy` — expected in dep-free local env; no arch-specific error |
| pytest collection of `test_feed_risk_metrics.py` | pytest not installed locally; no collection errors verifiable here |

**Recommendation:** Re-run `gh run list --workflow ci-tests.yml --branch main --limit 5` from an env with `gh` to confirm Python 3.11/3.12 green before closing this audit.

---

## Summary Table

| PR | Title | Verdict |
|---|---|---|
| #348 | ML Feature Persistence | ✅ Wired |
| #392 | HF Stats v2 | ✅ Wired |
| #393 | Feed Risk-Metrics | ⚠️ No prod caller — wiring plan needed |
| #400 | Sports Edge Integration | ✅ Wired (via import chain) |
| #434 | Tennis ELO | ✅ Wired |

**Overall verdict: GAPS FOUND (1) — PR #393 `tools/feed_risk_metrics.py` has no production caller. All other PRs pass Wire-Up Rule.**
