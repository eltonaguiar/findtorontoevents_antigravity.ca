# Forward n→100 tracker

**Generated:** 2026-06-05T05:04:23.569727+00:00
**Target:** n=100 | n>=100, WR>=55%, PF>=1.4 (evaluate_forward_tier2)

| Sleeve | n | remaining | WR% | PF | tier2 pass |
|--------|---|-----------|-----|-----|------------|
| luxalgo_confluence_pilot | 827 | 0 | 42.08 | 0.9685 | no |
| macd_rsi_m048 | 65 | 35 | 75.38461538461539 | None | no |
| inverse_ml_render_1h | 54 | 46 | 42.59 | 0.9507 | no |
| bootstrap_inverse_ml_btc | 52 | 48 | 55.769999999999996 | 1.0853 | no |
| inverse_ml_btc_15m | 52 | 48 | 55.769999999999996 | 1.0853 | no |
| inverse_ml_render_4h | 52 | 48 | 50.0 | 0.1214 | no |
| b_flip_price_roc | 39 | 61 | 53.849999999999994 | 1.0773 | no |
| bootstrap_b_flip | 39 | 61 | 53.849999999999994 | 1.0773 | no |
| inverse_ml_ada_15m | 36 | 64 | 55.559999999999995 | 1.7302 | no |
| inverse_ml_ada_15m_db | 2 | 98 | 50.0 | 2.9115 | no |
| crypto_wf_hyro | 0 | 100 | 0.0 | 0.0 | no |
| etf_dual_momentum | 0 | 100 | 0.0 | 0.0 | no |
| faber_taa | 0 | 100 | None | None | no |
| inverse_ml_ada_15m_virtual | 0 | 100 | 0 | 0.0 | no |

**Closest:** `luxalgo_confluence_pilot` at n=827 (0 to go)

luxalgo n=827 is deduped DB history, not isolated forward pilot clock — use promotion_status SHADOW until day_count>=30 and rolling metrics pass. ADA DB n may lag bootstrap (36) if strategy rows pre-filter; trust bootstrap + virtual log.
