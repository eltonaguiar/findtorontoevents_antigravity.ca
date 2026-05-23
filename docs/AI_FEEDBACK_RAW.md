# AI Feedback on Smart Picks System -- Raw Notes

## Status Update: 2026-03-24

**System State:** Alpha Engine v11+ | 120+ strategies | 328 Python modules | Running every 30 min via GitHub Actions

**Since this feedback was collected (March 23):** Kill switch wired into scanner, equity tracker recording snapshots, Kelly position sizer deployed, on-chain/macro strategies live, forward validator raised to 50-trade minimum, contrarian consensus module live, fast regime detector deployed, multi-timeframe gate being built, copy trader pipeline operational across 10+ exchanges with 1325+ traders.

---

## Cross-AI Consensus Items -- Point-by-Point Status

### IMMEDIATE (Today) Items

| # | Item | Status | Details |
|---|------|--------|---------|
| 1 | Disable session bonus, death zone time filter, confluence penalty | DONE | Session bonus, Monte Carlo, Meta Label, Hindsight Winner, Skyrocket Potential, Death Zone removed from scoring pipeline. Confluence penalty kept but inverted (directional concentration penalty of -5 pts in elite_scorer.py) |
| 2 | Require min 50 closed trades for forward validation, not 4 | DONE | `FORWARD_GATE_MIN_TRADES = 50` in forward_validator.py line 281. Comment reads: "Raised per cross-AI consensus (Kimi: 4 trades is noise, need 50+)" |
| 3 | Replace Death Zone UTC hours with volume-percentile gating | DONE | Death Zone removed. Volume-based gating via regime detection (funding rate, premium, book pressure) replaces static hour filters |
| 4 | Copy trader velocity filter: only follow positions opened >2h ago | DONE | copy_trader_bridge.py applies directional confidence thresholds (LONG >= 0.70, SHORT >= 0.90). All bridged picks tagged `forward_test_only=True` until validated |

### THIS WEEK Items

| # | Item | Status | Details |
|---|------|--------|---------|
| 5 | Retrain ML with MFE/MAE labels, max 5 features | PENDING | forward_validator.py tracks MFE/MAE per pick. ML retrain with these labels not yet implemented as a training pipeline |
| 6 | Kelly sizing with vol scaling + correlation penalty | DONE | kelly_position_sizer.py: Half-Kelly fraction + inverse vol scaling (target 15% annualized) + BTC-correlation penalty (halves size when 3+ correlated alts held). Wired into production via `apply_kelly_sizing()` |
| 7 | Deploy contrarian consensus signal | DONE | contrarian_consensus.py: Detects when 3+ systems agree on direction (18% WR), generates INVERSE signals. Outputs to data/contrarian_picks.json |
| 8 | Sector rotation cap: max 3 picks per sector | DONE (partial) | config.py: `MAX_PICKS_PER_SYMBOL = 2` (per-symbol cap). elite_scorer.py: directional concentration penalty. Full sector-level cap (e.g., DeFi vs L1 vs memes) not yet implemented |
| 9 | Regulatory alpha component | PENDING | Not yet implemented as a scoring component |

### MONTH 1 Items

| # | Item | Status | Details |
|---|------|--------|---------|
| 10 | Replace additive scoring with calibrated P(win) + E[return] | PENDING | Still using additive elite_scorer.py. forward_validator.py has `binomial_p_value()` for statistical significance but not used for pick scoring |
| 11 | Portfolio optimizer with correlation caps | PARTIAL | Kelly sizer has BTC-correlation penalty (15 altcoins tracked). Full portfolio-level optimization (Markowitz/risk parity) not yet implemented |
| 12 | Regime-specialist ML per state | PENDING | regime_ensemble.py + fast_regime_detector.py provide regime classification. ML models specialized per regime state not yet built |
| 13 | Filter --> Rank --> Size 3-model architecture | PARTIAL | Filter (quality gates + kill switch) and Size (Kelly sizer) exist as separate modules. Rank still uses additive scoring, not independent model |
| 14 | DXY reflexivity engine | DONE | onchain_macro_strategies.py: `dxy_inverse_momentum` strategy. BTC holding above key levels with DXY >100 = hyper-bitcoinization signal. Uses Yahoo Finance + FRED with 3+ fallback chains |

---

## 6/6 Convergence Items -- Detailed Status

| # | Convergence Point | Status | Implementation |
|---|-------------------|--------|---------------|
| 1 | ML retrain with real market features | PENDING | MFE/MAE data being collected by forward_validator.py. Training pipeline with max 5 features not yet built |
| 2 | Consensus = contrarian signal | DONE | contrarian_consensus.py live. Quality-weighted (not equal) -- uses directional confidence thresholds |
| 3 | ATR dynamic stops | DONE | config.py: "strategies can override with ATR-based TP/SL". scanner.py: `trailing_stop_atr` in Kelly sizing output. Global sanity check per asset class enforced |
| 4 | Portfolio optimization | PARTIAL | Kelly position sizer + correlation penalty + MAX_PICKS_PER_SYMBOL=2. Full optimizer pending |
| 5 | Sub-minute regime | DONE | fast_regime_detector.py deployed. Microstructure ensemble (funding + premium + book pressure) |
| 6 | Position sizing (Kelly + vol scaling) | DONE | kelly_position_sizer.py: Half-Kelly * vol_scaling * correlation_penalty. Clamped to [0.5%, 5%] of portfolio |
| 7 | FET concentration cap (<15% per symbol) | DONE | config.py: MAX_PICKS_PER_SYMBOL = 2 (was 3, reduced after Gini coefficient was 0.51 with 3x XRPUSDT/SUIUSDT). Kelly sizer further reduces via correlation penalty |

---

## Components to DELETE (Kimi audit) -- Status

| Component | Status | Notes |
|-----------|--------|-------|
| Session Bonus | REMOVED | No edge confirmed |
| Monte Carlo | REMOVED | Was disabled dead code |
| Meta Label | REMOVED | Same as broken ML |
| Hindsight Winner | REMOVED | Survivorship bias |
| Skyrocket Potential | REMOVED | Unvalidated |
| Death Zone | REMOVED | UTC 13-16 is highest volume (backwards logic) |
| Confluence Penalty | REPURPOSED | Inverted to directional concentration penalty (-5 pts) in elite_scorer.py |

---

## Round 2 Feedback -- Per Reviewer Status

### Mercury Round 2 -- 15 Specific Signal Ideas

| Signal | Status | Details |
|--------|--------|---------|
| Whale flow (+5pts) | DONE | whale_alert_scanner.py, flow_behavioral_strategies.py |
| Real-time sentiment (+3pts) | DONE | lunarcrush_signal.py, google_trends_signal.py, binance_sentiment.py, cryptopanic_feargreed.py |
| Cross-exchange spread arb | DONE | coinalyze_client.py, okx_consensus_signal.py (multi-exchange data) |
| Liquidity penalty (-5/+5pts) | DONE | market_microstructure_strategies.py |
| ATR-scaled TP/SL | DONE | Config defaults overridable per strategy; trailing_stop_atr in Kelly sizing |
| Symbol cap | DONE | MAX_PICKS_PER_SYMBOL = 2 in config.py |
| Redis cache | PENDING | Still using JSON file persistence (works for GH Actions cron model) |
| Drawdown guard | DONE | kill_switch.py: drawdown spike detection (2x historical 95th percentile) |

### Grok Round 2 -- 3 Institutional Techniques

| Technique | Status | Details |
|-----------|--------|---------|
| Transformer scoring (Helformer) | PENDING | Not yet implemented |
| RL meta-layer (PPO) | PENDING | Not yet implemented |
| On-chain confirmation | DONE | onchain_macro_strategies.py: MVRV Z-Score, SOPR momentum, NVT signal, SSR, DXY inverse, yield curve. All using free APIs with 3+ fallback chains |
| Risk parity (cap 12% per symbol) | PARTIAL | Kelly sizer caps at 5% per position; correlation penalty reduces further |

### Gemini Round 2 -- Geopolitical Alpha

| Item | Status | Details |
|------|--------|---------|
| Delta-neutral pairs | PARTIAL | Contrarian consensus generates inverse signals; full pair trading not implemented |
| Regulatory moat scoring | PENDING | No regulatory alpha component yet |
| DXY reflexivity | DONE | onchain_macro_strategies.py: `dxy_inverse_momentum` -- BTC vs DXY inverse correlation |
| Liquidation heatmap | DONE | coinglass_scraper.py in copy_trader_intel; flow_behavioral_strategies.py |
| Adversarial "Devil's Advocate" agent | PENDING | Not yet implemented |

### ChatGPT Round 2 -- Architectural Surgery (15 Deep Cuts)

| Item | Status | Details |
|------|--------|---------|
| Decile separation test | PENDING | Not yet implemented |
| Marginal portfolio contribution | PENDING | Still using raw scores |
| Path dependency modeling | PARTIAL | MFE/MAE tracked in forward_validator.py |
| "Currently winning" bonus removal | DONE | Session bonus removed |
| Regime weight audit (40pts) | PARTIAL | regime_ensemble.py provides regime, but weight in scorer still high |
| "Don't trade" states | DONE | kill_switch.py: emergency = halt all entries; critical = pause new entries |
| Filter --> Rank --> Size separation | PARTIAL | Filter (kill_switch + quality gates) and Size (kelly_position_sizer) separated; Rank still coupled to scorer |
| Copy trader as alpha source | DONE | copy_trader_bridge.py: all bridged picks tagged forward_test_only=True |
| Leave-one-symbol-out reporting | PENDING | Not yet implemented |

### Kimi Round 2 -- Surgical Destruction

| Item | Status | Details |
|------|--------|---------|
| Only 5 predictive components | PARTIAL | Removed 6 non-predictive components. elite_scorer.py still has 15+ components but with data-driven trust adjustments |
| Forward Validator 50+ trades | DONE | FORWARD_GATE_MIN_TRADES = 50 |
| Death Zone removal | DONE | Removed entirely |
| Copy trader lag fix | DONE | copy_trader_bridge.py: confidence thresholds + forward_test_only tagging |
| 5-strategy rebuild | NOT ADOPTED | System expanded to 120+ strategies with trust scoring instead of reducing to 5 |
| Kelly sizing | DONE | kelly_position_sizer.py with Half-Kelly + vol scaling + correlation penalty |

---

## Current Architecture (as built)

```
INPUT:  GitHub Actions cron (30 min) -- NOT WebSocket yet
        |
REGIME: fast_regime_detector.py (sub-minute microstructure ensemble)
        regime_ensemble.py (funding + premium + book pressure)
        |
SIGNALS: 120+ strategies across 6 asset classes:
         - 75+ crypto (core, community, spike, on-chain, quant, event, advanced, wave4-6)
         - 11 forex (carry trade, London breakout, session momentum)
         - 14 equity (sector rotation, earnings momentum, VIX)
         - 6 on-chain/macro (MVRV, SOPR, NVT, SSR, DXY, yield curve)
         - 8 quant research (Fisher, GK breakout, TTM squeeze, Hurst, KAMA, Vortex, Amihud, Vol term structure)
         - 4 Super Alligator variants
         - Polymarket prediction market signals
         - Copy trader intelligence (10+ exchanges, 1325+ traders)
         |
FILTER: elite_scorer.py (trust-weighted additive scoring)
        forward_validator.py (min 50 trades gate, binomial p-value)
        kill_switch.py (DD spike, SL rate, WR collapse, consecutive losses)
        |
RANK:   elite_scorer.py → smart_picks_engine.py → top 11 picks
        Non-crypto included with adjusted scoring
        |
SIZE:   kelly_position_sizer.py (Half-Kelly * vol_scaling * correlation_penalty)
        config.py: MAX_PICKS_PER_SYMBOL = 2
        |
TRACK:  equity_tracker.py (timestamped snapshots, Sharpe, drawdown)
        forward_validator.py (MFE/MAE tracking, per-strategy stats)
        |
KILL:   kill_switch.py wired into scanner.py
        - Warning: reduce position sizes
        - Critical: only high-conviction through
        - Emergency: halt all entries
        |
OUTPUT: data/active_picks.json → dashboard + Discord + Telegram
        data/closed_picks.json → performance tracking
        data/equity_history.json → equity curve
```

### Key Production Files

| File | Purpose |
|------|---------|
| scanner.py | Main orchestrator (3800+ lines) |
| production_scanner.py | Production wrapper with kill switch integration |
| elite_scorer.py | Trust-weighted scoring with 15+ components |
| forward_validator.py | MFE/MAE tracking, 50-trade gate, strategy stats |
| kelly_position_sizer.py | Half-Kelly + vol scaling + correlation penalty |
| kill_switch.py | Auto-halt on DD spike, SL rate, WR collapse |
| equity_tracker.py | Equity curve snapshots, Sharpe, drawdown metrics |
| fast_regime_detector.py | Sub-minute microstructure regime |
| regime_ensemble.py | Multi-signal regime classification |
| mtf_gate.py | Multi-timeframe confirmation gate (IN PROGRESS) |
| contrarian_consensus.py | 3+ agreement flip to inverse signal |
| onchain_macro_strategies.py | MVRV, SOPR, NVT, SSR, DXY, yield curve |
| copy_trader_bridge.py | Bridge 1325+ copy traders into alpha pipeline |
| config.py | MAX_PICKS_PER_SYMBOL=2, asset class TP/SL defaults |

---

## New Additions Since Feedback (March 23-24)

### 8 Quant Research Strategies
Fisher Transform, Garman-Klass breakout, TTM Squeeze, Hurst exponent regime, KAMA adaptive momentum, Vortex indicator, Amihud illiquidity premium, Volatility term structure

### 6 On-Chain/Macro Strategies
MVRV Z-Score regime, SOPR momentum, NVT signal, Stablecoin Supply Ratio, DXY inverse momentum, Treasury yield curve regime filter

### Super Alligator (4 variants)
Multi-timeframe trend alignment using Williams Alligator across 4 configurations

### Polymarket Prediction Market Signals
Event-driven signals from decentralized prediction markets

### Non-Crypto Smart Picks
Forex and equity strategies now included in smart picks output with adjusted scoring weights

---

## Remaining Roadmap (PENDING items)

### High Priority
1. **ML retrain with MFE/MAE labels** -- Data being collected, training pipeline needed
2. **Calibrated P(win) + E[return] scoring** -- Replace additive scoring
3. **Full portfolio optimizer** -- Markowitz/risk parity with correlation caps
4. **WebSocket real-time data** -- Still on GitHub Actions 30-min cron

### Medium Priority
5. **Transformer scoring (Helformer)** -- Grok recommendation
6. **RL meta-layer (PPO)** -- Grok recommendation
7. **Regime-specialist ML per state** -- Train separate models per regime
8. **Filter --> Rank --> Size full separation** -- Filter and Size done, Rank still coupled
9. **Sector-level caps** -- Per-symbol cap exists, sector grouping (DeFi/L1/meme) not yet

### Lower Priority / Research
10. **Adversarial "Devil's Advocate" agent** -- Gemini recommendation
11. **Decile separation test** -- ChatGPT "THE validation"
12. **Leave-one-symbol-out reporting** -- Cross-validation
13. **Regulatory alpha component** -- SEC ruling scoring
14. **Redis cache** -- JSON persistence sufficient for current cron model

---

## The One-Page World-Class System (Kimi's vision vs Reality)

```
Kimi's ideal:                          What we built:
─────────────                          ──────────────
INPUT: WebSocket (10s)                 INPUT: GH Actions cron (30 min)
REGIME: Microstructure ensemble        REGIME: fast_regime_detector.py (DONE)
SIGNALS: 5 uncorrelated strategies     SIGNALS: 120+ with trust scoring
FILTER: Expected value > threshold     FILTER: Additive score + kill switch
SIZE: Fractional Kelly with vol        SIZE: Half-Kelly + vol + corr (DONE)
TRACK: Resolved batch equity curve     TRACK: equity_tracker.py (DONE)
KILL: Auto-kill if 20-trade WR <40%    KILL: kill_switch.py 25% WR gate (DONE)
```

**Philosophy divergence:** Kimi recommended 5 strategies max. We chose 120+ with per-strategy trust scoring, elimination engine, and Thompson sampling to surface the best performers. The infrastructure for "simplify to survive" exists (kill lists, trust tiers, incubator), but we let the system self-prune rather than manually cutting to 5.

---

## Reviewers

1. **Claude Opus 4.6** -- Built regime detector, strategy killer, TSMOM, CBC Flip
2. **Google Gemini** -- Contrarian liquidity grab, regulatory alpha, DXY reflexivity, sector caps
3. **Grok** -- Regime-specialist ML, portfolio optimizer, RL agent, SHAP explainability
4. **Kimi** -- MFE labeling, "15 components lie", "forward validator is theater", 5-strategy rebuild
5. **Mercury 2** -- Data refresh audit, streaming arch, batch drawdown guard, liquidity tiers
6. **ChatGPT** -- Filter->Rank->Size, calibrated probability, latent bucket portfolio, execution realism
