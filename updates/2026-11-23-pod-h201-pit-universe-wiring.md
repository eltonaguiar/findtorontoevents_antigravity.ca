# H-201 pod: point-in-time universe wired in, clock restarted under archive

**Date:** 2026-11-23
**Files:** `tools/pod_forward.py`, `reports/pit_equity_universe_20261122.json`,
`reports/pods/forward/` (rows, anchor, archive), `.github/workflows/pod-h201-forward-clock.yml`
**Status:** verified; clock now structurally capable of a verdict it could never reach before

## What was broken

`tools/pod_forward.py` recorded real forward observations, but it read its universe from
`UNIVERSES["EQUITY"]` in `tools/per_class_edge_harness.py` — **10 mega-caps**. The pod spec
(`reports/pods/pod_h201_xsmom_2026-11-22.json`) requires
`universe.minimum_names: 22`, and the recorder enforced that faithfully: every run set
`universe_ok: false`, `universe_block: "universe_below_minimum_names"`, and barred itself from
ever returning a PASS.

So the pod had a defined arithmetic path to a verdict — 20 days, 10 trades, 77 days for a full
read — and no possible way to walk it. It could only ever return a KILL. Recording forward rows
into a clock that is unable to conclude is bookkeeping, not a test.

The 44-name point-in-time artifact (`reports/pit_equity_universe_20261122.json`) fixed the count
bar but nothing read it, so building it changed no verdict.

## What changed

1. **`read_universe(path)`** — prefers the audited PIT artifact, falls back to
   `UNIVERSES["EQUITY"]`. Returns the names *and* a description of the universe:
   `source`, `survivorship_status`, `survivorship_direction`, `label`. The description travels
   into every summary so a consumer cannot see `universe_names: 44` without also seeing
   `PARTIAL_NON_DELISTING_AWARE`.
2. **`load_closes(names)` / `load_opens(names)`** — take the chosen universe instead of reaching
   for the global. Both now raise a clear `SystemExit` if no series load, rather than returning
   an empty frame that would fail later and confusingly.
3. **Universe pinned at the anchor, with a refusal path.** `_anchor.json` already stored the
   universe; the tool now *checks* it. If the requested universe differs from the pinned one and
   `--switch-universe` is not passed, the run aborts with the pinned count, the pinned timestamp
   and the requested source. A clock whose basket changes while `n_days` keeps counting is
   describing two portfolios in one running total — the same defect class as a status that
   ignores its own statistics.
4. **`--switch-universe` archives and restarts.** Moves the running `.jsonl` and `_anchor.json`
   into `forward/archive_pre_switch_<UTC>/`, writes a `switch.json` recording from/to universe,
   both anchors, the new survivorship status, and *why*, then re-anchors on the new universe.
   The change is visible in history instead of being a diff nobody notices.
5. **Verdict cap renamed.** On a flagged universe the top rung is now
   `CANDIDATE_SURVIVORSHIP_FLAGGED`, not the clean-sounding
   `CANDIDATE_NEEDS_SECOND_UNIVERSE`. Same admissibility, honest label. A KILL remains
   admissible for the original reason: survivorship inflates returns, so failing to clear zero
   *despite* the inflation is the stronger result.
6. **`.github/workflows/pod-h201-forward-clock.yml`** — the clock had no scheduler. The existing
   `premia-pod-forward-clock.yml` is a stub whose run step is
   `echo "Forward clock not yet implemented (Phase 3)."` with the real call commented out.

## How it was verified

| Check | Command | Result |
|---|---|---|
| Compiles | `python3 -c "import py_compile; ..."` | `py_compile OK` |
| Refuses silent swap | `python3 tools/pod_forward.py --dry-run` | **RC=1**, message names pinned 10 vs requested 44 and the `--switch-universe` remedy |
| Archived restart | `python3 tools/pod_forward.py --switch-universe` | **RC=0**, `archived prior clock to .../archive_pre_switch_20261123T001739Z`, anchor `2026-10-30`, 15 sessions, 15 new rows |
| Universe fields | same run | `universe_names: 44`, `universe_ok: true`, `universe_source: PIT_ARTIFACT:pit_equity_universe_20261122.json`, `universe_survivorship_status: PARTIAL_NON_DELISTING_AWARE` |
| Verdict honesty | same run | `NO_VERDICT_TOO_FEW_DAYS_FOR_INFERENCE` — 15 days is below the 20-day gate, so the universe change did **not** manufacture a result |
| Idempotent | `python3 tools/pod_forward.py --dry-run` | **RC=0**, `new 0` — no duplicate rows, no refusal, anchor stable |
| Workflow parses | `yaml.safe_load`, triggers `['schedule','workflow_dispatch']`, cron `20 22 * * *` | all six steps present |

## Limits, stated plainly

- **The universe is still survivorship-contaminated.** 44 names clear the count bar; they are
  today's survivors. `PARTIAL_NON_DELISTING_AWARE`, direction UPWARD. This changes which verdict
  is *nameable*, not what is *true*. A real PASS needs CRSP/Norgate/Polygon; none has a key here.
- **The restart discards 15 days of rows.** They were structurally incapable of producing a
  verdict (10 < 22), so nothing admissible was lost, and they are preserved in the archive
  directory with the reason recorded.
- **n_days stayed at 15** because the new anchor (2026-10-30) has the same 15 sessions available.
  The switch changed the universe, not the elapsed time.
- **The 44-name set is equities *and* ETFs** (GLD, TLT, SHY, SPY, QQQ …). The spec's rule reads
  "liquid US equities/ETFs" and its top-3 6-month momentum can therefore pick a bond ETF. That is
  compliant with the spec as written and is worth watching when the first baskets print, not
  worth re-specifying mid-clock.
- **The workflow only runs once pushed and merged.** Not pushed from here.
- **Cost basis is still 11 bp/side assumed** (10 slip + 1 commission), while the measured equity
  cost is 6.04 bp/side / 12.07 round-trip. The assumption is conservative, so it cannot flatter a
  pass; it is still an assumption, and `COMMISSION_UNKNOWN` fleet-wide means the 1 bp is not
  measured either.
- **Nothing here re-runs the backtest.** M-107 forbids re-cutting this hypothesis; the pod exists
  to add forward observations without adding trials to the family.
