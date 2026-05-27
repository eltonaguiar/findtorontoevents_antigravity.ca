# EAGLE Quick Wins — Kimi K2.6 Cloud Review
**Date:** 2026-05-27 02:31 EDT | **Model:** Kimi K2.6 (via Cloud)  
**Branch:** `eagle-quickwins-2026-05-27`  
**Scope:** End-to-end audit across all asset classes + IPOs + safety-gate exemption analysis

---

## Executive Summary

This review builds on the Opus 4.7 and GPT-5.4 audits from 2026-05-27 and adds **live-data findings** from `pick_summary_stats_48h.json` (2026-05-25T05:52Z) + `money_ready_verdict.json` (2026-05-26T07:31Z) + `quality_gates.py` line-level code review.

**Kimi-specific discoveries:**
1. `WIN_RATE_TRAP_BLACKLIST` (IWM/GLD) is **defined but NEVER CHECKED** in `passes_active_gate` — orphaned gate since at least 2026-05-17.
2. **FOREX 48h stats show 86.2% WR / PF 6.35** (n=29) while `money_ready_verdict.json` reports 9.1% WR / PF 0.21 (n=11) — a 77pp contradiction requiring immediate investigation.
3. **FUTURES ConnorsRSI2 on YM=F** produced 13/13 winners in 48h (PF=inf) — the closest evidence we have of a repeatable oscillation-capture strategy.
4. **CRYPTO 0 closed in 48h** (322 active, all unresolved) — confirms class collapse; source whitelist is now urgent, not optional.
5. **IPO lockup short strategy backtest FAILED** (PF 0.18, WR 34.8%, n=23) — literature edge (Field & Hanka 2001) does NOT reproduce; recommend pivot to post-IPO momentum avoidance.

---

## PR-1: Wire Orphaned WIN_RATE_TRAP_BLACKLIST into passes_active_gate
**Impact:** MEDIUM | **Effort:** S | **Class:** ETF

**Finding:** `quality_gates.py:1690` documents: `"WIN_RATE_TRAP_BLACKLIST is NEVER CHECKED in passes_active_gate"`. The list contains `IWM` (n=19, WR 37%) and `GLD` (n=11, WR 36%) — both proven losers. Despite the blacklist existing, picks on these symbols still flow through to the dashboard because `passes_active_gate` never references the frozenset.

**Files:**
- `audit_trail/quality_gates.py` — add `WIN_RATE_TRAP_BLACKLIST` check near the ETF blacklist gate (~line 1608)

**Acceptance:**
- `passes_active_gate` rejects any pick where `symbol in WIN_RATE_TRAP_BLACKLIST`
- Dashboard ETF tile no longer shows IWM/GLD emissions
- Add env kill-switch `WIN_RATE_TRAP_GATE_DISABLED=1` (fail-open pattern)

---

## PR-2: FOREX Contradiction Audit — 48h Stats vs money_ready Verdict
**Impact:** CRITICAL | **Effort:** S-M | **Class:** FOREX

**Finding:** The 48h panel (`pick_summary_stats_48h.json`) shows FOREX with 25 wins / 4 losses (86.2% WR, PF 6.35, mean PnL +0.31%) — almost entirely USDCAD=X LONG via `regime_mild_bull`/`regime_accumulation`. Meanwhile `money_ready_verdict.json` (generated 26h later) shows FOREX n=11, WR=9.09%, PF=0.21, verdict=INSUFFICIENT_DATA.

**This is not a rounding error — it is a 77 percentage point win-rate contradiction.**

Root causes to investigate:
- `money_ready_verdict.py` may filter out AlphaEngine-only source systems (48h shows 100% AlphaEngine concentration)
- The 48h picks may still be OPEN misclassified as CLOSED in the JSON generator
- `won_pnl_contradiction_dryrun_20260527_0627Z.json` already found 3 rows where `exit_reason="TP_HIT"` but `pnl_pct` is negative (-0.03%) — this proves the resolver/dry-run logic has TP/SL sign bugs

**Files:**
- `alpha_engine/money_ready_verdict.py` — trace FOREX n filtering
- `tools/audit_pick_funnel/dry_run_resolver.py` — fix TP_HIT/SL_HIT sign logic
- `audit_dashboard/data/pick_summary_stats_48h.json` — verify closed-vs-open classification

**Acceptance:**
- Reconcile n=11 vs n=29: identify which filter drops 18 FOREX picks
- If the 48h numbers are real → FOREX LONG on USDCAD=X may deserve a SHORT-ONLY exemption relaxation (bounded)
- If the 48h numbers are bugs → fix the generator before any FOREX allocation decision

---

## PR-3: Promote FUTURES ConnorsRSI2 on YM=F to Paper Pilot
**Impact:** HIGH | **Effort:** S | **Class:** FUTURES

**Finding:** In the last 48h, `futures_connors_rsi2` on `YM=F` (Dow e-mini) produced **13 wins / 0 losses** (PF=inf, +1.95% per trade, ~20,000 min hold times). This is a classic Larry Connors RSI(2) mean-reversion strategy — buy when RSI(2) < 10 on a broad index futures contract, sell on reversion.

YM=F is a **highly liquid, range-bound instrument** during the observed period. ConnorsRSI2 is explicitly designed for oscillating, mean-reverting behavior. This is the **only credible evidence in the entire system of a repeatable oscillation-capture edge**.

**Files:**
- `alpha_engine/futures_strategies.py` — verify ConnorsRSI2 params (period=2, threshold=10, exit=RSI>50)
- `audit_trail/quality_gates.py` — unblock `futures_connors_rsi2` from BLOCKED_STRATEGIES if present
- `tools/paper_trade_pilot.py` — start 30d paper on YM=M (micro Dow) with $1/tick sizing

**Acceptance:**
- ConnorsRSI2 emits YM picks without gate rejection
- Paper pilot tracks: WR, PF, avg hold time, max consecutive wins/losses
- If 30d paper shows PF>1.5 / WR>55% / n>20 → promote to live micro sizing (0.1% risk)
- If it fails → archive with note "ConnorsRSI2 works only in specific regimes; needs VIX<20 filter"

**Note:** `NG=F` (natural gas) LONG via `cta_cross_asset_tsmom` also shows 100% WR but n=1, hold=162 min — noise, not edge.

---

## PR-4: CRYPTO Source Whitelist — Emergency Shrink
**Impact:** CRITICAL | **Effort:** M | **Class:** CRYPTO

**Finding:** 0 closed picks in 48h (322 active, all unresolved). The 14d panel already collapsed from 78.9% → 38% WR. The class is producing volume but not resolutions — a classic sign of stale/dud signals accumulating.

Immediate whitelist (highest-PF sources from prior audits):
- `mega_mutation` (PF 2.29)
- `dna_winner_picks` (PF 1.88)
- `aggregated_picks` (PF 1.88)
- `kimi_riseoftheclaw` (PF 1.57)
- `baby_strats_forward` (PF 1.46)
- `claude_gainer_st` (PF 6.80 historically but only 3 closed in raw DB — treat as research-only until n>50)

**Block immediately:** `luxalgo_filters` (23% vol, PF 1.07), `alpha_engine` (12% vol, PF 0.99), `quan_engine` (10.5% vol, PF 1.36 WR 35%), `copy_trader_highscore`, `battleground`, `regime_terminal`.

**Files:**
- `audit_trail/quality_gates.py` — add `CRYPTO_SOURCE_WHITELIST` check in `passes_active_gate`
- `alpha_engine/production_scanner.py` — reject non-whitelisted CRYPTO sources at scanner level
- Env: `CRYPTO_SOURCE_WHITELIST_ENABLED=1`

**Acceptance:**
- Non-whitelisted CRYPTO sources emit zero dashboard picks
- CRYPTO n drops ~30-40% but expected PF rises +0.15-0.30
- 48h closure rate improves from 0 → >5

---

## PR-5: ETF VIX<25 Gate Wire-Up
**Impact:** HIGH | **Effort:** S | **Class:** ETF

**Finding:** Already identified by Opus 4.7 and GPT-5.4. Still unwired as of this review. `vix_regime_gate.py` exists and handles ETF, but `etf_sector_emitter.py` never calls it before emitting picks.

Backtest: VIX<25 → PF 3.22 / Sharpe 1.63 / MDD 11.8% (Tier-1 PF, Tier-2 MDD).

**Files:**
- `tools/etf_sector_emitter.py` — add VIX check before generating rotation picks
- `audit_trail/vix_regime_gate.py` — verify ETF asset class handling

**Acceptance:**
- ETF emitter produces 0 picks when VIX≥25
- VIX<25: emitter runs normally
- Dashboard ETF PF converges toward backtest 3.22 over next 30d

---

## PR-6: IPO Strategy Pivot — Kill Lockup Short, Test Post-IPO Momentum Avoidance
**Impact:** MEDIUM | **Effort:** M | **Class:** IPO (EQUITY sub-class)

**Finding:** `reports/ipo_lockup_backtest_2026-05-17.md` proves the IPO lockup short strategy FAILS all 4 evaluable §23 gates:
- n=23 (FAIL, need ≥100)
- WR=34.8% (FAIL, need >50%)
- PF=0.18 (FAIL, need >1.5)
- Walk-forward decay: 2022 +17.9% → 2024 −116.6% → 2025 −46.5% (severe decay)

The Field & Hanka 2001 thesis (post-lockup selling pressure) does NOT reproduce in 2024-2025 bull-market IPOs. RDDT, ALAB, VKTX, etc. rallied THROUGH lockup expiry, hitting 15% short stops.

**Pivot:** Instead of shorting lockup expiry, test the **inverse** — go LONG on recent IPOs (first 90 days) with strong opening-day momentum, or simply AVOID the lockup window entirely. Academic evidence (Ritter 2020) shows IPO underperformance is a 3-5 year phenomenon, not a 10-day lockup window.

**Files:**
- `alpha_engine/ipo_lockup_strategy.py` — deprecate short logic, add post-IPO momentum pilot
- `alpha_engine/ipo_data_pipeline.py` — fix Nasdaq API date normalization (`M/D/YYYY` → ISO)

**Acceptance:**
- No live emissions from `ipo_lockup_strategy` until new backtest clears T2
- Historical IPO calendar expanded to 300+ names (EDGAR S-1 or stockanalysis.com)
- New backtest: long-only, first 90 days, SPY>200SMA filter

---

## PR-7: EQUITY Universe Split — Remove 8 Speculative Tickers
**Impact:** HIGH | **Effort:** S | **Class:** EQUITY

**Finding:** Already flagged by Opus 4.7 and GPT-5.4. The 48h panel confirms the problem: EQUITY is 100% AlphaEngine-sourced with single-source concentration. While 48h PF is strong (2.85), the narrow universe (18 names, 8 speculative) creates idiosyncratic risk.

Split:
- `LARGE_CAP_EQUITY_SYMBOLS`: AAPL, MSFT, NVDA, TSLA, AMZN, GOOGL, META, AMD, COIN, MSTR, AVGO, UNH, V, LLY, JPM, WMT, XOM, PG, JNJ, BAC, HD, COST, KO, PEP, BA, CAT, CRM, NFLX, DIS
- `SPECULATIVE_RESEARCH_SYMBOLS`: PLTR, SOFI, RIVN, LCID, NIO, SNDL, GME, AMC

**Files:**
- `alpha_engine/config.py` — add split lists
- `alpha_engine/equity_strategies.py` — block speculative list from live emission

**Acceptance:**
- 0 live emissions from NIO/LCID/RIVN/SNDL/GME/AMC as EQUITY picks
- EQUITY dashboard tile shows concentration shift to LC

---

## PR-8: Add Profitable-but-Filtered Audit Lane (Shadow Table)
**Impact:** MEDIUM | **Effort:** S-M | **Class:** OVERALL

**Finding:** The user explicitly asked: "do we have picks that would have won big, but our safety gates consistently filtered them out?" Today there is NO table tracking rejected picks and their hypothetical forward outcomes.

**Implementation:** Add a `rejected_picks_audit` table (or JSON sidecar) that logs every pick rejected by `passes_active_gate` with:
- `symbol`, `strategy`, `source_system`, `rejection_reason`, `rejection_gate`, `timestamp`
- `hypothetical_outcome`: resolved via yfinance OHLCV after 7d/14d hold
- `would_have_won`: boolean
- `missed_pnl_pct`: float

This answers the user's question with data, not opinion.

**Files:**
- `audit_trail/rejected_picks_logger.py` — new module
- `audit_dashboard/data/rejected_picks_audit.json` — shadow output

**Acceptance:**
- Every `return False` in `passes_active_gate` logs a row before returning
- Weekly cron resolves hypothetical outcomes
- Dashboard shows "filtered winners per gate" breakdown

---

## Implementation Order
1. PR-2 (FOREX contradiction — data integrity P0)
2. PR-4 (CRYPTO emergency whitelist — 0 closures)
3. PR-1 (Orphaned WIN_RATE_TRAP — smallest fix)
4. PR-5 (ETF VIX gate — backtested, just needs wiring)
5. PR-7 (EQUITY split — removes drag)
6. PR-3 (FUTURES ConnorsRSI2 pilot — evidence-based)
7. PR-8 (Rejected-picks audit — observability)
8. PR-6 (IPO pivot — research-only)

---

## References
- `reports/EAGLE_end_to_end_review_2026-05-27_claude_opus_4_7.md`
- `reports/EAGLE_quick_wins_2026-05-27_claude_opus_4_7.md`
- `updates/QUICK_WINS_EAGLE_2026-05-27_0217_EST_GPT-5.4_OpenAI.md`
- `audit_dashboard/data/pick_summary_stats_48h.json`
- `audit_dashboard/data/money_ready_verdict.json`
- `audit_trail/quality_gates.py:1690` (orphaned WIN_RATE_TRAP)
- `reports/ipo_lockup_backtest_2026-05-17.md`
- `tools/dedup_md_files.py` + `.claude/skills/dedup-md-files/SKILL.md`
