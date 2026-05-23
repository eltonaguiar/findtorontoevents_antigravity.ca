# Strategy / Copytrader / Prediction-Market Inventory — 2026-05-18

**Goal:** a clear at-a-glance inventory of every strategy (per asset class), every
copytrader source, and every prediction-market source — what each one IS, what it
does, and how it performs.

**Canonical data:** `audit_dashboard/data/pf_registry.json`
(`by_asset_class_strategy_policy_clean_net` view, generated 2026-05-19T02:18Z —
policy-clean, net-of-slippage, deduped). Cross-ref:
`reports/PER_CLASS_CANDIDATE_TRADES_2026-05-18.md`,
`reports/MAGIC_FILTER_HUNT_2026-05-18.md`,
`audit_trail/quality_gates.py` (`BLOCKED_SOURCE_SYSTEMS`, blacklists).

## How to read this

- **n / PF / WR** are the policy-clean-net registry numbers — the verdict-grade view.
  Raw `closed_picks.json` is NOT used (pnl-unit-mismatch trap).
- **PF=UNDEF (no losses)** = the strategy has only winning rows in the clean ledger.
  At n<5 this is **statistically meaningless** — it means "too few trades to have a
  loss yet", not "perfect". Treated as NEUTRAL/insufficient, never as edge.
- **Verdict** — blunt call per entry:
  - **CONTRIBUTING** — real positive PF, n large enough to mean something (n≥30,
    PF≥1.3, no artifact pattern).
  - **NEUTRAL** — too few trades to judge (n<15) OR PF≈1.0; neither helps nor hurts.
  - **DRAGGING** — negative PF (loses money) OR a flagged artifact masquerading as edge.
  - **ARTIFACT** — headline metric is a statistical illusion (placeholder stats,
    near-zero-avg-loss, COT look-ahead leakage, single-giant-win). Always also DRAGGING
    in practice because it pollutes aggregates.

### Artifact families flagged in this inventory

| Family | Pattern | Why it is fake |
|---|---|---|
| `ml_enhanced_<SYM>_<tf>_<letter>_<model>` | ~270 micro-cohorts; the n≥19 ones show PF 1.2–53, WR 57–97% | Placeholder-stat family. Near-zero avg-loss inflates PF; insane W/L ratios (FET 7.0, DYDX 2.0). n=1 for the vast majority. **Excluded from all candidate sets.** |
| `cot_positioning` / `multi_asset_cot` / `multi_asset_copytrader` on CT=F | 70–78% WR, PF 2.8–4.7 on cotton | COT look-ahead leakage (CFTC data not available at decision time). Strip CT → COMMODITY = PF 0.23. Gate M-095 blocks `cot_positioning`. |
| `UNKNOWN` n=24 PF 145 (CRYPTO) | one giant win, WR 4.2% | Single-giant-win placeholder. Not tradeable. |
| `EmaRibbon` n=2 PF 367, `futures_connors_rsi2` n=136 PF 613666 | absurd PF magnitudes | Unit-corruption / placeholder. `futures_connors_rsi2`'s +19M pnl% is a broken-unit row, NOT real. |
| `smart_money_consensus` n=667 PF 16.5 WR 82.5% (EQUITY) | +7039 pnl% on 667 trades | Implausible for equity; near-zero-avg-loss placeholder pattern. Treat as artifact pending resolver audit — non-crypto resolution is the known-broken P0. |

> **Big-picture caveat.** Non-crypto forward-resolution is broken (UNCLAIMED P0):
> picks are emitted but rarely resolved to WON/LOST. So EQUITY/ETF/FUTURES/COMMODITY/
> BOND policy-clean cohorts are tiny and the few large-PF ones are almost all
> placeholder/unit artifacts. The only asset class with enough clean volume to
> judge strategies honestly is **CRYPTO**.

---

## 1. PER-STRATEGY INVENTORY (by asset class)

### CRYPTO — 208 strategy cohorts (the only class with real volume)

Top of the table — strategies that survive the artifact screens, ranked by PF:

| Strategy | What it is | n | PF | WR | Verdict |
|---|---|---|---|---|---|
| `mega_mutation` | DNA-mutated genetic strategy (best survivor of the mutation engine) | 72 | 2.19 | 56.9% | **CONTRIBUTING** — only n≥30 / PF≥1.5 slice that survives every concentration + artifact screen (27 distinct days, top symbol AVAX 17%, W/L 1.66). Marginal — n=72 has wide CI; size small + monitor. |
| `ensemble` | Multi-signal ensemble aggregator | 410 | 1.47 | 41.5% | **NEUTRAL** — most data, but PF 1.47 below 1.5 bar; harness showed zero per-window separation = volume not edge. Regime-dependent profit. |
| `st_fear_greed_contrarian` | Contrarian entries on fear/greed extremes | 155 | 1.09 | 51.0% | **NEUTRAL** — PF barely >1; a single-day cohort (05-17) is itself an artifact. |
| `st_rsi_vol_bounce` | RSI + volume bounce setup | 15 | 2.18 | 53.3% | **NEUTRAL** — promising PF but n=15 too small. |
| `crypto_soc_micro_noise_filter_a09_v1` | Social-microstructure noise filter | 18 | 2.63 | 61.1% | **NEUTRAL** — speculative, n=18. |
| `crypto_liquidity_wick_reversal_v1` | Liquidity-wick reversal | 36 | 1.10 | 52.8% | **NEUTRAL** — PF≈1, no edge. |
| `atr_percentile_gate` | ATR-percentile volatility gate | 29 | 1.10 | 58.6% | **NEUTRAL** — PF≈1. |
| `multi_period_rsi_confluence_eth` | Multi-timeframe RSI confluence (ETH) | 26 | 1.08 | 46.2% | **NEUTRAL**. |

CRYPTO **artifacts** (excluded from edge — headline PF is fake):

| Strategy | n | PF | WR | Verdict |
|---|---|---|---|---|
| `UNKNOWN` | 24 | 145.07 | 4.2% | **ARTIFACT** — one-giant-win, WR 4%. |
| `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` | 31 | 53.44 | 96.8% | **ARTIFACT** — near-zero-avg-loss placeholder. |
| `ml_enhanced_BNBUSDT_15m_B_lightgbm` | 19 | 52.58 | 89.5% | **ARTIFACT** — ml_enhanced family. |
| `ml_enhanced_INJUSDT_1d_B_lightgbm` | 28 | 40.98 | 96.4% | **ARTIFACT** — ml_enhanced family. |
| `ml_enhanced_FETUSDT_1d_B_lightgbm` | 44 | 9.25 | 56.8% | **ARTIFACT** — insane W/L 7.0. |
| `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` | 47 | 3.80 | 61.7% | **ARTIFACT** — ml_enhanced family. |
| `ml_enhanced_STRKUSDT_15m_D_ensemble_stack` | 29 | 3.48 | 89.7% | **ARTIFACT** — ml_enhanced family. |
| `ml_enhanced_RENDERUSDT_4h_D_ensemble_stack` | 37 | 2.06 | 56.8% | **ARTIFACT** — ml_enhanced family. |
| `ml_enhanced_XRPUSDT_1d_D_ensemble_stack` | 28 | 1.76 | 60.7% | **ARTIFACT** — ml_enhanced family. |
| `ml_enhanced_FETUSDT_15m_B_lightgbm` | 29 | 1.18 | 62.1% | **ARTIFACT** — ml_enhanced family. |
| ~260 more `ml_enhanced_*` cohorts at n=1 (PF 0.00 or UNDEF) | 1 | — | — | **ARTIFACT** — placeholder family, ignore. |

CRYPTO **draggers** (real negative PF, lose money):

| Strategy | n | PF | WR | Verdict |
|---|---|---|---|---|
| `sell_the_rally` | 8 | 0.00 | 0.0% | **DRAGGING** — 0% WR, -39% pnl. |
| `ema_stack` | 7 | 0.00 | 0.0% | **DRAGGING** — -36% pnl. |
| `connors_rsi2` (crypto) | 7 | 0.00 | 0.0% | **DRAGGING** — -24% pnl. |
| `system_b_standalone` | 7 | 0.00 | 0.0% | **DRAGGING** — -32% pnl (also blocked as `ml_bg_system_b`). |
| `rapid_fire` | 91 | 0.37 | 33.0% | **DRAGGING** — biggest-n loser, -13% pnl. |
| `fibonacci_retracement` | 5 | 0.00 | 0.0% | **DRAGGING** — -16% pnl. |
| `st_momentum_compression` | 5 | 0.47 | 20.0% | **DRAGGING** — -6.5% pnl. |
| `copy_trader_clones` | 34 | 0.78 | 44.1% | **DRAGGING** — see Copytrader table. |
| `copy_trader_intel` | 32 | 0.00 | 0.0% | **DRAGGING / ARTIFACT** — see Copytrader table. |
| `seasonal_factor_rotation` | 21 | 0.63 | 28.6% | **DRAGGING**. |
| `fractal_sr_bounce` | 24 | 0.78 | 25.0% | **DRAGGING**. |
| `ml_breakout` | 21 | 0.00 | 0.0% | **DRAGGING** — also blocked as `breakout_b_ml`. |
| ~40 more at n<15, PF 0.0–0.75 | — | — | — | **DRAGGING / NEUTRAL** — small-n losers. |

### EQUITY — 38 strategy cohorts (resolution-starved; treat large PF as suspect)

| Strategy | What it is | n | PF | WR | Verdict |
|---|---|---|---|---|---|
| `smart_money_consensus` | Equity smart-money consensus aggregator | 667 | 16.55 | 82.5% | **ARTIFACT** — +7039 pnl% on 667 trades is implausible for equity; placeholder/resolution artifact. Do NOT treat as edge. |
| `EmaRibbon` | EMA-ribbon trend | 2 | 366.76 | 50.0% | **ARTIFACT** — n=2, absurd PF. |
| `MomentumFactor` | Momentum factor | 3 | 14.74 | 66.7% | **NEUTRAL** — n=3. |
| `stocks_ema_golden_cross` | EMA golden-cross on stocks | 44 | 9.26 | 70.5% | **NEUTRAL→suspect** — PF 9.26 on n=44 is high for equity; likely resolution-inflated. Needs walk-forward before trusting. |
| `connors_rsi2` (equity) | Connors RSI-2 mean reversion | 11 | 5.42 | 54.5% | **NEUTRAL** — n=11. |
| `signal_recorder` | Passive signal logger (not a trader) | 41 | 1.85 | 51.2% | **NEUTRAL** — recorder, not a live strategy. |
| `regime_*` family (mild_bull/strong_bear/accumulation/...) | Regime-tagged buckets | 1–5 each | 0.5–3.0 | varies | **NEUTRAL** — all n≤5; regime tags, not strategies. |
| `cta_cross_asset_tsmom` (equity) | Cross-asset TSMOM | 5 | 1.18 | 80.0% | **NEUTRAL** — n=5. |
| `contrarian_consensus_flip` | Inverse-consensus | 3 | 0.00 | 0.0% | **DRAGGING** — -66% pnl on n=3. |
| `multi_sigma_reversal` | Multi-sigma reversal | 1 | 0.00 | 0.0% | **DRAGGING** — -10% pnl. |
| `regime_mild_bear` | regime bucket | 4 | 0.54 | 25.0% | **DRAGGING**. |
| 14 cohorts at n=1 PF=UNDEF (no losses) | — | 1 | — | 100% | **NEUTRAL** — n=1, meaningless. |

> EQUITY policy-clean class baseline (Magic-Filter Hunt) is **n=5, PF 0.35** — the
> registry's strategy view rows are mostly the *pre-block / unresolved* residue.
> No real EQUITY edge exists. `stocks_competition`, `goldmine_stocks` already blocked.

### ETF — 21 strategy cohorts (resolution-starved)

| Strategy | What it is | n | PF | WR | Verdict |
|---|---|---|---|---|---|
| `regime_mild_bull` | Regime bucket | 6 | 42.14 | 83.3% | **ARTIFACT** — n=6, absurd PF. |
| `leveraged_etf_decay` | Short leveraged-ETF decay | 4 | 19.47 | 50.0% | **NEUTRAL** — n=4; thesis sound but no data. |
| `signal_recorder` | Passive logger | 4 | 1.98 | 75.0% | **NEUTRAL** — recorder. |
| `unknown` | Untagged | 6 | 1.57 | 50.0% | **NEUTRAL** — n=6, untagged. |
| `connors_rsi2` (ETF) | Connors RSI-2 | 11 | 0.25 | 18.2% | **DRAGGING** — -44.76 pnl, 18% WR. |
| `BettingAgainstBeta` | BAB factor | 3 | 0.00 | 0.0% | **DRAGGING** — -22.67 pnl. |
| 11 cohorts at n=1 PF=UNDEF | — | 1 | — | 100% | **NEUTRAL** — n=1. |

> ETF class baseline n=87-ish raw but only ~30 clean; no n≥15 non-artifact winner.

### FOREX — 32 strategy cohorts

| Strategy | What it is | n | PF | WR | Verdict |
|---|---|---|---|---|---|
| `ig_contrarian_sentiment` | Fades IG retail-sentiment positioning | 246 | 44.68 | 96.3% | **ARTIFACT** — PF 44 / WR 96% is a near-zero-avg-loss placeholder pattern. Not real edge. |
| `non_crypto_consensus` | Multi-source non-crypto consensus | 27 | 14.79 | 81.5% | **ARTIFACT/NEUTRAL** — PF 14.8 implausible; resolution-inflated. |
| `cta_replicator` | CTA-style trend replication | 95 | 2.69 | 66.3% | **NEUTRAL (fails concentration)** — 86% USDJPY; it's a single-pair bet, not a filter. Not a portfolio edge. |
| `signal_recorder` | Passive logger | 14 | 2.04 | 71.4% | **NEUTRAL** — recorder. |
| `MeanReversionBB` | Bollinger mean reversion | 5 | 1.81 | 80.0% | **NEUTRAL** — n=5. |
| `multi_asset_copytrader` | Multi-asset copytrade (FX slice) | 25 | 1.42 | 52.0% | **NEUTRAL** — PF 1.42, n=25; see Copytrader table. |
| `alpha_engine` | Core alpha engine (FX slice) | 13 | 1.07 | 46.2% | **NEUTRAL** — PF≈1. |
| `cta_cross_asset_tsmom` (FX) | Cross-asset TSMOM | 52 | 0.43 | 65.4% | **DRAGGING** — -12.38 pnl despite 65% WR (small wins, big losses). |
| `multi_asset_scanner` (FX) | Multi-asset scanner | 11 | 0.21 | 9.1% | **DRAGGING**. |
| `fx_smart_forex_rsi2_mean_reversion` | FX RSI-2 mean reversion | 4 | 0.07 | 25.0% | **DRAGGING**. |
| `regime_accumulation` / `regime_mild_bull` | regime buckets | 4 each | 0.0–0.06 | low | **DRAGGING**. |
| `contrarian_consensus_flip`, `forex-scanner-live`, `DXYReversal` | inverse / scanner | 3–6 each | 0.00 | 0.0% | **DRAGGING** — all 0% WR. |
| 13 cohorts at n=1–6 PF=UNDEF | — | small | — | 100% | **NEUTRAL** — n too small. |

> FOREX class baseline PF 1.64 (n=144) — but the >1.5 strategies are all artifact
> (`ig_contrarian_sentiment`, `non_crypto_consensus`) or single-pair (`cta_replicator`
> 86% USDJPY). **No diversified FOREX edge.**

### FUTURES — 10 strategy cohorts (resolution-starved)

| Strategy | What it is | n | PF | WR | Verdict |
|---|---|---|---|---|---|
| `futures_connors_rsi2` | Connors RSI-2 on futures | 136 | 613666.95 | 94.9% | **ARTIFACT** — +19M pnl% is a broken-unit row. Garbage, ignore. |
| `signal_recorder` | Passive logger | 20 | 2.48 | 60.0% | **NEUTRAL** — recorder. |
| `cta_golden_cross_200` | 200-day golden cross | 71 | UNDEF | 100% | **ARTIFACT** — n=71 all "wins" / no losses = unresolved-as-win artifact. |
| `cta_cross_asset_tsmom` (futures) | Cross-asset TSMOM | 93 | 0.76 | 47.3% | **DRAGGING** — -78 pnl. |
| `futures_bb_mean_reversion` | Bollinger mean reversion | 63 | 0.30 | 17.5% | **DRAGGING** — -127 pnl. |
| `cftc_cot_commercial_signal` | CFTC COT commercial signal | 117 | 0.04 | 5.1% | **DRAGGING / ARTIFACT** — -571 pnl, COT-family. |
| `multi_asset_scanner` (futures) | Multi-asset scanner | 11 | 0.48 | 9.1% | **DRAGGING**. |
| `non_crypto_consensus` (futures) | Multi-source consensus | 11 | 0.37 | 27.3% | **DRAGGING** — -40 pnl. |

> `futures_momentum` already in `BLOCKED_SOURCE_SYSTEMS` (0% WR, killed 2026-05-06).
> FUTURES class baseline PF 0.96, n=12 clean — sample-starved, no edge.

### COMMODITY — 2 strategy cohorts

| Strategy | What it is | n | PF | WR | Verdict |
|---|---|---|---|---|---|
| `multi_asset_copytrader` | Multi-asset copytrade (COMMODITY slice) | 51 | 1.67 | 56.9% | **ARTIFACT/DRAGGING** — 81% of volume is CT=F (cotton) COT-leakage cohort. Strip CT → COMMODITY PF 0.23. The class's apparent edge IS the artifact. |
| `cta_replicator` | CTA trend replication | 1 | UNDEF | 100% | **NEUTRAL** — n=1. |

### BOND — 1 strategy cohort

| Strategy | n | PF | WR | Verdict |
|---|---|---|---|---|
| `cta_replicator` | 1 | 0.00 | 0.0% | **DRAGGING** — n=1, single loss. No BOND data exists. |

### PENNY_STOCK — 1 strategy cohort

| Strategy | n | PF | WR | Verdict |
|---|---|---|---|---|
| `multi_asset_scanner` | 1 | 0.00 | 0.0% | **DRAGGING** — n=1. No PENNY_STOCK data. |

### UNKNOWN (untagged residue) — 24 cohorts

Untagged asset-class residue, not a real class. Best is `adaptive_vr_confluence`
n=2 PF 15.33 (**ARTIFACT**, n=2). Includes `prediction_market_agents` n=2 PF=UNDEF
(see Prediction-Market table). **Whole class = NEUTRAL** — un-tagged noise.

### BLOCKED / KILLED source systems (from `quality_gates.py::BLOCKED_SOURCE_SYSTEMS`)

Hard-blocked — picks hidden from all views. All **DRAGGING** (that is why they were killed):

`mercury2_fast` (PF 0.02), `stocks_competition` (33.5% WR, -304%),
`fast_stocks_competition`, `ml_bg_system_a` (PF 0.14), `ml_bg_system_b` (PF 0.02),
`ml_bg_system_c` (0% WR), `ml_bg_system_f` (0% WR), `ml_bg_ensemble` (0% WR),
`ml_crypto_pred_v12` (PF 0.55), `crypto_winners` (PF 0.30),
`breakout_b_ml` (0% WR placeholder), `kimi_claw_research` (0% WR placeholder),
`rocket_scanner` (0% WR), `copy_trader_highscore` (PF 0.74 — see Copytrader table),
`goldmine_stocks` (PF 0.03), `multi_asset` (PF 0.32),
`quan_engine_scalp` (25% WR, -353%), `cot_positioning` (COT leakage, M-095),
`futures_momentum` (0% WR). `multi_asset_cot` in `REQUIRES_WALKAHEAD_AUDIT`
(COT over-emission artifact).

---

## 2. COPYTRADER SOURCES

The `copy_trader_intel/` pipeline scrapes ~30 exchange/DEX leaderboards
(Binance, Bybit, Bitget, OKX, BingX, HTX, Gate, dYdX, GMX, Drift, Gains, Dune,
Nansen, Hyperliquid, MyFXbook, eToro, ZuluTrade, etc.) and clones top traders into
pick streams. Sources that reach the canonical ledger:

| Source | What it tracks | Data source | n (clean) | PF / WR | Verdict |
|---|---|---|---|---|---|
| `multi_asset_copytrader` | Non-crypto copytrade (commodity/FX/equity) | `multi_asset_copytrader_scraper.py` | 51 COMM / 25 FX / 2 EQ | COMM 1.67 / FX 1.42 / EQ 0.00 | **DRAGGING (COMMODITY)** — COMM number is 81% CT=F COT-leakage artifact (real PF 0.23). FX slice NEUTRAL. |
| `copy_trader_clones` | Generic cloned top-trader strategies | `strategy_clone_generator.py` | 34 (CRYPTO) | 0.78 / 44.1% | **DRAGGING** — negative PF, loses money. |
| `copy_trader_intel` | Aggregated copytrade intel feed | `copy_trader_intel/main.py` pipeline | 32 (CRYPTO) | 0.00 / 0.0% | **DRAGGING / ARTIFACT** — 0% WR cohort; flagged in PER_CLASS doc as a known artifact. Mostly `clone_hl_copy_*` rows with placeholder/identical-triple stats. |
| `copy_trader_highscore` | Hyperliquid leaderboard SHORT replay | `hyperliquid_scraper.py` | 234 (aggregate) | 0.74 / 31.6% | **DRAGGING — BLOCKED.** 3-axis mutation autopsy found no save axis; 6 symbols with identical +3.50% placeholder stats. In `BLOCKED_SOURCE_SYSTEMS`. |
| `copy_trader_bybit` | Bybit copytrade leaderboard | `bybit_scraper.py` | 5 (CRYPTO) | 0.00 / 0.0% | **DRAGGING** — small-n 0% WR. |
| `copy_trader_bitget` / `copy_trader_binance` / `copy_trader_dune` | Exchange/DEX leaderboards | respective scrapers | 5 / 3 / 1 (verification report) | n/a — no clean-ledger cohort | **NEUTRAL** — too few resolved picks to judge. |
| `clone_hl_copy_*` (Hyperliquid whale clones) | Individual HL whale wallets cloned (e.g. `whale_433roi`, `PensionFund_24M`) | `hyperliquid_scraper.py` + `strategy_clone_generator.py` | folded into `copy_trader_intel` | identical-triple placeholder stats | **DRAGGING / ARTIFACT** — `feedback_clone_hl_placeholder_stats.md`: 100/100/100, 85/85/85.7 placeholder triples. Quarantine before any HC trade. |
| `cta_replicator` / `cta_cross_asset_tsmom` | CTA-style trend replication (not retail copytrade — managed-futures replication) | `cta_strategy_replicator.py` | 95 FX / 93 FUT / 52 FX | FX 2.69 (86% USDJPY) / FUT 0.76 / -0.43 | **NEUTRAL→DRAGGING** — FX `cta_replicator` PF 2.69 fails concentration (single pair); `cta_cross_asset_tsmom` is a real dragger (-78 to -12 pnl). |
| `non_crypto_consensus` | Consensus across copytrade sources for non-crypto | `non_crypto_consensus.py` | 27 FX / 11 FUT / 1 EQ | FX 14.79 / FUT 0.37 | **ARTIFACT (FX)** — PF 14.8 resolution-inflated; **DRAGGING (FUT)**. |

**Copytrader bottom line:** the copytrade program is **net DRAGGING**. Every
copytrade source with a clean-ledger cohort is either negative-PF (`copy_trader_clones`
0.78, `copy_trader_highscore` 0.74, `copy_trader_bybit` 0.00) or an artifact
(`copy_trader_intel` 0% WR, `multi_asset_copytrader` CT=F leakage,
`clone_hl_copy_*` placeholder triples). **Zero copytrade source is a trusted edge.**
`copy_trader_highscore` is already hard-blocked.

---

## 3. PREDICTION-MARKET SOURCES

Modules: `alpha_engine/polymarket_signals.py`, `polymarket_merger.py`,
`polymarket_pmxt.py`, `kalshi_signals.py`, `prediction_market_consensus.py`,
`prediction_market_whales.py`, `prediction_market_agents/` (Polymarket momentum +
Kalshi signal agents), `predictions/scrapers/{polymarket,kalshi}_scraper.py`.

| Source | What it feeds | Data source | n / perf | Wired? | Verdict |
|---|---|---|---|---|---|
| `prediction_market_agents` | Polymarket momentum + Kalshi signal agents → pick stream | Polymarket + Kalshi APIs | n=2 (UNKNOWN class), PF=UNDEF (no losses) | wired into resolver/dashboard path (`quality_gates.py`, `dashboard_generator.py` reference it) | **NEUTRAL** — only 2 resolved picks; statistically nothing. No edge demonstrated. |
| `polymarket_signals` / `polymarket_merger` / `polymarket_pmxt` | Polymarket whale + market-odds signals merged into consensus | Polymarket trade API, PMXT | no distinct clean-ledger cohort | wired (`prediction_market_consensus` imports referenced) | **NEUTRAL** — produces signals but no resolved per-source PF cohort exists. |
| `kalshi_signals` | Kalshi event-contract signals | Kalshi API (`kalshi.log` shows live polling) | no clean-ledger cohort | wired into consensus | **NEUTRAL** — no resolved cohort. |
| `prediction_market_whales` | Tracks large Polymarket wallets | Polymarket on-chain | folded into whale signals | sidecar | **NEUTRAL** — research feed, no isolated perf. |
| `prediction_market_consensus` | Aggregates Polymarket+Kalshi into a consensus signal | upstream PM modules | no clean-ledger cohort | wired (consumer in dashboard path) | **NEUTRAL** — aggregator; no measurable edge yet. |
| Polymarket trader audit (`polymarket_strategy_audit.json`) | Audits Polymarket wallets for copyability | snapshot | focus wallets: `0x8dxd` blocked (hft_micro), `justdance` watch_only | sidecar / research | **NEUTRAL** — all audited wallets are `blocked` or `watch_only`; none promoted to live copy. |

**Prediction-market bottom line:** the prediction-market stack is **wired but NEUTRAL**.
It emits signals into the consensus/dashboard path, but only `prediction_market_agents`
has any resolved picks (n=2, meaningless). No prediction-market source has demonstrated
edge; none is dragging either — it simply has no measurable contribution yet.

---

## 4. MASTER RANKING — best-to-worst PF per asset class

Artifacts and n<5 PF=UNDEF rows are marked; only non-artifact, n≥10 entries are
"real". Verdict legend: ✅ CONTRIBUTING · ➖ NEUTRAL · ❌ DRAGGING · 🎭 ARTIFACT.

### CRYPTO (n≥10, non-artifact, real-ranking)

| Rank | Strategy | n | PF | WR | Verdict |
|---|---|---|---|---|---|
| 1 | `mega_mutation` | 72 | 2.19 | 56.9% | ✅ CONTRIBUTING (only real edge candidate) |
| 2 | `ensemble` | 410 | 1.47 | 41.5% | ➖ NEUTRAL |
| 3 | `crypto_liquidity_wick_reversal_v1` | 36 | 1.10 | 52.8% | ➖ NEUTRAL |
| 4 | `atr_percentile_gate` | 29 | 1.10 | 58.6% | ➖ NEUTRAL |
| 5 | `st_fear_greed_contrarian` | 155 | 1.09 | 51.0% | ➖ NEUTRAL |
| 6 | `multi_period_rsi_confluence_eth` | 26 | 1.08 | 46.2% | ➖ NEUTRAL |
| 7 | `copy_trader_clones` | 34 | 0.78 | 44.1% | ❌ DRAGGING |
| 8 | `fractal_sr_bounce` | 24 | 0.78 | 25.0% | ❌ DRAGGING |
| 9 | `order_book_imbalance` | 13 | 0.76 | 38.5% | ❌ DRAGGING |
| 10 | `seasonal_factor_rotation` | 21 | 0.63 | 28.6% | ❌ DRAGGING |
| 11 | `widened_tp_momentum_carry` | 12 | 0.42 | 16.7% | ❌ DRAGGING |
| 12 | `rapid_fire` | 91 | 0.37 | 33.0% | ❌ DRAGGING (worst large-n) |
| 13 | `autocorrelation_exploiter` | 12 | 0.28 | 25.0% | ❌ DRAGGING |
| 14 | `ml_breakout` | 21 | 0.00 | 0.0% | ❌ DRAGGING |
| 15 | `copy_trader_intel` | 32 | 0.00 | 0.0% | ❌ DRAGGING / 🎭 |
| 16 | `connors_rsi2` | 7 | 0.00 | 0.0% | ❌ DRAGGING |
| 🎭 | `UNKNOWN`, all `ml_enhanced_*` n≥19 | — | 1.2–145 | — | 🎭 ARTIFACT (10 cohorts) |

### FOREX (n≥10, non-artifact)

| Rank | Strategy | n | PF | WR | Verdict |
|---|---|---|---|---|---|
| 1 | `cta_replicator` | 95 | 2.69 | 66.3% | ➖ NEUTRAL (86% USDJPY — not diversified) |
| 2 | `signal_recorder` | 14 | 2.04 | 71.4% | ➖ NEUTRAL (recorder) |
| 3 | `multi_asset_copytrader` | 25 | 1.42 | 52.0% | ➖ NEUTRAL |
| 4 | `alpha_engine` | 13 | 1.07 | 46.2% | ➖ NEUTRAL |
| 5 | `cta_cross_asset_tsmom` | 52 | 0.43 | 65.4% | ❌ DRAGGING |
| 6 | `multi_asset_scanner` | 11 | 0.21 | 9.1% | ❌ DRAGGING |
| 🎭 | `ig_contrarian_sentiment` (246, PF 44.7), `non_crypto_consensus` (27, PF 14.8) | — | — | — | 🎭 ARTIFACT |

### EQUITY (n≥10, non-artifact)

| Rank | Strategy | n | PF | WR | Verdict |
|---|---|---|---|---|---|
| 1 | `stocks_ema_golden_cross` | 44 | 9.26 | 70.5% | ➖ NEUTRAL→suspect (resolution-inflated, needs walk-forward) |
| 2 | `connors_rsi2` | 11 | 5.42 | 54.5% | ➖ NEUTRAL |
| 3 | `signal_recorder` | 41 | 1.85 | 51.2% | ➖ NEUTRAL (recorder) |
| 🎭 | `smart_money_consensus` (667, PF 16.5), `EmaRibbon` (2, PF 367) | — | — | — | 🎭 ARTIFACT |
| ❌ | `contrarian_consensus_flip` (3, PF 0, -66 pnl) | — | — | — | ❌ DRAGGING |

### ETF (n≥10, non-artifact)

| Rank | Strategy | n | PF | WR | Verdict |
|---|---|---|---|---|---|
| 1 | `connors_rsi2` | 11 | 0.25 | 18.2% | ❌ DRAGGING (best n≥10 is still a loser) |
| 🎭 | `regime_mild_bull` (6, PF 42), `leveraged_etf_decay` (4, PF 19.5) | — | — | — | 🎭 ARTIFACT / n<10 |

### FUTURES (n≥10, non-artifact)

| Rank | Strategy | n | PF | WR | Verdict |
|---|---|---|---|---|---|
| 1 | `signal_recorder` | 20 | 2.48 | 60.0% | ➖ NEUTRAL (recorder) |
| 2 | `cta_cross_asset_tsmom` | 93 | 0.76 | 47.3% | ❌ DRAGGING |
| 3 | `multi_asset_scanner` | 11 | 0.48 | 9.1% | ❌ DRAGGING |
| 4 | `non_crypto_consensus` | 11 | 0.37 | 27.3% | ❌ DRAGGING |
| 5 | `futures_bb_mean_reversion` | 63 | 0.30 | 17.5% | ❌ DRAGGING |
| 6 | `cftc_cot_commercial_signal` | 117 | 0.04 | 5.1% | ❌ DRAGGING / 🎭 (worst) |
| 🎭 | `futures_connors_rsi2` (136, PF 613666), `cta_golden_cross_200` (71, UNDEF) | — | — | — | 🎭 ARTIFACT |

### COMMODITY

| Rank | Strategy | n | PF | WR | Verdict |
|---|---|---|---|---|---|
| 1 | `multi_asset_copytrader` | 51 | 1.67 | 56.9% | 🎭 ARTIFACT — 81% CT=F COT leakage; real PF 0.23 |
| — | (no other clean cohort) | — | — | — | — |

### BOND / PENNY_STOCK

Single-row classes (`cta_replicator` BOND n=1 PF 0; `multi_asset_scanner`
PENNY_STOCK n=1 PF 0). **Both ❌ DRAGGING, no data.**

### COPYTRADERS (cross-class)

| Rank | Source | best n | PF | Verdict |
|---|---|---|---|---|
| 1 | `multi_asset_copytrader` (FX slice) | 25 | 1.42 | ➖ NEUTRAL |
| 2 | `copy_trader_clones` | 34 | 0.78 | ❌ DRAGGING |
| 3 | `copy_trader_highscore` | 234 | 0.74 | ❌ DRAGGING — BLOCKED |
| 4 | `copy_trader_intel` | 32 | 0.00 | ❌ DRAGGING / 🎭 |
| 5 | `copy_trader_bybit` | 5 | 0.00 | ❌ DRAGGING |
| — | `multi_asset_copytrader` (COMMODITY) | 51 | 1.67 | 🎭 ARTIFACT (CT=F leakage) |

### PREDICTION MARKETS (cross-class)

| Source | n | PF | Verdict |
|---|---|---|---|
| `prediction_market_agents` | 2 | UNDEF | ➖ NEUTRAL (wired, no edge) |
| `polymarket_signals` / `kalshi_signals` / `prediction_market_consensus` | 0 | — | ➖ NEUTRAL (wired, no resolved cohort) |

---

## 5. EXECUTIVE SUMMARY

**Strategy counts per asset class** (registry `by_asset_class_strategy_policy_clean_net`):

| Class | Strategy cohorts | Top contributor | Worst drag |
|---|---|---|---|
| CRYPTO | 208 | `mega_mutation` (n=72, PF 2.19) — the **only** real edge candidate system-wide | `rapid_fire` (n=91, PF 0.37, -13% pnl) — largest-n real loser; `sell_the_rally`/`ema_stack` 0% WR |
| EQUITY | 38 | none real — `stocks_ema_golden_cross` (PF 9.26) is resolution-suspect | `contrarian_consensus_flip` (n=3, PF 0, -66% pnl) |
| ETF | 21 | none — best n≥10 is `connors_rsi2` PF 0.25 (a loser) | `connors_rsi2` (n=11, PF 0.25, -44.76 pnl) |
| FOREX | 32 | none diversified — `cta_replicator` PF 2.69 is 86% USDJPY (single-pair) | `cftc`/`multi_asset_scanner` (PF 0.21) / `cta_cross_asset_tsmom` (-12.4 pnl) |
| FUTURES | 10 | none — `signal_recorder` PF 2.48 is just a logger | `cftc_cot_commercial_signal` (n=117, PF 0.04, -571 pnl) |
| COMMODITY | 2 | none — `multi_asset_copytrader` PF 1.67 is the CT=F leakage artifact | same — strip CT=F → PF 0.23 |
| BOND | 1 | none | `cta_replicator` (n=1, PF 0) |
| PENNY_STOCK | 1 | none | `multi_asset_scanner` (n=1, PF 0) |
| UNKNOWN | 24 | none — untagged residue | n/a |

**Artifact count:** roughly **280+ entries are artifacts** — dominated by the
`ml_enhanced_*` placeholder family (~270 micro-cohorts, of which 10 have n≥19 and
deceptively high PF). Plus ~10 non-`ml_enhanced` artifacts: CRYPTO `UNKNOWN` (PF 145),
EQUITY `smart_money_consensus` (PF 16.5) + `EmaRibbon` (PF 367), FOREX
`ig_contrarian_sentiment` (PF 44.7) + `non_crypto_consensus` (PF 14.8), FUTURES
`futures_connors_rsi2` (PF 613666) + `cta_golden_cross_200` (UNDEF n=71), ETF
`regime_mild_bull` (PF 42), COMMODITY/FUTURES COT-leakage cohorts (`cot_positioning`,
`multi_asset_cot`, `cftc_cot_commercial_signal`).

**The blunt verdict:**

- **One** strategy in the entire repo is a genuine, non-artifact, time-and-symbol-
  distributed edge candidate: **`mega_mutation`** (CRYPTO, n=72, PF 2.19). And even
  it is "size small + monitor", not proven — n=72 is ~1 harness window.
- **Every copytrade source is DRAGGING or artifact.** Best is `multi_asset_copytrader`
  FX slice at PF 1.42 (NEUTRAL). `copy_trader_highscore` is already hard-blocked.
- **Every prediction-market source is NEUTRAL** — wired into the consensus/dashboard
  path but with no resolved cohort large enough to show edge (or drag).
- **5 of 8 asset classes (EQUITY/ETF/FUTURES/COMMODITY/BOND/PENNY_STOCK) have no real
  strategy edge** — their few large-PF cohorts are placeholder/unit/COT-leakage
  artifacts. Root cause is the **broken non-crypto forward-resolution pipeline**
  (UNCLAIMED P0), not strategy design. Until clean resolved picks accumulate, those
  classes cannot be ranked honestly.

*Source: `audit_dashboard/data/pf_registry.json` policy-clean-net (2026-05-19T02:18Z).
Cross-ref: `PER_CLASS_CANDIDATE_TRADES_2026-05-18.md`, `MAGIC_FILTER_HUNT_2026-05-18.md`,
`audit_trail/quality_gates.py::BLOCKED_SOURCE_SYSTEMS`. Read-only inventory — no
production files modified.*
