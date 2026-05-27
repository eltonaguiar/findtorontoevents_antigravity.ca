# EAGLE Remaining Items — Kimi K2.6 Cloud Backlog (Enhanced v2)
**Date:** 2026-05-27 10:31 EDT | **Model:** Kimi K2.6 (via Cloud)  
**Branch:** `eagle-quickwins-2026-05-27`  
**Depends on:** `reports/EAGLE_quick_wins_2026-05-27_1031_EDT_Kimi_K2.6_Cloud.md`  
**Prior Reviews:** Opus 4.7 (02:26), GPT-5.4 (02:17), Grok 4.3 (02:12→10:16, 18+ cycles), Kimi K2.6 v1 (02:31)

---

## Direct Answers to User Questions (Enhanced with 12-Engine Consensus)

### Q1: Do we have picks that would have won big, but safety gates filtered them out?

**Answer: YES — confirmed in at least 2 sleeves, but catastrophic data corruption makes the magnitude uncertain.**

**Evidence (updated):**
- **FOREX 48h contradiction:** `pick_summary_stats_48h` shows 86.2% WR / PF 6.35 on recent USDCAD=X LONG picks, while `money_ready_verdict` shows 9.1% WR. **However**, the won_pnl_contradiction dryrun at 04:00Z found a `-106,700.68%` AUDUSD=X row labeled `TP_HIT_RESOLVED`. This means **the 48h data may be mixed with physically impossible corrupted rows**. The 48h stats are NOT fully trustworthy until the resolver is fixed. The conservative interpretation: some real winners were filtered, but we cannot quantify how many until data integrity is restored.
- **FUTURES ConnorsRSI2:** Blocked historically under `BLOCKED_STRATEGIES`. The 13/13 YM=F winners in 48h (+1.95%/trade, ~20K min holds) suggest prior rejections were false negatives.
- **Confidence 0.85–0.90 band:** Already corrected in `quality_gates.py` (M-034 threshold raised from 0.85 → 0.90 after Kimi live-site analysis showed 82% WR in 0.85–0.90 band). This WAS a confirmed case of gate-filtered winners.
- **New finding (Opus oscillation analysis):** AUDUSD=X SHORT has PF 3.55 (n=11) in mutation autopsy — likely filtered by FOREX HARD_DISABLE gate.

**Without a `rejected_picks_audit` table (PR-8), these remain hypotheses. The honest answer: we don't know for sure, and that ignorance is itself a P0 risk.**

---

### Q2: Do some picks deserve exemption to safety gates?

**Answer: No blanket exemptions. Bounded, auditable, time-boxed exemptions are defensible — formalized below.**

**MiMo-V2.5 formalization (meta-synthesis partner #8):**

| Criterion | Threshold |
|---|---|
| Consecutive wins | ≥10 |
| Rolling 20-pick WR | ≥70% |
| Clean PF | >1.5 |
| DSR | ≥0.85 |
| Clean n | ≥30 |

**Earned relaxations:**
- Sharpe gate: 0.3 (vs default 0.5)
- Max DD: 25% (vs default 20%)
- Minimum hold time: 10 minutes (vs 20 minutes)

**Forced tightenings:**
- Trailing stop: 1.5× ATR (vs default 2×)
- Max single-trade risk: 0.75% (vs default 1%)

**Hard floors that NEVER relax:**
- Leakage guards (no open picks before closing)
- WON/PnL sign coherence (TP_HIT must have positive PnL)
- Monte-Carlo p-value ≥0.05
- Concentration cap (no single symbol >50% of class PnL)

**Time-box:** Max 30-day exemption, auto-revoke if rolling 10-trade WR <45%.

**The `_STREAK_CACHE` in `quality_gates.py` (line 258) is already computed but NEVER used for admission decisions.** It should be wired to `streak_exemption_engine.py`.

---

### Q3: Do certain trades fluctuate between 2 prices and are basically a sure thing?

**Answer: No "sure thing" exists. The closest evidence is bounded mean-reversion on 3 structural oscillations (per Opus 4.7 analysis).**

| Candidate | Structural Driver | Evidence | Confidence | Regime Break Risk |
|---|---|---|---|---|
| **YM=F ConnorsRSI2** | Broad-index mean-reversion | 13/13 wins, +1.95%/trade | Medium | DXY super-trend, VIX>30 |
| **AUDUSD=X carry MR** | Interest rate differential | PF 3.55 SHORT n=11 | Low-Medium | DXY trend >2σ, NFP/FOMC |
| **BTCUSDT VWAP+Funding** | Funding exhaustion + DXY neutral | Connors 75%+ pattern | Low-Medium | ETF approval, halving, macro |
| **TLT/IEF yield curve** | 10Y–2Y spread oscillation | Academic (Moskowitz 2012) | Low | Rate shock, FOMC surprise |

**Critical caveat:** All four BREAK during regime shifts. AUDUSD broke in 2022 rate-hiking cycle. BTC broke on ETF approval. TLT/IEF broke in 2022 bond crash. The correct posture: **treat oscillation strategies as high-frequency, low-duration pilots with hard regime-change stops (auto-revoke when DXY/VIX/MOVE >2σ).**

**Proposed `oscillation_detector.py` pipeline:**
```
For each symbol with n≥30 closed picks:
  1. Hurst exponent H<0.5 = mean-reverting
  2. 30d rolling PF of ConnorsRSI2 signals
  3. 30d range <5% of price = oscillation candidate
  4. Regime: DXY neutral (±0.5%), VIX<25, MOVE<20d MA
  5. Flag IS_OSCILLATING=True if H<0.4 AND range<5% AND regime=neutral
  6. Auto-exempt from trend-following gates when oscillating
  7. Auto-revoke when regime shifts (>2σ DXY/VIX/MOVE move)
```
Env: `OSCILLATION_DETECTOR_ENABLED=1` (default OFF)

---

## Batch A — Observability & Governance (next 7 days)

### PR-009: Rejected Picks Audit Lane (completes PR-8)
- Log every `return False` in `passes_active_gate` to `rejected_picks_log.json`
- Shadow table: hypothetical outcome if pick had been emitted (price fetch at decision time + 48h forward)
- Files: `audit_trail/rejected_picks_logger.py`, `audit_dashboard/template.html` (new panel)
- Acceptance: dashboard shows "what we missed" metric per class

### PR-010: Hot-Streak Exemption Engine (MiMo formalization)
- Wire `_STREAK_CACHE` to admission logic with bounded rules (see Q2 above)
- Files: `audit_trail/streak_exemption_engine.py`, `audit_trail/quality_gates.py` (import + call)
- Acceptance: exemption decisions logged with evidence hash, auto-revoke on WR drop

### PR-011: Oscillation-Detection Scanner
- Auto-flag symbols with 14d RSI(2) mean-reversion behavior + Hurst exponent
- Files: `tools/oscillation_detector.py`
- Output: `oscillation_candidates.json` consumed by `futures_strategies.py` + `etf_strategies.py`
- Acceptance: at least 1 symbol flagged in 48h backtest with H<0.4

### PR-012: DB Schema — MiniMax 5-Table Layout (Canonical)
**Replaces my v1 3-table proposal.** MiniMax Agent (partner #8) won meta-synthesis with audit-log tables:

```sql
-- incidents (severity P0-P3, status transitions)
-- enhancements (impact, effort S/M/L/XL, status)
-- roadmap_items (quarter, theme, links to incident_ids + enhancement_ids)
-- incident_resolution_log (every status change with actor + timestamp)
-- enhancement_progress_log (every progress update with actor + timestamp)
```

**Why this wins over v1 `findings` single table:**
- Full audit trail (who changed what when)
- Multi-AI peer-review provenance (each partner's contribution = a row in progress_log)
- Python query API examples already specified by MiniMax

**Migration path:**
1. Seed from existing `reports/incidents_*.md` via parser
2. Wire `audit_trail/dashboard_generator.py` to read tables for `/audit/incidents.html`
3. Add `incident_id`/`enhancement_id` to every PR template for auto-linking
4. Meta-synthesis provenance: every partner review gets a `progress_log` entry

**Files:**
- `db/migrations/2026_05_27_roadmap_items.sql`
- `tools/roadmap_query_api.py` — `get_p0_incidents_by_class()`, `link_enhancement_to_roadmap()`

---

## Batch B — Asset-Class Corrective PRs (next 14 days)

### EQUITY
1. **Merge VIX regime sidecar branch** (`feat/equity-vix-regime-gate-sidecar-2026-05-13`) — backtest PF 5.37
2. **PEAD strategy on top-100 LC** (M-009) — earnings post-announcement drift
3. **Overnight intraday reversal** (M-025) — module not created
4. **DOW tilt** (M-026) — Tue/Wed long bias hook in score_booster

### ETF
5. **Antonacci sector dual momentum 12-1** (M-023) — module not created
6. **Black-Litterman with Ledoit-Wolf fix** — prior LinAlgError on rolling cov
7. **FRED economic momentum** — blocked on no FRED_API_KEY

### COMMODITY
8. **COT MATCH gate + DSR≥0.85** (M-008) — `verify_system_pf.py` shipped but not called
9. **Carry-momo double-sort sidecar** (M-022) — Miffre 2010 replication
10. **Re-derive PF/WR post-PR-#994** — P0 data integrity

### FOREX
11. **Live carry_yield_diff from FRED** — replace static snapshot
12. **4-major universe limit** — EURUSD, GBPUSD, AUDUSD, USDJPY only
13. **Real CFTC COT data for 6E/6B/6J** — proxy z-score is noise
14. **SHORT-only sleeve + DXY confluence gate** — 48h PF 6.35 vs money_ready PF 0.21

### CRYPTO
15. **BTC UTC-hour death-zone filter** (M-001) — 08-09Z reject, 22Z boost
16. **ADV minimum gate (>$1M)** in production path
17. **On-chain momentum enable** (Glassnode MVRV-Z)
18. **Source whitelist emergency shrink** — 5 sources only (PR-4 in quick-wins)

### BOND
19. **FRED_API_KEY in GitHub secrets** (M-032)
20. **TIPS-Treasury breakeven MR** — Fleckenstein-Longstaff-Lustig 2014 pilot
21. **Cochrane-Piazzesi curve-carry** — TLT/IEF/SHY momentum
22. **HYG-LQD credit-spread MR** — 2σ bounce pilot

### FUTURES
23. **Unify futures taxonomy** — merge empty FUTURES tile into COMMODITY or standalone
24. **Micro contract support** — MES, MNQ, MGC
25. **Asia overnight MR pilot** — MGC/JPY futures
26. **ConnorsRSI2 YM=F → micro Dow pilot** (ENH-028)

### PENNY / MEME / IPO
27. **Permanent quarantine enforcement** — 0% risk, block all emitters
28. **IPO post-listing momentum** — replacement for failed lockup-short (PR-6)
29. **Cheap-stock (<$5) ADV gate** — no emission if float < $10M ADV

---

## Top-Notch Strategy Per Asset Class (12-Engine Consensus v2)

| Class | Strategy | Rationale | Expected PF | Evidence Quality | Blocker |
|---|---|---|---|---|---|
| **CRYPTO** | Liquid Core 25 + source whitelist + on-chain MVRV-Z | Shrink to BTC/ETH/SOL + top 7 L1s; block diluters | 1.45–1.60 | Medium | 0 closed in 48h; resolver corruption |
| **EQUITY** | VIX<22 + 12-1 momentum on 30 LC + PEAD overlay | Backtest PF 5.37; merge existing branch | 2.50–3.50 | **High** | Sidecar branch not merged |
| **ETF** | 11-Sector Rotation + VIX<25 + dual momentum | Faber/Antonacci academic; backtest PF 3.22 | 2.00–3.00 | **High** | VIX gate unwired |
| **COMMODITY** | Miffre carry-momo double-sort + COT dedup | Real edge; COT headline is artifact | 1.50–2.00 | Medium | COT DSR=1.0 contradiction |
| **FOREX** | 4-major SHORT-only + DXY confluence + session gate | SHORT PF 8.11 vs LONG PF 0.80 | 1.30–1.50 | Low-Medium | 48h vs money_ready contradiction; resolver sign bug |
| **BOND** | TIPS-Treasury breakeven MR + curve carry + credit MR | 3 academic pilots; research-only | Unknown | Low | n=11; no FRED key |
| **FUTURES** | ConnorsRSI2 on YM=F + micro Dow pilot | 13/13 in 48h; oscillation capture | 1.50–2.50 | Medium | BLOCKED_STRATEGIES; needs n>30 paper |
| **PENNY** | **NO PRODUCTION STRATEGY** | Quarantine permanently | N/A | N/A | N/A |
| **MEME** | **NO PRODUCTION STRATEGY** | Quarantine permanently | N/A | N/A | N/A |
| **IPO** | Post-listing momentum avoidance (90d long, SPY>200SMA) | Lockup short failed; pivot to momentum | Unknown | Low | Needs n≥100 backtest |
| **Cheap Stocks (<$5)** | **NO PRODUCTION STRATEGY** | Same as PENNY; ADV <$10M = block | N/A | N/A | N/A |

**Only 2 classes have HIGH evidence quality:** EQUITY (VIX<22 backtest) and ETF (sector dual momentum backtest). All others are MEDIUM or LOW and should NOT be sized up until n≥100 clean post-noise-filter trades.

---

## Incidents / Enhancements Dashboard Items (v2)

### New INCIDENT Rows (suggested)

| # | Type | Class | Priority | Title | Evidence |
|---|---|---|---|---|---|
| INC-029 | INCIDENT | FOREX | **P0** | 48h stats contradict money_ready by 77pp WR + resolver sign bug | `pick_summary_stats_48h` vs `money_ready_verdict.json` + `won_pnl_contradiction_dryrun_20260527_0400Z.json` |
| INC-030 | INCIDENT | ETF | P1 | WIN_RATE_TRAP_BLACKLIST orphaned — IWM/GLD still emitting | `quality_gates.py:1690` |
| INC-031 | INCIDENT | CRYPTO | **P0** | 0 closed in 48h (322 active) — class stalled | `pick_summary_stats_48h.json` |
| INC-032 | INCIDENT | OVERALL | P1 | No rejected-picks audit lane — cannot answer "what did we miss?" | Missing table |
| INC-033 | INCIDENT | FUTURES | P2 | 70% of =F activity misrouted to COMMODITY | Known from prior audits |
| INC-034 | INCIDENT | IPO | P2 | Lockup short strategy backtest FAILED all gates | `ipo_lockup_backtest_2026-05-17.md` |
| **INC-035** | **INCIDENT** | **OVERALL** | **P0** | **Resolver produces impossible PnL (-106,700% on TP_HIT_RESOLVED)** | **`won_pnl_contradiction_dryrun_20260527_0400Z.json`** |
| **INC-036** | **INCIDENT** | **OVERALL** | **P0** | **Data rot unchanged after 8h: 56k ghost rows, 99.99% trust_score NULL, 0.09% resolver coverage** | Grok 18-cycle loop + meta-synthesis |
| **INC-037** | **INCIDENT** | **COMMODITY** | **P1** | **CT=F 73% PnL concentration — single-symbol risk** | `money_ready_verdict.json` |

### New ENHANCEMENT Rows (suggested)

| # | Type | Class | Impact | Title |
|---|---|---|---|---|
| ENH-025 | ENHANCEMENT | OVERALL | HIGH | MiniMax 5-table schema + dashboard renderer + audit logs |
| ENH-026 | ENHANCEMENT | OVERALL | HIGH | Bounded hot-streak exemption engine (MiMo formalization) |
| ENH-027 | ENHANCEMENT | OVERALL | MEDIUM | Oscillation-detection scanner (Hurst + RSI(2) + regime) |
| ENH-028 | ENHANCEMENT | FUTURES | HIGH | ConnorsRSI2 YM=F → micro Dow paper pilot |
| ENH-029 | ENHANCEMENT | EQUITY | HIGH | PEAD earnings-drift sleeve on clean LC universe |
| ENH-030 | ENHANCEMENT | CRYPTO | HIGH | Source whitelist + noisy-source quarantine |
| ENH-031 | ENHANCEMENT | IPO | MEDIUM | Post-listing momentum strategy (replacement for lockup short) |
| ENH-032 | ENHANCEMENT | COMMODITY | HIGH | Carry-momo double-sort wiring (Miffre 2010) |
| ENH-033 | ENHANCEMENT | FOREX | MEDIUM | Live carry_yield_diff from FRED (not static snapshot) |
| ENH-034 | ENHANCEMENT | BOND | MEDIUM | TIPS/curve/credit MR pilot trio |
| **ENH-035** | **ENHANCEMENT** | **OVERALL** | **HIGH** | **Meta-synthesis provenance logging — every partner review = progress_log row** |
| **ENH-036** | **ENHANCEMENT** | **OVERALL** | **HIGH** | **Forward validator restart with EXPIRED_BACKLOG + batching + circuit breaker (code landed, needs server restart)** |
| **ENH-037** | **ENHANCEMENT** | **OVERALL** | **P2** | **WON PnL contradiction TP_HIT tolerance fix (code landed at 7e8ad9f21, may conflict with PR #15)** |

---

## 12-Engine Consensus Summary

| Partner | Model | Unique Contribution | Relevance to This Doc |
|---|---|---|---|
| #1 Grok 4.3 | xAI | 18-cycle recurring loop, QW-1 wiring call, tournament opt-in pattern | Data rot P0s unchanged; VIX+clean30LC only Tier-1 |
| #2 Opus 4.7 | Anthropic | Oscillation analysis (3 candidates), meta-synthesis, full end-to-end review | AUDUSD/X carry MR, BTC VWAP, TLT/IEF yield curve |
| #3 Sonnet 4.6 | Copilot | Quick-wins + remaining-items split | Structure of this doc |
| #4 Qwen | Alibaba | Alpha-engine drill-down | Quality gate line-by-line analysis |
| #5 DeepSeek-v4 | DeepSeek | Working code PR #16 (795 LOC), `audit_roadmap_seed.py` | Schema seeding script already exists |
| #6 GPT-5 | OpenAI | Comprehensive scope statement | Original ask decomposition |
| #7 GPT-5.4 | OpenAI | Deduplicated canonical report review | Avoided duplicate findings |
| #8 MiMo | Xiaomi | Hot-streak formalization, asset-class-specific gate profiles | Q2 exemption criteria |
| #9 MiniMax | MiniMax | 5-table DB schema + audit logs, 5-phase 12-week roadmap | PR-012 schema |
| #10 Mercury 2 | Inception Labs | Strategic-review table template (exemption column) | Top-notch strategy table format |
| #11 Kimi K2.6 v1 | Cloud | Direct answers to user questions, FOREX contradiction | Q1/Q2/Q3 foundation |
| **#12 Kimi K2.6 v2** | **Cloud** | **Enhanced synthesis of all 11 partners + new data** | **This file** |

**Consensus action:** All 12 engines independently converged on the same foundation order:
1. Data integrity P0s (PR-9)
2. QW-1 VIX regime gate wiring (PR-5)
3. CRYPTO source whitelist emergency shrink (PR-4)
4. FOREX contradiction + resolver corruption (PR-2)
5. Orphaned gate fixes (PR-1)
Everything else is research or secondary.

---

## Data Rot P0s — Universal Blocker Detail

These issues were **unchanged after 8+ hours of multi-engine analysis** and block ALL class-level credibility:

| Issue | Evidence | Severity | Code Status |
|---|---|---|---|
| Resolver coverage | ~0.09% of picks resolved | P0 | `forward_validator.py` restart landed at `3d1b237aa`, needs server restart |
| WON-label contradictions | TP_HIT with negative PnL (10 rows, -106,700% max) | P0 | Tolerance fix landed at `7e8ad9f21`, may conflict with PR #15 |
| Ghost rows | 56,000+ in DB | P0 | Not yet addressed |
| trust_score NULL | 99.99% of rows | P0 | Not yet addressed |
| CT=F concentration | 73% PnL mass single symbol | P1 | Concentration gate not enforced |
| COT DSR contradiction | cot_positioning DSR=1.0 vs BLOCKED benchmark | P1 | Verify logic in `verify_system_pf.py` |

**Until these are fixed, NO asset class can be promoted to Tier 1 or sized up.** The numbers in `money_ready_verdict.json`, `pick_summary_stats_*.json`, and the audit dashboard are all potentially contaminated.

---

## Verification Plan
- `py_compile` on all touched `.py` files
- `python3 tools/dedup_md_files.py --paths-only` on any batch review
- No local dashboard generation (per CLAUDE.md)
- Git push to origin/main after `git stash && git pull --rebase origin main && git stash pop`
- After any commit touching `updates/*.html`, run `python3 tools/deploy_audit_files.py --only updates`

---

## References
- `reports/EAGLE_quick_wins_2026-05-27_1031_EDT_Kimi_K2.6_Cloud.md` (v2)
- `reports/EAGLE_quick_wins_2026-05-27_0231_EDT_Kimi_K2.6_Cloud.md` (v1)
- `reports/EAGLE_remaining_items_2026-05-27_0231_EDT_Kimi_K2.6_Cloud.md` (v1)
- `reports/EAGLE_range_bound_2026-05-27_claude_opus_4_7.md`
- `reports/EAGLE_2026-05-27_1016_EST_Grok43_xAI_scheduled_continuation.md`
- `reports/EAGLE_2026-05-27_0218_EDT_Claude-Opus-47_Anthropic_meta_synthesis_5partner_review.md`
- `reports/won_pnl_contradiction_dryrun_20260527_0400Z.json`
- `reports/won_pnl_contradiction_dryrun_20260527_0627Z.json`
- `tools/ai_tournament/tournament_quality_gates.py`
- `audit_dashboard/data/pick_summary_stats_48h.json`
- `audit_dashboard/data/money_ready_verdict.json`
- `audit_trail/quality_gates.py:1690`
- `reports/ipo_lockup_backtest_2026-05-17.md`
