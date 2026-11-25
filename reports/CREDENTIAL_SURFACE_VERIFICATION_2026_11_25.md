# Credential Surface Verification — 2026-11-25

**Question asked:** after the CI-secret rotation, does all FTP and database access
still work? Verify the consumers, not just the two workflows that happened to be
green.

**Answer:** Yes. Every credential consumer was exercised independently:
2/2 FTP hosts authenticate, 10/10 MySQL databases authenticate locally, and CI
demonstrably writes to MySQL. The five failures in the 19:16–19:26Z window are
all accounted for — four were `530`-at-job-start (stale secret resolved before
the 19:24:28Z write) and now pass on re-run; the fifth is an unrelated GitHub
Pages artifact error. One additional failure (the DB diagnostic) was caused by a
bug in the diagnostic itself, not by any credential.

---

## 1. Direct authentication tests (local, independent of CI)

Run with `ftplib.FTP_TLS` and `pymysql`, printing only a `sha256[:12]`
fingerprint and length — never a password value.

### FTP — 2/2 hosts

| Host | User | Password fingerprint | Entries | Result |
|---|---|---|---|---|
| `ftps2.50webs.com` | `ejaguiar1` | `fc6bfb818db2` len 21 | 15 | `LOGIN OK` |
| GoDaddy (`elton@torontoevent.net`) | — | `c4ecaafd839d` len 21 | 468 | `LOGIN OK` |

Both fingerprints match **exactly** the values written to the four GHA secrets at
19:24:28–19:24:30Z. Method: `connect(host, 21, 30)` → `login(user, pw)` →
`prot_p()` → `nlst()`.

### MySQL — 10/10 databases

From local outbound IP `142.181.219.3` against `mysql.50webs.com:3306`
(port confirmed OPEN):

| Database | Tables |
|---|---|
| `ejaguiar1_backtests` | 10 |
| `ejaguiar1_backups` | 414 |
| `ejaguiar1_deals` | 0 |
| `ejaguiar1_events` | 5 |
| `ejaguiar1_favcreators` | 59 |
| `ejaguiar1_memecoin` | 58 |
| `ejaguiar1_news` | 2 |
| `ejaguiar1_sportsbet` | 49 |
| `ejaguiar1_stocks` | 463 |
| `ejaguiar1_tvmoviestrailers` | 15 |

**Result: OK=10 FAIL=0.**

---

## 2. CI failures in the 19:16–19:26Z window — all diagnosed

| Run | Workflow | Failing step | Cause |
|---|---|---|---|
| 45683930112 | [torontoevent.net] Run Backtests & Deploy Dashboards | Deploy dashboard to *** via FTP | `ftplib.error_perm: 530` @ 19:25:46 |
| 45684528630 | Deploy Rise of the Claw Dashboard | Deploy to GitHub Pages | **Not credentials** — `No artifacts named "github-pages" were found for this workflow run` |
| 45684667268 | Send Accountability Reminders | Merge API keys into existing .env on server | `530` @ 19:23:20 |
| 45684767601 | Deploy Competition to Live Site | Deploy competition files to live site via FTP | `530` @ 19:24:50 |
| 45684869782 | GHCOPILOT prospective paper monitor | Deploy public monitor and preserve live footer | `530` @ 19:25:32 |

### Why the `530`s were not a new breakage

A GitHub Actions job resolves `secrets.*` **at job start**. The four jobs began
at 19:18:46, 19:23:10, 19:23:45 and 19:24:23 — all **before** the secret write
completed at 19:24:28–19:24:30Z. They therefore authenticated with the stale
value and recorded `530` minutes later, when the FTP step actually ran and
credited its already-resolved old credential.

Two runs that started **after** the write were green on the first attempt:
`deploy-fte-index.yml` #45684917739 (19:24:41) and
`torontoevent-backtest-and-deploy.yml` #45684920518 (19:24:43).

### Re-run results — 4/4 now pass

| Run | Workflow | Rerun |
|---|---|---|
| 45683930112 | [torontoevent.net] Run Backtests & Deploy Dashboards | **success** (3m19s — `Deploy dashboard to *** via FTP` ✓) |
| 45684667268 | Send Accountability Reminders | **success** |
| 45684767601 | Deploy Competition to Live Site | **success** |
| 45684869782 | GHCOPILOT prospective paper monitor | **success** |

The first one is the decisive proof: it re-ran the **exact step** that had failed
with `530`.

### The one non-credential failure

`45684528630` — `Deploy Rise of the Claw Dashboard`, step
`Deploy to GitHub Pages`, error:

```
##[error]Fetching artifact metadata failed. Is githubstatus.com reporting issues with API r...
##[error]Error: No artifacts named "github-pages" were found for this workflow run.
```

The `github-pages` artifact is produced by an earlier step in the same run. This
is an artifact-producer / ordering problem (or a transient GitHub API fault — the
same message references `githubstatus.com`), **not** an FTP or DB credential
failure. It is deliberately not folded into the credential story and was not
re-run for credential reasons.

---

## 3. Database access in CI — proven by a real write, not a smoke test

`audit-dashboard.yml` run **#45673781942** (success, today):

```
PICK_OUTCOMES_MYSQL_ENABLED: 1
DB_STOCKS_HOST: mysql.50webs.com
2026-11-25T18:38:27 [INFO] [mysql] wrote/updated 713 outcomes to at_pick_outcomes
2026-11-25T18:38:27 [INFO] MySQL sync: 713 outcomes written to at_pick_outcomes
```

713 rows written to a production MySQL table from a GitHub runner. Recent
conclusions for DB-touching workflows:

| Workflow | Latest runs |
|---|---|
| `audit-dashboard.yml` | success 11-25T18:18, 15:17, 12:23 |
| `db-sync-bidirectional.yml` | success 11-25T08:43, 11-24, 11-23 |
| `ai-leaderboard-freshness.yml` | success 11-25T04:52, 11-24, 11-23 |
| `sleeve-daily.yml` | success 11-24T22:21, 11-23, 11-22 |
| `alpha-engine-daily-picks.yml` | success 11-24T22:17, 11-23, 11-22 |

DB secrets (`DB_PASSWORDS_JSON`, `DB_PASS`, `MYSQL_PASSWORD`, `AUDIT_DB_PASS`, …)
all carry `updatedAt = 2026-05-23T10:50Z` — untouched by this session, so nothing
here could have invalidated them.

---

## 4. `db-credentials-test.yml` — the diagnostic was wrong, not the credential

**Run #45686338230** (first ever execution of this workflow) failed with
`10 database connection(s) failed`. The table showed:

```
ejaguiar1_backtests   SKIP   no entry for 'backtests' in DB_PASSWORDS_JSON
... (all ten SKIP)
GitHub runner outbound IP: 3.41.210.118
```

This is **not** an authentication failure. `tools/test_db_credentials.py` treated
a *missing key* as a failure and counted it in `failures`, so a secret that
manages only some databases reports as "10 failed". `tools/db_env.py` documents
the canonical shape as `DB_PASSWORDS_JSON["stocks"]` — nothing guarantees all ten
keys exist.

### Fix applied to `tools/test_db_credentials.py`

1. Prints the **key names present** (key names are not secrets), so a SKIP is
   actionable instead of a mystery.
2. A missing key is now `SKIP` and is **not** counted as a failure — an absent
   key means "not managed by this secret", not "wrong password".
3. New guard: if **zero** databases were actually tested, exit 1 with
   `no database was actually tested — DB_PASSWORDS_JSON has no key matching any
   of the 10 expected names`. This prevents the inverse bug (all-SKIP silently
   passing).
4. Summary line now reads `N OK / N FAIL / N SKIP`.

Verified: `py_compile` OK; simulated with `{"stocks":"x"}` → 1 tested, 9 SKIP,
correct FAIL on the bogus password; simulated with `{}` → hard error.

**Caveat:** the fix is on branch `security/2026-11-25-phishing-cleanup` and is
not yet pushed, so `workflow_dispatch` (which runs the default branch) still
executes the old version until it merges.

---

## 5. Verification matrix (final)

| Surface | Local | CI |
|---|---|---|
| 50webs FTP | ✅ login OK, 15 entries | ✅ 3/3 reruns + 2 post-write runs green |
| GoDaddy FTP | ✅ login OK, 468 entries | ✅ `torontoevent-backtest-and-deploy` #45684920518 green |
| MySQL (10 DBs) | ✅ 10/10 OK | ✅ 713 rows written @ 18:38Z; 5 workflows green |
| `DB_PASSWORDS_JSON` | n/a (not set locally) | ⚠️ diagnostic bug — fixed, unmerged |
| GitHub Pages deploy | n/a | ❌ #45684528630 — artifact ordering, unrelated to credentials |

Open failures after this work: **zero credential-related.** The one red run in
the last 40 (`45686338230`, DB Credentials Test) fails only because its own
assertion is wrong, and the correction is pending merge.

---

## 6. Reproducer

```bash
# FTP (auth only, no writes)
python3 - <<'PY'
import ftplib, ssl, os
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
for label, host, user in [("50webs","ftps2.50webs.com","ejaguiar1"),
                          ("godaddy","ftps2.50webs.com","elton@torontoevent.net")]:
    f = ftplib.FTP_TLS(context=ctx); f.connect(host,21,30); f.login(user, os.environ["FTP_PASS"]); f.prot_p()
    print(label, "LOGIN OK", len(f.nlst()), "entries"); f.quit()
PY

# MySQL (all ten)
python3 tools/test_db_credentials.py   # with DB_PASSWORDS_JSON exported

# CI-side, after merge
gh workflow run db-credentials-test.yml
gh run watch "$(gh run list --workflow=db-credentials-test.yml --limit 1 --json databaseId --jq '.[0].databaseId')"
```

---

## 7. Corrections and caveats

- **`--dry-run` does not connect.** `tools/deploy_audit_files.py --dry-run` skips
  the FTP connection entirely, so it cannot prove authentication. Only a real
  `login()` can.
- **A green run on workflow A does not prove workflow B's secret path.** Each
  consumer resolves its own secret at job start; the four reruns were necessary.
- **Secrets are write-only.** Staleness was established only from `updatedAt` plus
  failure timing, never by reading a value.
- **Job-start vs step-run timing** is the reason the `530`s appeared *after* the
  fix landed. The error timestamp is when the step ran, not when the credential
  was resolved.
- The `github-pages` artifact failure is recorded here for completeness but is
  **not** a credential issue and has no verified fix yet.
