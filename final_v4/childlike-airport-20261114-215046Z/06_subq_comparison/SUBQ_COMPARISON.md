# 06 — SubQ Comparison & Coverage (Final)

**Method:** SubQ-style decomposition (coverage + option comparison). `tools/subq_translation_proxy.py` exists; **no verifiable live SubQ invocation/response artifact** in reviewed materials — matrix is SubQ-equivalent (upgrade to logged SubQ run when available).

## Scoring (0/1/2, /14)
1) Data integrity  2) Universe/history  3) Validation (OOS,n,PBO/DSR/effective-N)  4) Cost/execution realism  5) Benchmark/regime  6) Implementability  7) Capital/fee accessibility

| Option | Class | 1 | 2 | 3 | 4 | 5 | 6 | 7 | Score | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **Vol-Targeted TSMOM** (IT-005) | Crypto | 0 | 2 | 1 | 1 | 1 | 1 | 1 | **7** | **LEAD beyond MF** (prove benchmark/bear/net + paper) |
| **Regime-Filtered VWAP-MR core** (BTC,ETH,SOL,XRP,ADA) | Crypto 4h | 0 | 1 | 1 | 1 | 1 | 1 | 1 | **6** | **CONDITIONAL** (v11 PF1.435 Sharpe7.10 MDD3.5% n=65; v12 PF1.210 Sharpe3.76 MDD10% n=129 PBO~0.489, **PBO<0.3 fails**) |
| **Faber TAA / sector-neutral QVM** | Stocks/ETFs (MF-adaptable) | 0 | 2 | 1 | 1 | 1 | 1 | 2 | **8** | **BUILD/VALIDATE non-crypto lead** |
| **Walk-Forward Variant C** | Equity/ETF | 0 | 1 | 1 | 1 | 1 | 1 | 2 | **7** | **PILOT** (PF 1.26 n=237 p<0.0013) |
| **Low-fee $0-min index MF allocation** (FXAIX/FSKAX/SWPPX/SWTSX/FXNAX core) | Mutual Funds | 0 | 2 | 0 | 2 | 1 | 1 | 2 | **8** | **BUILD accessibility/cost** (not proven alpha) |
| **mega_mutation_macd_rsi/ema_momentum** | Crypto | 0 | 1 | 0 | 1 | 0 | 1 | 1 | **4** | **HOLD** (unreplicated/leakage) |
| **Vol-Targeted Bond Trend** | Bonds | 0 | 2 | 0 | 1 | 1 | 1 | 2 | **7** | **BUILD later** |
| **FX Momentum + kill-switch** | Forex | 0 | 1 | 0 | 0 | 1 | 1 | 1 | **4** | **HOLD** |
| **Commodity Trend (post-fix)** | Commodities | 0 | 1 | 0 | 1 | 1 | 0 | 1 | **4** | **BLOCKED** |

## Recommendation
- **1–2 beyond MF:** **Crypto TSMOM** + **Crypto VWAP-MR core** (complementary, conditional); **Equity/ETF TAA/QVM** in parallel.
- **MF:** $0-min/no-load/ultra-low-ER subset (FXAIX 0.015%, FSKAX 0.015%, SWPPX 0.02%, SWTSX 0.03%, FXNAX 0.025% core; + FSMDX/FSSNX/FSGGX/SWISX) — cost/capital advantage, not guaranteed alpha.
- **Promotion gate:** integrity clean + net-of-cost OOS + benchmark-relative + **PBO<0.3, DSR>0.95, MDD<20%, sufficient n, stability + paper-forward**.
