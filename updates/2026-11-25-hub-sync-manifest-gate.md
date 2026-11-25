# Hub Data Sync — the freshness gate asserted a property nothing could satisfy

**Date:** 2026-11-25
**Workflow:** `.github/workflows/hub-sync.yml` (`Hub Data Sync`, hourly `6 * * * *`)
**Failing run investigated:** `45719481029` (main `b66ad335`, 2026-11-25T23:12Z) — failure with no prior success.

## What was broken

The job failed on its last step:

```
hub manifest generated_at=2026-03-02T10:00:00Z age=268.6d (limit 7d)
##[error]hub manifest is 268.6 days stale
```

That step asserted `hub/data/systems_manifest.json` must be under **7 days** old. Two facts made that
unsatisfiable:

1. **Nothing in the repository writes `hub/data/systems_manifest.json`.**
   `grep -rln systems_manifest` (excluding worktree copies) returns only readers — `hub/js/consensus_engine.js`
   reads it for display. There is no generator, no exporter, no cron job that produces it. Its
   `generated_at` is a hand-maintained review stamp, not a build stamp.
2. **The file is a curated config**, not a data snapshot: `version`, `hub_metadata`, `categories` (5),
   `systems` (27), `consensus_config`, `quality_scoring`.

So the gate was red from the day it landed and could never go green except by hand-editing a date to
claim a review that did not happen. An hourly workflow that is permanently red trains everyone to
ignore it — the opposite of a gate.

The step immediately before it *did* have real signal, and it passed: `winning_combos.json` was
re-stamped `2026-11-25T23:23:14Z` by the run itself (the export works).

## What changed

Replaced `Assert the hub manifest is fresh` with `Assert hub data is fresh and well-formed`, which
gates each file on a property that can actually be violated:

**`hub/data/winning_combos.json` — the artifact this workflow regenerates hourly (hard fail):**
- file must exist and be valid JSON (a missing file means the export produced nothing)
- `updated_at` must parse and be **≤ 26 h** old (hourly cron + slack) → catches an export that stops
  re-stamping while the job still reports success
- `total_found == 0` emits a `::warning::` (the hub would have nothing to display)

**`hub/data/systems_manifest.json` — hand-curated config (hard fail on integrity, warning on age):**
- must exist and be valid JSON
- must contain `version`, `generated_at`, `categories`, `systems`
- `systems` and `categories` must be non-empty (an empty map means the hub renders nothing)
- `generated_at` must parse; if older than **180 days** it emits a `::warning::` asking for a review
  instead of failing the job

## Why this is not a weakened gate

The old check could not distinguish "hub data is stale" from "this config has not been re-reviewed" —
it failed on the latter while the former was healthy, so its output was constant and ignored. The new
checks fail on the exact conditions the job exists to detect (export produced nothing / stopped
re-stamping / manifest unusable) and keep the age of the curated file visible as a non-fatal
annotation. Nothing that used to fail for a *real* reason stopped failing.

## Verification

Extracted the step's `run:` script from the YAML and executed it directly (`bash -e`), four scenarios:

| Scenario | Expected | Observed |
|---|---|---|
| Real `hub/data/` | exit 0 | `updated_at=2026-11-25T23:23:14Z age=0.2h`, `systems=27 categories=5`, 2 warnings, **exit 0** |
| `updated_at` forced to 2026-11-01 | exit 1 | `is 599.6h stale — this run did not re-stamp it`, **exit 1** |
| `systems` emptied | exit 1 | `has an empty systems map — the hub would render nothing`, **exit 1** |
| manifest deleted | exit 1 | `systems_manifest.json is missing`, **exit 1** |

Plus: `python3 -c "yaml.safe_load(...)"` parses, `actionlint -shellcheck=` reports nothing for this
file, and shellcheck count is unchanged (base 0 → now 0).

## Follow-up surfaced (not fixed here)

`hub/data/winning_combos.json` currently has `total_found: 0` — the exporter's query
(`p_value < 0.05 AND win_rate > 0.55 AND total_trades >= 5`, `LIMIT 50`) matches no rows. The new
warning now says so out loud every hour; whether the combo table is empty or the thresholds are too
strict is a data question, not a workflow one.
