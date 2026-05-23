# Swarm review: NS-F BTC bear-regime LONG-reject diff (Edge #11)

## Context

Prior swarm consult (4 engines): 3/4 voted Option A (universal CRYPTO LONG in BEAR reject). Cerebras dissented (Option B with hardcoded source list). Expected PF lift mean ~0.14.

## Diff (audit_trail/quality_gates.py, inserted after NS-D, before NS-E)

```python
if str(asset_class).upper() == "CRYPTO" and _truthy(
    os.environ.get("BTC_BEAR_LONG_REJECT"), "1"
):
    _dir_f = str(
        pick.get("direction") or pick.get("signal_type") or ""
    ).strip().upper()
    if _dir_f in ("LONG", "BUY"):
        _btc_reg_f = str(
            pick.get("btc_regime") or pick.get("regime_at_entry") or ""
        ).strip().upper()
        _is_bear = (
            "BEAR" in _btc_reg_f
            or "DOWN" in _btc_reg_f
            or _btc_reg_f == "BEARISH"
            or pick.get("btc_below_200ma") is True
        )
        if _is_bear:
            pick["_hf_quality_gate_reason"] = "ns_f_btc_bear_long_reject"
            return False
```

10 unit tests in `tests/test_ns_f_btc_bear_long_reject.py`. **37/37 tests pass** (10 new + 27 regression NS-C/D/E + FX1).

## Properties

- CRYPTO-only (EQUITY/FOREX/etc. unaffected)
- LONG/BUY direction (SHORT/SELL preserved)
- BEAR/DOWN/BEARISH variants caught + `btc_below_200ma` boolean fallback
- Whitespace-tolerant (`.strip()`)
- Env-gated `BTC_BEAR_LONG_REJECT` default ON
- Reads `pick['btc_regime']` already populated upstream (no fresh fetch)
- Audit reason: `ns_f_btc_bear_long_reject`
- Placed after NS-D (CRYPTO LONG), before NS-E (FOREX)

## Question to engines

Final approval. Return strict JSON ONLY:

```json
{
  "verdict": "APPROVE | APPROVE_WITH_CAVEATS | REQUEST_CHANGES | REJECT",
  "merge_decision": "MERGE | HOLD | REJECT",
  "code_quality_score": <1-10>,
  "concerns": ["<list>"],
  "missing_edge_cases": ["<list>"],
  "stacking_concern_with_existing_gates": "<low|medium|high — does this double-reject things NS-D already catches?>"
}
```

## Constraints

- NS-D already catches `ml_crypto_pred` LONG (regardless of regime). NS-F adds bear-regime universal reject. Overlap acceptable — NS-D fires first since placed earlier.
- Existing `elite_scorer.py` ALREADY penalizes BEAR LONGs with score adj. This adds hard reject layer.
- pick['btc_regime'] freshness: assumed populated at pick-generation by conviction_stack. If stale, hot picks may not see updated regime — minor concern.
