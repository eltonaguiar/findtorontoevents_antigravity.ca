# Swarm consult: Edge #11 BTC 4h regime gate — implementation spec

## Context

From CRYPTO swarm round 2026-05-13 synthesis:
> BTC 4h regime defined as: RED when BTCUSDT.4h.close < BTCUSDT.4h.SMA(10); GREEN otherwise.
> Application: 7 LONG-only emitters reject LONG signals when BTC 4h RED. All emitters: allow SHORT signals regardless of regime.

## Existing repo state

- `pick['btc_regime']` field is already populated per `alpha_engine/conviction_stack.py:638` (values: BULL/BEAR/BEARISH/UP/DOWN/NEUTRAL etc.)
- `fetch_btc_4h_regime()` lives in 4 modules; uses +1%/-1% threshold (NOT close-vs-SMA10)
- `elite_scorer.py:2357-2367` already PENALIZES alpha_engine + ml_crypto_pred LONGs in BEAR regime (-8 to -14 score adj) but NOT a hard reject
- NS-D (just merged): hard-rejects ml_crypto_pred LONG regardless of regime
- No explicit "7 LONG-only sources" constant in repo

## Three implementation candidates

**Option A — Universal CRYPTO LONG-in-BEAR reject**
```python
# NS-F: reject ANY CRYPTO LONG when BTC regime is bearish
if asset_class == "CRYPTO" and direction == "LONG":
    btc_reg = (pick.get("btc_regime") or "").upper()
    if "BEAR" in btc_reg or "DOWN" in btc_reg:
        return False
```
- Simplest, no source-list dependency
- Most aggressive — rejects all CRYPTO LONGs in BEAR (including potentially-good non-LONG-only sources)

**Option B — Restrict to known LONG-only sources**
Requires hardcoding a list of 7 sources (memory references but no list in repo). Risk: list becomes stale; future LONG-only sources added by other agents bypass.

**Option C — Per-source LONG_WR_THRESHOLD gate**
Compute each source's LONG WR from `dashboard_data.json::systems[].strategies[].long_wr` and auto-reject LONG when source's historical LONG WR < 30% AND BTC regime bearish.
- Adaptive, no hardcoded list
- Requires reading dashboard payload at exec time OR caching the threshold list
- More moving parts

## Question to engines

Which option is the right shipping pattern? Return strict JSON ONLY:

```json
{
  "recommended_option": "A | B | C | OTHER",
  "rationale": "<1-2 sentences>",
  "expected_pf_lift": <0-0.3 range>,
  "false_positive_risk": "<low | medium | high>",
  "concerns_about_option_A_universal": ["<concrete>"],
  "should_check_btc_regime_freshness_first": "yes | no",
  "merge_safety": "safe | risky | needs_shadow_first"
}
```

## Constraints

- Reversibility critical
- Must NOT touch SHORT signals (preserve working side per AA-1 + swarm)
- Default-ON preferred unless engines flag risk
- pick['btc_regime'] is populated upstream — no fresh fetch needed in the gate itself
