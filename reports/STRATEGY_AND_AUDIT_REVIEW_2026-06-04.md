# Strategy / DB-Tracking / Audit Review — 2026-06-04

3-agent grounded review (DB SELECTs + canonical JSON + 2-week MD digest). Every number cited to a
table/file. No fabrication. Sources: `money_ready_verdict.json` + `pf_registry.json` (gen 2026-06-05
01:50Z), `ai_tournament_leaderboard.json` (gen 2026-06-05 00:03Z), live `ejaguiar1_stocks` /
`ejaguiar1_backtests`, ~30 substantive MDs from 2026-05-21→06-05.

## 1. /audit money-ready — 0 of 9 classes ready (current)
`summary.money_ready=[]`, `watch=[]`. CRYPTO **NOT_READY** (n=311, WR 36.3%, PF 0.98; fails dsr/pbo/
spa/expectancy/mdd/cvar). All others **INSUFFICIENT_DATA**: EQUITY n=46 WR24% PF0.25 · FOREX n=22 WR23%
PF11.2 (small-n artifact, fails n-gate) · FUTURES n=15 WR6.7% PF0.38 · ETF n=11 WR63.6% PF0.80 ·
COMMODITY n=4 PF10.5 (n=4!) · BOND n=0 · PENNY n=1. **No proven real-money edge anywhere.**

## 2. Strategy tracking per asset class — INCOMPLETE / partly broken
Canonical per-engine tracker `at_strategy_stats` (175 rows, single batch 2026-05-31). Schema gotcha:
its `strategy` column is the conviction TIER; `source_system` is the real engine; **no PF column**.

| Class | Tracked in at_strategy_stats | True-PF table | Status |
|---|---|---|---|
| CRYPTO | ✅ 87 rows | at_strategy_symbol_performance (410, **3-mo STALE** Mar-06) | best-covered |
| MEMECOIN | ✅ 45 rows | — | folded into crypto |
| EQUITY | ⚠️ 7 rows (3 engines, all failing: 0–24% WR) | algorithm_performance (23, **STALE** Feb-Mar, all negative) | thin |
| FOREX | ❌ dead: 2 rows / 0 wins (vs 8,640 raw picks, 15,538 outcomes) | fx_algo_performance (8 rows, **all 0 picks, STALE Feb-09**) | untracked |
| FUTURES | ❌ 0 rows (vs 4,094 raw picks, 246 in last 14d) | none | **untracked** |
| ETF | ❌ 0 rows (vs 421 raw picks) | none | **untracked** |
| BOND | ❌ 0 rows (vs 90 raw picks) | none | **untracked** |
| COMMODITY | ❌ 0 rows (vs 5,723 resolved) | none (only eagle2_methodology) | **untracked** |
| PENNY | ❌ 0 rows (vs 494 raw picks) | none | **untracked** |

Real emission ledger `at_raw_picks` (74,269) DOES carry per-class strategy names; outcomes in
`at_pick_outcomes` (39,098) + `at_signal_outcomes` (240,869). `at_incubator_strategies` (344, true
PF/Sharpe/MDD) is FRESH (2026-06-04) but crypto-technical only. eagle2_methodology (10) +
eagle2_consensus_picks (15) present in ejaguiar1_backtests.

## 3. AI tournament (ai-tournament.html)
Real-n leaders: **grok3** n=97 WR54.6% PF2.16 T2 (actively picking) · **kimi_direct** n=52 PF2.78 T1 +
**llm7_qwen** n=39 PF2.40 T1 — but BOTH T1 are **STALE (no picks since 2026-05-24)**. **deepseek_v4**
rank6/T3 n=39 WR48.7% PF1.92, **PF CI lower 0.86 < 1** — consistent with its leakage-free attribution
failure (t=1.74); the "PF 3.46 best edge" framing is **debunked** (reports/attribution_probe_2026-06-03).
Tiny-n PFs (nvidia_minimax n=1 PF10, gpt4o_mini n=4) are pure noise. `tournament_model_stats` DB table
is STALE (2026-05-22, contradicts JSON) — ignore it; DB `tournament_picks` resolution lags the JSON snapshot.

## 4. Edge consensus (2-week MD digest)
Only **ETF dual-momentum (H-103)** clears the full clean-bar gate-stack (attr t=2.36, beta0.34, Sharpe
1.62, OOS holds) — a forward-pilot CANDIDATE, not money-ready; enable flag OFF, needs n≥100. 4 other
archetypes REJECTED/MIXED (all beta/survivorship). `tools/data/latest_scorecard.md` (06-05): every
strategy in every class = UNPROVEN.

## 5. NEW issues found this review (logged)
- **Tracking gap (ENHANCEMENT):** FUTURES/ETF/BOND/COMMODITY/PENNY emit picks (FUTURES 246/14d) with ZERO strategy-level perf tracking in `at_strategy_stats` — only raw/outcome ledgers.
- **Stale trackers (INCIDENT):** fx_algo_performance (Feb-09), at_strategy_symbol_performance (Mar-06), algorithm_rolling_perf (Apr-27), algorithm_performance (Feb-Mar) — per-strategy perf not refreshing.
- **Corrupt data (INCIDENT):** `cr_algo_performance` "CR Mean Reversion" avg_return 95,692% on 288 trades — units/aggregation bug; do not cite.
- **Asset_class tagging bug:** 32 blank-class rows in at_strategy_stats; fragmented labels (STOCKS vs STOCK, MEME vs MEMECOIN, PENNY/PENNYSTOCK) in at_pick_outcomes → undercounts on class aggregation.
- **INCIDENT #91 (P0, prior):** 8–43× duplicate inflation in at_signal_outcomes (opened_at NULL → unique index never fires). Dashboard verdict JSON dedups (user-facing safe); raw-table analysis NOT.

## 6. Disputed / do-not-cite (confirmed stale)
78.9% CRYPTO Smart-Picks (real 36.3%); FOREX PF 11.2 / COMMODITY PF 10.5 (small-n); deepseek_v4 PF3.46
(debunked); luxalgo_confluence PF 2.36 vs OVERFIT_LIKELY@n=31 (dedup-window discrepancy — reconcile before sizing).

## 7. Top pending (operator-gated)
1. Rotate DB password (#89; literal still in git history). 2. Flip `ETF_VERIFIED_DUAL_MOMENTUM_ENABLED=1` to start the one validated candidate's forward clock. 3. INCIDENT #91 dedup index (maintenance window). 4. Refresh the stale per-class strategy trackers (esp. FOREX dead, FUTURES/ETF/BOND untracked). 5. Wire `is_admissible_for_production()` into the scanner emission path.

**Bottom line:** numbers are honest (0/9 money-ready, 1 lab candidate). The real operational gap is
**strategy-level tracking**: 5 asset classes emit picks with no perf table, and the crypto/FX/equity
trackers are stale. Fixing tracking is prerequisite to ever evaluating per-class edge properly.
