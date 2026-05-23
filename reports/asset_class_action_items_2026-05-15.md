# Asset-Class Action Items — Graphify Cross-Reference (2026-05-15)

Top action items per asset class, derived by querying the 200K-node Graphify
knowledge graph (whole-repo code + docs) and cross-referencing against the
**May-15-2026 master plans**: `reports/SUPREME_PLAN_90days.md`,
`FOOLPROOF_ACTION_PLAN.md`, and the eight `reports/asset_class_90day_plan_*_2026-05-15.md`
linked from `findtorontoevents.ca/updates/index.html`.

Live performance source: `audit_dashboard/data/dashboard_data.json::performance.asset_class_health`
(verdict-grade, post-noise-filter).

> **✅ VERIFIED 2026-05-15.** Every claim below was independently re-checked
> against primary code + JSON by 3 adversarial subagents (forbidden from citing
> plan docs) plus a main-thread reproduction. Corrections applied inline.
> Full method + evidence: `reports/asset_class_verification_2026-05-15.md`
> (incl. a deterministic-reproduction proof, `tools/_verify_n_reproducible.py`).

## Scoreboard vs the plans

| Class | Live PF / WR / n | Plan headline | Drift |
|---|---|---|---|
| COMMODITY | 2.37 / 60.7% / 326 | PF 2.49 (plan) · 4.03 (FOOLPROOF) | plans understate maturity — WR already clears Tier-1 floor |
| EQUITY | 1.56 / 51.8% / 423 | PF 1.57 / n=420 | accurate — no material drift |
| ETF | 1.33 / 57.4% / 108 | PF 1.48 / n=106 | **PF fell 0.15, further from T2** |
| CRYPTO | 1.29 / 46.1% / 8108 | "quan_engine 18% @ PF 0.70" | stale villain — quan_engine already capped to 5% |
| FOREX | 0.79 / 51.6% / 347 | PF 0.27 / n=1169 | massively stale — live is 3× better but still sub-floor |
| BOND | 0.66 / 54.5% / 11 | FOOLPROOF: PF 1.72 "meets T2" | **falsified** — legacy mis-tagged futures rows |
| FUTURES | none / 0 / 0 | FOOLPROOF: "no strategies" | **factually wrong** — 4 strategies coded + wired |
| PENNY/MEME | (folded into EQUITY/CRYPTO) | "class-wide block exists" | **wrong** — only leaky strategy-pair blocks |

## Cross-cutting findings (apply to multiple classes)

1. **`kill_gate.py` (M-055) is wired into the kill switches, NOT the active
   gate.** Callers: `commodity_kill_switch.py`, `fx_kill_switch.py`,
   `policy_backtest.py`. Gap: `quality_gates.passes_active_gate` does not
   consult it. Wire `evaluate_kill()` there so no strategy block fires below
   the per-class min-n floor.
2. **`n` is reproducible — but two metrics get conflated** (corrected
   2026-05-15). The verdict `n` (`asset_class_health.n` = `wins+losses`,
   post-`_is_valid_resolved_pick` filter) is a deterministic pure-function
   output — proven: 3 identical SHA256 runs (`tools/_verify_n_reproducible.py`).
   What drifts is reports citing raw `closed` (e.g. COMMODITY closed=513) as if
   it were the verdict `n` (326). Fix is naming discipline: cite `resolved_n`
   everywhere; stop quoting raw `closed`. Not a reproducibility crisis.
3. **`FOOLPROOF_ACTION_PLAN.md` is out of sync** with the eight 90-day plans —
   wrong on FUTURES ("no strategies"), BOND ("meets T2"), CRYPTO ("cap
   quan_engine" already done), ETF ("scanner wired" but emits 0). Reconcile or
   supersede it.
4. **`FRED_API_KEY` unset** (`SKIP_FRED=1`) blocks curve/macro data for BOND +
   EQUITY + COMMODITY at once — shared-infra P0, not a per-class task.

---

## COMMODITY — PF 2.37 / WR 60.7% / n=326 (pushing Tier-1)

WR 60.7% already clears the Tier-1 55% floor. The plans frame COMMODITY as
"not production-grade" — the real remaining gap is **MDD verification + de-concentration**, not edge.

> **⚠ Verified caveat (2026-05-15):** the headline PF 2.37 / n=326 is itself
> suspect. The `cot_positioning` dedup ledger only landed PR #994 (2026-05-14) —
> `n=326` carries pre-dedup COT over-emission. The COT pilot's own code comments
> record WR 90.1%→40% and n=101→5 once de-duplicated. **Re-derive COMMODITY
> PF/WR on post-PR-#994 picks before any Tier-1 / real-money claim.**

**Top action items**
1. Re-aggregate COT over-emission on historical reads — `cot_positioning::CT=F`
   still fires one weekly CFTC signal ~20×/cycle; headline PF carries inflated
   pre-2026-05-13 data. `dashboard_generator.py` lacks 1-per-(symbol, COT_date,
   direction) dedup on historical reads.
2. Tighten the COMMODITY concentration cap — `concentration_cap.py` is wired
   (`quality_gates.py:4851`) but CT=F still holds 73% PnL mass. Add hard
   per-symbol ≤30% / per-strategy ≤25%.
3. Wire `commodity_carry_momo_double_sort` — `audit_dashboard/data/commodity_carry_momo.json`
   (18 symbols, Miffre/Fuertes) has **zero code callers**. It is the natural
   diversifier off CT=F. New caller in `alpha_engine/scanner.py`.
4. Add a per-symbol futures liquidity/MDD gate in `quality_gates.py` — none
   exists; CT=F has no micro-contract. Prerequisite for real-money.

**Further enhancements (not in any plan):** MDD measured on independent COT
cycles (not hourly bars) inside `kill_gate.py`; DBMF/KMLM external-replication
CI benchmark (`tools/commodity_external_replication.py`).

## EQUITY — PF 1.56 / WR 51.8% / n=423 (locking Tier-2)

Live numbers confirm the plan baseline — plans correctly diagnose the levers.

**Top action items**
1. Merge the VIX-regime hard filter — branch `feat/equity-vix-regime-gate-sidecar-2026-05-13`
   is unmerged; `non_crypto_quality_gate.py` only does soft VIX confidence
   scaling. Research (`equity_vix_regime_breakthrough_20260513.md`): VIX<22 lifts
   PF to 4.55+. Single biggest consolidation lever.
2. Split the universe — `config.py:587 EQUITY_SYMBOLS` mixes 10 large-caps with
   8 pennies/memes (NIO/LCID/RIVN/GME/AMC). Add `LARGE_CAP_EQUITY_SYMBOLS` +
   `is_liquid_equity()`. Penny gap-risk is the WR drag.
3. Wire a PEAD strategy (M-009) — `equity_factor_model.py` has an earnings
   boost but no standalone post-earnings-drift strategy. New
   `alpha_engine/strategies/pead_equity.py`.
4. Wire an execution-cost/slippage model — PF 1.56 is gross; Tier-2 must hold
   net of 5-20bp friction (M-017/018 scaffolds unwired).

**Further enhancements:** reconcile the two VIX thresholds (hard-block VIX>40
vs momentum-skip VIX>22) in one place; FRED macro overlay via
`fred_macro_context.py`; per-class `ml_score≥55` hard gate (gatekeeper is 83%+
accurate but unused as a gate).

## ETF — PF 1.33 / WR 57.4% / n=108 (slipping from Tier-2)

PF fell 0.15 below the plan's 1.48 baseline — the "clear path to T2" framing is
now over-optimistic.

**Top action items**
1. Debug the ETF sector emitter's **zero-pick output** — corrected 2026-05-15:
   `tools/etf_sector_emitter.py:98` defaults `ETF_SECTOR_EMITTER_ENABLED="1"`
   (**already ON**, not opt-in). It ran 2026-05-15 and wrote
   `etf_sector_picks.json` with `picks:[]`. This is a silent failure — the fix
   is diagnosing why it emits nothing, not "enabling" it.
2. Enforce a VIX<25 gate on the ETF emit path — `vix_regime_gate.py` supports
   ETF but isn't default-on; backtest PF 2.05→3.22 with it.
3. Add a per-symbol concentration cap (<25%) — XLE is 20.55% share / 53.74% PnL.
4. Cap/prune `intermarket-flow-scout` if its ETF-slice PF < 1.4 — it dilutes the
   cleaner rotation edge.

**Further enhancements:** per-source ETF entry in `per_source_volume_cap.py`;
positive source bonus for `etf_sector_momentum`/`etf_dual_momentum` in
`quality_gates.py`; backtest a quarterly (vs monthly) rebalance to cut friction;
dashboard PF-reconciliation tile (rotation vs mixed).

## CRYPTO — PF 1.29 / WR 46.1% / n=8108 (volume-weighted dilution)

The plans chase a stale `quan_engine` villain — it is already capped to 5% and
fully blocked. The live drag has shifted.

**Top action items**
1. Cap `luxalgo_filters` CRYPTO volume share — `per_source_volume_cap.py:24-25`
   caps only `quan_engine`; `luxalgo_filters` is uncapped. **Verified live
   numbers (2026-05-15):** PF **1.12**, WR 44.3%, 1,421 resolved ≈ **17.5%** of
   CRYPTO `n` — marginally profitable but dilutive (below class PF 1.29). Add
   `{"luxalgo_filters": {"CRYPTO": 0.10}}`. _(Earlier "~23% vol / PF ~1.0" was
   overstated.)_ Also fix the `quan_engine` cap desync: `per_source_volume_cap.py`
   says 5%, `quarantine_manifest.json` + tests say 12% — pin one value.
2. Give `enforce_cap()` a second caller — it is INTAKE-only, called only from
   `smart_picks_engine.py`; picks via `production_scanner.py` bypass it. Wire it
   into `production_scanner.py`.
3. Pair-block remaining sub-PF-1.0 sources (`alpha_engine` generic PF 0.99,
   `copy_trader_highscore` 0.80, `battleground` 0.65, `regime_terminal` 0.95) in
   `quality_gates.py:1494 BLOCKED_SOURCE_SYSTEMS`.
4. Build a crypto liquidity/ADV gate — no `is_liquid_crypto()` exists; stop
   emission on ~179-symbol meme/alt noise.
5. Fix the `ml_crypto_pred` 95.3% resolver-exclusion in `forward_validator.py`
   (808/848 closed picks unresolved hides rot).

**Further enhancements:** LONG-only volume penalty for `luxalgo_confluence`
(35% WR LONG); replace per-source whack-a-mole with a class-level PF-weighted
volume budget in `quality_gates.py` (auto-starves any sub-1.0 source).

## FOREX — PF 0.79 / WR 51.6% / n=347 (sub-floor, mutate-before-kill)

Live PF is 3× the stale plan figure (0.27) but still losing. The fix is
mutation, not new volume — and it is a small PR, not a 90-day project.

**Top action items**
1. Wire a directional gate — autopsy (`forex_mutation_autopsy_20260515.md`):
   LONG = 29.4% WR / PF 0.80, SHORT = PF 8.11. `BLOCKED_ASSET_STRATEGY_TRIPLES`
   (`quality_gates.py:2045`) exists but has zero FOREX entries. Highest-leverage
   move; pure mutation.
2. Wire a `BLOCKED_SYMBOLS_BY_CLASS["FOREX"]` allowlist — autopsy KILLs
   NZDUSD=X/EURJPY=X/USDCHF=X, BOOSTs AUDUSD=X/AUDJPY=X; the symbol gate is
   unwired.
3. Replace the COT proxy — `cot_positioning_forex` (`forex_strategies.py:536`)
   is a price-zscore proxy, not real CFTC 6E/6B/6J data — disguised
   mean-reversion. Wire free CFTC legacy COT.
4. Enforce a <25% concentration cap — USDJPY=X is 36% PnL mass via
   `cta_fx_multifactor`.

**Further enhancements:** make n-reconciliation a P0 (FOREX `n` is
unreproducible); use MyFXBook/ZuluTrade retail sentiment as a *contrarian gate
input*, not just copy-replication; run a 4th mutation axis — time-of-day /
session (London-NY overlap vs Asia) — never tried for FOREX.

## BOND — PF 0.66 / WR 54.5% / n=11 (n is the blocker, not edge)

n=11 is the problem. FOOLPROOF's "PF 1.72, meets T2" is falsified — legacy
mis-tagged ZN=F futures rows that rolled off.

**Top action items**
1. Lower `BOND_ELITE_FLOOR` to 32-35 (`bond-agent.yml`) — the emitter produces
   ~10 raw signals/day but quality=0 because a crypto-calibrated elite floor of
   40 is unreachable for low-vol bond signals. This is the n=11 root cause.
2. Wire the 3 spec'd pilots (TIPS-breakeven MR, Cochrane-Piazzesi curve carry,
   HYG-LQD credit MR) from `bond_deep_dive_round2_2026-05-13.md` into
   `bond_strategies.py` — uses the unused IEF/SHY/TIP/LQD universe (~114
   events/yr → reaches n≥80).
3. Confirm BR-3 merge lands picks in `active_picks.json` (blocked upstream by #1).
4. Do NOT run `kill_gate` against BOND — n=11 < MIN_N=30 → it correctly returns
   INSUFFICIENT_EVIDENCE. There is nothing to kill, only an emitter to unblock.

**Further enhancements:** set `FRED_API_KEY` (shared-infra, unblocks 5 classes);
frozen-snapshot mechanism for reproducible BOND verdicts; wire Kalshi rate/macro
gating (`kalshi_signals.py`, no-key API) for duration timing.

## FUTURES — no data (alive but starved, NOT dead)

4 strategies (`futures_tsmom`, `futures_connors_rsi2`,
`futures_cross_asset_momentum`, `futures_vol_regime_breakout`) are coded in
`alpha_engine/futures_strategies.py` and wired into `non_crypto_agent/main.py`.
`FOOLPROOF`'s "no strategies, no scanner" is factually wrong.

**Top action items**
1. Decide merge-vs-retire formally — plans recommend merging into a unified
   tile; execute or formally retire. Do not leave a zombie tile.
2. Fix classification — `dashboard_generator.py:3168-3197` routes most `=F`
   roots to COMMODITY; only ES/NQ/ZN-type go to FUTURES, starving the tile. Add
   a `contract_type` tag.
3. Lower `conf_floor` from 0.50 → 0.40 for the 4 unvalidated strategies
   (`non_crypto_agent/main.py:431`) so signals reach shadow emission and accrue
   n — currently a self-fulfilling kill loop.

**Further enhancements:** non-empty-results assertion on the futures backtest
job (`new_strategies/futures_regime_report.json` is empty-bodied); rename the
unified tile `FUTURES_CTA` for honesty; per-gate rejection-reason telemetry in
`curate_quality_picks`.

## PENNY/MEME — folded into EQUITY/CRYPTO (leaky quarantine)

Not a separate `asset_class_health` key. `quality_gates.py:1933-1974` has a
MEMECOIN quarantine but it is **strategy-pair-only** (exact `(MEMECOIN,strategy)`
tuples, no wildcard) — there is NO class-wide gate, despite the 90-day plan
describing one as if it exists. **Verified worse (2026-05-15):** the string
`PENNY_STOCK` does not appear in `quality_gates.py` **at all** — penny stocks
have zero gating, not even leaky pair-blocks.

**Top action items**
1. Add a class-wide gate — `class in ("MEMECOIN","PENNY_STOCK") → fail` in
   `quality_gates.py` + `non_crypto_quality_gate.py`. Replaces the leaky pair list.
2. Add `is_low_quality_or_meme(symbol)` to `config.py` (mktcap<$2B / ADV<$5M),
   gated in `scanner.py`/`production_scanner.py` before emit.
3. Map `CATEGORY_RISK` "meme"/"penny" to BLOCK (`config.py:173`) — currently
   -15%SL/+35%TP amplifies losses.
4. Deprecate `penny_volume_breakout` + `community_penny_volume_surge` (return []).

**Further enhancements:** `n<20 → "noise"` pill on the dashboard symbol-perf
render (small-n meme winners display as 100% WR); remove penny/meme from
`ml_ranker.py:420 CATEGORY_MAP`; gap-risk circuit breaker (no overnight holds
for float<10M).

---

## Priority stack (ranked, cross-class)

1. **Standardize the cited verdict metric** — name it `resolved_n` everywhere;
   stop reports quoting raw `closed`. The metric is already deterministic; this
   is a citation-discipline fix, not a reproducibility fix.
2. **Merge the EQUITY VIX-regime gate** — biggest single PF lever, branch ready.
3. **Cap `luxalgo_filters` + second `enforce_cap()` caller** — CRYPTO's real drag.
4. **Lower `BOND_ELITE_FLOOR`** — one-line change that makes BOND solvable.
5. **Wire the FOREX directional gate** — small PR, structure already exists.
6. **Class-wide PENNY/MEME gate** — closes the biggest live leak.
7. **Fix FUTURES classification + `conf_floor`** — ends the self-fulfilling kill loop.
8. **COMMODITY COT re-aggregation + concentration cap** — makes the Tier-1 push real.
9. **Wire `kill_gate.evaluate_kill()` into `quality_gates.passes_active_gate`.**
10. **Set `FRED_API_KEY`** — unblocks macro data for 3 classes at once.

_Generated 2026-05-15 from the Graphify whole-repo knowledge graph + 4-agent
plan cross-reference. Source plans: SUPREME_PLAN_90days.md, FOOLPROOF_ACTION_PLAN.md,
asset_class_90day_plan_*_2026-05-15.md._
