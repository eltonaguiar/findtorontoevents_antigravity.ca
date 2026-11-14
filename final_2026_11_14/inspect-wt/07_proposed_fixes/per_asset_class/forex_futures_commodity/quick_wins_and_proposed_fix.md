# FOREX / FUTURES / COMMODITY — quick wins + proposed fix (deepAI, 2026-11-14)

Worktree base: `.inspect-wt` @ f54efb3b4a (~5 months behind origin/main — re-verify anchors on rebase).
Live-data evidence: `2026-11-14/inspect-wt_20261114_1058/evidence_live_audit.json`.

---

## Quick win 1 — PASS (anchor verified): turn the FOREX kill-switch back ON by default

- **Anchor:** `alpha_engine/config.py:324-329`
  ```python
  # FOREX hard disable — 2026-05-15
  # FOREX class re-enabled 2026-06-05: forex_carry_g10 extended backtest meets unlock condition.
  #   PF=1.593, WR=60.4%, n=197 (reports/forex_carry_backtest_extended_20260606.json)
  # Kill-switch: set env FOREX_HARD_DISABLE=0 to re-enable.
  FOREX_HARD_DISABLE: bool = _forex_os.environ.get("FOREX_HARD_DISABLE", "0") not in ("0","false","FALSE","False")
  ```
  Default `"0"` ⇒ switch is **OFF**. Emission gates exist and honor it: `alpha_engine/scanner.py:2606`
  (`if cat == "FOREX" and _ae_config.FOREX_HARD_DISABLE:`), plus `mysql_trading_sync.py:676` and
  `risk_regime_validator.py:304-306`.
- **Why:** the 2026-06-05 re-enable was justified by ONE in-sample backtest (PF 1.593, n=197).
  Live resolution since then: money_ready FOREX PF **0.660** (n=612), registry PF 1.214 — and the
  class is NOT_READY on its own verdict. Live data has not confirmed the unlock condition.
- **Minimal change:** default `"0"` → `"1"` (one character), or set `FOREX_HARD_DISABLE=1` in the
  alpha-engine workflows so it doesn't depend on the runner's env.
- **Effect:** stops new FOREX emission; display keeps showing history; FOREX NOT_READY verdict
  finally matches behavior.
- **Risk:** low — re-enable is one env var. Rollback: flip env.

## Quick win 2 — PASS (data verified): FUTURES — show INSUFFICIENT_DATA, not one live-looking pick

- **Evidence:** `.picks.active_raw` FUTURES n=13, median age 2,343.9h (98 days); money_ready PF
  1.0936 on n=52 with pf_ok=False; surface_truth verdict INSUFFICIENT_DATA. The single fresh pick
  (2.8h) sits on a zombie pile and implies an active system that isn't.
- **Change:** in the asset-class summary builder, mark a class `DISPLAY:DEGRADED` when
  active_raw median age > 168h; frontend renders the surface_truth verdict instead of the live count.
- **Risk:** cosmetic; no stat change.

## Quick win 3 — PASS (data verified): COMMODITY — surface the single-source concentration

- **Evidence:** registry COMMODITY row: `single_source_pct = 0.913` (top source dominates);
  my 14d recompute PF 0.604 on n=7; money_ready PF 1.0256 n=229 pf_ok=False.
- **Change:** pf_registry already emits `single_source_pct` per class — render it as a warning
  badge on the COMMODITY (and CRYPTO 97.9% / EQUITY 97.6%) class cards in template.html. Data is
  already in the payload; this is frontend-only.
- **Risk:** none (display only).

## Quick win 4 — FAIL (needs shared generator work): purge FOREX/COMMODITY zombie rows

- Same fix as crypto (see `fixspecs/fixspec_zombie_purge_and_reemission_guard.md`) — the generator
  filter is shared, so it's one implementation covering all classes. No independent quick win here.
- Evidence: FOREX active_raw oldest 6,415h; COMMODITY oldest 4,056h; USDCAD=X/NZDUSD=X rows are
  mostly EXPIRED pnl-0 zombies (their "flat 0%" displays are artifacts).

## Quick win 5 — FAIL (spec only): COT paper-pilot commodity sourcing

- Could not verify from available files that the COT paper pilot (cot_*.json) feeds live commodity
  picks with fresh data — the live payload's COMMODITY closed count (n=7/14d) is too thin to
  confirm. UNVERIFIED; needs the cot paper pilot status file inspected on a live run.

---

# Proposed fix (deeper) — Policy layer that gates emission AND display from one verdict

## Problem
The FOREX kill-switch proves the pattern: `FOREX_HARD_DISABLE` gates **emission** (scanner.py:2606),
but the dashboard's NOT_READY verdict (surface_truth) and the kill-switch are **two separate
systems that can disagree** — FOREX was emitting picks for months while officially blocked/re-blocked,
and verdict flip-flops (ETF money_ready PF 0.02 vs registry 1.84) never gate anything.

## Spec
1. New `alpha_engine/class_policy.py`: one module that, per asset class, computes a single verdict
   from the canonical ledger (see `fixspecs/fixspec_single_canonical_ledger.md`):
   verdict ∈ {ACTIVE, WATCH, BLOCKED, INSUFFICIENT_DATA} + reasons + as-of timestamp.
2. Consumers:
   - Emitters (scanner.py, production_scanner.py, per-class agents) call `class_policy.get(class)`
     before emitting; BLOCKED/INSUFFICIENT_DATA ⇒ no emission.
   - Dashboard generator embeds the verdict in `asset_class_summary` and `data_freshness`.
   - Frontend renders the verdict as the class header state.
3. Kill-switches (FOREX_HARD_DISABLE, commodity_kill_switch) become **inputs** to the policy module
   rather than independent env flags, so there is exactly one source of truth per class.
4. Migration: keep env flags working for 2 weeks (override mode) with a banner when they disagree
   with the policy verdict.

## Acceptance test
- A class marked BLOCKED emits zero new picks across 3 consecutive hourly cycles.
- No surface shows a class as tradeable while its policy verdict is BLOCKED/INSUFFICIENT_DATA.
