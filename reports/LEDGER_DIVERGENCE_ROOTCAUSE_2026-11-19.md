# /audit vs /audit3 ledger divergence — root cause and fix

**Author:** Buffy · **Date:** 2026-11-19 · **Status:** diagnosed, guard added, owner action required

## The claim

The two surfaces disagree by 11 rows. It is **not** a data conflict, not corruption, and
**not** an edge change. It is a **publish-lag ordering bug**: `/audit3` renders a build
109 minutes newer than `/audit`, and the only rows that differ are the picks that resolved
in that window.

## Measurements

| | `/audit/data/audit3_ledger.json` | `/audit3/audit3_ledger.json` |
|---|---|---|
| bytes | 665,028 | 665,250 |
| `generated_at` | 2026-11-19T21:02:25Z | 2026-11-19T22:47:15Z |
| `source_generated_at` | 2026-11-19T**20:05:51**Z | 2026-11-19T**21:55:00**Z |
| `summary.n_rows` | 8,621 | 8,632 |
| `denylist_hits` block | **absent** | present |

Source build gap: **109 minutes**. Surface publish gap: **105 minutes**.

## The 11 rows, accounted for exactly

| class | /audit n | /audit3 n | Δ |
|---|---:|---:|---:|
| CRYPTO | 6,749 | 6,757 | **+8** |
| EQUITY | 941 | 942 | **+1** |
| ETF | 588 | 590 | **+2** |
| FOREX | 258 | 258 | 0 |
| COMMODITY | 46 | 46 | 0 |
| BOND | 35 | 35 | 0 |
| FUTURES | 4 | 4 | 0 |
| **total** | **8,621** | **8,632** | **+11** |

8 + 1 + 2 = 11. There is no missing row, no phantom row, and no disagreed value — the
older build simply had not yet ingested eleven resolutions.

## Why this matters less than it looks — and more

**Less:** every class verdict is **identical** on both surfaces — CRYPTO KILL, EQUITY
WEAK, ETF WEAK, FOREX WEAK, COMMODITY KILL, BOND WEAK, FUTURES INSUFFICIENT_N. So the
divergence does not change a single trading decision. Nobody was misled about an edge.

**More:** a surface that silently serves a 105-minute-old build is exactly the failure
class this repo has been burned by before. The number on screen is not the number in the
database, and nothing said so. If the deploy order slips further during a market move,
the displayed verdicts *will* diverge. Yesterday's cosmetic lag is tomorrow's wrong KILL.

The structural tell: `/audit3`'s payload carries a `denylist_hits` block that `/audit`'s
does not. That is a schema-level difference, so the two surfaces are not merely stale
relative to each other — they are produced by **different generator revisions**.

## Root cause

Two independent publish steps write two independent files:

- `tools/deploy_audit_files.py` maps sources to `/findtorontoevents.ca/audit/data/…`
  and has **no `/audit3/` target** at all (verified: every mapping line references
  `/audit/data/` only).
- `audit3-ledger.yml` publishes the `/audit3/` copy on its own schedule.

So `/audit3` is refreshed by the workflow that generates the ledger, while `/audit` gets
whatever the deploy step last copied. They are not synchronized by construction — only by
luck of timing, and luck ran out by 109 minutes.

## Fix

**Structural (owner action, one line of ordering):** publish both surfaces from the single
artifact produced by the ledger build — i.e. have the deploy step copy the freshly built
`audit3_ledger.json` to *both* targets in the same job, or have `/audit` read the `/audit3`
path directly and delete its own copy. One artifact, two views. Not two artifacts.

I am **not** making this change myself: `audit-dashboard.yml` is one of the pre-registered
paths this fleet agreed not to edit unattended, and a deploy-order change affects every
surface at once. It belongs to whoever owns the deploy pipeline.

**Guard (shipped here):** `.github/workflows/surface-parity.yml` runs
`tools/assert_surface_parity.py` hourly and fails on RED. Exit codes are 0 GREEN,
1 YELLOW, 2 RED, and a deliberate divergence can be declared with
`--allow-rows-diff N --why "<reason>"` rather than discovered. The gate is how this stops
being invisible.

## Verify it yourself

```bash
curl -s https://findtorontoevents.ca/audit/data/audit3_ledger.json | python3 -c \
  'import json,sys; d=json.load(sys.stdin); print(d["source_generated_at"], d["summary"]["n_rows"])'
curl -s https://findtorontoevents.ca/audit3/audit3_ledger.json | python3 -c \
  'import json,sys; d=json.load(sys.stdin); print(d["source_generated_at"], d["summary"]["n_rows"])'
```

If the two `source_generated_at` values are more than one build cycle apart, the pipeline
is serving two different ledgers again.
