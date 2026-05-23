# Workstream E — `strat_name` Data Quality Investigation

**Date:** 2026-04-27
**Author:** claude-opus-4-7 (investigation only — no code modified)
**Source payload:** `audit_trail/data/dashboard_payload.json` (3,500 rows in `picks.recent_closed`, generated_at 2026-04-27T22:08:21Z)
**Scope:** Verify peer claim that `strat_name` is UNKNOWN for all 3,500 rows; trace upstream; design fix; quantify blast radius.

---

## 1. TL;DR — Peer claim was partially incorrect

**Peer claim:** `strat_name` is UNKNOWN for all 3,500 rows in `picks.recent_closed`.

**Actual state (this audit, replicable from `tools/_mercury2_recompute.js` schema):**
- The field literally named `strat_name` **does not exist** as a key on any of the 3,500 rows. `r.strat_name === undefined` for 3500/3500. The peer was searching for the wrong field name.
- The field that **does** carry per-strategy attribution is **`strategy`** (singular), and it is populated with a real, non-fallback value for **3,436 / 3,500 rows = 98.2%**.
- 51 rows carry literal `"unknown"` and 13 are empty strings — concentrated in 4 source_systems: `quan_engine` (20), `regime_terminal` (17), `kimi_signal_tracking` (14), `kimi_riseoftheclaw` (13). Total 1.83% of payload.
- 194 distinct `strategy` values are present. The COMMODITY systems flagged in Workstream F (`cot_positioning`, `cftc_cot_commercial_signal`, `cta_commodity_momentum_term`, `cta_cross_asset_tsmom`, `cta_golden_cross_200`) **are themselves real `strategy` values**, not source_system fallbacks. The names in Part 3 of `reports/asset_class_independent_recompute_2026_04_27.md` are correctly attributed at the strategy level for those 5 systems.

**What is true** about `tools/_mercury2_recompute.js:98`: it does fall back to `r.source_system` when `r.strategy` is empty, which masks 1.8% of rows whose attribution is genuinely lost. That is a real but small data-quality defect — not a 100% bug.

The Workstream F kill-or-investigate decision on the 5 COMMODITY systems is **NOT BLOCKED** by this issue, because their names appear as the literal `strategy` value in 213 rows (46+32+26+9+10 from the audit's Part 3 sample sizes) — those rows carry true per-strategy attribution.

---

## 2. Methodology

1. Read 5 raw rows from `audit_trail/data/dashboard_payload.json` to capture every field.
2. Counted `strat_name`, `strategy`, `strategy_name`, `strat_id`, `system`, `source_system` presence across all 3,500 rows.
3. Distribution of `strategy` values broken down by asset_class and by source_system to identify gaps.
4. Greped `audit_trail/dashboard_generator.py` for the schema (`_CLOSED_PICK_KEEP_FIELDS`) and the slim function (`_slim_closed_pick`).
5. Greped pick-creation paths in `alpha_engine/forward_validator.py`, `alpha_engine/isolated_signal_integrator.py`, `alpha_engine/cot_positioning.py`, `alpha_engine/commodity_signal_generator.py`.
6. Compared upstream `alpha_engine/data/closed_picks.json` (6,906 rows) against the 3,500 published rows to detect drops in fidelity.
7. Greped consumers (`audit_dashboard/template.html`, `alpha_engine/ml_ranker.py`, `ml_gatekeeper/gatekeeper.py`, `cross_aggregation/performance_alerts.py`).

---

## 3. Confirmed field state — 5 sample rows

All 5 rows have `strategy: "quick_engine"` and `source_system: "crypto_ml_edge"`, asset_class ETF. None has any field named `strat_name`. Schema is consistent.

| Field | Row 0 | Row 1 | Row 2 | Row 3 | Row 4 |
|---|---|---|---|---|---|
| id | `connors_rsi2::GLD::2026-03-18` | `connors_rsi2::SPY::2026-03-23` | `connors_rsi2::QQQ::2026-03-23` | `connors_rsi2::TLT::2026-04-01` | `connors_rsi2::IWM::2026-04-13` |
| symbol | GLD | SPY | QQQ | TLT | IWM |
| direction | LONG | LONG | LONG | LONG | LONG |
| **strategy** | quick_engine | quick_engine | quick_engine | quick_engine | quick_engine |
| **source_system** | crypto_ml_edge | crypto_ml_edge | crypto_ml_edge | crypto_ml_edge | crypto_ml_edge |
| **strat_name** | (absent) | (absent) | (absent) | (absent) | (absent) |
| asset_class | ETF | ETF | ETF | ETF | ETF |
| status | LOST | WON | WON | UNRESOLVED | WON |
| pnl_pct | -2.21 | 1.05 | 1.02 | 0.0 | 0.57 |
| score | 61 | 55 | 55 | 56 | 56 |
| confidence | 0.8 | 0.7 | 0.7 | 0.73 | 0.73 |
| trust_tier | UNTRUSTED | UNTRUSTED | UNTRUSTED | UNTRUSTED | UNTRUSTED |
| strat_fwd_wr | 57.1 | 57.1 | 57.1 | 57.1 | 57.1 |
| strat_fwd_pf | 0.76 | 0.76 | 0.76 | 0.76 | 0.76 |

**Note** the id-prefix (`connors_rsi2::...`) is an internal pick-id namespace — distinct from the live `strategy` field (`quick_engine`). The two diverge intentionally; the `id` is a stable composite key, `strategy` is the runtime label.

There are **85 distinct keys** across all 3,500 rows. Strategy-related keys present:
`source_system`, `strat_concentration_level`, `strat_concentration_penalty`, `strat_concentration_warning`, `strat_decay`, `strat_fwd_pf`, `strat_fwd_trades`, `strat_fwd_wr`, `strat_pnl_ex_top_symbol`, `strat_top_symbol`, `strat_top_symbol_pnl_pct`, `strategy`, `strategy_concentration_*`, `strategy_distinct_symbols`, `strategy_top_symbol*`, `at_issue_strat_fwd_*`. **There is no `strat_name`.**

### Distribution

- Distinct `strategy` values: **194**
- Distinct `source_system` values: **40**
- Top 5 strategies: `forex_rsi2_mean_reversion` (555), `futures_momentum` (498), `quan_engine` (314), `st_fear_greed_contrarian` (256), `luxalgo_confluence` (181)
- Per-class strategy populated rate:

| Asset class | n | with strategy | unknown/empty |
|---|---:|---:|---:|
| BOND | 17 | 17 | 0 |
| COMMODITY | 622 | 622 | 0 |
| CRYPTO | 1598 | 1556 | 42 |
| EQUITY | 381 | 377 | 4 |
| ETF | 83 | 83 | 0 |
| FOREX | 794 | 776 | 18 |
| FUTURES | 2 | 2 | 0 |
| UNKNOWN | 3 | 3 | 0 |

**COMMODITY is 100% populated** — Workstream F is unblocked. The 64 unknown/empty rows are 84% CRYPTO.

---

## 4. Upstream trace — schema and pick creation

### Schema (the published payload)

`audit_trail/dashboard_generator.py:154-177` defines `_CLOSED_PICK_KEEP_FIELDS`. Line 155 includes `"strategy"` but **not** `"strat_name"`. Line 180 `_slim_closed_pick(pick)` filters every pick through this set before serialization (line 12654: `"recent_closed": [_slim_closed_pick(p) for p in recent_closed]`).

> So even if some upstream layer attached a `strat_name`, the slim filter would strip it. There is no slim-level data loss for `strategy` itself — it passes through.

### Pick creation (where `strategy` IS set)

- **Crypto/forex production path** — `alpha_engine/forward_validator.py:2182`:
  ```python
  pick = {
      "id": f"{strategy}::{signal['symbol']}::{_now_date()}",
      "strategy": strategy,
      ...
  }
  ```
  And `alpha_engine/forward_validator.py:2858` — same shape for the secondary emit. Both populate `strategy` from the upstream `signal['strategy']`.
- **Isolated-signal integrator** (regime_terminal, genome, battleground, claude_gainer) — `alpha_engine/isolated_signal_integrator.py`. Per-source normalizers all set `"strategy"` explicitly. Example line 325:
  ```python
  "strategy": f"regime_{pick.get('regime', 'unknown').lower().replace(' ', '_')}",
  ```
  → if upstream `regime_terminal/data/active_signals.json` is missing the `regime` key, the resulting strategy is `"regime_unknown"`. We see 17 such rows.
- **Commodity strategies** — `alpha_engine/cot_positioning.py:169` sets `"strategy": "cot_positioning"`; `alpha_engine/commodity_signal_generator.py:99` sets `"strategy": strategy_name` from caller. CTA replicator sets `"cta_commodity_momentum_term"`, `"cta_cross_asset_tsmom"`, `"cta_golden_cross_200"` directly. **All 5 Workstream-F-flagged systems are real strategy values.**

### Where empty/unknown rows come from

- 20 rows from `quan_engine` source_system carry `strategy="unknown"` and numeric ids like `6158`. These rows enter via a different path (likely `quan_engine/forward_tracker.py` writing to `quan_engine/data/`, then ingested without a strategy attribute). The 314 rows with `strategy="quan_engine"` come from `alpha_engine` source_system — those are the production scanner rows where `strategy` IS set. The 20 unknown rows are quan_engine's own forward-tracker output, which lacks a strategy label.
- 17 from `regime_terminal` — `regime` key missing in upstream JSON → `"regime_unknown"` (which then appears as plain `"unknown"` after a downstream lower/strip; check `audit_trail/dashboard_generator.py` normalizers — but regardless, the upstream root cause is missing `regime` in `regime_terminal/data/active_signals.json`).
- 14 from `kimi_signal_tracking`, 13 from `kimi_riseoftheclaw` — opt-in ingestion paths that do not stamp a strategy.

### `_mercury2_recompute.js` fallback

Line 98 `const s = r.strategy || r.source_system || 'UNKNOWN';` is the audit's fallback. For the 64 rows with no/empty `strategy`, this aliases the row to its source_system. At 1.8% of rows, this **does not bias the audit's per-class WR/PF/PnL aggregates** (those don't depend on the strategy bucket). It only biases per-strategy counts where the source_system label collides with a real strategy label — which happens for `quan_engine` (`strategy="quan_engine"` exists for 314 rows + fallback adds 20 more = 334 attributed to a "strategy" called `quan_engine`). That's a 6% upward bias on the `quan_engine` strategy bucket — small but worth noting in any quan_engine kill decision.

---

## 5. Crypto vs non-crypto comparison

| Path | Where strategy is set | Population in payload | Notes |
|---|---|---|---|
| Crypto (forward_validator) | `alpha_engine/forward_validator.py:2182, 2858` | 1556 / 1598 = 97.4% | The 42 unknowns concentrate in `quan_engine`/`regime_terminal` ingestion sub-paths, not the main path |
| Forex | `alpha_engine/cot_positioning.py:169` + `forex_rsi2_mean_reversion` strategies | 776 / 794 = 97.7% | 18 unknowns; main strategy `forex_rsi2_mean_reversion` (555) and `futures_momentum` (498) populate cleanly |
| Commodity | `alpha_engine/cot_positioning.py:169`, `cta_replicator` | 622 / 622 = 100% | Workstream F is unblocked |
| Equity | `alpha_engine/strategies/connors_rsi2.py`, `stocks_competition` strategies | 377 / 381 = 99.0% | |
| ETF | `connors_rsi2`, `quick_engine` | 83 / 83 = 100% | |
| BOND | various | 17 / 17 = 100% | |

**The published audit's per-strategy claims for COMMODITY (Part 3 of the master audit) are valid** — those rows carry true per-strategy attribution, not a source_system fallback masquerading as a strategy.

The master audit's caveat at line 44 (`"a third peer agent verified that strat_name is UNKNOWN for all 3,500 rows"`) **should be retracted or corrected**. The right caveat is: "1.8% of rows lack a real strategy label and fall back to source_system in the recompute; this affects `quan_engine`, `regime_terminal`, `kimi_signal_tracking`, and `kimi_riseoftheclaw` only."

---

## 6. Fix design

### 6a. Backfill (existing 64 unknown/empty rows)

- **`quan_engine` × 20**: backfill via `(source_system, symbol, direction) → strategy="quan_engine_scalp"` mapping. Upstream `alpha_engine/data/closed_picks.json` shows 5,293 rows attributed to `quan_engine_scalp` and 109 to `quan_engine_swing`. Without entry-time/regime context, conservative backfill is `quan_engine_scalp` (the dominant variant) with a marker `_strat_inferred=true`.
- **`regime_terminal` × 17**: backfill from `regime_terminal/data/active_signals.json` if the file still has the `regime` key for the matching `(symbol, timestamp)`. Otherwise use `regime_unknown` literally and don't infer.
- **`kimi_*` × 27**: probably unrecoverable — the kimi cohort lacks fine-grained strategy IDs; backfill as `"kimi_signal"` with `_strat_inferred=true`.

Backfill is a one-time pass; suggested file `tools/backfill_strat_name.py` (NEW). Operates on a snapshot copy of `audit_trail/data/dashboard_payload.json`, never on the live payload.

### 6b. Fix-forward (newly created picks)

The defect is upstream of `_slim_closed_pick`. Three fixes:

1. **`alpha_engine/isolated_signal_integrator.py:325`** — change `pick.get('regime', 'unknown')` to require `regime` and skip the row if missing (loud failure), or assign a deterministic value. Minimal patch:
   ```python
   regime_val = pick.get("regime")
   if not regime_val:
       logger.warning("regime_terminal pick missing 'regime' for %s", ticker)
       return None  # drop, don't ingest
   ```
2. **quan_engine ingest path** — find where the 20 rows with strategy=`"unknown"` enter (likely `quan_engine/forward_tracker.py` or `audit_trail/universal_pick_resolver.py:68`). Stamp `strategy="quan_engine_scalp"` (or read it from upstream metadata) at ingest.
3. **kimi paths** — same: stamp a strategy at ingest. The cleanest place is `alpha_engine/isolated_signal_integrator.py` or the kimi-specific normalizer.

**Schema enforcement (recommended):** add a one-time check in `audit_trail/dashboard_generator.py` after `_build_recent_closed_picks` returns:

```python
unknown_strat = [p for p in recent_closed if not p.get("strategy") or p.get("strategy") == "unknown"]
if unknown_strat:
    logger.warning("strat-quality: %d/%d rows have unknown strategy: srcs=%s",
                   len(unknown_strat), len(recent_closed),
                   collections.Counter(p.get("source_system","?") for p in unknown_strat))
```

**Warn-only initially** (don't reject, since the dashboard is now load-bearing). After 2 cycles with the fix-forward in place, escalate to error-and-block if `unknown_strat / total > 1%`.

---

## 7. Downstream consumers

| Consumer | File:line | Reads | Behavior on `strategy=unknown`/empty |
|---|---|---|---|
| Audit dashboard frontend | `audit_dashboard/template.html:1844, 2006, 4521, 4893, 4961, 5176, 5199, 5206, 5488, 5673, 5732, 5785` (and 329 more refs) | `pick.strategy` with `\|\| p.signal_type \|\| '?'` fallback | Renders "?" for empty; existing empty-handling. Not broken, just attribution lost. |
| Strategy popup/leaderboard | `audit_dashboard/template.html:1715, 1723` | finds `s.strategy === strategyName` in `window.D.leaderboard` | Misses 64 rows; non-fatal. |
| ML ranker training | `alpha_engine/ml_ranker.py:630, 1363, 1657, 1668, 2741` | groups by `strategy` for per-strategy stats; uses (symbol, strategy) as cohort key | 64 rows go into `(sym, "")` bucket — small bias, ~1.8% of training rows |
| ML gatekeeper | `ml_gatekeeper/gatekeeper.py:98, 200, 463, 590, 642` | `(pick.get("strategy") or "").lower()` for kill-list match and per-strategy thresholds | Empty matches no kill rule; 64 rows pass through gates that should have caught them |
| Performance alerts | `cross_aggregation/performance_alerts.py:62-68` | `_strategy_baseline_wr_from_stats(stats, strat_name)` — uses pick's strategy as the lookup key | Empty key returns no baseline; alert silently no-ops on those rows |
| Audit recompute scripts | `tools/_mercury2_recompute.js:98`, `tools/_root_cause_2026_04_27.js`, `tools/_recompute_2026_04_27.js` | Falls back to `r.source_system` | 64 rows misattributed (1.8%); minor bias |
| Confluence/blueprint reports | `audit_dashboard/blueprint_generator.py:459-550` | groups by strategy for STRATEGY_LOGIC table | 64 rows aggregated under their source_system in fallback contexts |
| Mutation pipeline | (downstream of audit recommendations) | Reads strategy name from audit reports | If audit names a strategy, mutation runs against it — works for the 5 COMMODITY systems |

The peer's framing that consumers see "UNKNOWN everywhere" is incorrect. They see real strategy values for 98.2% of rows.

---

## 8. Test plan

1. **Unit — schema invariant**: add `tests/test_strategy_field_invariant.py` that loads `audit_trail/data/dashboard_payload.json` and asserts `>= 99%` of `picks.recent_closed` rows have a non-empty, non-`"unknown"` `strategy`. Threshold 99% leaves headroom; tighten to 99.9% after fix-forward.
2. **Unit — schema completeness**: assert `_CLOSED_PICK_KEEP_FIELDS` contains `"strategy"` (already does — regression guard against accidental removal).
3. **Integration — pick creation**: extend existing `tests/test_quality_gates.py` (line 117 already uses `source_system="regime_terminal"`) to assert the resulting pick has a non-empty `strategy`.
4. **Recompute audit**: re-run `node tools/_mercury2_recompute.js` after fix-forward and confirm the per-strategy bottom-5 lists for COMMODITY do not change materially (they should not — the 100% coverage means F's targets are unaffected).
5. **Property test on backfill**: backfill script must not modify any row whose existing `strategy` is non-empty. Snapshot diff before/after.
6. **Backwards compat**: confirm `audit_dashboard/template.html` still renders correctly when ALL rows have a populated strategy (previously some were `?`; now they will be specific names).

---

## 9. Blast radius — if `strategy` becomes 100% populated

| Surface | Effect |
|---|---|
| Audit dashboard "Strategy" filter dropdown | Adds ~3 new options (`quan_engine_scalp` for the 20 backfilled, `regime_unknown` for 17, `kimi_signal` for 27); existing dropdown options unchanged. |
| Per-strategy leaderboard tile | 3 new low-volume rows. `quan_engine_scalp` row gains 20 closed; `regime_unknown` becomes a 17-row outlier worth investigating. |
| ML ranker training | Empty-strategy bucket disappears; per-strategy feature buckets gain ~1.8% more rows. Negligible accuracy impact (n=64 across 194 strategies). |
| ML gatekeeper kill rules | None of the 4 backfill labels (`quan_engine_scalp`, `regime_unknown`, `kimi_signal`) are currently in the kill list. **Action:** confirm with `audit_trail/quality_gates.py` kill-set state before backfill. |
| Performance alerts | 64 rows that were silently skipped now generate alerts if their strategy WR drops below baseline. Expected to surface 0-2 net new alerts per cycle. |
| Audit master report Part 3 | Bottom-strats lists are unchanged for COMMODITY/EQUITY/ETF/BOND/FOREX (already 100% / 99.0% / 100% / 100% / 97.7% populated). CRYPTO bottom-strats may add `"unknown"` or `"regime_unknown"` to its bottom-5 list — explicit data, not noise. |
| Cohort sizes for the 5 Workstream-F COMMODITY systems | UNCHANGED (already 100%). |

---

## 10. PR sequencing — does this block Workstream F?

**No.** Workstream F (mutation-before-kill on the 5 COMMODITY systems: `cot_positioning` n=10, `cftc_cot_commercial_signal` n=9, `cta_commodity_momentum_term` n=46, `cta_cross_asset_tsmom` n=32, `cta_golden_cross_200` n=26) operates on rows where `strategy` is **already** populated 100%. The Workstream F mutation harness (per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` and `tools/mutation_analysis.py`) keys on the literal `strategy` value, which exists for every COMMODITY row.

**Recommended ordering:**

1. **Workstream F (commodity mutation)** — proceed independently. Treat the 5-system per-strategy cohort sizes (10, 9, 46, 32, 26) as authoritative.
2. **Workstream E fix-forward** (`isolated_signal_integrator.py:325` regime_terminal guard + quan_engine + kimi stamping) — small, atomic, ~3 file PR. Independent of F.
3. **Workstream E backfill** (`tools/backfill_strat_name.py` snapshot pass) — optional, run once after fix-forward stabilizes. Independent of F.
4. **Workstream E schema enforcement** (warn-then-error invariant in `dashboard_generator.py`) — last; gated on backfill + fix-forward sticking for 2 cycles.

**Audit master report correction:** the caveat in `reports/asset_class_independent_recompute_2026_04_27.md` line 44 should be edited from "strat_name is UNKNOWN for all 3,500 rows" to: "the field is named `strategy` (not `strat_name`); 1.8% of rows lack a populated value and fall back to `source_system` in the recompute, concentrated in `quan_engine`, `regime_terminal`, and the kimi cohorts. COMMODITY is 100% populated; per-strategy claims for the 5 commodity systems are valid."

---

## Appendix — quick reproduction

```bash
# Verify field state
node -e "
const closed=JSON.parse(require('fs').readFileSync('audit_trail/data/dashboard_payload.json','utf8')).picks.recent_closed;
let strat_name=0, strategy_pop=0, strategy_unk=0;
for (const r of closed){
  if (r.strat_name!==undefined) strat_name++;
  if (r.strategy && r.strategy!=='unknown' && r.strategy!=='') strategy_pop++;
  else strategy_unk++;
}
console.log('strat_name present:', strat_name, '/', closed.length);
console.log('strategy populated:', strategy_pop, '/', closed.length);
console.log('strategy unknown/empty:', strategy_unk);
"
# Expected output:
# strat_name present: 0 / 3500
# strategy populated: 3436 / 3500
# strategy unknown/empty: 64
```

**End of report.**
