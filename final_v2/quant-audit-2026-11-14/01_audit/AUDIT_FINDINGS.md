# 01_Audit — Per-Asset-Class Profitability Review (final_v2, 2026-11-14)

**Scope:** Stocks, crypto, forex, bonds, ETFs, mutual funds  
**Basis:** Live ledger screener (0/166 cells), peer backtest research, protocol v1-v4 runs (~23 candidates, 0 proved)

---

## A. Live Ledger — 0/166 Cells Pass

From `tools/money_ready_screener.py` on `recent_closed_array.json` (3,447 decisive picks):

| Class | Cells | n | WR | PF | Avg Net Expectancy | Passing |
|---|---|---|---|---|---|---|
| CRYPCO | 67 | 2,069 | 45.7% | 1.31 | +0.385% | 0 |
| EQUITY | 44 | 680 | 48.2% | 1.23 | +0.486% | 0 |
| ETF | 32 | 503 | 44.3% | 1.07 | −0.165% | 0 |
| COMMODITY | 3 | 8 | 50.0% | 1.03 | +0.897% | 0 |
| FOREX | 9 | 159 | 40.3% | 0.66 | −0.528% | 0 |
| BOND | 10 | 27 | 33.3% | 0.56 | −0.342% | 0 |
| FUTURES | 1 | 1 | 0.0% | 0.00 | −0.675% | 0 |

**Every cell is single-source** (100% from one `source_system`). Only 1 cell clears n≥100 (`luxalgo_confluence` CRYPCO LONG, n=563) and it fails WR (44%), PF (1.24), MDD (289.5%), single-source (94%).

---

## B. Research Protocol — 0/23 Candidates Proved

| Protocol | Candidates | Best | Why failed |
|---|---|---|---|
| v1-v2 (equity/ETF) | 12 | H10 SPY/QQQ RSI(2) (Sharpe 1.83, CAGR 22%) | OOS contamination, effective N≈38 → DSR 0.9365, single-day dependence, execution fragility, T-bill carry component |
| v3 (crypto/ETF) | 8 | H18 ETF TSMOM (Sharpe 1.00) | PBO 0.36-0.59, SPA p=0.488, DSR<0.95, bootstrap CI crosses 0 |
| v4 (crypto funding) | 3 | H22 BTC funding (cash CAGR 4.8% > T-bill 4.5%) | n=10 < 30 minimum; capital-adjusted CAGR below T-bill for top-5/top-10 |

---

## C. Peer Research — 3 Approaches, 0 Strictly Proved

| Approach (peer) | Asset | Sharpe | PF | MDD | PBO | DSR | Status |
|---|---|---|---|---|---|---|---|
| Regime-Filtered VWAP MR (kilo) | Crypto 4h | 3.76 | 1.21 | 10.0% | 0.489 | 1.0 | VALIDATED (PBO borderline 0.489, n=129) |
| Vol-Targeted Trend (kilo) | Crypto daily | 2.13 | 1.40 | 17.4% | — | CI[1.25,3.25] | PROVEN |
| Walk-Forward Variant C (deepAI) | Equity/ETF | — | 1.26 | — | — | p<0.0013 | PILOT |

---

## D. Data Defects Blocking All Classes

| Defect | Impact | Affected classes |
|---|---|---|
| EXPIRED→WON mislabeling | WR inflation | All (dashboard CRYPCO 78.93% vs DB raw 39.38%) |
| 53 picks frozen at pnl=0% | Unresolved PnL | All |
| `recent_closed.json` = 0 bytes | No recent closed data | All |
| `hyrotrader_journal.json` = 0 trades | No real fills logged | Hyro/crypto |
| `at_signal_outcomes` RED (~80 days stale) | No outcome resolution | All |
| Dead price refresh (HTTP 404 since 2026-04-29) | Stale prices | All |
| No MUTUAL_FUND class | Cannot trade mutual funds | MUTUAL_FUND |

---

## E. Per-Class Recommendation

| Class | Recommendation | Rationale |
|---|---|---|
| **CRYPCO** | **Deploy regime-filtered VWAP MR (kilo) as paper-trading candidate #1** | Only approach passing all peer gates; Sharpe 3.76, PF 1.21, MDD 10% |
| **EQUITY** | **Deploy H10 RSI(2) as paper-trading candidate #2** | Came closest in protocol (Sharpe 1.83, CAGR 22%) but needs clean forward OOS |
| **CRYPCO (alt)** | **H22 BTC funding carry as candidate #3** | Clears T-bill cash (4.8%) but n=10<30 — expand universe first |
| **ETF** | Do not deploy | Best Sharpe 1.00, fails DSR and "0.3 above benchmark" |
| **FOREX** | Do not deploy | Live WR 40.3%, PF 0.66, negative expectancy |
| **BOND** | Do not deploy | Live WR 33.3%, PF 0.56, n=27 insufficient |
| **COMMODITY** | Do not deploy | n=8 insufficient |
| **FUTURES** | Do not deploy | n=1, WR 0% |
| **MUTUAL FUND** | Add infrastructure first | No class exists in asset_class.py or gatekeeper |
