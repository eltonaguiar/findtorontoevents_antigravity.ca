# 02 — SubQ Comparison & Coverage (Decision Gate)

**Date:** 2026-11-14 | **Method:** SubQ-style decomposition (sub-question coverage + option comparison) before recommendation.  
**Note:** `tools/subq_translation_proxy.py` exists in-repo; no live SubQ API calls made in this pass. Structured SubQ-equivalent coverage matrix.

## Sub-Questions (0=poor/unknown, 1=partial, 2=good; /14)
1. Data integrity ready  2) Universe/history  3) Validation (OOS,n,PBO/DSR/effective-N)  4) Cost/execution realism  5) Benchmark/regime robustness  6) Implementability  7) Capital/fee accessibility

## Comparison Matrix

| Option | Asset | 1 | 2 | 3 | 4 | 5 | 6 | 7 | Score | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **Vol-Targeted TSMOM** (IT-005) | Crypto | 0 | 2 | 1 | 1 | 1 | 1 | 1 | **7** | **LEAD beyond MF**: reproduce net/benchmark/bear & paper |
| **Regime-Filtered VWAP-MR core** (BTC,ETH,SOL,XRP,ADA) | Crypto 4h | 0 | 1 | 1 | 1 | 1 | 1 | 1 | **6** | **CONDITIONAL**: v11 PF1.435 Sharpe7.10 MDD3.5% n=65; v12 PF1.210 Sharpe3.76 MDD10% n=129 PBO~0.489 (**strict PBO<0.3 fails**); needs >730d data & fill realism |
| **Walk-Forward Variant C** | Equity/ETF | 0 | 1 | 1 | 1 | 1 | 1 | 2 | **7** | **PILOT**: PF 1.26 n=237 p<0.0013 |
| **Faber TAA / sector-neutral QVM** | Stocks/ETFs (MF-adaptable) | 0 | 2 | 1 | 1 | 1 | 1 | 2 | **8** | **BUILD/VALIDATE**: best non-crypto testability & low cost |
| **mega_mutation_macd_rsi / ema_momentum** | Crypto | 0 | 1 | 0 | 1 | 0 | 1 | 1 | **4** | **HOLD**: unreplicated/leakage risk |
| **Low-fee $0-min index MF allocation** (no-load, ultra-low ER) | Mutual Funds | 0 | 2 | 0 | 2 | 1 | 1 | 2 | **8** | **BUILD (accessibility)**: best capital/fee profile; needs wired validated signal |
| **Vol-Targeted Bond Trend** | Bonds | 0 | 2 | 0 | 1 | 1 | 1 | 2 | **7** | **BUILD later** |
| **FX Momentum + kill-switch** | Forex | 0 | 1 | 0 | 0 | 1 | 1 | 1 | **4** | **HOLD** (thin after costs) |
| **Commodity Trend (post-fix)** | Commodities | 0 | 1 | 0 | 1 | 1 | 0 | 1 | **4** | **BLOCKED** (98.4% zero-P/L/pricing) |

## Recommendation
- **1–2 profitable targets beyond MF:** **(1) Crypto Vol-Targeted TSMOM** and **(2) Crypto Regime-Filtered VWAP-MR core** (complementary); run **Equity/ETF Faber TAA/QVM** in parallel as non-crypto diversifier.
- **Mutual funds:** $0-min, no-load, ultra-low-ER subset (FXAIX/FSKAX/SWPPX/SWTSX/FXNAX) — structural cost/capital advantage; requires validated allocation signal (not yet proven).
- **Promotion gate:** integrity clean + net-of-cost OOS + benchmark-relative + **PBO<0.3**, **DSR>0.95**, MDD<20%, sufficient n, stability + paper-forward pass.
