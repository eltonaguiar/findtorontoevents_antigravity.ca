# Asset-Class Tagger Investigation — Root Cause + Patch

## TL;DR

The 92% null-`asset_class` gap in `alpha_engine/data/closed_picks.json` is **NOT** caused by missing derivation logic. `audit_trail/dashboard_generator.py::_derive_asset_class()` is comprehensive (USDT→CRYPTO, =F→COMMODITY/FUTURES, =X→FOREX, hint-keys, source-system fallbacks).

The actual root cause is in `alpha_engine/outcome_resolver.py`: when the resolver closes a pick, it computes the resolved asset_class **internally** for threshold gating (`_resolve_asset_class(pick)`) but **never writes it back** to `pick["asset_class"]`. The pick is then appended to `closed_picks` and dumped to JSON with the original null value preserved.

**One-line fix unlocks the +/- $80K of hidden P&L** documented in `reports/unknown_asset_class_deep_investigation_2026_05_04.md` (5 buried elites + 5 buried disasters).

## Call-graph

```
quan_engine_scalp / ml_enhanced_*  (pick generators — emit pick with asset_class=None)
    └─> active_picks.json          (pick lands with asset_class=null)
            └─> outcome_resolver.py::resolve_single_pick(pick)         ←── BUG SITE
                    │
                    ├─ asset_class = _resolve_asset_class(pick)         line 689 / 955
                    │   ├─ reads pick["asset_class"] (null)
                    │   ├─ falls back to symbol suffix (BTCUSDT → CRYPTO)
                    │   └─ returns "CRYPTO" (string, used internally)
                    │
                    ├─ uses asset_class for win-threshold gating        line 690+
                    │   (CRYPTO=0.1bp, others=5bp)
                    │
                    └─ closed_picks.append(rp)                          line 2118 etc.
                        ↑ rp still has pick["asset_class"]=null!
                        ↑ resolved value was never persisted.

  └─> json.dump(closed_picks, f, indent=2, default=str)                 line 2123
        ↑ writes closed_picks.json with 92% null asset_class
```

Then downstream:

```
audit_trail/dashboard_generator.py
    ├─ _derive_asset_class()                                            (correct, comprehensive)
    └─ but only invoked at dashboard-render time on the active book
        — closed_picks.json is read-only into hf_stats.by_asset_class
        and inherits the null tags as-is.
```

## Evidence

`alpha_engine/outcome_resolver.py:612-631`:

```python
def _resolve_asset_class(pick: dict) -> str:
    """Best-effort asset_class string for threshold gating."""
    raw = str(pick.get("asset_class") or pick.get("category") or "").upper().strip()
    if raw:
        aliases = {"STOCKS": "EQUITY", "FX": "FOREX", "COMMODITIES": "COMMODITY",
                   "BONDS": "BOND", "INDICES": "INDEX"}
        return aliases.get(raw, raw)
    sym = str(pick.get("symbol", "") or "")
    if sym.endswith("=X"):
        return "FOREX"
    if sym.endswith("=F"):
        return "COMMODITY"
    if _is_non_crypto(pick):
        return "EQUITY"
    return "CRYPTO"
```

This function correctly classifies BTCUSDT, MATICUSDT, etc. as CRYPTO via the final `return "CRYPTO"` (after USDT-suffixed symbols pass through `_is_non_crypto()` returning False). But the **return value is a local variable in the caller**, not a mutation on the pick dict.

`alpha_engine/outcome_resolver.py:689`:

```python
asset_class = _resolve_asset_class(pick)        # local string
is_non_crypto = asset_class != "CRYPTO" and ... # used internally
# ... TP/SL touch detection, exit-price computation ...
# ... resolved pick written ...
# pick["asset_class"] is NEVER set.
```

## Concrete fix

**Patch 1** — `alpha_engine/outcome_resolver.py:689` (and line 955):

```python
asset_class = _resolve_asset_class(pick)
# ALSO persist the resolved class back to the pick so downstream
# consumers (dashboard_generator hf_stats, per-class panels,
# strategy promotion gates) see the same value the resolver used.
# Only overwrite if the original was null/empty/'UNKNOWN' to avoid
# clobbering upstream-tagged values.
_existing = str(pick.get("asset_class") or "").upper().strip()
if not _existing or _existing in ("UNKNOWN", "NONE"):
    pick["asset_class"] = asset_class
```

3 lines. No behavior change for picks that already have a valid asset_class (the conditional). Persists the already-computed value for the 6,886 null picks.

**Patch 2** — One-time backfill of the existing `closed_picks.json` after the writer fix lands. Either:

(a) **Re-run the resolver** on the existing closed picks (clean but slow; depends on resolver idempotency).

(b) **Backfill script** `tools/backfill_asset_class_in_closed_picks.py` — applies `_resolve_asset_class` to every null-tagged closed pick in-place. ~30 lines. The 99.9% CRYPTO heuristic from `reports/unknown_asset_class_deep_investigation_2026_05_04.md` matches what `_resolve_asset_class` already does, so the backfill is deterministic. Recommended.

## Why dashboard_generator.py's logic doesn't help

`_derive_asset_class()` in `dashboard_generator.py` is **only invoked on active picks** during dashboard generation, NOT on closed picks. Closed picks come pre-tagged from `alpha_engine/data/closed_picks.json` and the generator doesn't re-classify them.

Two reasons this is correct design:
1. Performance — re-classifying 7,472 closed picks on every dashboard render would be wasteful.
2. Audit trail — the asset_class at close-time is what matters for hf_stats; mutating it post-hoc breaks the historical record.

So the right place for the fix IS the resolver, not the generator. The resolver runs once per pick close and writes the canonical record.

## Validation

After Patch 1 lands, the next outcome_resolver run should:
- Mutate `pick["asset_class"]` for any null-tagged pick passing through.
- Each subsequent `closed_picks.json` write should have monotonically fewer null tags as new picks resolve.
- The HISTORICAL closed picks (the 6,886 already-null ones) need Patch 2 to retroactively get tags.

## EV unlock

Per `reports/unknown_asset_class_deep_investigation_2026_05_04.md`:

| Strategy | n | sum_$ | Surfaced after fix? |
|---|---|---|---|
| `ml_enhanced_FETUSDT_1d_B_lightgbm` | 44 | +$15,181 | ✅ ELITE |
| `ml_enhanced_INJUSDT_1d_B_lightgbm` | 28 | +$8,106 | ✅ ELITE |
| `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` | 47 | +$3,254 | ✅ ELITE |
| `ml_enhanced_RENDERUSDT_4h_D_ensemble_stack` | 37 | +$1,552 | ✅ ELITE |
| `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` | 31 | +$1,119 | ✅ ELITE |
| `ml_enhanced_TRXUSDT_1d_B_lightgbm` | 26 | -$33,094 | ⚠️ DISASTER (visible for blocking) |
| `ml_enhanced_APEUSDT_1d_D_ensemble_stack` | 30 | -$17,237 | ⚠️ DISASTER |
| `ml_enhanced_JTOUSDT_1d_B_lightgbm` | 30 | -$2,888 | ⚠️ DISASTER |
| `ml_enhanced_HBARUSDT_1d_D_ensemble_stack` | 28 | -$928 | ⚠️ DISASTER |
| `ml_enhanced_ALGOUSDT_15m_B_lightgbm` | 26 | -$700 | ⚠️ DISASTER |

Plus the 5,293 `quan_engine_scalp` picks become aggregable per-symbol and per-class — currently they wash out every cross-class metric on `/audit`.

## Related fixes already in place

The codebase already has TWO similar "UNKNOWN-trap" fixes documented in `_derive_asset_class()`:

- Line 6552-6565: copy_trader_intel sources auto-classify as CRYPTO.
- Line 3467 `_coerce_asset_class()`: re-derives when stamped value is empty/'UNKNOWN'/'NONE'.

Adding the resolver-side persistence (Patch 1) completes the pattern: every pick that reaches a closed state should carry an asset_class.

## Out of scope (deferred)

- Backfill of historical closed_picks.json (Patch 2) — separate PR.
- Source-emission fix for `quan_engine_scalp` to tag CRYPTO at pick-creation time (not resolver time) — eliminates the resolver round-trip but requires touching the scalp generator. Lower priority once Patch 1 + Patch 2 land.
- ML-enhanced strategy emission fixes (similar to quan_engine_scalp but per-strategy).

## Provenance

- Source: `alpha_engine/outcome_resolver.py:612-631, 689, 955, 2118-2123`
- Cross-references: `audit_trail/dashboard_generator.py::_derive_asset_class()` (lines 3265-3464); `_coerce_asset_class()` (line 3467).
- Cross-references: `reports/unknown_asset_class_deep_investigation_2026_05_04.md` (the 99.9% CRYPTO heuristic confirms the patch is safe).
- No code changes — read-only investigation per CLAUDE.md.
