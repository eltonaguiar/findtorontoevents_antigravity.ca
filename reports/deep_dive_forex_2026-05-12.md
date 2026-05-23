# Deep Dive: FOREX Asset Class Rescue Plan — Mutate Before Kill
**Date:** 2026-05-12  
**Protocol:** docs/MUTATION_THREE_AXIS_PROTOCOL.md + docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md  
**Status:** Live edge under 0.8 PF hard-cap gate (PR #909 active)

---

## 1. Current State — PF/WR/n with Citations

**Live FOREX metrics (2026-05-05, post-resolver-v2):**
- **Profit Factor: 0.28** (updates/2026-05-05-buffy-asset-class-FOREX.md:3, dashboard asset_class_health)
- **Win Rate: 45.6%** (ibid:3)
- **n (total trades): 1,169** (ibid:3, scope: 7,645 closed FOREX trades; recent 883 at +14.07% PnL)
- **Max Drawdown: TBD** — needs DB query from dashboard_data.json capped-PnL calc

**Data integrity note:** Total FOREX shows -986.27% cumulative PnL (ibid:13) but is 286 old historical trades; recent FOREX (883 trades, 47.9% WR) is net +14.07% (ibid:14). Root cause: 3 corrupted outcome rows (USDCAD=X +40%, EURUSD=X +66%, AUDUSD=X +95%, all confidence=9.9999, id=MISSING) inflate aggregate. JPY-cross pairs (EURJPY=X −16.75%, USDJPY=X −2.94%) are chronic bleeders. (ibid:29-34)

**Hard-cap gate:** PR #909 deployed lpha_engine/risk_policy_check.py:is_forex_sizing_allowed() — zero-sizing FOREX picks until PF ≥ 0.8, n ≥ 250 rolling. Status verified 2026-05-12. (money_ready_validation_plan_2026-05-11.md:164, updates/index.html:320)

---

## 2. Per-Source Autopsy — n / WR / PnL Contribution

Per updates/2026-05-06-forex-mutation-decisions.md (mutation_analysis.py output on 719 FOREX trades):

| Strategy | n | WR | Contribution | Status | Citation |
|---|---|---|---|---|---|
| **cta_cross_asset_tsmom** | 117 | 53.0% | +1.26% avg | KEEP | mutation-decisions:13, USDJPY=X alone: n=62, WR 67.7%, PF 1.64 |
| **ig_contrarian_sentiment** | 195 | 41.4pp asymmetry | SHORT: +8.2%, LONG: -17.1% | SHORT-ONLY | mutation-decisions:18, WR 57% SHORT vs 16% LONG |
| **myfxbook_retail_contrarian** | 128 | 35.6pp spread | SHORT: +0.96%, LONG: -1.8% avg | SHORT-ONLY | mutation-decisions:25, WR 46% SHORT vs 11% LONG |
| **forex_rsi2_mean_reversion** | 115 | Break-even | +0.44% avg (TP hits) | KEEP | mutation-decisions:33 |
| **quan_engine_swing** | 30 | 34pp spread | SHORT: PF 1.80, LONG: PF 0.52 | SHORT-ONLY | mutation-decisions:40, WR 60% SHORT vs 26% LONG |
| **forex_copy_trader** | 38 | 57.9% WR | +profit (small n) | KEEP | buffy-asset-class-FOREX:50 |
| **signal_validation** | 15 | 53.3% WR | +efficient | KEEP | buffy-asset-class-FOREX:50 |
| **multi_asset_copytrader** | 576 | 45.0% WR | Workhorse driver | KEEP | buffy-asset-class-FOREX:48 |

**JPY-cross unit-corruption flag:** EURJPY=X shows -16.75% cum PnL (n=87, 32.2% WR). Quality_gates.py hardcodes JPY_CROSS_BUY_KILL as default-on. (quality_gates.py:948-951, buffy:35)

---

## 3. Three-Axis Mutation Results Already Run

Per updates/2026-05-06-forex-mutation-decisions.md decision tree (§Decision Tree Results):

### Decisions Verbatim

**cta_cross_asset_tsmom (117 FOREX trades)**  
**Status: KEEP AS-IS**
- "FOREX WR: 53.0% (63/117) — above 50% threshold"
- "FOREX avg PnL: +1.26% — positive edge"
- "Mutation axis: NONE — live edge confirmed"

**ig_contrarian_sentiment (195 FOREX trades)**  
**Status: SHORT-ONLY MUTATION**
- "SHORT: 42 trades, WR 57.1% (24W/18L), PF 1.54, +8.2% sum"
- "LONG: 153 trades, WR 15.7% (24W/129L), PF 0.35, -17.1% sum"
- "Spread: 41.4pp — strong directional asymmetry"
- "Action: Block LONG direction via BLOCKED_DIRECTION_TRIPLES. Keep SHORT."
- "Mutation axis: DIRECTION (invert LONG, preserve SHORT)"

**myfxbook_retail_contrarian (128 FOREX trades)**  
**Status: SHORT-ONLY MUTATION**
- "SHORT: 13 trades, WR 46.2%, +0.96% avg"
- "LONG: 113 trades, WR 10.6%, -1.8% avg"
- "Spread: 35.6pp — confirmed direction asymmetry"
- "Action: Block LONG direction via BLOCKED_DIRECTION_TRIPLES. Keep SHORT."
- "Mutation axis: DIRECTION"

**forex_rsi2_mean_reversion (115 FOREX trades)**  
**Status: KEEP**
- "SHORT: 11 trades, WR 27.3%, -2.1% avg"
- "LONG: 104 trades, WR 3.8%, avg PnL +0.44% (mean reversion TP hit)"
- "Break-even to slightly positive. No block needed."
- "Mutation axis: NONE"

**quan_engine_swing (30 FOREX trades)**  
**Status: SHORT-ONLY MUTATION**
- "SHORT: 5 trades, WR 60.0%, PF 1.80"
- "LONG: 25 trades, WR 26.0%, PF 0.52"
- "Spread: 34pp — confirmed direction asymmetry"
- "Action: Block LONG direction via BLOCKED_DIRECTION_TRIPLES. Keep SHORT."
- "Mutation axis: DIRECTION"

### Implementation Status

Per quality_gates.py (2026-05-12):
- **quan_engine_swing LONG:** Blocked (line 1816)
- **ig_contrarian_sentiment LONG:** TEMP UNBLOCKED 2026-05-08 (line 1814, "phantom data" re-eval by 2026-05-22)
- **myfxbook_retail_contrarian LONG:** TEMP UNBLOCKED 2026-05-08 (line 1815, same)
- **forex_rsi2_mean_reversion:** Commented out of PERMANENTLY_KILLED_STRATEGIES (line 874) as of 2026-05-08

---

## 4. External Replication Options (No Invented Data)

**Candidates without forward-test data in repo:**
- **MyFXBook public FOREX stats:** Retail sentiment contrarian edge documented (reference: myfxbook_retail_contrarian strategy lineage exists but external benchmark not cited in repo)
- **Hyperliquid HLP composition:** Not referenced in current repo; cross-exchange CTA strategies (cta_cross_asset_tsmom) may correlate
- **Academic baseline:** Connors RSI2 (Connors & Alvarez 2008) baseline 68% WR; current forex_rsi2_mean_reversion measures 43.3% WR on phantom-expired data, re-eval needed post-resolver fix
- **Published contrarian research:** ig_contrarian_sentiment Sharpe 5.87 (quality_gates.py:1814 comment) — source: external IG sentiment feed (not repo-hosted validation)

**TBD — needs external API audit:**
- MyFXBook API correlation check (live vs repo edge attribution)
- Hyperliquid HLP manager allocation correlation
- IG retail sentiment feed staleness / calendar effect

---

## 5. 30/60/90-Day Rescue Plan

### Day 0-30: Verification + Fresh Mutation Cycle

1. **Sizing-at-0 hold (PR #909 verification)**  
   - Confirm block_reason field appears in dashboard_data.json
   - Audit: zero sized FOREX picks in live feed while PF < 0.8
   - Target: 14 days of clean zero-sizing baseline

2. **Re-run mutation analysis with fresh n**  
   - Export closed_picks.json → run tools/mutation_analysis.py --json
   - Resolve phantom_expired feedback loop: confirm resolver-v2 deployed, phantom % < 20%
   - Decision gate: if phantom % still > 20%, defer rest of plan and root-cause resolver

3. **USDCHF=X unit corruption upstream resolution**  
   - Identify data source (alphavantage? yfinance?) emitting corrupted USDCHF prices
   - Cross-check with: quality_gates.py CORRUPTED_OUTCOME_ROWS hard blocks, universal_pick_resolver.py make_pick_id() key logic
   - Action: fix at resolver, re-run closed_picks deduplication

### Day 30-60: AB-test Composite Ranking Formula

4. **Implement Chinese report's Final_Score formula**  
   - Spec: Final_Score = 0.4·WR + 0.3·Trust + 0.2·Score + 0.1·Liquidity (Wenxin AI audit, 2026-04-22)
   - Wire behind feature flag FOREX_RANKING_V2 in quality_gates.py
   - Compare against current: calculate_smart_score (7-component additive, no WR weight)

5. **A/B test on closed Q2 2026 picks**  
   - Backtest both formulas on same closed dataset
   - Acceptance: composite PnL parity + walk-forward consistency ≥ current
   - Fallback: pure score if composite fails

### Day 60-90: Graduation Criteria

6. **Unblock sizing once PF ≥ 0.8, consistency ≥ 60%**  
   - Delete is_forex_sizing_allowed() hard-cap gate
   - Enable LONG direction for ig_contrarian_sentiment + myfxbook_retail_contrarian (per mutation axis)
   - Revert TEMP UNBLOCKED comments in quality_gates.py if walk-forward WR < baseline

---

## 6. Risk Register

| # | Risk | Probability | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Phantom-expired > 20% persists → sizing gate falsely blocks good trades | Med | High | Re-run resolver forensic; escalate to resolver team if > 20% at day 15 |
| R2 | USDCHF unit corruption spreads to other crosses | Low | High | Hard-block USDCHF at resolver; cross-verify all JPY pair sources |
| R3 | Composite ranking formula over-fits to 2026-04-22 data | Med | Med | Hold-out validation set; if walk-forward WR drops > 5pp, revert to pure score |
| R4 | ig_contrarian_sentiment LONG re-unlock may reintroduce phantom-driven losses | Med | Med | Require n ≥ 50 clean forward trades before unblocking (currently n=33 total, phantom ~60%) |
| R5 | Multi_asset_cot PF 12.16 → 2.0-2.5 post-forensic (PR #913) erases COMMODITY's tier-2 candidacy | Low | High | PR #904 DB verify must complete before relying on multi_asset_cot for rescue |
| R6 | JPY-cross seasonal volatility vs mean-reversion TP conflicts | Low | Med | Monitor RSI2 TP-hit rate (Connors academic: 68% WR; repo: 43% on phantom data) post-resolver |

---

## 7. Acceptance Criteria — Numeric Gates for Un-blocking

**Hard requirement before sizing re-enabled:**

1. **Profit Factor ≥ 0.8** (from 0.28)  
   - 3x improvement required; measured on n ≥ 250 rolling closed picks
   - Data source: asset_class_health.FOREX.profit_factor (dashboard_data.json)

2. **Walk-forward consistency ≥ 60%** (from 48.4% per live state)  
   - Defined: % of 30-day rolling windows with positive PnL
   - Baseline: 30 calendar days, re-evaluate monthly

3. **Win Rate ≥ 50%** (from 45.6%)  
   - 4.4pp improvement; measured same as PF on rolling n ≥ 250
   - JPY pairs (EURJPY, USDJPY) individually monitored; blocker if < 40% per pair

4. **Zero phantom-expired in current sample** (from 96.21% per FOREX resolver report)  
   - Acceptance: < 5% phantom-expired in last 100 closed picks
   - If > 5%, freeze sizing until resolver forensic completes

5. **No USDCHF or unit-corruption entries** (from 3 detected 2026-05-05)  
   - Hard block via quality_gates.py: any pick with confidence=9.9999 or id=MISSING rejected at emission
   - Audit: zero such picks in last 50 closed FOREX trades

6. **Composite ranking formula A/B parity** (if PR deployed)  
   - Alternative Final_Score = 0.4·WR + 0.3·Trust + 0.2·Score + 0.1·Liquidity
   - Acceptance: PnL within ±5pp of pure score baseline on same test set

**Escalation:** If any gate fails by day 60, de-scope FOREX from money-ready and route resources to COMMODITY / EQUITY rescue (both closer to tier-2).

---

## 8. Implementation Touches (Repo Files)

- audit_trail/quality_gates.py (lines 874, 1153, 1318, 1595-1607, 1650-1652, 1812-1822)
- alpha_engine/risk_policy_check.py (is_forex_sizing_allowed, PR #909 live)
- alpha_engine/forex_strategies.py (TP/SL caps, updates/2026-05-08-forex-p0-p1-fixes-implementation.md)
- tools/mutation_analysis.py (re-run per MUTATION_THREE_AXIS_PROTOCOL.md)
- alpha_engine/data/closed_picks.json (source data; 7,645 total, 1,169 in current sample)
- audit_dashboard/template.html (banner update for FOREX-as-emergency framing once P0-A verified)

---

**Prepared by:** Claude Code  
**Next review:** 2026-05-26 (14 days post-PR #909 gate activation)
