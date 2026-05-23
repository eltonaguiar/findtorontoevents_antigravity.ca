# Audit: Vol-Targeting Clamp Limits CRYPTO MDD Reduction

**Date:** 2026-04-28
**Author:** claude-opus-4-7
**Triggered by:** Building "PR-V vol-targeting" from `reports/deep_dive_crypto_mdd_reduction_2026_04_28.md` led to discovering vol-targeting **already exists** in production at `alpha_engine/kelly_position_sizer.py:78-100`.
**Companion:** `updates/2026-04-28-goal-1-next-ships-synthesis.md` (Goal #1 ship sequence).

## TL;DR

The deep-dive projected CRYPTO MaxDD 140% → 9.21% via vol-targeting at a 15% annualized portfolio vol target. **Vol-targeting is already implemented and production-wired.** The MDD isn't 9% because line 99 clamps the minimum scaling factor at `0.25x`, capping how aggressively a high-vol asset can be downscaled. CRYPTO needs ~0.092x scaling for 15% target on 162% realized vol; the floor caps it at 0.25x, leaving residual portfolio vol at ~40% and a corresponding MDD floor around 60%, not 9%.

The fix is one line — but it's risk-changing code that deserves a daylight review, not a 02:00 UTC ship. Filing this audit + recommendation; not opening a PR tonight.

## Background — what's already shipped

`alpha_engine/kelly_position_sizer.py` has been live in `production_scanner.py:5012-5015` for some time:

```python
# 6h. Kelly Criterion Position Sizing (Half-Kelly + vol scaling + correlation penalty)
try:
    from kelly_position_sizer import apply_kelly_sizing
    portfolio_val = float(os.environ.get("ALPHA_PORTFOLIO_VALUE", "10000"))
    active = apply_kelly_sizing(active, portfolio_value=portfolio_val)
except Exception as e:
    print(f"  [KELLY] Position sizing skipped (non-fatal): {e}")
```

**The bare-name import works** because Python automatically adds the script's directory (`alpha_engine/`) to `sys.path[0]` when you run `python alpha_engine/production_scanner.py`. (I initially mis-read this as a silent-failure bug analogous to the auto_tuner module-path bug from Workstream A; that was wrong. The import succeeds.)

The module implements all three pieces from the deep-dive's PR-V spec:
- Kelly fraction (line 44)
- Vol-adjusted sizing at 15% target (line 78–100)
- Correlation penalty (line 107–128)

It's wired into the production pick path. So why does CRYPTO MaxDD measure 140% instead of the projected 9–25%?

## The clamp

Line 99 of `kelly_position_sizer.py`:

```python
def vol_adjusted_size(base_size: float, current_atr_pct: float,
                      target_vol: float = 0.15) -> float:
    realized_vol = current_atr_pct * math.sqrt(365)
    if realized_vol <= 0:
        return base_size
    vol_scale = target_vol / realized_vol
    # Clamp: never less than 0.25x (still get exposure), never more than 2x (overleveraged)
    return base_size * max(0.25, min(2.0, vol_scale))
```

The `max(0.25, ...)` is a "still get some exposure" safety rail. It prevents the function from returning ~0 sizing when realized vol is extreme. **But for the institutional-grade target the deep-dive recommends, that floor is the binding constraint.**

### The math

From `reports/deep_dive_crypto_mdd_reduction_2026_04_28.md` Phase 2.4:

- Per-trade `pnl_pct` stddev = 2.13%
- Trades/day = 23.12
- **Annualized vol = 162.77%**
- Target = 15%
- Required scale = 15 / 162.77 = **0.092x**

With the 0.25x floor, the effective scale is `max(0.25, 0.092) = 0.25x`. So for the highest-vol pick the function returns size `base × 0.25`, not `base × 0.092`.

**Resulting effective portfolio vol:** 0.25 × 162.77% = **40.7%** (vs 15% target).

**Resulting MDD compression vs uncapped:** the deep-dive's projection of `MDD 140% → 9.21%` assumed scaling 0.092x. With the 0.25x floor, the compression is the ratio `0.25 / 0.092 = 2.7x` weaker. Empirically MDD is around 140% currently, suggesting that even the 0.25x downscale isn't fully active — possibly due to other modifiers, the 2x upper clamp pulling some scale-ups, or correlation-penalty interactions.

## Recommended fix (small, isolated)

**Option A — Per-class minimum-scale config (recommended):**

Add a `min_scale_per_class` lookup table:

```python
# Per-class minimum-scale floors. Lower for high-vol classes where institutional
# downsize is required to hit the 15% target; keep at 0.25 for stable classes
# where over-aggressive downsize would produce ~0 exposure for no benefit.
MIN_SCALE_PER_CLASS = {
    "CRYPTO":    0.05,   # allow 0.05x for 162% ann-vol → 8.1% effective vol target
    "EQUITY":    0.20,   # 30% ann-vol → 0.5x clamp is generous
    "ETF":       0.20,
    "FOREX":     0.50,   # G10 FX is naturally low-vol; aggressive downsize is wasteful
    "COMMODITY": 0.30,
    "BOND":      0.50,
    "DEFAULT":   0.25,
}

def vol_adjusted_size(base_size, current_atr_pct, target_vol=0.15, asset_class="DEFAULT"):
    realized_vol = current_atr_pct * math.sqrt(365)
    if realized_vol <= 0:
        return base_size
    vol_scale = target_vol / realized_vol
    floor = MIN_SCALE_PER_CLASS.get(asset_class, MIN_SCALE_PER_CLASS["DEFAULT"])
    return base_size * max(floor, min(2.0, vol_scale))
```

Pros: keeps the safety rail conceptually but makes it class-aware. Doesn't disable the floor — just relaxes it where data justifies. Backward-compat (callers without `asset_class` get DEFAULT 0.25x).

Cons: requires every caller to pass `asset_class`, which is a non-trivial refactor for `compute_position_size` and `apply_kelly_sizing`.

**Option B — Add a hard 30d-rolling-DD halt at the gate:**

Independent of per-trade scaling, add a portfolio-level halt that refuses new emissions when 30-day realized PnL drawdown exceeds 15%. Per the deep-dive's PR-K spec, wire at `alpha_engine/production_scanner.py:5025` (the existing observability check). This catches the case where per-trade scaling is insufficient.

Pros: orthogonal to the per-trade scaling — doesn't risk breaking the existing function. Strictly additive guard. Smaller diff.

Cons: doesn't fix the underlying "can't scale enough" issue; only catches the consequence after the fact.

**Recommendation:** ship **Option B first** (smaller, safer, additive). It catches the real-world MDD before it gets to 140%. Then ship Option A as a follow-up after validating B works.

## What I'm NOT doing tonight (and why)

- Editing `kelly_position_sizer.py` directly — risk-changing code at 02:00 UTC. Daylight review for any change to this file.
- Opening a PR for Option A — needs caller-refactor across 10 files in `alpha_engine/`. Too much surface area for late-night work.
- Opening a PR for Option B — possible but interacts with `risk_policy_check.py:5019-5023` (already an observability check). Need to read more of that flow before adding the hard halt.

## Acceptance criteria for "vol-targeting actually delivers"

After whichever fix lands:

1. Re-run the canonical recompute against a 30-day-post-fix payload.
2. CRYPTO MaxDD should drop below **30%** (Tier 3 ceiling). Stretch target: <15% (Tier 2 / institutional).
3. Per-trade Sharpe should remain **above 0.04** (preserve edge while compressing variance).
4. PF should remain **above 1.10** (don't kill edge by over-downscaling).

## Why this matters for Goal #1

CRYPTO is n=1,598 — 45.7% of the entire ledger. Its MDD compression is the single largest lever for Goal #1's "phenomenal performance across ALL asset classes." Until vol-targeting actually targets vol (not just nominally), CRYPTO can't be Tier 2 even with PR #461's strategy/symbol kills.

The deep-dive's projected `MDD 140% → 9.21%` is achievable, but only after either Option A or Option B (or both) lands. With current code, the projection's math doesn't reach the production calculation.

## Cross-references

- `reports/deep_dive_crypto_mdd_reduction_2026_04_28.md` Phase 2.4 — the math projection
- `alpha_engine/kelly_position_sizer.py:78-100` — the clamp itself
- `alpha_engine/production_scanner.py:5012-5015` — production wire-up
- `alpha_engine/production_scanner.py:5019-5023` — adjacent risk_policy_check (where Option B's halt would slot in)
- `updates/2026-04-28-goal-1-next-ships-synthesis.md` §2 P0 #3 — sequence this fix sits in
