# Expert Feedback Action Plan — Ernie + Xiao Mi Mimo Synthesis
**Date:** 2026-05-17
**Source experts:** Ernie (COMMODITY/CRYPTO structural analysis), Xiao Mi Mimo (per-asset aggregate stats)
**Goal:** Translate dual expert analysis into ranked, executable action items for the audit pipeline

---

## Performance Snapshot (Expert-Verified, Post-Noise-Filter)

| Asset Class | WR | PF | n | Tier | Verdict |
|-------------|----|----|---|------|---------|
| COMMODITY | 85.5% | 7.71 | 228 | T1 | Crown jewel — broadly distributed edge |
| ETF | 66.7% | 2.25 | 75 | T1 candidate | Stronger than dashboard claims; n→100 |
| EQUITY | ~52.7% | 1.41 | 421 | T2 candidate | Gate calibration ongoing |
| CRYPTO (aggregate) | 47.2% | 1.33 | 7,766 | Sub-T2 | Volume drag from low-quality picks |
| CRYPTO (top ML) | ~75-80% est. | 3.14+ | ~250-300 | T1 | Only INJ, FET, DYDX, RENDER w/ conf 0.85-0.90 |
| BOND | ~55.6% | 0.66 | 11 | Thin | n<charter floor (18); do not size up |
| FOREX | 46.4% | <1.0 | 1,169 | Sub-floor | DSR=0; confirmed do not trade |
| FUTURES | N/A | N/A | 2 | Dead | Ignore |

---

## Expert Findings Summary

### Ernie's Key Findings

1. **COMMODITY is already T1** (PF 7.71 aggregate) with broadly distributed edge — not concentrated in a single source system. This is the most trustworthy asset class in the portfolio.

2. **CRYPTO edge is real but narrow:** top ML tokens are INJ, FET, DYDX, RENDER with confidence range 0.85-0.90 and `ml_score >= 0.65`. These ~250-300 picks represent genuine T1 edge.

3. **CRYPTO confidence > 0.90 is an overfit cliff:** 14.4% WR at confidence > 0.90 — a dramatic inversion. This must be hard-gated. The model is memorizing training noise at extreme confidence.

4. **Direction encoding bug:** `direction="BUY"` for CRYPTO has PF 0.38 vs `direction="LONG"` at PF 3.14. This is a data integrity issue — "BUY" picks are encoding something structurally different (likely legacy signals or mis-mapped source system output). Enforcing LONG-only removes a 0.38 PF drag.

5. **ETF may be underrated:** Dashboard shows PF 2.25 which exceeds the T1 minimum; document claims T3 — discrepancy suggests the document used pre-noise-filter data.

6. **5 CRYPTO feature gaps:** OI momentum, Garman-Klass volatility, OBI/OFI order flow, NUPL regime filter, exchange spread divergence. (See `reports/crypto_prediction_system_review_2026-05-17.md` for implementation details.)

### Xiao Mi Mimo's Key Findings

1. **CRYPTO aggregate (7,766 picks):** 47.2% WR, PF 1.33 — system-wide sub-T2. The volume is dominated by lower-quality picks diluting the elite signals.

2. **Only ~250-300 CRYPTO picks are truly T1** — the rest are noise. Reducing volume from 7,766 to ~300 is the single highest-leverage action for CRYPTO.

3. **COMMODITY (228 picks):** 85.5% WR, PF 7.71 — confirmed crown jewel. Edge is broadly distributed, not source-concentrated.

4. **ETF (n=75):** 66.7% WR, PF 2.25 — stronger than document claims. Push n to 100 with hard gates to establish charter-floor track record.

5. **FOREX confirmed PF < 1.0, DSR=0** — do not trade. Apply MUTATION_THREE_AXIS_PROTOCOL before any kill decision; deep-dive doc required.

6. **BOND thin (n=11, PF 0.66)** — below charter floor (n=18). Do not size up until n >= 100 with clean WR > 55%.

---

## Ranked Action Items by ROI

| Priority | Action | File | Effort | Expected Impact |
|----------|--------|------|--------|-----------------|
| P0 | Hard-cap CRYPTO confidence at 0.90 in quality_gates.py | audit_trail/quality_gates.py | XS (30min) | Removes 14.4% WR overfit cliff |
| P0 | Block CRYPTO direction="BUY", enforce LONG only | audit_trail/quality_gates.py | XS (30min) | PF 0.38 → 3.14 for affected picks |
| P0 | Enforce ml_score >= 0.65 as hard gate for CRYPTO | alpha_engine/config.py | XS (30min) | Removes bottom 30% (32.5% WR tier) |
| P1 | NUPL regime filter — block CRYPTO LONG when NUPL > 0.75 | alpha_engine/feed_hygiene.py or quality_gates.py | S (4h) | Avoids euphoria tops |
| P1 | ETF hard gates: trusted=true AND score>=60 | audit_trail/quality_gates.py | XS (30min) | PF 2.25 → target 2.5+ |
| P1 | Reduce CRYPTO signal volume (raise vote threshold for CRYPTO) | alpha_engine/config.py | S (2h) | 7,766 → target ~300 high-confidence picks |
| P2 | Garman-Klass volatility feature for CRYPTO/COMMODITY ML | crypto_ml_edge/features/engine.py | M (1 day) | Better vol estimate → sharper signals |
| P2 | OBI/OFI order flow signal | crypto_signal_engine/ (new file) | M (1 day) | Institutional-grade order flow gate |
| P2 | COMMODITY: add OI momentum feature | coinglass_strategies/data_fetcher.py | M (1 day) | Push WR 89.8% → 93%+ |
| P2 | Exchange spread divergence filter | coinglass_strategies/data_fetcher.py | M (1 day) | Filter false CRYPTO breakouts |
| P3 | NUPL module (full implementation) | crypto_ml_edge/features/nupl.py | M (1 day) | Regime-aware CRYPTO sizing |

---

## P0 Implementation Details

### P0-A: Hard-cap CRYPTO confidence at 0.90

Add to `audit_trail/quality_gates.py` in the CRYPTO gate block:

```python
# Ernie finding: confidence > 0.90 = overfit cliff (14.4% WR)
if pick.get("asset_class") == "CRYPTO" and pick.get("confidence", 0) > 0.90:
    return {"passed": False, "reason": "CRYPTO_CONFIDENCE_OVERFIT: conf > 0.90 hard-blocked (14.4% WR)"}
```

### P0-B: Block CRYPTO direction="BUY", enforce LONG only

Add to `audit_trail/quality_gates.py`:

```python
# Ernie finding: direction="BUY" for CRYPTO has PF 0.38 vs LONG PF 3.14
if pick.get("asset_class") == "CRYPTO" and pick.get("direction") == "BUY":
    return {"passed": False, "reason": "CRYPTO_DIRECTION_BUY_BLOCKED: use LONG only (PF 0.38 vs 3.14)"}
```

### P0-C: ml_score >= 0.65 hard gate for CRYPTO

Add to `alpha_engine/config.py` or directly in `quality_gates.py`:

```python
CRYPTO_ML_SCORE_MIN = 0.65  # Below this: 32.5% WR (Ernie analysis)
```

Then in `quality_gates.py`:
```python
if pick.get("asset_class") == "CRYPTO":
    ml_score = pick.get("ml_score", 0)
    if ml_score < CRYPTO_ML_SCORE_MIN:
        return {"passed": False, "reason": f"CRYPTO_ML_SCORE: {ml_score:.3f} < {CRYPTO_ML_SCORE_MIN} floor"}
```

---

## P1 Implementation Details

### P1-A: NUPL Regime Filter

Gate structure (env-var-gated, fail-open, matching approved pattern):

```python
if os.environ.get("ENABLE_ONCHAIN_REGIME", "0") == "1":
    try:
        nupl = _get_latest_nupl("BTC")
        if nupl is not None and nupl > 0.75 and pick.get("direction") == "LONG":
            return {"passed": False, "reason": f"NUPL_REGIME: {nupl:.3f} > 0.75 euphoria — LONGs blocked"}
    except Exception:
        pass  # fail-open
```

### P1-B: ETF Hard Gates

```python
if pick.get("asset_class") == "ETF":
    if not pick.get("trusted", False):
        return {"passed": False, "reason": "ETF_TRUST: trusted=false — gate blocks"}
    if pick.get("score", 0) < 60:
        return {"passed": False, "reason": f"ETF_SCORE: {pick.get('score')} < 60 floor"}
```

### P1-C: Reduce CRYPTO Signal Volume

In `alpha_engine/config.py`, raise the vote threshold specifically for CRYPTO:

```python
ASSET_CLASS_VOTE_THRESHOLDS = {
    "CRYPTO": 4,     # raised from 2 → targets ~300 high-confidence picks from 7,766
    "EQUITY": 2,
    "COMMODITY": 2,
    "ETF": 2,
}
```

---

## Asset Class Priority Order (for capital sizing)

Based on combined expert analysis, capital should be prioritized:

1. **COMMODITY** — T1 confirmed, broadly distributed, crown jewel. Size up to charter max.
2. **ETF** — T1 candidate at PF 2.25 / WR 66.7%. Push n to 100, then size up.
3. **EQUITY** — T2 candidate. Gate calibration ongoing. Size at T2 level until T1 confirmed.
4. **CRYPTO (post-P0 gates)** — Target ~300 picks from 7,766. Only after P0 gates verified in shadow mode.
5. **BOND** — Do not size up. n=11, below charter floor.
6. **FOREX** — Do not trade. Apply MUTATION_THREE_AXIS_PROTOCOL. Deep-dive doc required before any kill decision.
7. **FUTURES** — Dead (n=2). Ignore.

---

## Shadow Mode Protocol for P0 Gates

Before activating P0 gates in production:

1. Run P0 gates in shadow mode for 14 days: log `would_block=True` without actually blocking
2. Measure: what % of current picks would be blocked? What is the WR/PF of blocked vs. passed picks?
3. Acceptance criteria: blocked picks must show WR < 45% AND PF < 1.0; passed picks must show WR > 55% AND PF > 2.0
4. If criteria met: activate in production
5. Monitor for 30 days post-activation; report in `reports/p0_gate_shadow_results_*.md`

---

## References

- `reports/crypto_prediction_system_review_2026-05-17.md` — feature gap implementation details
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md` — FOREX mutation protocol
- `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` — required before any source kill
- `audit_dashboard/data/dashboard_data.json::performance.asset_class_health` — live performance numbers
- `reports/hedge_fund_performance_review_*.md` — tier definitions (T1: PF>2/WR>55/MDD<10; T2: PF>1.5/WR>50/MDD<20)
