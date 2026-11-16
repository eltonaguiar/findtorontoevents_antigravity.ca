# DECISION_LOG — rejections and why (prevents re-investigation)

**Folder**: `WIRED_IN/final_v001/2026-11-15T0740Z_finpredict-v4/`
**Purpose**: record every negative result so future sessions do not re-test a dead class. Each entry is a ticket to *not* re-open.

## Rejections (final this cycle)

| Candidate | Class | Verdict | Evidence | Do not re-test because |
|---|---|---|---|---|
| TLT sma200 | Bonds | REJECT | Sharpe −0.95 vs −0.46; final 0.67 vs 0.69 | negative Sharpe + loses wealth |
| BND sma200 | Bonds | REJECT | Sharpe −0.21 vs +0.10; final 0.96 vs 1.02 | worse than B&H after costs |
| SPY/QQQ/VTI sma200 standalone | Equities | DD_OVERLAY | better Sharpe/DD but lose final wealth | risk overlay, not alpha |
| IWM sma200 | Equities | REJECT | Sharpe 0.29 vs 0.50; loses wealth | well below baseline |
| ETH sma200 | Crypto | REJECT | wealth wins but Sharpe 0.28 vs 0.29 fails | fails harness Sharpe rule |
| SGOV sma200 | Cash | REJECT | 0 edge; pure cash | no edge to claim |
| ^DXY / forex pairs | Forex | BLOCKED | n=0 / insufficient data | no data, not signal |
| Prediction-market copy trading | All | REJECT | zero-sum, adverse selection, fees, size, PBO=0.603 | structural |
| Equity-only Faber sleeve vs SPY | Equities | REJECT_VS_BENCH | 1.856 vs 1.851 (fails 1.01 wealth gate) | marginal; use mixed sleeve instead |
| Forward-tracker first candidate | — | ELIMINATE_FAST | n=35, 9% excess>0, Sharpe −10.9 | failed elimination criteria fast |
| DARWIN/GP evolution artifacts (Sharpe 95–97, WR 90.5%) | Crypto | REJECT (overfit) | all-time-record Sharpe impossible after multiplicity correction; 0/37 combos passed 7 gates independently | artifact of evolutionary search, not tradeable edge |
| >3-parameter / OHLCV-microstructure / HMM/GARCH regime rules | all | REJECT | graveyard: more params = more overfit; OHLCV microstructure proxies zero predictive power; complex regime models fail | violates graveyard lessons 1-4 |

## Active (not rejected)

| Candidate | Class | Status |
|---|---|---|
| BTC sma200 | Crypto | PROMISING — run 10-gate protocol |
| GLD sma200 | Commodity | PROMISING (window-sensitive) — run protocol w/ 1% margin gate |
| vwap-reversion-scout | Equities | forward alpha clock OPEN (n=28/155) |
| Mixed Faber sleeve | Multi | baseline benchmark sleeve (WEALTH_BEAT vs SPY) |

## Rule
Once written here as REJECT, a candidate is **not** re-tested unless the underlying evidence/constraint changes (e.g., new clean FX data arrives for forex). Re-opening requires a new, defensible reason.
