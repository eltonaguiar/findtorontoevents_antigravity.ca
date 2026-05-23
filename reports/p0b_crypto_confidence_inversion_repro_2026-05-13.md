# P0-B CRYPTO Confidence-Inversion Reproduction

**Date:** 2026-05-13
**Asset class:** CRYPTO
**Source claim:** confidence_top_band WR is 24.9pp BELOW confidence_bottom_band WR

## Verdict: DIRECTIONALLY-REAL, MAGNITUDE-OVERSTATED

| Band | Confidence range | WR | n |
|------|------------------|----|----|
| Bottom | 0.00 – 0.25 | **53.7%** | (sufficient) |
| Top | 0.85 – 1.00 | **34.5%** | **58 (thin)** |

**Measured inversion:** 19.2pp (53.7 − 34.5), not the claimed 24.9pp.

## Implications

1. The inversion is directionally real — high-confidence CRYPTO picks really do under-perform low-confidence picks. This is the wrong sign for a calibrated scoring system and indicates a regression target (either the scorer is anti-predictive at the top, or top-band picks are getting filled in adverse regimes).
2. Top-band sample size (n=58) is too thin to claim a 24.9pp gap with confidence. Bootstrap 95% CI around 34.5% with n=58 is ~±12pp — the magnitude reported in the source was outside the supportable error bar.
3. **Action — do NOT close the gate PR** (originally proposed by sub-agent). The directional finding alone is sufficient evidence to add a confidence-band quality gate guard for CRYPTO; magnitude will refine as n grows.

## Recommended next steps

- Add a CRYPTO-specific gate in `alpha_engine/quality_gates.py`: penalize or block picks where `confidence > 0.85` until top-band sample reaches n≥150 AND realized WR ≥ 50%.
- Track the band breakdown in `audit_dashboard/data/dashboard_data.json::performance.asset_class_health[crypto].confidence_bands` so the inversion is monitored on /audit.
- Re-evaluate at n_top ≥ 150 to confirm/refute the magnitude claim.

## Provenance

- Sub-agent reproduction completed 2026-05-13 ~22:30Z
- Underlying data: closed CRYPTO picks in `audit_dashboard/data/dashboard_data.json::picks.recent_closed` + historical archive
- Cross-referenced against `reports/CONFIDENCE_SLICE_DIAGNOSIS_2026_04_22.md` (prior diagnosis, pre-resolver-v2)
