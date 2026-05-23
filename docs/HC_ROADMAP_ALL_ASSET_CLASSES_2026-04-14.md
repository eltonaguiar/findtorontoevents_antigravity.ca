# Roadmap: HC Picks Across All 7 Asset Classes

**Goal:** In the coming weeks, the High Conviction button should surface statistically validated picks in every asset class, not just CRYPTO.

**Constraint:** Option A is final (backtest confirmed — see `BACKTEST_TIER_BYPASS_2026-04-14.md`). HC gates stay strict. The levers are all upstream data, strategy, and forward-tracking work, not gate loosening.

## Current state (2026-04-14)

| Asset class | HC picks | Why | Plausible path |
|---|---|---|---|
| CRYPTO | **3-6** | Working as designed | Maintain |
| EQUITY | 0 | 43/49 fail `scoreAbsoluteFloor`, 6/49 fail compound; META near-miss at score 37 | **META unlock + inverse_goldmine validation** |
| FOREX | 0 | 2 active picks, both fail Gate 1 or Gate 5 | **Forex copy-trader pipeline + forex strategy dev** |
| COMMODITY | 0 | 0 active picks; per-class gate rejects (PF CI straddles 1.0) | **Cross-asset Bollinger MR port (Cursor rehab §COMMODITY)** |
| BOND | 0 | Scanner just unblocked by PR #200 `BOND_SYMBOLS` fix — n-starved | **Wait for accumulation + audit bond-specific penalties** |
| ETF | 0 | Dead per MERCURYPROMPT (PF 0.28, n=19) | **Redesign or permanently retire from HC** |
| FUTURES | 0 | Dead per MERCURYPROMPT (WR 5.9%, n=17) | **Redesign or permanently retire from HC** |

## Workstreams (prioritized by marginal value)

### Tier 1 — Ship this week

#### WS-0: breakout_b_ml near-miss CRYPTO unlock [highest marginal value, easiest]

**Discovery:** When running `tools/hc_gate_failure_report.py` (shipped in this PR) on the current snapshot, three CRYPTO picks from `breakout_b_ml` are failing Gate 2 by 1-8 score points despite having all other metrics:

| Symbol | Score | Trust | fwdN | fwdWR | Gap |
|---|---|---|---|---|---|
| ADAUSDT | **49** | 6 | 14 | 64.3% | **1 point** from score≥50 |
| DOTUSDT | **44** | 6 | 14 | 64.3% | **6 points** |
| BNBUSDT | **42** | 6 | 14 | 64.3% | **8 points** |

All three pass fwdN≥5, fwdWR≥45%, trust≥6 (crypto floor), and consensus (they have source_systems arrays). The ONLY blocker is Gate 2 compound (`score < 50 AND trust < 8`).

**Investigation:**

1. Trace `breakout_b_ml` source's penalty stack — same approach as goldmine's `null_ml_solo_source` timing bug
2. Check whether `breakout_b_ml` suffers from the same ml_score timing issue (penalty fires before ml_composite_score is populated)
3. Fix the score path so breakout_b_ml scores hit 50+ naturally for high-quality picks

**Effort:** 2-6 hours
**Impact:** 3 immediate additional CRYPTO HC picks (doubles today's count from 3 to 6)

#### WS-1: META score unlock (EQUITY) [second-highest marginal value]

**Gap:** META's state depends on snapshot timing. Cursor's earlier snapshot had META at `multi_asset_copytrader` sc=37 trust=5 fwdN=746 fwdWR=46.8% (Gate 1 near-miss). The current snapshot has META at `regime_terminal` sc=30 trust=5 fwdN=20 fwdWR=40% (deeper Gate 1 fail, fwdWR below Gate 5 threshold). The META name can appear from MULTIPLE sources; the correct unlock depends on which variant is live at a given time.

**Investigation:**

1. Pull all `META` entries from the current `picks.active` and enumerate sources
2. For the multi_asset_copytrader variant (Cursor's sighting): trace the penalty stack at `quality_gates.py` ~2042+ and ~2074+ for stale copytrader penalties and non-crypto raw floor
3. For the regime_terminal variant (current sighting): the fwdWR=40% blocker is Gate 5, not Gate 1. Requires WS-6 (regime_terminal fwdWR audit) to be solved first.

**Investigation:**

1. Trace `multi_asset_copytrader`'s penalty stack in `audit_trail/quality_gates.py` (Cursor pointed to lines ~2042 stale copytrader penalties and ~2074 non-crypto raw floor)
2. Identify which penalties fire for META and why
3. If any penalty is over-applying (similar to the `null_ml_solo_source` timing bug on goldmine), exempt multi_asset_copytrader or fix the timing
4. Target: META score 37 → 50+ → passes HC

**Effort:** 4-8 hours
**Impact:** 1st-ever EQUITY HC pick on the dashboard

#### WS-2: Gate-failure report per pick (diagnostic)

**What:** Ship `tools/hc_gate_failure_report.py` (delivered in this PR) — reads `dashboard_data.json` and emits a per-pick report of which gate each pick hits first. Makes every future investigation data-driven instead of guessing.

**Effort:** Done (shipped in this PR)
**Impact:** Accelerates WS-1, WS-3, WS-4, WS-6

#### WS-3: HC health monitor (visibility)

**What:** Ship `tools/hc_health_monitor.py` (delivered in this PR) — daily/weekly snapshot of HC pick count by class, with delta tracking. Run it manually or wire to a GitHub Action.

**Effort:** Done (shipped in this PR)
**Impact:** See progress toward the multi-week goal

#### WS-4: Forward-tracking audit sweep

**What:** Grep `_extract_picks` consumers in `audit_trail/dashboard_generator.py` for any source with `closed_path = None` or non-standard top-level keys. Each such source is a "silent data dropout" like goldmine was (PR #207).

**Initial targets:**
- `pm_whale_signals` — `closed_path = None`, strat_fwd_trades always 0
- `pm_kalshi_signals` — same
- `prediction_market_consensus` — same
- Any `multi_asset_*` source without a closed file
- Any entry in `JSON_PICK_SOURCES` with `None` in the third position

**Effort:** 3-6 hours
**Impact:** Fixes N more goldmine-shaped bugs, each unlocking a new source's forward tracking

### Tier 2 — Start this week, finish in 1-2 weeks

#### WS-5: inverse_goldmine_stocks forward validation (EQUITY)

**What:** The `inverse_goldmine_stocks` baby strategy config from PR #208 is in `awaiting_forward_test` state. The baby pipeline runner needs to:

1. Identify goldmine_stocks entries as they close
2. Flip their direction (LONG→SHORT) to create inverse picks
3. Track those inverse picks forward
4. After n≥20 inverse trades, evaluate: WR≥60% → promote; WR<40% → kill AND block parent

**Effort:** 1-2 weeks (forward accumulation time)
**Impact:** If inverse hypothesis holds (~78% theoretical), unlocks 5-15 equity HC picks per day

#### WS-6: regime_terminal fwdWR audit (EQUITY)

**Question:** Is regime_terminal's 40% fwdWR accurate, or is there a calculation bug?

**Investigation:**

1. Pull closed picks where `strategy == 'regime_terminal'` (should be ≥100 from the strategy leaderboard)
2. Compute raw WR independently: wins / (wins + losses)
3. Compare to the stored `strat_fwd_wr` field — they should match
4. If they don't match: bug in forward_wr computation → fix → regime_terminal might actually pass Gate 5
5. If they match: regime_terminal is genuinely below edge → run through `MUTATION_THREE_AXIS_PROTOCOL.md` (mutation, inverse, symbol rotation)

**Effort:** 4-8 hours
**Impact:** Either unlocks regime_terminal for HC (EQUITY + FOREX since it covers AUDUSD=X) OR produces a validated inverse candidate

#### WS-7: Forex copy-trader pipeline (FOREX)

**What:** `copy_trader_intel` has forex trader clones somewhere. Route their picks through the standard active→closed→leaderboard pipeline so forward tracking fires.

**Steps:**

1. Find the forex copy-trader data source (likely `copy_trader_intel/data/forex_copytrader_picks.json` or similar per the JSON_PICK_SOURCES list)
2. Verify closes are being generated (same style as goldmine — check for a closed_trades.json)
3. If closes don't exist, design an outcome resolver for forex copy-trader picks (time-based? symbol-based?)
4. Wire it through `JSON_PICK_SOURCES`

**Effort:** 1-2 weeks
**Impact:** Unlocks FOREX HC picks (currently 2 active, need ≥5 per day with fwdWR ≥50%)

### Tier 3 — Start in 1-2 weeks, finish in 2-4 weeks

#### WS-8: Commodity strategy cross-port (COMMODITY)

**What:** Cursor's rehab plan §COMMODITY recommends: *"Add Bollinger MR to commodity futures (GC=F, SI=F, PL=F, HG=F) — it works on equity (PF 1.71) and forex (PF 4.18)"*. Cross-asset mean reversion is the lowest-risk path.

**Steps:**

1. Run `alpha_engine/incubator/run_incubator.py` (if it exists — Cursor mentioned it) on commodity symbols with MeanReversionBB
2. Validate: fwdWR ≥ 45%, fwdN ≥ 30 after a forward window, PF CI lower > 1.0
3. If validated, wire into scanner
4. Relax my per-class gate for COMMODITY from "reject all" to "allow if trust≥3 AND fwdWR≥45%" once commodity edge is statistically confirmed

**Effort:** 2-4 weeks
**Impact:** Unlocks COMMODITY HC picks

#### WS-9: Forex strategy development (FOREX)

**What:** Even with WS-7 (copy-trader pipeline), we need at least one native forex strategy with proven fwdWR ≥ 50% to have reliable HC picks.

**Candidates:**

- `forex_rsi2_mean_reversion` (Cursor's rehab plan §FOREX mentions this — currently coupled to copy_trader, decouple it)
- `MeanReversionBB` cross-port (works on equity + commodity)
- A new design based on session carry or momentum

**Effort:** 2-4 weeks per candidate
**Impact:** Sustainable FOREX HC coverage independent of copy-trader quality

### Tier 4 — Passive, wait for time

#### WS-10: BOND accumulation (BOND)

**What:** PR #200 added `BOND_SYMBOLS` to `ALL_SYMBOLS`, unblocking the scanner to iterate bond tickers. But we need ~n=30 closed bond picks before any statistical gate can fire. Scanner runs hourly, generates maybe 1-5 bond picks per day, each takes days to close → 3-6 weeks to accumulate enough.

**Active work during wait:**

- Audit `audit_trail/quality_gates.py` for any bond-specific scoring penalties (analog of the `equity_greedy_tp` penalty that's over-applying to goldmine)
- Verify `forward_validator.py` correctly resolves bond pick outcomes (TLT/IEF/AGG behave differently than crypto)
- Pre-wire any needed bond strategy to the scanner

**Effort:** 1-2 hours active + 3-6 weeks passive
**Impact:** Unlocks BOND HC picks

### Tier 5 — Defer or abandon

#### WS-11: ETF/FUTURES redesign

**Reality:** Per MERCURYPROMPT.md:
- ETF: PF 0.28, n=19 → dead
- FUTURES: WR 5.9%, n=17 → dead

Per my v2 MIMO harness (shipped earlier today in PR #200):
- All 7 MIMO rescue strategies fail on real bars. Zero viable.

**Decision:** Either commit to a multi-week strategy redesign (new theoretical basis, full backtest + validation) OR **permanently retire** ETF/FUTURES from HC view with documentation explaining why.

**My recommendation:** Permanently retire. Update `hcEdgeManifest` in `audit_dashboard/template.html` to make the "DEAD" label persistent, and explain to users that these classes don't have tradeable edge in this ecosystem. If a future signal source changes that, re-evaluate.

**Effort to retire:** 1 hour (doc + UI text update)
**Effort to redesign:** 4-8 weeks per class with no guarantee

## Near-term delivery schedule

| Week | Ship | Measurable outcome |
|---|---|---|
| 2026-04-14 (today) | This roadmap + WS-2 (gate failure report) + WS-3 (health monitor) | Baseline HC pick count by class |
| 2026-04-14 to 2026-04-18 | WS-1 (META unlock) + WS-4 (forward-tracking sweep) + WS-6 (regime_terminal audit) | **First EQUITY HC pick** (via META), any extra sources found |
| 2026-04-14 to 2026-04-28 | WS-5 (inverse_goldmine validation) + WS-7 (forex copy-trader pipeline) | **Sustainable EQUITY + FOREX flow** |
| 2026-04-28 to 2026-05-12 | WS-8 (commodity) + WS-9 (forex native strategy) | **COMMODITY + robust FOREX** |
| 2026-04-28 to 2026-05-28 | WS-10 (bond passive accumulation) | **BOND** |
| Ongoing | WS-3 (health monitor) + regular backtest re-runs | Progress tracking |
| Decision point | WS-11 (retire or redesign ETF/FUTURES) | Documented permanent state |

## Goal: 6-week state

**Target by 2026-05-26:**

| Class | Target | Rationale |
|---|---|---|
| CRYPTO | 3-10 | Current + growth from new sources |
| EQUITY | 3-8 | META + inverse_goldmine + regime_terminal (if audit clears it) |
| FOREX | 2-5 | Copy-trader pipeline + native strategy |
| COMMODITY | 1-3 | Bollinger MR cross-port |
| BOND | 1-2 | Accumulation + clean gates |
| ETF | 0 | Permanently retired (or 1-2 if redesign ships) |
| FUTURES | 0 | Permanently retired (or 1-2 if redesign ships) |
| **Total** | **10-30** | vs current 3-6 |

The realistic stretch goal is **5 of 7 classes with ≥1 HC pick each** by end of May 2026.

## Risk register

| Risk | Mitigation |
|---|---|
| Codebuff's uncommitted quality_gates.py work collides with WS-1 | Coordinate via peers bus when they resume |
| META score penalty is rooted in a structural multi_asset_copytrader issue, not a tunable | Fallback: force non-copytrader rescoring for high-n copy picks |
| inverse_goldmine forward WR is also <45% | Kill the inverse AND add goldmine to BLOCKED_SOURCE_SYSTEMS |
| regime_terminal audit shows the 40% is real | Run mutation protocol; accept regime_terminal stays out of HC |
| Forex copy-trader data source doesn't exist or is stale | Build new pipeline; higher effort |
| Bond accumulation stalls because scanner isn't emitting | Debug scanner's bond universe iteration |
| Commodity Bollinger MR doesn't port (different market regime) | Try alternative strategy families |

## Dependencies + coordination

- **Codebuff:** currently paused; working tree has `quality_gates.py` + `ml_ranker.py` uncommitted. WS-1 touches `quality_gates.py`, needs coordination when they resume.
- **Cursor:** has shipped multiple analysis docs today. The rehab plan at `docs/ASSET_CLASS_REHAB_PLAN_2026-04-14.md` has per-class "What's NOT done" checklists that substantially overlap with this roadmap.
- **GitHub Actions `audit-dashboard.yml`** runs hourly; dashboard deployments happen on that cadence so all shipments land within ~1 hour of merge.

## What this PR ships

- `docs/HC_ROADMAP_ALL_ASSET_CLASSES_2026-04-14.md` — this document
- `tools/hc_gate_failure_report.py` — per-pick gate failure diagnostic (WS-2)
- `tools/hc_health_monitor.py` — weekly HC snapshot with class breakdown (WS-3)
