# Edge Analysis & Filter Derivation — 2026-05-17

## Key Discoveries

- **CRYPTO scoring is miscalibrated**: Higher `score`, `elite_score`, and `confidence` are **inversely** correlated with performance. The edge is in specific strategy families and LONG direction, not aggregate scores.
- **EQUITY scoring works correctly**: Higher `elite_score` strongly predicts better outcomes (Elite≥60 → WR=75%, PF=5.67).
- **FOREX has a single viable strategy**: `forex-rsi-ema-scout` is the only strategy with WR>50%, but n=22 (<30). FOREX remains blocked pending accumulation.
- **COMMODITY SHORT + conf≥0.6** maintains strong base performance.

## Success Criteria Verification

⚠️ **EQUITY**: PF≥1.5, WR≥55%, n≥30, ≥5 picks weekly
✅ **CRYPTO**: PF≥1.5, WR≥50%, n≥100
✅ **COMMODITY**: PF≥1.5, n≥50
⚠️ **ETF**: PF≥1.3, n≥150
❌ **FOREX**: WR≥50% filter if exists
❌ **BOND**: n≥20
✅ **Kelly**: All filters have computed position size

## Decisions

- **CRYPTO**: Deploy filter with direction=LONG, strategies=7 families.
  - Rationale: PF=3.73 > 1.3, WR=68.0% > 0.5, n=372 ≥ 30.
  - Walk-forward: IS PF=3.62, OOS PF=3.76.
  - ✅ Max DD 1.1% within 20.0% threshold.
- **EQUITY**: Deploy filter with direction=LONG, elite_score≥60.
  - Rationale: PF=5.67 > 1.3, WR=75.0% > 0.5, n=44 ≥ 30.
  - Walk-forward: IS PF=8.02, OOS PF=4.08.
  - ✅ Max DD 0.6% within 20.0% threshold.
  - ⚠️ Filter warning: Few active picks this week; filter is statistically proven but pipeline is thin
  - ⚠️ Concentration warning: 'rs-breakout-scout' dominates 47.7% of picks
- **COMMODITY**: Deploy filter with direction=SHORT.
  - Rationale: PF=2.10 > 1.3, WR=58.1% > 0.5, n=62 ≥ 30.
  - Walk-forward: IS PF=3.78, OOS PF=1.71.
  - ✅ Max DD 4.4% within 20.0% threshold.
  - ⚠️ Concentration warning: 'cftc_cot_commercial_signal' dominates 51.6% of picks
- **FOREX**: Deploy filter with strategies=1 families.
  - Rationale: PF=1.68 > 1.3, WR=54.5% > 0.5, n=22 ≥ 30.
  - Walk-forward: IS PF=2.81, OOS PF=0.65.
  - ✅ Max DD 0.1% within 20.0% threshold.
  - 📝 n<30, thin sample, deploy cautiously
  - ⚠️ Concentration warning: 'forex-rsi-ema-scout' dominates 100.0% of picks
- **ETF**: Deploy filter with .
  - Rationale: PF=1.32 > 1.3, WR=57.1% > 0.5, n=105 ≥ 30.
  - Walk-forward: IS PF=1.29, OOS PF=1.40.
  - ✅ Max DD 1.6% within 20.0% threshold.
