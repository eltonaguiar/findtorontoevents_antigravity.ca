# Per-Class Clean Metrics — Post-AI-Panel Recompute

_Generated: 2026-04-29 16:06 UTC_

## Methodology

### Data source
- `audit_dashboard/data/dashboard_data.json` → `picks.recent_closed`
- Raw pick count before purge: **3500**

### Outliers stripped
- `symbol == 'USDCHF=X'` — **51 picks** removed. Cited as 3015.8% concentration outlier in the AI panel synthesis (reports/ai_challenge_synthesis_2026_04_29.md). Single-symbol dominance inflates FOREX WR and sum_pnl, masking true edge distribution.
- `source_system contains 'mercury2'` — **37 picks** removed. Mercury2 source is one of the three toxic-outlier categories in `system_clean_metrics.purge_summary` (alongside TRX* and KATUSDT).
- `TRX*` / `KATUSDT` symbols — **0 picks** (absent from recent_closed at time of analysis; guard kept for forward-compatibility).

**Total purged: 88 picks** → clean set: **3412**

### Metrics computed
- **n**: clean pick count per asset class
- **WR%**: win rate (pnl_pct > 0)
- **95% CI**: ±1.96 × √[WR·(1−WR)/n]  (Wilson-approx)
- **PF**: profit factor = Σwins / Σ|losses|
- **Sharpe (per-trade)**: mean(PnL) / std(PnL)
- **Calmar**: avg_pnl / |worst single-trade loss| (proxy for MDD)
- **Verdict**: MARGIN-WR-ONLY if 95% CI overlaps 50%

Methodology informed by the 6-AI consultation panel (reports/ai_challenge_synthesis_2026_04_29.md), specifically the 'Methodology improvements' table and Q8 CPCV consensus.

---

## Per-Class Results (Clean)

| Class | n | WR% | 95% CI | WR lo | WR hi | PF | Sharpe | Calmar | Verdict |
|-------|---|-----|--------|-------|-------|----|--------|--------|---------|
| BOND | 20 | 50.0% | ±21.9% | 28.1% | 71.9% | 1.720 | 0.134 | 0.134 | INSUFFICIENT DATA (n<30) |
| COMMODITY | 648 | 43.4% | ±3.8% | 39.5% | 47.2% | 1.156 | 0.025 | 0.005 | NO CLEAR EDGE |
| CRYPTO | 1497 | 43.0% | ±2.5% | 40.4% | 45.5% | 1.165 | 0.055 | 0.006 | NO CLEAR EDGE |
| EQUITY | 401 | 50.4% | ±4.9% | 45.5% | 55.3% | 1.269 | 0.091 | 0.021 | MARGIN-WR-ONLY (CI overlaps 50%) |
| ETF | 81 | 53.1% | ±10.9% | 42.2% | 64.0% | 1.172 | 0.066 | 0.033 | MARGIN-WR-ONLY (CI overlaps 50%) |
| FOREX | 760 | 49.6% | ±3.6% | 46.1% | 53.2% | 0.707 | -0.028 | -0.001 | MARGIN-WR-ONLY (CI overlaps 50%) |

---

## Comparison: Dirty vs Clean Metrics (Delta)

| Class | Dirty n | Clean n | Δn | Dirty WR% | Clean WR% | ΔWR% | Dirty PF | Clean PF | ΔPF |
|-------|---------|---------|-----|----------|-----------|-------|----------|----------|------|
| BOND | 20 | 20 | +0 | 50.0% | 50.0% | +0.0% | 1.720 | 1.720 | +0.000 |
| COMMODITY | 648 | 648 | +0 | 43.4% | 43.4% | +0.0% | 1.156 | 1.156 | +0.000 |
| CRYPTO | 1534 | 1497 | -37 | 42.7% | 43.0% | +0.3% | 1.155 | 1.165 | +0.011 |
| EQUITY | 401 | 401 | +0 | 50.4% | 50.4% | +0.0% | 1.269 | 1.269 | +0.000 |
| ETF | 81 | 81 | +0 | 53.1% | 53.1% | +0.0% | 1.172 | 1.172 | +0.000 |
| FOREX | 811 | 760 | -51 | 50.7% | 49.6% | -1.1% | 0.729 | 0.707 | -0.022 |

---

## TL;DR (5 bullets)

1. **Clean survivors with measurable edge:** none.
2. **Margin-WR-only (95% CI overlaps 50%):** EQUITY, ETF, FOREX — cannot statistically confirm WR > 50% without wider sample.
3. **No clear edge after clean:** COMMODITY, CRYPTO.
4. **Biggest WR shift from purge:** FOREX moved -1.1pp — confirming outlier contamination was real.
5. **Purge scope:** 88 picks removed (2.5% of recent_closed). Primary drivers: USDCHF=X (51) + Mercury2-source (37). Clean n=3412 is the recommended denominator for all forward-looking reporting.

---

_Source: AI panel synthesis 2026-04-29 (P0 item) — run `python tools/compute_per_class_clean_metrics.py` to reproduce._
