# Capacity Constraints + Kelly Sizing — Qwen-Pro Deep-Dive (2026-05-31)

**AI:** qwen-max via dashscope-intl (compatible-mode/v1)
**Key used:** `QWEN_API_KEY_FREE` (fallback — `QWEN_API_KEY_PRO` in `~/dbpasses.txt` returned HTTP 401 `invalid_api_key`; the wrapped `sk-sp-...` token format is not accepted by the international DashScope endpoint. Operator: rotate/refresh PRO key.)
**Purpose:** Wire capacity-haircut + Kelly into the 24-strategy paper-pilot harness emitting 13:30 UTC 2026-06-01.

---

## 3-line operator summary

1. **Adopt fractional Kelly (1/4) as default**; reserve full Kelly only for strategies with Wilson-LB win-rate >= 60% AND bootstrap-PF LB >= 1.5 AND n>=500 (i.e. our existing gate suite passes with margin).
2. **Apply capacity haircut `min(1, threshold/AUM)`** per-strategy with class-specific thresholds (CRYPTO mean-rev = $50M, EQUITY momentum = $500M, BOND momentum = $600M, etc. — full matrix below). Multiplies the Kelly fraction at sizing time.
3. **Reject any new strategy where marginal portfolio Sharpe falls** OR where pairwise correlation to existing book > 0.5 (drives diversification, gates the 24->N expansion).

---

## Distilled spec (ready for `docs/PAPER_PILOT_HARNESS.md`)

### Capacity degradation thresholds ($M AUM at which alpha decays)

| Edge type        | CRYPTO | EQUITY | FOREX | COMMODITY | ETF | BOND | FUTURES | PRED_MKT |
|------------------|-------:|-------:|------:|----------:|----:|-----:|--------:|---------:|
| Mean-reversion   |     50 |    200 |   100 |       100 | 150 |  300 |     100 |       50 |
| Momentum         |    100 |    500 |   200 |       200 | 300 |  600 |     200 |      100 |
| Stat-arb         |     20 |    100 |    50 |        50 | 100 |  200 |      50 |       20 |
| Cross-asset arb  |     50 |    300 |   100 |       100 | 200 |  400 |     100 |       50 |

Interpretation: above the threshold, market-impact and queue-position decay multiply alpha by `threshold/AUM`. PRED_MKT and CRYPTO stat-arb degrade fastest (thin books). BOND momentum is most capacious.

### Kelly defaults

- **Full Kelly:** only when edge is high-certainty (Wilson LB WR >= 0.60, bootstrap PF LB >= 1.5, n>=500, intrabar-replay-validated).
- **Fractional Kelly (f* = 0.25 * f_kelly):** DEFAULT for the 24-strategy pilot. Matches MacLean+Thorp+Ziemba (2010) "Good and Bad Properties" — full Kelly maximizes log-growth but has unacceptable drawdown distribution; fractional dramatically reduces P(ruin) at modest growth cost.

### Per-strategy NAV cap

- **5% NAV cap:** high-risk / lower-certainty (failed any sub-gate, n<500 still in observation).
- **15% NAV cap:** low-risk / high-certainty (all gates pass with margin).
- Hard portfolio cap: sum of per-strategy weights <= 1.0 after Kelly+haircut; if Kelly proposes more, scale all down proportionally.

### Diversification gate (when adding strategy N+1)

```python
def admit_new_strategy(portfolio, candidate):
    # Reject if marginal Sharpe is negative
    s0 = sharpe(portfolio)
    s1 = sharpe(portfolio + [candidate])
    if s1 <= s0:
        return False, "marginal_sharpe_nonpositive"
    # Reject if correlation to any existing > 0.5
    for s in portfolio:
        if abs(corr(s.returns, candidate.returns)) > 0.5:
            return False, f"corr>0.5 vs {s.name}"
    return True, "ok"
```

### Capacity-haircut + Kelly application (production pseudo-code)

```python
def capacity_haircut(aum_usd_m, threshold_usd_m):
    return 1.0 if aum_usd_m <= threshold_usd_m else threshold_usd_m / aum_usd_m

def kelly_fraction(edge_mean, edge_variance, rf=0.0):
    # f* = (mu - rf) / sigma^2  (Thorp 2006 continuous form)
    if edge_variance <= 0:
        return 0.0
    return (edge_mean - rf) / edge_variance

def size_strategy(strategy, aum_usd_m, full_kelly: bool):
    threshold = CAPACITY_TABLE[strategy.asset_class][strategy.edge_type]
    h = capacity_haircut(aum_usd_m, threshold)
    f = kelly_fraction(strategy.mean_excess_return, strategy.variance)
    if not full_kelly:
        f *= 0.25
    # Hard cap per strategy
    cap = 0.15 if strategy.high_certainty else 0.05
    return max(0.0, min(cap, f * h))
```

### Citations

- **Thorp, E. O. (2006).** "The Kelly Capital Growth Investment Criterion." In *Handbook of Asset and Liability Management, Vol 1*. North-Holland. — derives continuous-time f* = (mu - r)/sigma^2.
- **MacLean, L. C., Thorp, E. O., & Ziemba, W. T. (2010).** "Good and Bad Properties of the Kelly Criterion." *Quantitative Finance* 10(7): 681-687. — empirical justification for fractional Kelly under estimation error.

---

## Raw API response (qwen-max)

```
1. **AUM Degradation Thresholds (in $M):**
   - Mean-Reversion: CRYPTO 50, EQUITY 200, FOREX 100, COMMODITY 100, ETF 150, BOND 300, FUTURES 100, PREDICTION_MARKETS 50
   - Momentum:       CRYPTO 100, EQUITY 500, FOREX 200, COMMODITY 200, ETF 300, BOND 600, FUTURES 200, PREDICTION_MARKETS 100
   - Stat-Arb:       CRYPTO 20,  EQUITY 100, FOREX 50,  COMMODITY 50,  ETF 100, BOND 200, FUTURES 50,  PREDICTION_MARKETS 20
   - Cross-Asset Arb: CRYPTO 50, EQUITY 300, FOREX 100, COMMODITY 100, ETF 200, BOND 400, FUTURES 100, PREDICTION_MARKETS 50

2. Kelly Fraction Defaults:
   - Full Kelly: low-risk, high-certainty strategies.
   - Fractional Kelly (1/4): higher-risk, lower-certainty strategies.

3. Per-Strategy Weight Cap:
   - 5% NAV: high-risk, low-certainty.
   - 15% NAV: low-risk, high-certainty.

4. Adding New Strategy Reduces Portfolio Expected Utility:
   - Correlation Threshold: > 0.5
   - Marginal-Sharpe Test (combined_sharpe < original_sharpe -> reject)

5. Capacity Haircut + Kelly Application (Python pseudo-code provided; reproduced above).

Citations:
- Thorp, E. O. (2006). "The Kelly Capital Growth Investment Criterion."
- MacLean, L. C., Thorp, E. O., & Ziemba, W. T. (2010). "Good and Bad Properties of the Kelly Criterion."
```

---

## Wiring instructions

1. Add `CAPACITY_TABLE` dict (above matrix) to `alpha_engine/sizing/capacity.py` (new file).
2. Add `size_strategy()` to same file; import from the paper-pilot harness pre-emit step.
3. Add `admit_new_strategy()` gate to `tools/strategy_admission.py` and call it before any expansion beyond the initial 24.
4. Default `full_kelly=False`; flip to True per-strategy only after the strategy has passed all sub-gates with margin for 4 consecutive weeks of paper trading.
5. Log the realized `(haircut, f_raw, f_fractional, cap, f_final)` tuple per pick into the audit trail so the audit-pick-flow skill can trace any sizing decision.

## Caveats

- Qwen's $M thresholds are order-of-magnitude consensus values, not derived from our book's actual market-impact model. Treat as defaults; calibrate per-strategy once we have >= 4 weeks of live fill data and can fit a square-root impact model (Almgren-Chriss style).
- The marginal-Sharpe test is computed on backtest returns and is biased upward in-sample; combine with the existing Bonferroni + bootstrap-PF gates already shipped by Cursor.
