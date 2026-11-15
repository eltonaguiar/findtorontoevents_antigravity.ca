# Harvested Ideas — Multi-Asset, Meta-Selection & Prediction Markets

**Asset Class:** `MULTI_ASSET` (Meta-Strategy Selection, Cross-Asset Risk Parity, Polymarket/Kalshi Prediction Markets)  
**Inventory Coverage (`00_inventory.csv`):** `3,824` `MULTI_ASSET` rows spanning `alpha_engine/ensemble/`, `copy_trader_intel/`, `prediction_market_agents/`, `tools/hrp_allocator.py`, `tools/pypfopt_allocator.py`, `audit_trail/dashboard_generator.py`.

---

## 1. What Was Already Tried in the Repo
- **Meta-Learners & Signal Combiners (`alpha_engine/ensemble/`):** `meta_learner.py`, `regime_allocator.py`, `signal_combiner.py`, `alpha_engine/contrarian_consensus.py`, `alpha_engine/prediction_market_consensus.py`.
- **HRP & Portfolio Optimization (`tools/hrp_allocator.py`, `tools/pypfopt_allocator.py`):** López de Prado (2016) single-linkage Hierarchical Risk Parity and `PyPortfolioOpt` Efficient Frontier / Ledoit-Wolf shrinkage (built as sidecars, not wired into a live capital engine).
- **Variant-C Walk-Forward Meta-Selector (`final_2026_11_14/inspect-wt/06_profitable_approach/walkforward_v6.py`):** Pre-specified monthly selector picking top-6 strategies (`n_train >= 20, PF_train > 1.3`) strictly from prior months. Achieved `n=237, WR=47.3%, PF=1.26, +98.7pp` over 7–8 OOS months (`p < 0.0013` vs 800 random-selection draws).
- **Prediction Markets (`prediction_market_agents/`, `alpha_engine/polymarket_signals.py`, `kalshi_signals.py`):** Scraped Polymarket whale wallets and Kalshi binary event contracts (note: `memory/2026-11-15.md` migrated dead Data API v1 -> v2, recovering 0->6 markets, and caught a sports-market leak `'MONTREAL CANADIENS VS BUFFALO SABRES'` into financial picks).

## 2. Observed Results & Suspected Failure Modes
- **Live Fleet Aggregate (`TESTING_PROTOCOL.MD`, `memory/2026-11-14.md:82`):** Live 30d closed picks across all classes: `n=1,273, PF=0.80, -424pp`. **0/9** classes ready.
- **Prediction-Market Copy-Trading Failures:** Latency/size asymmetry, binary payoff convexity mismatch against TP/SL, zero fill replay, and tiny $n$ (`MEMORY.md` & `ELIMINATION_RATIONALE.md:37`).
- **Meta-Selection Caveat on `MA1` (Variant C):** While `p < 0.0013` against random strategy draws, Variant C has only **7–8 OOS calendar months** (Feb–Nov 2026), misses Tier-2 (`WR 47.3% < 50%`, `PF 1.26 < 1.5`), and shows vintage sensitivity (`Oct-23` snapshot yielded `PF 0.906`).
- **Failure Modes:** #8 Short OOS Calendar Window (7–8 months on `/audit` trade ledger), #7 Ledger Hygiene Bugs (`TIME_EXPIRED`, missing `resolution_method`, sports leaks).

## 3. Research Gap for Phase 3 (`Plan/multi_asset/PLAN.md`)
Two pre-registered multi-asset experiments directly fill the remaining repo gaps:
1. **Candidate `MA1_VariantC_MetaSelector`:** Full 10-step proof evaluation (including 2,000-path circular block bootstrap, permutation shuffle control, Canadian tax drag, and repo-wide `N=646` DSR) on the exact `live_dashboard_payload.json` closed-trade stream.
2. **Candidate `MA2_MultiAsset_RiskParity_Combo` (Portfolio Combination per `negative_result_diagnosis.md` §5):** Combine **low-correlation sleeves** ($\rho < 0.3$ — US/Global Equities `E1`, Duration/Bonds `B1`, Gold/Commodity Trend `CM1`, and T-Bill Cash ballast) using **inverse-volatility / risk-parity weights**, evaluating cascaded DSR across all 9 tested candidates (`N=9`) AND the full 646-strategy history (`N=646`).

