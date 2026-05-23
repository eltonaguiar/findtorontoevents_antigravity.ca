# Edge Analysis & Filter Derivation — 2026-05-16

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
  - Rationale: PF=3.15 > 1.3, WR=64.3% > 0.5, n=305 ≥ 30.
  - Walk-forward: IS PF=1.61, OOS PF=3.79.
  - ✅ Max DD 1.5% within 20.0% threshold.
- **EQUITY**: Deploy filter with direction=LONG, elite_score≥45.
  - Rationale: PF=2.77 > 1.3, WR=60.8% > 0.5, n=125 ≥ 30.
  - Walk-forward: IS PF=4.45, OOS PF=1.84.
  - ✅ Max DD 1.8% within 20.0% threshold.
- **COMMODITY**: Deploy filter with direction=SHORT.
  - Rationale: PF=2.10 > 1.3, WR=58.1% > 0.5, n=62 ≥ 30.
  - Walk-forward: IS PF=3.78, OOS PF=1.71.
  - ✅ Max DD 4.4% within 20.0% threshold.
- **FOREX**: Blocked — thin sample. `forex-rsi-ema-scout` shows promise (PF=1.68, WR=54.5%, n=22) but n<30 and dashboard sizing is disabled.
  - Walk-forward: IS PF=2.81, OOS PF=0.65.
  - 📝 Re-evaluate when n≥30.
- **ETF**: Deploy filter with .
  - Rationale: PF=1.32 > 1.3, WR=57.1% > 0.5, n=105 ≥ 30.
  - Walk-forward: IS PF=1.09, OOS PF=1.90.
  - ✅ Max DD 1.6% within 20.0% threshold.
