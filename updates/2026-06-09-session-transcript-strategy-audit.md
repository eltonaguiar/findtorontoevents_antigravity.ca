# Session Transcript — 2026-06-09: Top-Notch Strategies Per Asset Class

> **⚠️ SUPERSEDED / PARTIALLY REFUTED (2026-06-09 audit):** Several claims in this transcript
> (FOREX 14d 64.2% WR / PF 2.43, GBPUSD n=114 WR 58.8%, stocks_rsi2_pullback PF 2.68,
> "Forex is winning") were **independently falsified** against clean DB cohorts.
> Authoritative verdict: `reports/OBS_FINDING_JUNE8.MD`, `reports/UPDATED_MONEY_READY_RECOMMENDATION_2026-06-09.md`,
> `money_ready_verdict.json` (0/9 Tier-2). **Do not size up from this doc without re-verification.**

**Model**: DeepSeek V4 Flash  
**Mode**: Plan mode  
**Repo**: `findtorontoevents_antigravity.ca`

---

## User Request (Initial)

> "Lot of time has passed, proceed on your next steps, use subagents & parallel coding as needed. We need to get top-notch strategies, statistically proven, per asset class. For now, focus on the low hanging fruit with one subagent and let them summon a team of subagents as needed to work on sub-tasks and research etc. We have research here `https://findtorontoevents.ca/audit/research_index.html` we also have "picks now" `https://findtorontoevents.ca/audit/picks-now.html` double-check their quality. Use subagents."

---

## Phase 1 — Data Gathering

### Fetched Pages
- **Research Index** (`findtorontoevents.ca/audit/research_index.html`): Multi-AI 5-pass orchestration runs per asset class. Verdicts: ALL classes either NO_EDGE or MIXED. None achieve Tier-2 (n≥100, PF≥1.5, WR≥50%, MDD<20).
- **Picks Now** (`findtorontoevents.ca/audit/picks-now.html`): Quant multifactor screener (330 symbols → 20 picks). AI Tournament leaders: cursor_agent (66.1% WR, PF 2.35, n=59), deepseek_v4 (PF 3.72, n=43), llama4_scout (61.4% WR, n=57), grok3 (58.4% WR, PF 2.02, n=89). 0/8 classes money-ready.

### Local Data Files Read
- `audit_dashboard/data/money_ready_verdict.json` (June 8, 2026)
- `audit_dashboard/data/top_notch_money_ready.json` (June 6, 2026)
- `audit_dashboard/data/pick_summary_stats_14d.json` (June 5, 2026)
- `audit_dashboard/data/pick_summary_stats_48h.json` (June 5, 2026)
- `alpha_engine/production_scanner.py` (line 488: stocks_rsi2_pullback removal context)
- `alpha_engine/data/freshpicks_sent.json` (active emissions)
- `low_hanging_fruit_report.md` (pre-existing report)

### Key Findings

| Class | 14d WR | 14d PF | Clean n | Official Verdict |
|-------|--------|--------|---------|-----------------|
| **FOREX** | **64.2%** ✅ | **2.43** ✅ | 22 ❌ | INSUFFICIENT_DATA |
| **EQUITY** | 44.3% | 1.32 | 71 ❌ | INSUFFICIENT_DATA |
| **CRYPTO** | 40.1% | 6.54 | 171 ✅ | NOT_READY |
| **COMMODITY** | — | — | 15 ❌ | INSUFFICIENT_DATA |
| **ETF** | — | — | 18 ❌ | INSUFFICIENT_DATA |
| **FUTURES** | — | — | 20 ❌ | INSUFFICIENT_DATA |
| **BOND** | — | — | 0 ❌ | INSUFFICIENT_DATA |

**Top per-symbol edges**:
- FOREX: GBPUSD=X (n=114, WR 58.8%), EURGBP=X (n=171, WR 56.1%), USDCHF=X (n=99, WR 60.6%)
- CRYPTO: FETUSDT (n=69, WR 81.2%), TONUSDT (n=59, WR 71.2%), STRKUSDT (n=63, WR 69.8%)
- CRYPTO: RENDERUSDT inverse_ml (n=15, WR 80%, PF 7.7)
- EQUITY: stocks_rsi2_pullback (n=894, WR 58.8%, PF 2.68 — 5/6 gates, recency fail)

**AI Tournament Leaders**:
- cursor_agent 🥇 — 66.1% WR, PF 2.35, n=59 (most balanced)
- deepseek_v4 🥈 — PF 3.72, 55.8% WR, n=43 (highest PF, big avg win +4.8%)
- llama4_scout 🥉 — 61.4% WR, PF 2.26, n=57 (solid but unremarkable)
- grok3 — 58.4% WR, PF 2.02, n=89 (most picks, diluted edge)

**Existing `low_hanging_fruit_report.md` candidates**:
1. stocks_rsi2_pullback (EQUITY) — 5/6 gates passed, recency fail
2. GBPUSD=X / EURUSD=X (FOREX) — 4/6 gates, need PF/DSR
3. RENDERUSDT inverse_ml (CRYPTO) — 4/6 gates, need n≥100
4. V, SPY (ETF) — 3/6 gates, need 6-month backtest

---

## User Follow-Up: "What does clean N mean?"

**Answer**: Clean N = resolved trades that survived noise filters: flicker dedup, EXPIRED→WON mislabel correction, resolver threshold fixes (PNL_WIN_THRESHOLD_BY_CLASS, v2.1 May 2).

Three N's in play:
- `n_resolved` in `money_ready_verdict.json` — all closed trades, pre-filter
- `n_clean` in `top_notch_money_ready.json` — post-noise-filter
- Per-symbol `n` in `at_pick_outcomes` DB — richer data (e.g. GBPUSD=X shows n=114 vs class-level n=25)

**Tier-2 threshold**: n ≥ 100 clean, WR ≥ 50%, PF ≥ 1.5, MDD < 20%

**Discrepancy**: FOREX shows n=25 at class level (filtered `closed_picks` source) but GBPUSD=X alone has n=114 in the DB (`at_pick_outcomes`). The DB per-symbol count is more complete.

---

## User Follow-Up: "Review low_hanging_fruit_report.md and merge to super plan"

The existing report was read from `/home/eaguiar2015/findtorontoevents_antigravity.ca/low_hanging_fruit_report.md`. It identified 4 concrete action items with implementation-ready specificity.

**Merged Super Plan** was created and saved to `/memories/session/plan.md`. Structure:

### Phase 1: Investigate — 4 Parallel Subagents

| Agent | Focus | Key Questions |
|-------|-------|---------------|
| **A** — FOREX Deep Dive | Why 64% WR? Expand pairs? | 30-day fwd test design, source concentration risk |
| **B** — Picks Quality Audit | Current picks, AI Tournament | How good are AMZN/AAPL/NVDA/META? cursor_agent secrets? |
| **C** — stocks_rsi2 Resurrection | Why killed? Can mutation revive? | production_scanner.py line 488, mutation_tracker |
| **D** — CRYPTO Bootstrap + ETF | Push RENDER→n=100, ETF backtest | 90-day rolling bootstrap, V/SPY quick-win |

### Phase 2: Synthesis
Cross-reference findings, rank by ROI, produce `reports/super_synthesis_2026-06-09.md`

### Phase 3: Implementation (contingent)
Concrete code changes from Phase 2 recommendations

**Ranked implementation candidates** (from merged plan):

| # | Candidate | Gates | Action | Est. Effort |
|---|-----------|-------|--------|-------------|
| 1 | stocks_rsi2_pullback (EQUITY) | 5/6 ✅ | Re-activate emission (adjust RSI, daily schedule) | 1-2 days |
| 2 | GBPUSD=X / EURUSD=X (FOREX) | 4/6 ✅ | 30-day forward test for PF/DSR | 2-3 days |
| 3 | RENDERUSDT inverse_ml (CRYPTO) | 4/6 ✅ | Bootstrap on 90-day historic windows | 3-5 days |
| 4 | V, SPY (ETF) | 3/6 ✅ | 6-month backtest for DB metrics | 3-5 days |

### Relevant Files
- `low_hanging_fruit_report.md` — existing concrete action plan
- `alpha_engine/production_scanner.py` — line 488: stocks_rsi2_pullback removal
- `alpha_engine/data/dna_mutation_tracker.json` — mutation records
- `tools/picks_now_professional.py` — picks-now generator
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md` — strategy revive protocol
- `audit_dashboard/data/money_ready_verdict.json` — official verdict
- `audit_dashboard/data/top_notch_money_ready.json` — top edges per class
- `audit_dashboard/data/pick_summary_stats_14d.json` — recent window
- `audit_dashboard/data/pick_summary_stats_48h.json` — ultra-recent

---

## Key Decisions Made

1. **FOREX** is the most intriguing low-hanging fruit (14d WR 64%, PF 2.43) but has a data source discrepancy — class-level verdict (n=25) vs DB per-symbol (n=57-171). Need discrepancy investigation.
2. **stocks_rsi2_pullback** has the most proven stats (894n, 58.8% WR, PF 2.68) and passed 5/6 gates, but the emission pipeline is broken and 14d WR collapsed to 29.9%. Needs mutation diagnosis.
3. **AI Tournament leaders** (cursor_agent, deepseek_v4) have distinct winning patterns worth studying to improve overall pick quality.
4. **All changes remain paper/research-only** — no live deployment without explicit approval.
5. **Phase 1 subagents were NOT dispatched** — user asked to merge plans first before proceeding to execution.

---

## Notes

- Session goal: Goal #1 from CLAUDE.md (phenomenal performance across ALL asset classes on `/audit`)
- Current state: 0/6 classes pass Tier-2 minimums
- Clean N definition is critical for understanding the discrepancy between `money_ready_verdict.json` (gates-based) and `low_hanging_fruit_report.md` (DB per-symbol counts)
- The merged super plan is ready for Phase 1 dispatch when approved
