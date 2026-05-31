# /money-maker-readyv2 — PENNY

## Class verdict at 06:30Z 2026-05-31

**PF=0.169  WR=28.6%  n=8 (resolved=7)  Sharpe-proxy=-0.51  T2-status: DORMANT / INSUFF-N — FAIL on every axis (PF, WR, n; MDD untrustworthy at n=7)**

Lifetime PENNY data (`ejaguiar1_stocks.trading_picks WHERE category IN ('penny','pennystock')`):
- n=8 total, resolved=7 (5 LOST, 2 TP_HIT, 1 EXPIRED)
- avg_pnl=-3.12%, gross_win=5.08, gross_loss=30.02, PF=0.169
- Date range: **2026-03-11 → 2026-03-16**. **75 days of zero emissions since.**
- 14d window: 0 picks. 48h window: 0 picks. 30d cadence: 0.
- NOT tracked in `pf_registry.by_asset_class_policy_clean_net` — folded into EQUITY (which itself FAILs T2 with PF 0.90 / WR 33% / n=33).

Symbol audit on the 8 picks: IONQ, RIOT, AMC, MARA, SOFI, NIO, SNDL — **only SNDL is a sub-$5 true penny**. The other 7 are mid-cap volatile equities mistagged as `category='penny'` by `institutional_picks_engine.penny_deep_oversold` and friends. This is a **category-mistag class**, not a real penny-stock book.

## Best candidate

**None at n≥10.** Highest n is `institutional_picks_engine.penny_deep_oversold` at n=4, resolved=4, WR=50%, PF=0.19 (2 small TP_HITs at +1.8%/+3.3% offset by 2 large losses at -14.6%/-11.8% — R:R inverted, classic deep-oversold knife-catch geometry). Already on `_BLOCKED_CATEGORY_STRATEGIES` for `("equity", "penny_deep_oversold")` in `alpha_engine/production_scanner.py:2649` — but blocked under EQUITY key, NOT under `("penny", ...)`, so a relabeling could leak it back in.

No PENNY strategy on the Phase-3 MC watchlist (PR #179). No PENNY strategy approaches the n=30 floor MC needs to run.

## T2 gap

- **100 more clean closures needed** (from 0 toward n=100). All 7 resolved rows are 75+ days old and would not be in any 30/60/90d evaluation window.
- **At current cadence (0 closures/day in last 75 days) → time-to-T2 = ∞**. Class is effectively shut down.
- Bottlenecks:
  1. **Emission tap off**: `penny_deep_oversold` was blocked 2026-04-19 (`_BLOCKED_CATEGORY_STRATEGIES` rollout). `skyrocket_detector` exists (`alpha_engine/strategies/skyrocket_detector.py` — 613 lines, emits `category='penny'` line 296) but per `tools/audit_pick_funnel/seed_incidents_enhancements.py:151` is **NOT wired to production_scanner.py**.
  2. **Orphan harness**: `alpha_engine/penny_stock_strategy_harness.py` (1869 lines) has zero callers outside its own file (only matches in `tools/kimi_research_2026_05_20/` research dir). Classic Wire-Up Rule violation (CLAUDE.md).
  3. **Category mistag at source**: `institutional_picks_engine` emitted mid-caps (IONQ/MARA/RIOT) as `category='penny'`. There is no price-based check (`entry_price < $5`) gating the penny tag.
  4. **No price-cap filter**: nothing in `production_scanner.py` enforces "penny means <$5"; the category is treated as a free-text label set by the emitter.

## Resolver / data quality risk factors

- Phase 4 resolver bug (past-TP writes without intrabar verification): of 7 resolved PENNY rows, `tp_fill_method IS NULL` for all 7; exit_reason distribution is `None×2, TIME_EXPIRY×1, STATUS_STANDARDIZED×2, SL_HIT×1, PURGE_FOREX_PENNY×1`. The 2 TP_HIT rows (AMC +1.82%, MARA +3.26%) have `exit_reason='STATUS_STANDARDIZED'` — these were back-filled by a sweep, not by the resolver detecting an intrabar TP. **Trust these 2 wins less than the 5 losses.**
- 1 row with `exit_reason='PURGE_FOREX_PENNY'` — a deliberate purge sweep was run at some point (grep finds no current code path emitting it; appears in 3 dashboard snapshots from 2026-04-06/07). Implies historical operator intent to disable this class.
- Category mistag is the bigger data-quality blocker than the resolver bug for this class.
- pf_registry: PENNY entirely absent from `by_asset_class_policy_clean_net`. The audit dashboard does not report PENNY as a separate verdict — operator cannot even see this class on `/audit`.

## Actions ranked by impact

1. **DECISION GATE — shut PENNY down explicitly, or commit to rebuilding it.** Current state (0 picks/75d, n=8 lifetime, no operator visibility) is the worst of both: occupying code + harness footprint, generating zero learning. **Recommended: shut down via explicit dashboard label "PENNY: DORMANT — see decision doc" rather than leave dangling.** Files: add `"penny": {"status": "DORMANT", "reason": "..."}` block to `audit_dashboard/data/asset_class_health.json` (or wherever the verdict consumer reads) + banner in `audit_dashboard/template.html`.

2. **KILL/MUTATE — formalize the kill of `penny_deep_oversold` for ALL category labels.** Currently blocked only under `("equity", "penny_deep_oversold")` in `alpha_engine/production_scanner.py:2649`. Add `("penny", "penny_deep_oversold")` and `("pennystock", "penny_deep_oversold")` to `_BLOCKED_CATEGORY_STRATEGIES` so a relabel cannot leak it back. Mutation-three-axis: regime gate FAIL (no regime detection on these knife-catches), vol floor FAIL (deep-oversold by definition is post-vol-spike — late), source-confluence FAIL (single-source, no confirmation).

3. **ADD — price-based category enforcement** (1-file PR). In `alpha_engine/production_scanner.py` or `alpha_engine/concept_registry.py` add an emitter-side guard: if `category in ('penny','pennystock')` AND `entry_price >= 5.0`, force `category = 'equity'` (re-route to EQUITY gates). Prevents IONQ/MARA-style mistags from ever counting as PENNY again. Cite: 7/8 lifetime PENNY rows were >$5 at entry. ~10 lines.

4. **WIRE-UP — `skyrocket_detector` into production_scanner.py OR explicitly retire it.** Per `tools/audit_pick_funnel/seed_incidents_enhancements.py:151` this has been an open P2 incident. Two options:
   a. **Wire** with strict price-cap (entry_price < $5), volume_ratio >= 3.0, and float < 50M (already in the detector). Add caller in `production_scanner.py` near other strategy invocations.
   b. **Retire** — move to `alpha_engine/strategies/retired/` and close the incident. Recommended unless an operator has a clear price-action thesis to test live.
   Either way, close the incident — the dangling-orphan state is the bug.

5. **WIRE-UP or RETIRE — `alpha_engine/penny_stock_strategy_harness.py`** (1869 lines, zero callers). Same call as #4. CLAUDE.md Wire-Up Rule says breadth-only PRs are closed; this is the lifetime example.

6. **WATCHLIST — none.** No PENNY strategy currently warrants protected emission cadence; there's no edge to protect.

## What I would ship next

Two concrete PRs the operator can merge today, both docs/config-scope (admin-mergeable):

### PR-A (1 file, ~15 lines): Lock penny_deep_oversold under all category labels + price-cap mistag guard
- Edit `alpha_engine/production_scanner.py` `_BLOCKED_CATEGORY_STRATEGIES` to add:
  ```python
  ("penny", "penny_deep_oversold"),
  ("pennystock", "penny_deep_oversold"),
  ```
- Add early in the emission pipeline (where `category` is first assigned):
  ```python
  if (pick.get("category") or "").lower() in ("penny", "pennystock"):
      ep = float(pick.get("entry_price") or 0)
      if ep >= 5.0:
          pick["category"] = "equity"  # mistag: not a sub-$5 penny
          pick["_mistag_corrected"] = True
  ```
- Test: `pytest alpha_engine/tests/test_equity_routing.py` (already untracked locally — extend with a penny-mistag case).

### PR-B (docs-only, admin-mergeable): formal DORMANT status for PENNY
- New file `reports/penny_class_dormancy_decision_2026-05-31.md`: records n=8 lifetime, 0 picks/75d, category mistag, decision to either rebuild via skyrocket_detector wire-up or retire.
- Add 1-line PENNY entry to `audit_dashboard/template.html` MAJOR GOAL banner (lines ~808-820) noting "PENNY: DORMANT (0 picks/75d, lifetime n=8 mostly mistagged)".
- Update `updates/index.html` (insertion above `<!-- AUTO-INJECTED:INCIDENTS-ENHANCEMENTS:START -->` per CLAUDE.md rule).
- FTP-deploy via `tools/deploy_audit_files.py --only updates` after merge.

PR-B unblocks operator visibility — right now PENNY is invisible on /audit because the verdict consumer doesn't even render it. PR-A closes the loophole that would let mistagged mid-caps re-enter under the penny label if a future emitter regresses.

---

**Verdict 1-liner:** PENNY is DORMANT (n=8 lifetime, 0/75d, PF 0.17, WR 29%, 7/8 mistagged mid-caps); kill `penny_deep_oversold` under all category labels + add entry-price<$5 mistag guard, and either wire or retire `skyrocket_detector` + `penny_stock_strategy_harness`.
