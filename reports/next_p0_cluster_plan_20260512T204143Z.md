# Next P0 Cluster Plan — 2026-05-12T20:41:43Z

Branch: `main` @ `023e636e26c`
Author: claude-opus-4-7 (autonomous loop)
Scope: 3 remaining supreme-plan P0s + 2 validation follow-ups; targets
real-money readiness gates for COMMODITY, EQUITY, CRYPTO.

---

## Context

The supreme-edge master plan
(`updates/2026-05-11-money-maker-master-plan.html`) listed 10 P0 items.
7 are shipped on main as of this commit:

| # | Item | Commit / Location |
|---|---|---|
| 1 | kimi_signal_tracking blacklist | `alpha_engine/config.py:216` |
| 2 | claude_gainer_st blacklist | `alpha_engine/config.py:216` |
| 3 | crypto_soc family quarantine | `audit_trail/quality_gates.py:884+` |
| 4 | FOREX hard-cap (min_score 70) | `alpha_engine/config.py:239` |
| 5 | DEAD-status flag for >30d stale systems | `023e636e26c` |
| 6 | auto_retire drawdown sign-convention fix | `8a82f133ca7` |
| 7 | auto_retire FOREX mutate-before-kill guard | `8a82f133ca7` |

Three remain. Plus two validation-loop items the 2026-05-12T19:44Z audit
flagged (`reports/money_maker_ready_20260512T194402Z.md`).

---

## P0-#1 — Verify `multi_asset_cot` PF=19.93 via DB query

### Why

`dashboard_data.json::systems` reports PF=19.93 / WR=87.4% / n=135 / MDD=17.8.
Up from PF=19.19 / n=130 yesterday. This is implausibly high for a
real strategy and would be the highest-leverage candidate for Tier-1
sleeve allocation IF the number is real. If it's a payload aggregation
bug, the dashboard is currently advertising a phantom edge.

### Implementation

New script: `tools/verify_system_pf.py`

```python
"""Verify a system's PF/WR/n on /audit dashboard against ejaguiar1_stocks DB.

Usage:
  python tools/verify_system_pf.py --system multi_asset_cot
  python tools/verify_system_pf.py --all-winners

Requires DB_STOCKS_PASSWORD env var (or DB_PASSWORD fallback).
"""
# pulls per-system aggregate from trading_picks:
#   SELECT COUNT(*) n, SUM(pnl_pct>0) wins, SUM(pnl_pct) sum_pct,
#          SUM(CASE WHEN pnl_pct>0 THEN pnl_pct ELSE 0 END) gross_win,
#          SUM(CASE WHEN pnl_pct<0 THEN -pnl_pct ELSE 0 END) gross_loss
#     FROM trading_picks
#    WHERE source_system = %s AND status IN (terminal_set)
# computes PF = gross_win / gross_loss
# compares against dashboard_data.json::systems[name] PF
# emits audit_dashboard/data/system_pf_verification.json
# verdict: MATCH / DIVERGENT_<delta>pp / NO_DB_DATA
```

Wired into existing `ab_analysis.yml` workflow (already has DB creds).
Output committed nightly. NFA: read-only.

### Testing

Run manually with `--system multi_asset_cot` and confirm output JSON has:
- `db_pf` numeric
- `dashboard_pf` numeric
- `delta_pp` numeric
- `verdict` enum {MATCH, DIVERGENT, NO_DB_DATA}

If `delta > 2pp` and `dashboard_pf > 5.0`, the system should be flagged
in a follow-up `quarantine_manifest.json` note as
`pf_verification_pending` — NOT auto-quarantined. Tier-1 allocation
gated on verdict=MATCH.

---

## P0-#2 — CT=F / KC=F symbol concentration on COMMODITY class tile

### Why

The `_toxic_concentration` field (computed in `audit_trail/dashboard_generator.py:9436+`)
already flags systems where one symbol dominates ≥70% of PnL mass.
This is surfaced at SYSTEM-level via the TOXIC badge
(`audit_dashboard/template.html:10241 toxicConcBadgeHtml`). But the
CLASS-level COMMODITY tile (which is what users see when scanning
"is COMMODITY my edge?") does not aggregate it.

If CT=F drives 90% of COMMODITY PF, then "COMMODITY PF=2.08" is
misleading — the real attribution is "CT=F PF=2.08, rest-of-commodity
PF≈0.7".

### Implementation

1. Extend `dashboard_generator.py::_normalize_pick` aggregation pass to
   emit per-class symbol-concentration:
   ```python
   asset_class_concentration[class] = {
     "top_symbol": str,
     "top_share_pct": float,  # of abs(pnl_pct) mass within class
     "is_concentrated": bool,  # share >= 70
   }
   ```
2. Output payload field: `performance.asset_class_concentration` (new).
3. Template.html: in the per-class banner spans (line ~866), append a
   small inline warning when `is_concentrated`:
   `(CT=F 89% — single-symbol concentration)`.

### Testing

- Unit test on `tools/test_asset_class_concentration.py` — synthetic
  pick list with 90% mass in one symbol → assert concentration flagged.
- Manual: open `/audit` in browser; verify COMMODITY tile shows
  concentration badge if dashboard_data has one.
- Regression: confirm no other tile output changes when no class is
  concentrated.

---

## P0-#3 — `capped_vs_raw_pnl_gap` field exposure (Kimi 680% MDD anomaly)

### Why

Per supreme plan EQUITY block:
> Verify capped-vs-raw PnL gap (Kimi flagged 680% MDD anomaly; Codex
> made it a payload-contract field `capped_vs_raw_pnl_gap`).

A 680% MDD on EQUITY is either a unit conversion bug OR a legitimate
outlier from a 10×-leverage position not capped during resolution.
The fix from Codex was to add a payload-contract field that exposes
the gap between capped and raw aggregates so reviewers can spot it
without digging into raw rows.

### Implementation

1. Search dashboard_generator for "max_drawdown" computation; identify
   where capping happens (if at all).
2. Compute uncapped MDD alongside capped one; emit
   `per_class_pnl_capping.{COMMODITY,EQUITY,CRYPTO,...}` with:
   ```
   {capped_total_pnl_pct, raw_total_pnl_pct,
    gap_pct, capping_threshold_used}
   ```
3. Surface on the per-class tile as a small tooltip on the PF number:
   "capped at 200%/-100% per pnl_pct anomaly clamp PR-876; raw PnL diverges X%".

### Testing

- Pick a class where raw and capped differ; verify gap > 0.
- Pick a class where no capping triggered; verify gap == 0 and tooltip
  is hidden.
- Regression: ensure existing PF/WR numbers unchanged on tile (cap is
  cosmetic disclosure, not a recompute).

---

## Validation-loop follow-ups (not strictly P0 but blocking real-money)

### V1 — `asset_class_health.n=0` bug

This bug has been called out in 2026-05-11 plan + 2026-05-12 audit. All
classes report n=0 despite walk-forward producing real folds. The
aggregator in `audit_trail/dashboard_generator.py` is silently
producing empty rows. Until fixed, every per-class tier verdict is
PHANTOM.

Root cause unknown — needs `cavecrew-investigator` to locate the
`_compute_asset_class_health()` (or equivalent) callsite and identify
what's filtering all picks out.

### V2 — drift detector cron refresh

`hf_stats.generated_at: 2026-04-22` (20 days stale). The drift
detector now produces real KS_D=0.31 (6.6× critical = SEVERE). But the
snapshot is stale — the regime may have moved further or rolled back.
Fix the cron that refreshes `hf_stats`. Likely workflow is
`audit-dashboard.yml` or `ml-staleness-watchdog.yml`. Need to grep
for the writer.

---

## Cross-cutting acceptance criteria

For all 3 P0s above:
1. New code passes `py_compile`.
2. New JSON outputs pass schema check (no required field missing).
3. UI changes verified by opening `/audit` in a browser (no console errors).
4. No regressions in:
   - `audit_dashboard/index.html` (must remain auto-generated; do NOT
     edit directly — template.html only).
   - `dashboard_data.json` field stability (additive only).
   - `actions/dashboard-payload-contract-reviewer` (the
     `dashboard-contract-reviewer` agent must pass).

## Estimated effort

| Item | LOC | Effort | Risk |
|---|---|---|---|
| P0-#1 verify_system_pf.py + wire | ~120 | 1.5h | Low |
| P0-#2 asset_class_concentration | ~80 + tests | 2h | Low |
| P0-#3 capped_vs_raw_pnl_gap | ~60 + tests | 1.5h | Low |
| V1 asset_class_health bug | unknown | 2-4h | Med — root-cause first |
| V2 hf_stats cron refresh | small | 0.5h | Low |

Total: ~6-9 hours over 5 PRs.

## What I want the swarm to review

1. Are the 3 P0 ranking + ordering correct? Is there a higher-leverage
   item I missed?
2. P0-#1 verification — is DB query approach correct, or should we
   instead use `audit_dashboard/data/dashboard_data.json::systems`
   cross-checked against `cross_strategy_permutations` to avoid DB hop?
3. P0-#2 concentration — should it block live sizing or just warn?
4. P0-#3 capping disclosure — should the cap THRESHOLDS themselves be
   reviewed before disclosure UI is built?
5. Are any of the existing 7 "shipped" P0s actually NOT enforcing the
   intended block (memory: `feedback_gate_at_execution_not_generation`)?
6. Is the V1 `asset_class_health.n=0` bug actually the same root cause
   as the walk-forward fix delta (now 4/7 classes populated, was 0/7)?

## NFA

Research surface only. No real-money sizing changes proposed in this
plan. The 3 P0s are diagnostic + UI disclosure improvements. None
modify trade execution gates.
