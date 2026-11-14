# 50webs FTP credential rotation and local deployment repair

## What was broken

- GitHub's 50webs credential aliases still had May timestamps.
- The current agent process inherited an obsolete `FTP_PASS`. It overrode the newly rotated password even though the canonical local file was correct; real authentication failed with that inherited value and succeeded with the file's value.
- `tools/deploy_supplements.py` had a nonempty hardcoded FTP password fallback.
- Several local deployment entrypoints used plaintext FTP; the picks-now deployer disabled TLS certificate verification.
- `deploy_instrumented_audit.py` reused the 50webs `FTP_PASS` for a different GoDaddy account.
- The Kimi deployer accepted generic operating-system `USER`/`PASSWORD` variables as FTP credentials.
- Sports deployment still depended on an old Windows credential backup and passed its runtime password in curl's process arguments.

## Changes

- Added `tools/ftp_credentials.py`, a shared password-safe loader and command wrapper:
  - Reads only the line immediately following the `50WEBS_FTP` password label in `~/dbpasses.txt`, stopping there.
  - For `ftps2.50webs.com` / `ejaguiar1`, the local canonical file takes precedence over stale inherited password variables.
  - CI without that file uses `FTP_PASS`/`FTP_PASSWORD` and FTP-specific user/host aliases.
  - Never sends the local file's 50webs password to a different host/account; conflicting FTP host aliases fail closed.
  - Password is omitted from object representations; the check command reports sanitized failures and exits nonzero.
- Wired audit, supplements, GHA summary, main-site partial/full deploys, movies 2/3, alternate-site deploys, picks-now, root FTPS/Kimi and instrumented deploy paths.
- Removed the hardcoded supplements fallback. Added `dbpasses.txt` to `.gitignore`.
- Enforced verified TLS and protected data on the touched main deployment paths. No fallback to plaintext on failure.
- Kept GoDaddy on its separate `FTPGODADDYHOST_TE_DOTNET` / `FTPGODADDYUSER` / `FTPGODADDYPASS` settings.
- Sports uses the shared wrapper and curl's stdin configuration rather than embedding a password in curl argv.
- No new credential values are stored in tracked source, this document, command arguments, or PR text.

## GitHub rotation scope

Metadata inventory inspected 77 owned repositories. Relevant active deployments:

- `eltonaguiar/findtorontoevents_antigravity.ca`: updated 10 50webs aliases: `FTP_PASS`, `FTP_USER`, `FTP_HOST`, `FTP_SERVER`, and password/user/server triplets for `50WEBS` and `TDOTEVENT`.
- `eltonaguiar/TORONTOEVENTS_ANTIGRAVITY`: updated `FTP_PASSWORD`, `FTP_USERNAME`, `FTP_SERVER`.
- `eltonaguiar/STOCKSUNIFY2`: updated `FTP_PASS`, `FTP_USER`, `FTP_HOST`.
- `eltonaguiar/findtorontoevents_antigravity.ca-archive-2026-05-23`: despite its name it is not GitHub-archived and still has active deployment workflows; updated the same 10 confirmed 50webs aliases as the primary repository.

Total: **26 encrypted secret entries across four repositories**. Values were passed to `gh secret set` over stdin, not shell arguments. Primary repo's `github-pages` environment had no FTP-secret overrides. Unrelated GoDaddy/TORONTOEVENT aliases and the two genuinely GitHub-archived repositories were not blindly overwritten with another account's password. Inventory metadata for historical copies is not a claim that every historical repository/file was remediated.

## Peer coordination / no duplicate cleanup

Checked current main and shared uncommitted paths before publication. Shared `tools/deploy_audit_files.py` had one unrelated new upload-list entry; this patch only changes credential imports/loading and TLS construction, not its upload list. Another agent had broad DB/workflow cleanup in flight. Those shared files and stashes were not edited, copied, reverted or committed here. This branch is FTP-specific and leaves that DB/workflow work to its owner.

## Safe usage

```sh
# Read-only authentication check: verified TLS, protected data, site cwd, NOOP.
python3 tools/ftp_credentials.py --check

# Audit dry-run: does not upload any files.
python3 tools/deploy_audit_files.py --dry-run --only incidents

# For an existing legacy deployment entrypoint, inject credentials only at runtime.
python3 tools/ftp_credentials.py -- python3 tools/deploy_updates_v05.py
```

The last command is an actual deployment if deliberately invoked; it was **not** executed for this repair. Do not paste passwords into shell commands or source files. A wrapper can set a child's environment, but cannot mutate the already-running parent shell's environment. Use the loader/wrapper rather than exporting another permanent plaintext copy.

## Verification

- Focused credential tests cover exact-label parsing, missing values, redacted repr, local rotation overriding a stale env, CI without a file, separate-account isolation, FTP-specific aliases, control characters, sanitized failures, TLS/protected-data sequencing, connection cleanup, command-wrapper behavior and sports argument handling.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_ftp_credentials.py -q -p no:cacheprovider`: **21 passed**.
- `bash -n tools/deploy_sports_files.sh`: passed. Every changed Python file parsed successfully with `ast.parse`.
- Live read-only authentication with the new value succeeded as `ejaguiar1`; verified TLS hostname/certificate, protected data mode, `/findtorontoevents.ca` directory access and NOOP. No production files were uploaded or deleted.
- Audit incidents deployment dry-run succeeded. Its existing summary says “uploaded” for dry-run entries; individual records explicitly say `DRY-RUN would upload`. This repair did not change that unrelated wording.
- Full repository tests are not claimed green. Only targeted tests and syntax checks are appropriate for this credential-loading change.
- Final source/added-lines and published PR scans compare the actual current FTP password without displaying it.
- Independent security review of the shared loader, tests, audit/main/sports deploy wiring and separate-account instrumented deployment found no high-confidence introduced vulnerabilities. The reviewer independently quoted the original audit deployer's environment-only password lookup from git, without reading the credential file.

## Historical exposure caveat

Removing an old password literal does not erase git history, pre-existing agent transcripts or previously published logs. The newly rotated password must never be copied there. This task updates the provided FTP credential in consumers; it does **not** change MySQL passwords or claim to have scrubbed every past log. Rotate any separately exposed DB credentials through the appropriate account owner.
