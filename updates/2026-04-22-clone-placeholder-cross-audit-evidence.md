# Clone-Placeholder Blocker — Cross-Audit Corroboration

**Date:** 2026-04-22
**Status:** BLOCKER CORROBORATED — realized closed-trade data directly contradicts the placeholder stats
**Companion to:** `updates/2026-04-22-clone-placeholder-stats-blocker.md` (Copilot agent)
**Author:** Claude (independent verification)

---

## Purpose

The companion doc identified the mechanism (EXEMPT_FROM_SAFETY_GATES tag + float `forward_trades` + false `forward_validated: true`). This doc adds **independent evidence from the closed-trade ledger** that the placeholder stats don't hold up in realized performance — which strengthens the case for Option D (fix the pipeline, don't trade).

## The disconnect, in one table

| Source                      | Placeholder stat (active_picks.json) | Realized (universal_resolved_picks.json, my audits)          |
|-----------------------------|--------------------------------------|--------------------------------------------------------------|
| `clone_hl_copy_whale_433roi` | **86% WR** (ExpWR tag)               | Not in universal ledger — no independent closed trades      |
| `clone_hl_copy_PensionFund_24M` | **100% WR** (ExpWR tag)           | Not in universal ledger — no independent closed trades      |
| `clone_hl_copy_lb_None`     | **80% WR** (ExpWR tag)               | **28.2% WR, -0.53% mean PnL, n=346** (feature stability audit) |
| `source_system=copy_trader_intel` | _claims edge via clones_       | **31% WR, -0.31% mean PnL, n=286** (stability audit, 100% stability) |
| `source_system=copy_trader_highscore` | _claims edge via clones_   | **Flipped to urgent_retrain last 7d**: +0.351% → **-0.277%** mean PnL (drift demo) |

Sources:
- `docs/reports/feature_stability_2026-04-22.md` (purged K-fold CV, commit `3537a1e867` on feat/ship-week-integrations-2026-04-21)
- `docs/reports/drift_demo_2026-04-22.md` (KS-test drift, commit `e86a02e382` on financial-audit-analysis)

## Why this matters for the blocker recommendation

The companion doc's Option D says *"require independent forward trades before HC acceptance"*. My audit adds a stronger claim: **the independent forward trades we DO have show the clone sources are systematic losers, not winners** — the placeholder stats are directionally wrong, not just overstated.

Specifically:
- `copy_trader_intel` appears **stable** in the drift sense (no regime-change) but stably **losing** at 100% fold-agreement across 5 time-sorted folds. This is the worst case: a consistent drain dressed up as high-conviction via placeholder WR.
- `copy_trader_highscore` *has* drifted — and the drift is **toward worse performance**, not the direction the placeholder 85% WR would suggest. A source flipping from +0.35% to −0.28% mean PnL in 7 days while its placeholder says 85% WR is the clearest possible signal that the placeholder is decoupled from reality.

## Concrete ask to reinforce Option D

On top of the companion doc's pipeline fix:

1. **Add a real-closed-trade guard** at the HC-gate level: a pick with `clone_safety_mode: EXEMPT*` is only HC-passed if its `source_system`'s **realized** 30-day mean PnL (from `universal_resolved_picks.json`) is positive. Today that guard would block every clone row — which is the right answer.

2. **Surface the drift-demo output** (`docs/reports/drift_demo_2026-04-22.md`) on the audit dashboard next to the clone-row count. Operators seeing "50 clone picks passing HC" and "copy_trader_highscore flipped urgent_retrain" in the same view will make better gating calls than either signal alone.

3. **Add a regression test** on top of the companion doc's:
   ```python
   def test_clone_row_blocked_when_source_system_drifting():
       # Any clone pick whose source_system has drift_severity >= retrain
       # in the last 7d must not receive EXEMPT treatment.
   ```
   The `alpha_engine/drift_aware_scoring.detect_simple_drift` primitive is already available and tested (26 passing tests).

## Blast-radius note

This corroboration does **not change the Option D recommendation** — the companion doc's path stands. The value added here is that:
- The stats aren't just unverified — they're **measurably wrong** against the closed-trade ledger.
- We already have standalone tools (`tools/feature_stability_audit.py`, `tools/drift_demo.py`, `alpha_engine/drift_aware_scoring.py`) that detect this pattern without waiting for the pipeline fix to land.

Operators should treat any current clone-row HC pass as **quarantined** (option b short-term) while the pipeline fix (option d long-term) lands.

---
*Per project memory rules: "Confidence ≠ Edge" and "Gate At Execution Not Generation" — this blocker is the textbook example of both.*
