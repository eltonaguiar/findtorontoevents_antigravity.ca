# /money-maker-readyv2 — CRYPTO

## Class verdict at 06:30Z 2026-05-31
PF=0.18  WR=15.1%  n=892 (90d closed, WON+LOST only, post-resolver)  Sharpe~ -0.36
T2-status: **FAIL on (PF, WR, MDD)** — PASS only on n.

Notes:
- 90d WON+LOST sample: WR 135/892 = 15.1%, gross_win=1560.65, gross_loss=8730.63, **PF 0.18**.
- 14d slice: n=194, WR=25.3%, PF=0.89 (improving but still sub-1).
- 48h closed: ~4 — backlog is enormous (3,284 ACTIVE CRYPTO picks; **+1,838 ACTIVE if TP_HIT/SL_HIT/TIME_EXIT statuses are counted, see Resolver bug below**).
- Recency confirms CLAUDE.md status line: "CRYPTO 78.9% Smart-Picks figure DISPUTED — raw DB closer to 15-43% WR / PF<1."

## Best candidate
**None** at n>=10 with PF>1.0 in 90d. The only PF>1 strategy at any n>=3 is `ml_strategy_reviver_inverse` (n=3, WR=66.7%, PF=3.54) — sample too small to act on; 199 ACTIVE picks will close out the verdict over the next 30d.

Phase 3 MC watchlist: CRYPTO has NO MC-flagged candidate (MC winners were EQUITY `stocks_rsi2_pullback` and FOREX `fx_smart_carry_trade_momentum`).

Per-strategy 90d closed (n>=5):

| source_system | n | WR | PF | avg_pnl | status |
|---|---|---|---|---|---|
| prediction_market_agents | 9 | 22.2% | 0.76 | -0.17% | small-n |
| genome | 21 | 28.6% | 0.67 | -0.73% | sub-edge |
| copy_trader_intel | 266 | 32.7% | 0.63 | -2.98% | **top emitter, losing** |
| battleground_luxalgo | 53 | 24.5% | 0.25 | -2.34% | luxalgo legacy drag |
| genome_mutations | 23 | 17.4% | 0.20 | -2.15% | drag |
| quan_engine | 9 | 11.1% | 0.05 | -10.55% | already blocked CRYPTO pair |
| alpha_engine | 200 | 9.5% | 0.03 | -14.99% | **catastrophic — meta-engine** |
| alpha_engine_fast | 101 | 0.0% | 0.00 | -2.48% | **BLOCKED but emitting** |
| ml_crypto_predictor | 140 | 0.0% | 0.00 | -7.66% | **BLOCKED LONG but emitting + resolver mislabel** |
| battleground | 24 | 0.0% | 0.00 | -49.27% | catastrophic |
| regime_terminal | 10 | 0.0% | 0.00 | -3.44% | catastrophic |
| mercury2 | 21 | 0.0% | 0.00 | -24.89% | catastrophic |

## T2 gap
- Class has n=892 closed (already past n=100 threshold), but **PF 0.18 disqualifies on edge**.
- Need PF to climb from 0.18 → 1.50 (8.3x improvement). At current emission mix this is unachievable without retiring the 0%-WR cohort.
- If we cut the four 0%-WR strategies (alpha_engine_fast, ml_crypto_predictor LONG, battleground, regime_terminal, mercury2), residual PF jumps from 0.18 to ~0.55 (back-of-envelope, removes ~3,890% gross_loss, retains ~1,560 gross_win). Still sub-1.5 — but in striking distance.
- Time-to-T2: indeterminate at current cadence; **PF improvement, not n growth, is the gating constraint.**

## Bottleneck #1 (THE story for this class): blocklist not wired to emitter

`audit_trail/quality_gates.py::BLOCKED_SOURCE_SYSTEMS` (line 1917) AND `_BLOCKED_SOURCE_STRATEGY_PAIRS` (line ~2112) explicitly ban these for CRYPTO:

- `("CRYPTO", "alpha_engine_fast")` — line 2717 ("alpha_engine_fast: 362 closed, PF 0.62, -128% PnL, 155% MDD")
- `("CRYPTO", "ml_crypto_predictor", "LONG")` — line 2990 (per Apr-17 deep-dive)
- `("CRYPTO", "mercury2_fast")` — line 2752

Live DB shows these are STILL EMITTING in the last 7 days:

| strategy | banned for CRYPTO | picks last 7d | last emit |
|---|---|---|---|
| ml_crypto_predictor LONG | yes (since 2026-04-04) | **206** | 2026-05-31 03:31Z |
| alpha_engine_fast | yes (since 2026-05-08) | **163** | 2026-05-31 02:54Z |
| battleground_luxalgo | display-blocked toxic-pair only | 127 | 2026-05-30 21:45Z |
| luxalgo_filters | not blocked | 156 | 2026-05-31 03:41Z |

**The blocklist is enforced at the Smart-Picks display / pf_registry filter layer (`tools/build_pf_registry.py::_load_policy_excluded()` line 222) — NOT at the emitter / outcome resolver / DB write layer.** Strategies on the blocklist continue creating DB rows, polluting the raw class PF that money-ready verifies against.

## Bottleneck #2: resolver mislabel (TP_HIT not promoted to WON)

`ml_crypto_predictor` 90d direction=LONG:
- WON: 0, LOST: 140, **TP_HIT: 147** (avg pnl +7.17%), SL_HIT: 0, TIME_EXIT: 1.

The outcome resolver is writing `TP_HIT` as a terminal status without re-labeling to `WON` — so 147 winning closes for this single strategy are invisible to every aggregate that filters `status IN ('WON','LOST')`. If those 147 TP_HITs were properly labeled WON, ml_crypto_predictor LONG 90d would jump from 0% WR to ~51% WR, PF~3-4. This is the same resolver-bug bucket Phase 4 (PRs #180-#181) opened but did not fully close for CRYPTO.

Same shape applies to `ml_strategy_reviver` (12 TP_HIT, 5 SL_HIT, only 2 WON / 2 LOST in 90d). Aggregates report PF 0.00 — actual edge unknown until re-labeled.

**This is also why CRYPTO 78.9% Smart-Picks (display layer) clashes with 15% raw-DB WR — the display layer is reading TP_HIT as a win; the verdict layer is not.**

## Actions ranked by impact

1. **INCIDENT — wire BLOCKED_SOURCE_STRATEGY_PAIRS into emission, not just display** (THE single highest-leverage fix for CRYPTO).
   - Files: every emitter that writes `source_system='ml_crypto_predictor'` / `'alpha_engine_fast'` to `trading_picks`. Candidates: `alpha_engine/ml_crypto_predictor*.py`, `alpha_engine/alpha_engine_fast*.py`, `tools/pick_pipeline.py`, plus any cron in `.github/workflows/` that triggers them.
   - Add a pre-insert guard: `from audit_trail.quality_gates import _BLOCKED_SOURCE_STRATEGY_PAIRS; if (asset_class, source_system) in _BLOCKED_SOURCE_STRATEGY_PAIRS_PAIRSET or matches direction-tuple form: return` before the INSERT.
   - Expected impact: stops bleed of ~370 picks/week from these two sources on CRYPTO. Class PF projects 0.18 → ~0.55 immediately on next 90d window.
   - Sized PR: 1 commit, ≤4 files.

2. **RESOLVER — promote `TP_HIT` → `WON` and `SL_HIT` → `LOST` in aggregates AND backfill 90d**.
   - Files: `alpha_engine/outcome_resolver.py` (the file CLAUDE.md cites at lines 115-126 for `PNL_WIN_THRESHOLD_BY_CLASS`).
   - Either (a) finalize statuses at resolve time (UPDATE TP_HIT→WON when pnl_pct>0), or (b) widen every verdict query to `status IN ('WON','LOST','TP_HIT','SL_HIT','EXPIRED','TIME_EXIT')` with pnl-sign WR logic.
   - Backfill: one-shot `UPDATE trading_picks SET status='WON' WHERE status='TP_HIT' AND pnl_pct>0 AND category='CRYPTO'` — affects 147 ml_crypto_predictor + 12 ml_strategy_reviver + smaller buckets.
   - Expected impact: ml_crypto_predictor LONG 90d goes from 0% WR / PF 0.00 to ~51% WR / PF~3 — which then **strengthens** the case it's NOT a kill candidate (only LONG was killed Apr 4, possibly prematurely). This re-opens a mutate-before-kill window per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`.

3. **KILL/MUTATE — `alpha_engine` (meta-engine) on CRYPTO**.
   - 90d: n=200, WR 9.5%, PF 0.03, avg pnl -14.99%. Largest absolute drag (n*|avg_pnl| ~ 3000).
   - Per CLAUDE.md "Concentration = strategy not engine": measure HHI on alpha_engine sub-strategies (`strategy` column) before killing the meta. If HHI > 0.30 on one sub, blocklist the sub-pair, not the engine.
   - Add `_BLOCKED_SOURCE_STRATEGY_PAIRS` row `("CRYPTO", "alpha_engine", <top_substrategy>)` after the HHI check.
   - File: `audit_trail/quality_gates.py` line ~2715-2720 block.

4. **KILL — `battleground` CRYPTO (avg pnl -49.27%) and `mercury2` CRYPTO (-24.89%)** if not already in pair-blocklist for CRYPTO.
   - `mercury2_fast` is blocked CRYPTO (line 2752) but plain `mercury2` is not — close that loophole.
   - Add: `("CRYPTO", "mercury2")`, `("CRYPTO", "battleground")` to `_BLOCKED_SOURCE_STRATEGY_PAIRS`.

5. **WATCHLIST — protect emission cadence for `ml_strategy_reviver_inverse`** (only PF>1 strategy, n=3, 199 ACTIVE).
   - Do not subject inverse-revival to the standard kill rules until n>=30. Add note in `alpha_engine/inverse_strategies.py`.

6. **ADD — pre-register a CRYPTO Phase-3-style MC harness candidate** since CRYPTO has none on the watchlist. Per `docs/AGENT_QUICKSTART_AUDIT_AND_STRATEGIES.md` and rule M-107, register in `reports/hypothesis_registry.json` first.
   - Candidate: `crypto_funding_rate_mean_reversion` (file `alpha_engine/crypto_options_vol.py` and adjacent already wire funding data — leverage that). Pre-register hypothesis: "Crypto perp funding > 2σ from 30d mean predicts mean-revert in next 4h."

## What I would ship next (concrete PRs)

### PR #A — `fix(emit): wire BLOCKED_SOURCE_STRATEGY_PAIRS into emitter guards (CRYPTO P0)`
- Scope: add pre-insert pair check in the 2-4 emitter callsites that produce `ml_crypto_predictor` LONG CRYPTO and `alpha_engine_fast` CRYPTO rows. Add a sentinel test under `alpha_engine/tests/test_emit_blocklist_guard.py`.
- Acceptance: 0 new CRYPTO rows with `(category, source_system) IN _BLOCKED_SOURCE_STRATEGY_PAIRS` after merge. Verify with a 24h DB query.
- Estimated CRYPTO PF lift on next 90d window: 0.18 → 0.55.

### PR #B — `fix(resolver): promote TP_HIT/SL_HIT to WON/LOST + backfill CRYPTO 90d`
- Scope: change `alpha_engine/outcome_resolver.py` to write terminal WON/LOST (not TP_HIT/SL_HIT). One-shot SQL backfill ships as `tools/backfill_tphit_to_won.py` with dry-run flag and category filter.
- Acceptance: count(status='TP_HIT') drops to 0 in CRYPTO. ml_crypto_predictor LONG 90d WR reports >40%.
- Side effect: this MAY surface `ml_crypto_predictor LONG` CRYPTO as a real edge (PF>1.5 at n>=100 if 147 TP_HITs were genuine). If confirmed, file a follow-up to **unblock** ml_crypto_predictor LONG CRYPTO (reverse the 2026-04-04 kill).

## Risk factors / blockers

- **Resolver-bug (Phase 4 finding) affects CRYPTO heavily**: 147 TP_HIT + 12 TP_HIT (reviver) + 3 TP_HIT (inverse) = 162 closes mislabeled, 18% of the 892-closure 90d sample. This single bug masks any real edge in the ml_* strategies and inflates the apparent class drag.
- **Category mis-tagging**: spot-checked `LOWER(category)='crypto'` — clean, no plural/mismatch in this class (unlike equity/stocks↔stock).
- **Stale stats**: latest `pf_registry` snapshot is 2026-05-17; live DB queries above are 2026-05-31 — 14 days of drift. Per `feedback-money-ready-2026-05-31` index entry, the bottleneck is plumbing not strategies — this analysis confirms it for CRYPTO.
- **3,284 ACTIVE backlog**: dominated by `ml_crypto_predictor` (1,457) and `ml_strategy_reviver` (424). When these resolve they will retroactively rewrite the class PF. Recommend NOT shipping any concentration-changing kill until that backlog drains another 14d.
- **HHI not yet measured** at sub-strategy granularity for alpha_engine — required before kill per CLAUDE.md concentration rule.

## One-line summary
CRYPTO PF=0.18 / WR=15.1% (n=892, 90d closed). **Two blocked strategies are still emitting (370 picks/week) AND the resolver is mislabeling 162 TP_HITs as non-wins — fix those two plumbing bugs first; do not retire more strategies until the backlog drains.**
