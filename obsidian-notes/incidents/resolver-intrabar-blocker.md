---
tags: [incident, blocker]
created: 2026-06-06
severity: P0
status: open
---

# Incident: Resolver Intrabar Blocker

## Summary

Upstream T2 blocker: `alpha_engine/outcome_resolver.py` does not replay intrabar OHLC to validate fills. All paper-pilot sleeves requiring fill validation are blocked at Stage 0.

## Root Cause

Resolver uses `NOW()` for closed_at backfill; does not cross-reference intrabar bar data to confirm TP/SL was actually hit.

## Impact

- 4 CRYPTO sleeves (JUP/ENA/ADA mega_mutation + DYDX alpha_engine) blocked
- 28-100% of picks would be reclassified if intrabar replay ran
- No T2 class can be "confirmed" without this fix

## Fix

- Tool exists: `tools/validate_intrabar_fills.py`
- Resolver fix applied 2026-04-28 (v2 + v2.1 bug bundle 2026-05-02) for `PNL_WIN_THRESHOLD_BY_CLASS`
- Intrabar replay portion NOT yet shipped

## Update 2026-06-06 — quantified + partial mitigations shipped

Fresh evidence and read-side fixes landed this session ([[sessions/2026-06-06-edge-audit-and-resolver-fix]]):

- **Quantified intrabar inflation:** `tools/validate_intrabar_fills.py` (read-only) → 63% of sampled CRYPTO TP_HITs actually hit SL first; all 4 sleeves FAIL_RECLASSIFY. New de-biased tool `tools/reresolve_intrabar.py` → CRYPTO orig WR 52.3% → **intrabar-true 42.9% / PF 1.22**, 26.4% TP→SL reclassification.
- **Resolver-version selection bias** is the sharper framing: same June CRYPTO data gives PF 0.51 (v2.2_sync) vs 2.15 (universal_v2) — a verdict inversion driven by which resolver ran, not alpha.
- **Read-side mitigations shipped** (don't fix the resolver, but stop laundering artifacts into verdicts): backfill quarantine in `build_pf_registry.py` (77.8% of WON/LOST rows excluded) + per-class sane-pnl guard (drops CADJPY +428% feed bugs / reverse-split signatures).
- **Still open:** the resolver itself doesn't replay intrabar in production; `reresolve_intrabar.py --apply` is gated; and the gating dependency is **`crypto_ohlcv` only has 30 days of 1h history** — need ~6–12 months backfilled before the full book can be re-resolved.

## Related

- [[sessions/2026-06-06-edge-audit-and-resolver-fix]]
- [[strategies/mega_mutation]]
- [[strategies/READY-TO-TRADE-NOW]]
- [[reference/performance-tiers]]
