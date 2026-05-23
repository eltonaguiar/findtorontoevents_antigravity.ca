# Action-Items Verification Deep-Dive (2026-05-15)

Independent verification of `reports/asset_class_action_items_2026-05-15.md`.
Every claim was re-checked against **primary sources only** — live code and
`audit_dashboard/data/dashboard_data.json` — by three subagents explicitly
forbidden from citing the plan docs as evidence, plus direct main-thread
analysis. Method counters the multi-AI convergence trap: the original 4
analysts partly propagated numbers from the same 90-day plan docs.

## Methodology (so this is checkable, not trust-me)

1. **Adversarial framing.** Each of the 7 asset-class claims + the keystone
   claim was handed to an independent subagent as *guilty until verified*.
   Agents were explicitly **forbidden from citing the 90-day plan docs or
   autopsy reports** — those are the artifacts under suspicion. Only live code
   and `audit_dashboard/data/dashboard_data.json` count as evidence.
2. **Three parallel verifiers**, non-overlapping claim sets, so no agent could
   anchor on another's conclusion (counters the convergence trap that produced
   the original errors — see `feedback_multi_ai_convergence_trap`).
3. **Main-thread reproduction.** The keystone "unreproducible" claim was
   settled by *running code*, not reading docs — see Evidence below.
4. **Every row in the scorecard cites a `file:line` or a JSON path** that a
   reader can open and check. No claim rests on a plan doc.

## Evidence — empirical reproducibility proof

Script: `tools/_verify_n_reproducible.py` (committed). It imports the **real**
filter functions from `audit_trail/dashboard_generator.py` — `is_corrupted_outcome_row`,
`_is_valid_resolved_pick`, the win/loss tally — and does NOT run `main()` (no
HTML written). It runs the resolved-pick count over a fixed snapshot of
`picks.recent_closed` (3,500 picks) three times:

```
run 1: sha256=2553033cea8c4de7
run 2: sha256=2553033cea8c4de7
run 3: sha256=2553033cea8c4de7
DETERMINISM: PASS — all 3 runs identical
```

Then it prints the two distinct n-metrics straight from `dashboard_data.json`:

```
class         raw closed   resolved n    health.n
BOND                  13           11           11
COMMODITY            513          326          326
CRYPTO             26375         8108         8108
EQUITY              1054          423          423
ETF                  120          108          108
FOREX               1099          347          347
FUTURES                4            0            0
```

`resolved n == health.n` for **every class** — the verdict metric is exact.
`raw closed` is a *different, larger* number (it includes corrupted rows,
blocked-strategy history, pip/percent-confused rows, and `pnl==0` rows that
`_is_valid_resolved_pick` strips). When a report says "FOREX n drifts
148/342/1033/1169" it is quoting raw `closed` from different snapshots/tools —
not an unstable verdict metric. **Re-run the script any time: identical hash.**

## Verdict on the keystone claim

**"Every verdict on /audit is currently unreproducible" — REFUTED.**

`compute_asset_class_health` (`dashboard_generator.py:5392`) computes
`n = wins + losses` from `ac_breakdown`. `ac_breakdown` is built by a single
deterministic pass over `active + closed` (`:14002-14041`) with fixed,
pure-function filters: `is_corrupted_outcome_row`, then `_is_valid_resolved_pick`
(`:4606` — pure, no I/O, no randomness, no time dependence), then
`pnl>0`→win / `pnl<0`→loss. **Given a fixed input ledger, `n` is fully
determined.** Same ledger → same verdict.

What is actually true: **multiple `n`-metrics coexist** — raw `closed` count,
verdict-grade `resolved_n` (= `wins+losses` post-filter), and the pre-resolver-fix
`by_asset_class` raw counts — and reports/tools cite them interchangeably. That
is a **citation-discipline** problem, not non-determinism. The "n drifts
148/342/1033/1169" figure in the FOREX plan is different *metrics*, not an
unstable *metric*.

Corrected priority #1: not "pin the resolved-pick definition because verdicts
are unreproducible" — but **"name the canonical metric `resolved_n` everywhere
and stop reports citing raw `closed` as if it were the verdict `n`."**

## Per-claim verification scorecard

| Claim | Verdict | Evidence |
|---|---|---|
| COMMODITY PF 2.37 / WR 60.7 / n=326 | ✅ VERIFIED | `asset_class_health.COMMODITY` exact |
| CT=F = 73% COMMODITY PnL mass | ✅ VERIFIED | `asset_class_concentration.COMMODITY.top_share_pct=73.71` |
| cot_positioning fires weekly signal ~20×, no dedup | ⚠️ REFUTED (current) | `cot_positioning.py:47-93` has a per-release dedup ledger (PR #994, 2026-05-14). **But** the over-emission was real pre-patch — n=326 carries inflated history |
| ETF PF 1.33 (fell from plan's 1.48) | ✅ VERIFIED | `asset_class_health.ETF` PF=1.33 |
| ETF sector emitter is "opt-in" | ❌ REFUTED | `etf_sector_emitter.py:98` env defaults `"1"` — **default-ON** |
| ETF emitter produced 0 picks 2026-05-15 | ✅ VERIFIED | `etf_sector_picks.json: picks:[]` |
| quan_engine capped to 5% CRYPTO | ⚠️ DESYNCED | code `per_source_volume_cap.py:25`=5%; `quarantine_manifest.json:29`=12%; tests assert 12%. Enforced=5% |
| luxalgo_filters uncapped | ✅ VERIFIED | absent from `PER_SOURCE_VOLUME_CAP` |
| luxalgo "PF ~1.0, ~23% volume" | ⚠️ OVERSTATED | real: PF **1.12**, WR 44.3%, 1421 resolved ≈ **17.5%** of CRYPTO n |
| enforce_cap() one caller, scanner bypasses | ✅ VERIFIED | only `smart_picks_engine.py:2139`; zero refs in `production_scanner.py` |
| BOND PF 0.66 / WR 54.5 / n=11 | ✅ VERIFIED | `asset_class_health.BOND` exact |
| FOOLPROOF claims BOND "PF 1.72, meets T2" | ✅ VERIFIED (doc says it) | `FOOLPROOF:202` — but `FOOLPROOF:18` says PF 0.66 — **self-contradiction** |
| BOND n inflated by legacy ZN=F mis-tags | ⚠️ UNVERIFIABLE | no BOND+`=F` rows present now; `dashboard_generator.py:3338` shows ZN=F→FUTURES routing already fixed |
| BOND_ELITE_FLOOR default 40 | ✅ VERIFIED | `bond-agent.yml:53,77` |
| 4 futures strategies coded + wired | ✅ VERIFIED | `futures_strategies.py:74,169,265,358` → `non_crypto_agent/main.py:388-391` |
| FOOLPROOF says FUTURES "no strategies" | ✅ VERIFIED (doc says it, doc is wrong) | `FOOLPROOF:19` — `FOOLPROOF:204` contradicts with "n=2 Donchian" |
| =F routes mostly to COMMODITY, starves FUTURES tile | ✅ VERIFIED | `dashboard_generator.py:3168-3350` routing rule |
| MEMECOIN gate is strategy-pair-only | ✅ VERIFIED | `quality_gates.py:1933-1974` — all `("MEMECOIN",strategy)` 2-tuples, exact-match, no wildcard |
| PENNY_STOCK class-wide gate | ❌ WORSE | `PENNY_STOCK` does not appear in `quality_gates.py` at all — **zero gating** |
| penny emitters live | ✅ VERIFIED | `penny_volume_breakout` (`equity_strategies.py:160`) called `non_crypto_agent/main.py:359` |
| kill_gate.py is an orphan | ❌ REFUTED | 3 callers: `commodity_kill_switch.py`, `fx_kill_switch.py`, `policy_backtest.py` |

## Corrections to the action-items report

1. **Headline downgrade** — verdicts ARE reproducible. Reframe priority #1 as a
   metric-naming/citation fix, not a reproducibility crisis.
2. **COMMODITY headline is itself suspect** — PF 2.37 / n=326 carries
   pre-2026-05-14 COT over-emission (dedup only landed PR #994). The honest
   read: re-derive COMMODITY PF on post-patch picks before any Tier-1 claim.
   This is *stronger* than the original report — the flagship number may not
   survive clean re-aggregation.
3. **ETF emitter is a silent failure, not an opt-in** — it is default-ON and
   produces 0. Action: debug the emitter (why 0 picks), not "enable it."
4. **quan_engine cap is config-drifted** — 5% (code) vs 12% (manifest + tests).
   Pin one value; fix the desync. New action item.
5. **luxalgo_filters numbers corrected** — PF 1.12 (marginally profitable but
   dilutive vs class PF 1.29), ~17.5% volume share. Still worth a cap, but it
   is not the "PF ~1.0 / 23%" villain the original framing implied.
6. **PENNY_STOCK is completely ungated** — worse than "leaky pair-blocks". A
   class-wide gate must cover `PENNY_STOCK`, which appears nowhere in
   `quality_gates.py`.
7. **`FOOLPROOF_ACTION_PLAN.md` is internally self-contradictory** (BOND
   line 18 vs 202; FUTURES line 19 vs 204) — not merely stale. It should be
   regenerated from live `asset_class_health` or retired.

## Confidence-ranked action stack (post-verification)

**High confidence (verified, deterministic fix):**
1. Regenerate `FOOLPROOF_ACTION_PLAN.md` from live `asset_class_health` — it
   contradicts itself and the 8 newer plans.
2. Re-derive COMMODITY PF/WR on post-PR-#994 (dedup) picks before any Tier-1
   claim — the flagship 2.37 may be over-emission inflated.
3. Add a class-wide `PENNY_STOCK` + `MEMECOIN` gate — `PENNY_STOCK` is entirely
   ungated today.
4. Fix the quan_engine cap desync (code 5% vs manifest/tests 12%).
5. Standardize on `resolved_n` as the cited verdict metric; stop reports using
   raw `closed`.

**Medium confidence (verified state, fix needs design):**
6. Debug the ETF sector emitter's 0-pick output (it is on, just silent).
7. Cap `luxalgo_filters` + give `enforce_cap()` a `production_scanner.py` caller.
8. Wire the EQUITY VIX-regime gate (branch exists; perf lift claim is from a
   research doc — backtest-verify before merge).
9. Fix FUTURES `=F` classification + `conf_floor` so the tile accrues honest n.

**Unchanged from original:** FOREX directional gate, BOND elite-floor unblock,
`kill_gate` into `passes_active_gate`, `FRED_API_KEY`.

_Verification method: 3 independent subagents on primary code/JSON + main-thread
analysis of `dashboard_generator.py`. Counters the convergence trap in the
original 4-analyst pass. 2026-05-15._
