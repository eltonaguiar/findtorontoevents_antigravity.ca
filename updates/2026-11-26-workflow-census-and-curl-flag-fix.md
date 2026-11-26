# 2026-11-26 — Workflow census + local validation sweep, and the `--retry-on-http-error` bug

Asked to: count the unique workflows, check the ones not yet checked, "run each unique
workflow once locally", and log every failure/warning/incorrect-data finding.

## 1. Census

`.github/workflows/` holds **406 files**:

| Kind | Count |
|------|-------|
| Active workflow files (`.yml`) | **388** |
| Disabled (`.yml.disabled`) | 8 |
| Draft (`.yml.draft`) | 1 |
| Retired (`.yml.retired`) | 6 |
| Stray markdown | 4 |

**Unique workflows: 387** — 388 files, but one pair shares a `name:` value:

- `edge-stability-daily.yml` and `edge-stability-refresh.yml` are both named
  `Edge stability refresh`.

The two are intentionally serialized through the shared `concurrency.group:
edge-stability-shared`, but they emit the same JSONs and the duplicate name makes the
Actions UI list two indistinguishable entries (you cannot tell which one ran from the
run list). Not changed here — consolidating them is a behaviour change (the `-daily`
variant has no FTP deploy step) and needs its own decision; flagged as a follow-up.

## 2. What "run each workflow once locally" can and cannot mean

Running 388 workflows means `act` + Docker + every repo secret + hours of wall clock, and
most of them would fail for missing secrets rather than for anything real. Instead every
active workflow was validated with the checks that actually catch defects before a run:

1. **YAML parse of all 388** — 388/388 parse, 0 failures, 0 empty `jobs:` blocks.
2. **actionlint 1.7.7 over all 388** — 1,468 findings, 363 `shellcheck` (style/info, all
   pre-existing) and 4 `syntax-check`.
3. **Referenced-script existence** — 920 `python|python3|bash|sh|node <file>` invocations
   resolved against `origin/main` with `cd`/`working-directory` tracking. A naïve version
   of this check reports 114 "missing" files; almost all are false positives from a `cd`
   into a subdirectory, so the check is `cd`-aware.
4. **Live rerun of the failing command** (see §3) — the one class of failure that could be
   reproduced from this machine.

### The 4 `syntax-check` findings are stale linter, not broken workflows

`crypto-ohlcv-refresh.yml`, `daily-prices-yf-refresh.yml`, `db-freshness-guardian.yml`,
`stocks-daily.yml` all use `concurrency.queue: max`. Local actionlint 1.7.7 predates
actionlint commit `644076a` (2026-05-20) which added the key; GitHub shipped
`concurrency.queue` in May 2026 (`queue: single|max`). Proof it is valid: all four of
those workflows have recent **successful schedule runs**
(`crypto-ohlcv-refresh` 2026-11-25T20:55Z, `daily-prices-yf-refresh` 2026-11-25T08:36Z,
`db-freshness-guardian` 2026-11-26T00:36Z, `stocks-daily` 2026-11-25T21:45Z). No change.

## 3. The real bug: `--retry-on-http-error` does not exist in curl

Three workflows on `main` fetched data with:

```bash
curl -fsS --max-time 180 --retry 2 --retry-delay 5 --retry-all-errors \
     --retry-on-http-error 403,429,500,502,503 ...
```

`--retry-on-http-error` is not a curl option in **any** version (the documented knobs are
`--retry`, `--retry-delay`, `--retry-all-errors`, `--retry-connrefused`,
`--retry-max-time`). curl exits **2 before opening a connection**:

```
$ curl --retry-on-http-error 403 https://example.com
curl: option --retry-on-http-error: is unknown
curl: try 'curl --help' or 'curl --manual' for more information
```

Every attempt aborted instantly. The `for i in 1..4` retry loop therefore slept 15/30/45/60s
and failed four times, then took the failure branch.

### Impact per workflow (evidence from Actions logs/run history)

| Workflow | Symptom | Severity |
|---|---|---|
| `claudes-test-portfolios.yml` | Both fetches fail → `dashboard_payload.json unavailable` **and** `state fetch failed — portfolios will re-bootstrap this run`. All 36 portfolios reset to $10k of notional every 30 minutes. | **Data corruption** |
| `audit3-ledger.yml` | Job `ledger` → step 3 `Fetch live closed-pick ledger` fails → **whole job fails**, steps 4–15 (ledger build, denylist assert, commit, FTP deploy) all **skipped**. Run `45730922567` (schedule, main, 2026-11-26T00:44Z) failed; `45614970785` (2026-11-25T12:33Z) failed the same way. | **Hard failure, 2 silent skips/day ago** |
| `asset-class-freshness-watchdog.yml` | All 4 attempts abort → `both data sources unreachable`; the warn-only report then runs with no input. Run 2026-11-25T13:21Z failed. | Degraded, warn-only |

The log for `45730922567` shows the loop burning 90s per origin on nothing:

```
curl: option --retry-on-http-error: is unknown
attempt 1 failed for https://findtorontoevents.ca; sleeping 10s
...
##[error]live dashboard_data.json unreachable from origin and mirror
```

### Fix

Deleted the bogus flag from all 5 call sites (3 files). `--retry-all-errors` was already
on every invocation and is what `--retry-on-http-error` was reaching for — it retries
403/429/5xx as well as transport errors. A dated comment in each file records why, so the
flag is not "helpfully" re-added.

### Verification

- `grep -rn retry-on-http-error .github/workflows/` → only the 5 explanatory comments.
- All 3 files parse (`yaml.safe_load`), actionlint reports no new findings for them.
- **The fixed command was run live** against the same URL the workflow uses:

```
curl -fsS --max-time 180 --retry 2 --retry-delay 5 --retry-all-errors -o /tmp/audit3_probe.json \
  https://findtorontoevents.ca/audit/data/dashboard_data.json
→ 27,239,184 bytes in 0.58s
→ generated_at=2026-11-25T21:53:28Z, picks.recent_closed=3500  (assert >=100 passes)
```

The workflow's own thin-data guard (`assert len(rows) >= 100`) passes on the real payload,
so `audit3-ledger` should go green on its next schedule tick.

## 4. Residual findings — logged, not changed

Missing-script references on `main` (files lost in the 2026-05-23 history strip,
INCIDENT #126). Guarded ones are already warning-only; two are unguarded but have **never
run** (dispatch-only, zero runs in the API):

| Workflow | Missing file | Behaviour |
|---|---|---|
| `deploy_bundle.yml` | `deploy_prod_bundle.py` | **Unguarded** → would hard-fail on first dispatch |
| `fast-stocks-competition.yml` | `STOCKS/competition/run_fast_competition.py` | **Unguarded** → would hard-fail on first dispatch |
| `ai-tournament-pipeline.yml` | `tools/ai_tournament/generate_diagnostics.py` | `|| echo ::warning` — green but degraded |
| `genome-daily-pipeline.yml` | `genome/dna_macd_mutations.py`, `genome/dna_pumpwatch_mutations.py` | `|| echo ::warning` — those two variants never produce picks |
| `algorithm-competition-refresh.yml`, `torontoevent-algorithm-refresh.yml` | `STOCKS/competition/run_competition.py` | `if [ -f ]` guard → documented skip |
| `sports-betting-refresh.yml` | `tools/update_custom_sports_picks.py` | `if [ -f ]` guard → UFC/Tennis/Golf picks stale |
| `cost-model-reconciliation.yml`, `hypothesis-registry-append-guard.yml`, `premia-pod-forward-clock.yml` | various | only in comments — no-op placeholders |
| `claude-gainer-tracker.yml` | `live_scanner.py` (relative) | resolves only under `claude_gainer_ml/` — runs green, verify intent |

Also noted: 9 workflow files in the local tree (`audit-review-doc-lint`,
`class-verdict-gate`, `digest-artifact-guard`, `harness-certification`, `surface-parity`,
`price-freshness-guardian`, `carry-cost-series`, `etf-spread-series`, `live-daytrade-sim`)
are **branch-only**, absent from `main`, hence `404` from the workflows API. Their
`tools/*.py` targets do not exist on `main` either — they are parked, not broken.

No workflow file references a non-existent runner label, and no workflow has an empty
`jobs:` map.
