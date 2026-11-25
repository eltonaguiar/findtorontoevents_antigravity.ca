# MiracleBoot zips + BOOTFIXPREMIUM repos — compromise check (2026-11-25)

Follow-up to the easybank phishing-kit cleanup. Question: are the two downloadable
builds in `WINDOWSFIXER/` tampered, and are the two GitHub repos that produce them
compromised?

**Verdict: no compromise found in either. Two unrelated exposure issues were found
and fixed (auto-index on a source tree, and `.git` inside the docroot), plus one
regression of mine that hid the legitimate downloads on torontoevent.net.**

## 1. The zips — content-identical to repo HEAD

| Artifact | Size | SHA-256 |
|---|---|---|
| `MiracleBoot_GitHub.zip` | 1,568,175 B | `023a7067946215bfb186040ead2aa9fbb44ce2dcb230d0d0b02de789c4ab8746` |
| `MiracleBoot_Cursor.zip` | 4,539,216 B | `adbaf70e74b4357a21bb93cce5f53f77c647799eb38e216abd444c0e040bdf0d` |

Byte-identical on **every** host copy (same SHA-256 for all three):

| Host / docroot | Path | Result |
|---|---|---|
| 50webs `findtorontoevents.ca` | `/WINDOWSFIXER/` | present, hash matches |
| 50webs `tdotevent.ca` | `/WINDOWSFIXER/` | present, hash matches |
| GoDaddy `torontoevent.net` | `/WINDOWSFIXER/` | present, hash matches |

No per-host variant, so nothing was swapped on one host only. Server-side mtimes are
Feb 7 2026 (50webs) and Feb 17 2026 (GoDaddy) — nothing was re-uploaded during the
Nov 23–25 incident window.

HTTP after the fixes below: `200 / 1,568,175` and `200 / 4,539,216` on both
`tdotevent.ca` and `torontoevent.net`; `findtorontoevents.ca` still `403` site-wide
from the 50webs host-level lockdown (not evidence about the file — FTP is the
authority there and the file is present and correct).

### Diff against the repos

| Build | Files in zip | Files in repo `main` | Only in zip | Only in repo | Content-equal after CRLF/BOM normalisation |
|---|---|---|---|---|---|
| GitHub | 364 | 364 | 0 | 0 | **364 / 364** |
| Cursor | 335 | 335 | 0 | 0 | **335 / 335** |

Raw SHA-256 differed on 363 / 94 files, which looked alarming until line endings were
normalised: the zips were repacked on Windows (UTF-8 BOM + CRLF) while the repo stores
LF. After normalisation **zero** files differ, and no file exists in one and not the
other. Conclusion: the served zips are the repo content, repacked — no injected file,
no modified record.

File types in the GitHub zip: 194 `.md`, 113 `.ps1`, 34 `.txt`, 17 `.cmd`, 2 `.bat`,
1 `.xaml`, 1 `.pdf`, `.gitignore`, `.cursorrules` — no executables.
Cursor zip adds 5 `.dll`, 2 `.exe`, 2 `.mui`, 1 `.rtf`, 3 `.png`, 2 `.pdf`, 2 `.json`,
81 `.log`.

## 2. Binaries in the Cursor zip — genuine Microsoft DaRT, not malware

All 7 binaries live in one folder, `Helper/CrashAnalyzer/`:

| File | Strings evidence |
|---|---|
| `crashanalyze.exe` | `Microsoft Corporation`, `<description>ERD Crash Analyzer</description>` |
| `DartRemoteViewer.exe` | `2014 Microsoft Corporation`, `_About DaRT`, PDB path `...\private\product\ERD\RemoteRecovery\DartRemoteViewer\...` |
| `MSDartCmn.dll`, `stdp.dll` | Microsoft DaRT class names (`DartConfig`, `IDartConfig`) |
| `mfc100u.dll`, `msvcr100.dll`, `msvcp100.dll` | VC++ 2010 runtimes the above link against |

Only external hosts in any of them are `microsoft.com` certificate/CRL URLs. Matches
the Microsoft Diagnostics and Recovery Toolset Crash Analyzer that ships with DaRT.

Caveats worth recording, not findings of compromise:
- Authenticode signatures were **not** cryptographically verified (no `osslsigncode`
  on this host); the evidence is embedded strings + cert URL patterns only.
- `DartRemoteViewer.exe` is a remote-viewing component. It is normal for DaRT, but a
  user running this package is running a tool with remote-desktop capability, which is
  worth knowing before shipping it from a public web directory.

## 3. Scripts — no C2, no persistence, no encoded payloads

Every outbound host referenced by the ~450 `.ps1`/`.cmd`/`.bat` files:

- `github.com/PowerShell/PowerShell` releases (portable pwsh 7.4.1, in `FETCH_PWSH.cmd`)
- `raw.githubusercontent.com/eltonaguiar/BOOTFIXPREMIUM_GITHUB/.../EMERGENCY_BOOT_REPAIR_V4.cmd`
- `github.com/eltonaguiar/MiracleBoot_v7_1_1` (zip download in `WinRepairGUI.ps1`)
- `microsoft.com` (connectivity probe only)
- vendor/tool homepages in docs: hirensbootcd, macrium, ventoy, intel, acronis,
  paragon, portableapps, snappy-driver-installer, asus/msi/gigabyte/asrock/amd/nvidia,
  uupdump, chatgpt/openai (documentation links)

No unknown or attacker-controlled host, no `.onion`, no `FromBase64String` payload, no
`reg add ...\Run` persistence, no `schtasks /create`. The `DownloadString` / `bitsadmin`
hits are a portable-PowerShell fetcher and a documented emergency download path.

## 4. The two GitHub repos — clean, and inactive since January

| Repo | Visibility | Default branch | Last push | Size |
|---|---|---|---|---|
| `eltonaguiar/BOOTFIXPREMIUM_GITHUB` | public | `main` | `2026-01-18T10:37:38Z` | 3123 KB |
| `eltonaguiar/BOOTFIXPREMIUM_CURSOR` | public | `main` | `2026-01-18T10:37:18Z` | 5931 KB |

- `.github/workflows` → **404 on both**: no CI, so no workflow could have pushed to the
  FTP hosts. This matters because the incident root cause was a GitHub Actions job with
  FTP credentials; these two repos have no Actions path at all.
- Deploy keys: **0** on both. Webhooks: **0** on both.
- Commit authorship: `eltonaguiar` and `MiracleBoot Developer` only.
  `BOOTFIXPREMIUM_GITHUB` history is Jan 15–18 2026 (`Update README with project
  documentation link` last); `BOOTFIXPREMIUM_CURSOR` is Jan 11–18 2026.
- **No commit, push or release activity in Nov 2026** — roughly 10 months before the
  incident. Nothing in either repo was used to deliver the kit.

## 5. Exposure issues found in `WINDOWSFIXER/` and fixed

These are hygiene, not phishing-kit indicators, but they were live on the same hosts.

**a) Apache auto-index on a source tree.** `GET /WINDOWSFIXER/MiracleBoot_v7_1_1/`
returned `200` with an `Index of /WINDOWSFIXER/MiracleBoot_v7_1_1` page listing
`.cursor/`, `DOCUMENTATION/`, `Helper/`, `Logs/`, `Test/`, `workspace/`, and the files
under them were readable (e.g. `Helper/WinRepairCore.ps1` → 200). Full source and logs
of the tooling were downloadable file-by-file.

Fix: a 517-byte `.htaccess` in **both** source directories (`MiracleBoot_v7_1_1` and
`MiracleBoot_v7_1_1 - Github code`) on **both** 50webs vhosts (`findtorontoevents.ca`,
`tdotevent.ca`) and on GoDaddy, containing `Options -Indexes` plus `Require all denied`
(with an Apache 2.2 `Order allow,deny` fallback). The published zips are unaffected.

**b) `.git` inside the docroot.** `WINDOWSFIXER/MiracleBoot_v7_1_1/.git/` existed on
GoDaddy **and** on 50webs. It was already 403 via the `.git` deny rule, but the history
should not be sitting in a public docroot.

Fix: renamed to `.git_QUARANTINE_2026-11-25` in all four directories (50webs copies had
already been renamed by a peer agent at 17:49 today; GoDaddy's were renamed in this
pass). Re-verified 403 on `/WINDOWSFIXER/MiracleBoot_v7_1_1/.git_QUARANTINE_2026-11-25/config`.

**c) Regression I introduced, now reverted.** The blanket
`RedirectMatch 404 (?i)[.](sql|zip|tar|tgz|bak)$` from the earlier exposure lockdown also
404'd the two legitimate public downloads on `torontoevent.net`. Narrowed to root-level
archives plus all SQL:

```apache
# root-level archives only -- /WINDOWSFIXER/*.zip are legitimate public downloads
RedirectMatch 404 (?i)^/[^/]+[.](zip|tar|tgz|bak)$
RedirectMatch 404 (?i)[.]sql$
```

Re-verified on `torontoevent.net`: both zips `200` (correct byte sizes), while
`/findtorontoevents_antigravity.ca.zip` and `/_dbrestore_ejaguiar1_stocks.sql` remain
`404`. GoDaddy `.htaccess` is now 4,816 B, md5 `9ea09d06ab51f4c69ccfdfd6a0601251`
(a peer agent had added kit-path deny rules in the same window; those were preserved).

## 6. Per-domain status

| Domain | Host | Zips in place | Zips served | Source dirs | `.git` |
|---|---|---|---|---|---|
| `torontoevent.net` | GoDaddy | yes, hash match | `200` (both) | `403` | quarantined, `403` |
| `tdotevent.ca` | 50webs | yes, hash match | `200` (both) | `403` | quarantined, `403` |
| `findtorontoevents.ca` | 50webs | yes, hash match (FTP) | host-level `403` | `403` via .htaccess | quarantined (FTP) |
| `ejaguiar1.50webs.com` | 50webs | n/a — no `WINDOWSFIXER/` | — | — | — |

## 7. What this does not cover

- Authenticode verification of the bundled Microsoft binaries (tooling unavailable here).
- A byte-level malware scan of `crashanalyze.exe` / `DartRemoteViewer.exe` against
  VirusTotal or similar. Recommended if the package is going to stay publicly linked.
- 50webs access logs for `WINDOWSFIXER/` specifically — not available from the host; the
  Webalizer reports show no campaign traffic to that path.
