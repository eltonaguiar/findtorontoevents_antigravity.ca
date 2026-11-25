# findtorontoevents_antigravity.ca — Actions validation (main + gh-pages)

**Date:** 2026-11-25 21:30Z · **Method:** 600-run window from the Actions API (18:24–21:23Z), per-workflow
last-success/last-failure, failing step logs, plus the `gh-pages` tree fetched over git and compared
byte-for-byte with what `eltonaguiar.github.io` actually serves.

---

## 1. Headline

Last 600 runs: **546 success · 23 failure · 16 cancelled · 13 in progress · 2 pending**.
`main` carries 499 successes and all 23 failures; the remaining branches are clean.

Only **3 failures have no later success**, and all three are explainable (§3). The rest of the red is
concentrated in one workflow that is not a "failure" in the usual sense — it is a publisher that
half-works (§4).

---

## 2. What is healthy

| Workflow | State |
|---|---|
| `live_tracker.yml` | hourly SUCCESS (20:25, 19:25, 18:27…) — pushes a 191 KB Alpha Engine dashboard to `gh-pages` |
| `audit-dashboard.yml` | running on the hourly cron, publishing `/audit` |
| `hub-sync.yml` | hourly "success" — but see §5, the success is hollow |
| `deploy-bestiejob-page.yml` | last success 2026-11-19; dormant by design (manual) |
| `fix-battleground.yml` | last success 2026-11-16 (force-pushes `gh-pages` when run) |

No workflow in this repo has been silently dormant inside the 3-hour window. The long-dormant set from
the earlier cross-repo audit still stands elsewhere.

---

## 3. The three failures with no later success

**a) `QA Market Validation` (hourly, failed 19:16 and 20:16, 21:16 still running).**
Not infrastructure. It is a data-quality gate that exits 1 when the ledger has critical flags:

```
QA ledger: 183 picks, 21 flags (15 critical)
  EQUITY   n=31  blank_tp/sl=6  mismatch=12
  BOND     n=54  quar=1
```

So the gate is doing its job: **equity picks are shipping with missing or inverted TP/SL.** Fix the
emitters, not the gate. Until then this workflow is red every hour by construction.

**b) `Forward-Test New Strategies Tracker` (6-hourly, failed 00:53 / 06:48 / 12:45 / 18:45).**
Also deliberate:

```
Strategy generation is FROZEN: no new strategy may be generated while a P0 item is open.
  P0 E11: Backfill FX prices (fx_prices ends 2026-02-09)
  P0 E13: Stamp gate inputs at issue time (at_issue_* on 215/3500 rows)
  P0 E14: Kill the negative-alpha expressions (crypto LONG -0.442%/pick)
```

This is a policy gate, red on purpose until those three items close. Its file is
`forward-test-new-strategies.yml` (the similarly named `forward-test-new-strategies-tracker.yml`
returned 404 — worth knowing if anything references it).

**c) `Mirror: findtorontoevents.ca → torontoevent.net` (18:28, `530 Login authentication failed`).**
Its `SRC_PASS` is `secrets.FTP_PASS`, which was refreshed at **20:28:59Z — after** that run. Verified
the credentials independently over FTPS (listing the 50webs root succeeds). The workflow is
`state=disabled_manually`, so it will not retry on its own; when re-enabled it should pass. Re-enabling
was **not** done here because it overwrites the GoDaddy site with 50webs content — that is an owner call.

---

## 4. gh-pages: the real defect

**The site does not serve the `gh-pages` branch.** Facts:

| Fact | Value |
|---|---|
| `gh-pages` tip | `1eeeebb0bb36`, 2026-11-25 20:25:50, committed by `live_tracker.yml` |
| `gh-pages:index.html` | **191,291 bytes** — "Alpha Engine — Live Autonomous Dashboard" |
| Served `/` | **260 bytes** — `<meta http-equiv="refresh" content="0; url=./hub/">` |
| Served `/live_picks.json`, `/big_mover_widget.html`, `/bestiejob/` | **404** (all exist in the branch) |
| Served `/hub/` | 200, 168 KB, title "Trading Systems Hub" |
| `hub/` present in `gh-pages` tree? | **No** |

The 260-byte redirect is byte-identical to the heredoc in `deploy-riseoftheclaw.yml` (`_site/index.html`),
and that workflow finishes by calling `actions/upload-pages-artifact` + `actions/deploy-pages`.
So Pages is publishing **workflow artifacts**, while `live_tracker` keeps writing a dashboard branch
that nothing reads. Two publishers, two incompatible trees, one of them parasitic.

Complicating it, `GET /repos/…/pages` reports `source=gh-pages`, `build_type=legacy` while the served
bytes are an artifact deployment — the configured source and the live content disagree. That mismatch
is itself the reason this has drifted for months without anyone noticing.

**`deploy-riseoftheclaw.yml` is where the red comes from:** last 100 runs = **56 failure / 36 success /
7 cancelled**. The failure is always the same:

```
Fetching artifact metadata for "github-pages" in this workflow run
Found 0 artifact(s)
##[error]No artifacts named "github-pages" were found for this workflow run
```

`upload-pages-artifact` did not produce an artifact for those runs (the step before it also runs a
JS-syntax validation loop that can `exit 1`), yet the deploy step still executes and fails loudly.
It is scheduled twice an hour (`49,19 * * * *`), so this is ~40–50 red runs/day on its own.

---

## 5. `Hub Data Sync` is a green no-op

`hub-sync.yml` runs hourly and reports success every time. Meanwhile:

- `hub/data/systems_manifest.json` → `"generated_at": "2026-03-02T10:00:00Z"` (both on `main` **and** live).
- Last commit touching `hub/data/`: **2026-11-20** ("Sync hub data 02:19 [skip ci]").

The reasons are in the workflow:

```yaml
PYTHONPATH=. python signal_recorder/export_hub_combos.py || echo "::warning::Combo export failed"
git commit -m "Sync hub data $(date +%H:%M) [skip ci]" || echo "No changes"
```

Both failure paths are swallowed, so "success" means only that the shell reached the end. The landing
page the whole Pages site redirects to has been serving March data since March.

---

## 6. Recommended fixes (not applied — workflows are outside this agent's ownership prefixes)

1. **One publisher.** Keep `deploy-riseoftheclaw.yml` as the Pages deployer (it builds the `hub/` landing
   the site actually serves) and **delete the `peaceiris/actions-gh-pages` step from `live_tracker.yml`**,
   folding its dashboard output into `_site/dashboard/` instead. Until one is removed, every hourly
   `live_tracker` success is a lie about what users see.
2. **Make `deploy-pages` conditional on the artifact.** `if: steps.upload.outcome == 'success'` on the deploy
   step, and stop the run at the JS-syntax gate instead of continuing into a guaranteed deploy failure.
3. **Make `hub-sync` fail loudly**: drop `|| echo "No changes"`, add
   `git diff --quiet hub/data/ && { echo "::error::hub data unchanged for this run"; exit 1; }`, and treat a
   missing exporter as an error rather than a warning.
4. **Fix the equity TP/SL emitters** (12 mismatches, 6 blanks) so `QA Market Validation` can pass on merit.
5. **Pick one Pages source in repo settings** (`gh-pages` branch or GitHub Actions) and delete the publisher
   that does not match, so `/pages` config and served content agree.

Until item 1 or 5 is done, any claim that "the gh-pages site is up to date" is unsupported: the branch is
current, the site is not built from it.
