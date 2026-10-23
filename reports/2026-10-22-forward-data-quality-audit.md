# Forward-Pick Data Quality & Tracking-Gap Audit — 2026-10-22

**Auditor:** Zoo (independent, per directive: "find bugs where performance P/L is impossible, or 0% etc." + "analyze forward pick data … check for errors in the tracking of that data, or gaps")
**Tool:** `tools/pnl_impossibility_audit.py` (new, independent audit harness)
**Timestamp:** 2026-10-22T23:16Z

---

## 1. Headline result

The **deployed dashboard output is clean**: `audit_dashboard/data/dashboard_data.json`
(generated 2026-10-19T19:40) passes the full P/L-impossibility sweep with **0 issues** —
no exact-zero-PnL terminal leaks, no direction/reported-PnL mismatches, no impossible
magnitudes, no placeholder exits.

The genuine problems found are **tracking gaps at the source-feed level** (not in the
deployed metrics), concentrated in three places: KIMI winner attribution, `ml_consensus`,
and `ml_gatekeeper`.

---

## 2. Verification method

`tools/pnl_impossibility_audit.py` scans each closed-pick feed for:

1. exact `0.0%` pnl on terminal status (placeholder/breakeven leak);
2. direction-vs-reported-PnL mismatch (LONG win but implied move negative, etc.);
3. impossible `|pnl| >= 10,000%` (and suspect `>= 1,000%`);
4. terminal rows with placeholder/`<=0` exit but pnl present;
5. reported-vs-implied divergence (>20% tolerance).

Cross-checked against the generator filters in
[`dashboard_generator.py`](../audit_trail/dashboard_generator.py:4816)
(`_is_valid_resolved_pick`: `_NON_PERFORMANCE_EXIT_REASONS`,
`STALE*`, `RESOLVE_FAILED*`, placeholder-exit, corrupt-price, magnitude gates).

---

## 3. Findings

### 3.1 alpha_engine zero-PnL clusters — correctly filtered, NOT a deployed bug

`alpha_engine/data/closed_picks.json` (510 rows) has 246 exact-zero-PnL rows:

| exit_reason | count | strategy cluster |
|---|---|---|
| `FORCE_CLOSED_TOXIC` | 123 | `futures_momentum` (SI=F/PL=F/HG=F/NKD=F), `forex_rsi2_mean_reversion` JPY pairs |
| `RESOLVE_FAILED_MAX_RETRIES` | 118 | breakeven-fallback (priced-failed) |
| `STALE_NO_DATA` | 5 | `ml_strategy_reviver`/inverse, `genome_mega_mutation` |

**Verdict:** All three reasons are excluded by the deployed generator filter
(`_NON_PERFORMANCE_EXIT_REASONS`, `startswith("STALE")`, `startswith("RESOLVE_FAILED")`).
The live dashboard does not count them. This is expected behavior — not a bug in output.

### 3.2 KIMI_RISEOFTHECLAW — 521 winners with NO strategy attribution (tracking error)

`KIMI_RISEOFTHECLAW/data/closed_picks.json` (2229 rows):

- **521 winners (>2% realized PnL)** — **100% have `algorithm="unknown"`** (no strategy attribution).
- **All 521 also have `take_profit=0` and `stop_loss=0`** — risk levels are never recorded.
- Top winner symbols: TIA-USD (71), ETH-USD (48), BTC-USD (45), SOL-USD (43), NEAR-USD (34), ADA-USD (34), BNB-USD (33), ATOM-USD (31).

**Impact:** These wins cannot be credited to a strategy/algorithm, so they are
invisible to any strategy-level leaderboard or tuning. This is a data-tracking gap.
Note: this file is currently **not** consumed by the dashboard (only
`active_picks.json` is read at
[`dashboard_generator.py`](../audit_trail/dashboard_generator.py:8924)), so it is an
external research ledger — but it would corrupt any future integration unless attribution
is fixed.

### 3.3 `ml_consensus` — wired in source chain but emits NOTHING

- `ml_consensus` is registered in `JSON_PICK_SOURCES`
  ([`dashboard_generator.py`](../audit_trail/dashboard_generator.py:4101)).
- But `data/active_picks.json` is **MISSING** and `data/closed_picks.json` is **empty**
  (`[]`, len=0).
- [`consensus.py`](../ml_consensus/consensus.py:389) explicitly only writes
  `[]` with the comment `"empty for now, dashboard generator resolves"`.

**Impact:** The prior audit report (`reports/2026-10-22-ml-stack-audit.md`) cites
`ml_consensus` as a validated +10.71pp WR edge — but **no pick data is persisted** for it.
The dashboard source entry silently contributes zero. The edge is claimed but not
reproducible from the persisted artifacts. **This is a real gap** and blocks
WIN-INTEGRATE until consensus output is persisted.

### 3.4 `ml_gatekeeper` — registered but emits NO pick files

- `ml_gatekeeper` is registered in `JSON_PICK_SOURCES`
  ([`dashboard_generator.py`](../audit_trail/dashboard_generator.py:4096)).
- `data/` contains only `ab_history.jsonl`, `ab_rollback_state.json`, `ab_summary.json`,
  `per_class_gates.json` — **no** `active_picks.json`, **no** `closed_picks.json`.
- Its ML quality prediction runs only in **shadow mode** (never rejects; logs to
  `per_class_gates.json`, per [`quality_gates.py`](../audit_trail/quality_gates.py:10092)).

**Impact:** The source entry no-ops. No gatekeeper-gated picks ever reach dashboard
metrics. To leverage it (per WIN-INTEGRATE) it must persist gated pick files first.

### 3.5 ★ MICRO-HOLD / INSTANT SYNTHETIC FILLS — "ultimate bug" class FOUND & FIXED

**New finding (this session, directive "find the ultimate bugs … give us a wrong P/L").**
A whole class of rows passes every *price-based* impossibility check yet is **not** a real
trade: rows opened and closed within seconds at synthetic/same-tick prices. They inflate
WR/PF/total PnL with phantom trades.

**Evidence (hold-time scan, `tools/hold_time_anomaly_scan.py`):** across 8 closed-pick feeds
(4,465 rows) → **956 micro-holds < 60s**, contributing **~+2200.9% phantom PnL** and
**584 phantom wins**:

| feed | rows | micro-hold <60s | phantom PnL sum | phantom wins |
|---|---|---|---|---|
| `genome/data/closed_picks.json` | 1,085 | **955** (mega_mutation_*) | +2200.9% | 583 |
| `alpha_engine/data/closed_picks.json` | 510 | 1 | ~0.0% | 1 |

Sample artifact (`STXUSDT`, `mega_mutation_macd_rsi_m048`): entry `timestamp=2026-04-16T20:08:26.969Z`
→ exit `closed_at=2026-04-16T20:08:27.513Z` (0.544 s), status `LOST`, pnl `-2.763%`.
955 rows share this signature.

The `mega_mutation` source is wired into the dashboard
([`dashboard_generator.py`](../audit_trail/dashboard_generator.py:3940)) with closed source
= `genome/data/closed_picks.json`, so these rows **were** flowing into performance metrics.

**Fix (TDD, merged into `_is_valid_resolved_pick`):** added `_MIN_HOLD_SECONDS = 60` and
`_pick_hold_duration_seconds()` ([`dashboard_generator.py`](../audit_trail/dashboard_generator.py:4816)),
rejecting rows held <60s **only when both timestamps exist** (never over-reject on missing
timestamps). Entry/exit keys scanned include `timestamp`/`created_at` (genome's schema).
7+1 regression tests in [`tests/test_dashboard_generator_micro_hold.py`](../tests/test_dashboard_generator_micro_hold.py)
(26 total passing with the placeholder-exit suite).

**Runtime impact (verified):** on `genome/data/closed_picks.json` the gate now excludes
**955 micro-holds → +2200.9% phantom PnL and 583 phantom wins** removed from performance metrics.

---

## 4. Winner-hunting note (forward data)

The only feed with genuine, resolved forward winners is KIMI (top: TIA/ETH/BTC/SOL/NEAR),
but attribution is missing. `ml_consensus`/`ml_gatekeeper` have no forward picks to
analyze until export is fixed. No other feed showed impossible P/L.

---

## 5. Recommended actions

1. **KIMI:** backfill `algorithm` attribution + TP/SL in `closed_picks.json` before any
   dashboard integration.
2. **ml_consensus:** persist `active_picks.json`/`closed_picks.json` from the consensus
   run (currently only writes `[]`), then they can be validated against the claimed edge.
3. **ml_gatekeeper:** emit gated `active_picks.json`/`closed_picks.json` so the source
   entry is non-empty.
4. Re-run `tools/pnl_impossibility_audit.py` (the full sweep) after any of the above.
5. **DONE:** micro-hold/instant-fill gate (section 3.5) — keep `_MIN_HOLD_SECONDS` low enough
   (60s) to only catch synthetic fills, not genuine scalps.

*Not financial advice. Research/educational only. Past performance does not guarantee future results.*
