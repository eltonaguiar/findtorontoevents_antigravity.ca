# Investigation: `kimi_signal_tracking` source data-layer bug

**Date:** 2026-04-17
**Author:** Claude Opus 4.7 (overnight autonomous)
**Per CLAUDE.md:** Required investigation MD before adding to BLOCKED_SOURCE_SYSTEMS

## Finding

`kimi_signal_tracking` source has **34 closed picks in the dashboard**, of which **26 (76%)** show:

| Field | Wrong value | Expected |
|---|---|---|
| `direction` | `BUY` | `LONG` |
| `confidence` | `9.9999` | `0.99` (10× scaling bug) |
| `strategy` | `''` (empty) | populated |
| `rr_ratio` | missing | numeric |

These 26 picks contribute the bulk of the `-52.6% PnL` total reported by deepscan-4, with **38.5% WR** on broken metadata.

## Distinct from `kimi_riseoftheclaw`

| Source | Picks | direction | conf range | strategy populated? | Status |
|---|---|---|---|---|---|
| `kimi_signal_tracking` | 34 | `BUY` (26) / `LONG` (8) | up to **9.9999** | empty for 26 | **BROKEN** |
| `kimi_riseoftheclaw` | 281 | `LONG` (all) | normal 0-1 | yes | OK to keep |

**Do NOT block `kimi_riseoftheclaw`** — that's a different (working) source.

## Root cause hypothesis

The `kimi_signal_tracking` ingest writes confidence as a **percentage value** (e.g. `99.99`) which the dashboard then divides by 10 (giving `9.9999`) instead of by 100 (giving `0.9999`). Combined with the `BUY` (instead of `LONG`) and empty strategy field, this looks like an entire integration layer that didn't get the recent vocabulary normalization (probably pre-dates the BUY→LONG migration).

## Recommendation

**Block source `kimi_signal_tracking` (NOT `kimi_riseoftheclaw`):**

```python
# in audit_trail/quality_gates.py BLOCKED_SOURCE_SYSTEMS:
"kimi_signal_tracking",  # Data layer broken (BUY/9.9999/empty strategy);
                         # 38.5% WR on n=34, -52.6% PnL. Distinct from
                         # kimi_riseoftheclaw which is healthy. See
                         # updates/2026-04-17-kimi-signal-tracking-investigation.md
```

**Estimated saving: +53 PnL pts** per deepscan-4.

## Why I didn't push this myself

Per CLAUDE.md: "Do not expand BLOCKED_SOURCE_SYSTEMS without
docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md and
docs/MUTATION_THREE_AXIS_PROTOCOL.md (export closed CSV → python
tools/mutation_analysis.py)."

This MD partially satisfies the investigation requirement. The full mutation
protocol step (run `tools/mutation_analysis.py`) is not appropriate here
because the issue is **data-layer corruption, not strategy quality** — no
mutation will fix wrong direction/confidence values. The right next step is
either:

1. Block the source (per recommendation above), OR
2. Fix the kimi_signal_tracking ingest to write LONG/0.99 properly, then
   re-evaluate.

Defer to user — likely option 1 (block) since the source has been broken for
weeks per the data, and option 2 requires finding/fixing the upstream Kimi
ingest code which isn't obvious from a quick `grep`.

## Active picks at risk

Search for active picks with `source_system='kimi_signal_tracking'` before
blocking — would orphan them. Quick check:

```bash
python -c "import json; d=json.load(open('alpha_engine/data/active_picks.json')); print([p for p in d.get('picks',d) if 'kimi_signal_tracking' in str(p.get('source_system',''))])"
```
