# Agent E — adaptive_tp_sl.py asset_class Fix

## Task
Stop `alpha_engine/adaptive_tp_sl.py` from silently defaulting non-crypto
picks (FX, equity, commodity, futures, ETF) to crypto during TP/SL
enrichment, and back-fill `asset_class` / `category` on each pick so the
downstream ledgers (`closed_picks.json`, `universal_resolved_picks.json`)
get correct tags.

## PR
fix/adaptive-tp-sl-asset-class — "fix(adaptive-tp-sl): infer asset_class
from symbol instead of defaulting to crypto"

## Files modified
- `alpha_engine/adaptive_tp_sl.py` — replace `cat or "crypto"` defaults with
  symbol-based inference (`_infer_asset_class_from_symbol`); add
  `_ensure_asset_class()` helper that backfills `asset_class` + `category`
  on each pick during `apply_adaptive_tp_sl()`; add DEFAULTS / DEFAULT_ATR_PCT
  entries for `etf` and `futures`.
- `tests/test_adaptive_tp_sl_asset_class.py` — new regression test (8 cases)
  covering all 6 asset classes plus an "existing tag respected" guard and a
  direct unit test of the inference helper.
- `docs/agents/agent_e_adaptive_tp_sl_fix.md` — this report.

## Why (root cause)
`apply_adaptive_tp_sl()` read `category = pick.get("category", "crypto")`
and `_normalize_category()` itself contained `cat = (cat or "crypto")`. Any
pick that arrived without a category — which is the common case for FX /
equity / commodity feeds — was treated as crypto, looked up in the crypto
DEFAULTS bucket, given crypto-scale TP/SL (3% / 2% — wildly wrong for FX
which should be 0.3% / 0.2%), and never had its `asset_class` written back.
The downstream ledger writers therefore saw `asset_class` either missing or
set to whatever upstream had — leaving ~99% of non-crypto rows in
`alpha_engine/data/closed_picks.json` and
`audit_trail/data/universal_resolved_picks.json` tagged UNKNOWN or CRYPTO.
This is the same root cause Agent D pinpointed in PR #159 and that Mercury
flagged in `MERCURY_APRIL132026.MD`. PR #145 added a sister helper
(`tools/data_integrity/_common.classify_asset()`) which we mirror here in
an inlined, extended form so this module stays self-contained.

## Before / after behavior
Synthetic pick fixtures (no `asset_class`/`category` preset, fresh strategy
with no cache history → reaches the default branch):

| Symbol  | Before (asset_class) | After (asset_class) | After (category) |
|---------|----------------------|---------------------|------------------|
| BTCUSDT | (unset, treated CRYPTO) | CRYPTO            | crypto           |
| EURUSD  | (unset, treated CRYPTO) | FOREX             | forex            |
| AAPL    | (unset, treated CRYPTO) | EQUITY            | equity           |
| GC=F    | (unset, treated CRYPTO) | COMMODITY         | commodity        |
| ES=F    | (unset, treated CRYPTO) | FUTURES           | futures          |
| SPY     | (unset, treated CRYPTO) | ETF               | etf              |

Existing tags are honored: a pick that already has
`asset_class="FOREX"` is left untouched.

## Verification
- `python -m py_compile alpha_engine/adaptive_tp_sl.py` → OK
- `python -m pytest tests/test_adaptive_tp_sl_asset_class.py -q` → **8 passed**
  (7 had failed before the fix, confirming the regression test was
  load-bearing).

## Scope guardrails honored
- Did NOT modify `audit_trail/dashboard_generator.py` (Session 3 already
  patched that code path).
- Did NOT modify any other file under `alpha_engine/` or `audit_trail/`.
- Did NOT backfill or rewrite any existing rows in `closed_picks.json` /
  `universal_resolved_picks.json` (separate data migration).
- Did NOT touch strategies, gates, filters, or scoring.
- New test is self-contained — it monkeypatches the in-memory cache and
  redirects `OUTPUT_PATH` to a tmp file so no live data is touched.

## Follow-ups
1. **Backfill existing UNKNOWN-tagged rows.** Run
   `tools/data_integrity/_common.classify_asset()` (or the new
   `_infer_asset_class_from_symbol`) over both
   `alpha_engine/data/closed_picks.json` and
   `audit_trail/data/universal_resolved_picks.json` to overwrite
   `asset_class` where it is missing or `UNKNOWN`. Stage as a one-shot
   migration script under `tools/data_integrity/backfill_asset_class.py`.
2. **Audit dashboard re-aggregation.** After the backfill, `/audit FOREX`
   and `/audit EQUITY` filters should start returning the recovered rows
   the same way Session 3 recovered 1,142 crypto picks — expect a similar
   uplift on the non-crypto side.
3. **Tighten ETF DEFAULTS.** Current ETF default (2% / 1.5%) is a guess —
   re-derive once enough closed ETF picks accumulate.
