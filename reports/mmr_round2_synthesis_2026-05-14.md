# MMR Round-2 Synthesis — Deep-Dive + Strategy Roadmap

**Date:** 2026-05-14 UTC. **Inputs:** money-maker-ready audit (PR #986) + Round-1 swarm (10 cavecrew-investigator agents) + Round-3 second-opinion consult (DeepSeek).

## 0. TL;DR

Three blocker fixes shipped in Round 2 PRs (#993, #994, #995). Round-3 consult identifies 5 P0 ship candidates and 5 traps to avoid. 5 additional candidates the swarm missed are flagged.

| Verdict | Item |
|---|---|
| ✅ Ship Round-2 | B2 walkforward gap (PR #993), B1 multi_asset_cot dedup (PR #994), ETF TLT/HYG lookup (PR #995) |
| 🚀 P0 next-90d | EQUITY RSI-2 SHORT, CRYPTO `proven_research_strategies` wire, EQUITY Earnings PEAD SHORT, CRYPTO `new_crypto_strategies_20` wire, FUTURES ES/NQ divergence (conditional on PR #946/#949) |
| ⚠ Trap | All 3 BOND candidates, all 3 COMMODITY candidates, CRYPTO `pattern_strategies` |
| 🔍 Missed by swarm | EQUITY put-writing on SPY/QQQ (biggest miss), CRYPTO basis trade, FUTURES VIX contango roll, ETF TLT put spreads, COMMODITY CL=F calendar spread |

## 1. Round-1 swarm findings (per-class)

### Blockers

**B1 — `multi_asset_cot` over-emission artifact (CONFIRMED)**
- File: `copy_trader_intel/multi_asset_copytrader_scraper.py:1160` emits `source_system="multi_asset_cot"`.
- 21 closed picks share 1 `latest_cot_date` = ~21× over-emission ratio.
- Same falsified shape as PR #961 fix.
- **Action: PR #994 ships — wires `_load_emitted_releases` / `_record_emitted_release` from `alpha_engine.cot_positioning` keyed on `(symbol, ISO-week-Monday)`.** Expected WR drops to ~47%, PF to ~1.1 (truthful revaluation).

**B2 — walkforward gap (BOND, FUTURES missing)**
- File: `alpha_engine/walkforward_validator.py:184-200`.
- Root cause: `DEFAULT_CLASS_WF_CONFIG` had no entries for BOND or FUTURES; default `min_trades=30` silently skipped BOND (n=12) and FUTURES (n=0).
- **Action: PR #993 ships — adds 2 config entries with `min_trades=5`.**

**B3 — `concept_drift.ks_d` / `ks_critical` are None**
- Root cause: 16-day stale cache at `tools/data/hf_stats_summary.json` + likely field-name mismatch (writer emits `ks_D` uppercase + `ks_critical_05`; reader may look for lowercase `ks_d` / `ks_critical`).
- **Action: TODO — invalidate stale cache + verify field-name contract in consumer. Not shipped this round; queued P1.**

### Asset classes

**CRYPTO** — WR 46.4% / PF 1.33. Walkforward OOS WR 45.2% / sharpe 1.74. **3 unwired modules** with zero callers:
1. `alpha_engine/new_crypto_strategies_20.py` (20 vol/OI/funding/on-chain strategies)
2. `alpha_engine/pattern_strategies.py` (10 chart patterns)
3. `alpha_engine/proven_research_strategies.py` (22 research-backed)
- Total wire-up: 3-5h via `smart_picks_engine` orchestrator.
- Drag attribution: `alpha_engine_fast` only 0.2% of volume (negligible). Real CRYPTO is broad + healthy.
- Top unexploited edge: ONDOUSDT × `quan_engine` LONG (n=128, WR 64.1%).

**EQUITY** — WR 51.4% / PF 1.55 (Tier-2 candidate). Walkforward OOS WR 61.9% / sharpe 7.53.
- Production has **98.9% LONG bias** (266 LONG vs 3 SHORT picks in `recent_closed`).
- Zero EQUITY-SHORT strategies wired into active scanner.
- Candidates: RSI-2 overbought SHORT, VWAP fade SHORT, Earnings PEAD negative SHORT.
- Effort 2-5 days per strategy.

**ETF** — WR 56.6% / PF 1.41 (Tier-2-PF gap 0.09). Walkforward EXCELLENT (OOS WR 74%, sharpe 10.08, consistency 100%).
- Only 7 active picks today (target n≥200 = 28× undersized).
- Bottleneck: TLT/HYG silently dropped (PR #995 fixes), crossover signal sparsity, narrow filter universe.
- Scale-up effort: 7h (Scenario 2 — intraday MR variant + filter loosening) → 120-200 picks.

**COMMODITY** — Apparent WR 70.5% / PF 4.03 is **99% COT over-emission artifact**.
- Non-COT subset (n=15) stats: WR 20% / PF 0.88 — sub-floor.
- Once PR #994 dedup ships and re-aggregates, COMMODITY revealed as one of the weakest classes.

**FOREX** — WR 41.8% / PF 0.63 sub-floor. Walkforward OOS WR 11.5% / sharpe -12.26.
- Existing rescue work: JPY-cross blocks already shipped 2026-05-12, PR #946 + #949 (confluence + Donchian) pending merge after my pushed fixes.
- Swarm agent claimed root-cause is outcome resolver not wired for FOREX — claim **NEEDS INDEPENDENT VERIFICATION** before acting. My earlier session forensic showed non-zero pnl_pct values for JPY pairs, so the resolver IS reaching FOREX picks. Filed as P1 investigation.

**BOND** — WR 54.5% / PF 0.66 thin. All 12 picks LONG TLT/HYG in rising-rate environment.
- Direction bias × rate environment mismatch creates R:R inversion (avg loss 2× avg win).
- All 3 candidates (curve steepener, HYG/IEF spread, TIP/IEF real-yield) flagged as **TRAPS** by Round-3 consult (n-starved + sub-floor expected stats).

**FUTURES** — 0 closed trades. After PR #946 + #949 merge: 8 wired strategies.
- Round-1 next-tier candidates: FX futures momentum, crack-spread, ES/NQ divergence.
- Round-3 consult ranks ES/NQ divergence as P0 conditional on PR pipeline unblocking.

## 2. Round-2 Ships (3 PRs)

| PR | Title | Effort | Status |
|---|---|---|---|
| #993 | walkforward BOND + FUTURES config | 5 min | OPEN |
| #994 | multi_asset_cot per-release dedup | 30 min | OPEN |
| #995 | etf_sector_momentum TLT/HYG lookup | 10 min | OPEN |

All three are bounded-scope fixes addressing audit blockers / silent regressions. No new strategies introduced.

## 3. Round-3 Consult — TOP 5 P0 Ship

Per DeepSeek second-opinion consult (`reports/mmr_round2_consult_deepseek_2026-05-14.md`):

| Rank | Strategy | Class | 90-day Tier-2 progress | Risk |
|---|---|---|---|---|
| 1 | RSI-2 Overbought SHORT (SPY/QQQ/IWM) | EQUITY | HIGH (mirror of 75.7% LONG twin) | regime dependency — pause when VIX >30 |
| 2 | `proven_research_strategies.py` wire | CRYPTO | HIGH (22 strategies; 13+ survive walkforward likely) | survivorship bias in 62-83% WR claims — run 70/30 split first |
| 3 | Earnings Negative Drift SHORT (PEAD) | EQUITY | MEDIUM-HIGH | macro regime — only trade when VIX <25 |
| 4 | `new_crypto_strategies_20.py` wire | CRYPTO | MEDIUM | overfit to 2024-2025 vol patterns — add regime detection |
| 5 | ES=F vs NQ=F divergence | FUTURES | MEDIUM (conditional on PR #946/#949) | n=0 infra — 2-3 weeks to wire |

## 4. Round-3 Consult — TOP 5 TRAPS

| Trap | Why |
|---|---|
| Gold/Silver seasonal vol crush | "Aug-Sep doldrums" → 0 signals in 90d starting May |
| TIP/IEF real-yield momentum | Duration risk repackaged; correlation 0.85+ with bonds; expected WR 48% below floor |
| `pattern_strategies.py` wire | H&S / triangles on 1h-4h crypto = 45-50% WR academic — overfit claims |
| Grains post-USDA reversal | Monthly reports → 3 events in 90d → n=3-6 (no stat-sig) |
| ZN/ZT yield curve trades | Expected WR 50% / PF 1.2 below Tier-2 floor; 3-year losing trade since curve inversion |

## 5. Round-3 Consult — MISSED CANDIDATES

DeepSeek flagged these strategies the Round-1 swarm did not surface:

| Candidate | Class | Expected | Priority |
|---|---|---|---|
| Put-writing on SPY/QQQ (30Δ / 30 DTE) | EQUITY | WR 80%+, PF 2.0+, n>100 in 90d | **P1** ("biggest miss") |
| Basis trade (perpetual vs futures arb) | CRYPTO | WR 90%+, PF 5.0+, free money until exchange risk | P1 |
| VIX futures contango roll (VX=F short) | FUTURES | WR 70%+, PF 2.0+, n>100 in 90d | **P1** ("critical miss") |
| TLT put spreads (rate hedge) | ETF/BOND | WR 55-60%, PF 1.5+, complements current BOND-LONG-only book | P2 |
| CL=F calendar spread (front vs 6m) | COMMODITY | WR 60%+, PF 1.5+; CL=F outright blocked but calendar spreads aren't | P2 |

**Critical observation:** the system has zero options strategies despite options being the highest-Sharpe equity-derivative class. The VIX-futures contango miss is structural (no vol product coverage). Both should be P1 next-quarter.

## 6. Revised P0-P5 ranked action list (post-consult)

Replaces §10 of the MMR audit report (PR #986).

| Priority | Action | Class | Effort | Expected lift |
|---|---|---|---|---|
| **P0** | Merge PR #993, #994, #995 (blockers) | All | review only | Audit integrity |
| **P0** | Wire `proven_research_strategies.py` with 70/30 walkforward gate | CRYPTO | 3h | n>2000 in 90d, 10+ strategies likely pass Tier-2 |
| **P0** | EQUITY RSI-2 SHORT (mirror futures_connors_rsi2 template) | EQUITY | 2-3d | First EQUITY-SHORT surface; expected WR 60-65% |
| **P0** | Wire `new_crypto_strategies_20.py` (funding-rate subset first) | CRYPTO | 3h | Funding strategies have empirical 55-60% WR |
| **P0** | Mark `ml_crypto_predictor` INACTIVE (n=22805 / 0% WR placeholder) | CRYPTO | 0.5h | Removes biggest visual artifact |
| **P0** | Quarantine `mercury2_fast` (PF 0.07), `fast_stocks_competition` (0 WR), `breakout_b_ml` (0 WR) | mixed | 1h | Stop active drag |
| **P1** | EQUITY Earnings PEAD SHORT | EQUITY | 3-4d | Hits when VIX<25 |
| **P1** | EQUITY put-writing on SPY/QQQ (30Δ / 30 DTE) | EQUITY | 1 week (options infra) | Highest-Sharpe equity-derivative |
| **P1** | CRYPTO basis trade (funding-rate arb) | CRYPTO | 4-5d | Near-riskless until exchange risk |
| **P1** | B3 concept_drift cache invalidation + field-name verify | All | 1h | Makes drift alert actionable |
| **P1** | Investigate FOREX outcome-resolver claim (swarm flagged — needs independent verify) | FOREX | 2h | Either explains broken FOREX or rules out the lead |
| **P2** | ETF intraday MR variant (RSI-2 on 4h bars) | ETF | 3h | Scale to n≥200 active |
| **P2** | FUTURES VIX contango roll (short VX=F) | FUTURES | 1 week | Vol product coverage; n>100 in 90d |
| **P2** | TLT put spreads | ETF/BOND | 4d | Complements current BOND-LONG book |
| **P3** | FUTURES ES/NQ divergence | FUTURES | 2-3 weeks (post PR #946/#949) | Spread mean reversion |
| **P3** | Riskfolio-Lib CVaR risk-cap layer | All | 1d | Prevents -160% multi_asset class drags |
| **P3** | UI High-Conviction filter audit | UI | 4h | Aligns surface with reality (memory: 0.90+ conf = 22.2% WR trap) |
| **P4** | CL=F calendar spread | COMMODITY | 1 week | Only commodity strategy that survives Round-3 review |
| **P5** | All Round-1 BOND candidates (curve, credit, real-yield) | BOND | DON'T SHIP | All flagged as TRAPS — n-starved + sub-floor |
| **P5** | All Round-1 COMMODITY candidates (copper, metals seasonal, grains) | COMMODITY | DON'T SHIP | All flagged as TRAPS — n-starved + monthly cadence |
| **P5** | CRYPTO `pattern_strategies.py` wire | CRYPTO | DON'T SHIP | Overfit claims; expected WR 45-50% |

## 7. Verifiable claims log

All Round-1 + Round-3 outputs preserved:
- `reports/money_maker_ready_20260514T001749Z.md` — original MMR audit (PR #986)
- `reports/mmr_round2_consult_prompt_2026-05-14.md` — Round-3 consult prompt
- `reports/mmr_round2_consult_deepseek_2026-05-14.md` — Round-3 DeepSeek response
- `reports/mmr_round2_synthesis_2026-05-14.md` — this synthesis

Round-2 PRs:
- PR #993 — walkforward BOND/FUTURES config
- PR #994 — multi_asset_cot per-release dedup
- PR #995 — etf_sector_momentum TLT/HYG lookup

Round-1 swarm: 10 agents, all completed, transcripts in
`C:\Users\zerou\AppData\Local\Temp\claude\…\tasks\*.output` (not committed).

## 8. Updated verdict

**Still NOT ready for real-money trading** at current state. Three independent blockers remain:

1. **PR #994 not yet merged** — multi_asset_cot will continue inflating COMMODITY headline numbers until ledger gate is live.
2. **Walkforward gap not filled** — PR #993 fixes config; BOND/FUTURES still need to actually run through one walkforward cycle to populate `by_class`.
3. **B3 (concept_drift stats) not yet addressed.**

Once Round-2 PRs merge + one walkforward cycle runs:
- ✅ §1 Tier-2-floor count revised (likely drops by 1 as multi_asset_cot deflates)
- ✅ §2 Walkforward all 7 classes visible (BOND with caveat)
- ❌ §3 multi_asset_cot audit closed (PR #994 ships the dedup)
- ⏳ §6 drift stats still need B3 fix
- ⏳ §7 UI High-Conviction filter audit P3

**Real-money green-light gate:** Tier-2-pass on EQUITY + ETF + CRYPTO post-resolver-v2-with-multi-asset-cot-dedup AND walkforward COMMODITY (post-COT-dedup) shows neither stable nor decay. Currently: 2/3 (EQUITY + ETF), CRYPTO marginal, COMMODITY pending dedup.
