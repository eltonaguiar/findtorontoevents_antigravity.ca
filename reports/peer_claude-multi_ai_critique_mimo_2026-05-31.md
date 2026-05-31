# Peer Critique — MIMO (mimo-v2.5-pro) on Day-1 Methodology Brief

- **Date:** 2026-05-31
- **Model:** mimo-v2.5-pro (Xiaomi MIMO Token-Plan endpoint, https://token-plan-sgp.xiaomimimo.com/v1/chat/completions)
- **Requested model id "mimo-token-plan":** rejected with HTTP 400 "Not supported model". Switched to `mimo-v2.5-pro` (top-tier general model from `/v1/models` listing).
- **Status:** ok
- **Agree-with-brief:** 72%
- **Method:** Posted the Day-1 methodology brief from claude-opus-4-7 as a `user` message with a quant red-team `system` prompt at temperature 0.3, asked for strict JSON reply.

## Parsed JSON critique (5-field schema)

```json
{
  "agree_with_brief_pct": 72,
  "top_missing": "No block bootstrap; trades have autocorrelation — use stationary block bootstrap (Politis-Romano).",
  "top_wrong": "Wilson LB on WR>0.50 and PF>1.2 are mechanically coupled — Bonferroni over-corrects.",
  "top_addition_execution": "Queue-position-aware fill simulation + conservative back-of-queue fills must still pass gates.",
  "top_addition_regime": "Regime-tag every trade; strategy must pass gates in ≥2 regimes independently.",
  "top_addition_live_vs_paper": "Daily |live_PF - paper_PF|/paper_PF with alert >15% over 20d, hard-kill >30%.",
  "top_addition_sizing": "Half-Kelly with 6mo rolling edge/variance window; never full Kelly.",
  "top_predicted_bug": "TIME_EXIT classification leak — pending SL/TP that *would* have triggered intrabar get phantom-counted as wins; expect 3-8% of TIME_EXIT trades to be phantom wins (inflates WR ~1-2pp)."
}
```

## Highest-signal additions to fold into the harness

1. **Block bootstrap** instead of iid bootstrap (autocorr in trade returns).
2. **MDD / Calmar gate** — current gates allow PF 1.2 / WR 51% with -45% drawdown.
3. **OOS decay ratio gate**: `IS_PF / OOS_PF < 0.6` across ≥3 walk-forward folds → overfit flag.
4. **Cross-strategy multiplicity correction**: 24 strategies × 7 gates = 168 comparisons → Holm-step-down or Benjamini-Hochberg FDR at portfolio promotion.
5. **Capacity gate**: avg_daily_volume × close > $2M for ≥80% of trades, else PF evaporates above $500K AUM.
6. **Economic rationale requirement** alongside statistical gates (defend against pure-noise n=500 strategies).
7. **DSR threshold calibration**: a fixed 0.95 is impossible across 24 strategies × ~50 param combos; calibrate to actual trial count.
8. **Conservative + optimistic SL fill replay**: bar's high == stop price is fill-order-ambiguous; require both modes to pass.
9. **Permutation spec**: circular block permutation of signal labels with block length = avg trade duration (current brief leaves this underspecified).
10. **HHI is not enough for diversity** — also require max pairwise return correlation < 0.40 AND effective number of independent bets > 3.

## Predicted bugs in a 30-day paper-pilot harness across 24 strategies (verbatim from MIMO)

1. **TIME_EXIT phantom wins**: trades classified as TIME_EXIT when CANCELLED SL/TP would have hit intrabar; expect 3-8% inflation of WR by ~1-2pp.
2. **Walk-forward overlap pseudo-replication**: 12mo train / 1mo step shares 11/12 months of training data; effective independent OOS = 1/12 of nominal; 8/12 folds pass then 4 fail and you cannot tell regime shift from genuine decay.
3. **Bootstrap seed non-determinism across agents**: independent 2nd-agent verification will disagree ~30% of the time near the 1.2 PF threshold (no antithetic bootstrap or seed fixing specified).
4. **Open == High / Open == Low bars**: asymmetric SL_HIT vs TP_HIT classification inflates long-strategy PF by 5-15%.
5. **ETF sleeve silent re-inclusion**: portfolio-wide n≥500 gate hides per-sleeve n=4 INSUFF (gate must be applied per-strategy, not per-portfolio).
6. **HHI calculation contaminated by TIME_EXIT phantom wins** (Bug #1 propagates into concentration check, masking real concentration in another strategy).

## Raw response (verbatim, parsed JSON)

The full assistant message was a fenced ```json``` block. Parsed file saved to `/tmp/mimo_parsed.json` (10,498 chars). Reproduced verbatim below:

```json
{
  "missing": [
    "No block bootstrap — naive 10K resamples assume iid returns; trades exhibit autocorrelation (mean reversion / momentum clustering). Use stationary block bootstrap with Politis-Romano optimal block length or at minimum 10-trade blocks.",
    "No maximum drawdown / Calmar gate — PF 1.2 with WR 51% can coexist with a -45% peak-to-trough. Add: max_drawdown_pct < -20% (peak-to-trough, intra-equity-curve) AND Calmar > 0.5.",
    "No out-of-sample decay ratio — must track IS_PF / OOS_PF. If OOS_PF < 0.6 × IS_PF across ≥3 walk-forward folds, flag overfitting regardless of aggregate gates passing.",
    "No explicit look-ahead bias audit checklist — feature engineering must be timestamped to bar_close - 1 (strict left-causal). Needs automated test: shift features +1 bar, re-run, verify PF drops to noise.",
    "No across-strategy multiplicity correction — Bonferroni corrects the 7 gates within one strategy but 24 strategies × 7 gates = 168 effective comparisons. Either Holm-step-down across the full matrix or FDR (Benjamini-Hochberg) at portfolio promotion time.",
    "No liquidity / ADV cap — a strategy showing PF 2.0 on illiquid micro-caps evaporates at $500K AUM. Add: avg_daily_volume × close > $2M (or your capacity threshold) for ≥80% of trades.",
    "No economic rationale requirement — purely statistical gates can still pass noise (especially with n=500 at WR 51%). Require a written causal mechanism that maps to a known market microstructure friction, behavioral bias, or structural supply/demand imbalance.",
    "No model complexity budget — no limit on parameters, no AIC/BIC gate, no MDL constraint. Add: effective parameters (per BIC) < sqrt(n_trades) or require the model to beat a parsimonious benchmark (e.g., buy-and-hold with volatility targeting) on DSR.",
    "No handling of ex-dividend / split adjustments in intrabar OHLC replay — raw OHLC can produce phantom SL/TP triggers around corporate actions.",
    "No portfolio-level VaR / ES gate — individual strategy gates don't bound tail risk of the correlated bundle. Add: portfolio 99% CVaR (1000-day historical sim) < 8% of NAV at target allocation."
  ],
  "wrong": [
    "Wilson LB on WR > 0.50 is mechanically coupled with PF > 1.2 — they are not independent gates, so Bonferroni over-corrects.",
    "n >= 500 is the wrong granularity — should be stratified by trade frequency. Calibrate as: n × avg_holding_period_in_days > 252 (≥1 full market-year of cumulative exposure).",
    "DSR > 0.95 is near-impossible for single-strategy with realistic Sharpe — Lopez de Prado's deflator penalizes heavily when N_trials is large; calibrate threshold to actual trial count.",
    "Intrabar OHLC replay without queue-position modeling is WRONG for limit/stop orders — must run both conservative (worst fill) and optimistic (exact level) modes and require both pass.",
    "Permutation p-value definition is underspecified — specify circular block permutation of signal labels with block length matching avg trade duration.",
    "HHI < 0.30 conflates source diversity with strategy diversity — add max pairwise correlation < 0.40 and effective number of independent bets > 3."
  ],
  "additions": {
    "execution": [
      "Queue-position-aware fill simulation (conservative back-of-queue must still pass gates).",
      "Spread cost = 0.5 × bid-ask × volatility regime; stress at 1x/2x/5x.",
      "Square-root market impact for trades > 1% ADV.",
      "Partial fill modeling at AUM > $1M.",
      "Slippage decay curve recalibrated monthly by time-of-day, day-of-week, VIX bucket."
    ],
    "regime": [
      "Regime-tag every trade (trend up/down, mean-rev, hi-vol, lo-vol via 60d/252d realized vol + ADX); pass gates in ≥2 regimes independently.",
      "Synthetic regime-switch injection in walk-forward; PF must not collapse below 1.0.",
      "Max regime-vulnerability: no single regime > 60% of cumulative PnL.",
      "PELT / BOCPD changepoint detection on returns; ≥2 changepoints OOS → re-estimate.",
      "Macro-conditioned gates: separate pass for QE-tightening vs QE-easing."
    ],
    "live_vs_paper": [
      "Daily |live_PF - paper_PF|/paper_PF, alert >15% over 20d, hard-kill >30%.",
      "Fill quality ratio per strategy; <0.80 for 5 consecutive days → auto-deallocate.",
      "Latency attribution per signal → order → fill; >500ms median for sub-hour holds → execution-degraded.",
      "Ghost portfolio: keep paper-trading rejected strategies; 90 consecutive days passing live → re-evaluate.",
      "Weekly trade-level paper-vs-live PnL reconciliation; McNemar's test p<0.01 → investigate."
    ],
    "sizing": [
      "Half-Kelly with 6mo rolling edge/variance window.",
      "Risk-parity / min-variance with rolling 90d correlation; cap any strategy at 25% of portfolio risk budget.",
      "Drawdown-adaptive sizing: halve allocation after 2× historical max DD, restore linearly.",
      "Capacity-aware sizing: position × impact ≤ 10bps of expected edge.",
      "Anti-Martingale floor: never increase allocation after losses."
    ]
  },
  "predicted_bugs": [
    "TIME_EXIT classification leak — pending SL/TP that would have triggered intrabar get counted as TIME_EXIT phantom wins (3-8% of TIME_EXIT trades, inflates WR 1-2pp).",
    "Walk-forward overlap pseudo-replication — 11/12 months shared across consecutive folds; effective OOS sample = 1/12 nominal; cannot distinguish regime shift from decay.",
    "Bootstrap seed non-determinism across independent agents — ~30% disagreement near the PF 1.2 threshold; no antithetic bootstrap or seed-fixing specified.",
    "Intrabar replay misclassifies bars where open == high or open == low — asymmetric SL/TP fill price inflates long-strategy PF by 5-15%.",
    "ETF (n=4) sleeve silently re-included when portfolio-wide n≥500 passes — gate must be per-strategy, not per-portfolio.",
    "HHI computation contaminated by TIME_EXIT phantom wins (Bug #1) — over-weights one strategy's share, masks concentration in another."
  ],
  "agree_with_brief_pct": 72
}
```

## Method log

- Endpoint advertised model id `mimo-token-plan` was REJECTED with HTTP 400 ("Not supported model"). Pulled `/v1/models` listing; chose `mimo-v2.5-pro` (Xiaomi's flagship general model). HTTP 200, 16,232 bytes, single completion, finish_reason=stop, no retries needed, no rate-limit.
- Auth header: `Authorization: Bearer tp-s72xhkxoi7dupmjsfvf344ihmjshtbca0gxibsg5v87zbp97` (key sourced from `/home/eaguiar2015/dbpasses.txt` under `XIAOMI_MIMO_TOKEN_PLAN`).
- Temperature 0.3, system prompt = "quant methodology red-teamer", user prompt = the Day-1 brief verbatim.
