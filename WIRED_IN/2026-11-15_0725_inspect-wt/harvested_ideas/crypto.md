# Harvested Ideas — Crypto

**Asset Class:** `CRYPTO`  
**Inventory Coverage (`00_inventory.csv`):** `1,104` pure `CRYPTO` files + `600+` cross-asset crypto files (`ml_crypto_predictor`, `ml_battleground`, `copy_trader_intel`, `genome`, `incubator`, `kimi_claw_pro.pine`).

---

## 1. What Was Already Tried in the Repo
- **5-System ML Battleground (`ml_battleground/ensemble_coordinator.py`):** System A (ML Filter), System B (Regime), System C (GRU-Attention Neural Net), System D (Funding Rate Contrarian Carry), System E (Cross-Sectional Momentum).
- **Deep Learning & Meta-Labeling (`ml_crypto_predictor/`):** `world_class_transformer_v2.py`, `informer_lite.py`, `gnn_onchain.py`, `meta_labeler.py`, `hmm_regime_researcher.py`.
- **Copy-Trader & Whale Scanners (`copy_trader_intel/`, `alpha_engine/config.py:76`):** `copy_hl_*`, `ct_consensus_*`, `cg_whale`, BingX/Hyperliquid mirrors, `crypto_liquidity_wick_reversal_v1` (`updates/index.html:56`).
- **Genetic & Rehab Mutations (`genome/`, `TESTING_PROTOCOL.MD`):** `mega_mutation::crypto`, `winner_pattern_precursor_inverse`, `claude_gainer_ml_inverse`, `kimi_riseoftheclaw`.
- **TradingView Indicator (`kimi_claw_pro.pine`):** 63-plot Pine v6 indicator with KAMA, HMA, SFP, Z-Score MR, CVD, TTM Squeeze, Kyle's Lambda, Hurst, Top Gainer detection.

## 2. Observed Results & Suspected Failure Modes
- **Canonical Live Readiness (`TESTING_PROTOCOL.MD:20`):** `CRYPTO` (`n=347, WR=39.2%, PF=0.879, MDD=100.0%` -> `NOT_READY`). Live Nov 2026 closed picks (`memory/2026-11-14.md`): 30d `-352.7pp`, `CRYPTO PF=0.805 (n=471)`.
- **Stop-Fill Overshoot (`tools/stop_fill_replay.py`):** Across $n=771$ `SL_HIT` rows, planned risk `1.932%` vs realized loss `2.970%` (+828pp overshoot); replay fix recovers `+67.5pp` lifting PF from `0.768` only to `~0.80` (still unprofitable).
- **Meme/Alt Pollution & Single-Source Artifacts:** 179+ alt/meme symbols (`PEPEUSDT`, `FARTCOINUSDT`, `FETUSDT`) created huge tails; `mega_mutation::crypto` flagged `is_single_source_artifact=True` (`0` rows in `recent_closed`, `PF 49-53` artifact in `pf_registry`).
- **Failure Modes:** #1 Overfitting (`ml_enhanced_` 112+ variants; 86% `OVERFIT_LIKELY`), #4 Friction & Stop Overshoot, #6 Chop/All-LONG Regime Mistake (`regime_position_sizer.py:6`), #9 Comparing against `0` instead of `BTC` buy-and-hold Sharpe (`~2.2`).

## 3. Research Gap for Phase 3 (`Plan/crypto/PLAN.md`)
- Evaluate `BTCUSDT` using **local cached real 1h OHLCV (`data/cache/BTCUSDT_3mo_1h.csv`) + real archived perpetual funding rates (`data/funding_rate_archive/BTCUSDT.jsonl`, `ETHUSDT.jsonl`, `SOLUSDT.jsonl`)** AND live `CRYPTO` closed trades (`n=771+` SL-overshoot sensitivity) under a **15 bps/side taker + funding carry model**, testing whether **Funding-Rate Regime Carry + Vol-Targeted Trend** beats `BTC Buy-and-Hold` risk-adjusted and survives **shuffle control + block bootstrap**.

