# ML Metrics & KPI Quick Reference

## Critical Metrics Summary

### Feature Health (Must Monitor)
| Metric | Formula | Green | Yellow | Red | Frequency |
|--------|---------|-------|--------|-----|-----------|
| Dead Features % | dead/39 × 100 | < 12% | 12-25% | > 25% | Daily |
| Feature Drift PSI | Σ(%Δ × ln ratio) | < 0.1 | 0.1-0.25 | > 0.25 | Daily |
| Coverage % | complete/total × 100 | > 99% | 95-99% | < 95% | Real-time |
| Max Correlation | max\|corr(fi,fj)\| | < 0.8 | 0.8-0.9 | > 0.9 | Daily |

### Model Performance (Must Validate)
| Metric | Formula | Green | Yellow | Red | Frequency |
|--------|---------|-------|--------|-----|-----------|
| Precision@20 | TP20/(TP20+FP20) | > 52% | 50-52% | < 50% | Daily |
| AUC-ROC | Area under ROC | > 0.58 | 0.53-0.58 | < 0.53 | Daily |
| ECE | Σ\|acc-conf\|×n/N | < 0.05 | 0.05-0.10 | > 0.10 | Daily |
| Log Loss | -Σ(y·log(p)) | < 0.65 | 0.65-0.69 | > 0.69 | Hourly |

### Trading Performance (Must Achieve)
| Metric | Formula | Green | Yellow | Red | Frequency |
|--------|---------|-------|--------|-----|-----------|
| Expectancy/Trade | win%×avgWin - loss%×avgLoss | > 0.3% | 0.1-0.3% | < 0.1% | Daily |
| Win Rate | wins/total × 100 | > 52% | 48-52% | < 48% | Daily |
| SL Hit Rate | SL hits/total × 100 | < 35% | 35-45% | > 45% | Daily |
| Adverse Entry bps | (entry-worst)/entry×10k | < baseline-2 | ±2 | > baseline+2 | Per entry |
| Profit Factor | grossWin/\|grossLoss\| | > 1.3 | 1.1-1.3 | < 1.1 | Daily |

### Risk Metrics (Must Control)
| Metric | Formula | Green | Yellow | Red | Frequency |
|--------|---------|-------|--------|-----|-----------|
| Max Intraday DD | (peak-trough)/peak × 100 | < baseline | baseline+1% | > baseline+1% | Real-time |
| Daily VaR 95 | percentile(PnL, 5) | > -2% | -2 to -3% | < -3% | Daily |
| Regime Concentration | Σ(pnl_share²) | < 0.25 | 0.25-0.35 | > 0.35 | Weekly |
| Consecutive Losses | max streak | < 8 | 8-12 | > 12 | Daily |

### Operational Metrics (Must Maintain)
| Metric | Formula | Green | Yellow | Red | Frequency |
|--------|---------|-------|--------|-----|-----------|
| Latency P99 | percentile(latency, 99) | < 150ms | 150-300ms | > 300ms | Hourly |
| SL Calibrator Coverage | calibrated/total × 100 | > 80% | 50-80% | < 50% | Daily |
| System Uptime | up minutes/total × 100 | > 99.9% | 99-99.9% | < 99% | Real-time |
| Error Rate | errors/total × 100 | < 0.1% | 0.1-1% | > 1% | Hourly |

---

## Health Gate Pass/Fail Criteria

### Gate 1: Feature Health (Pre-Merge)
```
PASS if:
  - Dead features <= 5 (12.8%)
  - Constant features = 0
  - Coverage >= 99%
  - Drift PSI < 0.1
  - Max correlation < 0.9
  - Null rate < 1% per feature
```

### Gate 2: Model Quality (Shadow Mode)
```
PASS if:
  - Precision@20 >= 52%
  - AUC-ROC >= 0.55
  - ECE < 0.10
  - Log loss < 0.68
  - Regime precision >= 50% all regimes
  - Regime concentration < 0.35
```

### Gate 3: Trading Live (Gradual Rollout)
```
PASS if:
  - Adverse entry <= baseline - 1 bps
  - SL hit rate <= 40%
  - Expectancy >= 0.15% per trade
  - Expectancy drop < 0.20%
  - Win rate >= 50%
  - Max intraday DD <= baseline
  - Daily VaR 95 > -2.5%
  - Latency P99 < 150ms
```

---

## Progressive Threshold Tightening

| Phase | Dead Feature Threshold | Trigger Condition |
|-------|----------------------|-------------------|
| Initial | <= 20 (51%) | Start of integration |
| After 3 stable retrains | <= 14 (36%) | 3 consecutive weeks stable |
| After backfill + coverage | <= 8 (20%) | Coverage >= 95% for 2 weeks |
| Final (pre-production) | <= 5 (13%) | Ready for full deployment |

---

## Alert Escalation

| Severity | Response | Channels | Auto-Action |
|----------|----------|----------|-------------|
| P1 (Critical) | 5 min | PagerDuty, Slack, SMS | Circuit breaker / Halt |
| P2 (Warning) | 30 min | Slack, Email | Notify team |
| P3 (Info) | 4 hours | Daily digest | Log only |

---

## Rollout Stages

| Stage | Traffic | Duration | Success Criteria |
|-------|---------|----------|------------------|
| 1 | 10% | 3 days | Basic metrics stable |
| 2 | 25% | 5 days | Expectancy positive |
| 3 | 50% | 7 days | Risk metrics green |
| 4 | 100% | Ongoing | All KPIs maintained |

---

## SL Calibrator Milestones

| Phase | Timeline | Coverage Target | Groups Calibrated |
|-------|----------|-----------------|-------------------|
| Phase 1 | Week 1-2 | 20% | 4 groups |
| Phase 2 | Week 3-4 | 40% | 8 groups |
| Phase 3 | Week 5-6 | 60% | 12 groups |
| Phase 4 | Week 7-8 | 80% | 16+ groups |
