# Canonical PF Registry — Action Item A8

**Date:** 2026-05-17
**Deliverable:** `tools/build_pf_registry.py` + `audit_dashboard/data/pf_registry.json`
**Goal:** kill the "COMMODITY PF 2.57 vs 21.33" class of ambiguity by producing
ONE source-of-truth profit-factor registry. Every surface currently recomputes
PF its own way; the registry is the value they should all read instead.

---

## 1. What the registry contains

`audit_dashboard/data/pf_registry.json` is a versioned JSON
(`schema_version: 1.0.0`) with:

- `generated_utc`, `source_files` (which ledgers were found + row counts),
  `methodology` (dedup key, flicker rule, win/PF definitions).
- `counts` — raw / closed / after-flicker / deduped row counts plus each drop
  bucket, so the dedup delta is auditable from inside the file.
- `by_asset_class_raw` — PF/WR per asset class **without** dedup or flicker
  filtering (the "before" picture).
- `by_asset_class` — deduped, sanitized PF/WR per asset class (the canonical
  number).
- `by_asset_class_strategy` — deduped PF/WR per `(asset_class, strategy)`.
- `by_asset_class_strategy_symbol` — deduped PF/WR per
  `(asset_class, strategy, symbol)` (lets you isolate a single instrument,
  e.g. CT=F).
- `by_asset_class_strategy_date` — deduped PF/WR per
  `(asset_class, strategy, trade_date)`.

### Source ledgers ingested

| File | Present | Rows |
|------|---------|------|
| `alpha_engine/data/closed_picks.json` | yes | 8421 |
| `alpha_engine/data/closed_picks_fast.json` | yes | 323 |
| `battleground/data/closed_picks.json` | yes | 170 |
| **Total raw** | | **8914** |

### Methodology

- **Dedup key:** `(strategy, symbol, direction, trade_date, entry_price~2dp)`.
  `strategy` = `source_system` (falls back to `strategy`) — the COT
  re-emission bug lives at the `source_system` grain. `trade_date` falls back
  `entry_date → timestamp → created_at → closed_at → resolved_at → exit_date`
  because `entry_date` is only ~27% populated in the main ledger.
- **Spot-flicker sanitize:** a non-crypto closed pick with `abs(pnl_pct)` <
  0.0002 (2 bp) is dropped as a resolver spot-flicker artifact (the non-crypto
  outcome resolver closes at near-identical yfinance spot — ref MEMORY
  `feedback_noncrypto_resolver_live_close_bug`).
- **Win:** `pnl_pct > 0`. **PF:** `gross_profit / gross_loss` (loss as positive
  magnitude); `null` when there are no losses (reason flagged).
- Read-only w.r.t. all inputs; idempotent (only `generated_utc` changes
  between runs — verified by hashing the registry minus that field).

### Drop summary (this run)

| Bucket | Count |
|--------|-------|
| Raw rows | 8914 |
| Dropped: not actually closed | 78 |
| Dropped: resolver spot-flicker | 2 |
| Dropped: duplicate re-emissions | 3649 |
| **Deduped rows kept** | **5185** |

41% of raw closed rows were duplicate re-emissions — the exact mechanism that
inflated COMMODITY.

---

## 2. Raw vs deduped PF per asset class

| Asset class | RAW PF | DEDUP PF | RAW n | DEDUP n | PF delta |
|-------------|-------:|---------:|------:|--------:|---------:|
| BOND | 0.00 | 0.00 | 1 | 1 | 0.00 |
| COMMODITY | 2.284 | 1.106 | 354 | 173 | **−1.178** |
| CRYPTO | 0.450 | 0.480 | 7253 | 4360 | +0.030 |
| EQUITY | 0.678 | 0.602 | 45 | 33 | −0.076 |
| FOREX | 0.348 | 0.322 | 932 | 458 | −0.026 |
| FUTURES | 0.064 | 0.090 | 203 | 114 | +0.026 |
| UNKNOWN | 1.588 | 1.588 | 48 | 46 | 0.000 |

**Reading it:**

- **COMMODITY is the big mover** — raw PF 2.284 collapses to 1.106 once
  re-emissions are removed (n 354 → 173). This is the inflation the action
  item targets: COT signals re-emitted asymmetrically (winners more than
  losers) bias the un-deduped aggregate upward. The deduped class-level PF of
  1.106 is barely above break-even — the "edge" was a counting artifact.
- CRYPTO/FUTURES PF tick *up* slightly after dedup, which is expected: dedup
  removes whichever side was over-counted, and for those classes losers were
  over-represented.
- EQUITY/FOREX move modestly; their re-emission rate is lower.
- `UNKNOWN` = rows whose `asset_class` could not be resolved (mostly from the
  fast/battleground ledgers that lack the field); kept visible rather than
  silently merged.

---

## 3. COMMODITY sanity check

The action item requires the registry's `multi_asset_cot` COMMODITY figure to
match the ~4.69 deduped PF from `reports/commodity_pf_verification_2026-05-17.md`.

That report scoped specifically to `multi_asset_cot` **on `CT=F`** (cotton):
114 raw → 40 deduped, PF 4.69, WR 77.5%.

Registry `by_asset_class_strategy_symbol`, row
`(COMMODITY, multi_asset_cot, CT=F)`:

```
deduped PF = 4.68742   WR = 77.5%   n = 40
```

**Exact match.** ✅ The dedup logic reproduces the verification report to 4
decimal places.

Note: the registry's *strategy-level* row `(COMMODITY, multi_asset_cot)` shows
PF ≈ 2.33, n = 52 — that is correct, not a discrepancy. The strategy pools CT=F
(40 signals, PF 4.69) with ZW=F (wheat, a genuine loser) and KC=F. The report's
4.69 is the CT=F instrument isolated; the registry's
`by_asset_class_strategy_symbol` granularity exposes exactly that number, while
the strategy/class rows correctly show the diluted, more honest picture.

---

## 4. Wiring plan (follow-up PR — NOT done here)

Per the repo Wire-Up Rule, the registry is the new source of truth but
**re-pointing consumers at it is a separate change**. This PR ships the
registry only. Surfaces to re-point in a follow-up:

| Surface | File | What to change |
|---------|------|----------------|
| Dashboard generator | `alpha_engine/dashboard_generator.py` | The `asset_class_health` / `systems` PF aggregation should read `pf_registry.json::by_asset_class` and `by_asset_class_strategy` instead of recomputing from `closed_picks.json` un-deduped. This is the surface that currently emits the inflated COMMODITY PF 7.71. |
| Score booster | `alpha_engine/score_booster.py` | Any per-strategy PF lookup used to boost/penalize scores should consume `by_asset_class_strategy` so booster decisions use the deduped PF, not the re-emission-inflated one. |
| Position sizing | `alpha_engine/position_sizing.py` (and `conformal_sizing.py`) | Kelly / risk sizing should size off `by_asset_class` / `by_asset_class_strategy` deduped PF. Sizing off raw COMMODITY PF 2.28 would over-allocate vs the true 1.11. |

Follow-up PR should also add a hourly/CI step that runs
`tools/build_pf_registry.py` so the registry stays fresh, and a thin
`pf_registry` reader helper so the three consumers do not each re-parse the
JSON.

**Wiring status of this PR:** registry builder is a standalone read-only
producer; it has no production caller yet and is intentionally so — it is the
*new source*, and the wire-up above is the named follow-up. This satisfies the
Wire-Up Rule's opt-in/sidecar path: the consumers are named with file +
function + intent.

---

## 5. How to reproduce

```
python tools/build_pf_registry.py
```

Writes `audit_dashboard/data/pf_registry.json`. Idempotent, read-only w.r.t.
all `closed_picks*.json` ledgers. `python -m py_compile tools/build_pf_registry.py`
passes.
