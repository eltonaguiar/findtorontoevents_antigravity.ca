# Second emit callsite — and the emit-coverage survey it forced

**Date:** 2026-11-22
**Files:** `alpha_engine/provenance_hook.py` (new), `alpha_engine/smart_picks_engine.py`,
`alpha_engine/production_scanner.py`, `tests/test_provenance_hook.py` (new),
`.github/workflows/provenance-verify.yml`
**Ledger item:** T4

---

## The hole

`alpha_engine/production_scanner.py` was the **only** path that emitted to the
provenance ledger. Every pick that reached the dashboard by another route was
invisible to the instrument built to measure it — a survivorship hole inside the
thing that exists to close survivorship holes.

`reports/provenance/reconciliation.json` put a number on it: **3,500 of 3,500 closed
dashboard picks were `dashboard_only`** — none had ever been emitted.

## What changed

### 1. One shared hook instead of a copy

`alpha_engine/provenance_hook.py`:

```python
emit_picks(picks, default_source=None, label="PROVENANCE", quiet=False, path=None)
    -> (written, rejected)          # never raises
```

- **Field-name normalisation.** Each producer spells its fields differently —
  `entry` / `entry_price`, `tp` / `take_profit`, `direction` / `side`,
  `strategy` / `strategy_family`. The hook accepts all of them, so a new callsite does
  not need to learn the ledger schema.
- **`created_at` cannot be supplied.** The hook builds a fresh dict, so a caller's
  `created_at` is dropped by construction; `provenance_ledger.emit` refuses it a second
  time. Both guards are asserted in tests, because this is the property the whole
  ledger rests on.
- **No zero-filled records.** A pick missing entry, TP or SL is *dropped*, not emitted
  with zeros — a pick with no levels has no resolvable outcome and would sit OPEN
  forever, silently dragging `pct_forward` down.
- **Fail-safe.** Every exception is caught and `([], [])` returned. The ledger observes
  the trading system; it must never gate it.

### 2. Second callsite

`alpha_engine/smart_picks_engine.py`, immediately before it writes `smart_picks.json`:

```python
_prov_emit_picks(output.get("picks") or [], default_source="smart_picks_engine",
                 label="PROVENANCE/smart_picks")
```

`source_system` is stamped `smart_picks_engine`, so ledger rows from the two paths are
distinguishable rather than pooled.

### 3. The scanner migrated to the same hook

The inline mapping in `production_scanner.py` section 6y is gone; it now calls the
shared hook with the same fail-safe wrapper. One implementation, not two copies that
drift. Import handles both invocation styles
(`from alpha_engine.provenance_hook import ...` with a bare-module fallback), verified
both ways.

## Emit-coverage survey (the honest picture)

| path | emits? |
|---|---|
| `alpha_engine/production_scanner.py` | **yes** (migrated to the shared hook) |
| `alpha_engine/smart_picks_engine.py` | **yes** (new callsite) |
| `alpha_engine/*` producers that write their own pick files — `crypto_smart_picks.py`, `prediction_market_consensus.py`, `pm_consensus_overlay.py`, `consensus_tier.py`, `ml_engine_v2.py`, `elite_scorer.py`, `hybrid_strategies.py`, `proven_portfolio.py`, `forex_strategy_harness.py`, `bond_strategy_harness.py`, `bitget_scraper.py`, `bybit_scraper.py`, `copy_trader_analyzer.py`, `etherscan_whale_tracker.py`, … | **no** |
| `copy_trader_intel/`, `ml_consensus/`, `prediction_market_agents/`, `baby_strategies/` | **no** |
| `verified_strategies/paper_pilot/*` | **no** |

**2 of roughly 20 identified producers emit.** This is a survey of `alpha_engine/` and
the three sibling pick-producing packages by grep for the hook and for the main pick
output filenames — not an exhaustive audit of 20K files. The count is directional and
is stated as such rather than as a precise coverage percentage.

What it means: two callsites materially widen coverage, but they do **not** close it.
Any future claim of the form "N% of picks are forward-creditable" has to be checked
against `reports/provenance/reconciliation.json`, not against the number of hooks.

## Verification

```
python3 -m pytest tests/test_provenance_hook.py -q
  20 passed
```

| test class | what it pins |
|---|---|
| `TestMapping` | both field-name conventions map; missing entry/TP/SL refused; side must be LONG/SHORT; zero/negative levels refused |
| `TestLedgerWrite` | **a pick from the new callsite produces a valid hash chain** (`verify().ok is True`, seq 1..2); the two callsites are distinguishable by `source_system`; tampering after a hook write is detected; unusable picks are dropped, not zero-filled |
| `TestFailSafe` | `None`, `[]`, a bare string, and an unwritable path all return `([], [])` without raising |
| `TestNoCreatedAtEscapes` | a caller-supplied `created_at` does not reach the ledger |

Also verified: `production_scanner.py` and `smart_picks_engine.py` both compile; the
hook imports as a package *and* as a bare module.

## CI

`provenance-verify.yml` push paths now include
`alpha_engine/provenance_hook.py` and `tools/provenance_reconcile.py`. The two large
producer files are deliberately **not** in the path list — they do not affect the
ledger's correctness, only its coverage, and adding an actively-edited 7K-line scanner
would churn the workflow's status commit on every unrelated change.

## What is still missing

The remaining non-emitting producers above. Each one is a place where a real pick can
be born and never be credited. Closing them is mechanical (call `emit_picks`) but must
be done per path with its own field mapping checked — which is exactly why the shared
hook exists.

Zero capital sanctioned. Not investment advice.
