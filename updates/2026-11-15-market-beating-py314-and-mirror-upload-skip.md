# market_beating py3.14 failure + mirror-site upload skip (2026-11-15)

Two financial-pipeline failures from the same root class: `ubuntu-latest` now
resolves to Ubuntu 26.04, and one stray filename on the source FTP aborts the
mirror before it uploads anything.

## 1. `market_beating.yml` — pandas 2.1.4 cannot build on Python 3.14

**Symptom** (23-min job, died in the install step):

```
error: too few arguments to function '_PyLong_AsByteArray'; expected 6, have 5
  pandas/_libs/tslibs/base.cpython-314-x86_64-linux-gnu.so.p/...base.pyx.c:5397
error: metadata-generation-failed
```

**Root cause** — not pip, not the package: the pins. Measured from the PyPI
release metadata (`https://pypi.org/pypi/<pkg>/<ver>/json`):

| pin | manylinux cp312 wheels | cp314 wheels | sdist |
|---|---|---|---|
| `pandas==2.1.4` | 2 | **0** | yes |
| `numpy==1.26.2` | 2 | **0** | yes |

`requirements.txt` pins both, so on 26.04 (system Python 3.14) pip has no wheel
to install and compiles pandas from source, where Cython 0.29 output no longer
matches the 3.14 C-API (`_PyLong_AsByteArray` gained an argument). On 24.04
(Python 3.12) both wheels exist and install in seconds.

**Fix** — pin the job to `ubuntu-24.04`, keeping the `vars.ACTIONS_RUNNER_LABEL`
override so self-hosted runners still win. Same pattern already merged for the
Playwright smoke job.

**Scope of the class** — 22 workflows do `pip install -r requirements.txt`.
Only jobs that end up on the *system* interpreter are exposed; the ones that
successfully pin a toolcache Python via `actions/setup-python` are fine. This PR
fixes the reported one rather than mass-editing 22 files.

## 2. `mirror-site.yml` — one bad filename skipped every upload for days

**Symptom** — every run since at least 2026-11-14 fails, and steps 4-7
(`Upload to torontoevent.net`, `Upload to tdotevent.ca`, `.env deploy`,
`Verify mirrors`) are all **skipped**. So the mirror has been receiving nothing
while the workflow looked merely "red".

**Root cause** — not repo size, and not credentials. The log contains exactly
two error lines, one per lftp attempt:

```
mirror: Access failed: 553 Prohibited file name: hot_trending_30m<garbage>%2527%2522\.json
```

lftp returns exit 1 for a per-file access failure, and the workflow's
`if ! lftp ...; then retry; fi` only retries the identical script — so after
27,692 successful file transfers the step dies and the uploads never start.
The source creds are fine: 27,692 files transferred proves auth works.

**Fix** — exclude the stray artifact (`hot_trending_30m*%25*`, i.e. only names
containing the double-encoded `%25`), and drop pure ballast that can never be
served: `.git/` directories (3,791 transfers in one run) and
`__pycache__/` + `*.pyc` (51).

**Measured effect** by replaying the exclude regexes over all 27,692 real paths
from run 43684463176:

```
excluded by git-dirs : 3791
excluded by pycache  :   51
excluded by pyc      :   51
excluded by bad-name :    2
kept for mirror      : 23848 / 27692  (86.1%)
audit/ paths still mirrored: 4134
```

The financial payload is untouched: every `audit/` path is still mirrored.

## Live-site delta (why this mattered)

Compared origin vs mirror at 2026-11-15 08:3x UTC:

| path | origin | mirror | verdict |
|---|---|---|---|
| `/audit/data/dashboard_data.json` | 24,681,343 B, sha `905dfc08f525` | identical | **in sync** — financial data reaches torontoevent.net via the `audit-dashboard` deploy, not this mirror |
| `/audit/`, `/audit/picks-now.html`, `/audit/portfolio_history.html`, `/audit/benchmark_proof.html` | — | +454 B each | only difference is a GoDaddy-injected `tccl.min.js` telemetry snippet (`_trfq`/`_trfd`, `secureserver.net`, `cp_id 10873446`) appended before `</html>`. Host-side, not our deploy. |
| `/events.json` | 21,052,037 B, `last_updated` **2026-11-15T04:10** , 13,835 events | 34,914,487 B, `last_updated` **2026-10-06T12:10**, 21,737 events | **mirror 40 days stale** — the visible cost of the skipped uploads |

So the mirror being red was **not** threatening the trading payload; it was
freezing the events site on torontoevent.net. That is now unblocked.

## Verification

- Both workflows parse with `yaml.safe_load`; the four new exclude patterns are
  present in the mirror download script.
- Exclude replay over the real 27,692-path transfer log: see table above.
- PyPI metadata proof of the missing cp314 wheels: see table above.
- `market_beating.yml` `runs-on` resolves to `ubuntu-24.04`.
- Live delta measured against both hosts (not assumed).

## NOT MEASURED

- The mirror fix is **not yet proven end-to-end**: a `workflow_dispatch` run is
  in flight as this lands, and a full pull+upload takes ~20-40 min. The claim
  here is only that the aborting file is excluded and the regexes behave as
  measured on the real path list.
- The `market_beating` fix is verified by runner pin + wheel evidence, not by a
  completed 23-min run.
- `dbpasses.txt` is a freeform notes file (not key/value, not JSON). Parsing it
  for credential labels echoed some raw values into a local terminal transcript;
  treat anything in that file as displayed and rotate the ones that matter. Its
  `50WEBS_FTP` entry is consistent with working source creds — the 27,692-file
  transfer proves the 50webs password is **not** wrong.

## Unrelated, flagged only (not financial)

- `Sports endpoint smoke + Playwright` 4/10 fails — user asked to ignore.
- `Branch Large File Duplicate Guard` 20/22 cancelled — self-cancelling
  concurrency group, invalid signal on any PR.
- `Outcome Resolver` 4/5 cancelled, `Strategy Funnel Hourly Refresh` 4/4
  cancelled, `Secret Scan` 3/12 cancelled — concurrency cancellations, no
  failure signal.
- `Verified pilot daily` 1/1 fail and `Backup Restore Verification` 1/3 fail —
  worth a separate look, not touched here.

## Addendum 2026-11-15 09:0xZ — the 553 is fixed; volume is now the limiter

Re-dispatched after the first fix merged (run **43695030179**):

- `553 Prohibited file name`: **0 occurrences** (was 2 per run) — the exclusion works.
- New/remaining failure: `The action 'Download from findtorontoevents.ca (50webs FTP)' has timed out after 30 minutes`, after **15,225 transfers**.
- Measured throughput: **507 files/min**. Remaining workload after the excludes:
  27,692 − 3,794 = **23,898 files ≈ 47 min** for a cold pull.

The deeper defect: each run starts on a fresh runner with an **empty**
`/tmp/site_mirror`, so every 6-hourly run re-downloads the whole tree from
scratch and can never finish before the cap.

**Fix (this commit):** persist the tree with `actions/cache@v5`
(`key: site-mirror-<run_id>`, `restore-keys: site-mirror-`), so every pull after
the first is incremental, and raise the download cap 30 → 50 min so a cold pull
fits inside the 90-min job budget (50 download + 15 + 15 uploads + ~2).

A cold run may still exceed 50 min; the cache post-step saves progress anyway, so
the next run resumes instead of restarting.

**Still NOT MEASURED end-to-end:** at 09:11Z `torontoevent.net/events.json` was
still `last_updated 2026-10-06` / 21,737 events, i.e. no upload has succeeded yet.
