# CI secret rotation — FTP credentials (2026-11-25)

**Status:** DONE, verified end-to-end by real workflow runs.
**Owner:** `ghcopilot`
**Trigger:** two FTP passwords were rotated on 2026-11-25; the GitHub Actions
secrets were not updated, so every FTP deploy in CI was failing `530 Login
authentication failed`.

---

## 1. What was broken

Two separate credentials were rotated on 2026-11-25, and in both cases the
rotation stopped at the account — the CI secret kept the pre-rotation value.

| Host | Account | Rotation evidence |
|------|---------|-------------------|
| GoDaddy `132.148.176.163` | `elton@torontoevent.net` | `dbpasses.txt` mtime `17:23:26Z`; last green deploy `17:19Z`, first red `17:34Z` |
| 50webs `ftps2.50webs.com` | `ejaguiar1` | annotated `(new one on nov 25 2026)`; old value returns `530`, new value logs in |

Failed signature, from `torontoevent-backtest-and-deploy.yml`:

```
ftplib.error_perm: 530 Login authentication failed
  step: Deploy dashboard to *** via FTP
  uses: secrets.FTPGODADDYPASS
```

`FTPGODADDYPASS` had `updatedAt = 2026-05-23T21:50:42Z` — i.e. six months
stale, independent confirmation the secret was never touched when the account
password changed.

## 2. Secret → host mapping (established from the workflows, not guessed)

`FTP_SERVER` and `FTP_HOST` both resolve to 50webs — several workflows carry the
literal fallback `${{ secrets.FTP_SERVER || 'ftps2.50webs.com' }}`, which pins
the host:

| Secret | Host | Referencing workflows |
|--------|------|-----------------------|
| `FTP_PASS` | 50webs | 59 |
| `FTP_PASSWORD_50WEBS` | 50webs | 3 |
| `FTPGODADDYPASS` | GoDaddy | 37 |
| `FTP_PASSWORD_TDOTEVENT` | GoDaddy (`torontoevent.net`) | 1 |

Only the four **password** secrets were stale. `*_USER`, `*_SERVER`, `*_HOST`
were correct and were left alone.

## 3. What was changed

1. **Four GitHub Actions secrets updated** (repo scope,
   `eltonaguiar/findtorontoevents_antigravity.ca`):

   | Secret | before (`updatedAt`) | after (`updatedAt`) |
   |--------|----------------------|---------------------|
   | `FTP_PASS` | 2026-10-23T04:18:44Z | 2026-11-25T19:24:28Z |
   | `FTP_PASSWORD_50WEBS` | 2026-10-23T04:18:46Z | 2026-11-25T19:24:29Z |
   | `FTPGODADDYPASS` | 2026-05-23T21:50:42Z | 2026-11-25T19:24:30Z |
   | `FTP_PASSWORD_TDOTEVENT` | 2026-10-23T04:18:47Z | 2026-11-25T19:24:30Z |

   Values were piped from a `umask 077` temp file on stdin (`gh secret set NAME
   < file`), never passed on a command line, and the temp files were shredded
   afterwards. No secret value appears in this document.

2. **`tools/deploy_audit_files.py` — `.env` fallback** (code change).
   The script read credentials *only* from `os.environ` and never loaded `.env`,
   so a correct `.env` plus a stale exported `FTP_PASS` still produced `530`.
   Added `_load_env_fallback()`, which fills **missing** `FTP_*` keys from the
   repo-root `.env` and never overrides an explicit export. Also accepts
   `FTP_HOST` as a host fallback and names both sources in the error message.

3. **Local `.env`** `FTP_PASS` refreshed (gitignored via `.gitignore:72 *.env`).
   Previous local value was a 10-character legacy string.

## 4. Verification — evidence, not assertion

Both rotated passwords were proved to authenticate **before** being written to
any secret (one successful login each; repeated failures risk a lockout):

```
ftps2.50webs.com  ejaguiar1              LOGIN OK  root entries=15
132.148.176.163   elton@torontoevent.net LOGIN OK  root entries=468
```

Then two real deploys were dispatched and watched to completion:

| Run | Workflow | Result |
|-----|----------|--------|
| 45684917739 | `deploy-fte-index.yml` (50webs) | **success** — `Upload core site files to findtorontoevents.ca (50webs FTP)` ✓ |
| 45684920518 | `torontoevent-backtest-and-deploy.yml` (GoDaddy) | **success** — `Deploy dashboard to *** via FTP` ✓, `Rise of the Claw` ✓, `updates page` ✓ |

The GoDaddy run is the decisive one: it executes the exact step that had failed
10 consecutive times since 17:34Z.

Regression checks on the code change:

- `py_compile` clean.
- No `FTP_*` in env → resolves from `.env`, `LOGIN OK`.
- Explicit `FTP_PASS` in env → preserved, `.env` does not override (asserted).
- Repo scan for either current password across `yml/yaml/py/js/json/env/sh/md/txt/php`:
  **no hardcoded copies**.

## 5. Notes and corrections

- **This report corrects an earlier claim of mine.** I first reported "GoDaddy
  FTP was NOT rotated / open P1", inferred from the *absence* of a
  `(new one on …)` annotation on that line of `dbpasses.txt`. That inference was
  wrong: the password had been rotated four hours earlier. The correct finding
  is that the rotation was real and the **CI secret** was the stale half. I
  retracted the claim on the COMS bus
  (`notes/copilot-correction-godaddy-rotated-2026-11-25`).
- Secrets are write-only over the API. "Which secret is stale" was established
  from workflow run timing + the `530` traceback, never by reading values.
- `gh run list --workflow=X --json … | python -c` silently errored in this
  session; the plain `gh run list --workflow=X` plus `--json`/`-q` form worked.

## 6. Reproducer

```bash
# 1. which secrets carry a password, and which host do they target?
grep -rhoE 'secrets\.(FTP|FTPGODADDY)[A-Za-z0-9_]*' .github/workflows/ \
  | sort | uniq -c | sort -rn
grep -rn "secrets.FTP_SERVER ||" .github/workflows/ | head   # pins FTP_SERVER to 50webs

# 2. detect staleness from CI, not from reading secrets
gh run list --workflow=torontoevent-backtest-and-deploy.yml --limit 10
gh run view <id> --log-failed | grep -E '530|error_perm'

# 3. update without exposing the value
umask 077
printf '%s' "$NEW_PASS" > /tmp/.pw && gh secret set FTPGODADDYPASS < /tmp/.pw
shred -u /tmp/.pw

# 4. verify with a real run
gh workflow run deploy-fte-index.yml --ref main
gh run watch <id>
```

## 7. Follow-ups (not done here)

- Local shells that exported the old `FTP_PASS` keep the stale value for their
  lifetime. Re-export after any rotation, or rely on the new `.env` fallback.
- `windows_env_backup_2026-04-14.md` on the Windows box still records
  April-era hashes. It is a backup, not a credential store — do not let it
  become a third stale copy.
- Repeat this check after **every** host-password rotation: the account side
  going green is not evidence CI went green.
