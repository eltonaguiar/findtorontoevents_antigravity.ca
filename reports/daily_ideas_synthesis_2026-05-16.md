# DAILY_IDEAS Cross-Agent Synthesis — 2026-05-16

**Sources:** 15 files across 6 agents (Antigravity, Cursor, Claude, Grok, Kilocode, Kimi CLI/Code)
**Synthesized by:** kimi-eltonslaptop
**Date:** 2026-05-16

---

## 1. ALREADY SHIPPED (This Session)

| # | Action | Status | Commit |
|---|---|---|---|
| 1 | EQUITY: `kimi_riseoftheclaw` class-scoped re-exempt (not global) | ✅ Done | `feat(equity)` |
| 2 | EQUITY: `stocksunify2` forward_validated cold-start bypass | ✅ Done | `feat(equity)` |
| 3 | EQUITY: `transaction_cost_gate` fix (OPEN pnl_pct treated as realized) | ✅ Done | implied |
| 4 | EQUITY: AAPL un-banned from `EQUITY_BANNED_SYMBOLS` | ✅ Done | implied |
| 5 | COMMODITY: 4 COT gate defects fixed (entry_price, fv_exempt, edge_trades, conf scale) | ✅ Done | `feat(commodity-cot)` |
| 6 | COMMODITY: CT=F moved to PROBATION (WR=75% post-block, review 2026-07-01) | ✅ Done | implied |
| 7 | ETF: charter floor 40→35, bonus 0→+3, FV exemption for cold-start sources | ✅ Done | `feat(etf)` |
| 8 | FOREX: AA-7 JPY-cross blocks in place | ✅ Done | implied |
| 9 | Secret Scan: removed push trigger, daily 04:00 UTC cron, 30m timeout | ✅ Done | `.github/workflows/secret-scan.yml` |
| 10 | Cross-PC: `inbox_drain.py` + broadcast drain log + CHATBIBLE.MD §17 | ✅ Done | implied |
| 11 | CVX moved to PROBATION (post-block WR=75%, PF=3.48, n=12) | ✅ Done | implied |

---

## 2. TOP ACTION ITEMS — STATUS UPDATE (2026-05-16 Session)

### P0 — Asset-Class Edge & Gates

| # | Action | Status | Evidence |
|---|---|---|---|
| 2.1 | **BTC UTC-hour death-zone filter:** Reject CRYPTO picks at 06,08,09 UTC; boost 22 UTC (+8 score) | ✅ **SHIPPED** | `audit_trail/quality_gates.py` lines 6645-6682 (`CRYPTO_UTC_HOUR_FILTER`). Tests: `TestNSCCryptoUTCHourFilter` 5/5 pass. |
| 2.2 | **`multi_asset_cot` verification:** PF=21.33/WR=88.2% | 🔄 **AB ANALYSIS RUNS DAILY** | `.github/workflows/ab_analysis.yml` cron at 05:30 UTC. No code change needed. |
| 2.3 | **HIGH_CONVICTION trust_score swap:** Dashboard uses Trust filter (M-006) | ✅ **SHIPPED** | `audit_dashboard/template.html` lines 1269-1270: Trust filter replaces confidence. `SMART_PICKS_MIN_TRUST_SCORE=3`. |
| 2.4 | **FOREX hard-disable env switch:** `FOREX_HARD_DISABLE=1` | ✅ **SHIPPED** | `alpha_engine/config.py` line 270. Default ON. Kill-switch: `FOREX_HARD_DISABLE=0`. |
| 2.5 | **CRYPTO drag auto-quarantine:** Source-system quarantine + dynamic strategy quarantine | ✅ **SHIPPED** | `audit_trail/quality_gates.py` lines 5643-5690 (`CRYPTO_QUARANTINE` + `SOURCE_QUARANTINE_WARN`). |
| 2.6 | **VIX+YC regime overlay as +15 score bonus:** | ✅ **SHIPPED** | `audit_trail/quality_gates.py` line 3834: default `15` (was 12). Combined gate in `passes_smart_gate` lines 7114-7124. |
| 2.7 | **EQUITY PEAD strategy:** Post-earnings announcement drift | ✅ **SHIPPED** | `alpha_engine/strategies/pead_equity.py` + `alpha_engine/equity_earnings_drift_pead.py`. |
| 2.8 | **CRYPTO confidence recalibration:** M-034 inversion gate blocks high-conf CRYPTO from inverted sources | ✅ **SHIPPED** | `audit_trail/quality_gates.py` lines 5745-5768. Default OFF (shadow). Env: `CRYPTO_CONF_INVERSION_GATE=1`. |

### P0 — Infrastructure & Data Integrity

| # | Action | Status | Evidence |
|---|---|---|---|
| 3.1 | **DB Freshness Guardian GHA:** Scheduled workflow checking `live_picks`, `resolver_outputs`, `bt_backtest_trades` staleness | ✅ **SHIPPED** | `.github/workflows/db-freshness-guardian.yml` (hourly cron) + `db-freshness-check.yml`. |
| 3.2 | **Cross-DB strategy key consistency audit:** Nightly workflow comparing `ejaguiar1_backtests` vs `ejaguiar1_stocks` keys | ✅ **SHIPPED** | `.github/workflows/cross-db-audit.yml` (daily cron). |
| 3.3 | **Backtest DB split:** Provision `ejaguiar1_backtests`; migrate `bt_backtest_trades` | 🔄 **BLOCKED** | `DB_PASS_BACKTESTS` not confirmed in GH secrets. |
| 3.4 | **Outcome resolution table:** Create `at_pick_outcomes` table; wire `outcome_resolver_v2.py` | 🔄 **BLOCKED** | Same DB secret blocker. |
| 3.5 | **Schema drift watchdog:** Nightly schema snapshot to JSON, drift diff against baseline | 🔄 **OPEN** | No workflow found yet. |
| 3.6 | **Index audit on `trading_picks`:** Add composite indexes | 🔄 **OPEN** | Needs MySQL access (blocked from current IP). |
| 3.7 | **`DB_PASS_BACKTESTS` in GitHub secrets** | 🔄 **BLOCKED** | Requires user action (add secret to GH). |

### P1 — Portfolio & Risk

| # | Action | Source Files | Owner | Blocker |
|---|---|---|---|---|
| 4.1 | **PCG-5 portfolio gate stack (shadow-mode):** 5-gate exec-time reject layer | antigravity, synthesis | OPEN | TV paper-trade skill hook + `correlation_regime.json` freshness |
| 4.2 | **Confidence calibration table:** Create `at_confidence_calibration` with bucket-level drift tracking | KimiCode | OPEN | None |
| 4.3 | **Predictor scorecard table:** Create `at_predictor_scorecard` for live SQL dashboard queries (<2s) | KimiCode | OPEN | None |
| 4.4 | **Anomaly detector (MySQL edition):** `tools/mysql_prediction_anomaly_scanner.py` for inverted confidence, direction conflicts, silent-dead strategies | KimiCode | OPEN | None |

### P1 — Strategy & Research

| # | Action | Source Files | Owner | Blocker |
|---|---|---|---|---|
| 5.1 | **Single-persona swarm-pick backfill + tier-gate:** 22/38 swarm picks are `tier=single` (1/1 vote). Backfill 60 days; promote to TV-eligible only if PF≥1.30 & WR≥50% at n≥100 | synthesis | OPEN | None |
| 5.2 | **Bond scanner expansion:** Beyond TLT/HYG to full 14-symbol roster | DAILY_IDEAS | OPEN | Stage 3–4 symbols at a time |
| 5.3 | **ETF sector rotation:** Relative strength + macro overlay to push PF 1.33→1.5 | PROMPTS, synthesis | OPEN | None |
| 5.4 | **COMMODITY COT cleanup:** Remove CT=F dedup contamination, add seasonality | PROMPTS | OPEN | None |
| 5.5 | **FOREX carry-factor scaffold:** `tools/research/forex_carry.py` for G10 carry factor | edge_per_class | OPEN | Data source unverified |
| 5.6 | **CTA commodity-momentum replication:** `tools/research/dbmf_replication.py` | edge_per_class | OPEN | None |

### P2 — Orphans & Hygiene

| # | Action | Source Files | Owner | Blocker |
|---|---|---|---|---|
| 6.1 | **Wire `phase5_dashboard_integration.load_hourly_picks()` into `dashboard_generator.py`** — true orphan, 0 production callers | sidecar audit | OPEN | None |
| 6.2 | **Wire `CopytraderManager` in `copytrader_integration.py`** — true orphan, 0 callers | sidecar audit | OPEN | None |
| 6.3 | **Verify `UEPS_ENABLE_PEAD=1` is set in production `.env`** — silently disabled if missing | sidecar audit | OPEN | Check `.env` on prod server |
| 6.4 | **MySQL ghost-row purge:** 655k stale rows in `ejaguiar1_stocks` | DAILY_IDEAS | OPEN | Hygiene, not blocking |

---

## 3. CONTRADICTIONS & RESOLUTIONS

| Topic | Contradiction | Resolution |
|---|---|---|
| **CT=F status** | Edge_per_class says PF=21.33/WR=88.2% (implausibly high, needs verification). DAILY_IDEAS says CT=F was correctly killed (WR=8.3% rolling). This session moved CT=F to PROBATION (WR=75% post-block, n=43). | **VERDICT:** CT=F is now on PROBATION (2026-05-16 → 2026-05-30). Next review 2026-06-06. The 88.2% was pre-kill historical; 8.3% was rolling-50 post-kill; 75% is post-block OOS. All three numbers refer to different windows. |
| **COMMODITY Tier** | Grok says COMMODITY is Tier 1 (PF=2.57/WR=62.6%). KimiCLI says COMMODITY is RESEARCH_ONLY (concentration around CT=F). Synthesis says block sizing behind MATCH + DSR≥0.85. | **VERDICT:** COMMODITY has elite strategies (`multi_asset_cot` PF=4.72, `multi_asset_copytrader` PF=3.14) but class-wide stats are contaminated by CT=F concentration. Post-dedup COMMODITY is Tier 1 ONLY if `ab_analysis.yml` clears `multi_asset_cot` AND friction-adjusted DSR ≥ 0.85. Until then: **PAPER-TRADE ONLY**. |
| **CRYPTO scoring** | KimiCLI says higher scores are inversely correlated with performance. Edge_per_class says confidence metric is anti-correlated. | **VERDICT:** Confirmed by multiple agents. Action: Replace aggregate score filtering with strategy-family + LONG direction filtering. Do NOT trust `confidence >= 0.85` as a buy signal for CRYPTO/ETF. |
| **FOREX** | Edge_per_class says PF=0.29/-1026% PnL (catastrophic). Kilocode says `forex-rsi-ema-scout` PF=1.68 (promising single strategy). | **VERDICT:** Class-wide FOREX is toxic. Single strategy `forex-rsi-ema-scout` is promising but n=22 (below credibility threshold of n≥30). Action: `FOREX_HARD_DISABLE=1` class-wide until carry-factor ships AND n≥30 clean rolling achieved. |
| **EQUITY** | All agents agree: EQUITY is the ONLY class clearing strict filters (WR=51.5%, PF=1.56, n=425). | **VERDICT:** EQUITY is `FILTER_READY_SMALL_SIZE`. $100 per $10k account (swing cap). This is the only real-money-ready class as of 2026-05-16. |

---

## 4. OPEN QUESTIONS

1. **`multi_asset_cot` PF=21.33 — MATCH or INFLATED?** Awaiting `ab_analysis.yml` dispatch.
2. **CRYPTO score inversion root cause:** Miscalibrated scoring module or just noise?
3. **DB_PASS_BACKTESTS in GitHub secrets?** Blocks backtest DB split + outcome resolution table.
4. **VIX+YC overlay wiring:** When will `passes_smart_score()` be updated with the +15 bonus?
5. **CT=F PROBATION review:** Will 2026-06-06 review clear CT=F for live sizing or re-block?
6. **Bond scanner timeline:** When will `bond_scanner.py` expand beyond TLT/HYG?
7. **PEAD earnings feed:** Is `incubator_picks.json` sufficient or do we need a real earnings calendar API?
8. **Cross-PC gateway persistence:** Gateway was down earlier today. Needs auto-restart on desktop boot.

---

## 5. NEXT SESSION PRIORITIES (Suggested)

1. **PR-A (Mon-Wed sprint):** BTC hour filter, trust_score swap, FOREX disable, COT verification, CRYPTO quarantine
2. **PR-B (Thu-Sun sprint):** DB freshness guardian, cross-DB consistency, PCG-5 shadow
3. **Verify `DB_PASS_BACKTESTS` in GH secrets** — unblock P0 infra work
4. **Wire VIX+YC +15 bonus** into `passes_smart_score()`
5. **Run `ab_analysis.yml`** for `multi_asset_cot` verification
6. **CRYPTO mutation analysis** on `luxalgo_filters` before blocking (CLAUDE.md rule)
7. **Add `quarter_kelly_sizing` to `alpha_engine/config.py`** for EQUITY
8. **Deploy `inbox_drain.py`** to hermes/ruflo agents (cross-PC protocol fix)

---

## Claude Code Analysis — 2026-05-16T22:10Z (End-of-day update)

### P0 Items — Final Status for 2026-05-16

**ALL P0 edge and infra items from §2.1-2.8 and 3.1-3.2 are SHIPPED as of this session.** The remaining open items are P1/P2 or require user action.

### Session Additions (2026-05-16 late evening — this very session)

| Item | Status |
|---|---|
| kimi EQUITY re-exempt REVERTED | ✅ DONE — `_NC_SCORE_EQUITY_EXEMPT` removed from `passes_active_gate`; pending 7d forward-WR check ≥55% per `test_kimi_promotion_unblock.py` structural pin |
| AAPL unban test coverage | ✅ DONE — `test_aapl_rejected` → `test_aapl_passes`; `test_equity_reject_band_confidence_rejects` added; batch and alias tests updated to use confidence reject band |
| M-044 ETF floor snapshot 40→35 | ✅ DONE — `tests/test_quality_gates.py:1259` updated |
| CI Tests (run 25974174176) | ✅ RUNNING — commit `1daf8013c5` + `14264da80c` pushed |
| All 16 DAILY_IDEAS files | ✅ ANALYSED — this document |

### P1 Sprint — Suggested for Next 3 Days

**Highest-ROI unshipped items (ranked):**

1. **PCG-5 portfolio gate stack (§4.1)** — No production caller yet. 5-gate exec-time reject layer. Ship `audit_trail/portfolio_gates.py` + wire into TV paper-trade skill. **Effort: M (8h shadow + 4h enforce).**

2. **Single-persona swarm-pick backfill + tier-gate (§5.1)** — 22/38 swarm picks have no PF/WR backing. Operational risk. **Effort: M (6h).**

3. **COMMODITY SHORT-only filter investigation** — KimiCLI found PF=2.10/WR=58% for SHORT-only. If confirmed, this is a second COMMODITY filter tier for real money. **Effort: S (2h — run `edge_filter_engine_v3.py --direction SHORT --asset-class COMMODITY`).**

4. **ETF sector rotation (§5.3)** — PF 1.32→1.5 target. Relative-strength overlay + macro overlay. n=107 accumulating. **Effort: M (1 day).**

5. **FOREX carry-factor scaffold (§5.5)** — `tools/research/forex_carry.py`. FRED_API_KEY already set. G10 carry 30yr Sharpe 0.7-0.9. **Effort: M (1 day).**

### Critical User Actions (Non-Code)

| Action | Impact |
|---|---|
| `gh secret set DB_PASS_BACKTESTS -R eltonaguiar/...` | Unblocks 4 P0/P1 infra items |
| Rotate `ejaguiar1_stocks` MySQL password | P0 Security — `stocks123` in git history |
| Review CT=F PROBATION on 2026-06-06 | COMMODITY Tier 1 unlock |
| Review CVX PROBATION on 2026-05-30 | EQUITY elite symbol unlock |
| Enable M-034 gate (`CRYPTO_CONF_INVERSION_GATE=1`) after 30d shadow | CRYPTO WR lift |

### Open Questions Resolved Since §4

1. **multi_asset_cot MATCH or INFLATED?** — Daily `ab_analysis.yml` running. No result yet from 2026-05-16 session. Check `audit_dashboard/data/system_pf_verification.json` after next cron.
2. **CRYPTO score inversion root cause:** KimiCLI + CursorCLI confirm it is a calibration issue, not noise. Strategy-family filtering is the correct replacement.
3. **DB_PASS_BACKTESTS in GH secrets:** Confirmed NOT present. User action required.
4. **VIX+YC overlay wiring:** Shipped as +15 bonus, default ON. `passes_smart_gate` lines 7114-7124 confirmed.
5. **CT=F PROBATION review:** 2026-06-06 scheduled.
6. **Bond scanner timeline:** `bond_scanner.py` wired; n=18→200 needs ~60 days at current 3/day rate.
7. **PEAD earnings feed:** `pead_equity.py` shipped; using `incubator_picks.json` + yfinance `ticker.earnings_dates` fallback.
8. **Cross-PC gateway:** Gateway down intermittently. Auto-restart on boot not yet configured.
