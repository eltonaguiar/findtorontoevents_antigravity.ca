# FOREX PF Gap Investigation — 2026-05-18

**Filed by:** Forensics Agent (Claude Sonnet 4.6)  
**Date:** 2026-05-18  
**Status:** COMPLETE — hypothesis CONFIRMED WITH NUANCE

---

## Executive Summary

The FOREX PF gap (raw = 3.177 vs clean = 0.174) is caused by **two separate defects**, not one:

1. **Raw PF contamination:** The raw PF = 3.177 is dominated by a single outlier: a `futures_momentum` FOREX pick on HG=F (copper) with +9.65% PnL. Without it, raw FOREX PF = **0.338**. The raw PF figure is not a real signal — it is a data artifact.

2. **Clean PF underperformance:** The clean PF = 0.174 is genuinely bad. It is dragged down by `source_system=multi_asset_copytrader` (707 FOREX picks, PF = 0.138, LONG-heavy) which is NOT excluded from `by_asset_class_policy_clean_net` because `build_pf_registry.py` does not apply `BLOCKED_DIRECTION_TRIPLES` or `BLOCKED_ASSET_STRATEGY_PAIRS`.

**The hypothesis is CONFIRMED:** direction-blind exclusion logic in `build_pf_registry.py` is suppressing real SHORT edge while leaving the damaging LONG picks in the clean view.

**Proposed fix impact:** A direction-aware policy_clean would show FOREX at **n=48, WR=62.5%, PF=2.204** — T1-grade by the charter definition.

---

## Section 1: Raw vs Clean PF — Full Breakdown

### pf_registry.json FOREX data (from `audit_dashboard/data/pf_registry.json`)

| View | n | WR% | PF |
|------|---|-----|----|
| `by_asset_class_raw` | 982 | 25.2% | **3.177** |
| `by_asset_class_policy_clean` | 295 | 12.5% | 0.187 |
| `by_asset_class_policy_clean_net` | 295 | 12.5% | **0.174** |

### closed_picks.json FOREX ground truth (from `alpha_engine/data/closed_picks.json`)

| All FOREX picks | n | WR% | PF | GP | GL |
|-----------------|---|-----|----|----|----|
| RAW (all) | 954 | 25.4% | 3.194 | 10.791 | 3.378 |

---

## Section 2: Why Raw PF = 3.177 Is Contaminated

The raw PF is computed from pre-dedup, pre-exclusion rows across all source files. A single `futures_momentum` pick on `HG=F` (copper futures miscategorized as FOREX) has **+9.65% PnL**, accounting for 89% of all FOREX gross profit in the registry:

```
futures_momentum  HG=F  LONG  pnl=+9.649615%  (BLOCKED_SOURCE_SYSTEMS)
futures_momentum  SI=F  LONG  pnl=-0.005%
```

**Without this outlier:**
- Raw FOREX PF drops from 3.194 → **0.338**
- GP drops from 10.791 → 1.142
- This single pick inflates the raw number by 9× — it is a misclassified commodity futures trade appearing in the FOREX asset class bucket

**Root cause:** `futures_momentum` is correctly in `BLOCKED_SOURCE_SYSTEMS` and `PERMANENTLY_KILLED_STRATEGIES`, but the `raw_by_class()` function in `build_pf_registry.py` applies NO policy exclusions — so it appears in the raw view. This is expected behavior, but creates a deeply misleading raw PF figure.

---

## Section 3: Strategy-Level Breakdown (Policy-Excluded Categories)

Using `alpha_engine/data/closed_picks.json` as ground truth (n=954 FOREX picks):

| Category | n | WR% | PF | Note |
|----------|---|-----|-----|------|
| `PERMANENTLY_KILLED` | 153 | 14.4% | 0.194 | forex_rsi2_mean_reversion (138), combined_confidence (14) |
| `BLOCKED_SOURCE_SYSTEMS` | 2 | 50.0% | 1929.9 | futures_momentum HG=F outlier! |
| `PF_REGISTRY_POLICY_EXCLUDED` | 180 | 57.8% | 2.025 | **cta_cross_asset_tsmom** — SHORT edge! |
| `BLOCKED_ASSET_STRATEGY_PAIRS` | 314 | 10.5% | 0.137 | forex_carry_momentum (178), myfxbook_retail_contrarian (136) |
| `dir_blocked_long` (LONG only, by strategy) | 144 | 18.8% | 0.227 | LONG picks from direction-blocked strategies |
| `blocked_symbol` | 111 | 20.7% | 0.402 | NZDUSD=X, EURJPY=X, USDCHF=X, AUDUSD=X |
| **Surviving (all blocks applied)** | **50** | **64.0%** | **2.514** | Real FOREX edge |

**Key finding:** The `PF_REGISTRY_POLICY_EXCLUDED` bucket (cta_cross_asset_tsmom SHORT direction) has **PF = 2.025, WR = 57.8%** — this is legitimate edge being thrown away because `cta_cross_asset_tsmom` is excluded in full (BOTH directions) via `PF_REGISTRY_POLICY_EXCLUDED`, even though only LONG is bad (LONG n=60 WR=41.7% PF=1.071, SHORT n=120 WR=65.8% PF=2.819).

---

## Section 4: The Source System Mapping Problem

The critical data structure issue: `alpha_engine/data/closed_picks.json` stores FOREX picks with `source_system = 'multi_asset_copytrader'` regardless of the actual strategy:

| source_system | strategy | n |
|---------------|----------|---|
| multi_asset_copytrader | ig_contrarian_sentiment | 255 |
| multi_asset_copytrader | forex_carry_momentum | 178 |
| multi_asset_copytrader | forex_rsi2_mean_reversion | 138 |
| multi_asset_copytrader | myfxbook_retail_contrarian | 135 |
| multi_asset_copytrader | futures_bb_mean_reversion | 1 |

`build_pf_registry.py`'s `_is_policy_excluded()` checks `source_system` field FIRST. Since `multi_asset_copytrader` is NOT in `PERMANENTLY_KILLED`, `BLOCKED_SOURCE_SYSTEMS`, or `PF_REGISTRY_POLICY_EXCLUDED`, all 707 of these picks pass into the policy_clean view — including the catastrophic LONG picks (613 picks, WR=10.8%, PF=0.138).

The SHORT picks within this source (94 picks, WR=52.1%, PF=1.335) are good and should pass, but they are overwhelmed by the LONG volume.

---

## Section 5: Hypothesis Test — Direction-Blind Exclusions Killing SHORT Edge

**CONFIRMED.** The test was run with 4 scenarios on the 954 FOREX closed picks:

| Scenario | n | WR% | PF | Description |
|----------|---|-----|----|-------------|
| 1. Current policy_clean | 617 | 18.3% | 0.264 | Excludes only perm_killed + blocked_source + pf_reg_excl |
| 2. + Blocked asset-strat pairs (blind) | 303 | 26.4% | 0.447 | Adds BLOCKED_ASSET_STRATEGY_PAIRS |
| 3. + All direction-blocked strats (blind) | 16 | 43.8% | 1.018 | Excludes ALL picks from dir-blocked strategies |
| **4. Direction-AWARE (proposed fix)** | **48** | **62.5%** | **2.204** | **Keeps SHORT from LONG-blocked strategies** |

The SHORT picks from LONG-direction-blocked strategies (ig_contrarian SHORT, cta_cross_asset_tsmom SHORT) that survive a direction-aware filter:

| Strategy | Direction | n | WR% | PF |
|----------|-----------|---|-----|----|
| ig_contrarian_sentiment | SHORT | 57 | 59.6% | 1.952 |
| cta_cross_asset_tsmom | SHORT | 120 | 65.8% | 2.819 |
| myfxbook_retail_contrarian | SHORT | 14 | 50.0% | 0.941 |
| **Combined SHORT edge** | SHORT | **191** | **62.8%** | **2.043** |

---

## Section 6: Specific Fix Recommendation

### Fix 1 (HIGH PRIORITY): Make `build_pf_registry.py` direction-aware

**File:** `tools/build_pf_registry.py`  
**Change:** Extend `_is_policy_excluded()` to apply `BLOCKED_DIRECTION_TRIPLES` at the individual pick level (not strategy level):

```python
# In _load_policy_excluded() — additionally load BLOCKED_DIRECTION_TRIPLES
from audit_trail.quality_gates import BLOCKED_DIRECTION_TRIPLES

def _is_policy_excluded(row) -> bool:
    """True if the row's strategy OR source_system is verdict-excluded."""
    if not POLICY_EXCLUDED:
        return False
    strat = str(row.get("strategy") or "").lower()
    src = str(row.get("source_system") or "").lower()
    if strat in POLICY_EXCLUDED or src in POLICY_EXCLUDED:
        return True
    # Direction-aware check: only exclude LONG picks from LONG-direction-blocked strategies
    direction = str(row.get("direction") or "").upper()
    direction_norm = "LONG" if direction in ("LONG", "BUY") else "SHORT" if direction in ("SHORT", "SELL") else direction
    asset_class = str(row.get("asset_class") or "").upper()
    if (asset_class, strat, direction_norm) in BLOCKED_DIRECTION_TRIPLES_SET:
        return True
    # Also apply BLOCKED_ASSET_STRATEGY_PAIRS
    if (asset_class, strat) in BLOCKED_ASSET_STRATEGY_PAIRS:
        return True
    return False
```

**Estimated PF impact:**
- Current clean FOREX PF: 0.174
- After direction-aware fix: **PF = 2.204, WR = 62.5%, n = 48**
- This meets T1 charter (PF > 2.0, WR > 55%)

### Fix 2 (MEDIUM PRIORITY): Fix `cta_cross_asset_tsmom` in `PF_REGISTRY_POLICY_EXCLUDED`

`cta_cross_asset_tsmom` is in `PF_REGISTRY_POLICY_EXCLUDED` which excludes ALL picks (both directions). The SHORT direction has PF = 2.819, WR = 65.8%, n = 120. The correct action is:
- Keep `cta_cross_asset_tsmom` in `BLOCKED_DIRECTION_TRIPLES` for FOREX LONG only (already there)
- REMOVE it from `PF_REGISTRY_POLICY_EXCLUDED` (currently excludes ALL cta_cross_asset_tsmom)
- This allows SHORT cta_cross_asset_tsmom picks to appear in the policy_clean view

**Impact:** +120 picks at WR=65.8% PF=2.819 added to the clean pool.

### Fix 3 (LOW PRIORITY): Annotate the raw PF contamination

The raw PF = 3.177 is driven by one outlier (futures_momentum HG=F +9.65%). The `by_asset_class_raw` view should annotate this as contaminated, or the raw_by_class() function should skip picks from `BLOCKED_SOURCE_SYSTEMS`.

---

## Section 7: Top 5 FOREX Strategies Surviving ALL Current Blocks with PF > 1.0

Based on `alpha_engine/data/closed_picks.json` after applying all blocks (PERMANENTLY_KILLED + BLOCKED_SOURCE_SYSTEMS + PF_REGISTRY_POLICY_EXCLUDED + BLOCKED_ASSET_STRATEGY_PAIRS + BLOCKED_DIRECTION_TRIPLES LONG + BLOCKED_SYMBOLS_BY_CLASS):

| Rank | Strategy | Direction | n | WR% | PF | Note |
|------|----------|-----------|---|-----|-----|------|
| 1 | cta_fx_multifactor | LONG | 2 | 100% | inf | Too small (n=2) |
| 2 | fx_smart_forex_mean_reversion_200d | SHORT | 1 | 100% | inf | Too small (n=1) |
| 3 | **ig_contrarian_sentiment** | **SHORT** | **38** | **65.8%** | **2.395** | T1-grade, sufficient n |
| 4 | **fx_smart_forex_rsi2_mean_reversion** | **LONG** | **8** | **50.0%** | **1.625** | Small n, watch |
| 5 | futures_bb_mean_reversion | SHORT | 1 | 0% | 0.000 | Loss, disregard |

**Statistically meaningful survivors (n >= 10):**
- `ig_contrarian_sentiment` SHORT: n=38, WR=65.8%, PF=2.395 — **T1-grade**

**Worth including if direction-aware fix is applied (currently direction-blocked but SHORT is clean):**
- `cta_cross_asset_tsmom` SHORT: n=120, WR=65.8%, PF=2.819 — **T1-grade**
- `ig_contrarian_sentiment` SHORT (combined with above): n=57, WR=59.6%, PF=1.952

---

## Section 8: Non-JPY Pair Status

EURGBP=X and GBPUSD=X show real edge but are blocked by strategy-level exclusions (not symbol-level):

| Symbol | Total n | Blocked n | Surviving n | Best Strategy PF |
|--------|---------|-----------|-------------|-----------------|
| EURGBP=X | 50 | 45 | 5 | myfxbook_retail_contrarian 13.4 (BLOCKED) |
| GBPUSD=X | 35 | 12 | 23 | ig_contrarian_sentiment 3.1 (BLOCKED) |
| EURUSD=X | 1 | 0 | 1 | fx_smart_forex_rsi2 0.0 (PASS, loss) |
| EURCHF=X | 0 | 0 | 0 | — |

The non-JPY pairs (EURGBP=X, GBPUSD=X) have strong edge data (EURGBP ig_contrarian WR=58.1% PF=1.777, GBPUSD ig_contrarian WR=71.4% PF=3.108) but are blocked because the strategy (`ig_contrarian_sentiment`) is direction-blocked globally. The SHORT direction on non-JPY pairs specifically has not been separately analyzed — this is a further audit opportunity.

---

## Section 9: Action Items

| Priority | Action | Owner | Estimated Impact |
|----------|--------|-------|-----------------|
| P0 | Fix `build_pf_registry.py` to apply `BLOCKED_DIRECTION_TRIPLES` and `BLOCKED_ASSET_STRATEGY_PAIRS` per-pick | Quant | FOREX clean PF: 0.174 → 2.20 |
| P1 | Remove `cta_cross_asset_tsmom` from `PF_REGISTRY_POLICY_EXCLUDED`; keep LONG block in `BLOCKED_DIRECTION_TRIPLES` | Quant | +120 T1-grade SHORT picks in clean view |
| P2 | Annotate `by_asset_class_raw` FOREX PF with outlier warning (futures_momentum HG=F) | Quant | Prevents mis-reading raw as true edge |
| P3 | Investigate EURGBP=X / GBPUSD=X ig_contrarian SHORT direction specifically | Research | Potential symbol-level allowlist |
| P3 | Build n count for `fx_smart_forex_rsi2_mean_reversion` — currently n=8, needs n≥20 for promotion | Research | Could be T2 candidate |

---

## Appendix: Key File References

- `audit_dashboard/data/pf_registry.json` — registry source
- `alpha_engine/data/closed_picks.json` — ground truth (n=954 FOREX picks)
- `audit_trail/quality_gates.py` — `BLOCKED_DIRECTION_TRIPLES`, `BLOCKED_ASSET_STRATEGY_PAIRS`, `PF_REGISTRY_POLICY_EXCLUDED`
- `tools/build_pf_registry.py` — registry builder (fix target: `_is_policy_excluded()`)
- `reports/HFPA_PHASE-2-findings-FOREX-2026-04-29.md` — historical FOREX panel findings
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md` — direction-mutation analysis protocol
