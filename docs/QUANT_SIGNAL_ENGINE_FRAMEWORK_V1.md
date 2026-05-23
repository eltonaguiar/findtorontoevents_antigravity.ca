# Quantitative Trading Signal Engine — Multi-Asset Methodology Framework v1

**Date:** 2026-04-19
**Scope:** stocks, crypto (spot + perps), forex, bonds, ETFs, commodities
**Status:** authoritative methodology for this repo — supersedes ad-hoc strategy-generation prompts
**Anchors:** [docs/STRATEGY_FACTORY_V1_1_AMENDMENTS.md](STRATEGY_FACTORY_V1_1_AMENDMENTS.md), [TESTING_PROTOCOL.MD](../TESTING_PROTOCOL.MD), [docs/MONTE_CARLO_VALIDATION.md](MONTE_CARLO_VALIDATION.md), [docs/STATISTICAL_RIGOR_FRAMEWORK.md](STATISTICAL_RIGOR_FRAMEWORK.md)

## The framework (per spec)

```json
{
  "methodology_overview": "Signals are filtered hypotheses, not discovered edges. Every candidate must survive 6 stages (S0 hypothesis → S5 live) before emitting live picks. Core philosophy: pre-live validation cannot certify live performance (proven empirically today: 7 strategies tested, 2 marginal passes, 5 honest fails). Only S4 forward paper (50+ resolved trades at strategy-appropriate frequency) and S5 tiny-live provide promotion-grade evidence. Signal taxonomy: (1) event-driven (token unlocks, earnings, FOMC, buybacks), (2) regime filters (Copper/Gold ratio, HYG-LQD spread, VIX term structure, Fear&Greed), (3) structural (perp funding, futures roll, ETF NAV premium), (4) ensemble meta (≥4 fresh LLM agents unanimously agreeing). Key innovation over generic systems: rehabilitation-first philosophy (cross-symbol → cross-asset → inverse → mutation → regime → crossover → graveyard) preserves signal value instead of destroying it.",

  "signal_generation_pipeline": {
    "step_1_data_inputs": {
      "price": "OHLCV at native timeframe per asset (1m-1h for intraday, 1d for swing, 1w for regime). Minimum 5-year history for backtest, 1-year minimum for S1 qualification.",
      "volume": "Exchange-reported volume for crypto/stocks. Forex uses tick-volume (proxy). Commodities use COT open interest weekly.",
      "indicators": "ATR(14) (volatility), SMA(20/50/200) (trend), RSI(14) (momentum, NOT as primary per STRATEGY_GRAVEYARD lessons), realized_vol(20) = stdev(log_returns) * sqrt(252).",
      "regime_series": "VIX (equity), DXY (forex), HYG-LQD spread (credit), Fear&Greed (crypto, 0-100).",
      "refresh_cadence": "Live scanners poll at strategy-native interval. Daily closes finalized at 00:00 UTC. Hourly refresh for hourly strategies. Never trade on open-bar; signals fire on close of prior bar, execute at next bar's open.",
      "minimum_history": "S1: 12 months. S2 walk-forward: 36 months (3 years needed for 70/15/15 split + 3-month WF windows). S3 Monte Carlo: 60 months recommended for regime coverage."
    },

    "step_2_signal_logic": {
      "mean_reversion_component": "Price deviation from central tendency (SMA, regression line, VWAP, typical price). Example trigger: |close - SMA(20)| / ATR(20) > 2.0 AND ADX(14) < 20 (no strong trend). Weight = 0.3 in composite. Academic anchor: DeBondt & Thaler (1985) overreaction hypothesis.",
      "momentum_component": "Trend confirmation via higher-highs/higher-lows structure + MACD positive AND SMA(50) > SMA(200). Example: close > SMA(50) AND MACD_hist[t] > MACD_hist[t-3]. Weight = 0.3. Academic anchor: Jegadeesh & Titman (1993).",
      "volatility_component": "Compression → expansion pattern. Example: ATR(14) < 30th percentile of ATR(14) over last 60 bars. Weight = 0.2. Academic anchor: Bollinger (1983) squeeze.",
      "volume_component": "Confirmation via volume > 1.5× SMA(volume, 20) on entry bar. Weight = 0.2. Academic anchor: Karpoff (1987) volume-price correlation.",
      "composite_score": "score = 0.3*MR_sig + 0.3*MOM_sig + 0.2*VOL_sig + 0.2*VOLUME_sig, each normalized [0,1]. Fire LONG only when score > 0.65. Fire SHORT only when score > 0.65 on inverse. This is ENSEMBLE — weights are empirical, tuned per asset class via walk-forward.",
      "signal_quality_filter": "Reject when (a) strategy is in alpha_engine/strategy_blocklist.py (retired or paper-only), (b) asset is in dead-ticker list (feed_hygiene._DEAD_SYMBOLS, e.g. MATICUSDT), (c) regime_alignment fails (per step 4)."
    },

    "step_3_tp_sl_calculation": {
      "base_formula": "SL = entry - max(k_sl × ATR(14), min_sl_pct × entry); TP = entry + k_tp × (entry - SL). Asymmetric: k_tp/k_sl ≥ 1.5 mandated (R:R must favor system).",
      "k_sl_defaults_by_asset": "stocks: k_sl=1.5, min_sl_pct=0.008. crypto: k_sl=1.2, min_sl_pct=0.006 (due to 24/7 vol). forex: k_sl=1.5, min_sl_pct=0.003. bonds: k_sl=1.0, min_sl_pct=0.004. ETFs: k_sl=1.5, min_sl_pct=0.008. commodities: k_sl=1.5, min_sl_pct=0.010.",
      "k_tp_defaults": "k_tp = 2.0 by default. Raise to 2.5-3.0 for trend-following. Drop to 1.5 for fast mean-reversion (< 4 hour hold).",
      "atr_floor_rationale": "If pure ATR stop is below half the typical bar-noise range (derived from 14-period Parkinson range estimator), use min_sl_pct to avoid wick-stops. Today's MATIC and Hyrotrader SHORT bleed were caused by sub-ATR stops."
    },

    "step_4_regime_filtering": {
      "bearish_bull_tilt_detection": "Compute 20-day rolling pct of longs that closed negative. > 65% = BEARISH, penalize LONG signals. < 35% = BULLISH, penalize SHORT. Source: audit_dashboard/template.html:_marketRegime (already live).",
      "volatility_regime": "VIX > 30 for equities OR Fear&Greed < 20 for crypto → reduce position size 50%, widen SL 25%. VIX > 40 → disable new entries entirely.",
      "liquidity_regime": "For stocks: avg 20-day $-volume > $10M required. For alt-crypto: 24h $-volume > $50M. For forex: avoid 22:00-23:00 UTC (thin liquidity).",
      "choppy_market_detection": "ADX(14) < 15 AND abs(close - SMA(20)) / SMA(20) < 0.5% → regime = CHOPPY. Block trend-following signals. Allow mean-reversion.",
      "fresh_data_gate": "If upstream data source (agent, feed) has not updated in > _FRESHNESS_REQUIRED_HOURS[source] (per audit_trail/dashboard_generator.py), skip its signals entirely."
    }
  },

  "asset_class_specific_adaptations": {
    "stocks": {
      "volatility_profile": "Realized vol 15-40% ann (SPY typical 12-18%, small-caps 25-50%). Intraday bar vol 0.3-0.8%. Liquidity tiered: large-cap ($10B+) > mid-cap ($1-10B) > small-cap (<$1B). Hours 14:30-21:00 UTC (9:30-16:00 ET). Gap risk overnight significant.",
      "slippage_model": "Large-cap: 5 bps. Mid-cap: 10-15 bps. Small-cap: 20-50 bps. Event days (earnings): 2× normal.",
      "tp_sl_approach": "ATR(14) based, SL = 1.5 × ATR, TP = 3.0 × ATR for trend; SL = 1.0 × ATR, TP = 1.5 × ATR for mean reversion.",
      "worked_example": "AAPL entry $150.00. ATR(14)=$2.50. Trend long: SL=$146.25 (1.5×ATR), TP=$157.50 (3.0×ATR). 2% account risk on $10,000 = $200 → 200/(150-146.25) = 53 shares. Slippage assumed 8 bps ($0.12)."
    },
    "cryptocurrencies_spot_and_futures": {
      "volatility_profile": "BTC realized vol 40-80% ann. ETH 50-100%. Alts 80-200%. 24/7 trading — no weekend gaps but liquidity drops Sat/Sun. Perp funding ±0.01-0.1%/8h; extreme events hit ±0.5%/8h.",
      "slippage_model": "BTC/ETH majors: 3-5 bps. Mid-tier alts: 10-30 bps. Micro-cap (<$100M mcap): 50-300 bps; avoid. Liquidation cascades: 100-500 bps momentarily.",
      "tp_sl_approach": "Tighter k_sl (1.2) due to high baseline vol. min_sl_pct 0.6% floor to avoid wick-stops (empirically validated today: MATIC 0.15% stops caused 889 deterministic losses). Perp funding must be checked: if |funding| > 0.08%/8h, reduce size 30% (liquidation risk).",
      "worked_example": "BTCUSDT perp at $75,000. ATR(1h, 14)=$450 (0.6% bar). SL=$74,460 (0.72% = 1.2×ATR). TP=$76,080 (R:R 2.0). On $10k account, 0.5% risk = $50 → $50/540 = 0.093 BTC notional ≈ $6,975 exposure."
    },
    "forex": {
      "volatility_profile": "EURUSD realized vol 5-10% ann (low). GBPUSD 7-12%. USDJPY 8-15%. EM pairs 15-30%. Session dynamics: Tokyo (22:00-07:00 UTC) quiet, London open (07:00-16:00) most active, NY overlap (12:00-16:00) peak volume. Spreads widen 21:00-23:00 UTC.",
      "slippage_model": "Major pairs: 0.5-1 pip (5-10 bps). Cross pairs: 1-3 pips. Exotic: 5-15 pips. News events: 10-50 pips momentary.",
      "tp_sl_approach": "Pip-based thresholds derived from ATR. Example EURUSD: ATR(1h)=10 pips → SL=15 pips, TP=30 pips. For daily strategies: ATR(daily, 14)=70 pips → SL=100 pips, TP=200 pips.",
      "worked_example": "EURUSD at 1.0850. ATR(1h, 14)=10 pips. SL=1.0835 (15 pips), TP=1.0880 (30 pips). Account $10k, 0.3% risk = $30. Position = $30/(15 pips × $0.0001) = 20,000 units = micro-lot × 2."
    },
    "bonds": {
      "volatility_profile": "TLT (20Y Treasury) realized vol 10-18% ann. IEF (7-10Y) 5-10%. LQD (IG corp) 7-12%. HYG (high yield) 10-18%. Duration risk dominates: 1bp yield change × duration = price change. TLT duration ~18yr → 1bp = 0.18%.",
      "slippage_model": "Treasury ETFs: 2-5 bps. Corporate bond ETFs: 5-10 bps. Individual bonds: 15-50 bps (avoid retail).",
      "tp_sl_approach": "ATR-based for bond ETFs. For duration-aware strategy: SL = entry - (duration × max_yield_move_bps × 0.01%). Example: TLT with expected 10bp move = 0.18% SL.",
      "worked_example": "TLT at $95. ATR(14d)=$1.20. SL=$93.80 (1.0×ATR, tight for low-vol), TP=$96.80 (R:R 1.5). Account $10k, 0.3% risk = $30, position = $30/1.20 = 25 shares."
    },
    "etfs": {
      "volatility_profile": "Broad index (SPY/QQQ): 10-18% ann. Sector (XLK/XLF/XLE): 15-30%. Leveraged (TQQQ): 40-70%. Tracking error 0.05-0.5%. Expense ratio 0.03-0.95%.",
      "slippage_model": "Top-10 ETFs: 2-5 bps. Mid-tier: 5-15 bps. Leveraged/inverse: 10-30 bps (decay risk on multi-day hold).",
      "tp_sl_approach": "Apply underlying asset-class logic. Adjust k_sl DOWN 20% for diversified baskets (lower idiosyncratic risk), UP 30% for leveraged.",
      "worked_example": "SPY at $450. ATR(14d)=$5.50. Trend: SL=$441.75 (1.5×ATR), TP=$466.50 (3.0×ATR). Typical hold 3-10 days."
    },
    "commodities": {
      "volatility_profile": "Gold (GLD) 12-20% ann. Silver (SLV) 25-40%. Oil (USO) 25-60%. Nat gas (UNG) 40-90% with seasonality. Agricultural (DBA) 10-20%. Contract roll (futures) creates gaps — avoid trading 5 days pre-expiry.",
      "slippage_model": "Top commodity ETFs: 5-15 bps. Futures: 1-3 ticks ($10-30 per contract typical). Seasonal-demand commodities (UNG winter): 2× normal spread.",
      "tp_sl_approach": "Wider stops (k_sl=1.5-2.0) due to supply-shock tail risk. Avoid trading 48h around OPEC meetings, USDA reports, EIA releases.",
      "worked_example": "GLD at $180. ATR(14d)=$2.20. Trend: SL=$176.70 (1.5×ATR), TP=$186.60 (3.0×ATR). Risk $30 = 9 shares."
    }
  },

  "position_sizing_and_risk_management": {
    "position_sizing_rules": "Primary: fixed-fractional 0.5% account risk per trade (30k account → $150 max loss). Volatility-scaled variant: sigma_adj_size = base_size × (target_vol / realized_vol). Target vol 15% ann. Kelly: f* = (b×p - q)/b where b=avg_win/avg_loss, p=WR, q=1-p. Cap Kelly at 25% of full (quarter-Kelly) due to estimation error. Do NOT apply Kelly to strategies with n<100 resolved.",
    "portfolio_constraints": "Correlation: max 2 simultaneous positions with ρ_60d>0.7. Concentration: max 30% of account in any asset class; max 15% in any single symbol. Drawdown: if realized 5-day DD > 3%, halve all new position sizes. If 20-day DD > 8%, suspend trading for 48h.",
    "signal_filtering_and_regime_detection": "Block entries when: VIX > 40 (equity), F&G < 15 or > 85 (crypto extremes), spread > 2× median (liquidity dry-up), correlated instrument just hit max-loss SL (contagion).",
    "leverage_guidelines": "Stocks/ETFs: no leverage at $10k account. Crypto perps: max 3× (20× is gambling at this size). Forex: max 10× majors only. Bonds: no leverage (duration risk + low returns = negative expected Kelly). Commodities: no leverage."
  },

  "optimization_and_backtesting_framework": {
    "walk_forward_testing": "Methodology: 36m training → 3m out-of-sample test, roll 1m forward, repeat 30+ times. Pass rate > 60% of windows must exceed IS performance × 0.7. Source: institutional_backtest_suite (already in repo). Use --bootstrap-sims 10000 for MC component.",
    "parameter_sensitivity_analysis": "For each parameter, ±20% from optimal. If Sharpe drops >30%, parameter is brittle → reject. Acceptable parameter count per strategy: ≤3 tunable. More = overfitting.",
    "robustness_checks": "Min sample size n≥100 resolved trades (TESTING_PROTOCOL.MD). Regime stability: Sharpe > 0.5 in ≥4 of 5 Fear&Greed buckets (Extreme Fear 0-20 / Fear 20-40 / Neutral 40-60 / Greed 60-80 / Extreme Greed 80-100). Stress tests: COVID-March-2020, FTX-Nov-2022, SVB-March-2023 windows must not breach 2× typical DD.",
    "metrics_and_acceptance_criteria": "Sharpe ≥ 1.0 post-cost (IS). Sortino ≥ 1.5. Max DD ≤ 25% on IS. Calmar = CAGR/|maxDD| ≥ 0.5. Win rate ≥ 50% Wilson LB with Bonferroni. Profit Factor ≥ 1.5. Information Ratio (vs relevant benchmark) ≥ 0.5. Reject if ANY fails."
  },

  "path_to_live_deployment": {
    "research_phase": "S0 hypothesis doc with falsifiable prediction + S0.5 data integrity check (per docs/STRATEGY_FACTORY_V1_1_AMENDMENTS.md). Outputs: docs/hypotheses/<strategy>.md, backtest_results/<strategy>_raw.json.",
    "pre_production_phase": "S1-S3 gates. Transaction cost replay (L2/Trade data for <1-day holdings). Monte Carlo 10k sims with regime decomposition. Orthogonality check (feature correlation <0.7 vs existing strategies).",
    "production_readiness": "S4 forward paper: 50 resolved sub-daily trades OR 30-day window OR 10 events (event-driven). Live data hash firebreak (schema must match backtest). Position limits: 0.25% risk, 3 trades/day, max 5% open exposure.",
    "live_monitoring": "Daily: realized WR vs predicted WR (flag if |diff|>10pp). Weekly: Sharpe drift (auto-demote if rolling 30d Sharpe < 0.5 × IS Sharpe). Monthly: full strategy review via perf-review cycle (see PR #257/#258 pattern). Kill-switches: automatic demotion to paper-only on any gate re-fail."
  }
}
```

## How this connects to the repo

| Framework component | Existing repo artifact |
|---|---|
| Walk-forward testing | `alpha_engine/validation/institutional_backtest_suite` (use `--bootstrap-sims 10000`) |
| Layer 2.5 Quality Gates | `audit_trail/quality_gates.py` (Score≥40, Trust≥4) |
| Freshness gate | `_FRESHNESS_REQUIRED_HOURS` in `dashboard_generator.py` |
| Strategy blocklist | `alpha_engine/strategy_blocklist.py` (retired + paper-only) |
| Dead-ticker guard | `alpha_engine/feed_hygiene.py _DEAD_SYMBOLS` |
| Regime awareness | `audit_dashboard/template.html _marketRegime` + `getVerifiedTier` regime floor |
| Rehabilitation pipeline | TESTING_PROTOCOL.MD §7 (cross-symbol → cross-asset → inverse → mutation → regime → crossover) |
| S0.5 data integrity | `tools/s05_data_integrity_audit.py` (today's ship) |
| Monte Carlo validation | `docs/MONTE_CARLO_VALIDATION.md` |
| Statistical rigor | `docs/STATISTICAL_RIGOR_FRAMEWORK.md` |
| Strategy lifecycle | `docs/STRATEGY_LIFECYCLE_POLICY.md` |

## What this framework does NOT do

- **Invent edge.** It filters candidate hypotheses through discipline. Today's data: 7 strategies tested, 2 marginal passes, 5 honest fails → ~15% pass rate. That's the expected yield.
- **Replace good ideas.** A bad hypothesis processed through this framework stays a bad hypothesis. Use the framework to save time on bad ideas, not to find edge in them.
- **Eliminate drawdowns.** Even a passing strategy will have losing streaks. The framework bounds DD via position sizing + portfolio constraints, not by eliminating losses.

## Required next step before any new strategy generation

**Every new strategy proposal must submit a 1-page S0 hypothesis doc FIRST** (template: `docs/hypotheses/token_unlock_event_driven.md`, shipped today). Implementation code is deferred to after S0 review approval. This framework is the operational spec; submitting code without the hypothesis doc = auto-rejection per v1.1.

---

## Review feedback — Cursor agent (2026-04-19)

1. **v2 alignment:** Methodology JSON in this doc is the repo’s structural spec — if `docs/QUANT_SIGNAL_ENGINE_FRAMEWORK_V2.md` is present in the branch, keep risk checklist / walk-forward defaults / appendices aligned; otherwise track v2 as a planned supplement.
2. **Composite weights:** Section on fixed MR/MOM/VOL/VOLUME weights should state these are **class-tuned** via walk-forward — static 0.3/0.3/0.2/0.2 is a template, not a universal constant.
3. **Discovery protocol:** Link [STRATEGY_DISCOVERY_PROTOCOL.md](STRATEGY_DISCOVERY_PROTOCOL.md) for **novelty + correlation pruning + cost tables** when generating *new* templates; v1 JSON describes the engine, not the research sweep.
4. **Evidence discipline:** Reinforce “no live claims from IS backtest alone” — same sentence as Strategy Factory v1.1; newcomers land here first via search.
5. **Tooling:** Add optional row: `baby_strategies/correlation_prune_strategies.py` under “How this connects to the repo” once return-export plumbing exists.
