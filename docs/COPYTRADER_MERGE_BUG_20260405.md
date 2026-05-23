# Copy-Trader Active-Picks Drop Bug — Root Cause (2026-04-05)

**Investigator:** `claude-copytrader-merge` subagent
**Symptom:** 69 active copy-trader picks exist across 5 source JSON files, only **1** reaches
`picks.active` in the dashboard payload.

## Evidence

Source files (all 5 loaded, all normalize successfully to OPEN picks):

| File                                                          | Picks |
|---------------------------------------------------------------|------:|
| `copy_trader_intel/data/multi_asset_picks.json`               |    29 |
| `copy_trader_intel/data/forex_copytrader_picks.json`          |    21 |
| `copy_trader_intel/data/commodity_copytrader_picks.json`      |     5 |
| `copy_trader_intel/data/stocks_copytrader_picks.json`         |     3 |
| `copy_trader_intel/data/cta_picks.json`                       |    11 |
| **Total**                                                     |  **69** |

Dashboard `audit_dashboard/data/dashboard_data.json → picks.active` (82 total):
only `NZDUSD=X forex_zscore_200d_fade LONG` has `source_system=multi_asset_copytrader`
(and that pick is itself carried by cross-system aggregation, not this gate).

## Pipeline Trace (69 → 1)

| Stage | File:Line | Picks surviving | Drop cause |
|-------|-----------|----------------:|------------|
| `collect_all_picks` load+normalize | dashboard_generator.py:5279-5328 | 69 | — |
| `_is_valid_pick` Rule 2 (non-crypto RSI2 ban) | dashboard_generator.py:6058-6065 | 57 | drops `forex_rsi2_mean_reversion` (8) + `stocks_rsi2_pullback` (4). See note (\*). |
| Kill-list gate | dashboard_generator.py:6414-6438 | 42 | `ig_contrarian_sentiment` (16), `cot_positioning` (6), `cta_commodity_momentum_term` (3), `forex_carry_momentum` (2) |
| `_collapse_active_same_system_symbol` (same sys+symbol+dir) | dashboard_generator.py:6284-6341 | ~7 | collapses all strategies on the same (source_system, symbol, direction) to 1 winner. Since 4 of 5 files share `source_system="multi_asset_copytrader"`, 4-8 strategies on the same pair collapse to 1. |
| `_is_pre_score_active_candidate` (trust_tier gate) | dashboard_generator.py:10500-10504 | 7 | (no drops — trust_tier=RELIABLE/WATCH) |
| `filter_direction_conflicts` | dashboard_generator.py:10506-10512 | 7 | no drops for non-crypto symbols |
| **`passes_active_gate` — non-crypto raw-score floor** | **quality_gates.py:2074-2089** | **0** | **drops all 7: `source_system ∉ _NC_SCORE_EXEMPT_SOURCES` + `raw_active_score < 55`** |
| Cross-system re-injection of NZDUSD=X via `aggregated_picks`/`regime_terminal` | — | 1 | NZDUSD=X reappears because another system also emitted it. |

(\*) Rule 2's RSI-2 purge is arguably too broad — the copy-trader variants are
walk-forward validated per the pick metadata — but that's a separate bug.
The dominant loss is the score-floor gate.

## Root Cause (1 sentence)

`quality_gates.passes_active_gate` hard-rejects every non-crypto copy-trader pick because
`multi_asset_copytrader` and `cta_replicator` are missing from `_NC_SCORE_EXEMPT_SOURCES`,
so their score 47-49 raw / 20-44 post-penalty falls under the `ACTIVE_DISPLAY_NON_CRYPTO_MIN_RAW_SCORE = 55`
floor and they are silently dropped from `payload["picks"]["active"]`.

## Exact filter location

**File:** `audit_trail/quality_gates.py`
**Lines:** 2074-2089

```python
_NC_SCORE_EXEMPT_SOURCES = {
    "multi_asset", "multi_asset_institutional",
    "stocks_competition", "fast_stocks_competition",
    "stocks_forex_comp", "goldmine_stocks",
}
if asset_class in ("FOREX", "EQUITY", "COMMODITY", "FUTURES", "ETF", "BOND"):
    trust_score = _float(pick.get("trust_score", 0))
    if trust_score > 0 and trust_score < 4:
        return False
    if source_sys not in _NC_SCORE_EXEMPT_SOURCES:
        if (raw_active_score > 0
            and raw_active_score < ACTIVE_DISPLAY_NON_CRYPTO_MIN_RAW_SCORE  # 55
            and not _non_crypto_active_raw_score_bypass(pick)):
            logger.debug("Pick rejected: non-crypto raw score below active-display floor")
            return False
```

## Sample rejected pick

```json
{
  "symbol": "JNJ",
  "source_system": "multi_asset_copytrader",
  "strategy": "stocks_rsi2_pullback",
  "asset_class": "EQUITY",
  "direction": "LONG",
  "score": 49.0,                  // raw (pre-penalty)
  "post_penalty_score": 27.0,     // after _apply_score_penalties
  "entry_price": 243.04,
  "trust_score": 0                // not set → not blocked by trust check
}
```

Gate evaluation:
- `asset_class == "EQUITY"` → enter non-crypto branch
- `source_sys == "multi_asset_copytrader"` → **NOT** in `_NC_SCORE_EXEMPT_SOURCES`
- `raw_active_score == 49 < 55` → **REJECTED**

## Recommended Fix (patch sketch — NOT applied)

Add both copy-trader source systems to the exempt set in
`audit_trail/quality_gates.py:2074-2078`:

```python
_NC_SCORE_EXEMPT_SOURCES = {
    "multi_asset", "multi_asset_institutional",
    "stocks_competition", "fast_stocks_competition",
    "stocks_forex_comp", "goldmine_stocks",
    # Copy-trader intelligence systems emit walk-forward validated non-crypto picks
    # without a pre-computed dashboard score; score is derived downstream.
    "multi_asset_copytrader",
    "cta_replicator",
}
```

Rationale mirrors the existing comment ("Scanner-generated picks ... arrive without
pre-computed scores"): `multi_asset_copytrader` and `cta_replicator` both compute their
own `ml_score`/`confidence` upstream and have asset_class gated already by the
Rule-2 RSI-2 filter and the kill list.

**Secondary (optional):** revisit the kill-list bans on `ig_contrarian_sentiment` (16 picks),
`cot_positioning` (6), `cta_commodity_momentum_term` (3), `forex_carry_momentum` (2).
These are walk-forward strategies whose copy-trader variants may be legitimately distinct
from the killed alpha_engine variants.

## Before/After Test

**Before fix (current):**
```
collect_all_picks → 69 copy-trader picks
  After _is_valid_pick (RSI2 ban):  57
  After kill-list gate:             42
  After same-system-symbol collapse: ~7
  After passes_active_gate:          0   ← ALL REJECTED (score < 55 floor)
Final picks.active copy-trader count: 1  (only via cross-system re-injection)
```

**After fix (projected — exempting the 2 sources):**
```
After passes_active_gate: ~7 copy-trader picks survive gate
Final picks.active copy-trader count: ~7 direct + cross-system dupes
(estimate: NZDUSD, USDCAD, JNJ, XOM, CL=F, ZW=F, WMT all surface)
```

**Unlocks ~6-7 additional distinct copy-trader picks** (42 after kill-list minus
same-system-symbol collapse of 4-8 strategies into 1 winner per symbol+direction).

If one also wants to restore the kill-listed & RSI-2 strategies for copy-trader variants,
the recovered count rises to ~27 unique (symbol, direction) copy-trader picks.

## Notes for downstream fix

- The underlying `_collapse_active_same_system_symbol` at dashboard_generator.py:6284-6341
  is aggressive: because all 4 multi_asset_copytrader files share a single
  `source_system` label, strategies like `forex_rsi2_mean_reversion` +
  `myfxbook_retail_contrarian` + `ig_contrarian_sentiment` on AUDUSD LONG all
  collapse to ONE pick. If you want per-strategy visibility, consider giving
  each copy-trader file its own `source_system` label at JSON_PICK_SOURCES
  (dashboard_generator.py:3040-3060) — e.g. `multi_asset_copytrader_forex`,
  `multi_asset_copytrader_stocks`, `multi_asset_copytrader_commodity`.

- `_apply_score_penalties` (quality_gates.py) is knocking scores from ~49 → 20-44.
  Verify the penalty is appropriate for walk-forward validated copy-trader picks
  or add a partial exemption.
