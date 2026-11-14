# GitHub Actions fixes

**Measured this session** (not estimated) over `.github/workflows/*.yml`:

| Metric | Count | Share |
|---|---:|---:|
| workflow files | **360** | — |
| with `concurrency:` | 161 | 45% — **199 without** |
| with `timeout-minutes:` | 271 | 75% — **89 without** |
| with a `push:` trigger | **39** | 11% |
| with `workflow_dispatch:` | 354 | 98% |
| mentioning `[skip ci]` | 231 | 64% |
| distinct cron schedules | **187** | — |

**Schedule collisions** are structural, not incidental:

| bucket | workflows |
|---|---:|
| minute 0, hour 6 | 20 |
| minute 0, every 4th hour | 17 |
| minute 0, every 2nd hour | 15 |
| minute 0, every 6th hour | 13 |
| every 30 minutes | 12 |
| minute 0, hourly | 11 |

Twenty workflows start at the same moment. On a shared runner pool that is a queue, and queue
saturation is what produced the 2026-05-19 `audit-dashboard` cancel-cascade that forced removal of its
`push:` trigger. Nothing now prevents the same failure in the other 359.

---

## A1 — Add `concurrency:` to all 199 workflows missing it

**Why:** without a concurrency group, two runs of the same workflow overlap, both write the same
generated JSON, and the later commit silently reverts the earlier one. This is the documented
`feedback-silent-file-revert-pattern` hazard, automated.

**Do:** `concurrency: {group: ${{ github.workflow }}-${{ github.ref }}, cancel-in-progress: false}`
for data-writing workflows; `cancel-in-progress: true` only for check-only workflows.

**Acceptance:** `grep -L "concurrency:" .github/workflows/*.yml` returns only workflows that are pure
`workflow_dispatch` one-shots with no data commit.

---

## A2 — Add `timeout-minutes:` to all 89 workflows missing it

**Why:** a hung job holds a runner until GitHub's 6-hour ceiling. With 360 workflows that is how a
queue becomes a backlog, and a backlog is indistinguishable from an outage.

**Do:** `timeout-minutes` = 3× the workflow's observed p95 runtime (read from run history), never
above 60 except the known-long audit pipeline.

**Acceptance:** no workflow can occupy a runner for more than 90 minutes.

---

## A3 — De-collide the cron schedule

**Why:** 20 workflows at `0 6 * * *` and 17 at `0 */4 * * *` means burst contention, retries, and
intermittent stalls that look like flaky code.

**Do:** deterministically spread minutes: assign each workflow a distinct minute derived from its
filename hash, keeping its hour pattern. Keep the audit-dashboard at `:10` (documented contract).

**Acceptance:** ≤ 3 workflows share any (minute, hour) bucket; `0 6 * * *` reduced from 20 to ≤ 3.

---

## A4 — Audit the 39 `push:` triggers for cascade risk

**Why:** the one push trigger we know about had to be removed for a real incident. The other 38 were
never reviewed.

**Do:** for each, confirm it (a) does not commit generated data back to the same branch, or (b) if it
does, carries `[skip ci]` and a narrow `paths:` filter. Convert data-commit workflows to cron +
`workflow_dispatch`.

**Acceptance:** no workflow both writes a commit and triggers on `push` without `[skip ci]` **and** a
`paths:` allowlist.

---

## A5 — Freshness gates as failing CI steps, not warnings

**Why:** B9 — `fetch_prices.php` has 404'd since 2026-04-29, `signal_outcomes` is ~80 days stale, and
one peer dataset is 172 days stale, while the pipelines kept reporting success.

**Do:** each data workflow gains a final step that asserts its output's max timestamp is within TTL
(crypto 6h, equity 24h, COT 9 days, dashboard 2h) and **fails** otherwise. Extend
`tools/db_freshness_check.py` to these three feeds; the hourly guardian already has the scaffolding.

**Acceptance:** deliberately aging an input file turns the workflow red within one cycle.

---

## A6 — Run the cost gate and money-ready screener as CI steps

**Why:** `sizing_allowed: false` for all nine classes never blocked anything (B12).

**Do:** after each ledger refresh, run
`python3 tools/per_class_cost_gate.py --build --input <payload>` and fail the job if a class that
*previously* passed now fails (regression detection), plus publish the index as an artifact.

**Acceptance:** a simulated class regression (mean PnL drop) fails the job with a diff in the log.

---

## A7 — Enforce the trial counter

**Why:** B8 — 170 ledgers, 4 pass at 95% vs 8.5 expected by chance; 658 trials → 32.9 expected false
positives. Nothing counts trials.

**Do:** a `trials.json` registry incremented by any workflow that tests a hypothesis; the promotion
step reads it and applies BH-FDR at q=0.10 across the recorded count; no promotion without a trial ID.

**Acceptance:** a PR that promotes a strategy without a trial ID fails.

---

## A8 — Stop duplicate pipeline ownership

**Why:** 360 workflows almost certainly contain overlaps (multiple scanners, multiple resolvers,
multiple dashboard builders). `final_v2/finpredict-v2/01_audit/sub/A_workflow_matrix.csv` is the
starting map.

**Do:** classify each workflow as `producer | consumer | report-only | dead`. Delete or archive dead
ones (keep the file, disable the schedule). One owner per output artifact.

**Acceptance:** every generated file under `audit_dashboard/data/`, `data/`, `genome/data/` has
exactly one producing workflow in the matrix.

---

## A9 — Pin action versions and cut secret surface

**Why:** mixed `@v4`/`@v5`/unpinned usage across 360 files; each `secrets.*` reference is blast radius.

**Do:** pin to commit SHAs for third-party actions; one shared `env:` block per workflow rather than
inline secret expansion; scope `DB_PASS_STOCKS` only to jobs that write.

**Acceptance:** a secret referenced outside its owning job list fails review; no floating tags in
non-GitHub actions.

---

## A10 — Fail fast on conflict markers and unit drift

**Why:** `.github/scripts/assert_no_conflict_markers.sh` and `safe_push.sh` exist (per AGENTS.md) but
must run **before** any commit step in every writing workflow; and B6's unit bug means a mixed-unit
file can be committed silently.

**Do:** prepend both checks to every workflow that commits; add a unit assertion (`|pnl| > 100` requires
an explicit `unit` field).

**Acceptance:** a deliberately planted conflict marker stops the run before the commit step.

---

## A11 — Give the nightly pick-funnel a stale-source alarm

**Why:** `pick-funnel-nightly.yml` fetches `dashboard_data.json` from the live site. If the deploy
silently stops, the funnel keeps producing confident output from stale input.

**Do:** assert `generated_at` of the fetched payload is < 26h old; fail otherwise and open an issue.

**Acceptance:** pointing it at a frozen file fails the job.

---

## A12 — One dashboard deploy path

**Why:** AGENTS.md documents three sites plus `tools/deploy_audit_files.py` plus the per-site HTML page
lists. Multiple deploy paths are how the 2026-04-27 thumbnail outage happened (a stripped shell
replaced the live file).

**Do:** single deploy workflow calling one script; a post-deploy smoke test asserting key markers exist
in the fetched live HTML (e.g. the event-grid chunk reference and the audit payload size > 1MB).

**Acceptance:** a deploy that ships a page missing the known markers fails and does not report success.

---

## Order of work

1. **A1, A2** (mechanical, no behaviour change, removes the outage class)
2. **A5, A10, A11** (makes everything else trustworthy — a green run must mean something)
3. **A3, A4** (contention and cascade)
4. **A6, A7** (gates that can actually block)
5. **A8, A9, A12** (consolidation; do last, largest blast radius)
