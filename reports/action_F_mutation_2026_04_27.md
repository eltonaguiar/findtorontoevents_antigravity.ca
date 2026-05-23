# Workstream F — Strategy Mutation Investigation (COMMODITY 5 underperformers)

**Date:** 2026-04-27
**Author:** claude-opus-4-7 (Workstream F investigator)
**Scope:** investigation + writeup ONLY. No code or config touched. No PR opened.
**Canonical audit:** `reports/asset_class_independent_recompute_2026_04_27.md`
**Drilldown scripts:** `tools/_action_F_drilldown.js`, `tools/_action_F_extra.js` (read-only one-shots; safe to delete)

The COMMODITY class shows WR 42.60% / PF 0.896 / Sum PnL **-9.82%** on n=622 (`audit_trail/data/dashboard_payload.json` `picks.recent_closed`, generated_at `2026-04-27T22:08:21.106Z`). Five strategies (per `r.strategy` field — note Part 3 caveat in canonical audit, `strat_name` is UNKNOWN so labels are strategy names with source-system fallback) show WR <= 42.31% on n >= 5: `cot_positioning`, `cftc_cot_commercial_signal`, `cta_commodity_momentum_term`, `cta_cross_asset_tsmom`, `cta_golden_cross_200`. Per CLAUDE.md, `BLOCKED_SOURCE_SYSTEMS` cannot be expanded without first executing `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` + `docs/MUTATION_THREE_AXIS_PROTOCOL.md`.

This report executes that investigation against the protocol and produces a mutation-or-kill matrix.

## Methodology

1. Read protocol docs (`docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`, `docs/MUTATION_THREE_AXIS_PROTOCOL.md`) and the autopsy tool (`tools/mutation_analysis.py`).
2. Locate emitter file + parameter set + symbol universe + direction policy for each of the 5 strategies via `Grep` across `alpha_engine/`, `copy_trader_intel/`, `audit_trail/`.
3. Re-run the asset-class scorecard, restricted to COMMODITY rows whose `strategy` field matches the 5 names; for each, count noise-wins (`pnl_pct > 0 AND |pnl_pct| < 0.05`) and noise-losses (`pnl_pct <= 0 AND |pnl_pct| < 0.05`) — the resolver bug per `feedback_noncrypto_resolver_live_close_bug.md` flickers BOTH sides, not only wins.
4. Subtract noise rows to get a "clean" sample per strategy and report the residual WR/sumPnL.
5. Cross-reference with `audit_trail/quality_gates.py:BLOCKED_SOURCE_SYSTEMS` and `alpha_engine/hedge_fund_quality_gate.py` to see whether any of the 5 are already constrained somewhere.
6. Map the protocol's three axes onto each strategy and propose mutation candidates.

## Mutation-before-kill protocol summary

`docs/MUTATION_THREE_AXIS_PROTOCOL.md` formalizes a three-axis autopsy on the closed-pick ledger BEFORE expanding `BLOCKED_SOURCE_SYSTEMS`. The axes:

| # | Axis     | Slice | Mutation form |
|---|----------|-------|---------------|
| 1 | Symbol   | per (system, symbol) | `symbol_allowlist` / per-symbol block; ALLOW if WR >= ~55% on n>=10, BLOCK if WR < ~40% on n>=10 (or < 35% on n>=5) |
| 2 | Direction| per (strategy, LONG/SHORT) | `long_only` / `short_only` / inverse pipeline (`alpha_engine/strategy_mutator.py`, `dna_mutation_engine.py`) |
| 3 | Timeframe| per (strategy, TF bucket) | TF-gated picks (`scalp_only`, `swing_only`, …) |

Pass criterion (Step 5 — "mutation quality"): the winning subset must be **>= ~10% of the system's total closed trades** (avoids curve-fit on tiny pockets). Adjust with sample size and CI; combine with walk-forward / hold-out per `TESTING_PROTOCOL.MD` §7. The investigation doc adds an "exit-reason" axis (Kimi-CLI 2026-04-19 review feedback) and a deterministic-loss fast-path: `WR == 0% AND total_trades >= 20` is an immediate surgical block, no rehab — but none of our 5 underperformers individually has n >= 20 with WR=0 (largest is `cot_positioning` n=10 WR=0).

Hard-block fast-path (Step 3 of investigation doc): `WR < 0.35 AND avg_pnl_pct < -0.5 AND total_trades >= 10` → candidate for `BLOCKED_SOURCE_SYSTEMS`. **Even this fast-path requires Stages 2-4 of the escalation ladder unless the loss pattern is deterministic** (WR=0 on n>=20).

Concrete workflow (ranked, per protocol):
1. Export closed CSV → `python tools/mutation_analysis.py --json` (or `--csv closed_picks.csv`).
2. Document top splits in a short note.
3. Open a DNA ticket: parent strategy + mutation type (`symbol_allowlist`, `long_only`, …).
4. Implement gate behind `SANDBOX` tier, min 5-20 forward trades.
5. Hard block only after rehab fails.

## Per-strategy code map

| Strategy | Emitter file | Parameters | Symbol universe | Direction policy |
|---|---|---|---|---|
| `cot_positioning` | `copy_trader_intel/multi_asset_copytrader_scraper.py:1054-1165` (`scrape_cot_positioning`); separate forex-pair variant in `alpha_engine/cot_positioning.py:21-34` | Weekly RSI(14) on every-5th-close subsample (line 1105-1107); thresholds `< 30` LONG / `> 70` SHORT (1118-1124); seasonal bullish overlay (`COMMODITY_SEASONALS`, line 181); TP=2.0×ATR / SL=1.5×ATR (1139-1147); base conf 0.55, +0.10 if RSI < 25 or > 75, +0.05 if seasonal, cap 0.80 (1149-1154) | `FUTURES_SYMBOLS` filtered to `category=="commodity"`: GC=F, SI=F, CL=F, NG=F, HG=F, ZW=F, ZC=F, ZS=F, KC=F, SB=F, CT=F, PL=F (lines 145-162) | BOTH (LONG on RSI<30, SHORT on RSI>70). Wired in `alpha_engine/non_crypto_policy.py:201-209` with categories={forex, commodity, futures, bond, equity}, `min_confidence=0.55`, `min_forward_trades=20`, `min_forward_wr=0.35`. Boost 1.15× in `alpha_engine/production_scanner.py:325-327`. |
| `cftc_cot_commercial_signal` | `copy_trader_intel/multi_asset_copytrader_scraper.py:1645-1867` (`scrape_cftc_cot_weekly`) | Real CFTC Socrata API → commercial vs speculative pct positioning. LONG when `commercial_pct_long > 55 AND speculative_pct_short > 50`; SHORT when reverse (1712-1723). TP=2.0×ATR / SL=1.5×ATR (1727-1736). Conf = `0.60 + (commercial_pct/100)*0.2`, capped 0.82, +0.02 WoW (1738-1754). RSI proxy fallback if API down (1782-1865) — RSI(14) weekly < 25 LONG / > 75 SHORT. | `CFTC_CODES` (1606-1618): GC=F, SI=F, HG=F, CL=F, NG=F, ZC=F, ZW=F, ZS=F, KC=F, SB=F, CT=F (11 commodity contracts) | BOTH. Already gated in `alpha_engine/production_scanner.py:2519-2522` `BLOCKED_ASSET_SOURCE_PAIRS`: `("commodity", "cftc_cot_commercial_signal")` is on a watch comment but NOT actually inserted as an active block (the pair is commented "Insufficient data on commodity, not proven bad" — line 2520-2521). |
| `cta_commodity_momentum_term` | `copy_trader_intel/cta_strategy_replicator.py:630-764` (`commodity_momentum_term`); wrapped in `alpha_engine/cta_bridge.py:274-294` (`cta_commodity_momentum`). Strategy name `cta_commodity_momentum_term` is the suffixed wrapper variant — see comment "_term" suffix added when the wrapper retains the underlying replicator's strategy field via `_make_pick(strategy="commodity_momentum_term", …)` then prefixed by the bridge to `cta_commodity_momentum`. | 12-month return (`ret_252`) momentum rank + 12-month price-change as term-structure proxy (665-679). LONG top-3, SHORT bottom-3 by combined rank (692-706). TP=2.5×ATR / SL=2.0×ATR (714-720). Confidence = 0.70 - 0.1×rank_position for LONG (727-730). | `COMMODITY_SYMBOLS` from `cta_strategy_replicator.py:99` — 8 contracts: GC=F, SI=F, CL=F, NG=F, HG=F, ZC=F, ZW=F, ZS=F (no soft commodities — KC, SB, CT, PL, SB are absent here, unlike the COT variants) | BOTH (LONG top-3, SHORT bottom-3 by rank). Policy at `alpha_engine/non_crypto_policy.py:219-227` (`min_confidence=0.67`, `min_forward_trades=2`, `min_forward_wr=0.50`). **Already in `alpha_engine/hedge_fund_quality_gate.py:60-61` as `COMMODITY_BANNED_STRATEGIES = {"cta_commodity_momentum_term"}`** — but that file is opt-in/sidecar (line 1-19), not wired to production scanning. |
| `cta_cross_asset_tsmom` | `copy_trader_intel/cta_strategy_replicator.py:771-…` (`cross_asset_tsmom`); wrapped in `alpha_engine/cta_bridge.py:297-318`. | Cross-asset signals: bond returns predict equity, equity returns inversely predict bonds, commodity momentum predicts commodity (per docstring). 1/3/12-month time-series momentum on `CTA_UNIVERSE` (full 21-asset universe, line 54-80). | Whole `CTA_UNIVERSE`: equity, bond, commodity, forex (21 symbols). The COMMODITY-tagged emissions land on commodity contracts only when commodity assets surface from the cross-asset scoring. | BOTH. Confidence cap 0.65 via `_cta_conf_cap` (line 91-100 of `cta_bridge.py`). Probation policy unstated explicitly in `non_crypto_policy.py` (the entry exists for `cta_tsmom_blend` and `cta_commodity_momentum_term`; this strategy inherits a default policy or is unfiltered). |
| `cta_golden_cross_200` | `copy_trader_intel/cta_strategy_replicator.py:426-519` (`golden_cross_200`); wrapped in `alpha_engine/cta_bridge.py:227-247` (`cta_golden_cross`). | 50/200 SMA crossover + ADX(14) > 20 trending filter (467-469). LONG on golden cross + price > SMA200 (453-454). SHORT on death cross + price < SMA200 (455-456). TP=2.5×ATR / SL=1.5×ATR (475-481). Conf 0.70 fresh / 0.60 established (489). | `CTA_UNIVERSE` — 21 symbols across asset classes (54-80). Commodity emissions land only on the 8 commodity members. | BOTH. Boost 1.3× in `alpha_engine/production_scanner.py:325` (`cta_golden_cross_200`: 1.3 — comment "100% WR on 2 trades"). |

Notes:
- Three of the 5 strategies (`cot_positioning`, `cftc_cot_commercial_signal`, `cta_commodity_momentum_term`) have explicit policy / gate entries already; the two `cta_*_tsmom` and `cta_*_200` variants ride only on default policy + the strategy-name boost lookup.
- The `_term` and `_200` suffixed names that appear in `r.strategy` of `dashboard_payload.json` are the names actually persisted on each pick. The bridge sets `sig["strategy"]` to `cta_commodity_momentum`, `cta_cross_asset_tsmom`, `cta_golden_cross` (without the suffix) at lines 289, 314, 243 of `cta_bridge.py` — so the literal `cta_commodity_momentum_term`, `cta_golden_cross_200` strings observed in the closed ledger originate elsewhere (likely from copy_trader_intel which stores the underlying `commodity_momentum_term` / `golden_cross_200` and adds the `cta_` prefix at the multi-asset writer step). Investigation noted but not load-bearing for kill/mutate decisions.

## Per-strategy resolver-noise drilldown (COMMODITY only)

`tools/_action_F_drilldown.js` filters `audit_trail/data/dashboard_payload.json.picks.recent_closed` to `asset_class == "COMMODITY"` and groups by `r.strategy`. Noise threshold: `|pnl_pct| < 0.05` (matches Workstream B definition). "Clean" = absolute PnL >= 0.05% — the rows that aren't 1bp resolver flicker.

| Strategy | n | wins | losses | sumPnL% | noise wins | noise losses | total noise share | Clean n | Clean wins | Clean WR | Clean sumPnL% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `cot_positioning` | 10 | 0 | 10 | -9.36 | 0 | 7 | **70.0%** | 3 | 0 | **0.00%** | -9.18 |
| `cftc_cot_commercial_signal` | 9 | 1 | 8 | -12.15 | 0 | 5 | **55.6%** | 4 | 1 | **25.00%** | -11.97 |
| `cta_commodity_momentum_term` | 46 | 17 | 29 | -4.29 | 17 | 28 | **97.8%** | 1 | 0 | 0.00% | -4.22 |
| `cta_cross_asset_tsmom` | 32 | 13 | 19 | +1.90 | 12 | 18 | **93.8%** | 2 | 1 | 50.00% | +1.85 |
| `cta_golden_cross_200` | 26 | 11 | 15 | -0.02 | 11 | 15 | **100.0%** | 0 | 0 | n/a | 0.00 |

Verifiable computation: re-run `node tools/_action_F_drilldown.js` against the same payload (generated_at `2026-04-27T22:08:21.106Z`).

Reading: only **`cot_positioning`** and **`cftc_cot_commercial_signal`** have any meaningful clean signal. The three `cta_*` strategies are 94-100% noise — every closed pick except 1, 2, and 0 rows respectively is the resolver re-marking entry-price-equals-exit-price. Their sumPnL is statistical fog; the apparent 36-42% WR is meaningless because the wins are 1bp ticks.

Per-symbol clean breakdown (extra drilldown, `tools/_action_F_extra.js`):

| Strategy | Symbol | Direction | Clean n | Clean WR | Clean sumPnL% |
|---|---|---|---:|---:|---:|
| `cot_positioning` | KC=F | LONG | 2 | 0% | -5.91 |
| `cot_positioning` | CT=F | SHORT | 1 | 0% | -3.28 |
| `cftc_cot_commercial_signal` | CT=F | SHORT | 2 | 0% | -6.54 |
| `cftc_cot_commercial_signal` | KC=F | LONG | 1 | 100% | +0.07 |
| `cftc_cot_commercial_signal` | CL=F | SHORT | 1 | 0% | -5.49 |

Direction raw counts (all rows, pre-noise-filter):
- `cot_positioning`: 4 LONG / 6 SHORT
- `cftc_cot_commercial_signal`: 3 LONG / 6 SHORT
- `cta_commodity_momentum_term`: 46 LONG / 0 SHORT (all on SI=F: 45/46 + GC=F: 1/46) — single-symbol concentration, no SHORT half despite the algorithm being symmetric (Workstream C poison-pill territory).
- `cta_cross_asset_tsmom`: 2 LONG / 30 SHORT (predominantly GC=F SHORT: 24/32, then SI=F: 5)
- `cta_golden_cross_200`: 26 LONG / 0 SHORT (HG=F: 25/26 + ZC=F: 1/26)

## Mutation candidates per strategy

Per the three-axis protocol (symbol / direction / timeframe). Pass criterion in each row: a backtest WR > 50% AND PF > 1.2 on n >= 30 in the proposed subset, sustained for >= 5 SANDBOX forward trades before promotion (per `TESTING_PROTOCOL.MD §7`).

| Strategy | Inverse-direction mutation | Symbol-rotation mutation | Parameter mutation |
|---|---|---|---|
| `cot_positioning` | LONG=0/4 and SHORT=0/6 — both directions failing on this sample. Inverse won't help unless the closed-cohort is genuinely flat-mean and only TP/SL placement is wrong. SKIP for now (no clear "winner side"). | Both clean losses are KC=F LONG (-5.91%) and CT=F SHORT (-3.28%). Workstream C poison-pill audit also flagged CT=F (n=12 WR 8.3%) and KC=F (n=12 WR 8.3%) as commodity poison pills. **Block KC=F + CT=F, retain ZW=F/CL=F/GC=F** — this is the cheap, high-confidence mutation. Universe shrinks from 12 commodities to 10. | RSI thresholds 30/70 are textbook, low-info edit. Could try seasonal-only mode (require `has_seasonal == True`) — but n=10 is too small to sub-slice. SKIP at this n. |
| `cftc_cot_commercial_signal` | LONG 1/3 (33%) — the only winner is the +0.07% noise-flicker rounded to 100%; SHORT 0/6 (0%). Total clean sample n=4. Insufficient for an inverse-direction call. SKIP. | CT=F SHORT is the dominant cohort (n=5 raw, n=2 clean, both losses, -6.54%). Mirror-image to `cot_positioning`. **Block CT=F + KC=F**, keep CL=F (1 clean SHORT, also a -5.49% loss but n=1 too small to gate yet). | Confidence floor 0.55 → 0.70 (matches `COMMODITY_CONFIDENCE_MIN` from `hedge_fund_quality_gate.py:64`) drops the lowest-conf picks; fewer picks but on the conf-band-with-positive-PF slice. |
| `cta_commodity_momentum_term` | All 46 rows are LONG (algorithm currently emits LONG-only on the 2 surviving symbols SI=F+GC=F due to whatever the rank cohort has been since the window opened). The protocol's "if one direction is bad and the other is good" doesn't apply because we have no SHORT sample. Could DNA-mutate to `cta_commodity_momentum_term_inverse` and let it accumulate forward trades — but on near-zero clean signal there's nothing to invert against. SKIP. | 45/46 picks are SI=F. **The strategy is effectively a SI=F-only LONG bot in this window.** If that's not by design (the algorithm IS supposed to rotate among the 8 commodity contracts), this is a separate bug. **Symbol-rotation mutation is the SAME thing as fixing the rotation logic** — escalate to engineering, not gate. | TP=2.5×ATR / SL=2.0×ATR (R:R 1.25). Tighten SL to 1.5×ATR to match peer CTA strategies. But because clean-data n=1, no parameter tune is data-supported. |
| `cta_cross_asset_tsmom` | 2 LONG / 30 SHORT — the strategy is in a SHORT-bias regime currently. Of the 30 SHORTs, 12 are wins (40%) and 18 losses, but 28 of those 30 are noise-flicker. **Cannot decide on direction inverse from this data.** SKIP. | 24/32 picks GC=F SHORT, 5 SI=F. Same single-symbol concentration as `commodity_momentum_term`. Cross-asset TSMOM is supposed to operate across the 21-asset universe — if it's only emitting GC=F SHORT, the cross-asset rotation is broken. Same engineering escalation. | Lookback 1/3/12mo windows are textbook (Hurst-Ooi-Pedersen 2017). Param mutation low-value here. |
| `cta_golden_cross_200` | All 26 LONG. ADX > 20 + 50/200 SMA + price > SMA200. The strategy is structurally LONG-only when uptrending, SHORT-only when downtrending — current cohort is in an HG=F uptrend. Inverse mutation = "swap the threshold direction" makes no economic sense. SKIP. | 25/26 picks HG=F LONG. Single-symbol concentration. Same engineering issue as the other two `cta_*`. | SMA periods 50/200 are canonical. Could grid 50/100, 100/200, 200/300 — but needs walk-forward, and clean n=0 means no signal to grid against. |

Common pattern across the 3 `cta_*` strategies: **all three have collapsed to single-symbol cohorts in this window**, and **all three are entirely resolver-noise**. Nothing here is a candidate for the mutation protocol's symbol-rotation axis until the cross-asset rotation is verified to actually rotate.

## Mutation-or-kill matrix

"Real PnL after noise filter" uses Clean sumPnL%. "Recommended next step" is one of: `mutate-then-reassess`, `kill-now (data-supported)`, `wait-for-resolver-fix`, `wait-for-strat_name-fix`.

| Strategy | Real PnL after noise filter | Mutation candidates | Recommended next step |
|---|---:|---|---|
| `cot_positioning` | -9.18% on Clean n=3 (0/3 wins) | Symbol: block KC=F + CT=F (already poison-pill flagged Workstream C). Direction: both sides failing — no inverse signal. Param: hold | `mutate-then-reassess` — push the symbol-block mutation through SANDBOX with min_forward_trades=10 (matching protocol Step 4); revisit at n=20 forward trades or after Workstream B (resolver fix) ships. The 70% noise share means even -9.18% on n=3 is below stat-significance floor. |
| `cftc_cot_commercial_signal` | -11.97% on Clean n=4 (1/4 win = 25%) | Symbol: block CT=F + KC=F. Param: confidence floor 0.55→0.70 to align with `COMMODITY_CONFIDENCE_MIN` | `mutate-then-reassess` — symbol-block + confidence-floor, both behind SANDBOX. Already partially policy-gated; no `BLOCKED_SOURCE_SYSTEMS` expansion needed. The CFTC API is the strategy's strength on principle (real institutional positioning) — kill is premature. |
| `cta_commodity_momentum_term` | -4.22% on Clean n=1 (0/1 win) | Symbol: 45/46 single-symbol on SI=F suggests rotation logic broken; this is an engineering fix, not a gate | `wait-for-resolver-fix` — 97.8% noise share means even the symbol-concentration finding is downstream of resolver re-closing 45 entries at flat. The hedge-fund gate at `alpha_engine/hedge_fund_quality_gate.py:60-61` already has this in `COMMODITY_BANNED_STRATEGIES` (sidecar, not yet wired). No production action until resolver is fixed and we re-measure n. |
| `cta_cross_asset_tsmom` | +1.85% on Clean n=2 (1/2 win = 50%) | Symbol: cross-asset rotation collapsed to GC=F SHORT 24/32; engineering issue | `wait-for-resolver-fix` — 93.8% noise. Sum PnL is even mildly positive on raw data, so this is the LEAST data-supported kill candidate. Defer until clean n >= 20. |
| `cta_golden_cross_200` | n/a (Clean n=0 — every row is noise flicker) | Symbol: HG=F single-symbol; engineering | `wait-for-resolver-fix` — 100% noise share. **Zero** non-flicker closes in 26 picks. This is the cleanest possible "we have no signal yet" case in the audit. The 1.3× boost in `production_scanner.py:325` justified by "100% WR on 2 trades" is built on noise. |

**Summary by recommendation:**
- 0 of 5 are kill-now (data-supported) — none clears the WR=0/n>=20 deterministic-loss fast-path, and none has clean n high enough for the WR<0.35/avg<-0.5/n>=10 fast-path.
- 2 of 5 are `mutate-then-reassess` (`cot_positioning`, `cftc_cot_commercial_signal`) — both have clean-data losses concentrated on KC=F + CT=F, the same poison pills already flagged in Workstream C.
- 3 of 5 are `wait-for-resolver-fix` (the three `cta_*`) — too noise-contaminated to make any decision, and their underlying single-symbol concentration may itself be a downstream artifact of the same resolver logic.
- 0 of 5 are `wait-for-strat_name-fix` — these strategy labels are stable enough for source-system-level decisions, even though the canonical audit's Part 3 caveat about UNKNOWN `strat_name` does apply (we're operating at source-system / strategy-name granularity, not sub-strategy).

## Tool blockers (Workstream B + E dependencies)

`tools/mutation_analysis.py` accepts `--csv closed_picks.csv` or `--json [path]` (default `alpha_engine/data/closed_picks.json`) and groups by `strategy` (line 109-117), `system` (line 196-205), and `symbol`. **It does NOT take a `--source-system` filter or a `--strategy <name>` filter** — it always processes ALL strategies in the input and prints the top-20 spreaders. The investigation doc (Step 2) wraps it via `tools/run_all_mutations.sh` which iterates the unique strategy values and passes `--strategy <name>` (line 47 of investigation doc), but the flag `--strategy` does not exist in the actual `mutation_analysis.py` argparse (lines 280-312) — so the documented driver script targets a flag the script doesn't accept. **This is a discrepancy between investigation doc and tool code.**

What works today:
- `python tools/mutation_analysis.py --json` runs against `alpha_engine/data/closed_picks.json` (the legacy ledger, not `dashboard_payload.json`).
- `--matrix-csv mutation_artifacts/system_symbol_matrix.csv` writes per-(system,symbol) WR / trades / avg_pnl_pct → consumable by `tools/matrix_rules_from_csv.py` to generate `alpha_engine/data/matrix_symbol_gates.json`, which `audit_trail/quality_gates.py` loads behind the `MATRIX_SYMBOL_GATES` env flag.

What doesn't work:
- The recommended per-strategy autopsy from the investigation doc Step 2 is **broken** — `mutation_analysis.py` has no `--strategy` flag. Either the doc needs updating or the tool needs the flag added.
- The `--json` default path `alpha_engine/data/closed_picks.json` is the legacy ledger, NOT the `audit_trail/data/dashboard_payload.json` which the canonical audit treats as primary. They are separate sources with separate content. Per `feedback_dashboard_data_local_staleness.md`, the dashboard_payload is the authoritative current source.

**Workstream B (resolver-fix) blocker:** until `audit_trail/outcome_resolver.py:384-405` stops re-closing every resolved pick at the live yfinance spot price (which generates the `|pnl_pct|<0.05%` flicker on both win and loss sides), 94-100% of the `cta_*` rows are statistical fog. No mutation analysis output on this dataset can distinguish "strategy is broken" from "resolver is overwriting every entry with flat exit." Workstream B must land before any `cta_*` recommendation has data behind it.

**Workstream E (strat_name-fix) blocker:** as the canonical audit Part 3 caveat states, `strat_name` is UNKNOWN on all 3,500 rows in this payload, and the recompute falls back to `r.strategy || r.source_system`. The 5 names investigated here are strategy-level, so this report's findings are valid at strategy granularity, but if any of these 5 strategies is actually multiple sub-strategies multiplexed under one name, kill-at-strategy is too coarse. Workstream E (populate `strat_name`) would let us split, e.g., `cot_positioning::API_path` from `cot_positioning::RSI_proxy_path` and decide separately — currently both code paths emit the same `strategy="cot_positioning"`.

## Kill-without-replacement risk analysis

`project_futures_kill_without_replacement.md`: futures module went silent-dead at 5.9% WR / -96% PnL after 2 strategies were killed with no replacements added. Mirror risk for COMMODITY:

COMMODITY full source-system composition (`tools/_action_F_drilldown.js` final block):
- `futures_momentum`: **488** picks (78% of class)
- `cta_commodity_momentum_term`: 46
- `cta_cross_asset_tsmom`: 32
- `cta_golden_cross_200`: 26
- `cot_positioning`: 10
- `cftc_cot_commercial_signal`: 9
- (smaller buckets ignored)

Total of 5 underperformers: 123 picks (19.8% of class). If all 5 were killed, COMMODITY drops from n=622 to n=499. The class would NOT go silent — `futures_momentum` accounts for 488 picks alone and on its own measures (extra drilldown):

```
futures_momentum (n=488): WR=44.67% sumPnL=+16.11%
  noise share: 63.3% (134 noise wins + 175 noise losses)
  CLEAN n=179 wins=84 sumPnL=+16.33% WR=46.93%
```

**`futures_momentum` is the COMMODITY class's actual carrier**: clean n=179, clean WR=46.93%, clean sumPnL=+16.33%. The headline class-level -9.82% comes from the smaller losers — but even those losers are mostly resolver noise. If we kill nothing, the resolver fix alone may flip the class to mildly positive. **There is no kill-without-replacement risk on COMMODITY**. The class has carrier strategies; the 5 underperformers are not load-bearing.

That changes the urgency calculus. The "shut COMMODITY off entirely" alternative the prompt mentions is **not warranted** — `futures_momentum` is doing real work. The conservative move is: leave the carrier alone, gate the 2 `mutate-then-reassess` candidates behind SANDBOX symbol-blocks, defer the 3 `cta_*` until Workstream B ships.

## PR sequencing — what has to land first

1. **Workstream B (resolver fix)** — must ship first. Until `outcome_resolver.py:384-405` stops the 1bp-flicker behavior, 94-100% of the `cta_*` rows are noise; any mutation/kill PR on those 3 strategies is non-falsifiable. Tracked in `feedback_noncrypto_resolver_live_close_bug.md` and Part 7 P0 of canonical audit.
2. **Workstream B-followup: rebuild `dashboard_payload.json` recent_closed**. After resolver fix lands, re-export the closed ledger and re-run `tools/_action_F_drilldown.js`. Expected outcomes: (a) `cta_*` clean-n jumps from 0-2 to 20-40, putting them in the protocol's actionable range; (b) `cot_positioning` and `cftc_cot_commercial_signal` clean-n grows from 3-4 to ~10 each, raising or lowering kill confidence.
3. **Workstream F-1 PR (this report's actionable subset, written separately)** — add SANDBOX symbol-block mutation for `cot_positioning` and `cftc_cot_commercial_signal` on KC=F + CT=F + (optional) CL=F; record DNA lineage in `alpha_engine/data/strategy_mutations.json`; pass criterion: `mutate-then-reassess` at min_forward_trades=10 per strategy. **Does NOT expand `BLOCKED_SOURCE_SYSTEMS`** — operates at the per-(strategy, symbol) gate layer. Aligns with `audit_trail/quality_gates.py` matrix-symbol-gates flow.
4. **Workstream E (strat_name fix)** — independent of F but unlocks finer-grain decisions. Doesn't block F-1 because F-1 is at strategy granularity, but would refine future iterations.
5. **Workstream F-2 PR (after B + B-followup)** — once `cta_*` clean-n is real, run `python tools/mutation_analysis.py --json --matrix-csv mutation_artifacts/system_symbol_matrix.csv` and re-do steps 3-5 of the protocol. Likely outcomes (predicted, not data-supported yet): the GC=F-SHORT cohort of `cta_cross_asset_tsmom` may emerge as a real winner (cross-asset TSMOM SHORT on the Q1 gold reversal); the HG=F-LONG single-symbol concentration of `cta_golden_cross_200` may become a kill or a symbol-allowlist; `cta_commodity_momentum_term` may need rotation-logic engineering, not a gate.
6. **Workstream F-3 (engineering, not protocol)** — investigate why `cta_commodity_momentum_term` has 45/46 picks on SI=F and `cta_cross_asset_tsmom` has 24/32 on GC=F SHORT. Either the strategies are correctly responding to the current rank-distribution (Q1 2026 gold rally) and this is signal, OR the rotation logic is broken (deduping / single-symbol contention). The cleanest test is to back-fill clean closed-pick history pre-2026-04 and check whether the single-symbol concentration is persistent or window-specific.
7. **Tool fix: `tools/mutation_analysis.py` add `--strategy` and `--source-system` filters** so the documented per-strategy autopsy in `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` Step 2 actually matches the script. Small, ~30-line change.

The investigation doc explicitly forbids step-skipping: "Entries auto-flagged by this workflow must still traverse Stages 2-4 of the escalation ladder (rehabilitation → DNA mutation → backtest/WF) before any Stage-5 hard block, UNLESS the loss pattern is deterministic (WR = 0% on n >= 20)." None of the 5 strategies investigated here clears that fast-path. **No `BLOCKED_SOURCE_SYSTEMS` expansion is data-supported.**
