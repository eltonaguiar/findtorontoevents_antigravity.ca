# Quant Swarm Round 1 — Renaissance Lens (2026-05-12)

**Persona:** Senior quant, Medallion-style. Stat-arb, mean-rev, market-neutral, ultra-short hold, signal-stacking, regime-gated.
**Brief:** 55,510 trades, raw WR 11.13%, Sharpe -2.34. Save the company.

## Frame

Renaissance does not hunt directional alpha. Renaissance hunts **tiny, persistent stat anomalies, stacked, neutralized, leveraged**. Most signals here are directional bets dressed as edge. Reframe required.

## 1. Per-class keep / kill / rebuild

| Class | Verdict | Rationale |
|---|---|---|
| COMMODITY (CT=F PF 2.08-3.92, DSR 1.0, COT PF 19.19 n=130) | **KEEP + scale carefully** | COT is real factor literature. DSR 1.0 + n=130 = paper-pilot ready. Renaissance would carry-stack: COT × roll-yield × seasonality. |
| EQUITY (Sharpe +0.67, PF 2.18, n=814, WR 1.84%) | **REBUILD as cross-sectional** | Tiny WR + positive PF = fat-tail directional. Renaissance flips this to long/short top-vs-bottom decile, dollar-neutral, sector-neutral. Kill directional. |
| ETF (PF 1.20-1.58, n=87) | **KEEP, expand universe** | NAV-vs-price + sector pair-trade is Medallion bread-and-butter. Need n≥150. |
| BOND (PF 1.72, n=18, FRED fixed) | **REBUILD as curve trades** | n=18 is noise. Rebuild as 2s10s steepener + carry, not directional. |
| FOREX (PF 0.27) | **KILL directional, rebuild as triangular arb + carry-vol** | Directional FX is unwinnable retail. Triangular arb across G10 crosses + DXY-beta neutralization only. |
| CRYPTO (raw 11.3% WR, filtered PF 1.36, n=51k) | **KEEP filtered, kill toxic emitters** | Funding-rate arb + perp-vs-spot basis is the only Renaissance-style edge in crypto. Kill 69% zero-PnL ghosts at ingestion. |
| FUTURES (WR 17.4%, n=172, dead) | **KILL or merge into COMMODITY** | No emission, no edge, no rebuild path solo. |
| MEMECOIN / PENNY_STOCK | **KILL** | No microstructure data; no executable edge. |

## 2. Hidden-insight queries

**Low-score / high-PnL outliers** — Score loads on `confidence` (rank #11 in gatekeeper, 0.038 importance) and trust-tier. Missing: **realized vol regime, time-of-day (22 UTC = 61.2% WR per memory `project_clean_data_symbol_wr`), order-flow imbalance, funding sign**. The score is a stale-popularity proxy. Outliers win because they fire in low-vol, late-session windows the score ignores.

**High-score / low-PnL** — Score overfits **strategy-name autocorrelation and historical WR re-ingest** (`strat_fwd_wr` 13.4% importance). Look-ahead leak: forward-WR feeds back into score that ranks the same family. Drop self-referential features; refit on pure microstructure.

**Dormant top strategies (emission decay)** — `enhanced_ml_crypto_v3` 20K joblibs frozen 2026-03-28 = feature-schema drift gate is silently dropping retrains. CT=F-anchored COMMODITY emitters likely throttled by symbol-lock guards from mutation protocol. **Diagnostic:** plot daily-emission count per strategy × calendar; any flatline >7 days = scanner registry orphan or gate-rejected. FUTURES dead = silent-kill catch-22 (BLOCKED_ASSET_CLASSES was reverted but penalty replaced it).

## 3. New strategies to test FIRST

| # | Class | Hypothesis | Expected Sharpe |
|---|---|---|---|
| 1 | CRYPTO | Funding-rate × OI-delta mean-rev, 1-4h hold, market-neutral perp-vs-spot | 1.5-2.5 |
| 2 | EQUITY | Cross-sectional residual mean-rev top/bottom decile, beta+sector neutral, 1-5d | 1.0-1.8 |
| 3 | COMMODITY | COT extreme-percentile + roll-yield carry stack, weekly | 0.8-1.5 |
| 4 | ETF | Pair-trade cointegrated sector ETFs (XLF/KBE, XLE/XOP) | 0.7-1.2 |
| 5 | FOREX | G10 triangular arb residual + carry-vol parity | 0.4-0.9 |

Stack signals; portfolio Sharpe target 2.0+ via low-correlation aggregation, not single-strat heroics.

## 4. ML reality

Gatekeeper 32.6% accuracy is a labeling artifact (precision 11.5 / recall 84 = always-predict-WIN under 11% base rate). The real signal: AUC 0.595, p=0.003, +9.2pp WF lift. **Renaissance reads:** model has weak-but-real signal everywhere except CRYPTO (-16.67pp). CRYPTO confidence inversion = the gate learned the toxic-emitter prior, not market structure. **Fix:** per-class submodels; CRYPTO uses **flipped sign** (short the gate) until calibration retrains on dragger-quarantined data. The v3 staleness is the bigger crime — 6-week-frozen models on the largest book.

## 5. THE ONE THING — Day 1

**Stop all real capital. Build a tick-level order-book + funding-rate research warehouse, and forbid any signal that does not pass CPCV + PBO + Deflated Sharpe on out-of-sample.** Everything else is theater on contaminated data. No exceptions, no overrides, no "but this one looks good." Renaissance ships gates, not picks.

## NFA

Research surface. No real money until two classes hold T2 for 30 days post-quarantine.
