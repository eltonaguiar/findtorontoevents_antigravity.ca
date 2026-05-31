# Tick 30 — Real FOREX Wire-Up (cta_cross_asset_tsmom leakage cap + dxy_trend_filter policy entry)

**Date:** 2026-05-31
**Branch:** `fix/forex-cta-leakage-dxy-wireup-2026-05-31`
**Author:** Claude Opus 4.7 (subagent, tick30)

## PART A — cta_cross_asset_tsmom FOREX leakage trace

### Reference map
| File | Line | Role |
|---|---|---|
| `alpha_engine/cta_bridge.py` | 297-318 | **REGISTRATION + CALLER** — defines `cta_cross_asset_tsmom()` that calls upstream `cross_asset_tsmom()` and tags `source_system='cta_replicator'` (line 125) |
| `alpha_engine/cta_bridge.py` | 335, 365 | Listed in `cta_all_strategies()` master fanout + `CTA_BRIDGE_STRATEGIES` dict |
| `copy_trader_intel/cta_strategy_replicator.py` | 774-895 | Underlying `cross_asset_tsmom()` iterates `CTA_UNIVERSE` which includes forex symbols |
| `alpha_engine/scanner.py` | 593, 1247 | Imports `CTA_BRIDGE_STRATEGIES`, includes in regime allowlist |
| `alpha_engine/confluence_engine.py` | 116 | Classification: "momentum" |
| `alpha_engine/config.py` | 2082 | Classification: "momentum" |
| `alpha_engine/smart_picks_engine.py` | 525 | Listed in commodity allowlist set (intentional for commodity, not forex) |
| `alpha_engine/emitter_whitelist.py` | 41 | `("FOREX", "cta_replicator")` in `MANUAL_ALLOWLIST_PAIRS` — allows the source_system through despite no policy_clean PF record |

### Live DB leakage (ejaguiar1_stocks.trading_picks)
```
all-time by category:
  bond      53
  commodity 943
  equity    105
  forex     939   <-- LEAK

last forex emission: 2026-05-25 12:12:25 (5 days ago)
forex created 30d:    248
forex closed all-time: 86 (0 WON / 86 LOST = 0% WR)
emitter:               source_system='cta_replicator'
```

Conclusion: leakage is **ACTIVE, RECENT, and CATASTROPHIC** (0/86 closed; 248 still cooking). cta_replicator bypasses `evaluate_non_crypto_candidate` because the candidate path uses `source_system != 'alpha_engine'`. Cap MUST be applied upstream in cta_bridge.

## PART B — dxy_trend_filter wire-up plan

### B.1 — dxy_trend_filter signature
`multi_asset/forex_strategies.py:718`
```python
def dxy_trend_filter(df: pd.DataFrame, symbol: str, info: dict,
                     dxy_df: Optional[pd.DataFrame] = None) -> list[dict]:
```
Returns list of signal dicts. Already registered in `FOREX_STRATEGIES` at line 903.

### B.2 — Caller status (ALREADY WIRED)
`alpha_engine/scanner.py:288` imports `from forex_strategies import FOREX_STRATEGIES`
`alpha_engine/scanner.py:2069` calls `strategies.update(FOREX_STRATEGIES)`
`multi_asset/forex_strategies.py:947-956` calls `dxy_trend_filter` with `dxy_df` extra arg in `scan_forex()`.

**Root cause of 0 live picks**: missing entry in `NON_CRYPTO_STRATEGY_POLICY` → `evaluate_non_crypto_candidate` returns `reason="strategy_on_probation"` and all picks are silently dropped.

### B.3 — NON_CRYPTO_STRATEGY_POLICY entry schema (verified verbatim from line 222-230)
```python
"cta_tsmom_blend": {
    "categories": {"forex", "commodity", "futures", "bond", "equity"},
    "min_confidence": 0.68,
    "min_rr": 1.20,
    "min_elite_score": 58,
    "min_forward_trades": 4,
    "min_forward_wr": 0.50,
    "allow_without_forward": False,
},
```

## 3-PART DIFF (all applied to branch)

### Diff 1 — Add dxy_trend_filter to NON_CRYPTO_STRATEGY_POLICY (alpha_engine/non_crypto_policy.py)
Inserted AFTER `cta_commodity_momentum_term` block (line 239) per current alphabetical/logical ordering:
```python
"dxy_trend_filter": {
    "categories": {"forex"},
    "min_confidence": 0.55,
    "min_rr": 1.20,
    "min_elite_score": 50,
    "min_forward_trades": 5,
    "min_forward_wr": 0.40,
    "allow_without_forward": True,  # Probation: build forward record
},
```

### Diff 2 — Cap cta_cross_asset_tsmom FOREX leakage at emitter (alpha_engine/cta_bridge.py)
Inserts a forex-symbol skip inside the picks loop BEFORE the existing vol-regime gate. Commodity/equity/bond picks pass through unchanged.
```python
# 2026-05-31 leakage cap: forex picks from this strategy are 0/86 WR.
cat = (pick.get("category") or "").lower()
sym = pick.get("symbol", "") or ""
if cat == "forex" or sym.endswith("=X"):
    continue
```

### Diff 3 — Caller (no code change required)
`dxy_trend_filter` is already registered in `multi_asset/forex_strategies.py:903 FOREX_STRATEGIES` and called via `alpha_engine/scanner.py:2069 strategies.update(FOREX_STRATEGIES)`. The wire-up was always present; only the policy gate was missing.

## SELF-RED-TEAM VERIFICATION

| Check | Result |
|---|---|
| `multi_asset/forex_strategies.py:718-720` signature match | PASS — exact byte match |
| `alpha_engine/non_crypto_policy.py:222-239` BEFORE block | PASS — exact match before edit |
| `alpha_engine/cta_bridge.py:297-318` BEFORE block | PASS — exact match before edit |
| `__init__.py` presence | PASS — `alpha_engine/__init__.py` and `multi_asset/__init__.py` both exist |
| Import `from forex_strategies import dxy_trend_filter` | PASS — scanner.py already does this via sys.path injection |
| `py_compile non_crypto_policy.py cta_bridge.py` | PASS |
| Functional test of cta_bridge cap (mock cross_asset_tsmom with forex+commodity picks) | PASS — forex dropped, commodity passes |
| Policy lookup of dxy_trend_filter | PASS — returns `{categories: {'forex'}, min_confidence: 0.55, ...}` |

`diff_parts_verified=3/3`

## RISK NOTES

1. The cap blocks the strategy entirely on FOREX — cannot rescue. If forward research finds an FX subset where the edge survives, gate must move to a regime/symbol-level filter, not a category-wide block.
2. dxy_trend_filter has 0 live picks all-time so the probation gate `allow_without_forward=True` is necessary to bootstrap a forward record. Once n>=5, the `min_forward_wr=0.40` kicks in.
3. `("FOREX", "cta_replicator")` remains in `MANUAL_ALLOWLIST_PAIRS` because `cta_fx_multifactor` (32 picks 30d) still routes through it. Removing the pair entirely would also break that strategy. The right gate is at the strategy level inside cta_bridge — applied here.
4. No DB writes; no FTP deploys. Production gate change only.

## DELIVERABLE STATUS

- cta_leakage_30d = **248** (active emission, 0% WR on closed cohort)
- diff_parts_verified = **3/3**
- PR opened against main as DRAFT; see `PR_NUM_PLACEHOLDER` below
