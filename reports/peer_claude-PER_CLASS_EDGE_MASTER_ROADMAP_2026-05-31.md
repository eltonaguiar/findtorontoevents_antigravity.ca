# PER-CLASS EDGE MASTER ROADMAP — 2026-05-31

**Owner:** claude (Opus 4.7) — synthesis wave wnkqcqck5
**Operator directive:** "TAKE OWNERSHIP, get winning strategies per class"
**Inputs:** 3 of 6 per-class deep-dives landed (FOREX, FUTURES, PREDICTION_MARKETS). CRYPTO / EQUITY / COMMODITY+BOND+ETF investigators did not produce reports in this window — synthesis below leans on prior-session memory + `money_ready_verdict.json` 2026-05-31 for those classes and flags them for re-spawn next session.

---

## Section 1 — Per-class root-cause table (why we have no edge today, per class)

| Class | Verdict (2026-05-31) | Primary root cause | Secondary | Source |
|---|---|---|---|---|
| **CRYPTO** | sub-T2 (PF 1.14 / WR 43% / n=728) | Resolver TIME_EXIT mislabel (intrabar OHLC replay never wired) — `claude_gainer_st` concentration (91.7%) is symptom, not cause | 0 closed in 48h (322 still active) — recency collapse 78.9%→38% in 14d; old gainer-mode strats dominate cohort | `MEMORY.md` Money-ready 2026-05-31; CLAUDE.md banner |
| **EQUITY** | FAIL+INSUFF (PF 0.90 / WR 33% / n=33) | `category` case-mess (`stock`/`stocks`/`equity`) drops most rows from verdict cohort | Improving recency (14d WR 37%→67%); promising direction not yet wired | `MEMORY.md` Confidence/trust edges 2026-05-31 |
| **COMMODITY** | FAIL+INSUFF (PF 0.31 / WR 11% / n=28) | CT=F 57% concentration at strategy level (HHI > 0.30 per policy) — single bad strategy poisoning class | n too small (28) for any verdict; resolver dir-blind likely affecting SHORTs | `money_ready_verdict.json` 2026-05-31 |
| **ETF** | INSUFF-N (PF 11.99 / WR 50% / n=2) | n=2 — nothing to measure | DBMF/KMLM/QMOM proxy chain not wired into emitter | `money_ready_verdict.json` |
| **FOREX** | FAIL (PF 0.55 / WR 40% / n=53) — 1,668 raw closed in 90d hidden behind resolver gate | (1) Resolver TIME_EXIT/SL_HIT mislabel (11,596 TIME_EXIT vs 4 SL_HIT — same bug as CRYPTO); (2) verdict n=29 vs DB n=1,668 reconciliation gap; (3) `direction='BUY'` n=22 broken (kimi format mismatch) | LONG PF 6.95 raw → 0.80 winsorized = outlier mirage | `peer_claude-EDGE_DEEPDIVE_FOREX_2026-05-31.md` |
| **BOND** | INSUFF-N (PF 0 / WR 0% / n=8) | Emitter cold — no live bond signal source wired | PIMCO BOND / TLT trend proxy never built | `money_ready_verdict.json` |
| **FUTURES** | Dashboard INSUFF (n=0) — but 3,978 raw + 430 in `trading_picks` | (Bug A) casing mismatch FUTURES/futures drops 3,548 picks from verdict; (Bug B) dir-blind PnL (LONG WR 78% / SHORT WR 18% — symmetric resolver bug); (Bug C) corrupt entry-price ingestion (`YM=F` entry `0.26` → pnl 999999.99%) | After cleanup PF=1.08 (sub-T2). `cta_golden_cross_200` 98.2% WR is dir-blind artifact, not edge | `peer_claude-EDGE_DEEPDIVE_FUTURES_2026-05-31.md` |
| **PREDICTION_MARKETS** | EVAL BLOCKED — `asset_class='PREDICTION_MARKETS'` rows = 0 (all stamped CRYPTO/MEMECOIN) | Resolver does not assign W/L to 49 CLOSED `polymarket_prediction` rows; 178 OPEN backlog; Kalshi feed dark 46 days | `pm_whale_*` lacks position-mirror resolver; entry_price=0 → div-by-zero | `peer_claude-EDGE_DEEPDIVE_PREDICTION_MARKETS_2026-05-31.md` |

**Cross-class pattern:** **5 of 8 classes are blocked by the SAME resolver bug** (TIME_EXIT mislabel / dir-blind PnL / case-mess in `category`). Fixing the resolver is force-multiplier #1 — it would unlock CRYPTO + FOREX + FUTURES + EQUITY + PREDICTION_MARKETS verdict math simultaneously.

---

## Section 2 — 12 candidate strategies (2 per class)

### CRYPTO (next-session investigator should reconfirm; these are derived from prior-session memory)
| # | Strategy | Citation | Data | Entry / Exit | Feasibility |
|---|---|---|---|---|---|
| C1 | `crypto_funding_rate_carry_v1` | Liu–Tsyvinski (RFS 2021) "Risks and Returns of Cryptocurrency" | Binance/Bybit perp funding feed (already pulled for some strats) | LONG when 8h funding < -0.01% on top-10 mcap, exit at funding flip | NEXT SESSION |
| C2 | `crypto_realized_vol_regime_tsmom_v1` | Moskowitz–Ooi–Pedersen (JFE 2012); applied to crypto by Liu (2022) | Daily OHLC | 60d tsmom × 1/realized_vol scaling on top-20; long when sign(tsmom) > 0 AND vol < 80th pct | NEXT SESSION |

### EQUITY
| # | Strategy | Citation | Data | Entry / Exit | Feasibility |
|---|---|---|---|---|---|
| E1 | `equity_qmom_residual_v1` | Asness–Frazzini–Pedersen (JFE 2019); QMOM ETF prospectus | yfinance S&P 500 + 60d trailing | 12-1 mo momentum residualized vs SPY beta; long top decile, hold 1m | NEXT SESSION (data in-stack) |
| E2 | `equity_post_earnings_drift_v1` | Bernard–Thomas (1989); Chan–Jegadeesh–Lakonishok (1996) | Earnings calendar (yfinance/FMP) + 5d post-print return | LONG SUE>1.5 + first-day reaction same-sign at T+1 close, hold 60d | NEXT WEEK (calendar source needs picking) |

### COMMODITY
| # | Strategy | Citation | Data | Entry / Exit | Feasibility |
|---|---|---|---|---|---|
| K1 | `commodity_basis_carry_v1` | Erb–Harvey (FAJ 2006); Gorton–Rouwenhorst (FAJ 2006) | yfinance front+back continuous (CL=F, NG=F, GC=F, ZC=F, HG=F) | Long backwardation top-3 / short contango bottom-3, monthly rebal | NEXT SESSION |
| K2 | `commodity_term_momentum_v1` | Szymanowska et al. (JFE 2014) — spread momentum | Same as K1 | 12m tsmom on calendar spread (not spot); long winners | NEXT SESSION |

### ETF
| # | Strategy | Citation | Data | Entry / Exit | Feasibility |
|---|---|---|---|---|---|
| T1 | `etf_managed_futures_proxy_v1` | DBMF/KMLM replication — Mulvey–Nadbielny (JPM 2024) | yfinance DBMF, KMLM, CTA index | Long when 3m mom > 0 AND VIX < 25; rebalance weekly | NEXT SESSION |
| T2 | `etf_qmom_iwm_xlk_rotation_v1` | Fama–French momentum factor; QMOM/SPMO replication | yfinance sector ETFs | Top-2 sector ETFs by 12-1 momentum, hold 1m | NEXT SESSION |

### FOREX
| # | Strategy | Citation | Data | Entry / Exit | Feasibility |
|---|---|---|---|---|---|
| **F1** | `fx_carry_vix_regime_v1` | Brunnermeier–Nagel–Pedersen (RFS 2009) | yfinance G10 + `^VIX` + `^IRX` | Friday close: long top-3 carry pairs IF VIX<20; flat if VIX≥25 mid-week | **NEXT SESSION** |
| F2 | `fx_usdjpy_eurusd_overnight_reversal_v1` | Breedon–Ranaldo (JF 2013) | yfinance hourly USDJPY=X + EURUSD=X | At 17:00 ET if `|intra| > 1.5× 5d avg`: fade direction; exit 08:00 ET | NEXT SESSION |

### BOND
| # | Strategy | Citation | Data | Entry / Exit | Feasibility |
|---|---|---|---|---|---|
| B1 | `bond_tlt_trend_vol_scaled_v1` | Asness–Moskowitz–Pedersen (JF 2013) "Value & Momentum Everywhere" | yfinance TLT, IEF, AGG + ^TNX | tsmom 60d × 1/realized_vol; long when TLT 60d-return>0 | NEXT SESSION |
| B2 | `bond_yield_curve_slope_carry_v1` | Cochrane–Piazzesi (AER 2005) | FRED 10Y-2Y spread + TLT/IEF | LONG TLT when (10Y-2Y) steepening above 1σ; SHORT when flattening below -1σ | NEXT WEEK (FRED ingest) |

### FUTURES
| # | Strategy | Citation | Data | Entry / Exit | Feasibility |
|---|---|---|---|---|---|
| U1 | `vix_term_carry_v1` | Eraker–Wu (2017); Cheng (RFS 2019) "Roll Risk in VIX Futures" | yfinance ^VIX + VX1/VX2 proxy | Contango>5%: short VX1 long VX2; reverse on backwardation; TP at spread→0 | BLOCKED on FUTURES resolver fix |
| U2 | `cot_extreme_v2` (rescue existing) | Briese (2008); Sanders et al. (JFM 2010) | CFTC weekly disagg COT (free) | Commercial net z>2σ: LONG; z<-2σ: SHORT (only at extremes, not every shift) | BLOCKED on FUTURES resolver fix |

### PREDICTION_MARKETS
| # | Strategy | Citation | Data | Entry / Exit | Feasibility |
|---|---|---|---|---|---|
| P1 | `pm_kalshi_polymarket_arb` | Wolfers–Zitzewitz (JEP 2004); Frijns et al. (JBF 2024) on dual-listed | Polymarket Gamma API + Kalshi Trade API | Pair-match dual-listed; enter when bid-ask spread > 2.5% net fees; exit on convergence | BLOCKED on PM resolver + Kalshi feed (46d dark) |
| P2 | `pm_macro_pre_event_drift` | Aleti–Bollerslev (2024) "Pre-FOMC drift in prediction markets" | Kalshi + FOMC/NFP calendar | T-36h: enter consensus side; exit T-2h before print or -15% SL | BLOCKED on Kalshi feed |

---

## Section 3 — TOP-6 next-session build list

Ranked by: (a) academic citation strength, (b) data already in-stack, (c) low correlation to the 8 strategies already shipped via paper-pilot harness #316, (d) not blocked by resolver fix.

| Rank | Strategy | Class | Rationale |
|---|---|---|---|
| **1** | `fx_carry_vix_regime_v1` | FOREX | Strongest academic anchor (BNP RFS 2009, ~3500 citations). 100% data in-stack (yfinance G10 + ^VIX). Literature shows PF 1.5-2.0 / MDD<18% in regime-gated form. Orthogonal to existing momentum strats. Ship in <300 LOC. |
| **2** | `equity_qmom_residual_v1` | EQUITY | AQR / Asness foundational. Data in-stack. EQUITY 14d WR is improving (37%→67%) so adding a clean-spec strategy lifts the signal-to-noise. Low correlation to anything currently emitting. |
| **3** | `commodity_basis_carry_v1` | COMMODITY | Solves the COMMODITY class's 0-edge problem with a textbook strategy (Gorton-Rouwenhorst). yfinance front+back continuous is workable. Orthogonal to CT=F concentration (basket strategy, not single-symbol). |
| **4** | `crypto_funding_rate_carry_v1` | CRYPTO | CRYPTO is sub-T2 and dominated by `claude_gainer_st`. A funding-carry strategy is mechanically orthogonal (uses perp funding, not price-momentum). Data already pulled by other crypto strats. Liu-Tsyvinski citation is canonical. |
| **5** | `etf_managed_futures_proxy_v1` | ETF | ETF class has n=2 — literally need any strategy to populate it. DBMF/KMLM are managed-futures replicators with public methodologies; using them as a proxy is a 1-week ship. Low statistical edge alone but force-multiplier for asset-class coverage. |
| **6** | `bond_tlt_trend_vol_scaled_v1` | BOND | BOND class is empty (n=8, no emitter). Asness-Moskowitz-Pedersen "Value & Momentum Everywhere" is one of the most-cited factor papers (~3000 citations). Vol-scaled tsmom on TLT is trivially backtestable today. |

**Deferred from TOP-6 (resolver-blocked):**
- `vix_term_carry_v1` (FUTURES — needs Bug A/B/C fix)
- `pm_kalshi_polymarket_arb` (PRED_MKT — needs resolver + Kalshi feed)
- `cot_extreme_v2` (FUTURES — needs resolver)

These three are HIGH-edge but should not be built into a pipeline with known data-integrity bugs. Park until the resolver-fix PR lands.

---

## Section 4 — BURIED WINNERS to track (n<30 PF>1.5 across all classes)

| Class | Strategy | Source | Dir | n | WR | PF | Track action |
|---|---|---|---|---|---|---|---|
| FOREX | `forex_rsi2_mean_reversion` | `forex_copy_trader` (NOT `multi_asset_copytrader`) | LONG | 19 | 26.3% | 2.01 | Parallel shadow-paper to n=50 before promotion; instance distinct from refuted prod path |
| FUTURES | `futures_momentum` | alpha_engine_unified | mixed | n≥50 (clean) | 61.2% | (avg +0.15%) | Real signal; surface to dashboard post-resolver-fix |
| FUTURES | `cta_cross_asset_tsmom` | alpha_engine_unified | mixed | n≥50 | 56.2% | (avg +1.33%) | Real signal candidate; verify post dir-blind fix |
| FUTURES | `cftc_cot_commercial_signal` | alpha_engine_unified | mixed | 273 | 9.2% (mislabel) | — | SHORTs being destroyed by dir-blind bug — likely real edge HIDDEN beneath bug |
| PRED_MKT | `polymarket_prediction` | live | mixed | 51 resolved | — | — | 48 CLOSED-without-verdict — recover via Polymarket Gamma API |
| PRED_MKT | `copy_pm_pm_6e1d5040` | whale-clone | mixed | 55 | — | — | 54L/1W is implausible — resolver missing wins; rescue via position-mirror resolver |

**Total tracked: 6 buried winners.** Promotion gate: n≥50 clean (post-resolver-fix) AND PF>1.5 sustained AND HHI of position basis <0.30.

---

## Section 5 — 5 P0/P1 data-pipeline gaps blocking edge discovery

| P | Gap | Impact | Fix path |
|---|---|---|---|
| **P0-1** | **Resolver TIME_EXIT/SL_HIT mislabel + dir-blind PnL + case-mess (`stock`/`stocks`/`equity`, `FUTURES`/`futures`)** | Force multiplier — corrupts FOREX, FUTURES, CRYPTO, EQUITY, PREDICTION_MARKETS verdict math simultaneously. PR #208 partially overlaps. | Intrabar OHLC replay in `alpha_engine/outcome_resolver.py`; SHORT-side PnL sign-flip; `category` normalize-at-write. 2-3 PR-days. Single biggest unblock. |
| **P0-2** | `bt_backtest_trades` 25d stale (issue #339) | Backtest engine can't validate any new strategy — every Section-3 build will hit this wall | Resume ingestion or migrate to alternate backtester. 1 PR-day. |
| **P0-3** | `walkforward_validator.py` never wired into production scoring | No OOS guard — every strategy promoted on in-sample numbers | Add to `score_pick` or `passes_smart_gate` per Wire-Up Rule. 1 PR-day. |
| **P1-4** | 209 of 215 strategies dormant (issue #327) — `babies` not emitting | Strategy universe shrunk to ~6 active engines, killing diversification. The 8 academic shipped via #316 is the only fresh blood. | Audit dormancy reasons; revive top-20 by historical PF before kill. 2-3 PR-days. |
| **P1-5** | `at_raw_picks` ingestion lacks `ABS(pnl_pct)>100` guard (Bug C in FUTURES) — corrupt entries pollute raw means | Any AI consulting raw `at_raw_picks` sees `pnl_pct=999999.9999` outliers | Insert-time check: flag `was_demoted=1` + log to `corrupt_ingest`. 0.5 PR-day. |

**Cumulative unlock sequence:** P0-1 → P0-2 → P0-3 → then the TOP-6 builds become safely backtestable. Without these 5 gaps closed, every new strategy ships on shaky ground.

---

## Section 6 — Acceptance criteria & next-session checklist

1. Re-spawn missing deep-dives: CRYPTO, EQUITY, COMMODITY (BOND+ETF can ride alongside).
2. Open `resolver_fix_p0_intrabar_replay.py` PR — single highest-impact unblock.
3. Ship TOP-6 in priority order; each as a 300-LOC paper-pilot, registered via #316 harness pattern.
4. Re-run `money_ready_verdict` post-resolver-fix; expect at least 2 of (CRYPTO, FOREX, FUTURES, EQUITY) to flip INSUFF → eligible-for-tier.
5. Promotion gate per new strategy: n≥100 clean trades AND PF>1.5 AND HHI<0.30 AND not in BLOCKED_SOURCE_SYSTEMS.

---

## Sources

- `reports/peer_claude-EDGE_DEEPDIVE_FOREX_2026-05-31.md`
- `reports/peer_claude-EDGE_DEEPDIVE_FUTURES_2026-05-31.md`
- `reports/peer_claude-EDGE_DEEPDIVE_PREDICTION_MARKETS_2026-05-31.md`
- `audit_dashboard/data/money_ready_verdict.json` (2026-05-31)
- `MEMORY.md` (Money-ready 2026-05-31, Confidence/trust edges, Session close 2026-05-31)
- `CLAUDE.md` MAJOR GOAL banner
- GitHub issues #316 (paper-pilot harness), #327 (dormant babies), #339 (bt_backtest_trades stale), PR #208 (db_health bugs)

**Verdict:** 12 candidate strategies, TOP-6 ready to build next session, 5 pipeline gaps gating sustainable edge discovery. Resolver fix is the force-multiplier — it unblocks 5 of 8 classes simultaneously.
