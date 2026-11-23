# Scorecard `--strict`: one definition of the provenance gate, and it now fails the right things

**Date:** 2026-11-22
**Files:** `tools/weekly_scorecard.py`, `tools/provenance_resolver.py`
**Ledger item:** T7

---

## The problem: two definitions of one judgement

`tools/weekly_scorecard.py --strict` is the weekly gate. It had its own provenance
rule, written inline:

```python
if pf_ is not None and pf_ < 95:
    alerts.append(f"pct_forward is {pf_:.1f}% - picks are not being resolved ...")
```

Meanwhile `tools/provenance_resolver.py --gate` (the CI gate, blocking since today)
had a stricter, better-reasoned rule with a minimum-n guard and a starvation check.

Two implementations of one judgement is how a threshold drifts apart: adjust one and
the other silently disagrees. Worse, they disagreed in **both** directions, and both
of the errors mattered.

## The fix: extract the judgement, import it

`gate_problems(st, picks, res) -> (problems, verdict)` is now a **pure function** in
`tools/provenance_resolver.py` — no I/O, no printing. `cmd_gate()` calls it, and the
scorecard imports it. There is exactly one definition.

If the import fails the scorecard says so (`provenance gate NOT enforced this run`)
rather than quietly falling back to an invented rule.

## What actually changed, measured against the old logic

Five synthetic regimes, old rule vs new gate:

| case | OLD `--strict` | NEW gate | |
|---|---|---|---|
| A · ledger empty | pass | pass | agree |
| B · 5 picks, 5 resolved, **0% forward** | **FAIL** (1 alert) | **pass** | **fixed** |
| C · 25 picks, 25 resolved, 50% forward | FAIL | FAIL | agree |
| D · 25 picks, **0 resolved, oldest 70d** | **pass** (0 alerts) | **FAIL** | **fixed** |
| E · 5 resolved, chain edited | FAIL | FAIL | agree |

### Case B — the old rule fired on noise

A 5-pick week at 0% forward tripped `--strict`, because `0 < 95`. But `pct_forward`
over 5 observations is not a measurement; it is a coin landing once. The CI gate
already knew this (`MIN_RESOLVED = 20`). A gate that fires before there is data gets
switched off within a week, and then it protects nothing.

### Case D — the old rule was blind to the failure that actually matters

25 picks pending with the oldest **70 days** old, and **nothing resolved at all** —
the old scorecard reported **0 alerts**. It never looked at pending picks. That is
precisely the silent no-op this whole ledger exists to catch:

> An instrument that measures nothing looks identical to a measurement of nothing.

The new gate fails it explicitly: *"resolver starved: 25 pick(s) pending, oldest 70d
(limit 45d + 7d grace) — no market data path or a broken symbol map."*

So the change is not "stricter" or "looser". It is **correctly discriminating**:
lenient where the number is not yet meaningful, strict where it is meaningful and bad.

## Thresholds are now shared, not duplicated

`PCT_FORWARD_MIN = 95.0`, `MIN_RESOLVED = 20`, `MAX_DAYS = 45`,
`STARVE_GRACE_DAYS = 7` live in `tools/provenance_resolver.py` only.

## Verification

```
python3 tools/provenance_resolver.py --selftest   -> ALL RESOLVER SELFTESTS PASSED
python3 tools/provenance_resolver.py --gate       -> GATE: PASS (no picks emitted
                                                     yet -- nothing to measure)
six gate regimes re-run after the refactor        -> REGIMES: PASS
python3 tools/weekly_scorecard.py --strict        -> exit 0
   | Provenance ledger     | EMPTY   | 0 records; chain intact; forward-creditable 0
   | Provenance resolution | NO DATA | 0 resolved picks yet - no statistic can ...
   - provenance gate: GATE: PASS (no picks emitted yet -- nothing to measure)
```

The scorecard's current state is unchanged (`exit 0`) because the ledger is still
empty — the difference only shows up once there is data to judge, which is the point.

Zero capital sanctioned. Not investment advice.
