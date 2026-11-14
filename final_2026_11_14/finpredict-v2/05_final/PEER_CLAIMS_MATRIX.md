# Peer & Internal Claims — Certification Matrix (2026-11-14)

**Legend:** `VERIFIED` = reproduced independently; `FALSIFIED` = contradicts the underlying data;
`ARTIFACT` = statistically invalid measurement/selection; `UNVERIFIED` = no reproducible artifact;
`PILOT` = positive but not certified.

| # | Claim | Source | Reported | Independent check | Status |
|---:|---|---|---|---|---|
| 1 | `/audit` is profitable / statistically sound | original system | PF surfaces 9–18, WR 78–88% | 0/9 money-ready; fleet PF 0.2657, WR 42.21%, z −23.60; 658 strategies, 32.9 expected false positives | **FALSIFIED** |
| 2 | H10 SPY/QQQ RSI2 + T-bill cash | our v2 | 1.83 Sharpe, 22.0% CAGR, DSR 0.978 at N=12 | contaminated OOS; effective N≈38 DSR 0.9365; ex-best-day 0.8993; 2-day lag 0.696; T-bill carry | **NOT_PROVED** |
| 3 | Crypto funding carry | our v4 | 6.4–14.2 Sharpe, 5.6–7.2% notional | capital/1.5 CAGR 3.7–4.8% vs 4.5% cash; BTC-only 4.8% with n=10 | **NOT_PROVED / PILOT** |
| 4 | Regime-filtered VWAP mean reversion | peer VWAP doc | 3.76 Sharpe, PF 1.21, PBO 0.489, DSR 1.0 | correct Sharpe ~1.18 (t=0.91, p=0.18); CSCV PBO 0.84–0.97; true DSR 0.83/N=1, 0.01/N=960; 79/129 stops breached intrabar (PF 0.81, −17.4%); OOS 7.18 months, not 22; concurrent 40%/symbol = 280% gross, −15.8% | **FALSIFIED** |
| 5 | mega_mutation_macd_rsi / ema_momentum | flaxen-hair | forward n=50, WR 84%, PF 8.32; "statistically valid" | headline reproduces, but 21/50 are synthetic/replay rows; genuine OOS n=29; selection 8/33,000 uncorrected (best ledger p≈0.07); claimed backtest table not reproducible (m006/AVAX 0.54/41.7% not 4.66/87.5%); 13/24 TP_HIT never reached TP; strict n=16, WR 68.75%, PF 5.19 | **NOT_PROVED / FALSIFIED as "proven"** |
| 6 | deepAI walk-forward variant C | `audit/live-audit-2026-11-14` | n=237, PF 1.26, +98.7pp, p<0.0013 | no Nov-14 payload/log; same script on Oct-23 payload: n=764, PF 0.906, −134.5pp, p=0.4825; slippage not deducted; Bonferroni truncated to 4; random-selection benchmark; `vwap-reversion-scout` (n=15) ≈47% of P/L | **FALSIFIED as stated / UNVERIFIED** |
| 7 | `quan_engine` 95.8% WR, +669%, 284 trades | `PLAN_PATH_TO_PROFITABILITY.md` | blocked edge | real only in 2026-04-06 snapshot (292 closed, 280W/12L, PF 79.6, avg loss −0.73% = truncated-loss resolver artifact); today 0 resolved live; own DB 40.7% WR/PF 1.166 | **ARTIFACT** |
| 8 | `st_rsi_momentum_confluence` 65.1% WR, PF 2.53, 258 trades | same plan | blocked edge | zero rows in five datasets; cited `walk_forward_validation.json` absent | **UNVERIFIED** |
| 9 | SHORT 72.0% vs LONG 20.3% | same plan | direction edge | 25-row / 64-row cell; full population opposite (SHORT 31.6% n=307, LONG 47.2% n=3,181); today 53.6% vs 38.7% p=0.070; second ledger flips it | **ARTIFACT** |
| 10 | Score 40–59 = 60.8% WR | same plan | exploitable bucket | full bucket 54.4%, PF 1.74, n=331, p=0.124; claimed 60.8% is a 79-row subset | **NOT SIGNIFICANT** |
| 11 | Edge search v1–v4 | `updates/2026-11-14-edge-search-results.md` | 0/40 profitable | confirms negative | **VERIFIED NEGATIVE** |
| 12 | Inspect-wt/deepAI final audit | `audit/live-audit-2026-11-14` | FAIL | independent notes agree with our FAIL (population clocks differ) | **VERIFIED NEGATIVE** |
| 13 | Scratch-hippodraco audit/quickwins | `docs/scratch-hippodraco-audit-2026-11-14` | FAIL + quick wins | agrees on FAIL; quick wins overlap ours | **VERIFIED NEGATIVE** |

## Bottom line

No claim on 2026-11-14 is certified profitable. The strongest evidence is the pre-registered
research (23 candidates, 0 proved), the VWAP falsification, and the three peer-claim reviews
(mega-mutation, deepAI, path-to-profitability). Every positive claim fails on at least one of:
contaminated/selected OOS, wrong annualization, no intrabar stops, no concurrent capital, no cost
deduction, or multiple-testing.
