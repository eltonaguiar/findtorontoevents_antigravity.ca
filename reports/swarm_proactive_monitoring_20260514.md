# Swarm Round C: Proactive Monitoring Design — 2026-05-14

**Engines:** cerebras (gpt-oss-120b), deepseek (deepseek-v4-flash), xai (grok-3) | **All 3/3 OK**
**Run dir:** `swarm_runs/proactive_monitoring_20260514/`
**Briefing:** `swarm_runs/briefing_proactive_monitoring_20260514.md`

---

## Monitoring Checks (by frequency)

### Hourly

| check_name | data_source | alert_threshold | auto_action |
|---|---|---|---|
| open_bloat_ratio | cot_positioning: count OPEN vs CLOSED picks per class | OPEN ratio > 90% | Freeze new pick emission for affected class |
| data_timestamp_lag_check | COT data feed: compare data timestamp vs system clock | lag > 72h for COMMODITY | Pause all COMMODITY cot_positioning picks, flag data source |
| regime_tagging_integrity | pick_emission.log: regime_id field on last N emissions | missing_regime_rate > 0% (zero tolerance) | Halt all pick emission for the class with missing tags |

### Daily

| check_name | data_source | alert_threshold | auto_action |
|---|---|---|---|
| concept_drift_ks | prediction_store: last 24h vs reference distribution (last 30d) | KS_D > 0.15 (alert) / KS_D > 0.25 (auto-pause) | Set all strategy sizing to 0 for affected asset class |
| concept_drift_psi | prediction_store: 10-quantile bins last 24h vs reference 30d | PSI > 0.15 (alert) / PSI > 0.30 (auto-pause) | Pause forward-sizing for class with highest PSI |
| open_bloat_daily | cot_positioning: OPEN vs CLOSED ratio, rolling 7d trend | OPEN ratio > 80% sustained >7 days | Flag all OPEN picks as unvalidated, exclude from WR calc |
| source_score_freshness | goldmine_stocks.score_table vs live PF, WR, PnL | abs(score_reported_WR − live_WR) > 5pp (alert) / >10pp (pause) | Suspend scoring-based sizing for goldmine_stocks |
| cot_lag_compliance | COT ingestion timestamp vs CFTC release schedule (3-day lag) | Any record timestamp newer than allowed lag | Drop offending rows; pause COT-based sizing until compliant |
| regime_tagging_daily | active picks table: picks with regime_data IS NULL | >10% of active picks missing regime field | Block new pick emission until regime field is stamped |
| confidence_band_inversion | live picks performance grouped by confidence bucket (>0.85 vs <0.55) | high_conf_WR − low_conf_WR < −5pp (alert) / <−15pp (pause) | Suspend high-confidence pick emission for that asset class |
| confidence_calibration_error | actual WR per band vs predicted confidence per band | mean absolute error > 0.10 (alert) / >0.15 (pause) | Cap confidence scores to max of lower band |
| pipeline_health | scheduled check completion rate in last 24h | <99% of scheduled checks completed | PagerDuty alert; halt pick emission until pipeline confirmed |

### Weekly

| check_name | data_source | alert_threshold | auto_action |
|---|---|---|---|
| strategy_overfit_decay | strategy_perf.history: BT WR vs FWD WR per baby_strat, rolling 28d | WR decay >10pp or z-score >3.0 (alert) / decay >20pp or z-score >4.5 (pause) | Deactivate baby_strat, reduce sizing to 0 |
| source_score_audit | goldmine_stocks: score/comment vs actual live PF, WR, PnL | score > 5 but live PF < 0.5 or WR < 50% | Override score to 0, remove from active sources |
| canary_strategy_review | per-class canary WR, Sharpe, drawdown (rolling 20d) | Canary Sharpe < 0.0 for any class over 20 days | Reduce sizing on that class by 50% |

---

## Recommended Drift Tests

| test | detects | library | threshold |
|---|---|---|---|
| Kolmogorov-Smirnov (KS) | Distribution shift in model output probabilities; maximum CDF distance | `scipy.stats.ks_2samp` | KS_D < 0.10 stable; 0.10–0.20 moderate alert; >0.25 auto-pause |
| Population Stability Index (PSI) | Binned probability drift between reference and current windows | `evidently` / custom scipy | PSI < 0.10 stable; 0.10–0.20 moderate; >0.25 severe auto-pause |
| Wasserstein Distance (Earth Mover's) | Magnitude and geometry of shift in continuous prediction scores | `scipy.stats.wasserstein_distance` | WD > 0.5 × std(reference): alert; >1.0 × std: severe |
| Per-feature KS/PSI | Individual feature distribution changes upstream of predictions | `alibi-detect` / `evidently` | Any feature KS_D > 0.25 or PSI > 0.20 triggers alert |
| Label Drift (Chi-Square) | Change in target class frequencies; ground truth distribution shift | `scipy.stats.chi2_contingency` | p-value < 0.01 signals drift |
| Prediction Drift (EMD on binned scores) | Overall shift in prediction score distribution | `evidently` | EMD > 0.07 alert; >0.10 auto-pause |
| Cramer-von Mises | Tail-sensitive distributional test; catches edge distribution drift | `scipy.stats.cramervonmises_2samp` | p-value < 0.01 alert |

**Priority order for implementation:** PSI (lowest complexity, widest coverage) → KS (already partially in place) → per-feature KS/PSI → Wasserstein → Label Drift → CvM.

---

## Canary Strategy Design

**Concept:** Deploy ultra-lightweight, low-capital (1–2% of class allocation) strategies that trade on simple, interpretable signals isolated from production risk. Their sole purpose is to surface early degradation of edge, regime change, or data-pipeline anomalies. Each canary reports a fixed set of health metrics (WR, Sharpe, MDD, open-ratio) back to the monitoring layer on the same schedule as main strategies. A canary degrading 2σ from its own historical mean is a leading indicator to investigate before the main portfolio is affected.

**Key design rules:**
- Canary must use the same data feeds as production (so it catches feed issues too)
- Canary must be logically simpler than the production signal (so it degrades cleanly)
- Canary sizing must be small enough that losses don't affect the P&L report
- Canary results must feed the dashboard KPI "Canary Health Score"

| asset_class | canary_approach |
|---|---|
| COMMODITY | Momentum spread between front-month and next-month futures (20d vs 50d SMA cross). Monitor spread-WR and spread-KS. Degradation >2σ from historical spread performance triggers regime-shift alert. Alert if Sharpe < −0.5 or WR < 35% over 10 trades. |
| EQUITY | Sector-neutral long-short pair (top-ranked vs bottom-ranked stock in same industry) + 12m−1m momentum factor on S&P 500 constituents. Track pair-WR and pair-PSI. Alert if momentum premium spread < 0% (negative) or pair-WR decay >8pp/week. |
| CRYPTO | Volatility-scaled BTC-ETH ratio strategy with fixed 0.05% allocation + 20-day ATR breakout on BTC/USD. Watch confidence-band WR and daily Sharpe. Alert if WR < 40% or avg return < 0 over 20 trades, or confidence-band inversion >3pp. |
| ETF | Sector-ETF rotation based on macro-factor scores (value, quality) + carry canary (long-short highest vs lowest yield ETFs). Monitor open-ratio (>95% signals data-pipeline lag), cumulative PnL, Sharpe. Alert if drawdown >5% or Sharpe < 0 over 30 days. |
| BOND | Duration-tilt canary (long 2yr vs short 10yr Treasury) using the same yield-curve inputs as production. Observe duration-WR and label drift. Alert if accuracy < 45% on 10-day rolling window (below random). Label-drift p-value < 0.01 triggers early warning. |

---

## Dashboard Health KPIs (10 KPIs)

| KPI | formula | red_threshold | green_threshold |
|---|---|---|---|
| Live Win Rate (7d rolling) | COUNT(closed picks with PnL > 0, last 7d) / COUNT(all closed picks, last 7d) × 100 | < 40% | > 55% |
| Prediction Drift PSI (daily) | PSI(live_prediction_distribution vs training_prediction_distribution) | > 0.25 | < 0.10 |
| Concept Drift KS_D (daily max) | MAX(KS_D across all active strategies, last 24h) | > 0.25 | < 0.10 |
| Open Pick Ratio | COUNT(OPEN picks) / COUNT(all picks) × 100 | > 90% | < 60% |
| Strategy Decay Z-Score (max) | MAX(\|BT_WR − FWD_WR\| / std(BT_WR − FWD_WR, historical), across active strats) | > 4.0 | < 2.0 |
| Confidence Band Gap | high_conf_WR − low_conf_WR (rolling 7d, per class) | < −5pp | ≥ +2pp |
| Regime Tag Coverage | COUNT(picks with regime_data NOT NULL) / COUNT(all active picks) × 100 | < 99.5% | = 100% |
| Data Freshness (max lag) | MAX(system_time − data_timestamp, all active data sources) in hours | > 72h | < 24h |
| Source Score Accuracy | COUNT(sources where score matches live PF/WR within 20%) / COUNT(all sources) × 100 | < 70% | > 90% |
| Canary Health Score | Composite: avg(canary_WR, canary_Sharpe, inverse_drift_metric), scaled 0–100 | < 55 | > 75 |

---

## Circuit Breaker Logic

**Overall design:** Four-tier system. Tier 1 = alert only. Tier 2 = reduce sizing 50% on affected scope. Tier 3 = pause sizing on affected class. Tier 4 = global pause, manual-only resume. Auto-resume requires N consecutive clean checks at the recovery threshold. All state changes written to audit trail with timestamp + trigger condition.

| tier | condition | action | scope | auto_resume |
|---|---|---|---|---|
| T3 | KS_D > 0.25 on any asset class (daily check) | Pause sizing on that class | per-class | KS_D < 0.15 for 2 consecutive daily checks |
| T3 | PSI > 0.30 on any asset class (daily check) | Pause sizing on that class | per-class | PSI < 0.15 for 3 consecutive daily checks |
| T3 | OPEN ratio > 95% for 3 consecutive days | Pause all new pick emission | all-classes | Manual only (pipeline fix required) |
| T3 | Any COT record timestamp newer than allowed 3-day lag | Pause all picks dependent on that feed | per-class | Lag < 24h for 2 consecutive hourly checks |
| T3 | Missing regime rate > 0% on any emission (hourly) | Halt pick emission for affected class | per-class | Regime tagging restored and verified for 1h |
| T2 | Strategy decay z-score 3.0–4.4 on any baby_strat | Reduce sizing by 50% on that strategy | per-strategy | Z-score < 2.5 for 3 consecutive weekly checks |
| T3 | Strategy decay z-score ≥ 4.5 on any baby_strat | Deactivate baby_strat, sizing → 0 | per-strategy | Manual only |
| T2 | Confidence band inversion −5pp to −14pp for 2 consecutive days | Reduce sizing on high-conf picks by 75% | per-class | Inversion < −2pp for 5 consecutive days |
| T3 | Confidence band inversion ≥ −15pp | Pause high-confidence pick emission entirely | per-class | Gap > −2pp for 5 consecutive days |
| T2 | Source score audit finds >1 source with score-live PF mismatch >50% | Pause all picks from those sources | per-source | Manual only (re-audit required) |
| T2 | Canary Sharpe < −0.5 sustained 20 days | Reduce sizing on that class by 50% | per-class | Canary Sharpe > 0.3 for 10 consecutive days |
| T4 | System-wide live WR < 35% over 7 days | Global pause: all sizing across all classes | all-classes | Manual only |
| T4 | Pipeline health < 90% in last 24h | Global alert + pause until confirmed stable | all-classes | Pipeline health > 99% for 4 consecutive hours |

**Cooldown rule:** After any T3/T4 trigger, a 2-hour cooldown prevents rapid re-enable without a human sign-off OR confirmed auto-resume condition being met for N consecutive checks.

---

## Verdict: Gaps vs Industry Standard

Current state is fully reactive and manual — the 7 documented failure modes were all discovered retrospectively through one-off audits, not standing automated checks. Industry-standard production ML systems (institutional quant desks, Netflix/Google SRE playbooks) require: automated drift detection running daily (PSI + KS minimum), per-class canary strategies acting as leading indicators, multi-tier circuit breakers that auto-pause before losses compound, and a live dashboard showing system heartbeat KPIs at all times. The most critical gap is the complete absence of automated alerting on KS_D (currently at 6.6× the critical threshold with no alarm), combined with zero circuit breaker logic — any one of the 7 failure modes, if caught by the proposed hourly/daily checks, would have been contained within 24h instead of compounding for weeks. Closing these gaps (PSI/KS daily, open-ratio hourly, regime-tag integrity hourly, confidence-band inversion daily, canary strategies per class, tiered circuit breakers) is the minimum bar to reach institutional-grade operational robustness.

---

*Generated 2026-05-14 — sources: cerebras (gpt-oss-120b), deepseek (deepseek-v4-flash), xai (grok-3)*
*Run dir: `swarm_runs/proactive_monitoring_20260514/` | All 3/3 engines OK*
