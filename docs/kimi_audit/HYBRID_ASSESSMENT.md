# Hybrid Strategy Assessment — Kimi Agent Audit

**Date:** 2026-03-16
**Reviewer:** Claude (automated audit)
**Source:** `Kimi_Agent_Proven Crypto_Forex Strategies (1)/hybrid_dna_strategies_report.md` + `hybrid_strategies_implementation.py`

---

## Code Quality Verdict: TUTORIAL GRADE — Not Production Ready

The `hybrid_strategies_implementation.py` is a clean **educational backtest scaffold** but is NOT wirable into our alpha_engine. Issues:

1. **Standalone class hierarchy** — uses `HybridStrategy` base class with its own backtest loop. Our system uses function-based strategies that return `list[dict]` picks consumed by `scanner.py`.
2. **No live data integration** — expects a pre-loaded DataFrame. Our strategies pull from `data: dict[str, pd.DataFrame]` keyed by timeframe.
3. **Sample data only** — the `run_hybrid_backtests()` function generates synthetic sine+trend data. No real market validation.
4. **"AI Score" is faked** — Hybrid #3 (AI-Enhanced EMA) computes a heuristic from trend/vol/volume and calls it "AI". It's just a weighted composite indicator, not ML.
5. **No TP/SL/entry_price output** — our system requires structured pick dicts with `entry_price`, `target_price`, `stop_price`, `confidence`, `strategy` fields.
6. **VWAP is cumulative** — line 296 uses `cumsum()` VWAP which diverges over time. Our `vwap_session()` in `indicators.py` correctly resets per session.

**Bottom line:** Would need a full rewrite to match our `alpha_engine` contract. The logic itself is what matters — and it's all stuff we already have.

---

## Per-Hybrid Verdict

### Hybrid #1: VWAP-RSI Institutional Confluence (claimed 70-75% WR)

**Components we already have:**
- `proven_vwap_mean_reversion` in `proven_scanner_strategies.py` — VWAP + SD band mean reversion
- `vwap_sd_mean_reversion` in `crypto_strategies.py` — same concept, different params
- `vwap_session_mean_reversion` in `session_breakout.py` — session-aware VWAP
- `rsi_macd_confluence` in `crypto_strategies.py` — multi-indicator RSI confluence
- `multi_period_rsi_confluence` in battleground/incubator — exact multi-period RSI

**What the "hybrid" adds:** Uses RSI 14/21/50 as a triple-timeframe filter on VWAP touches. Short RSI oversold + medium RSI bullish + long RSI bullish = buy.

**Genuinely new idea?** NO. This is literally what our `confluence_engine.py` does when `proven_vwap_mean_reversion` and `rsi_macd_confluence` fire on the same symbol simultaneously. The cross-aggregation consensus engine already creates this exact hybrid signal organically.

**Verdict: SKIP** — Already emergent from our confluence system.

---

### Hybrid #2: AI-Enhanced EMA Pullback (claimed 72-78% WR)

**Components we already have:**
- `multi_timeframe_ema_stack` in `crypto_strategies.py` — EMA 9/21/50/200 alignment (65-72% WR)
- `proven_triple_ema_pullback` in `proven_scanner_strategies.py` — EMA pullback with volume
- `strategy_ema_stack` in `live_forward_test.py` — live EMA stack detection
- `multi_sigma_ema_stack` in `hybrid_strategies.py` (our own Wave 19 hybrid) — sigma reversal + EMA stack
- ADX trend strength filter — used across multiple strategies

**What the "hybrid" adds:** A composite "AI score" from trend strength + volatility + volume + ADX. Despite the name, this is NOT machine learning. It's a weighted average of 4 indicators clipped to 0-100.

**Genuinely new idea?** NO. Our `ml_signal_ranker.py` in KIMI already does actual ML ranking (Random Forest when enough data, heuristic before). The "AI score" here is just a basic composite indicator — less sophisticated than what we run.

**Verdict: SKIP** — Our existing EMA stack + ml_signal_ranker is superior. The "AI" label is marketing.

---

### Hybrid #3: Hoffman-Keltner Volatility Expansion (claimed 68-73% WR)

**Components we already have:**
- `hoffman_ema_trend` in `hoffman_strategy.py` — EMA 3/5/18 alignment + IRB pullback (62% WR, championship proven)
- `proven_keltner_squeeze_breakout` in `proven_scanner_strategies.py` — #1 PROVEN strategy, Keltner compression
- `ttm_squeeze_breakout` in `ttm_squeeze.py` — BB inside Keltner breakout (60-75% WR)
- `keltner_evolved_v1` / `keltner_evolved_moderate` in `keltner_evolved.py` — evolved Keltner variants
- `bollinger_keltner_squeeze_breakout` in `statistical_strategies.py` — BB+Keltner squeeze
- `super_keltner_ema_momentum` in `super_strategies.py` — Keltner + EMA momentum combo

**What the "hybrid" adds:** Requires Hoffman EMA alignment (3>5>18) AND Keltner bandwidth < 2% compression AND volume confirmation simultaneously.

**Genuinely new idea?** PARTIALLY. We run Hoffman and Keltner independently, and `super_keltner_ema_momentum` combines Keltner with EMA but uses different EMA periods (not Hoffman's 3/5/18). The specific Hoffman 3/5/18 + Keltner bandwidth compression as a combined filter is not explicitly coded. HOWEVER, our confluence engine already boosts confidence when `hoffman_ema_trend` and `proven_keltner_squeeze_breakout` fire together.

**Verdict: MARGINAL** — The explicit Hoffman+Keltner combo could be worthwhile as a named strategy if we want to formalize what the confluence engine already does implicitly. But the improvement over running them independently with consensus scoring is likely <5%.

---

### Hybrid #4: Convexity Zone Recovery (claimed 65-72% WR)

**What it does:** Trades supply/demand zones when drawdown exceeds 15% and a "convexity ratio" (recovery acceleration) exceeds 1.5.

**Do we have this?** Not explicitly. We have `wyckoff_accumulation` (accumulation detection) and `liquidation_cascade_bottom` (V-bounce after cascades), which cover similar ground.

**Genuinely new idea?** The "convexity ratio" (accelerating recovery measurement) is a somewhat novel framing, but it's essentially just measuring the second derivative of price — acceleration. Our `spike_predictor.py` and `drawdown_recovery_rsi` strategies detect similar bounce dynamics.

**Verdict: SKIP** — Not implemented in Kimi's code anyway (only 3 of 6 hybrids have Python code). Covered by existing bounce/recovery strategies.

---

### Hybrid #5: RSI-Weighted Pairs Arbitrage (claimed 75-82% WR)

**What it does:** Statistical arbitrage with RSI timing for pair reversion entries. Uses z-score, correlation, cointegration.

**Do we have this?** YES — `cointegration_pairs.py` exists in alpha_engine. Our quant_strategies.py has `cross_sectional_momentum`. The battleground has pairs-based strategies.

**Genuinely new idea?** Adding RSI divergence as an entry timer for pairs trades is a minor refinement. The claimed 75-82% WR for stat arb is aggressive — real-world pairs trading on crypto has much higher variance.

**Verdict: SKIP** — We have `cointegration_pairs.py`. RSI timing is a tweak, not a new strategy.

---

### Hybrid #6: Hoffman London Momentum (claimed 58-65% WR)

**What it does:** London session breakout filtered by Hoffman EMA alignment.

**Do we have this?** YES — `london_breakout` exists in `forex_strategies.py` (62% WR, documented). `hoffman_ema_trend` exists in `hoffman_strategy.py`. Our confluence engine merges them when both fire.

**Genuinely new idea?** NO. And at 58-65% WR, it actually performs WORSE than our standalone London breakout (62% WR). Adding the Hoffman filter apparently does not improve the London breakout meaningfully.

**Verdict: SKIP** — Lower WR than our existing London breakout.

---

## Summary Table

| Hybrid | Claimed WR | New Idea? | Our Existing Coverage | Verdict |
|--------|-----------|-----------|----------------------|---------|
| VWAP-RSI Confluence | 70-75% | No | `proven_vwap_mean_reversion` + `rsi_macd_confluence` + confluence engine | SKIP |
| AI-Enhanced EMA | 72-78% | No | `multi_timeframe_ema_stack` + `ml_signal_ranker` | SKIP |
| Hoffman-Keltner | 68-73% | Marginal | `hoffman_ema_trend` + `proven_keltner_squeeze_breakout` + `super_keltner_ema_momentum` | MARGINAL |
| Convexity Zone | 65-72% | Minor | `wyckoff_accumulation` + `liquidation_cascade_bottom` | SKIP |
| RSI Pairs Arb | 75-82% | No | `cointegration_pairs.py` | SKIP |
| Hoffman London | 58-65% | No | `london_breakout` (62% WR) already better solo | SKIP |

## Final Verdict

**0 of 6 hybrids warrant implementation.** Every single one is a combination of strategies we already run independently, and our cross-aggregation consensus engine (`cross_aggregation/`) + confluence engine (`alpha_engine/confluence_engine.py`) already creates these hybrid signals dynamically when multiple strategies agree on the same symbol.

The Kimi report's core insight — "combining proven strategies yields higher win rates" — is exactly what our consensus/confluence architecture already does, but in a more flexible and data-driven way (we don't hardcode which strategies combine; we let the data show us which combinations work via `conflict_lessons_learned.json`).

The one marginal candidate (Hoffman-Keltner) could be formalized as a named strategy, but the expected uplift over our existing consensus-based combination is negligible.

**Recommendation:** File this report for reference. No code changes needed.
