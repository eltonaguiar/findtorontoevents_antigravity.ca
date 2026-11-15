# Elimination Rationale — How the Others Were Eliminated

**Package:** WIRED_IN/2026-11-15_0135/inspect-wt
**Author:** inspect-wt · **Date:** 2026-11-15

**Standard applied:** a class, strategy or claim is eliminated by a *stated, pre-registered or
arithmetic* test — never by vibes. Each elimination below names the test, the number, and
what would reverse it.

---

## A. Eliminated by arithmetic (cost > reachable edge)

| Class / approach | Test | Number | Reversible if… |
|---|---|---|---|
| **FOREX as prediction class** | historical PF on honest n + retail spread model | PF **0.27** with high n (sample is honest, edge is absent); spreads historically modeled ~0 | Two pre-registered mutations (session-filtered carry-aware trend, then session-extreme MR) pass PF≥1.3 / n≥150 vs carry benchmark — then un-kill; otherwise class marked `KILLED — no edge at retail cost structure` |
| **COMMODITY/FUTURES emission** | focus-screen cost/PnL ratio | **422%** cost/PnL → emission blocked; no real feed (roll schedules) exists | Real feed + roll-cost model shipped → the ONE CTA trend hypothesis may run its gate (net PF≥1.3, n≥100, beat BCOM on Calmar) |
| **CRYPTO (as currently run)** | fill replay + post-fix PF | PF 0.768 → **~0.80** after +67.5pp kimi fix — still below breakeven; SWING emission PF 0.457, −328.6pp killed | Fill-fidelity gates pass per strategy AND forward PF≥1.3/WR≥55%/n≥100 AND beats B&H BTC risk-adjusted |
| **Intraday / scalping / day-trading, ALL classes** | fill model + cost at reachable horizon | No class has a verified intrabar fill model; B4 showed 28–100% of "TP hits" were actually SL hits under intrabar replay | A verified intrabar resolver on every emission path + measured cost < ½ breakeven margin |

## B. Eliminated by statistics (null not beaten)

| Claim | Test | Number | Reversible if… |
|---|---|---|---|
| **"Some strategy cell has edge" (V1)** | cell search with z-test | 46 cells (8 source / 12 source×class / 26 strategy): **zero** pass uncorrected z>1.96 | A pre-registered cell passes on forward data with trial ID |
| **"Alive-only filtering finds the durable winners"** | split-sample refinement | PF **0.80–0.84** — FAILED; the edge includes strategies that stop emitting | never re-tested without a documented reason (it's a counted trial) |
| **"The big strategies are proven" (n≥100 cohort)** | break-even + z vs coin-flip | 4 strategies have n≥100: rs-breakout-scout z=0.78 (luck-class), luxalgo_confluence z=**−5.02** (worse than coin flip), momentum-factor z=−0.29, intermarket-flow z=−0.59. **Zero pass n≥100 ∧ PF>1.3 ∧ z>1.96** | any strategy reaching n≥100 with z>1.96 on intrabar-truth data |
| **646-strategy "winners"** | multiple-testing expectation | at p=5%, ~**32/646** PF>1.3 winners exist by chance; live audit flags **69/80 (86%)** OVERFIT_LIKELY; White Reality Check never even ran | pre-registration ledger + FDR/single-source gates flipped ON (`MONEY_READY_*` currently default "0") |
| **EQUITY as a current edge source** | #773 SPY gate | t=**1.05**, median pick −0.57% vs SPY, 54% underperform → `NO_ALPHA_BETA` | ONE new pre-registered trial (RSI(2), trial ID, n=500 gate) — not a re-run with new thresholds |
| **Variants A/B/D of strategy selection** | Bonferroni ×4 | p=0.049 / 0.044 / 0.040 — fail correction; only **C** survives (p<0.005) | forward pilot data (already running, scheduler `5992b142`) |

## C. Eliminated by structural argument

| Approach | Argument | Reference |
|---|---|---|
| **Mutual funds as intraday TP/SL picks** | NAV priced once daily + next-NAV execution + 30-day frequent-trading limits make intraday picks structurally impossible; the honest deliverable is a *monthly allocation engine* | peer consensus, adopted; SubQ: active-beats-index P(yes)=**0.03** |
| **Prediction-market copy-trading (Kalshi/Polymarket)** | 7 structural reasons (latency/position-size asymmetry, adverse selection of who copies, no fill model on mirrors, etc.), each labeled arithmetic vs probabilistic | `2026-11-14＊7PM＊plan/inspect-wt/05_prediction_market_copytrading/` |
| **BOND as a prediction class (for now)** | n=18–35 vs floor 100; at 12 decisions/yr, trade-level n≥100 takes ~3–5 years; the "signal" was never well-defined (3 options, one pre-selected) | `01_plan_per_asset_class/bond.md` — infrastructure, not signal |
| **Display-tier / leaderboard as evidence** | curated `.picks.active` (10–20 fresh rows) shown vs `active_raw` (4,164 rows, 79% zombies) hidden; 81% of open picks show fake 0% P/L (reads as "flat", true mean −1.80%); `display_tier='ELITE'` renders golden rows for n=1 cohorts | `05_verdict` §E |

## D. Eliminated by adjudication (peer-reviewed, evidence-anchored)

| Claim | Adjudication | Where |
|---|---|---|
| **`mega_mutation` as proven** | **VETOED / "high-risk secondary sleeve only"** — single-source `at_pick_outcomes`, PF 49–53 cells flagged `is_single_source_artifact=True`, 0 rows on `recent_closed`, strict n≈16–18 | `final_v3/hilarious-seer/01-common_themes/peer_adjudication_summary.md`; my independent check agreed: pilot at best |
| **Kilo's VWAP edge claim** | **Refuted twice independently** (BUGS.md B1 conflict table + hilarious-seer adjudication) | canonical `final_v3/00_common_themes/BUGS.md` |
| **"COT as commodity feature"** | Test **failed 4/4** — honestly reported; may not be silently re-tested; a re-test needs a documented reason and a new trial ID | final_v3 COT test |
| **ITERATION-005 (crypto) deployment on "tested vs zero"** | Not deployable: must beat a **risk-matched** benchmark — TSMOM Sharpe 2.13 vs its own B&H ≈2.2 currently fails | `final_v4/inspect-wt/01_plan/PLAN_FINAL.md` §2 non-goals |
| **Copy-trader TSMOM as system alpha** | External risk premium (Sharpe 2.13 ≈ benchmark2.2) — risk premium, not system alpha | `final_2026_11_14/inspect-wt/08_peer_review/` |
| **Historical PF/WR snapshots (equity ~1.41/53%, commodity ~1.78/47%, bond ~1.72/56%)** | Measured **before** fill and cost modeling / on tiny n — not evidence | per-class plan files |

## E. What survives (for contrast)

1. **Variant C** — beats the selection null at Bonferroni-corrected p<0.005, +98.7pp over 8
   true OOS months, reproduced exactly by two independent peers. Sub-T2 → forward pilot is
   the arbiter.
2. **MF/ETF allocation sleeve** — benchmark-relative backtest with disclosed failures
   (loses to B&H, below its own Sharpe gate, DD-stop rejected). No alpha needed; that's why
   it ranks first.
3. **The process itself** — pre-registration, kill criteria, honest failure reporting
   (COT 4/4, DD-stop, alive-filter). The only thing here that scales with more data.

## F. The one caveat on my own eliminations

All ledger-based findings share one blocker: **`resolution_method=None` on all 3,500 closed
rows** — no PF anywhere is certifiable until intrabar-vs-nominal resolution is recorded
(`QA_PLAN` gate 3). The eliminations above are directionally robust (the failures are large:
PF 0.27, z=−5.02, 422% cost ratios), but the *survivors* are provisional until measurement
truth lands in Phase 0.
