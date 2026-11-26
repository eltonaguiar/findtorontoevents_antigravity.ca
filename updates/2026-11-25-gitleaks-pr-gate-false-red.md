# Gitleaks PR gate was a structural false red — fixed by scoping to the PR's own commits

**Date:** 2026-11-25
**Branch:** `ci/gitleaks-scope-pr-commits`
**Files changed:** `.github/workflows/secret-scan.yml`
**Severity:** P1 (a security gate that fires on everything is indistinguishable from one that fires on nothing)

---

## 1. What was broken

The `Gitleaks PR diff scan` job (`.github/workflows/secret-scan.yml`, job `pr-secret-scan`) had become
**guaranteed red for any pull request that had merged `main`** — regardless of what the PR contained.

The trigger was PR #1068:

```
Gitleaks PR diff scan   fail   32m05s      run 45704814146  job 139523964118
(all 5 other checks on that PR: pass)
```

Earlier the same job had been *cancelling* at its 20-minute cap. PR #1122 raised the cap to 45
minutes. That change was correct, but it converted a silent `cancelled` into a loud `failure`: the
scan now had time to finish and report what it had always been finding. **The timeout was masking a
scope bug, not causing one.**

### Root cause

`gitleaks/gitleaks-action@v2` runs, for `pull_request` events:

```
gitleaks git --first-parent <base.sha>^..<head.sha>
```

`base.sha` comes from the event payload and is **frozen at the PR's last push**. A PR that keeps
merging `main` after that push accumulates thousands of commits on `main`'s side of the range. On
PR #1068:

| Quantity | Value |
|---|---|
| `base.sha` | `4907385676644ab` — `main` @ 2026-11-22T10:50:53Z |
| `head.sha` | `9b1df933d1fee3f` — 2026-11-25T21:02:40Z |
| The action's range, `--first-parent base^..head` | **5,180 commits** |
| `--no-merges base..head` | **7,968 commits** |
| The PR's own commits vs *current* `origin/main` | **21 commits** |

### What it was actually finding

All inherited findings are **one false positive repeated**:

```
"key": "BTCUSDT/breakout/15m"
"key": "BTCUSDT/breakout/1h"
"key": "BTCUSDT/donchian/4h"
...
```

That is `1000_TODOS.json` — the strategy registry. The JSON field is *literally named* `key`, so
gitleaks' `generic-api-key` rule matches all 175 distinct lines (350 findings, two hits per line).
There is no credential in it.

Measured, on the real repo with gitleaks 8.30.1:

| Scan range | Commits scanned | Findings | Verdict under `--exit-code 1` |
|---|---|---|---|
| `--first-parent <base.sha>^..<head.sha>` (what the action did) | 5,123 | **350** | **RED** |
| `--no-merges <base.sha>..<head.sha>` | 7,882 | **350** | **RED** |
| `--no-merges merge-base(origin/main,HEAD)..HEAD` (the fix) | **21** | **0** | **PASS** |
| Full `--first-parent` history (context) | 8,128 | 555 | — |

The 555 full-history findings all trace to a single old import commit, `7ab6751117`
(2026-11-19, PR #977), and include two keys that are **public by design**: a YouTube InnerTube key
(in-file comment: "This is YouTube's public InnerTube API key (embedded in youtube.com JS)") and
`DISCORD_PUBLIC_KEY`, which is public by protocol (it verifies interaction signatures).

### The tell was already in the same file

The `scheduled-secret-scan` job scans the **identical HEAD tree**, with `--exit-code 0`, and files the
result as a `::warning::` calling it "legacy baseline debt". The PR job turned the same data into a
hard failure. **One dataset, two verdicts** — the inconsistency was visible in the YAML all along.

---

## 2. What changed

`.github/workflows/secret-scan.yml` → `pr-secret-scan`:

1. **`Gitleaks PR diff scan` (the action) → replaced** with an explicit, range-scoped CLI invocation.
2. **`Install Gitleaks CLI (verified SHA256)`** added — reuses the scheduled job's exact
   download-and-checksum pattern (`gh api … releases/latest` → fetch asset + `checksums.txt` →
   `sha256sum --check` → `tar -xzf`). Pinned to the release's published checksums rather than a
   floating image tag.
3. **`Gitleaks PR secret scan (PR's own commits only)`** — resolves the comparison base at *scan
   time*:
   ```bash
   git fetch --no-tags --quiet origin "+refs/heads/main:refs/remotes/origin/main" || true
   BASE=$(git merge-base origin/main HEAD)      # fallback: merge-base of event base.sha
   n=$(git rev-list --no-merges --count "${BASE}..HEAD")
   gitleaks git . --config .gitleaks.toml --redact --no-banner \
     --report-format json --report-path gitleaks-pr.json \
     --log-opts="--no-merges ${BASE}..HEAD"
   ```
   - `base.sha` is used **only** as a labelled fallback if `origin/main` cannot be fetched.
   - When `n == 0` the step emits an explicit `::notice::` instead of passing silently — a gate that
     passes without saying anything is indistinguishable from one that never ran (this repo already
     shipped a six-day-green-and-dead workflow through exactly that hole).
4. **`Summarise gitleaks findings (no secret values printed)`** — `if: failure()`. Prints
   `::error file=…,line=…::<RuleID> in a file this PR adds or modifies` and a per-file top-10. Never
   prints a value. If `gitleaks-pr.json` is absent it says the failure is *not* a finding, so an
   infrastructure error can never be mistaken for a leak.
5. **`Upload gitleaks report (evidence, pass or fail)`** — `if: always()`, artifact
   `gitleaks-pr-report`, 14-day retention. Evidence is retained either way.

`timeout-minutes: 45` from #1122 is retained (checkout of this repo alone is minutes; 20 was too
tight). The `scheduled-secret-scan` job is untouched.

**No allowlist was widened.** Adding `1000_TODOS.json` to `.gitleaks.toml` would also stop a *real*
credential from being caught there. The correct fix is to compare the right commits, not to stop
looking.

---

## 3. How it was verified

Local, against PR #1068's real branch (`/tmp/a1068`, HEAD `1c4997d8a38`), gitleaks **8.30.1 arm64**:

```
1. YAML structural validation
   yaml.safe_load(".github/workflows/secret-scan.yml")          -> OK
   jobs = ['pr-secret-scan', 'scheduled-secret-scan']
   pr-secret-scan steps = 5 (checkout, install, scan, summarise, upload)

2. Shell validation
   bash -n on every run: block                                 -> OK (3/3)

3. Reproduced the failure with the action's own range
   git rev-list --first-parent --count BASE^..HEAD             -> 5180
   gitleaks git --log-opts="--first-parent BASE^..HEAD"        -> 350 findings, all 1000_TODOS.json
   (the action runs --exit-code 1, so 350 == RED)

4. Proved the PR itself introduces nothing
   git rev-list --no-merges --count origin/main..HEAD          -> 21
   gitleaks git --log-opts="--no-merges origin/main..HEAD"     -> "no leaks found", exit 0

5. Attributed every inherited finding to main, byte-for-byte
   for each of the 83 flagged files: git rev-parse HEAD:<path> == origin/main:<path>
                                                               -> 83 identical, 0 differing

6. Inspected the non-generic findings by hand (values masked)
   gcp-api-key  x2  MOVIESHOWS2/3 api/freestyle-search.php:75  -> YouTube InnerTube, public by design
   discord-api-token favcreators/discord-worker/src/index.js:8 -> DISCORD_PUBLIC_KEY, public by protocol
   jwt              MOVIESHOWS2/scroll-fix.js:53               -> TMDB read token, client-side, pre-existing
   + gcp/rapidapi   STOCKSUNIFY{2,}/scripts/lib/stock-api-keys.ts -> client-side, pre-existing

7. Executed the NEW step body end-to-end with a deliberately stale base
   PATH=/tmp/glbin:$PATH EVENT_BASE_SHA=4907385676644ab bash /tmp/step_scan.sh
     comparison base : ecd1840aaa63dce7931dd11a4f7826579424269b  (current main, #1122)
     commits this PR adds: 21
     no leaks found
     ==> STEP EXIT CODE: 0     report written: True   findings: 0
```

Step 7 is the important one: the step self-corrects from a stale event payload, which is the exact
failure mode being fixed.

---

## 4. Follow-ups (measured, not applied here)

| Item | Evidence | Why deferred |
|---|---|---|
| `1000_TODOS.json` — 175 lines match `generic-api-key` | `"key": "BTCUSDT/breakout/15m"` | A path allowlist would blind the rule for that file. Better: a *narrow* regex allowlist for the `<PAIR>/<strategy>/<tf>` shape, so a real key in that file is still caught. Not needed for this gate to be correct. |
| 555 findings across full history | all introduced by `7ab6751117` (2026-11-19, #977) | Baseline debt, reported as `::warning::` by the scheduled job. Cleaning it is a separate, human-verified pass — mass-allowlisting 555 unreviewed findings is worse than reporting them. |
| YouTube InnerTube key + `DISCORD_PUBLIC_KEY` | in-file justification comments | Public by design; a narrow allowlist entry with the justification comment would silence them without weakening anything. |
| 20 runs stuck in `queued` since 2026-11-11T20:36 | all `event=schedule`, ~14 days | Separate `concurrency:` config problem; see the GHA bad-state audit. |

---

## 5. Notes for the next agent

- **`cancelled ≠ failure ≠ clean`.** A cancelled secret scan proves nothing and renders like a finding.
- **A gate that fails for reasons unrelated to the change is not a security control** — it trains
  reviewers to ignore red. That is worse than no gate.
- **`base.sha` from a `pull_request` payload is stale by design.** Always resolve the comparison base
  against current `origin/main`.
- **Never claim a gate passed because the job was green.** Check that the artifact exists and that
  the step actually ran.
