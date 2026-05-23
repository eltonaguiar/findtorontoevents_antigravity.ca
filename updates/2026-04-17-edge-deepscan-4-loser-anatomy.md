# Edge Deep-Scan 4 — Loser Anatomy

**Date:** 2026-04-17
**Source:** `audit_dashboard/data/dashboard_data.json` -> `picks.recent_closed`
**Universe:** 3,500 resolved picks (status WON/LOST/EXPIRED/CLOSED, all have `pnl_pct`)
**Read-only forensic — no code edits.**

---

## TL;DR — Three biggest structural killers

| # | Killer | Loss saved if blocked | Picks blocked |
|---|--------|----------------------:|--------------:|
| 1 | `claude_gainer_1h` strategy (CRYPTO LONG, conf 0.90, R:R ~0.05-0.46) | +88.3 pts | 53 |
| 2 | `kimi_signal_tracking` source (FOREX/EQUITY BUY, conf=10.0 bug, no rr_ratio) | +52.6 pts | 26 |
| 3 | R:R < 0.6 at entry (need 62%+ WR to break even, get 42%) | +78.1 pts | 38 |

Combined with the full top-15 strategy + top-20 pair + toxic-direction blocks: **+158 PnL pts**, WR 48.8% -> 56.5%.

---

## 1. Bottom-decile catastrophic picks (n=350, worst 10%)

Pnl range: **-46.80% to -1.95%**, mean **-4.02%**, median **-3.09%**

### What's WORSE than the book in the bottom decile:

| Field | Worst-decile mean | Full-book mean | Direction |
|-------|------------------:|---------------:|:---------:|
| **confidence** | **0.902** | 0.729 | **HIGHER** (high-conf trap) |
| score | 45.98 | 47.04 | slightly lower |
| elite_score | 28.31 | 32.76 | lower |
| forward_wr | 41.07 | 46.62 | lower |
| strat_fwd_wr | 42.99 | 48.80 | lower |
| strat_fwd_pf | 1.96 | 3.16 | lower |
| strat_fwd_trades | 268 | 538 | lower (less seasoned) |
| rr_ratio (raw field) | 1.68 | 1.86 | slightly lower |

**Headline:** Bottom-decile picks have HIGHER confidence than the full book. Confidence is anti-predictive at the tail.

### Bottom-decile composition

| Dimension | Top buckets |
|-----------|-------------|
| asset_class | CRYPTO 50.9% / EQUITY 34.3% / ETF 6.9% / FOREX 5.1% / COMM 2.9% |
| direction | LONG 82.9% / SHORT 14.0% / BUY 3.1% |
| elite_grade | C 49.1% / D 24.3% / B 21.1% / F 5.4% (B+C dominate, NOT just F) |
| exit_reason | SL_HIT 66.3% / EXPIRED 16.0% / FORCE_CLOSED 11.4% / TIME_EXIT 4.9% |

### Top contributors (worst decile, by total -PnL)

| Strategy | n | Total -PnL |
|----------|--:|----------:|
| claude_gainer_1h | 20 | -174.1% |
| (empty / kimi_signal_tracking) | 11 | -125.6% |
| luxalgo_confluence | 31 | -88.5% |
| Classic Momentum | 15 | -68.0% |
| Breakout Momentum | 18 | -64.0% |
| ml_crypto_predictor | 17 | -48.8% |
| st_rsi_momentum_confluence | 16 | -48.5% |
| Bollinger MR | 13 | -46.8% |
| unknown | 4 | -34.1% |
| st_multi_day_momentum | 11 | -33.4% |

---

## 2. Negative-EV at entry (R:R math)

| Bucket | Count | % of book | Actual WR | Required WR for breakeven |
|--------|------:|----------:|----------:|--------------------------:|
| R:R < 0.4 | 15 | 0.4% | (~13%) | 71% |
| R:R < 0.6 | 38 | 1.1% | 42.1% | 62% |
| R:R < 1.0 | 71 | 2.1% | 38.0% | 50% |
| R:R >= 1.0 | 3,326 | 97.9% | 47.1% | varies |

R:R<1.0 net contribution: **-89.7%** (dollars in, dollars out negative). Small footprint, surgical kill.

---

## 3. Toxic strategies (n>=20) — kill candidates

Sorted by total PnL (worst first). Target list for `BLOCKED_STRATEGIES`.

| # | Strategy | n | WR% | PF | AvgPnL | TotPnL |
|---|----------|--:|----:|---:|-------:|-------:|
| 1 | **claude_gainer_1h** | 53 | 43.4 | 0.52 | -1.67 | **-88.3** |
| 2 | **(empty) / kimi_signal_tracking** | 26 | 38.5 | 0.60 | -2.02 | **-52.6** |
| 3 | **unknown** | 28 | 32.1 | 0.44 | -0.98 | **-27.3** |
| 4 | crypto_bayesian_regime_transition_momentum_v1 | 34 | 26.5 | 0.55 | -0.15 | -5.2 |
| 5 | st_rsi_momentum_confluence | 88 | 43.2 | 0.97 | -0.03 | -2.5 |
| 6 | non_crypto_consensus | 63 | 52.4 | 1.12 | 0.00 | 0.0 |
| 7 | cta_cross_asset_tsmom | 56 | 37.5 | 1.24 | 0.02 | 1.1 |

Top 3 alone are responsible for **-168.2 pts** across 107 picks (3% of book).

**Surgical recommendation:** Add to `BLOCKED_STRATEGIES`:
```
claude_gainer_1h
kimi_signal_tracking          # block at source level (all picks have empty strategy)
unknown                       # placeholder bug — block while investigated
crypto_bayesian_regime_transition_momentum_v1
```

---

## 4. Top 20 toxic (strategy, symbol) pairs (n>=5)

For `BLOCKED_ASSET_STRATEGY_PAIRS`:

| # | Strategy | Symbol | n | WR% | TotPnL |
|---|----------|--------|--:|----:|-------:|
| 1 | ml_crypto_predictor | FETUSDT | 28 | 35.7 | -36.7 |
| 2 | st_multi_day_momentum | ARBUSDT | 9 | 0.0 | -28.3 |
| 3 | st_rsi_momentum_confluence | ADAUSDT | 16 | 6.2 | -23.5 |
| 4 | Breakout Momentum | JNJ | 8 | 0.0 | -22.7 |
| 5 | quan_engine | DOTUSDT | 11 | 0.0 | -20.1 |
| 6 | luxalgo_confluence | ARBUSDT | 9 | 22.2 | -15.4 |
| 7 | Classic Momentum | XOM | 8 | 25.0 | -14.8 |
| 8 | Breakout Momentum | FXA | 8 | 0.0 | -14.7 |
| 9 | ml_enhanced_ALGOUSDT_15m_B_lightgbm | ALGOUSDT | 5 | 40.0 | -13.9 |
| 10 | st_rsi_momentum_confluence | ATOMUSDT | 13 | 15.4 | -12.5 |
| 11 | ml_enhanced_AVAXUSDT_15m_D_ensemble_stack | AVAXUSDT | 6 | 0.0 | -12.3 |
| 12 | st_fear_greed_contrarian | ATOMUSDT | 23 | 26.1 | -10.7 |
| 13 | luxalgo_confluence | DOTUSDT | 13 | 30.8 | -9.2 |
| 14 | quan_engine_scalp | AVAXUSDT | 34 | 17.6 | -8.3 |
| 15 | st_obv_support_divergence | ETHUSDT | 10 | 10.0 | -8.2 |
| 16 | crypto_kalman_trend_residual_reversion_v1 | BTCUSDT | 13 | 15.4 | -8.2 |
| 17 | claude_ml_moderate_mut | JUPUSDT | 5 | 0.0 | -7.5 |
| 18 | st_fear_greed_contrarian | LTCUSDT | 7 | 0.0 | -6.4 |
| 19 | Breakout Momentum | FXC | 11 | 27.3 | -6.2 |
| 20 | st_fear_greed_contrarian | APTUSDT | 16 | 31.2 | -5.6 |

Notable pattern: **st_fear_greed_contrarian** appears 4x (ATOM/LTC/APT/SUI/UNI) — strategy is symbol-agnostic broken, consider full kill (also see strategy table).

---

## 5. Toxic asset_class x direction triples (n>=30)

For `BLOCKED_DIRECTION_TRIPLES`:

| Asset / Direction | n | WR% | TotPnL | AvgPnL |
|-------------------|--:|----:|-------:|-------:|
| **CRYPTO / SHORT** | 251 | 42.6 | **-36.7** | -0.146 |
| **ETF / LONG** | 63 | 47.6 | **-12.1** | -0.193 |
| FOREX / LONG | 382 | 45.5 | -3.2 | -0.008 |
| COMMODITY / SHORT | 280 | 41.1 | +4.7 | +0.017 |
| COMMODITY / LONG | 136 | 33.1 | +5.8 | +0.043 |
| FOREX / SHORT | 381 | 46.2 | +17.5 | +0.046 |
| EQUITY / LONG | 335 | 52.2 | +238.3 | +0.711 |
| **CRYPTO / LONG** | 1,622 | 53.5 | **+1183.5** | **+0.730** |

**Verdict:** CRYPTO/SHORT bleeds (-36.7), driven by `luxalgo_confluence` SHORTs (-18.2 from 88 trades, 38.6% WR) and ml_enhanced_*_15m models. Recommend block CRYPTO SHORTs **except** dna_winner / proven SHORT specialists. ETF/LONG also negative.

---

## 6. Confidence trap zones per asset class (WR < 35%, n >= 20)

| Asset | Conf bucket | n | WR% | TotPnL |
|-------|-------------|--:|----:|-------:|
| COMMODITY | 0.65 - 0.70 | 107 | 30.8 | -7.0 |
| COMMODITY | 0.70 - 0.75 | 97 | 34.0 | -7.9 |
| EQUITY | 0.60 - 0.65 | 50 | 34.0 | -15.1 |
| FOREX | 0.60 - 0.65 | 38 | 31.6 | -5.4 |
| FOREX | 0.70 - 0.75 | 52 | 32.7 | -4.3 |
| **FOREX** | **1.00 - 1.05** | **27** | **25.9** | **-23.4** (kimi bug bucket) |

### Confidence-bucket WR (full book)

| Bucket | n | WR% | AvgPnL |
|--------|--:|----:|-------:|
| < 0.50 | 395 | **61.5** | +1.272 (best!) |
| 0.50-0.70 | 1,393 | 43.5 | +0.251 |
| 0.70-0.85 | 1,426 | 49.5 | +0.343 |
| 0.85-0.95 | 169 | 55.0 | +0.088 |
| 0.95-1.00 | 77 | 51.9 | +0.216 |
| >= 1.00 (bug) | 14 | 64.3 | +1.686 |

**Key insight:** Low-confidence picks (< 0.5) win MORE often than mid-confidence (0.5-0.7). The 0.5-0.7 band is the **danger zone** — false confidence with no edge. The bottom-decile high-conf signature (mean 0.902) is also overrepresented in the 0.85-0.95 dropoff bucket.

---

## 7. Flat-trade dilution (FORCE_CLOSED / EXPIRED / TIME_EXIT, |pnl|<0.1)

| Asset | Invisible | Total | % Invisible |
|-------|----------:|------:|------------:|
| CRYPTO | 57 | 1,873 | 3.0% |
| EQUITY | 20 | 346 | 5.8% |
| ETF | 3 | 63 | 4.8% |
| **BOND** | 5 | 17 | **29.4%** |
| **FOREX** | 211 | 785 | **26.9%** |
| **COMMODITY** | 223 | 416 | **53.6%** |

Broader (any closed |pnl|<0.1): **FOREX 66.1%, COMMODITY 57.7%, BOND 35.3%**. These three asset classes are diluting reported WR with structural no-ops. They should be reported with separate "true-active" WR.

---

## 8. Single best blocker — ranked

| Rank | Blocker | n_blocked | PnL saved |
|-----:|---------|----------:|----------:|
| 1 | R:R < 0.4 at entry | 15 | +94.0 |
| 2 | Strategy = `claude_gainer_1h` | 53 | +88.3 |
| 3 | R:R < 0.6 at entry | 38 | +78.1 |
| 4 | Source = `kimi_signal_tracking` (empty strategy) | 26 | +52.6 |
| 5 | Asset=CRYPTO + Dir=SHORT | 251 | +36.7 |
| 6 | Strategy = `unknown` | 28 | +27.3 |
| 7 | Asset=ETF + Dir=LONG | 63 | +12.1 |
| 8 | Strategy = `crypto_bayesian_regime_transition_momentum_v1` | 34 | +5.2 |
| 9 | Asset=FOREX + Dir=LONG | 382 | +3.2 |
| 10 | Strategy = `st_rsi_momentum_confluence` | 88 | +2.5 |

**Best single 2-axis filter:** `R:R < 0.6 OR strategy=claude_gainer_1h` — saves +166 PnL pts on 91 picks (2.6% of book).

---

## Estimated cumulative impact

Apply: **top 15 toxic strategies + top 20 toxic pairs + toxic dir-asset triples + R:R<0.6**.

| Metric | Original | After blocks | Delta |
|--------|---------:|-------------:|------:|
| Picks | 3,500 | 1,525 (kept) | -56.4% (1,975 blocked) |
| Total PnL | +1,344.4% | +1,502.7% | **+158.3 pts** |
| WR | 48.8% | 56.5% | **+7.7pp** |

Note: 56% of book gets blocked because the `CRYPTO/SHORT` and `FOREX/LONG` triples are large (251 + 382). Trade-off: block-list is aggressive; consider gating only when triple AND another negative axis (e.g., R:R<1.5) co-occur.

### Less-aggressive alternative (strategy + pair + R:R only)

| Metric | Original | After blocks | Delta |
|--------|---------:|-------------:|------:|
| Block list | claude_gainer_1h + kimi_signal_tracking + unknown + 4 toxic strats + top 20 pairs + R:R<0.6 | | |
| Picks blocked | ~340 | (~10% of book) | |
| Est PnL saved | ~+260 pts (sum of strategy + pair + R:R items, less overlap) | | |

---

## Smoking guns to fix at the source

1. **`kimi_signal_tracking` integration is broken.** All 29 picks have empty `strategy` field, all FOREX/EQUITY use `direction=BUY` (wrong vocabulary), `confidence=9.9999` (10x scaling bug — should be 0.99), `rr_ratio=None`, all 26 BUYs return -52.6% PnL collectively. **Block source-level until FOREX direction normalization + confidence rescale fixed.**

2. **`claude_gainer_1h` ships chronically negative R:R.** Top 4 worst absolute losses in the entire 3,500-pick book are this strategy: -46.8% (FF), -23.8% (MMT), -20.8% (MMT), -12.3% (VANRY) — all conf=0.90 but R:R between 0.05 and 0.46. The strategy generates entries far above SL distance to TP. Either fix R:R generator or block.

3. **`st_fear_greed_contrarian` symbol-agnostic broken.** 4 separate symbols (ATOM/LTC/APT/SUI/UNI) all in worst-20 pairs list. Strategy itself isn't in worst-15 because total volume hides per-symbol bleed. Recommend pair-level blocks for all listed symbols.

4. **CRYPTO SHORT structural bleed.** `luxalgo_confluence` SHORTs are -18.2 over 88 trades (38.6% WR). The codebase memory note "feedback_long_source_bias" documents 7 sources are 99-100% LONG-only — luxalgo's SHORTs are forced inversion that doesn't work. Block luxalgo SHORTs explicitly.

5. **Strategy concentration warning is uncorrelated with edge.** Warning=True picks (n=574) have WR 49.7% vs Warning=False 48.6% (delta +1.1pp, basically noise). Either the warning threshold is wrong or the metric isn't predictive — investigate before relying on it for risk gating.

---

## Recommended config additions

```yaml
BLOCKED_STRATEGIES:
  - claude_gainer_1h
  - crypto_bayesian_regime_transition_momentum_v1
  - st_fear_greed_contrarian   # symbol-agnostic broken
  - unknown                     # placeholder bug
  # NOTE: must run docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md
  #       + docs/MUTATION_THREE_AXIS_PROTOCOL.md before adding to BLOCKED_SOURCE_SYSTEMS

BLOCKED_SOURCE_SYSTEMS:
  - kimi_signal_tracking        # fix conf scaling + direction normalization first

BLOCKED_ASSET_STRATEGY_PAIRS:
  # See section 4, top 20 list

BLOCKED_DIRECTION_TRIPLES:
  - {asset_class: CRYPTO, direction: SHORT, except_strategies: [dna_winner, proven_short_specialists]}
  - {asset_class: ETF, direction: LONG}

ENTRY_GATES:
  min_rr_ratio: 0.6   # blocks 38 picks, saves +78 pts
  # consider 1.0 (saves +90, blocks 71) if conservative

CONFIDENCE_TRAPS:
  COMMODITY: avoid [0.65, 0.75]
  EQUITY:    avoid [0.60, 0.65]
  FOREX:     avoid [0.60, 0.65], [0.70, 0.75], conf>=1.0 (bug)
```

---

*Generated by forensic loser-anatomy scan, n=3,500 resolved picks, snapshot 2026-04-17 01:51 UTC.*
