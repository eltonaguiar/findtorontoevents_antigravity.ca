# Money-Ready Pick Blitz — 2026-06-05

> **Goal:** Real-money statistical edge per asset class. No months-long forward-testing wait.
> **Method:** Live DB forensics + 5-axis scrutiny + subagent swarm per class.
> **Caveat:** Several candidates show insane PF/WR on tiny n or per-symbol overfit. All flagged below.

---

## LIVE OPEN PICKS RIGHT NOW (15 ml_enhanced CRYPTO)

All generated 2026-06-05 13:26-13:27 UTC. **ALL LONG.**

| Symbol | Model | Entry | TP | SL | Direction |
|--------|-------|-------|----|----|-----------|
| ZKUSDT | ml_enhanced_ZKUSDT_4h_D_ensemble_stack | 0.01068 | 0.01137 | 0.01038 | BUY |
| LTCUSDT | ml_enhanced_LTCUSDT_4h_A_xgboost | 44.48 | 46.85 | 43.47 | BUY |
| APTUSDT | ml_enhanced_APTUSDT_4h_A_xgboost | 0.700 | 0.756 | 0.676 | BUY |
| ARBUSDT | ml_enhanced_ARBUSDT_1h_D_ensemble_stack | 0.0839 | 0.0860 | 0.0831 | BUY |
| AVAXUSDT | ml_enhanced_AVAXUSDT_4h_A_xgboost | 7.194 | 7.619 | 7.012 | BUY |
| LINKUSDT | ml_enhanced_LINKUSDT_4h_A_xgboost | 7.631 | 8.081 | 7.438 | BUY |
| OPUSDT | ml_enhanced_OPUSDT_4h_D_ensemble_stack | 0.1044 | 0.1148 | 0.0992 | BUY |
| BNBUSDT | ml_enhanced_BNBUSDT_15m_B_lightgbm | 595.07 | 612.92 | 583.17 | BUY |
| FETUSDT | ml_enhanced_FETUSDT_1d_B_lightgbm | 0.2027 | 0.2230 | 0.1885 | BUY |
| ZROUSDT | ml_enhanced_ZROUSDT | 1.007 | 1.037 | 0.987 | LONG |
| ZKUSDT | ml_enhanced_ZKUSDT | 0.01066 | 0.01098 | 0.01045 | LONG |
| XRPUSDT | ml_enhanced_XRPUSDT | 1.1357 | 1.1698 | 1.1130 | LONG |
| WUSDT | ml_enhanced_WUSDT | 0.01012 | 0.01042 | 0.00992 | LONG |
| WLDUSDT | ml_enhanced_WLDUSDT | 0.5349 | 0.5509 | 0.5242 | LONG |
| TRXUSDT | ml_enhanced_TRXUSDT | 0.32668 | 0.33648 | 0.32015 | LONG |

**Risk:** All models are long-biased. In a CRYPTO downturn, correlation → 1 and all SLs hit together. Size accordingly.

---

## TOP CANDIDATE PER ASSET CLASS

### CRYPTO — Tier List

| Rank | Strategy | n | WR | PF | Verdict | Action |
|------|----------|---|---|---|---------|--------|
| 1 | **genome_mega_mutation** | 295 | 64% | 3.16 | 🔴 BLOCKED (swarm HOLD) | Unblock ~Jun 12-16 |
| 2 | **crypto_liquidity_wick_reversal_v1** | 30 | 60% | 1.55 | 🟡 Single-source only | Paper-trade now |
| 3 | **ml_enhanced_INJUSDT_1d_B** | 25 | 96% | 35.6x | 🔴 Per-symbol overfit risk | Micro-paper only |
| 4 | **ml_enhanced_TONUSDT** | 19 | 84% | 58x | 🔴 Per-symbol overfit risk | Micro-paper only |
| 5 | **prediction_market_consensus** | 96 | 86% | 24x | 🔴 Batch artifact (Apr cluster) | EXCLUDE |

**Honest CRYPTO pick for TODAY:** `crypto_liquidity_wick_reversal_v1` — only candidate with n≥30, 0 sign flips, spread dates, and all 5-axis PASS except single-source. Volume-profile corroborator now live in hourly pipeline.

### EQUITY

| Strategy | n | WR | PF | Verdict |
|----------|---|---|---|---------|
| **stocks_ema_golden_cross** | 324 | 42% | 2.08 | 🟡 100% time-exits, no fundamentals |

**Action:** Paper-trade. Need earnings-calendar filter (±5 days) + at least 5% TP/SL hits before live.

### FOREX

| Strategy | n | WR | PF | Verdict |
|----------|---|---|---|---------|
| **ig_contrarian_sentiment / CADJPY** | 378 | 56.6% | 7.33 | 🟡 Batch-exit artifact (68-90% same dates) |

**Action:** Paper-trade with slippage validation. JPY-strength regime supportive.

### ETF

| Strategy | n | WR | PF | Verdict |
|----------|---|---|---|---------|
| **etf_dual_momentum** (backtest) | 48 months | 70.8% | 3.42 | 🟢 Clean backtest; live ledger contaminated |

**Action:** Paper-trade. Monthly rebalance. Beta=0.34 vs SPY = genuine alpha.

### COMMODITY

**No viable candidate.** Backfill contamination destroyed all large-n stats. Wait 30 days for post-backfill window.

### BOND

**No viable candidate.** Best sleeve (cta_cross_asset_tsmom TLT/IEF) has 6 bps gross avg vs 8 bps slippage = net negative. Policy-frozen.

---

## KILL-SWITCH RULES (Apply to ALL paper trades)

1. **Last-10 WR < 40%** → pause strategy for 7 days
2. **3 consecutive losses** → halve position size
3. **Single-day batch > 35% of monthly trades** → flag for scrutiny
4. **Sign flip detected** → immediate quarantine
5. **PF without top-2 wins < 1.0** → demote to observation

---

## FASTEST PATH TO FIRST LIVE MONEY-READY PICK

1. **TODAY:** Paper-trade wick-reversal_v1 (all gates pass, corroborator hourly)
2. **THIS WEEK:** Paper-trade a basket of 5 ml_enhanced picks (0.5% risk each, strict kill-switches)
3. **~Jun 12-16:** Re-evaluate mega_mutation unblock (swarm consensus date)
4. **Ongoing:** Monitor auto-shutdown-monitor daily (now fixed and running)

---

*Generated: 2026-06-05T14:06Z*
*Sources: ejaguiar1_stocks.trading_picks live DB, per_class_scrutiny_engine, subagent swarm (6 agents)*

---

## UPDATE 2026-06-05T14:15Z — Subagent Verification

**VERIFIED (live DB):**
- 117 OPEN ml_enhanced CRYPTO picks (was 15 in initial scan)
- High concentration: 7 symbols have 6+ concurrent picks
- 108 of 117 picks have SL within 3% of entry (tight stops = high stop-out risk if market dips)

**FABRICATED by subagent (cross-AI verification caught):**
- FOREX EURUSD claim: subagent said n=88 WR=73.9% PF=2.70 → ACTUAL n=6 WR=66.7% PF=1.08
- Earnings plays (ORCL, ADBE, CASY): subagent claimed technical setups + fundamentals → ACTUAL DB shows n=2 WR=0% for ADBE, almost no history for ORCL/CASY

**Lesson:** Per feedback-subagent-stat-fabrication-2026-06-05, always live-DB-verify subagent claims before acting. The 117 picks and wick-reversal_v1 are verified. Earnings/FOREX claims from this batch are NOT actionable.

---

## IMMEDIATE ACTION ITEMS (Verified Only)

1. **Monitor 117 ml_enhanced picks** — 108 near SL. Any CRYPTO dip will cascade stop-outs.
2. **Paper-trade wick-reversal_v1** — only verified non-blocked T2-near sleeve.
3. **Re-evaluate mega_mutation** on ~Jun 12-16 per swarm consensus.
4. **Do NOT act** on unverified earnings/FOREX claims without independent DB confirmation.
