# GHA Prediction Market JSON Missing — Investigation Findings

**Date:** 2026-11-16
**Workflow:** `.github/workflows/polymarket-signals.yml` (lines 83-88)
**Repo:** eltonaguiar/findtorontoevents_antigravity.ca

## Summary

**No filename mismatch was found.** The workflow `git add` paths match the scripts' output paths exactly. The missing files (`alpha_engine/data/polymarket_signals.json`, `alpha_engine/data/kalshi_signals.json`) are absent because the producing scripts have not been run successfully in this worktree — not because of wrong filenames or wrong output paths.

The workflow already handles missing files gracefully via `2>/dev/null || true` on each `git add`, so the commit step does not fail — it simply skips adding those files.

## Files: Expected vs Actual

### Workflow `git add` targets (polymarket-signals.yml:83-88)

| Workflow path | Exists? | Produced by |
|---|---|---|
| `alpha_engine/data/polymarket_signals.json` | **NO** | `alpha_engine/polymarket_signals.py` (OUTPUT_FILE line 29) |
| `alpha_engine/data/kalshi_signals.json` | **NO** | `alpha_engine/kalshi_signals.py` (OUTPUT_FILE line 31) |
| `alpha_engine/data/prediction_market_picks.json` | YES (4061 B, 02:52) | `alpha_engine/prediction_market_consensus.py` (OUTPUT_FILE line 32) |
| `alpha_engine/data/prediction_market_whales.json` | YES (5305 B, 02:52) | `alpha_engine/prediction_market_whales.py` |
| `copy_trader_intel/data/polymarket_trader_profiles.json` | YES (63560 B, 02:52) | `copy_trader_intel/polymarket_scraper.py` |
| `copy_trader_intel/data/polymarket_picks.json` | YES (7085 B, 02:52) | `copy_trader_intel/polymarket_scraper.py` |

### Dashboard `JSON_PICK_SOURCES` (audit_trail/dashboard_generator.py:4083-4094)

| Registry key | Registered path | Exists? |
|---|---|---|
| `polymarket_signals` | `copy_trader_intel/data/polymarket_picks.json` | YES |
| `pm_momentum_signals` | `prediction_market_agents/data/momentum_signals.json` | **NO** |
| `pm_whale_signals` | `prediction_market_agents/data/whale_signals.json` | **NO** |
| `pm_kalshi_signals` | `prediction_market_agents/data/kalshi_signals.json` | **NO** |

### `prediction_market_agents/data/` contents

Files present: `orchestrator_summary.json`, `pm_leadlag_report.json`, `pm_macro_overlay_signals.json`, `pm_odds_history.jsonl`, `polymarket_strategy_audit.json`, `whale_alerts.json`, `whale_tracker.json`.

Missing: `momentum_signals.json`, `whale_signals.json`, `kalshi_signals.json` — none exist, and no workflow step produces them.

## Root Cause Determination

**Not a workflow bug (wrong filenames):** Lines 83-84 of `polymarket-signals.yml` specify `alpha_engine/data/polymarket_signals.json` and `alpha_engine/data/kalshi_signals.json`, which match `OUTPUT_FILE` in `polymarket_signals.py:29` and `kalshi_signals.py:31` respectively.

**Not a script bug (wrong output paths):** Both scripts write to exactly the paths the workflow expects.

**Actual cause:** The two missing files were never produced in this worktree. The scripts (`polymarket_signals.py`, `kalshi_signals.py`) make live API calls to Polymarket and Kalshi; if those fail or the scripts were never executed after a checkout, the output JSON files simply don't exist. The workflow runs them (lines 50 and 62) but with network-dependent APIs, output is not guaranteed.

The `prediction_market_agents/data/` files referenced by the dashboard (`momentum_signals.json`, `whale_signals.json`, `kalshi_signals.json`) are also missing — there are agent scripts (`polymarket_momentum_agent.py`, `polymarket_whale_tracker.py`, `kalshi_signal_agent.py`) but no workflow step runs them, and no output files exist.

## Fix Applied

**None required for path mismatch.** No code changes were made because there is no filename/path mismatch to correct. The workflow filenames already match the scripts' output paths.

**Recommended follow-up (not implemented):**
1. Ensure `polymarket_signals.py` and `kalshi_signals.py` run successfully so their output files exist for the workflow to commit.
2. Consider adding workflow steps to run `prediction_market_agents/polymarket_momentum_agent.py`, `polymarket_whale_tracker.py`, and `kalshi_signal_agent.py` so the dashboard-registered `prediction_market_agents/data/*.json` files are produced.
3. The `git add ... 2>/dev/null || true` pattern already prevents workflow failure when files are absent.

## Verification

- Read `.github/workflows/polymarket-signals.yml` lines 83-88 — confirmed `git add` targets.
- Read `alpha_engine/polymarket_signals.py:29` — `OUTPUT_FILE = alpha_engine/data/polymarket_signals.json`.
- Read `alpha_engine/kalshi_signals.py:31` — `OUTPUT_FILE = alpha_engine/data/kalshi_signals.json`.
- Read `alpha_engine/prediction_market_consensus.py:32` — `OUTPUT_FILE = alpha_engine/data/prediction_market_picks.json`.
- Listed `alpha_engine/data/`, `copy_trader_intel/data/`, `prediction_market_agents/data/` — confirmed which files exist vs missing.
- Grep `audit_trail/dashboard_generator.py` — confirmed `JSON_PICK_SOURCES` entries for PM sources.