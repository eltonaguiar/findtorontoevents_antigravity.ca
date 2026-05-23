# Daily Ideas Edge Sweep — 2026-05-17

**Sources:** 19 DAILY_IDEAS files from 12+ AI agents (Antigravity, Cursor, Grok, Kimi, HuggingFace, Nvidia, Ollama, OpenMonoAgent, XiaoMi Mimo, GH Copilot, Kilocode, LMArena)  
**Synthesized:** 2026-05-17T22:00Z  
**Method:** Read all files; ranked by multi-agent consensus count + evidence quality + effort-to-impact

## Current Performance Baseline

| Class | PF | WR | n | Status |
|---|---|---|---|---|
| EQUITY | 1.56 | 51.5% | 425 | Tier 2 confirmed |
| COMMODITY | 2.57 | 62.6% | 337 | Tier 1 candidate (CT=F probation) |
| CRYPTO | 1.31–1.36 filtered | 46.5% | 7935 | Sub-floor; qualification gate needed |
| ETF | 1.32 | 57% | 107 | Approaching T2 |
| FOREX | 0.27 | 46.2% | 1355 | HARD_DISABLE active |
| BOND | 0.66 | 54.5% | 11 | Too thin (n<30) |

---

## TOP 15 IDEAS — Ranked by Multi-Agent Consensus

### #1: CRYPTO UTC-Hour Death-Zone Filter
**Consensus:** 4 agents (Ollama, Edge-per-class, KimiCLI, Synthesis-05-15)  
**Asset class:** CRYPTO | **Type:** New filter | **Effort:** XS  
22:00 UTC = 61.2% WR; 08-09 UTC = 0% WR. Block 06:00–11:00 UTC.  
**Status: ✅ SHIPPED** — `quality_gates.py` lines 6645–6682  
**Projected impact:** +14pp WR for CRYPTO class

---

### #2: Remove MySQL Silent-Fail from Sync Workflow
**Consensus:** 4 agents (Cursor, KimiCode, Copilot, Synthesis-05-15)  
**Asset class:** Infrastructure | **Type:** Fix | **Effort:** XS (5 min)  
`|| echo "non-fatal"` in `mysql-trading-sync.yml` line 43 swallows DB failures silently.  
**Status: 🔄 OPEN** — 5-minute fix  
**Projected impact:** Catch DB outages instantly instead of hours later

---

### #3: COMMODITY COT Post-Dedup Verification Gate
**Consensus:** 6 agents (Grok, Edge-per-class, KimiCLI, Cursor, Kilocode, Ollama)  
**Asset class:** COMMODITY | **Type:** Gate | **Effort:** S  
`multi_asset_cot` PF=21.33 may contain duplicated 144 trades → phantom 88.2% WR. Gate sizing behind MATCH + DSR≥0.85 until ab_analysis confirms.  
**Status: ✅ DISPATCHED** — `ab_analysis.yml` runs daily; awaiting result  
**Projected impact:** Unlock COMMODITY Tier 1 OR reveal artifact (PF 2.57 real either way)

---

### #4: CRYPTO Strategy-Level Drag Auto-Quarantine
**Consensus:** 5 agents (Edge-per-class, KimiCLI, Synthesis-05-15, OpenMono, Ollama)  
**Asset class:** CRYPTO | **Type:** New filter | **Effort:** S  
Auto-quarantine CRYPTO strategies >40% volume with PF<1.0 (kimi_signal_tracking PF=−930%, crypto_winners PF=0.39).  
**Status: ✅ SHIPPED** — `quality_gates.py` lines 5643–5690  
**Projected impact:** +15-20pp WR for CRYPTO class

---

### #5: FOREX Hard-Disable Until Carry-Factor Ships
**Consensus:** 5 agents (Edge-per-class, Kilocode, Synthesis-05-15, Cursor, Ollama)  
**Asset class:** FOREX | **Type:** Safety gate | **Effort:** XS  
WR=46.2%, PF=0.27, −1026% total PnL. Carry-factor (G10 high-yield long/low-yield short) is only documented 30-yr edge.  
**Status: ✅ SHIPPED** — `FOREX_HARD_DISABLE=1` active  
**Projected impact:** Eliminate −1026% bleed; unlock FOREX T2 when carry ships

---

### #6: Replace Confidence with trust_score in HIGH_CONVICTION Gate
**Consensus:** 5 agents (Edge-per-class, KimiCLI, Cursor, Synthesis-05-15, OpenMono)  
**Asset class:** CRYPTO, ETF | **Type:** Score adjustment | **Effort:** S  
Confidence is anti-edge on CRYPTO/ETF (higher conf → lower WR). Gate on `trust_score >= 0.6` instead.  
**Status: ✅ SHIPPED** — `template.html` HC filter patched  
**Projected impact:** Prevent anti-edge picks from reaching dashboard

---

### #7: DB Freshness Guardian Workflow
**Consensus:** 5 agents (Cursor, KimiCode, Copilot, GH-Copilot, Synthesis-05-15)  
**Asset class:** Infrastructure | **Type:** Infrastructure | **Effort:** S  
Hourly GH Action checks live_picks/resolver_outputs/bt_backtest_trades stale > 6h; auto-opens GitHub Issue.  
**Status: ✅ SHIPPED** — `.github/workflows/db-freshness-guardian.yml`  
**Projected impact:** MTTR hours → <15 min

---

### #8: EQUITY PEAD (Post-Earnings Drift) Strategy
**Consensus:** 3 agents (Edge-per-class, Synthesis-05-15, Copilot)  
**Asset class:** EQUITY | **Type:** New strategy | **Effort:** M  
Long-only top-100 EQUITY in 2-day post-earnings window. Earnings feed via yfinance `ticker.earnings_dates`.  
**Status: ✅ SHIPPED** — `alpha_engine/strategies/pead_equity.py` wired  
**Projected impact:** +3-8pp WR for EQUITY top-100 cohort

---

### #9: Schema Drift Watchdog Workflow
**Consensus:** 4 agents (Cursor, KimiCode, GH-Copilot, Synthesis-05-15)  
**Asset class:** Infrastructure | **Type:** Infrastructure | **Effort:** S (3h)  
Nightly snapshot `information_schema` metadata → diff against version-controlled baseline in `schemas/`. CI fails on unexplained drift.  
**Status: 🔄 OPEN** — High value, no workflow found  
**Projected impact:** Catch silent schema regressions before dashboard generator fails

---

### #10: Cross-DB Strategy Key Consistency Audit
**Consensus:** 4 agents (Cursor, KimiCode, GH-Copilot, Synthesis-05-15)  
**Asset class:** Infrastructure | **Type:** Infrastructure | **Effort:** M  
Compare ejaguiar1_backtests vs ejaguiar1_stocks: strategies in backtests but never emitting live; symbol-class label mismatches.  
**Status: ✅ SHIPPED** — `.github/workflows/cross-db-audit.yml` daily  
**Projected impact:** Reduce false-confidence misclassification 40-60%

---

### #11: Confidence Calibration Tracking Table
**Consensus:** 4 agents (KimiCode, Cursor, LMArena, Synthesis-05-15)  
**Asset class:** CRYPTO, ETF | **Type:** New data table | **Effort:** S  
`at_confidence_calibration` MySQL table: per-bucket actual WR vs expected WR. Auto-quarantine when calibration_gap < −50pp.  
**Status: 🔄 BLOCKED** — Needs `at_pick_outcomes` table + DB_PASS_BACKTESTS secret  
**Projected impact:** +8-12pp class WR by auto-preventing inverted-confidence picks

---

### #12: Meta-Labeler Gate for CRYPTO
**Consensus:** 3 agents (LMArena, Cursor, Ollama)  
**Asset class:** CRYPTO | **Type:** New filter | **Effort:** M  
Wire `meta_labeler.py` into `quality_gates.passes_active_gate`. CRITICAL: must drop `forward_wr` (look-ahead leak) and `confidence` (known-inverted) from feature vector first.  
**Status: ✅ PARTIAL** — `meta_labeler.py` shipped with leak fixes; production gate wiring OPEN  
**Projected impact:** +8-15pp WR for CRYPTO filtered subset (high risk if gates miss)

---

### #13: Regime-Alignment Multiplier + Overconfidence Decay
**Consensus:** 3 agents (LMArena, Gemini, Ollama)  
**Asset class:** All | **Type:** Score adjustment | **Effort:** S  
`score_booster.py`: decay score ×0.8 when `abs(score) > THRESH`; regime multiplier ×0.6 counter-regime / ×1.2 with-regime.  
**Status: ✅ SHIPPED** — `_apply_overconfidence_decay` in `alpha_engine/score_booster.py`  
**Projected impact:** +2-4pp WR on top-quartile cohorts; prevents overconfidence blowups

---

### #14: FOREX Carry-Factor Scaffold
**Consensus:** 4 agents (Edge-per-class, Kilocode, Synthesis-05-15, Ollama)  
**Asset class:** FOREX | **Type:** New strategy (research) | **Effort:** M (1 day)  
`tools/research/forex_carry.py`: long G10 high-yielders, short low-yielders; monthly rebalance. AQR-documented 30-yr Sharpe 0.7-0.9. FRED_API_KEY already in secrets.  
**Status: 🔄 OPEN** — Not yet scaffolded; FOREX hard-disabled until this ships  
**Projected impact:** Only documented path from FOREX PF=0.27 to Tier 2

---

### #15: ETF Sector Rotation + Risk-Parity Overlay
**Consensus:** 3 agents (Edge-per-class, Kilocode, Synthesis-05-15)  
**Asset class:** ETF | **Type:** New strategy | **Effort:** M (1 day)  
Relative-strength across 11 SPDRs (XLF/XLE/XLK/...) + Black-Litterman risk-parity. Wire into `alpha_engine/etf_rotation_strategy.py`.  
**Status: 🔄 OPEN** — Not yet shipped  
**Projected impact:** ETF PF 1.32→2.1 (target); n=107 accumulating toward T2 floor

---

## Multi-Agent Consensus Summary

| Idea | Agents | Status |
|---|---|---|
| CRYPTO UTC-hour filter | 4 | ✅ SHIPPED |
| MySQL silent-fail removal | 4 | 🔄 OPEN (5 min) |
| COMMODITY COT post-dedup gate | 6 | ✅ DISPATCHED |
| CRYPTO drag auto-quarantine | 5 | ✅ SHIPPED |
| FOREX hard-disable | 5 | ✅ SHIPPED |
| Replace confidence w/ trust_score | 5 | ✅ SHIPPED |
| DB freshness guardian | 5 | ✅ SHIPPED |
| Cross-DB consistency audit | 4 | ✅ SHIPPED |
| Schema drift watchdog | 4 | 🔄 OPEN (3h) |
| Confidence calibration table | 4 | 🔄 BLOCKED (DB secret) |

## Critical Blockers (User Action Required)

| Blocker | Impact | Fix |
|---|---|---|
| `DB_PASS_BACKTESTS` not in GH secrets | Blocks 4 P0/P1 items | `gh secret set DB_PASS_BACKTESTS` |
| MySQL password rotation | P0 Security — `stocks123` in git history | Manual action (see PR #1086) |
| CT=F PROBATION review | 2026-06-06 deadline | Run `ab_analysis.yml` daily; calendar reminder |

## Open Action Items (Autonomous — No Approval Needed)

1. **Remove MySQL silent-fail** (XS, 5 min) — `mysql-trading-sync.yml` line 43
2. **Schema drift watchdog** (S, 3h) — new `schemas/baseline/` + workflow  
3. **FOREX carry-factor scaffold** (M, 1 day) — `tools/research/forex_carry.py`
4. **ETF sector rotation** (M, 1 day) — `alpha_engine/etf_rotation_strategy.py`
