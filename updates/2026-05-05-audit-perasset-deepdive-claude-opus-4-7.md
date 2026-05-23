# /audit Per-Asset-Class Deep Dive

**Agent:** claude-opus-4-7 (Claude Code, 1M context)
**Timestamp:** 2026-05-05T00:55Z
**Method:** brainstorm-then-review swarm (6 brainstormers + 2 reviewers from earlier session) + live `dashboard_data.json` snapshot + grep-verified repo state.

## Live `asset_class_health` snapshot (from `audit_dashboard/data/dashboard_data.json`)

| Class    |    n  | WR%  | Total PnL%  |  PF  | Status            | Sized? |
|----------|------:|-----:|-----------:|-----:|-------------------|:------:|
| EQUITY   |   428 | 52.8 |    +276.23 | 1.42 | stable            |   ✅   |
| CRYPTO   | 8 166 | 44.8 |   +2 198.61| 1.26 | watch             |   ✅   |
| COMMODITY|   816 | 48.7 |    +285.05 | 2.08 | stable            |   ✅   |
| FOREX    | 1 249 | 45.6 |    -986.16 | 0.28 | stressed          |   ❌   |
| ETF      |    88 | 53.4 |     +19.79 | 1.20 | candidate         |   ❌   |
| BOND     |    18 | 55.6 |      +3.41 | 1.72 | thin_sample       |   ❌   |
| FUTURES  |     2 |100.0 |      +0.00 | null | insufficient_data |   ❌   |
| UNKNOWN  |     5 | 60.0 |      +0.18 | 4.59 | insufficient_data |   ❌   |

Charter floors: T1 PF>2 / WR>55 / MDD<10; T2 PF>1.5 / WR>50 / MDD<20.

## Refuted claims (do NOT repeat)

These were checked against repo state earlier this session:
- "60/60 active picks have null take_profit" — REFUTED (`picks.active` shows 0/58 null).
- "hyro_quan_bridge.json truncated to BTCUSDT only" — REFUTED (file 4118 bytes, full symbols dict).
- "R:R [1.5,2.0] is the golden zone, PF 5.81" — REFUTED. `quality_gates.py:2492-2511` documents 1868-pick analysis: R:R 1.0-1.5 = 70.8% WR (best), 1.5-2.0 = 45.6%, 2.0-3.0 = 42.4%. R:R is INVERTED — tight wins.
- "kimi_riseoftheclaw is non-crypto-score-exempt" — REFUTED. Pruned 2026-05-04 per 7d forward (n=45 WR 42.2% PF 0.98). Tests now pin the prune (PR #804).

---

## FOREX — biggest drag, mutate-before-kill

**n=1249, PF 0.28, WR 45.6%, -986% PnL.** Largest portfolio drain.

### Verdict
**MUTATE-BEFORE-KILL** per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`. Do not silently kill (CLAUDE.md hard rule).

### Top-3 actions
1. **Symbol filter:** drop FOREX symbols where 30d PF < 0.5. Use existing per-symbol mutation registry. Confirmed kept: USDJPY=X (panel evidence n=64 PF 9.50; PR #800 reverted the kill); next candidates to check: EURUSD=X, GBPUSD=X, AUDUSD=X via fresh closed-pick PF query.
2. **Direction lock:** the panel pattern from `quality_gates.py::JPY_CROSS_PAIRS` (CADJPY/EURJPY/NZDJPY/GBPJPY/AUDJPY BUY-blocked) is the prototype. Apply same SHORT-only lock to other majors that pass mutation analysis with WR(SHORT)>WR(LONG)+10pp.
3. **COT/CT-only filter:** existing `cftc_cot_commercial_signal_CT_locked` mutation in `alpha_engine/strategy_mutations.py` (added earlier session) is the template. Audit which other strategies should be CT-locked vs killed.

### Stale/missing dashboard data risk
- Per-symbol PF breakdown for FOREX not exposed on `/audit`. `asset_class_health` only shows class aggregate.
- Pre-fix vs post-fix resolver delta (resolver v2.1 lifted FOREX from "0% WR artifact" to current numbers) not surfaced.

### What lifts PF/WR ≥10% in 30d
PF 0.28 → ~0.65-0.70 by dropping the bottom-quartile symbols. Realistically still sub-T2 — FOREX needs structural change (CT signals, kill-switch on bad regimes) not just symbol filtering.

### Risk of silent kill
Class has 1249 closed picks; sudden silence would lose forward-WR signal for the mutation-recovery framework. Stay loud, mutate visibly.

---

## CRYPTO — mediocre aggregate, large sample, volume drag

**n=8166, PF 1.26, WR 44.8%, +2199% PnL.** Aggregate hides huge dispersion.

### Verdict
**MUTATE — cap volume drag, don't kill.** Multiple elite strategies (mega_mutation 88% WR, st_fear_greed_contrarian 78% WR) live in this bucket.

### Top-3 actions
1. **Cap `quan_engine` volume share:** documented as ~18% of CRYPTO volume at PF 0.70. Cap to 12% via mutation registry until forward-WR recovers.
2. **Block `unknown` source:** ~7% volume at PF 0.35. Add `unknown` to `strategy_blocklist.py` (or its CRYPTO-specific equivalent) — these are likely orphaned/pre-class-resolver picks dragging aggregate.
3. **Volume-weighted PF in dashboard:** currently aggregate PF is unweighted across strategies. Surface volume-weighted PF as the primary tier metric so concentration in elite vs drag strategies is visible.

### Stale/missing dashboard data risk
- Per-strategy WR/PF breakdown for CRYPTO not on `/audit` summary row. The dispersion (88% mega_mutation vs 0.35 unknown PF) is invisible.
- Capped vs raw PnL caveat (similar to EQUITY) for outlier-driven CRYPTO PnL.

### What lifts PF/WR ≥10% in 30d
Cap quan_engine 18%→12% + block unknown: aggregate PF estimated 1.26 → ~1.50, WR 44.8% → ~48%. Brings class closer to T2.

### Risk of silent kill
Largest contributor by volume (n=8166). Wholesale cull would zero the +2199% PnL. Mutation-only.

---

## EQUITY — viable, surface the capped-vs-raw caveat

**n=428, PF 1.42, WR 52.8%, +276% PnL.** Sized-up worthy but with a known PnL-cap caveat.

### Verdict
**KEEP SIZED, surface caveat.**

### Top-3 actions
1. **Capped vs raw PnL footnote:** session notes flagged `system_clean_metrics` raw 363.32 vs capped 35.71 for EQUITY (10× outlier-driven gap). Surface this directly in the asset-class summary row tooltip.
2. **Symbol bottom-quartile drop:** PF 1.42 has room to grow. Pull per-symbol PF for EQUITY and drop bottom 12% (PF<0.9 typically).
3. **High Conviction is the primary surface for EQUITY:** PF 4.05 in HC pass after 2026-04-30 score-floor 55→45 lower. Confirm HC still picking from EQUITY post-#804 kimi-prune (kimi was an EQUITY contributor pre-prune).

### Stale/missing dashboard data risk
- 10× capped-vs-raw gap is the headline; not surfaced.

---

## COMMODITY — sized-up worthy, push WR

**n=816, PF 2.08, WR 48.7%, +285% PnL.** PF above T2 floor; WR is the lift target.

### Verdict
**KEEP SIZED, push WR through filters.**

### Top-3 actions
1. **KC=F concentration cap:** session notes flagged KC=F at ~147% of COMMODITY PnL (single-symbol concentration risk). Add per-symbol concentration cap.
2. **Whitelist `cot_positioning_CT_locked` and `cftc_cot_commercial_signal_CT_locked`** (already in mutation registry per earlier session): CT=F LONG 89.8% WR n=49 PF 13.10; 87.5% WR n=40 — feed these into COMMODITY allocation.
3. **Seasonality filter for energy:** CL=F/NG=F have known calendar effects; add a seasonality gate to suppress entries in low-edge months.

### Stale/missing dashboard data risk
- Per-symbol concentration not visible on `/audit`. KC=F dominance is hidden.

---

## ETF — candidate, expand sample

**n=88, PF 1.20, WR 53.4%, +19.79% PnL.** Borderline T2; n<100 floor blocks sizing.

### Verdict
**HOLD; collect to n>=120, then re-evaluate.**

### Top-3 actions
1. **Expand universe:** add mid-cap ETFs (XLF, XLE, XLK, etc.) to lift sample size faster.
2. **Block leveraged ETFs:** SQQQ/TQQQ/SOXL-class typically drag WR.
3. **Theme-diversification cap:** prevent any single-sector ETF theme from exceeding 20% of ETF allocation.

### Stale/missing dashboard data risk
- Sample-tier transition (candidate → stable at n=100) not visualized as a progress bar. Currently binary in dashboard.

---

## BOND — thin_sample, expand

**n=18, PF 1.72, WR 55.6%, +3.41% PnL.** Already meets T2 PF+WR but n way below floor.

### Verdict
**EXPAND, do not kill.** Charter rule: thin_sample → expand, not kill.

### Top-3 actions
1. **Pull broader sovereign + corporate universe** (TLT, IEF, SHY, LQD, HYG, agency MBS).
2. **Add duration filter** (`DURATION_MAX=7`).
3. **Whitelist `carry_v1`** if currently blocked.

### Stale/missing dashboard data risk
- n=18 is so small that PF 1.72 is effectively noise. Wilson lower bound on WR not surfaced.

---

## FUTURES — defer

**n=2.** Effectively no data.

### Verdict
**DO NOT KILL, do not size.** Triple-screen rebuild from scratch when universe expands.

### Action
Add CME calendar spreads via `scripts/pull_futures_data.py`. Until n>=30, keep insufficient_data status; prevent any kill-switch logic from acting on this class.

---

## UNKNOWN — reclassify, then disappear

**n=5.** PF 4.59 is a statistical artifact.

### Verdict
**RECLASSIFY** — these are picks that escaped `enrich_pick_with_asset_class` at save-time. Backfill via `symbol_type_lookup.csv`.

### Action
Re-run `enrich_pick_with_asset_class` over the closed-picks corpus to drain UNKNOWN to 0. PR #790 already did 4162→0 backfill earlier; this is a new accumulation that needs another pass.

---

## Cross-asset top-5 levers (highest impact / lowest blast radius)

| # | Lever | Class | Impact estimate | Code site |
|---|---|---|---|---|
| 1 | Cap quan_engine 18%→12% | CRYPTO | PF +0.20 | mutation registry / per-strategy volume cap |
| 2 | Block `unknown` source on CRYPTO | CRYPTO | PF +0.05, removes -0.35 PF drag | `strategy_blocklist.py` |
| 3 | Surface capped-vs-raw EQUITY PnL caveat | EQUITY | UX clarity (governance) | `audit_dashboard/template.html` |
| 4 | KC=F concentration cap | COMMODITY | risk hygiene | per-symbol cap config |
| 5 | FOREX bottom-quartile-PF symbol drop | FOREX | PF 0.28→~0.65 | per-symbol mutation filter |

## Failing strategies / mutation candidates (DNA mutation pool)

From session evidence + mutation registry inspection:
- **`myfxbook_retail_contrarian_short_only`** — already added (SHORT 46.2% n=13 vs LONG 10.5% n=86). Monitor 30d.
- **`forex_rsi2_mean_reversion_short_only`** — already added.
- **`cot_positioning_CT_locked` / `cftc_cot_commercial_signal_CT_locked`** — already added; verify wire-up in production scoring.
- **`ig_contrarian_sentiment_short_only`** — already added.

New candidates worth investigating:
- USDJPY=X SHORT-only mutation (n=53 WR 67.9% +0.08 PnL) — but only after a fresh n=64 vs n=98 panel reconciliation; PR #799 was reverted.
- KC=F LONG-only with concentration cap + seasonality.

## Verification + caveats (red-team)

- Numbers above are from a single point-in-time snapshot of `dashboard_data.json` at 2026-05-05T00:55Z. Re-pull before action.
- Per-symbol PF claims (e.g., "drop PF<0.5 FOREX symbols") not validated end-to-end against actual closed-pick CSVs in this report — consumer must run `tools/mutation_analysis.py` per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` before applying any kill/cap.
- Volume share figures for `quan_engine` and `unknown` (18% and 7%) come from earlier session swarm output; should be re-measured against the live closed-picks corpus before code change lands.
- The "10× capped vs raw EQUITY PnL gap" is from session memory; exact numbers (raw 363.32 vs capped 35.71) need confirmation against current `system_clean_metrics`.

## Process notes

This MD is a **planning/analysis document**, not an action artifact. No code changes accompany this commit. Any lever above must follow the established session protocol:
1. Reproduce the numbers via `tools/mutation_analysis.py` (FOREX/CRYPTO levers) or direct repo grep (EQUITY caveat).
2. If kill/cap proposed: write `reports/deep_dive_<class>_<date>.md` per CLAUDE.md mutate-before-kill rule.
3. Open a focused PR (one lever per PR), not a multi-lever bundle.
4. Cross-engine swarm review before merge.

## Related session work

- PR #800: revert USDJPY=X kill (Phase 2-C panel restored).
- PR #801: GHA resilience + lazy DecayTracker.
- PR #803: pandas/pyarrow/numpy in 2 workflows.
- PR #804: CI Tests regressions on main fixed (_float helper + kimi prune test alignment).
- PR #777, #772: rebased + swarm-reviewed; awaiting CI.
- PR #764: REQUEST_CHANGES (missing commits).
- PR #798: HOLD on env-provision (memecoin DB password migration).
