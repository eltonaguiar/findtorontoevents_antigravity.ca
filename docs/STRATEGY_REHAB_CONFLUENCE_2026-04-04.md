# Strategy rehab — confluence variants (mutate before kill)

**Policy:** The five forward-degraded parents are **not permanently killed**. We reduce ranking pressure when picks show **real confluence**, register **child strategy names** for filtered emits, and run subset analysis from closed data.

## Parent strategies (degradation watchdog)

| Strategy | Notes |
|----------|--------|
| `claude_gainer_1h` | Large realized drawdown — narrow with RSI / MTF |
| `enhanced_ml_A_xgboost` | Symbol-quality spread — align with `quality_gates` per-symbol caps |
| `st_fear_greed_contrarian` | Existing pattern: `st_fear_greed_contrarian_regime_filtered` in `smart_picks_engine.py` |
| `quality-minus-junk` | Small *n* — require second factor (value + momentum) before live |
| `crypto_bayesian_regime_transition_momentum_v1` | Tighten regime gate + confirmation bar |

## Code behavior

1. **`audit_trail/forward_degradation_tracker.py`**
   - **`REHAB_CONFLUENCE_PARENT_STRATEGIES`:** parents listed above still get severity tags, but **penalties are softened** when the active pick has:
     - `technical_buy_tfs` / `technical_sell_tfs` ≥ 2 (direction-aware), stronger relief at ≥ 3
     - `elite_score` ≥ 55 (mild) / ≥ 62 (stronger)
     - `agreement_count` ≥ 2  
     Minimum **15%** of the original penalty is always kept (not a free pass).

2. **Rehab child names** — strategies whose name is `parent_*` and suffix contains  
   `rehab`, `confluence`, `rsi2`, `mtf`, `regime`, `filter` (see `_is_rehab_variant_strategy`) **skip parent degradation penalty** entirely (until the child accumulates its own forward stats).

3. **`audit_trail/quality_gates.py`** — small **`+8`** sandbox lift for variant id strings containing `_rehab_`, `_confluence`, `_rsi2`, `regime_filtered`, `_mtf`.

## Variation ideas (implement in signal generators)

| Child name pattern | Confluence rule |
|--------------------|-----------------|
| `*_rsi2_confluence` | Connors-style: RSI(2) extreme **with** trend filter (e.g. price vs 200SMA or regime tag) |
| `*_mtf2_confluence` | Require ≥ 2 agreeing timeframes (`technical_buy_tfs` / `sell_tfs` populated by TA pass) |
| `*_regime_filtered` | Only emit in non-chop regime (reuse battleground / gainer regime enums) |
| Symbol whitelist | Use `compute_rehabilitation_hints` **winning_combos** from closed history |

## Backtest / report (no invented trades)

```bash
python tools/rehab_kill_candidate_report.py
python tools/rehab_kill_candidate_report.py --payload audit_dashboard/data/dashboard_data.json
```

Uses **`compute_rehabilitation_hints`** on real `recent_closed` rows: symbol/direction/asset-class winners and inverse candidates.

## Related

- `audit_trail/forward_degradation_tracker.py` — `compute_rehabilitation_hints`, `flag_degraded_picks`
- `tmp_rehab_analysis.py` — ad-hoc subset tables (legacy)
- `alpha_engine/forward_validator.py` / tournament flows — full OHLC backtests for new child strategies
