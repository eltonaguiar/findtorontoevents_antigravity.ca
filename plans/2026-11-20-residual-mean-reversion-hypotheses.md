# Pre-registration drafts — market-neutral residual mean reversion

**Status:** drafts, not filed · **Date:** 2026-11-20
**Target:** [`reports/hypothesis_registry.json`](../reports/hypothesis_registry.json) (M-107 gate)

These are the ideas from the residual mean-reversion design, written in the
registry's own format so they can be appended as-is. Registry rules honoured:
one test statistic per hypothesis, acceptance criteria stated numerically, no
data touched yet (`data_sample_lock: null`).

Last id observed in the registry is `H-143`, so these are `H-144`…`H-147` —
**re-check the tail before appending**, since the file is append-only and other
agents write to it.

Why they are not filed yet: filing requires editing JSON, and the architect mode
edits Markdown only. Per M-107 they must be committed *before* any backtest runs,
so filing them is the first task of the implementation pass, not the last.

---

## H-144 — ETF — factor-residual OU mean reversion

```json
{
  "id": "H-144",
  "asset_class": "ETF",
  "family": "residual_mean_reversion",
  "description": "Factor-residual OU mean reversion on liquid US sector ETFs. Rolling 60-day regression of each ETF on the market factor plus its sector factor; fit OU to the residual; enter when |s-score| >= 1.25, exit at |s| <= 0.5; beta-weighted factor hedge for neutrality; inverse-vol sizing with caps enforced in the order gateway, not the model. Daily rebalance, 5 bps per trade base and 10 bps stress.",
  "test_statistic": "net-of-cost Sharpe ratio of the residual book (annualized, walk-forward)",
  "acceptance_criteria": {
    "min_sharpe": 0.5,
    "min_n_per_leg": 50,
    "slippage_bps": 5,
    "stress_slippage_bps": 10,
    "dsr": 0.95,
    "n_trials_recorded": true,
    "validation": "purged walk-forward, 5 folds; reject if any fold < 0.2 Sharpe or if the paired-block 95% CI of net return includes 0"
  },
  "economic_prior": "Short-horizon overreaction and liquidity provision in idiosyncratic returns. The residual is market-neutral by construction, so this makes no direction call: the prior risk is that residuals trend (half-life drift), not that the market moves against us.",
  "status": "PRE_REGISTERED",
  "registered_at": "2026-11-20",
  "data_sample_lock": null,
  "result": {
    "verdict": "PRE_REGISTERED — not run.",
    "operator_note": "Do not test against the same sample as H-143 (month-end trend) or any ETF TAA variant. Publish the OU half-life per name alongside the Sharpe: a half-life longer than the holding period means the trade is a trend bet wearing a mean-reversion label."
  }
}
```

## H-145 — COMMODITY — energy calendar-spread reversion

```json
{
  "id": "H-145",
  "asset_class": "COMMODITY",
  "family": "calendar_spread_reversion",
  "description": "Energy calendar spread (front vs second contract, WTI and NG) mean reversion. Kalman-filter hedge ratio, Bollinger entry and exit on the spread, roll-aware continuous series with point-in-time contract selection. 10 bps per leg base, 20 bps stress.",
  "test_statistic": "net-of-cost Sharpe ratio of the spread sleeve (annualized, walk-forward)",
  "acceptance_criteria": {
    "min_sharpe": 0.5,
    "min_n_round_trips": 100,
    "slippage_bps": 10,
    "stress_slippage_bps": 20,
    "dsr": 0.95,
    "validation": "walk-forward spanning at least 3 regimes including the post-2020 negative-price regime; reject if any regime fold is negative"
  },
  "economic_prior": "Storage and roll-yield economics make calendar spreads less trend-exposed than outrights, and the spread is a relative-value claim rather than a price forecast. Published pre-2013 results do not transfer: WTI traded negative in 2020 and storage economics changed.",
  "status": "PRE_REGISTERED",
  "registered_at": "2026-11-20",
  "data_sample_lock": null,
  "result": {
    "verdict": "PRE_REGISTERED — not run.",
    "operator_note": "Kalman hedge ratios are free parameters: record how many were fitted and include them in n_trials. The 1992-2013 evidence is a different regime, not corroboration."
  }
}
```

## H-146 — ETF — cost-implied trade gate

```json
{
  "id": "H-146",
  "asset_class": "ETF",
  "family": "execution_cost_gate",
  "description": "Change position only when the forecast magnitude exceeds round-trip cost, applied to the H-144 signal set. Measured as a paired comparison on identical signals: gated versus ungated. Turnover reduction and gross-alpha retention are reported alongside, not substituted for, the primary statistic.",
  "test_statistic": "paired difference in net-of-cost Sharpe (gated minus ungated), block-bootstrapped 95% CI",
  "acceptance_criteria": {
    "paired_sharpe_delta": "> 0 with 95% CI excluding 0",
    "min_turnover_reduction": 0.5,
    "min_gross_alpha_retention": 0.6,
    "slippage_bps": 5,
    "validation": "same folds as H-144 so the comparison is paired, not independent"
  },
  "economic_prior": "Annual cost drag is turnover times round-trip cost. When the forecast is smaller than the cost it must pay, trading is strictly negative-expectancy regardless of whether the forecast is skilful. This should hold even if H-144 fails, which makes it the most independently informative hypothesis of the four.",
  "status": "PRE_REGISTERED",
  "registered_at": "2026-11-20",
  "data_sample_lock": null,
  "result": {
    "verdict": "PRE_REGISTERED — not run.",
    "operator_note": "If it holds here it applies to every class, so a CROSS-ASSET record may be warranted once the ETF measurement is done. Kept under ETF for now because a hypothesis needs one measurable population."
  }
}
```

## H-147 — EQUITY — does factor hedging recover selection alpha?

```json
{
  "id": "H-147",
  "asset_class": "EQUITY",
  "family": "factor_neutralization",
  "description": "For each resolved closed pick, hedge the market-factor exposure over its own holding window and re-measure selection alpha. Compare beta-hedged selection alpha to the current unhedged figure of -0.2763%/trade (CI [-0.506, -0.043], n=3192).",
  "test_statistic": "selection alpha = mean net return minus direction-adjusted buy-and-hold over the same window, beta-hedged",
  "acceptance_criteria": {
    "min_n": 200,
    "criterion": "beta-hedged selection alpha > 0 with 95% CI excluding 0"
  },
  "economic_prior": "Our selection alpha is negative and roughly the size of an unhedged beta mis-timing. If the picks carry information but time the market badly, hedging recovers it. If hedging does not recover it, the picks carry no information — which is the more likely outcome, and a clean falsification either way.",
  "status": "PRE_REGISTERED",
  "registered_at": "2026-11-20",
  "data_sample_lock": null,
  "result": {
    "verdict": "PRE_REGISTERED — not run.",
    "operator_note": "This is the cheapest decisive test in the set: it reuses existing closed picks and needs no new strategy code. Run it before building any new sleeve."
  }
}
```

## H-148 — ETF — intraday ETF vs constituent basket spread

```json
{
  "id": "H-148",
  "asset_class": "ETF",
  "family": "etf_basket_basis_reversion",
  "description": "Intraday mean reversion of the spread between a liquid index ETF and its constituent basket, traded as a relative-value pair. No creation/redemption authority required, unlike true NAV arbitrage. Minute bars, point-in-time constituents and weights, 2 bps per leg base and 5 bps stress.",
  "test_statistic": "net-of-cost Sharpe ratio of the basis-reversion pair (annualized, walk-forward)",
  "acceptance_criteria": {
    "min_sharpe": 0.5,
    "min_n_round_trips": 200,
    "slippage_bps": 2,
    "stress_slippage_bps": 5,
    "dsr": 0.95,
    "validation": "walk-forward across at least 2 volatility regimes; reject if the basis half-life exceeds the average holding period observed"
  },
  "economic_prior": "ETF price and basket value are tied by arbitrage, so deviation is a liquidity-provision claim rather than a direction call. The genuine NAV arbitrage is access-gated; this is the retail-accessible shadow of it.",
  "status": "PRE_REGISTERED",
  "registered_at": "2026-11-20",
  "data_sample_lock": null,
  "result": {
    "verdict": "PRE_REGISTERED — not run.",
    "operator_note": "Requires minute bars and point-in-time constituent weights, which we may not have. Check data availability before declaring this testable — a BLOCKED_DATA status is the honest outcome if we lack the bars, not a backtest on daily closes."
  }
}
```

---

## The tracker landscape (so nobody files into the wrong file)

| Path | What it is | Use it? |
|---|---|---|
| [`reports/hypothesis_registry.json`](../reports/hypothesis_registry.json) | Canonical M-107 pre-registration ledger, append-only, 108+ entries | **Yes — this is the tracker** |
| [`audit_trail/data/hypothesis_registry.json`](../audit_trail/data/hypothesis_registry.json) | Empty stub (`{"hypotheses": {}, "last_updated": ""}`) | No — explicitly not the ledger |
| [`audit_dashboard/data/theory_tracker.json`](../audit_dashboard/data/theory_tracker.json) | Per-theory status (B_news_sentiment, G_equity_mean_reversion, …) | Only for status display, not registration |
| [`research/profitability/HYPOTHESES.md`](../research/profitability/HYPOTHESES.md) | Separate 23-candidate research registry with its own PROTOCOL versioning | Separate programme — do not mix |

Statuses: use the canonical seven (`PRE_REGISTERED`, `UNTESTED`, `BLOCKED_DATA`,
`FORWARD`, `SUPPORTED`, `WEAK`, `REFUTED`) — normalized on read by
[`alpha_engine/hypothesis_status.py`](../alpha_engine/hypothesis_status.py),
which reports unmapped spellings rather than guessing them.
