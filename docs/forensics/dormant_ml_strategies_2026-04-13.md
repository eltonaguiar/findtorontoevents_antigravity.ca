# Dormant ML Strategies Investigation — ml_enhanced_FETUSDT / RENDERUSDT

Investigator: Claude (Opus 4.6 1M, read-only forensic)
Date: 2026-04-13
Branch: `chore/forensic-dormant-ml`
Reproduction: `tools/forensic/dormant_ml_reproduce.py`
Context PRs: #161 (`tools/adaptive/strategy_trust.py` surfaced these as dormant winners),
#157 (`tools/data_integrity/strategy_correlation.py` showed three `ml_enhanced_*`
strategies are 93-99% correlated — effectively one model).

## TL;DR

Neither strategy is actually dormant. Both are still firing at a normal cadence
inside `ml_crypto_predictor/enhanced_models/live_picks/all_picks_log.json` as of
2026-04-14T00:53Z (a few hours before this investigation). The bridge
`alpha_engine/ml_strategy_reviver.py` still copies them into
`alpha_engine/data/active_picks.json` (FET has one open pick from 2026-04-12;
RENDER was fully closed but generated 25 picks in the past 34 days). The
`strategy_trust.py` report correctly classifies them as `INSUFFICIENT`
(48h closes below `MIN_RECENT_48H=3`); the "dormant winner" framing in the
PR #161 body is a **threshold artifact**, not real dormancy.

The more important finding underneath the alleged dormancy is that the
historical edge was **never real in the form the scorer sees it**. The FET
n=32 ledger contains **10 duplicate +0.5813 TP_HITs on the same
`entry_price=0.1586 → exit_price=0.2508` trade replayed across 10 different
`entry_date` days in March**. Remove that one cluster and the raw WR drops
from 75% to ~45%, with all closes since 2026-03-31 exiting `EXPIRED` flat
or at a small loss (TP never reached). RENDER shows the same pattern: three
big TP_HITs on 2026-03-16, then mostly flat EXPIRED or SL_HIT afterward. The
`ewm_pf_23d=18.4` number is dominated by that one replayed winner, not a
genuine 23-day edge.

**Diagnosis: (f) Never really in live dispatch as the surfaced metric
suggests — historical WR/PF are inflated by ledger duplicates and an early
TP cluster that the model cannot reproduce in the current regime —
*plus* (c-lite) the `live_picks_tracker` prefers `C_random_forest` as its
A/B-test winner so `B_lightgbm` and `D_ensemble_stack` only win
tie-breakers, suppressing the exact variants surfaced by strategy_trust.**
**Evidence grade: DECISIVE on the ledger-duplicate artifact and the
`PREFERRED_MODEL_VARIANT = "C_random_forest"` routing; STRONG on the claim
that raw_wr=75% is not reproducible forward.**
Recommendation: **do NOT resurrect** as-is. Do NOT kill either — both files,
models, and feeders are healthy. The correct follow-up is to
(1) de-duplicate `closed_picks.json` by `(strategy, symbol, entry_price,
exit_price, pnl_pct)` before computing any trust scores, and (2) either
treat the historical metric as `LEGACY_BACKTEST_ONLY` in the scorer or add
an "edge-decay" classification that catches "raw_wr high, last_7d PF ~1"
cases.

## Reproduction

Script: `tools/forensic/dormant_ml_reproduce.py` (stdlib only, stand-alone).
Run from repo root:

```
python tools/forensic/dormant_ml_reproduce.py
```

It reads `alpha_engine/data/closed_picks.json`,
`alpha_engine/data/active_picks.json`, and
`ml_crypto_predictor/enhanced_models/live_picks/{active_picks,closed_picks,all_picks_log}.json`,
and reports n, first/last timestamp, 48h/7d counts, raw WR, and duplicate
clusters for both target strategies.

Observed on this run (2026-04-14 ~01:14 UTC, 10,448,960 bytes
`closed_picks.json`, 4,157 rows after ghost-filter):

```
ml_enhanced_FETUSDT_1d_B_lightgbm
  alpha_engine/closed_picks:  n=32  wins=24  raw_wr=0.750  pf=28.40  (inflated)
  alpha_engine/active_picks:  n=1   (entered 2026-04-12, still open)
  mlcp/all_picks_log:         n=623 (status: 71 WON, 388 EXPIRED, 138 ACTIVE, 26 CLOSED)
  mlcp/closed_picks:          last closed_at 2026-04-13 (FETUSDT 1d B_lightgbm)
  Duplicate cluster:          10 distinct rows with entry=0.1586 exit=0.2508
                              pnl=+0.5813 but distinct entry_date in Mar 13-25

ml_enhanced_RENDERUSDT_4h_D_ensemble_stack
  alpha_engine/closed_picks:  n=25  wins=16  raw_wr=0.640  pf=2.81
  alpha_engine/active_picks:  n=0
  mlcp/all_picks_log:         n=246 (status: 23 WON, 171 EXPIRED, 27 LOST, 25 ACTIVE)
  mlcp/closed_picks:          last closed_at 2026-04-13
```

`python tools/adaptive/strategy_trust.py --json` reports both strategies in
`INSUFFICIENT` with `last_48h.n = 2` (not 0) and `pf=0.0` (2 losses in
last 48h). They just fall below the `MIN_RECENT_48H = 3` bar by one trade.

## Timeline

### ml_enhanced_FETUSDT_1d_B_lightgbm (n=32 in alpha_engine/closed_picks.json)

```
2026-02-22  first created_at  (entry_date 2026-02-22, closed later)
2026-03-16  6× TP_HIT        pnls +0.30, +0.46, +0.45, +0.44, +0.35, +0.37
2026-03-24  1× EXPIRED       -0.01
2026-03-25 10× TP_HIT SAME   all entry=0.1586 exit=0.2508 pnl=+0.5813
2026-03-31  2× EXPIRED       -0.03, -0.09
2026-04-01  1× EXPIRED       +0.05
2026-04-03  1× EXPIRED       +0.01
2026-04-04  2× EXPIRED       +0.04, +0.03
2026-04-07  3× EXPIRED       -0.01, -0.01, +0.10
2026-04-09  2× EXPIRED       +0.02, +0.01
2026-04-10  1× EXPIRED       +0.02
2026-04-11  1× EXPIRED       -0.04
2026-04-13  2× EXPIRED       -0.01, -0.09   <-- 12h before scan (within 48h)
```

Gap analysis: **no gap**. Last close is 12.1h before the strategy_trust run.
Every close since 2026-03-31 is `EXPIRED` (never reached the 10% TP or the
7% SL — the model cannot realise its own targets in the April regime). The
"75% WR" is carried entirely by the March 16-25 window, of which at least
10 closes (31%) are **identical replay of one trade**.

### ml_enhanced_RENDERUSDT_4h_D_ensemble_stack (n=25)

```
2026-03-10  first created_at
2026-03-16  3× TP_HIT        +0.30, +0.19, +0.20
2026-03-16  2× EXPIRED       +0.09, +0.04
2026-03-17  1× EXPIRED       +0.04
2026-03-18  1× EXPIRED       -0.01
2026-03-28  3× SL_HIT        -0.12, -0.08, -0.10
2026-03-31  2× EXPIRED       +0.05, +0.03
2026-04-01  1× EXPIRED       +0.03
2026-04-03  1× EXPIRED       +0.11
2026-04-04  2× EXPIRED       +0.06, +0.02
2026-04-07  3× EXPIRED       -0.02, -0.01, +0.08
2026-04-09  2× EXPIRED       +0.06, +0.07
2026-04-10  1× EXPIRED       +0.00
2026-04-11  1× EXPIRED       -0.01
2026-04-12  2× SL_HIT        -0.07, -0.07   <-- 38.4h before scan
```

Gap analysis: **no gap**. 38.4h since last close, 2 closes within 48h but
below `MIN_RECENT_48H=3`. Raw WR 64% is more honest than FET but almost all
wins are tiny (+1% – +11%) vs occasional larger losses (-7% to -12%).
`ewm_pf_23d=2.17` is plausible but `last_7d_pf` is already 1.22 — the edge
is decaying.

Lifetime metrics earned in a concentrated window: **yes, partially**. The 3
TP_HITs on 2026-03-16 account for most of the PF; every close since 2026-04-01
is either tiny-flat EXPIRED or SL_HIT.

## Code audit

### Strategy name construction

`ml_crypto_predictor/enhanced_models/live_predictor.py` line 216 and
`live_picks_tracker.py` lines 216-298 iterate
`["A_xgboost", "B_lightgbm", "C_random_forest", "D_ensemble_stack"]` model
variants per pair/timeframe. The strategy name gets assembled by the alpha
bridge in `alpha_engine/ml_strategy_reviver.py:559`:

```
strategy_name = f"ml_enhanced_{model_variant}" if model_variant else f"ml_enhanced_{symbol}"
```

So `ml_enhanced_FETUSDT_1d_B_lightgbm` and
`ml_enhanced_RENDERUSDT_4h_D_ensemble_stack` are **not registry entries**
— they are dynamic names produced whenever the bridge copies a pick whose
`model_variant` field matches that pair/timeframe/variant triple.

### Which variant actually wins

`alpha_engine/ml_strategy_reviver.py:144`:

```
PREFERRED_MODEL_VARIANT = "C_random_forest"  # A/B test winner (81 wins, 0.275 avg)
```

Wait — that line is actually in `ml_crypto_predictor/enhanced_models/live_picks_tracker.py:144`.
Per-pair/timeframe the tracker loads every variant's joblib file, computes
`prob_up`, then **always prefers the variant whose name contains
`C_random_forest`** (lines 282-291). `B_lightgbm` and `D_ensemble_stack`
only win when `C_random_forest.joblib` is missing or errors. This is the
mechanism that makes `_1d_B_lightgbm` and `_4h_D_ensemble_stack` *look*
dormant in the live picks stream: the tracker picks C by default.
Confirmed by counting variants in
`ml_crypto_predictor/enhanced_models/live_picks/active_picks.json` (34 rows):
only one `B_lightgbm` row (INJUSDT_1d) and one `D_ensemble_stack` row
(RENDERUSDT_1h, not 4h). In
`ml_crypto_predictor/enhanced_models/results/live_picks_1h.json` (53 rows):
`A_xgboost=37`, `C_random_forest=7`, `B_lightgbm=9`, `D_ensemble_stack=0`.

This is already documented as the "v1.3 fix" in
`live_picks_tracker.py` lines 254-258: "Old logic picked highest prob_up
(most overconfident model). An overfit model predicting 85% always 'won'
selection -> bad picks. New logic: prefer the A/B test winner, fall back
to consensus."

### Active pipelines

- `.github/workflows/ml-forward-test.yml` runs every 4h (`30 */4 * * *`)
  via `python -m ml_crypto_predictor.enhanced_models.main live-picks` → calls
  `cmd_live_picks()` in `main.py:174` → `live_picks_tracker.run_prediction_cycle()`.
  Still active, still producing picks; last commit
  `b4ca7fb3b4 Forward test [2026-04-13 20:55 UTC] - 28 active, 37 closed`.
- `.github/workflows/enhanced-ml-crypto.yml` runs `predict` every hour.
- `alpha_engine/ml_strategy_reviver.py` is called from
  `alpha_engine/production_scanner.py` (grep hits around lines 2284, 2324-25,
  4047-48 in `production_scanner.py` show the `ml_enhanced_{FET,BNB,RENDER}`
  prefixes in active whitelists).
- No `BLOCKED_SOURCE_SYSTEMS` entry touches either target strategy.
  `ml_crypto_pred_v12` is blocked (quality_gates.py:834) but that's the
  v12 archive feeder, not the enhanced_models live pipeline.

## Model file audit

Both joblib files are present on disk and were touched in the worktree on
2026-04-13 21:13 (checkout timestamp, normal for a fresh worktree —
upstream mtimes are preserved by the ML feedback-retrain workflow).

```
ml_crypto_predictor/enhanced_models/models/FETUSDT_1d_B_lightgbm.joblib
  Size: 802,868 bytes        Modify: 2026-04-13 21:13:20

ml_crypto_predictor/enhanced_models/models/RENDERUSDT_4h_D_ensemble_stack.joblib
  Size: 3,175,470 bytes      Modify: 2026-04-13 21:13:25
```

The matching scalers (`FETUSDT_1d_scaler.joblib`, `RENDERUSDT_4h_v3_scaler.joblib`)
also exist. Total of 1,746 joblib files under
`ml_crypto_predictor/enhanced_models/models/`. No load-error traces were
found for these files in the recent ML bot commits.

`live_picks_tracker.py:234` globs `MODELS_DIR / f"{pair}_{tf_name}_*.joblib"`
so every variant on disk gets loaded; missing variants just silently
`continue`. Neither model is missing; neither is being skipped by a loader
error.

## Git log audit

30-day `git log --all --oneline -S "ml_enhanced_FETUSDT_1d_B_lightgbm"`
and the `RENDERUSDT_4h_D_ensemble_stack` equivalent return only bot-written
auto-commits (hindsight learner, dashboard refresh, signal recorder,
Enhanced ML predict) plus the two PR #161 commits that **added** the
strategy name as an example in `tools/adaptive/strategy_trust.py`
documentation. No human commit in the last 30 days touched code that
blocks, disables, or removes either strategy. `alpha_engine/ml_strategy_reviver.py`
was last touched structurally by `3c59800e69 feat(MiniMax): Add
edge-optimized strategies targeting low-pick/high-opportunity areas`, which
does not remove either strategy from `PROVEN_STRATEGIES` (both still present
at lines 137-149 for FET and 313-325 for RENDER_4h).

## Hypothesis test: (a) Explicit block

Checked:

- `audit_trail/quality_gates.py:822-844` — `BLOCKED_SOURCE_SYSTEMS` contains
  `ml_crypto_pred_v12` but NOT `ml_enhanced_*` anything, and the FET/RENDER
  strategy names are checked as `source.lower() in BLOCKED_SOURCE_SYSTEMS`
  (line 3233) which compares strategy *sources*, not strategy name suffixes.
- `alpha_engine/auto_tuner.py:114-117` blocks 4 `ml_enhanced_*` entries
  (BTCUSDT_15m_D, ADAUSDT_15m_D, ETHUSDT_1h_D, ETHUSDT_4h_D) — none overlap
  with our targets.
- `alpha_engine/confluence_engine.py:208-209` blocks
  `ml_enhanced_{BTCUSDT,ADAUSDT}_15m_D_ensemble_stack` — not ours.
- `alpha_engine/crypto_risk_gates.py:33-60` — same two 15m ensemble blocks.

**Verdict: NOT EXPLICITLY BLOCKED.**

## Hypothesis test: (b) Missing model file

Both `.joblib` files exist, are sized plausibly (800KB / 3.2MB), and
the matching scaler files exist. No loader error trace in the logs.

**Verdict: MODELS PRESENT AND LOADABLE.**

## Hypothesis test: (c) Scanner broken

`ml-forward-test.yml` workflow: last successful commit
`b4ca7fb3b4 Forward test [2026-04-13 20:55 UTC] - 28 active, 37 closed`.
`ml_crypto_predictor/enhanced_models/live_picks/all_picks_log.json` has
`last generated_at = 2026-04-14T00:53:41Z` for both target strategies
(check reproduction script). **Scanner is running normally.**

There IS a softer version of (c): the `PREFERRED_MODEL_VARIANT =
"C_random_forest"` routing means `_1d_B_lightgbm` / `_4h_D_ensemble_stack`
only fire when `C_random_forest` is missing or errors on that pair/TF.
That is not "broken scanner" — it is intended selection logic — but it IS
the reason the specific variant names surfaced by `strategy_trust.py` see
sparse 48h traffic.

**Verdict: SCANNER HEALTHY; VARIANT SELECTION BY DESIGN SUPPRESSES THESE
TWO SPECIFIC VARIANTS.**

## Hypothesis test: (d) Data feed gap

Fetchable: both FETUSDT and RENDERUSDT are in `CRYPTO_PAIRS` in
`ml_crypto_predictor/enhanced_models/config.py:57, 36`. Latest pick
`generated_at = 2026-04-14T00:53Z` in `all_picks_log.json` proves
`fetch_klines` is returning data for both pairs. Neither is delisted. The
`OTHER_EXCHANGE_PAIRS` dict (config.py:83-89) does not contain FET or
RENDER — they are on Binance spot.

**Verdict: NO DATA FEED GAP.**

## Hypothesis test: (e) Removed from registry

`PROVEN_STRATEGIES` in `alpha_engine/ml_strategy_reviver.py:137-325` still
lists both (`ml_enhanced_FETUSDT_1d_B_lightgbm` at 137, the RENDER 4h
inverse at 313 — the *forward* entry is the implicit dynamic name). Neither
was removed by a recent commit. `alpha_engine/concentration_model.py:65-67`
still allocates 30% to `ml_enhanced_fetusdt_1d_b_lightgbm` and 10% each to
the two RENDER variants. `alpha_engine/elite_scorer.py:229-231` still has
hardcoded high elite scores (93.8, 87.5, 87.5) for them. `send_to_bus.py:27`
still broadcasts `ml_enhanced_FETUSDT_1d_B_lightgbm` on startup.

**Verdict: NOT REMOVED FROM REGISTRY.**

## Hypothesis test: (f) Never actually in live dispatch (in the form the scorer sees)

This is the **dominant hypothesis, in a nuanced form**.

Yes, they ARE dispatched by the real live pipeline
(`ml_crypto_predictor/enhanced_models/main.py live-picks`) and ARE
re-imported by `alpha_engine/ml_strategy_reviver.py`. The `all_picks_log`
counts show 623 / 246 historical entries, 138 / 25 currently active,
last generation < 30 min before the scorer ran. That is not "never in
live dispatch".

But the `n=32` / `n=25` counts in `alpha_engine/data/closed_picks.json`
that drive `strategy_trust.py`'s 75% / 64% raw_wr and 18.4 / 2.17 ewm_pf
are **not a clean forward-test population**:

1. **10 of 32 FET closes are literal duplicates** of the same
   `entry_price=0.1586 → exit_price=0.2508 → pnl=+0.5813` trade, with
   distinct `entry_date` labels spanning 2026-03-13 through 2026-03-25
   but identical prices. Either the reviver created 10 picks for the same
   underlying trade (daily re-entry on an already-open position while the
   price had not moved) and they all resolved against the same
   eventual exit price, or a batch-backfill job re-wrote the same outcome
   10 times. Either way the 10 are not 10 independent samples.
2. **17 of 32 FET closes** (53%) land in a 10-day window (2026-03-16 to
   2026-03-25). The remaining 15 since 2026-03-31 are all `EXPIRED`,
   averaging +0.005 PnL — essentially a coin flip around zero at the
   1d horizon.
3. **All 3 FET `TP_HIT` rows on 2026-03-16** resolved at `exit_price=0.2508`
   matching the replayed cluster. This is either a bulk-resolve job
   backfilling March 16 entries at the March 25 price, or the reviver was
   adding the same open trade again each day while the model kept
   predicting BUY.
4. **RENDER is cleaner** — 25 distinct `(entry,exit)` tuples — but its
   edge is carried by 3 TP_HITs and the remainder are small EXPIRED or
   SL_HIT. `last_7d_pf=1.22` is already ≈ break-even; `ewm_pf_23d=2.17`
   is not a forward-reproducible 23-day edge.

Combined with the hypothesis (c-lite) variant-preference routing, the
"zero 48h activity" framing in PR #161 is factually wrong (2 closes each
within 48h, just below the threshold) and the "exceptional historical
edge" claim is inflated by at least 10 replayed ledger rows.

**Verdict: "Dormant winner" is a strategy_trust.py scoring artifact driven
by (1) duplicated closed_picks rows and (2) a `MIN_RECENT_48H=3` threshold
that accidentally treats `last_48h.n=2` the same as `n=0`.**

## Recommendation

**Do NOT resurrect, do NOT kill.** Both strategies are already live in the
correct pipeline — they are not missing from dispatch, they are not
blocked, and their model files are healthy. The scorer is telling a half-
true story because of data hygiene upstream.

Concrete next actions for a follow-up PR (out of scope for this read-only
forensic):

1. **De-duplicate `closed_picks.json` writes in `ml_strategy_reviver.py`**.
   The dedup key `{strategy}::{symbol}::{entry_date}` is too loose — it
   lets the same open trade be re-inserted daily. Tighten to
   `{strategy}::{symbol}::{entry_price}::{take_profit}::{stop_loss}` or
   add an "already_has_open_forward_instance" guard before inserting a
   new pick with the same entry price. The 10 FET +0.5813 rows are the
   smoking gun.
2. **Add a `LEGACY_BACKTEST_ONLY` or `EDGE_DECAY_DETECTED` classification
   to `tools/adaptive/strategy_trust.py`.** Current rule:
   `raw_wr > 0.6 AND ewm_pf_23d > 3.0 AND last_7d_pf < 1.3` → mark
   `EDGE_DECAY_DETECTED` instead of surfacing as a "dormant winner".
   This catches the FET/RENDER pattern where lifetime metrics look
   fantastic but recent windows show the edge is gone.
3. **Drop `MIN_RECENT_48H=3` artifact handling**: any `n < MIN_TRADES`
   already goes to `INSUFFICIENT`; a strategy with `n=32` and
   `last_48h.n=2` should at minimum land in `STABLE` with a "sparse
   recent" flag so we don't call it dormant.
4. **Consolidate the 3 correlated `ml_enhanced_*` strategies** per PR #157
   (rho 0.94-0.99 between FET_1d and RENDER_1h/4h). They are one model
   in three wrappers; the concentration in `concentration_model.py:15-17`
   already treats RENDER 1h+4h as one 20% bucket.

## Appendix: data sources

Files read (all absolute paths):

- `e:\findtorontoevents_antigravity.ca\.claude\worktrees\agent-a559c20d\alpha_engine\data\closed_picks.json`
  — 11,448,960 bytes, 4,157 rows (ghost-filtered), 32 FET + 25 RENDER.
- `e:\findtorontoevents_antigravity.ca\.claude\worktrees\agent-a559c20d\alpha_engine\data\active_picks.json`
  — 1 FET active (entry 2026-04-12), 0 RENDER_4h active, 1 RENDER_1h active.
- `e:\findtorontoevents_antigravity.ca\.claude\worktrees\agent-a559c20d\ml_crypto_predictor\enhanced_models\live_picks\all_picks_log.json`
  — 7,366 rows, 623 FET_1d_B_lightgbm, 246 RENDER_4h_D_ensemble_stack.
- `e:\findtorontoevents_antigravity.ca\.claude\worktrees\agent-a559c20d\ml_crypto_predictor\enhanced_models\live_picks\active_picks.json`
  — 34 rows, dominated by `A_xgboost` and `C_random_forest`.
- `e:\findtorontoevents_antigravity.ca\.claude\worktrees\agent-a559c20d\ml_crypto_predictor\enhanced_models\live_picks\closed_picks.json`
  — 37 rows (mlcp-side closed).
- `e:\findtorontoevents_antigravity.ca\.claude\worktrees\agent-a559c20d\ml_crypto_predictor\enhanced_models\results\live_picks_1h.json`
  — 53 rows, all `timeframe=1h`, variant mix `A_xgboost=37 / C_random_forest=7 / B_lightgbm=9 / D_ensemble_stack=0`.
- `e:\findtorontoevents_antigravity.ca\.claude\worktrees\agent-a559c20d\ml_crypto_predictor\enhanced_models\models\FETUSDT_1d_B_lightgbm.joblib`
  — 802,868 bytes, present.
- `e:\findtorontoevents_antigravity.ca\.claude\worktrees\agent-a559c20d\ml_crypto_predictor\enhanced_models\models\RENDERUSDT_4h_D_ensemble_stack.joblib`
  — 3,175,470 bytes, present.

Code files investigated:

- `tools/adaptive/strategy_trust.py` — scorer, MIN_RECENT_48H=3 threshold at line 38.
- `tools/data_integrity/_common.py` — CLOSED_PICKS path constant at line 10.
- `alpha_engine/ml_strategy_reviver.py` — bridge, PROVEN_STRATEGIES dict,
  dedup-by-`{strategy}::{symbol}::{entry_date}` at line 571.
- `alpha_engine/production_scanner.py` — active `ml_enhanced_*` whitelist at
  lines 2284, 2324-2325, 4047-4048 (no block).
- `alpha_engine/concentration_model.py` — 30% FET / 10% RENDER_1h /
  10% RENDER_4h still allocated (lines 65-68).
- `alpha_engine/elite_scorer.py:229-231` — hardcoded 93.8 / 87.5 / 87.5
  elite scores.
- `alpha_engine/auto_tuner.py:114-117`, `alpha_engine/confluence_engine.py:208-209`,
  `alpha_engine/crypto_risk_gates.py:33-60` — ml_enhanced_* blocks, none
  of which target FET_1d_B_lightgbm or RENDER_4h_D_ensemble_stack.
- `audit_trail/quality_gates.py:822-844` — BLOCKED_SOURCE_SYSTEMS, does not
  contain either strategy.
- `audit_trail/hf_pick_validator.py:90-92` — both names listed as "high WR
  in closed picks", not blocked.
- `ml_crypto_predictor/enhanced_models/live_predictor.py:216` — iterates
  all 4 variants per pair/timeframe.
- `ml_crypto_predictor/enhanced_models/live_picks_tracker.py:144, 282-298` —
  `PREFERRED_MODEL_VARIANT = "C_random_forest"` routing.
- `ml_crypto_predictor/enhanced_models/config.py:21-78` — CRYPTO_PAIRS
  includes FETUSDT, RENDERUSDT; TIMEFRAMES includes 1d and 4h.
- `.github/workflows/ml-forward-test.yml` — 4-hourly cron for live-picks.
- `.github/workflows/enhanced-ml-crypto.yml` — hourly predict.
