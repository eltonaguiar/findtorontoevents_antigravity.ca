# CRYPTO alpha_engine bleed 2026-06-04

## Pattern (at_signal_outcomes, asset_class=crypto, decisive only)

| Window | n | WR | w/l ratio |
|---|---:|---:|---:|
| 30d+ baseline | 100,793 | 37.4% | 0.60 |
| 30d total | 9,313 | 25.5% | 0.34 |
| 14d total | 3,399 | 18.6% | 0.23 |
| 7d total | 6,848 | 37.2% | 0.59 |
| **48h** | **92** | **41.3%** | **0.70** |

## Source attribution

7-30d bleed window:
- `alpha_engine`: **12,617 picks @ 23.5% WR** — the entire drag
- `mercury2`: 95 picks @ 41.1% WR (small-n, neutral)

48h recovery (alpha_engine only):
- 92 picks @ 41.3% WR — sample-size limited but trend reversed

## Interpretation

alpha_engine had ~3 weeks of CRYPTO 23.5% WR (May 5 - May 21 roughly), which dragged the rolling /audit money-ready verdict to CRYPTO NOT_READY (38.2% WR / PF 0.97). The last 48h shows a recovery but on too-small n (92) to be statistically confident.

The bleed coincides with crypto market regime change in May — possible that alpha_engine signals are momentum-following and got chopped in a sideways/down regime, then signals improved as the regime stabilized.

## Action

- Do NOT size up CRYPTO based on the 41.3% 48h figure (n too small).
- Monitor 7d window: if it stays >40% over the next week, may indicate genuine regime adaptation.
- If 7d drops back below 35%, suggests bleed wasn't regime-driven and alpha_engine CRYPTO logic needs review.

Generated 2026-06-04 by claude during /loop session.
