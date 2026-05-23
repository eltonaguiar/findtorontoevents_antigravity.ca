# Fix 3: Remove Blanket _BLOCKED_CATEGORIES, Add Per-Strategy Surgical Blocks

**Date:** 2026-04-19
**Author:** Buffy (Codebuff Agent)
**Status:** Implemented, pending PR review
**Related:** PR #240 (win-rate fix proposals), updates/2026-04-19-suggested-fixes-win-rate-and-audit-dashboard.md

---

## Problem

The production scanner's Gate 0 had a **blanket asset-class block** (`_BLOCKED_CATEGORIES`) that rejected ALL picks from 6 entire asset classes (equity, stock, etf, commodity, futures, bond), regardless of strategy quality:

```python
_BLOCKED_CATEGORIES = {"equity", "stock", "etf", "commodity", "futures", "bond"}
if category in _BLOCKED_CATEGORIES:
    reject_reason = "[NON-CRYPTO BLOCK] {category} picks disabled — 0-19% forward WR. Crypto-only mode active."
```

This was added on Mar 25, 2026 after equity showed 0% WR on 92 picks and commodity 19% WR on 16 picks. But the **root cause** was not the asset classes — it was **specific toxic strategies** (yahoo_analyst_consensus, claude_gainer_ml, goldmine_1x/2x/3x/4x_consensus, etc.) that polluted the sample.

The blanket block prevented **new, academically-backed strategies** (TSMOM 12m, Faber TAA, Connors RSI2, bond_yield_momentum, etc.) from ever entering production, since they could never build forward history while blocked.

## Fix

### 1. Removed `_BLOCKED_CATEGORIES` blanket block

Replaced with an empty set — no more entire-class bans.

### 2. Added `_BLOCKED_CATEGORY_STRATEGIES` — surgical per-strategy/per-class kill list

Instead of blocking all equity, only blocks the specific (category, strategy) pairs that are proven toxic:

```python
_BLOCKED_CATEGORY_STRATEGIES = {
    # Equity losers (0% WR strategies that polluted the 92-pick sample)
    # NOTE: stock/etf/bond are normalized to "equity" before Gate 0,
    # so bond/etf strategies must be listed under "equity" to match.
    ("equity", "yahoo_analyst_consensus"),
    ("equity", "claude_gainer_ml"),
    ("equity", "value_quality_factor"),
    ("equity", "consecutive_beats"),
    ("equity", "earnings_drift"),
    ("equity", "dividend_aristocrats"),
    ("equity", "penny_deep_oversold"),
    ("equity", "extreme_oversold_bounce"),       # was etf - normalized to equity
    # Equity goldmine strategies (0% WR, blocked in quality_gates.py too)
    ("equity", "goldmine_1x_consensus"),
    ("equity", "goldmine_2x_consensus"),
    ("equity", "goldmine_3x_consensus"),
    ("equity", "goldmine_4x_consensus"),
    # Commodity losers (19% WR on 16 picks)
    # NOTE: cot_positioning removed from block - it's in _BOOSTED_NON_CRYPTO_STRATEGIES
    # (1.15x boost) and has 50% WR / positive PnL on forex. Insufficient data on commodity.
    ("commodity", "cftc_cot_commercial_signal"),
    # Futures losers (Gate 5b already catches some)
    ("futures", "futures_mean_reversion"),
    ("futures", "ema_stack_momentum"),
}
```

### 3. Code-review fixes applied

Three issues caught by code-reviewer-lite and fixed:

| Issue | Fix |
|-------|-----|
| `("bond", "yahoo_analyst_consensus")` and `("etf", "extreme_oversold_bounce")` were dead entries — category is normalized to "equity" before Gate 0 | Moved both to `("equity", ...)` entries |
| `cot_positioning` was both **boosted** (1.15x in `_BOOSTED_NON_CRYPTO_STRATEGIES`) AND **blocked** — contradictory | Removed from block list (50% WR on forex, insufficient commodity data ≠ proven bad) |
| `goldmine_1x/2x/3x/4x_consensus` were caught by the old blanket block but not in the new surgical list | Added all 4 to equity block (also in downstream `quality_gates.py` `BLOCKED_ASSET_STRATEGY_PAIRS`) |

## Coverage Analysis

| Layer | What it catches |
|-------|----------------|
| **Gate 0** (`_BLOCKED_CATEGORY_STRATEGIES`) | 16 specific toxic (category, strategy) pairs — hard reject at scan time |
| **Downstream** (`quality_gates.py` `BLOCKED_STRATEGIES`) | Cross-class strategy blocks (asset-class-aware) — catches toxic strategies on any asset class |
| **Downstream** (`quality_gates.py` `BLOCKED_ASSET_STRATEGY_PAIRS`) | More granular (asset, strategy) blocks — catches strategies that are toxic on one class but work on another |
| **Downstream** (`quality_gates.py` `BLOCKED_DIRECTION_TRIPLES`) | Direction-specific blocks — catches e.g. SELL on equity/forex combos |
| **Gate 5b** (toxic forward WR) | Auto-blocks any strategy with <25% WR on 5+ forward-tested trades |
| **Gate 8** (algo probation) | Requires 0.80+ confidence + 10+ trades at 45%+ WR for algorithmic strategies |
| **Gate 10** (negative expectancy) | Blocks strategies with avg_pnl < -0.5% and WR < 30% on 15+ trades |

**New strategies NOT blocked** (this is the desired outcome):
- `tsmom_12m` — academic momentum strategy, needs forward history
- `faber_taa` — Faber Tactical Asset Allocation, proven in literature
- `connors_rsi2` / `stocks_rsi2_pullback` — 100% WR on 3 trades (already in `_BOOSTED_NON_CRYPTO_STRATEGIES`)
- `bond_yield_momentum` — relaxed in parallel change, needs forward history
- `cta_golden_cross_200` — 100% WR on 2 trades (already boosted)
- `cot_positioning` — 50% WR on forex, boosted 1.15x

## Files Changed

| File | Change |
|------|--------|
| `alpha_engine/production_scanner.py` | Replaced `_BLOCKED_CATEGORIES = {"equity", "stock", "etf", "commodity", "futures", "bond"}` with `_BLOCKED_CATEGORY_STRATEGIES = {16 specific toxic (category, strategy) pairs}`. Updated Gate 0 comment to explain the change rationale. Added normalization note. |

## Testing

- Python syntax validation: `py_compile.compile()` — **PASS**
- Code review: 3 issues found and fixed (see above)
- Gap analysis: verified no coverage gap between Gate 0 and downstream `quality_gates.py` filters

## Expected Impact

1. **Non-crypto strategies with proven or promising WR** can now enter production (were blocked before)
2. **Toxic strategies** remain blocked via surgical (category, strategy) pairs instead of blanket class blocks
3. **New strategies** (TSMOM 12m, Faber TAA, etc.) can accumulate forward history for data-driven evaluation
4. **Win-rate should improve** over 2-4 weeks as promising strategies build track records
