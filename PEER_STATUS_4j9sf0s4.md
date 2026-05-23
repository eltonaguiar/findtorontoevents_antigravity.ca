# Peer Status — Instance (me)
**Task:** Audit dashboard data-quality fixes
**Started:** 2026-04-04
**Target file:** `audit_trail/dashboard_generator.py` (10,600 lines)

## What I audited
Reviewed https://findtorontoevents.ca/audit/ (dashboard v99.0) via `data/dashboard_data.json`.

## Findings (summary)
1. **WLDUSDT closed pick has corrupt entry_price=66936.96** → displays −99.9996% (Binance real WLD range: 0.24–0.33). Existing sanity gate at `dashboard_generator.py:1186-1213` only fires on ACTIVE picks (unrealized PnL from live prices). CLOSED picks skip this gate entirely.
2. **10 systems count flat picks as "closed"** with 0W/0L/0% PnL (e.g., `kimi_claw_research` has 50 such rows). Inflates closed counts, distorts perception of system activity.
3. **`ml_crypto_predictor` total_pnl = −15,238.54%** — 93% TRX concentration already flagged in clean_metrics but no UI badge on headline number.
4. **FOREX/EQUITY aggregator mismatch** between `non_crypto_performance` and `performance.by_asset_class` (two pipelines, opposite PnL signs).
5. **390/1200 closed rows have `exit_price=null`** yet carry pnl_pct.
6. **6 system + 25 strategy WR arithmetic mismatches** — inconsistent flat-handling in WR denominator.
7. **Duplicate active picks** (ETHUSDT ×3 same entry, from multiple source systems).

## Planned fixes (surgical, low-blast-radius)
**I am editing `audit_trail/dashboard_generator.py` ONLY. If you are also editing this file, coordinate with me via send_message.**

1. **Extend entry_price sanity gate to closed picks** — new helper `_validate_closed_pick_entry()` that flags closed rows where `|pnl_pct| > 500%` OR where `entry_price / median_reference_price` ∉ [0.01, 100]. Flagged rows get `_entry_corrupt=true`, excluded from system totals.
2. **Flat-pick reclassification** — closed picks with `pnl_pct == 0` AND `wins==0 AND losses==0` aggregation get counted into `flat_picks` field, NOT `closed_picks`. UI change is additive.
3. **Add `_toxic_concentration` flag** at system level when >80% of total_pnl comes from a single symbol.

## Files I WILL touch
- `audit_trail/dashboard_generator.py` (edits only, no deletions)
- `CHATWITHIT.MD` (append a new dated section)
- This status file

## Files I will NOT touch
- `audit_dashboard/template.html` (index.html sync rule)
- `audit_dashboard/index.html` (auto-generated)
- Any workflow YAML
- Active strategy code, closed_picks.json, active_picks.json

## Validation
- `py_compile audit_trail/dashboard_generator.py` only.
- I will NOT run the generator locally (would overwrite live HTML per CLAUDE.md).
- GitHub Actions `audit-dashboard.yml` will validate on next scheduled run.

## ✅ COMPLETED (2026-04-04 17:xx UTC)

**Shipped 2 surgical edits to `audit_trail/dashboard_generator.py`** (py_compile OK, uncommitted):

### Fix 1: Entry/exit ratio sanity check for closed picks
- **Location:** `collect_system_stats()` closed-pick loop, inserted after `_is_valid_resolved_pick` gate (around line 6457).
- **Logic:** If a closed pick has `entry_price / exit_price` (or inverse) > 100x, mark `_entry_corrupt=True` and exclude from metrics (bumps `excluded_closed`, skips PnL/WR aggregation).
- **Catches:** WLDUSDT entry=66936.96 / exit=0.2614 (ratio ~256,000x) → previously displayed as −99.9996% loss in `super_signals`. Now excluded + logged.
- **Does NOT catch:** GC=F/4702 (Copilot's finding) — that's a median-reference problem, not entry/exit ratio. Needs a separate per-asset-class price-range validator (unclaimed P0 #3 in my todo list).

### Fix 2: Toxic symbol concentration flag
- **Location:** `collect_system_stats()` result-dict construction (around line 6638).
- **Logic:** For each system with |total_pnl|>50%, walk `sys_strategies[name]` per-symbol pnl sums. If any single symbol accounts for ≥70% of `sum(|symbol_pnl|)`, emit:
  - `toxic_concentration: true`
  - `toxic_symbol: "TRXUSDT"` (or whichever)
  - `toxic_share_pct: 93.0`
- **Catches:** `ml_crypto_predictor` 93% TRXUSDT concentration (−15,238% headline PnL). Template/UI can now surface a warning badge without changing the underlying aggregates.

### What I did NOT change
- No edits to `template.html` (Cursor's hot-zone, and CLAUDE.md says edit template not index).
- No changes to flat-pick classification (avoided WR-denominator region to prevent conflict with Cursor's post-gate NC recompute).
- No changes to reservation/quota block (Cursor's recent commit ae649c47f0).
- No dashboard generator run locally.

### Next steps for other agents
- **UI-side:** Template can now check `system.toxic_concentration` and render a ⚠️ badge + tooltip on headline PnL.
- **Still unclaimed P0s** from Copilot's list: `_is_verified_alpha_pick()` VA=0 bug, smart_picks source field propagation, GC=F per-asset-class entry range validator, null-exit_price hygiene.

## If you need me
Send via claude-peers. I'll check messages every 2–3 turns.