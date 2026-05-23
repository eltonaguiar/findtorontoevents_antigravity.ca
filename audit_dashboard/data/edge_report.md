# Audit edge report (automated health pipeline)

**Dashboard snapshot:** `2026-04-20T14:14:32.888111+00:00`  
**Source:** `C:\findtorontoevents_antigravity.ca\audit_dashboard\data\dashboard_data.json`  

## Data health (summary)

- Asset class mismatches (active): **0**
- Asset class mismatches (closed): **7**
- Forward WR &gt; 0 but strat_fwd_trades = 0: **0**
- Symbol+strategy wide WR spread groups: **6**
- Verified-alpha refs resolved to active: **13** / **13**

## Closed-book performance (recent_closed)

Counterfactual high-conviction uses the same ordered filter as `hc_filter.js` (correlation-pair registry applied in time order). Status is not forced OPEN for HC (gates do not check status).

| Cohort | n | Win% | Mean pnl% | PF |
|--------|---|------|------------|-----|
| recent_closed_baseline | 3500 | 39.314 | -0.29226 | 0.7566 |
| high_conviction_counterfactual_ordered | 75 | 65.333 | 0.76455 | 3.4417 |
| guide_proven_confidence_0.8_0.9 | 0 |  |  |  |
| guide_proven_trust_tier_only | 793 | 26.734 | -0.43585 | 0.5388 |

- **Active picks passing HC gates now:** 1 / 31 (3.2%)

- **Guide confidence band 0.8–0.9 on PROVEN:** n=0 in this `recent_closed` window — the UI sometimes cites this band; if n=0, that slice cannot be empirically validated on current history.

## TRUE edge vs marketing

- **High-conviction filter** is a strict multi-gate rule set (score, trust, forward WR, per-asset floors, regime blocks, independent consensus, walk-forward). Empirical closed-book stats above show whether that slice historically outperformed the baseline.
- **Guide slice** (`PROVEN` + confidence 0.8–0.9) is documented in the UI; when n=0 on closes, use **PROVEN-only** row or HC counterfactual instead.
- **Confidence** is weakly correlated with pool-wide PnL in prior quant review—do not equate confidence with expectancy.

## Limitations

- Closed history does not include uniform fees/slippage; sum of pnl% is not portfolio equity.
- Lookahead / stale forward stats on old rows possible.
- Many historical closes may omit fields the UI now shows.

## Combo / confluence track

- See `cross_strategy_permutations` in dashboard JSON and `audit_dashboard/data/strategy_expansion_backtests.json` for research artifacts; production confluence lives under `alpha_engine/` (multi_signal_confluence, confluence_pipeline).
- **cross_strategy_permutations.summary (snapshot):** `{"total_tracked": 15, "highly_trusted": 1, "trusted": 0, "with_trades": 5}`
- Per-strategy stats from closes: `tools/data/audit_combo_strategy_stats.json` (top by closed count).

## Machine-readable outputs

- `audit_dashboard/data/health_report.json`
- `tools/data/score_pnl_analysis.json` (from analyze_audit_scores_vs_pnl)
