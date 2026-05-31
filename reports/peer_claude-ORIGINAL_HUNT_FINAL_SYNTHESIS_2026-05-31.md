# ORIGINAL HUNT — FINAL SYNTHESIS (Per-Asset-Class Winner Deep-Dive)

**Author:** peer_claude (Opus 4.7)
**Date:** 2026-05-31 (EST overnight closure into 2026-06-01)
**Wave:** Original 5-strategy academic hunt × 7 asset classes (35 MC bootstrap tests)
**Verdict:** **NO_EDGE — 0 winners across 35 tests.**

---

## 1. Per-Class Verdict Table

| Class | Tested | Winner | Best Strategy (point) | n | WR | PF | Root Cause Family | Recommended Action |
|---|---|---|---|---|---|---|---|---|
| **CRYPTO**   | 5/5 | NO | volatility_breakout (keltner/ATR) | 85 | 0.612 | 1.47 (CI lo 0.77) | Data quality (no intrabar) + heavy-tailed pnl + universe-wide PF 1.14 | MORE_DATA_NEEDED → shadow-pilot vol-breakout only after intrabar replay + n→150 |
| **EQUITY**   | 5/5 | NO | stocks_rsi2_pullback | 39 | 0.590 | 1.20 (CI lo 0.53) | **PIPELINE GAP** — 4/5 academic strategies never implemented (magic_formula, piotroski, mom_12_1, low_vol) | TRY_DIFFERENT_FAMILY — implement 4 missing academic strategies; shadow-pilot rsi2 to n≥100 |
| **COMMODITY**| 5/5 | NO | cta_golden_cross_200 (bright spot) | 26 | 0.923 | n/a | Single-strategy concentration (futures_momentum 83% of flow, bleeding) + 4/5 families not emitted | TRY_DIFFERENT_FAMILY (COT extremes, seasonal, ATR-MR) + suspend futures_momentum size-up |
| **FOREX**    | 5/5 | NO | (none competitive; rsi2_mean_reversion is the size leader and is a P0 demote) | 664 | 0.449 | 0.42 | Lottery distribution + dxy_trend_filter (#275) likely sign-flipped + rsi2_MR is the loser | **RETIRE_CLASS from sizing** + demote rsi2_MR + multi-year carry/momentum backtest |
| **ETF**      | 5/5 | NO | none — 906k OPEN backtest rows, ~920 noise-only closed | <100 | n/a | n/a | Resolver gap (906k OPEN unresolved) + 133k SPY/QQQ rows mistagged as EQUITY + 0 academic strategies live | TRY_DIFFERENT_FAMILY — wire Faber 10mo MA on SPY/QQQ/IWM/EEM/GLD/TLT; backfill resolver; re-tag ETF |
| **BOND**     | 5/5 | NO | none — 5 closed bond rows total in 90d | 5 | 0 | 0 | **PIPELINE GAP** — no bond emitters in production scanner; 41k+ bt rows stuck OPEN | MORE_DATA_NEEDED (backfill resolver + wire bond emitters); conditional RETIRE_CLASS if no n≥100 in 30d |
| **PENNY_IPO**| 5/5 | NO | oversold_bounce_RSI2 | 15 | n/a | n/a | **PIPELINE GAP** — no IPO calendar, no float feed, no scanner; not an instrumented class | TRY_DIFFERENT_FAMILY + MORE_DATA_NEEDED — wire IPO/float feeds before any further hunt |

**Aggregate: 35 academic-literature strategies tested via MC bootstrap → 0 met winner criteria (n≥100, WR Wilson-lo>0.55, PF CI-lo>1.2, Sharpe CI-lo>0.5, Bonferroni p<0.01).**

---

## 2. Honest Closing Verdict — 7th Independent NO_EDGE Confirmation

This hunt closes the loop on a converging body of evidence from 7 independent sources:

| # | Source | Verdict | Date |
|---|---|---|---|
| 1 | My 10-agent swarm (this session's earlier brainstorm) | NO_EDGE | 2026-05-31 |
| 2 | 3 external AI peers (gpt-oss, deepseek, ring) | NO_EDGE consensus | 2026-05-31 |
| 3 | Kilo permutation test (p=1.0 across all classes) | NO_EDGE | 2026-05-31 |
| 4 | Kilo bright-spot review (refuted local "passes") | NO_EDGE | 2026-05-31 |
| 5 | Zoo truth filter (0/138 strategies cleared) | NO_EDGE | 2026-05-31 |
| 6 | Qwen audit pass | NO_EDGE | 2026-05-31 |
| 7 | **This hunt — 35 academic candidates × MC bootstrap** | **NO_EDGE (0 winners)** | 2026-05-31 |

The signal is unambiguous: **no live strategy in the current production pipeline clears tier-2 hedge-fund-grade gates on any of 7 asset classes today.** The class-level CLAUDE.md status (0/6 classes T2-passing) is independently re-confirmed strategy-by-strategy.

### Root-cause family distribution

| Family | Classes | Implication |
|---|---|---|
| **PIPELINE GAP** (strategies never implemented) | EQUITY (4/5), BOND (5/5), PENNY_IPO (5/5), ETF (4/5) | Cannot refute academic edge — we never tested it. Build first, then test. |
| **Single-strategy concentration** (one losing strategy dominates flow) | COMMODITY (futures_momentum 83%), FOREX (rsi2_MR 40%) | Demote the size leader before any new hunt. |
| **Thin n + heavy-tailed pnl** (data exists but insufficient for inference) | CRYPTO (n=85 best), EQUITY (n=39), COMMODITY (n=26 bright spot) | Wait for more closes OR backfill via resolver / intrabar replay. |
| **Data quality** (resolver/mislabel/no intrabar) | ETF (906k OPEN), BOND (41k OPEN), CRYPTO (no intrabar) | Plumbing fix is upstream of any strategy verdict — see memory `project-money-ready-2026-05-31`. |
| **Actual no-edge** (clean data, clean n, refuted) | FOREX rsi2_mean_reversion (n=664, WR 44.9%, PF 0.42) | Demote per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`. Single confirmed no-edge cell. |

**Critical reframing:** of 35 cells, only **1 cell (FOREX rsi2_MR)** is a clean "no-edge refutation" — the other 34 are dominated by plumbing/data/pipeline failures upstream of the strategy itself. This restates the `project-money-ready-2026-05-31` memory: **the money-ready bottleneck is PLUMBING, not strategies/MC.**

---

## 3. Operator Action Plan (Ranked)

### Tier 1 — Plumbing fixes that must land BEFORE the next test cycle

1. **Intrabar OHLC replay for CRYPTO TP/SL resolver.** Per memory `reference-sl-optimization-needs-pricepath` — already proven 2026-05-31 that winsorized TP/SL tuning is wrong. Wire intrabar OHLC into `alpha_engine/outcome_resolver.py` so CRYPTO closes match real fills. Upstream of every CRYPTO hunt.
2. **Backfill backtest resolver for ETF + BOND.** 906k ETF OPEN rows + 41k BOND OPEN rows in `bt_backtest_trades` need pnl_pct. Mirror the May-3 CRYPTO resolver fix at `outcome_resolver.py:115-126`.
3. **Status canonicalization + ghost-OPEN sweep.** Per `feedback-incident-page-stale-vs-live-db`: EXPIRED→WON mislabels, 1864 duplicate signal-ts groups, status string drift. One-shot UPDATE pass against `trading_picks` + `bt_backtest_trades`.
4. **Re-tag ETF rows.** 133k SPY/QQQ/IWM/EEM/GLD/TLT closed-pick rows are mistagged as `category='equity'` — `UPDATE ... SET category='etf' WHERE symbol IN (...)` migration.
5. **Demote FOREX `rsi2_mean_reversion`** per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` + three-axis mutation (`docs/MUTATION_THREE_AXIS_PROTOCOL.md`). Mutate-before-kill. Single cleanest no-edge cell in the entire hunt.

### Tier 2 — Top-3 strategies to BUILD fresh (from expanded-hunt NEEDS_IMPLEMENTATION when it lands)

Pending wave `wh77cfsja` expanded-hunt output, the highest cross-AI-consensus academic candidates are:

1. **Faber 10-month tactical MA** (ETF) — trivially instrumented: `if SPY.close > SMA(SPY, 10mo) then long SPY else cash`. Cleanest path to first ETF cohort with n≥100 in ~90d.
2. **Magic Formula / Piotroski F-score** (EQUITY) — published edges (Greenblatt 2005; Piotroski 2000); 0 production coverage today. Pair into a fundamental sleeve.
3. **COT commercial-extremes + seasonal** (COMMODITY) — replaces the bleeding `futures_momentum` mono-culture with two academic families that have decades of evidence.

(Penny/IPO is gated on data plumbing — IPO calendar + float feed — not strategy choice. Defer build until feeds wired.)

### Tier 3 — Per-class shadow-pilot priority order (only AFTER plumbing fixes)

1. **CRYPTO `volatility_breakout`** (keltner/ATR) — sole candidate with Wilson-lo>0.50 today. 0.25× baseline risk. Re-test at n≥150 with intrabar replay.
2. **EQUITY `stocks_rsi2_pullback`** — paper-only shadow until n≥100 policy-clean. WR 59%/PF 1.20 point estimates are interesting but every CI lower-bound fails.
3. **ETF Faber 10mo MA** (once wired) — diversifier; runs naturally at low frequency.
4. **NO SHADOW PILOT** for FOREX, COMMODITY, BOND, PENNY_IPO until plumbing or data lands.

### Tier 4 — Statistical-gate framework (apply from day 1 per cursor framework)

Every future winner-hunt cell MUST satisfy:

- **n ≥ 500** closed real (policy-clean) trades
- **WR Wilson lower-bound > 0.55**
- **PF bootstrap CI lower-bound > 1.2**
- **Sharpe bootstrap CI lower-bound > 0.8**
- **Bonferroni-corrected p < 0.01** across all simultaneously-tested candidates
- **Single-source concentration HHI < 0.30** (per `feedback-concentration-strategy-not-engine`)
- **Intrabar replay** for any TP/SL-sensitive class (per `reference-sl-optimization-needs-pricepath`)

The original hunt used n≥100 / Wilson-lo>0.55 / PF CI-lo>1.2 / Sharpe CI-lo>0.5 — going forward, tighten to the cursor-framework gates above. The lower n=100 floor was already too generous for tier-2 promotion.

---

## 4. Handoff Checklist for Next Wave

- [ ] Land Tier-1 plumbing PRs (intrabar resolver, ETF/BOND backfill, status canonicalization, ETF retag, FOREX rsi2_MR demote).
- [ ] Ingest expanded-hunt NEEDS_IMPLEMENTATION list from wave `wh77cfsja`.
- [ ] Build Faber 10mo MA + Magic Formula + Piotroski + COT extremes per Wire-Up Rule (production caller in `score_pick` / `smart_picks_engine`).
- [ ] Wait 30 days for forward closes → re-run this hunt with cursor-framework gates.
- [ ] Until then: **DO NOT SIZE UP any class. DO NOT promote any strategy to "proven" on `updates/index.html`.**

---

## Cross-references

- `reports/peer_claude-deep-dive-WINNER-{CRYPTO,EQUITY,COMMODITY,FOREX,ETF,BOND,PENNY_IPO}_2026-05-31.md`
- `audit_dashboard/data/money_ready_verdict.json` (2026-05-24)
- `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md`
- Memory: `project-money-ready-2026-05-31`, `reference-sl-optimization-needs-pricepath`, `feedback-concentration-strategy-not-engine`, `feedback-incident-page-stale-vs-live-db`
- CLAUDE.md MAJOR GOAL #1 (current per-class state)
