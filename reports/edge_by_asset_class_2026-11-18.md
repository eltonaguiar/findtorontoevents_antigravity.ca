# Edge by asset class — what the ledger can prove

Source: `audit_dashboard/data/dashboard_data.json` · 3500 closed picks · verdict thresholds n>=30, proven n>=100.

Win rate is compared with the **breakeven** win rate implied by the class's own
average win and average loss, not with 50%: a 45% win rate is edge on a 1:2
payoff and ruin on 2:1.

| class | n | win rate | Wilson 95% low | breakeven | PF | expectancy % | p vs breakeven | verdict |
|---|---|---|---|---|---|---|---|---|
| CRYPTO | 2070 | 46.1% | 44.0% | 39.5% | 1.31 | 0.54 | 0.0000 | **PROVEN** |
| EQUITY | 690 | 47.5% | 43.8% | 43.1% | 1.23 | 0.46 | 0.0107 | **PROVEN** |
| ETF | 503 | 44.3% | 40.1% | 42.7% | 1.07 | 0.08 | 0.2370 | **NO EDGE** |
| FOREX | 199 | 32.2% | 26.1% | 50.6% | 0.66 | -0.13 | 1.0000 | **NO EDGE** |
| BOND | 28 | 35.7% | 20.7% | 51.1% | 0.56 | -0.23 | 0.9654 | **INSUFFICIENT** |
| COMMODITY | 9 | 44.4% | 18.9% | 49.2% | 1.03 | 0.03 | 0.7322 | **INSUFFICIENT** |
| FUTURES | 1 | 0.0% | 0.0% | 100.0% | — | -0.47 | 1.0000 | **INSUFFICIENT** |

## Strategies carrying each class (n >= 30)

* **CRYPTO** — PROVEN
  * `luxalgo_confluence` — n=1211, WR 41.9% (CI low 39.2%, breakeven 41.3%), PF 1.03, p=0.3237, FDR no → NO EDGE
  * `MomentumEMA` — n=73, WR 57.5% (CI low 46.1%, breakeven 40.4%), PF 1.99, p=0.0022, FDR pass → PROVEN
  * `strong consensus (alpha_engine, luxalgo_filters)` — n=70, WR 41.4% (CI low 30.6%, breakeven 32.2%), PF 1.53, p=0.0632, FDR no → NO EDGE
  * `momentum_breakout` — n=69, WR 49.3% (CI low 37.8%, breakeven 42.8%), PF 1.30, p=0.1665, FDR no → NO EDGE
  * `mega_mutation_ema_momentum_m006` — n=66, WR 48.5% (CI low 36.8%, breakeven 55.1%), PF 0.77, p=0.8856, FDR no → NO EDGE
  * `mega_mutation_macd_rsi_m048` — n=57, WR 68.4% (CI low 55.5%, breakeven 29.8%), PF 5.11, p=0.0000, FDR pass → PROVEN
* **EQUITY** — PROVEN
  * `vol-contraction-scout` — n=59, WR 49.2% (CI low 36.8%, breakeven 39.9%), PF 1.46, p=0.0929, FDR no → NO EDGE
  * `momentum-factor` — n=57, WR 49.1% (CI low 36.6%, breakeven 44.7%), PF 1.19, p=0.2963, FDR no → NO EDGE
  * `quality-minus-junk` — n=49, WR 49.0% (CI low 35.6%, breakeven 58.1%), PF 0.69, p=0.9243, FDR no → NO EDGE
  * `adx-trend-scout` — n=49, WR 42.9% (CI low 30.0%, breakeven 44.8%), PF 0.93, p=0.6596, FDR no → NO EDGE
  * `rs-breakout-scout` — n=45, WR 53.3% (CI low 39.1%, breakeven 37.6%), PF 1.90, p=0.0212, FDR no → PROMISING
  * `stoch-rsi-scout` — n=42, WR 47.6% (CI low 33.4%, breakeven 56.7%), PF 0.69, p=0.9112, FDR no → NO EDGE
* **ETF** — NO EDGE
  * `intermarket-flow-scout` — n=97, WR 48.5% (CI low 38.8%, breakeven 44.3%), PF 1.18, p=0.2364, FDR no → NO EDGE
  * `rs-breakout-scout` — n=66, WR 56.1% (CI low 44.1%, breakeven 42.8%), PF 1.71, p=0.0200, FDR no → PROMISING
  * `rsi-divergence-scout` — n=45, WR 40.0% (CI low 27.0%, breakeven 42.3%), PF 0.91, p=0.6783, FDR no → NO EDGE
  * `quality-minus-junk` — n=41, WR 34.1% (CI low 21.6%, breakeven 37.2%), PF 0.88, p=0.7124, FDR no → NO EDGE
  * `adx-trend-scout` — n=35, WR 54.3% (CI low 38.2%, breakeven 40.3%), PF 1.76, p=0.0649, FDR no → NO EDGE
* **FOREX** — NO EDGE
  * `london-breakout-scout` — n=64, WR 39.1% (CI low 28.1%, breakeven 46.4%), PF 0.74, p=0.9044, FDR no → NO EDGE
* **BOND** — no strategy has 30 closed picks yet.
* **COMMODITY** — no strategy has 30 closed picks yet.
* **FUTURES** — no strategy has 30 closed picks yet.

## Multiple testing (Benjamini-Hochberg, q=0.1)

23 strategy tests with n>=30; 2 survive at q=0.1. A strategy is only called PROVEN when it survives this and its Wilson lower bound clears its own breakeven win rate.

* **CRYPTO** `MomentumEMA` — n=73, WR 57.5%, PF 1.99, p=0.00215
* **CRYPTO** `mega_mutation_macd_rsi_m048` — n=57, WR 68.4%, PF 5.11, p=0.00000
