# Edge Improvement — Agent Handoff Task List

**Session ending:** 2026-04-14 evening
**For:** other Claude / Cursor / Codebuff / Antigravity agents picking up this work
**Session context:** see [strategy-consistency-audit](../updates/2026-04-14-strategy-consistency-audit.md), [edge-discovery-and-plan](../updates/2026-04-14-edge-discovery-and-plan.md), [verified-edge-golden-glow](../updates/2026-04-14-verified-edge-golden-glow.md)

## How to use this document

Every task below is **spec-complete**: goal, rationale, files, implementation approach, QA process, acceptance criteria. Pick any task, follow its spec, ship in its own PR. **Do not batch multiple tasks into one PR** — they have different risk profiles and review needs.

Each task has a **Task ID** (`T1-A` through `T4-D`) you can cite in commits and PRs. Tiers:

- **T1** (this week, high confidence, low risk) — ship first
- **T2** (1-2 weeks, medium effort, some design calls)
- **T3** (2-4 weeks, requires investigation)
- **T4** (deferred / parked)

All numeric claims are reproducible from `audit_dashboard/data/dashboard_data.json → picks.recent_closed` (3,500 picks as of 2026-04-14 15:34 UTC snapshot). Regenerate with `python tools/_hc_noncrypto_diagnostic.py` or `python tools/hc_gate_failure_report.py` against a fresh snapshot.

## Coordination heads-up

- **Codebuff paused** with uncommitted changes to `alpha_engine/ml_ranker.py` + `alpha_engine/model_calibration.py` (drift remediation). **Do not touch those files** until they resume and ship their tree.
- **Workflow `audit-dashboard.yml`** has a recurring conflict-marker trap on auto-generated data files (`audit_dashboard/data/ai_challenge_summary.json`, `audit_trail/data/stock_prices.json`) that blocks the commit step — see issue #141. **Task T1-G below is the fix.**
- **Never** edit `audit_dashboard/index.html` or any `updates/index.html` directly. Edit `template.html` and let the workflow regenerate.
- **Never run `python -m audit_trail.dashboard_generator` locally** — it overwrites live HTML (per CLAUDE.md).
- Use worktrees: `git worktree add e:/task-XXX origin/main` then branch + PR + merge. Don't push to a shared dev branch.
- All task work should run `py_compile` on touched Python files before commit.

---

## TIER 1 — ship this week

### T1-A. Tighten HC Gate 7 to reject `confidence 0.85-0.95 AND fwd_n < 30`

**Goal:** Close the anti-predictive confidence band. Picks in 0.85-0.95 confidence have PF **0.61** (losing money), but HC Gate 7 only rejects `confidence > 0.90 AND fwd_n < 20`. The 0.85-0.90 band slips through.

**Evidence:**

| Confidence | n | WR | PF |
|---|---|---|---|
| 0.75-0.85 | 795 | 45.9% | 1.28 (positive) |
| **0.85-0.95** | **126** | **47.6%** | **0.61** (LOSING) |
| 0.95-1.01 | 110 | 44.5% | 1.04 |

**Files to touch:**

- `audit_dashboard/hc_filter.js` — `HC_GATE_PARAMS_EMBEDDED` (find `confidenceMax: 0.90`)
- `config/hc_gate_params.json` — deployed config override
- `tools/dashboard_hc_rules.py` — Python mirror (keep parity)

**Implementation approach:**

1. Add new params to both JS and Python mirrors: `confidenceLoBand: 0.85`, `confidenceHiBand: 0.95`, `confidenceLoBandFwdTradesMin: 30`
2. In `evaluateHcGates1to9()` Gate 7 section, add: `if (cf >= params.confidenceLoBand && cf < params.confidenceHiBand && fwd_n < params.confidenceLoBandFwdTradesMin) return false;`
3. Mirror in `tools/dashboard_hc_rules.py`.

**QA process:**

1. `py_compile tools/dashboard_hc_rules.py`
2. `node -e "require('./audit_dashboard/hc_filter.js'); console.log('ok')"`
3. Run `python tools/hc_gate_failure_report.py` — confirm picks with conf 0.85-0.95 AND fwd_n<30 now show G7 failure reason
4. Historical backtest: apply the new gate to `recent_closed` and verify the passing subset has PF ≥ 1.5

**Acceptance criteria:**

- Live HC button pick count drops by 1-2 picks (the 0.85-0.95-conf picks that were passing)
- Aggregate PF of HC-passing closed picks rises by ≥ 0.05
- Playwright test at `scripts/test_hc_button_playwright.py` still passes

**Risk:** Low. Targeted gate tweak.

---

### T1-B. Relax `forwardWRMinPct` from 45 → 55

**Goal:** The 45-55% fwdWR band is only marginally positive (PF 1.31); the 55-65% band jumps to PF 1.92. Moving the floor from 45 to 55 removes ~40% of HC-eligible picks while keeping the PF-dominant portion.

**Evidence:**

| fwdWR band | n | WR | PF |
|---|---|---|---|
| 45-55% | 1,134 | 47.7% | 1.31 |
| 55-65% | 348 | 58.9% | **1.92** |
| 65-80% | 370 | 57.6% | 2.35 |

**Files to touch:**

- `config/hc_gate_params.json` — change `forwardWRMinPct: 45` → `55`
- `audit_dashboard/hc_filter.js` — update embedded default
- `tools/dashboard_hc_rules.py` — update Python mirror

**QA process:**

1. Run `python scripts/backtest_tier_bypass_2026-04-14.py`-style test BEFORE merging
2. Confirm the 55% floor outperforms 45% on historical picks
3. Document the expected HC live pick count drop in the PR body

**Acceptance criteria:**

- Retrospective PF of HC-passing closed picks rises to ≥ 1.70
- Live HC button pick count drops by ~30-50% (expected; this is the point)
- Playwright test still passes

**Risk:** Medium. Policy tightening — produces fewer picks. **Coordinate with user before merging** — confirm they want fewer-but-stronger.

---

### T1-C. Bottom-symbol blocklist

**Goal:** Add `BLOCKED_SYMBOLS` set to `audit_trail/quality_gates.py` for 6 symbols with WR < 35% on n ≥ 20. Structural anti-edge — these symbols lose money regardless of strategy.

**Evidence:**

| Symbol | n | WR | PF | Sum PnL |
|---|---|---|---|---|
| **TRXUSDT** | 41 | **7.3%** | **0.08** | **−62.8%** |
| JTOUSDT | 33 | 18.2% | 0.38 | −34.1% |
| XLMUSDT | 26 | 19.2% | 0.81 | −1.7% |
| ICPUSDT | 53 | 22.6% | 0.65 | −6.7% |
| RENDERUSDT | 45 | 31.1% | 0.40 | −33.8% |
| NVDA | 21 | 33.3% | 0.77 | −6.3% |

**Note:** `EURJPY=X` (56 trades, 30.4% WR, PF 0.02) is ALSO in this tier but do NOT block — forex pnl_pct is scale-corrupted (see T2-C). Wait until that's fixed.

**Files to touch:**

- `audit_trail/quality_gates.py` — add `BLOCKED_SYMBOLS` set near `BLOCKED_STRATEGIES` (line ~910)
- Add `is_symbol_blocked(sym)` helper
- Wire into active-pick filter (find where `is_strategy_blocked` is called)

**QA process:**

1. `py_compile audit_trail/quality_gates.py`
2. Count current active picks matching blocked set — expected 0-3 (most not in pool today; preemptive block)
3. Grep for any existing per-symbol boosts that might conflict

**Acceptance criteria:**

- Next workflow run logs `[symbol-blocklist] dropped N picks`
- Blocked symbols do not appear in active feed on any future generation

**Risk:** Low.

---

### T1-D. Top-symbol score boost

**Goal:** Boost the 10 symbols with strongest WR+PF combos by +2 to +5 score. Nudges picks on proven combos over Gate 1/2 thresholds without changing any floor.

**Evidence:** Top 10 with n ≥ 20 and WR ≥ 50%: BNBUSDT (83.9%/12.70), CVX (72.4%/2.25), XRPUSDT (69.4%/4.43), OPUSDT (63.3%/2.37), NEARUSDT (62.5%/2.74), XOM (60.5%/1.53), WLDUSDT (60.0%/2.06), UNIUSDT (57.6%/1.54), ARBUSDT (54.1%/1.92), SOLUSDT (50.8%/1.84).

**Files to touch:**

- `audit_trail/quality_gates.py` — add `PROVEN_SYMBOL_BOOSTS` dict near line ~2186
- Apply in `_apply_score_penalties()`: `score += PROVEN_SYMBOL_BOOSTS.get(symbol, 0)`, add to `penalties` list

**Boost schedule:**

```
BNBUSDT: +5  CVX: +4  XRPUSDT: +4  OPUSDT: +3  NEARUSDT: +3
XOM: +3  WLDUSDT: +3  UNIUSDT: +2  ARBUSDT: +2  SOLUSDT: +2
```

**QA process:**

1. `py_compile`
2. Retroactive check: filter closed picks to `symbol in PROVEN_SYMBOL_BOOSTS`, confirm aggregate WR ≥ 55%
3. Check for interaction with `SYMBOL_DIRECTION_BONUSES` — avoid double-boosting
4. Verify no score pushes past 100 (cap if needed)

**Acceptance criteria:**

- Next run: proven symbols' score is +2 to +5 higher than without boost
- Boost log entry in pick's `_penalties` list
- No overflow past 100

**Risk:** Low.

---

### T1-E. Wire `inverse_goldmine_stocks` into live scanner at half-size

**Goal:** Inverse goldmine config exists (PR #208) but isn't wired. For forward validation, it needs to produce active picks. Wire at half-size to cap risk.

**Evidence:** Goldmine has 21.2% WR (validated). Inverse hypothesis: ~78% WR. Needs live validation.

**Files to touch:**

- `baby_strategies/inverse_goldmine_stocks.meta.json` — flip `wired_in_scanner: false` → `true`
- `baby_strategies/inverse_wrapper.py` — ensure it accepts `goldmine_stocks` source via `source_strategy_substring` config
- Whatever orchestrator imports baby strategies into scanner — grep `baby_strategies` in `alpha_engine/scanner.py` and `alpha_engine/production_scanner.py`

**Implementation approach:**

1. Read `baby_strategies/inverse_wrapper.py` runtime contract (dict-in/dict-out transformer)
2. Find where live scanner iterates baby strategies
3. Register `inverse_goldmine_stocks` as a transformer
4. Apply `size_multiplier: 0.5` to position sizing routed through it
5. Set `source_system = inverse_goldmine_stocks` on generated picks so downstream tracking works

**QA process:**

1. Dry-run: load current goldmine picks, apply inverse wrapper, verify flipped directions + mirrored TP/SL + halved qty
2. Check unique pick IDs don't collide with parent goldmine picks
3. After first live run: verify inverse picks in `dashboard_data.json` with correct `source_system`
4. Confirm forward tracker wires them into closed_picks

**Acceptance criteria:**

- Inverse picks generate within 24 hours of merge
- Half notional of parent
- Forward tracker records outcomes under `inverse_goldmine_stocks`
- After n ≥ 20 closes: follow-up task either promotes (WR ≥ 60%) or kills + blocks parent (WR < 40%)

**Risk:** Medium. First baby strategy wired live. **Verify inverse math is correct** — direction flipped, SL mirrored above entry on SHORT, TP mirrored below. Wrong-side SL causes instant stop-out.

---

### T1-F. Investigate + decide on `quan_engine_scalp` (540 trades, 38.9% WR, PF 1.25)

**Goal:** Biggest-sample borderline strategy in the book. Not blocked because PF 1.25 > 1.0, but 38.9% WR on 540 trades is the largest marginal drag. Decide: block, mutate, or tune.

**Files (investigation only):**

- `alpha_engine/scanner.py` — search for `quan_engine_scalp`
- `quan_engine/` — separate subsystem directory
- `audit_dashboard/data/dashboard_data.json → picks.recent_closed` filtered to `strategy=quan_engine_scalp`

**Investigation steps:**

1. Partition picks by: asset class, symbol, time-of-day, regime-at-entry, fwdWR at pick time
2. Compute WR/PF per partition — find any sub-slice with positive edge
3. Compare first-half vs second-half of 540 trades for decay signal
4. Check if 15/60-bar scalping framework has TP/SL imbalance

**Decision tree:**

- Sub-slice edge → tighten triggers. Document in `docs/strategy_audits/quan_engine_scalp_2026-04-14.md`
- Broken across slices → add to `BLOCKED_STRATEGIES` + mutation-before-kill
- Decaying → flag for decay watchlist
- Regime-dependent → gate by regime

**QA process:** Investigation doc is the deliverable. Any subsequent code change is a **separate follow-up task**.

**Acceptance criteria:**

- `docs/strategy_audits/quan_engine_scalp_2026-04-14.md` committed
- Recommended action stated with evidence
- Follow-up PR if action is block/tune/mutate

**Risk:** Medium-high for decision; zero for investigation.

---

### T1-G. Fix recurring workflow conflict-marker trap (issue #141)

**Goal:** `audit-dashboard.yml` commit step has a recurring failure where `<<<<<<< HEAD` conflict markers get left in auto-generated data files after the stash/pull/pop cycle. Blocks deployment for hours. Observed today: run 24408354405 failed, run 24411112345 hung for 1h27m.

**Evidence:**

```
Refusing to commit — unresolved git conflict markers detected in:
  audit_dashboard/data/ai_challenge_summary.json
  audit_trail/data/stock_prices.json
See issue #141 for background. Unstaging and aborting.
```

**Files to touch:**

- `.github/workflows/audit-dashboard.yml` — `Commit updated data` step around the `git stash pop || { ... }` fallthrough

**Implementation approach:**

1. After the `checkout --ours` + `git add` block, add a grep step for remaining `<<<<<<< HEAD` markers:
   ```bash
   DIRTY=$(git diff --cached --name-only | xargs -I{} grep -l '<<<<<<< HEAD' {} 2>/dev/null || true)
   if [ -n "$DIRTY" ]; then
     for f in $DIRTY; do
       git checkout --theirs -- "$f"
     done
   fi
   ```
2. Alternative: `git reset --hard HEAD` on specific poisoned files then regenerate via their individual generators
3. Add an early fail-fast check that rejects the run if the repo has markers from a prior bad state

**QA process:**

1. Do NOT test by creating a real merge conflict on main — blocks everyone
2. Create a unit test with pre-seeded conflict markers, verify the step exits cleanly
3. Post-merge: watch next 3-5 workflow runs complete successfully
4. If any future run still fails this way, open new issue referencing #141

**Acceptance criteria:**

- Next 5 consecutive workflow runs complete without `Refusing to commit` errors
- Workflow run time stays under 60 minutes (no hangs)
- Issue #141 closable

**Risk:** Medium. Touching the workflow file itself is sensitive — a bad edit breaks every deploy. **Test in a branch with manual `workflow_dispatch` before merging.**

**Coordination:** Multiple agents have touched this file — check git log first.

---

## TIER 2 — 1-2 weeks

### T2-A. R:R 2-3 death zone fix

**Goal:** Picks with R:R between 2.0 and 3.0 lose money net (PF 0.91 on n=1,152). This is the default R:R range most strategies land in.

**Evidence:**

| R:R | n | WR | PF |
|---|---|---|---|
| 0-1 | 978 | 44.1% | **1.50** |
| 1.5-2 | 1,235 | 46.7% | 1.14 |
| **2-3** | **1,152** | **38.7%** | **0.91** |
| 5+ | 37 | 62.2% | 1.98 |

**Investigation first:**

1. Which strategies are landing R:R 2-3? Partition closed picks by strategy, compute mean R:R
2. Which TP/SL parameter produces R:R 2-3? Usually `tp_atr_mult=2 + sl_atr_mult=1`
3. Would tightening to R:R 1:1 improve those strategies?

**Files (after investigation):**

- `alpha_engine/strategies/*.py` — individual strategy TP/SL configs
- `alpha_engine/tp_sl_filler.py` — ATR-based TP/SL
- `alpha_engine/adaptive_tp_sl.py` (known bug per Issue #186 — "calibrates on wrong dataset")

**QA process:**

1. Backtest: apply new R:R geometry retrospectively; verify PF improves
2. Forward-test: run on small strategy subset 1 week before wide rollout
3. Alert if max drawdown increases >2pp

**Acceptance criteria:**

- R:R 2-3 bucket shrinks from 1,152 to <500 on fresh data
- Aggregate PF rises
- No drawdown increase

**Risk:** High. TP/SL geometry affects every downstream strategy. Ablation-test per strategy.

---

### T2-B. Regime-aware direction filter (SHORT preference in bear)

**Goal:** SHORT beats LONG net (PF 1.32 vs 1.02) but active feed is LONG-heavy 3:1. In BEAR regime, LONG picks are catastrophically bad. Add regime gate.

**Prerequisite:** `regime_at_entry` is 0% populated today (MERCURYPROMPT.md Issue #186). Fix THAT first.

**Files:**

- `alpha_engine/scanner.py` — populate `regime_at_entry` at pick creation (wire from `alpha_engine/regime_*.py`)
- `audit_dashboard/hc_filter.js` — Gate 8 already reads it
- `tools/dashboard_hc_rules.py` — Python mirror
- `audit_trail/quality_gates.py:_apply_score_penalties` — add `score -= 15` for LONG-in-bear, `+3` for SHORT-in-bear

**QA process:**

1. Verify `regime_at_entry` populated on >80% of new picks within 1 week of fix
2. Regression: Playwright HC test still passes
3. Backtest: bear-regime LONGs get filtered

**Acceptance criteria:**

- `regime_at_entry` ≥ 80% populated
- Bear-LONG picks see ≥5 score penalty in `_penalties` log
- SHORT-in-bear gets small positive

**Risk:** Medium. Regime detection has existing bugs; don't build on shaky foundation.

---

### T2-C. FOREX pnl_pct scaling bug

**Goal:** FOREX picks report `pnl_pct` ~100× the actual underlying move. EURUSD=X 1.14338→1.15094 is a 0.66% move but ledger shows +66.76%. FOREX aggregate PF 2.03 is artificially inflated.

**Evidence:** Top "winners" in closed ledger: AUDUSD=X +95.58%, GBPJPY=X +76.13%, EURUSD=X +66.76%. None realistic.

**Files:**

- `alpha_engine/outcome_resolver.py` — where forex PnL is computed
- `kimi_signal_tracking/` — its own resolver if any
- `audit_trail/dashboard_generator.py:_normalize_pick` pnl fallback chain (~line 5125)

**Investigation steps:**

1. Trace forex `pnl_pct` from entry_price to exit_price
2. Determine multiplier source: leverage (50-100x common) vs pip-to-percent bug
3. Determine if bug is in collection vs aggregation

**Fix:**

1. Correct the root-cause scaling
2. Backfill closed forex picks if possible
3. Add sanity check: `abs(pnl_pct) < 20` on any forex row; reject/flag otherwise

**QA process:**

1. 10 random forex closes: compute manually `(exit-entry)/entry*100*direction_sign`
2. Compare to stored `pnl_pct` — current values are 50-100× the correct
3. Post-fix: values match within 0.1pp

**Acceptance criteria:**

- New forex closes have correct `pnl_pct`
- FOREX aggregate PF re-computed on corrected data stated in PR body (expected drop from 2.03 to ~1.0-1.2)
- Historical backfill or marked unreliable

**Risk:** Medium. Stakeholders reading "FOREX PF 2.03" will see it drop. Honest.

---

### T2-D. `null_ml_solo_source` timing fix (Codebuff's scope, coordinate)

**Goal:** The penalty at `audit_trail/quality_gates.py:2305-2316` fires on goldmine picks even when `ml_score` is populated in the final payload, because the penalty runs before ml_composite step. 21 of 34 goldmine picks drop 20 score points incorrectly.

**Evidence:** PR #207, `docs/HC_EQUITY_INVESTIGATION_2026-04-14.md`. Sample: `GE` has `ml_score=61.0` but `_penalties` contains `null_ml_solo_source(1):-20`.

**Files:**

- `audit_trail/quality_gates.py:2305-2316` — penalty itself
- `audit_trail/dashboard_generator.py` — pipeline order

**Approaches:**

1. **Move penalty to after ml_composite** (cleanest): reorder pipeline
2. **Exempt specific sources**: add `SOURCES_WITH_EXTERNAL_ML_SCORE = {'goldmine_stocks', ...}` skip list
3. **Re-read from checkpoint**: read `ml_composite_score` field if present

**Coordination:** Codebuff is paused with `quality_gates.py` uncommitted. **Wait for their drift-remediation to ship**, or send them a peer-bus message asking they handle it.

**QA process:**

1. Before: log 10 goldmine picks' penalty lists
2. After: verify `null_ml_solo_source` NOT in list
3. Regression: verify penalty STILL fires on truly single-source no-ml picks

**Acceptance criteria:**

- Penalty stops firing on picks with final `ml_composite_score > 0`
- Goldmine scores shift from 19-45 to 30-65
- Still blocks truly-missing-ml picks

**Risk:** Medium. Regression test coverage required.

---

### T2-E. `alpha_engine` crypto SL enforcement anomaly

**Goal:** Investigate why `alpha_engine` crypto picks have realized losses 10-12× their stated SL distance. Example: ALGOUSDT SHORT with 0.8% stated SL realized −10.39%.

**Files (investigation):**

- `alpha_engine/scanner.py` — pick creation
- `alpha_engine/outcome_resolver.py` — SL hit detection
- `alpha_engine/tp_sl_filler.py` — SL calculation
- `alpha_engine/adaptive_tp_sl.py` (known bug)
- `audit_trail/dashboard_generator.py:_normalize_pick` — pnl_pct normalization

**Investigation:**

1. Pull alpha_engine crypto SHORTs with `abs(pnl_pct) > 5` AND `(sl-entry)/entry*100 < 2`
2. For each, find raw pick in `alpha_engine/data/closed_picks.json` — check stored vs enforced SL
3. Check if pnl_pct is leveraged (same class as T2-C)
4. Check if outcome_resolver honors stored SL vs computes its own

**QA:** `docs/strategy_audits/alpha_engine_sl_enforcement_2026-04-14.md` with 10 examples.

**Acceptance criteria:** Root cause doc + follow-up task for actual fix.

**Risk:** Low for investigation; high for downstream fix (alpha_engine is 641 trades, biggest source).

---

### T2-F. `regime_terminal` 40% fwdWR audit

**Goal:** All 5 active regime_terminal equity picks (GOOGL, SPY, QQQ, AMD, META) show fwdWR=40%. Below the 45% Gate 5 floor. Before acting, verify whether 40% is real or calc bug.

**Files (investigation):**

- `audit_trail/dashboard_generator.py:10754` — `strat_fwd_wr` assignment from leaderboard
- `audit_trail/collect_strategy_leaderboard` function (~line 7980)
- `regime_terminal/` subsystem

**Investigation:**

1. Pull all closed picks where `strategy=regime_terminal`
2. Compute raw WR independently: `wins/(wins+losses)`
3. Compare to stored `strat_fwd_wr`
4. Match → real below-edge → inverse or kill
5. Mismatch → leaderboard bug → fix and regime_terminal passes Gate 5

**QA:** `docs/strategy_audits/regime_terminal_fwdwr_2026-04-14.md` with raw WR comparison.

**Risk:** Low.

---

### T2-G. Max-hold enforcement fix (multi_asset_institutional)

**Goal:** `penny_deep_oversold` has 3-day max_hold but picks held 22+ days. IONQ and RIOT examples closed with "Max hold exceeded (22d > 3d)" at −14.63% and −11.80%.

**Files:**

- `alpha_engine/outcome_resolver.py` — max_hold enforcement
- `multi_asset_institutional/` — strategy max_hold config
- `audit_trail/dashboard_generator.py:_is_closed_status`

**Investigation + fix:**

1. Find where `max_hold`/`max_holding_bars`/`max_holding_days` is read at close time
2. Check field name consistency across strategies
3. Implement universal enforcer: `now - entry_time > strategy.max_hold * day` → force-close

**QA process:**

1. Grep `Max hold exceeded` in closed picks — find all affected
2. Verify fix on test pick

**Acceptance criteria:** No future closed pick has `hold_days > strategy.max_hold` with "Max hold exceeded" reason.

**Risk:** Low-medium.

---

### T2-H. META score unlock (multi_asset_copytrader penalty trace)

**Goal:** META's strongest historical variant is at `multi_asset_copytrader` with `score=37, trust=5, fwdN=746, fwdWR=46.8%`. Passes Gates 4,5,6,8,9, fails only Gate 1. +13 score would make it the first-ever EQUITY pick to pass live HC.

**Files:**

- `audit_trail/quality_gates.py:_apply_score_penalties` around ~2042+ (Cursor's pointer to stale copytrader penalties) and ~2074+ (non-crypto raw floor)

**Investigation:**

1. Pull sample multi_asset_copytrader META pick
2. Trace `_penalties` list — which fire
3. Identify stale/incorrect penalties (similar pattern to `null_ml_solo_source`)
4. Remove or exempt for multi_asset_copytrader

**QA process:**

1. Before/after META score comparison
2. Broader impact: all multi_asset_copytrader picks should see positive delta
3. Regression: not pushing above real quality tier

**Acceptance criteria:**

- META at multi_asset_copytrader scores ≥ 50
- First EQUITY pick passes live HC filter
- Playwright confirms EQUITY count ≥ 1 in HC view

**Risk:** Medium.

---

### T2-I. `breakout_b_ml` near-miss unlock

**Goal:** 3 breakout_b_ml CRYPTO picks failing Gate 2 by 1-8 score points despite trust 6, fwdN 14, fwdWR 64.3%:

```
ADAUSDT  score=49  1 point gap
DOTUSDT  score=44  6 point gap
BNBUSDT  score=42  8 point gap
```

Close the score-depression gap → HC count rises from ~3 to ~6.

**Files:**

- `audit_trail/quality_gates.py:_apply_score_penalties` — trace breakout_b_ml
- `alpha_engine/strategies/breakout_b_ml.py` — if strategy has own scoring

**Same pattern as T2-D and T2-H.** Find penalty stack, identify mis-applying penalty, exempt/fix.

**Acceptance criteria:** ADAUSDT, DOTUSDT, BNBUSDT cross Gate 2. Playwright HC count: 3 → 6.

**Risk:** Medium.

---

### T2-J. `super_signals` + `multi_asset_copytrader` TP/SL exit attribution

**Goal:** These sources have clean profits (combined PF 1.53-1.94 on 877 trades) but report **zero TP_HIT and zero SL_HIT**. Outcomes are binary `WON`/`LOST` labels. Can't tune their TP/SL because we don't know which setting produced the wins.

**Files:**

- `super_signals/` subsystem (if dir exists)
- `copy_trader_intel/` — multi_asset_copytrader source
- `audit_trail/dashboard_generator.py:_normalize_pick` — `exit_reason` set (~line 5139)

**Investigation + fix:**

1. Pull sample `super_signals` closed pick — check raw `exit_reason`/`status`
2. If only `WON`/`LOST`, add post-resolver:
   ```python
   if abs(exit_price - tp) < abs(exit_price - entry):
       exit_reason = 'TP_HIT'
   elif abs(exit_price - sl) < abs(exit_price - entry):
       exit_reason = 'SL_HIT'
   ```

**QA process:**

1. Post-fix: at least 50% of future closes have TP_HIT/SL_HIT attribution
2. Backfill historical where possible

**Acceptance criteria:** TP_HIT/SL_HIT counts > 0 on these sources.

**Risk:** Low.

---

### T2-K. Forward-tracking audit sweep (goldmine-shaped bugs on other sources)

**Goal:** PR #207 revealed goldmine closed trades were silently dropped for months due to schema mismatch in `_extract_picks`. Same bug class may affect other sources.

**Files (investigation):**

- `audit_trail/dashboard_generator.py` `JSON_PICK_SOURCES` list (~line 3093)
- `_extract_picks` (~line 5588)
- `_normalize_pick` (~line 4960)

**Investigation steps:**

1. Grep `JSON_PICK_SOURCES` for tuples with `None` as 3rd element → no closed path
2. For each, check if source HAS closed trades file not wired
3. For each source with closed file, verify `_extract_picks` parses schema
4. Expected hits: `pm_whale_signals`, `pm_kalshi_signals`, `prediction_market_consensus`, `pm_momentum_signals` (confirmed today)

**Acceptance criteria:**

- `docs/FORWARD_TRACKING_AUDIT_SWEEP_2026-04-14.md` committed
- Per-source: gap identified, file path (if any), schema mismatch (if any)
- Fix tasks created for each

**Risk:** Zero investigation, low for fixes.

---

## TIER 3 — 2-4 weeks, investigation required

### T3-A. Forex copy-trader pipeline build

**Goal:** `copy_trader_intel` has forex trader clones. Wire picks through active→closed→leaderboard pipeline. Currently the 2 forex picks in active are not tracked.

**Files:** `copy_trader_intel/data/forex_copytrader_picks.json` (check), `audit_trail/dashboard_generator.py` JSON_PICK_SOURCES.

**Effort:** 1-2 weeks. Sub-tasks: identify source data, verify close attribution, wire through pipeline, test forward tracker.

**Acceptance:** Forex closed picks appear in leaderboard within 1 week.

---

### T3-B. Commodity Bollinger MR cross-port

**Goal:** Port Bollinger MR (works on equity PF 1.71, forex PF 4.18) to commodity futures GC=F, SI=F, PL=F, HG=F. Only viable path to COMMODITY HC picks.

**Effort:** 2-4 weeks. Real-data backtest on commodity symbols first.

**Acceptance:** Commodity closed-pick PF lower CI ≥ 1.2 on n ≥ 30 forward trades.

---

### T3-C. BOND accumulation monitoring

**Goal:** PR #200 added BOND_SYMBOLS to scanner. Need 3-6 weeks for n=30 bond closed picks. Passive task: weekly check.

**Files:** `tools/hc_health_monitor.py` — add BOND row tracking `strat_fwd_trades` accumulation.

**Acceptance:** n ≥ 30 bond closed picks + BOND-specific WR/PF computable.

---

### T3-D. PM forward-tracking pipeline (prediction markets)

**Goal:** `pm_whale_signals`, `pm_kalshi_signals`, etc. have `closed_path = None`. No forward tracking. Build an outcome resolver for PM signals (event-based, not price-based).

**Effort:** Multi-day design + implementation. Decisions: close semantics (time horizon vs market resolution).

**Acceptance:** PM closed trades show up in leaderboard with valid WR/PF.

---

## TIER 4 — deferred / parked

### T4-A. ETF/FUTURES retire decision

**Goal:** ETF PF 0.28, FUTURES WR 5.9% — structurally dead. MIMO rescue strategies failed real-data backtest (PR #200). Decision: permanently retire from HC view vs commit to multi-week redesign.

**Recommendation:** Retire. Update `hcEdgeManifest` to make "DEAD" label persistent + link to v2 MIMO harness findings.

**Effort if retire:** 1 hour. **If redesign:** 4-8 weeks per class.

---

### T4-B. Full R:R tuning audit

**Goal:** Beyond T2-A death zone fix, full ablation study of R:R per strategy. Revisit after T2-A lands.

---

### T4-C. Inverse candidates from sub-40% WR strategies

**Goal:** Systematic inverse generation for every n ≥ 30, WR < 40% strategy following the `inverse_goldmine` pattern.

**Candidates today:**

- `ml_crypto_pred` (16.8% WR → theoretical 83% inverse)
- `multi_asset_scanner` (16.9% WR)
- `alpha_engine_fast` (40% WR — borderline)
- `cta_replicator` (36.6% WR — small sample)

**NOT a T1 task** because current evidence is purely statistical. **Wait for `inverse_goldmine_stocks` results (T1-E)** to confirm the pattern before mass-producing inverses.

**Effort:** 30 min per strategy meta.json.

---

### T4-D. Strategy health monitor alerting

**Goal:** When a previously-verified strategy drops below PROVEN thresholds (WR −15pp, PF <1.0), alert automatically. `tools/hc_health_monitor.py` tracks state but doesn't alert.

**Effort:** 2-3 days.

---

## Shared coordination files

| File | Touched today by | Status |
|---|---|---|
| `audit_trail/quality_gates.py` | me (PR #221 blocks) | stable |
| `audit_dashboard/template.html` | me (PR #200, #211, #219) | stable but dense |
| `audit_dashboard/hc_filter.js` | Cursor + me | stable |
| `config/hc_gate_params.json` | Cursor | stable |
| `alpha_engine/ml_ranker.py` | Codebuff (uncommitted, paused) | **DO NOT TOUCH** |
| `alpha_engine/model_calibration.py` | Codebuff (uncommitted, paused) | **DO NOT TOUCH** |
| `.github/workflows/audit-dashboard.yml` | Multiple | **CAREFUL — breaks deploys if bad** |

## Test tooling available

- `scripts/test_hc_button_playwright.py` — desktop + Galaxy S20 Playwright
- `scripts/test_hc_button_live.py` — targets live findtorontoevents.ca/audit
- `tools/hc_gate_failure_report.py` — per-pick first-failed-gate + near-miss surfacing
- `tools/hc_health_monitor.py` — weekly HC snapshot with trend tracking
- `tools/dashboard_hc_rules.py` — Python mirror of hc_filter.js for backtest parity
- `tools/_hc_noncrypto_diagnostic.py` — Cursor's equity failure diagnostic
- `scripts/backtest_tier_bypass_2026-04-14.py` — template for other backtests

## Today's session PRs (for context)

All merged to main, deployment ETA depends on workflow recovery (T1-G):

- #200 HC button wiring + per-class filter + v2 MIMO harness + Playwright test
- #206 SPORTS data-layer fix
- #207 Goldmine forward-tracking loader (exposed 21% WR)
- #208 inverse_goldmine_stocks baby config (T1-E wires it live)
- #209 Tier bypass backtest (validated Option A — no bypass)
- #210 Roadmap + diagnostic tools + health monitor
- #211 FWD WR + FWD N columns
- #218 Strategy consistency audit (reporting)
- #219 Golden Glow / Verified Edge badges
- #220 Honest visibility-vs-improvement disclaimer
- #221 **First actual improvement**: 5 loser strategy blocks + edge discovery + plan

## How to pick your task

**Quick session:** T1-C, T1-D, or T1-G.

**Codebuff resuming:** finish drift-remediation commit first, then T2-D.

**Deep investigation work:** T1-F (quan_engine_scalp), T2-E (alpha_engine SL), T2-F (regime_terminal), T2-K (forward-tracking sweep).

**Medium task:** T1-A, T1-B, T1-E, T2-A, T2-C.

**Don't pick alone:** T1-G (workflow file), T2-A (R:R across strategies), T2-D (coordinate with Codebuff). Cross-cutting concerns or need user check-in first.

---

*Last updated by Claude Opus 4.6 (1M context) on 2026-04-14 evening. Session ending. Next agent: pick a task, follow the spec, ship in its own PR. Reference the Task ID in the commit message.*
