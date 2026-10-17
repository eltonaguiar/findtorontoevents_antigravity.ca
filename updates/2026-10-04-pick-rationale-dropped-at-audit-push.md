# Pick rationale was dropped at the audit-push step — `/audit` tooltips had nothing to show

**Date:** 2026-10-04
**Scope:** `alpha_engine/audit_push.py`, `breakout_arena/audit_push.py`,
`coinglass_strategies/audit_push.py`, `crypto_ml_edge/audit_push.py`,
`crypto_signal_engine/audit_push.py`, `KIMI_RISEOFTHECLAW/audit_push.py`,
`mercury2/audit_push.py`, `ml_battleground/audit_push.py`,
`predictions/audit_push.py`, `signal_aggregator/audit_push.py`
**New:** `audit_trail/pick_reason.py`, `tests/test_audit_push_reason_passthrough.py`
**Status:** fixed; verified by test + against the live production pick file

---

## Symptom

Every pick on `/audit` showed an empty rationale. The row tooltip already
implements a **"Why now:"** block, but for picks coming from the ten
`*_audit_push.py` emitters the text was blank — the pick was there, the
justification was not.

Requested fix: *"double-check today's picks and ensure there is a solid reason
for each pick properly documented in a tooltip and perhaps stored so we can
retrieve from our database."*

## Investigation (evidence, not assumption)

Live DB, 2026-10-04 (`ejaguiar1_stocks`, read-only):

| Check | Result |
|---|---|
| Picks recorded today | 30 (all `source_system='AlphaEngine'`, `created_by='aggregator'`) |
| `JSON_LENGTH(at_raw_picks.raw_payload)` | **8 for all 30** |
| Rationale-ish key anywhere in those payloads | **0 / 30** |
| Payload keys | `symbol, strategy, direction, stop_loss, timestamp, confidence, entry_price, take_profit` |

But the rationale existed upstream. `alpha_engine/data/active_picks.json` (the
file the emitters read) carries **~200 fields per pick**, including a populated
`reason`, e.g.:

> `"Residual momentum #2: beta=1.28, residual_7d=-2.3%, residual_14d=27.9%, RSI=64. Blitz et al. (2011 JFE): pure alpha after beta removal."`

25 of the 37 picks dated ≥ 2026-10-01 had a non-empty `reason`.

## Root cause

Every emitter's `normalize()` **rebuilt the pick dict from scratch** with a
fixed 8-key literal:

```python
def normalize(p):
    return {
        "symbol": ..., "direction": ..., "entry_price": ..., "take_profit": ...,
        "stop_loss": ..., "confidence": ..., "strategy": ..., "timestamp": ...,
    }   # <-- reason (and ~192 other fields) discarded here
```

`record_raw_pick(source, normalize(pick), run_id)` then persists **exactly the
dict it is handed** into `at_raw_picks.raw_payload`
(`audit_trail/recorder.py` → `json.dumps(pick)`). So the rationale was thrown
away one hop before storage.

Measured scope — **all ten emitters had the same defect**:

```
KIMI_RISEOFTHECLAW/audit_push.py     normalize_keys=8   reason=NO
alpha_engine/audit_push.py           normalize_keys=8   reason=NO
breakout_arena/audit_push.py         normalize_keys=9   reason=NO
coinglass_strategies/audit_push.py   normalize_keys=10  reason=NO
crypto_ml_edge/audit_push.py         normalize_keys=8   reason=NO
crypto_signal_engine/audit_push.py   normalize_keys=8   reason=NO
mercury2/audit_push.py               normalize_keys=8   reason=NO
ml_battleground/audit_push.py        normalize_keys=8   reason=NO
predictions/audit_push.py            normalize_keys=10  reason=NO
signal_aggregator/audit_push.py      normalize_keys=9   reason=NO
```

## Fix

New shared helper **`audit_trail/pick_reason.py`**:

- `extract_reason(pick)` — walks `reason → signal_reason → entry_reason →
  raw_reason → reasoning → confluence_reason → notes`, then one level into
  `extra` / `audit` / `signal` / `metadata`. Truncates to 600 chars.
- `with_pick_reason(normalized, pick)` — additively copies the reason plus the
  structural evidence the tooltip renders (`confluence_strategies`,
  `source_strategies`, `concept_family`, `antigravity_tooltip`).

Each of the ten `normalize()` functions now ends with:

```python
    out = { ...existing 8 keys... }
    # Keep the emitter's rationale so it survives into at_raw_picks.raw_payload
    # and the /audit "Why now:" tooltip. See audit_trail/pick_reason.py.
    try:
        from audit_trail.pick_reason import with_pick_reason
        return with_pick_reason(out, p)
    except Exception:  # fail-open: never break the audit push over a rationale
        return out
```

Design notes:

- **Fail-open.** A rationale helper must never be able to break an emitter's
  audit push, so the import + call sit inside `try/except Exception`.
- **Additive only.** An existing non-empty value on `normalized` always wins.
- **Bounded.** 600-char cap keeps `raw_payload` small; the sibling insert path
  (`sync_all_picks_to_mysql._safe_json`) truncates at 4000 chars, so this stays
  well inside it.
- **`antigravity_tooltip` is deliberately NOT a reason.** It is a safety /
  protocol note ("Safe Trading Protocol: Under Threshold (REJECTED for Real
  Money)"), not an entry rationale, and `/audit` renders it in its own
  "Antigravity safety" row. It is passed through as evidence instead.

## Verification

**1. Controlled experiment (proves the bug and the fix).** The same test file was
run against the pre-fix and post-fix normalizers:

| Code under test | Result |
|---|---|
| Pre-fix (`git show HEAD:...`, `with_pick_reason` refs = 0) | **10 failed** — all ten emitters drop the reason |
| Post-fix | **53 passed** |

Pre-fix failure message, one per emitter:

```
E  AssertionError: signal_aggregator.normalize() dropped the rationale — at_raw_picks.raw_payload
   will carry no 'reason' and the /audit tooltip will be empty
E  assert None == 'Residual momentum #2: beta=1.28, ...'
```

**2. Real production file.** `alpha_engine/audit_push.normalize()` run over the
actual `alpha_engine/data/active_picks.json` (45 picks):

| Metric | Before | After |
|---|---|---|
| Picks with a rationale, dated ≥ 2026-10-01 | 0 / 37 in DB | **26 / 37** |
| Carrying the antigravity safety note | 0 | 21 / 37 |
| `raw_payload` size | 8 keys | 9–11 keys, median **319 bytes**, max 584 |

**3. No collateral damage.** All ten emitter modules import cleanly; syntax
checked with `py_compile`.

```bash
python3 -m pytest tests/test_audit_push_reason_passthrough.py -q
# 53 passed
```

## What this does and does NOT fix

**Fixes:** the rationale is now **persisted and retrievable from the database**
(`at_raw_picks.raw_payload.reason`), which was 0/30 for today's picks. This is
the durable record — the `active_picks.json` files only retain *active* picks,
so the DB is the only place a closed pick's justification survives.

**Does not, on its own, change the tooltip.** `/audit`'s payload is built by
`audit_trail/dashboard_generator.py::_normalize_pick()`, which reads the
**source JSON files**, not `at_raw_picks.raw_payload`. That path already works:
78% of live `picks.active` (15/19) carry a reason today.

### Remaining known gaps (follow-up work, not covered here)

1. **Sources that never emit a prose reason.** `stocksunify2` — dominant in the
   "Recent Closed Picks" table, 21 payload keys, **0/13 rows** have any
   reason/rationale/notes/description, and upstream
   `STOCKSUNIFY/data/daily-stocks.json` has only 9 keys. It *does* carry
   structured evidence (`metrics`: `technicalScore` / `volumeScore` /
   `fundamentalScore` / `regimeScore`; plus `indicators`, `all_algorithms`) from
   which a reason could be synthesised.
2. **11 / 37 AlphaEngine picks** have no upstream `reason` at all —
   `regime_accumulation`, `regime_mild_bull`, `regime_mild_bear`,
   `regime_strong_bear`, `luxalgo_confluence`, `rapid_momentum_filter_mut`.
   These emit only an `antigravity_tooltip`.
3. **`picks.active_raw`** is 25% (1013/3939) reason coverage; the gap is
   dominated by `stocksunify2` per (1).

None of these should be papered over by inventing a rationale — either the
emitter writes one, or it is derived from the structured fields it already
produces, and labelled as derived.

## Files

| File | Change |
|---|---|
| `audit_trail/pick_reason.py` | **new** — shared rationale passthrough |
| `tests/test_audit_push_reason_passthrough.py` | **new** — 53 regression tests |
| the ten `*/audit_push.py` | `return {...}` → `out = {...}` + fail-open `with_pick_reason(out, p)` |
