# 2026-05-03 — Non-Crypto Remediation Wiring (Phase 4)

> Following [`CLAUDE_DEBUGGING_GUIDE.MD`](../CLAUDE_DEBUGGING_GUIDE.MD) Part 6
> ("Root Cause Summary — Still Needs Work"). Phase 1-3 created the modules;
> Phase 4 wires them into the live scoring/gating/resolution pipeline.

## What was broken

Three remediation modules existed on `main` but had **no production callers**,
which is exactly the orphan-rate failure mode AGENTS.md warns about:

| Module | Status before | Caller in production path |
|--------|---------------|---------------------------|
| `alpha_engine/non_crypto_boosters.py::compute_non_crypto_boost` | importable, tests pass | none — never invoked from `compute_elite_score()` |
| `audit_trail/quality_gates.py::get_effective_min_score` | helper existed | bypassed: `passes_smart_gate` re-implemented an if/elif chain that ignored `STRATEGY_SCORE_OVERRIDES` |
| `audit_trail/universal_pick_resolver.py::MAX_HOLD_HOURS` | constant 48h for all classes | TIME_EXIT closed forex/bond picks before they had time to resolve (Step 7 of the guide) |

## Asset-class health (pre-fix snapshot)

From `audit_dashboard/data/dashboard_data.json::performance.asset_class_health`:

| Class | PF | WR | Verdict |
|-------|----|-----|---------|
| FOREX | 0.27 | 46.4% | Catastrophic — deep-dive class |
| COMMODITY | 1.78 | 46.9% | Tier-2 PF, low WR |
| BOND | 1.72 | 55.6% | Tier-2 PF & WR (n=18, sample-low) |
| ETF | 1.24 | 55.2% | Borderline |
| EQUITY | 1.41 | 52.9% | Tier-2 candidate |
| CRYPTO | 1.24 | 44.6% | quan_engine + unknown drag |

## Changes

### 1. `audit_trail/quality_gates.py` — `passes_smart_gate` now uses `get_effective_min_score`

The if/elif chain was hard-coding `SMART_PICKS_MIN_SCORE_<CLASS>` as the floor,
so proven non-crypto strategies registered in `STRATEGY_SCORE_OVERRIDES` (e.g.
`forex_rsi2_mean_reversion: 30`, `bond_yield_momentum: 28`) were silently
gated at the class default of 40 — exactly the "score floor too high"
gate-killer #1 in the guide.

**Crypto unaffected**: no crypto strategies are registered in the override
dict, so the helper falls through to `SMART_PICKS_MIN_SCORE = 60`, identical
to the pre-fix path.

### 2. `alpha_engine/elite_scorer.py` — `compute_elite_score` calls `compute_non_crypto_boost`

Per the guide's score-component table:

> Score booster (MTF/ensemble) +0 to +25 — Crypto has it, non-crypto has none
> → structural gap

Wired the booster as an additive after concentration-penalty and before grade
assignment. `compute_non_crypto_boost` returns `(0, {"_non_crypto_boost": "skipped_crypto"})`
for crypto picks, so crypto scoring is unchanged. FOREX/COMMODITY/ETF/BOND/
EQUITY now get class-specific enrichment capped at:

| Class | Max boost | Source |
|-------|-----------|--------|
| FOREX | +15 | Session overlap + carry differential |
| COMMODITY/FUTURES | +15 | COT sentiment + seasonal pattern |
| ETF | +10 | 12m momentum + VIX regime |
| BOND | +10 | Yield curve + credit spread (FRED) |
| EQUITY | +8 | Sector momentum |

Booster is wrapped in `try/except` so any failure leaves the original score
intact and is recorded under `breakdown["_non_crypto_boost_error"]`.

### 3. `audit_trail/universal_pick_resolver.py` — per-asset-class TIME_EXIT window

Step 7 of the guide: **72.7% of picks never hit TP/SL within 24h. Forex and
bonds need 5–14 days to resolve.** The previous `MAX_HOLD_HOURS = 48` was a
crypto-shaped bias on all classes. Replaced with `MAX_HOLD_HOURS_BY_CLASS`:

| Class | Hold window |
|-------|-------------|
| CRYPTO | 48h (unchanged) |
| EQUITY/ETF/COMMODITY/FUTURES | 96h |
| FOREX/BOND | 120h |
| Unknown | 48h (legacy default) |

The resolver only looks up the per-class window for the time-expiry branch;
TP/SL hit detection is unaffected.

## Verification

| Check | Result |
|-------|--------|
| `tests/test_quality_gates.py` | 56/56 pass (was 54; +2 new tests for the override wire) |
| `tests/test_elite_scorer.py` | 6/6 pass (was 4; +2 new tests for the boost wire) |
| `tests/test_universal_pick_resolver.py` | 5/5 pass (was 4; +1 new test for per-class hold) |
| `tests/test_hf_audit_strict_smart_gate.py` | 3/3 pass (no regression on existing strict-gate suite) |
| `tests/test_dashboard_generator.py` | 19/19 pass (unchanged) |
| Step 9 crypto regression check (BTCUSDT/LONG/conf 0.80/score 70/RR 2.0) | passes_active_gate ✅ |
| Step 9 crypto floor check | `get_effective_min_score("fear_greed_contrarian", "CRYPTO") == 60` ✅ |
| FOREX override check | `get_effective_min_score("forex_rsi2_mean_reversion", "FOREX") == 30` ✅ |
| BOND override check | `get_effective_min_score("bond_yield_momentum", "BOND") == 28` ✅ |
| Non-crypto boost wired check | FOREX pick gets `breakdown["non_crypto_boost"] >= 0`, CRYPTO pick has no key ✅ |
| Resolver per-class window | CRYPTO 48h / FOREX 120h / BOND 120h / COMMODITY 96h / unknown 48h ✅ |

## What's NOT in this PR (by design)

The guide's Part 6 also lists three items that need separate work and were
left for follow-up so this PR stays surgical:

- **Transaction cost model not deployed** (`COST_MODEL` per the guide) — needs
  to be applied to closed-pick PnL across the dashboard payload, not the
  scoring path.
- **R:R ceiling 2.0** — `SMART_PICKS_MAX_RR = 3.5` already exists; tightening
  needs its own data-driven analysis (the existing 3.5 was widened from 1.75
  earlier this year with rationale; reverting requires evidence).
- **ETF/BOND scanner cron activation** — workflow scheduling is out of scope
  for a debug-and-wire PR; the scanners are importable and ready when a
  workflow is added.

## Why this is a Wire-Up PR (per AGENTS.md "Wire-Up Rule")

Each of the three modules now has a production caller in the pick-generation
or scoring path:

| Module | Caller (production path) |
|--------|--------------------------|
| `compute_non_crypto_boost` | `alpha_engine/elite_scorer.py::compute_elite_score` (every pick) |
| `get_effective_min_score` | `audit_trail/quality_gates.py::passes_smart_gate` (every smart pick) |
| `MAX_HOLD_HOURS_BY_CLASS` | `audit_trail/universal_pick_resolver.py::resolve_active_picks` (every TIME_EXIT decision) |

Confirmed via:
```bash
grep -rln "compute_non_crypto_boost" alpha_engine/
grep -rln "get_effective_min_score" audit_trail/
```
