# torontoevent.net (GoDaddy) — phishing kit removed + docroot exposed-data lockdown

**Date:** 2026-11-25
**Host:** GoDaddy shared hosting, docroot `/home/od9pbhr321dt/public_html` (FTP login lands at `/`)
**Vhost:** torontoevent.net (also answers on www)
**Relation to the 50webs incident:** same kit family. The 50webs cleanup on 2026-11-25 removed
`de/`, `appeasy/`, `easyapp/`, `de-de/` from `findtorontoevents.ca`, `tdotevent.ca`,
`ejaguiar1.50webs.com` and `torontoeventsvamp.50webs.org`. GoDaddy still had its own copy live.

## What was broken

Live, publicly reachable phishing payloads in the GoDaddy docroot:

| Path | Size | md5 | Identification |
|---|---|---|---|
| `/de/index.php` | 11,231 B | `586b76b00d80965e71182fadf67c2d76` | kit build A (reCAPTCHA-v3 gate + honeypot, 302 → `oldyhub.com/BQ2GS5/firstonline/bk/`) |
| `/de/visit.txt` | 79,366 B | `5dd2330b2eb700f80a9c223d74fb20ee` | harvested-victim log — **byte-identical to the 50webs copy**, i.e. staged here, not locally filled |
| `/de/error_log` | 57 B | `5fc1a173c4ee7deb286e78421b2498f5` | PHP error log from the kit |
| `/appeasy/index.php` | 11,231 B | `586b76b00d80965e71182fadf67c2d76` | kit build A |
| `/easyapp/index.php` | 11,231 B | `586b76b00d80965e71182fadf67c2d76` | kit build A |

Root `.htaccess` had already been compromised with the same payload seen on 50webs — the
`RewriteRule (([a-z]\d){5}/)(.*/)(.*/)(.*) de/index.php [L]` SEO doorway, 3,083 `deny from`
scanner-blocking lines and the trailing `##Off to the Mouse they go##` marker. A backup of those
exact bytes (76,678 B, md5 `95b93b4b17a32f4a0d6caf5e4cbb41cc`) was left **web-downloadable** at
`/.htaccess.bak-preipclear-20261125-123519` by an earlier remediation pass (kilo agent, 12:35 today)
that replaced the file but did not remove the payloads.

Also public and unrelated to the kit, but part of the same exposure:

| Path | Observed | Problem |
|---|---|---|
| `/.htaclu` | 200, 42 B | Basic-auth **MD5-crypt hash** for user `elton`, downloadable |
| `/.htacl` | 200, 139 B | `AuthUserFile` config (stale 50webs path) |
| `/findtorontoevents_antigravity.ca.zip` | 200, 52 MB | full repo source archive |
| `/_dbrestore_ejaguiar1_stocks.sql` (+42 more `.sql`) | 200, 28.5 MB | full MySQL dumps |
| `/EJAGUIAR1_MEMECOIN_FIXED.sql` | 200, 13 MB | full MySQL dump |
| `/_test_all_dbs.php`, `/_db_export_tmp.php`, `/cursor_test_sql.php` | 200/500 | DB probe/export tools |

## How it got there — deployment vector, not a fresh FTP break-in

`ftp.torontoevent.net-ftp_log-Nov-2026` (1,192,451 transfers, Oct 31 → Nov 25) contains **exactly one
FTP identity** (`elton@torontoevent.net`), **zero failed transfers**, and only Azure/GitHub-Actions
runner ranges. The kit files were pushed through that identity:

- `Mon Nov 23 23:53:05 2026` — `20.171.32.196` → `/public_html/de/index.php` (11,231 B) and `de/visit.txt` (1,875 B at that moment)
- `Tue Nov 24 11:46:04 2026` — `20.168.93.157` → `/public_html/easyapp/index.php` (11,231 B)

So the payload arrived over the same credentials and network path the deploy workflows use. Rotating
the FTP password alone will not stop a repeat: whatever job copies files from a poisoned source tree
must be found. (Same conclusion as 50webs, where the kit also appeared without an FTP-login anomaly.)

**Victim impact on GoDaddy: none observed.** Across 52,469 web requests in November (access + SSL
logs) there were **0** requests to `/de/`, `/appeasy`, `/easyapp`, `visit.txt`, `firstonline`,
`oldyhub`, `BQ2GS5`, `lfeind`, `/bk/` or `error=1`. The 50webs log by contrast recorded 227 real
302 redirects to `oldyhub.com`.

## What was changed

1. **Deleted** (hash-verified against the known kit hashes before each `DELE`):
   - `de/index.php`, `de/visit.txt`, `de/error_log`, then `RMDIR de`
   - `appeasy/index.php`, then `RMDIR appeasy`
   - `easyapp/index.php`, then `RMDIR easyapp`
   - `.htaccess.bak-preipclear-20261125-123519` (76,678 B compromised backup, retained locally as evidence)
2. **Hardened `.htaccess`** — appended a "Data-exposure lockdown" block (Apache 2.4 `RedirectMatch 404`,
   translate phase, so it beats the rewrite rules) covering `.htacl`/`.htaclu`/`.htaccess.*`/`.htpasswd`,
   `.github`/`.easyssl_backup`/`.google-api-private`/`.movies-db-private`, `BACKUPS_*`, `_dbrestore_*`,
   all `.sql|.zip|.tar|.tgz|.bak`, and `_test_all_dbs.php` / `_db_export_tmp.php` / `cursor_test_sql.php`.
   `/audit/`, `/fc/`, `/kimi-claw/`, `/updates/` paths contain none of those patterns.
   Deliberately not blocked: `_sync_tmp/*.php` (absent on this host anyway) and `_db_import_tmp.php`
   (tokenised pipeline endpoint).
   Resulting file: 4,306 B, md5 `6ef9ffa21228139e46db2426567cb7e6`.

## Verification (live HTTP after the change)

```
/                          200      /de/index.php        404
/index.html                200      /appeasy/            404
/riseoftheclaw.html        200      /easyapp/            404
/audit/                    200      /_test_all_dbs.php   404
/fc/                       200      /_db_export_tmp.php  404
/kimi-claw/                200      /cursor_test_sql.php 404
/updates/                  200      /findtorontoevents_antigravity.ca.zip  404
/MOVIESHOWS3/api/get-movies.php 200 /_dbrestore_ejaguiar1_stocks.sql        404
                                    /EJAGUIAR1_MEMECOIN_FIXED.sql           404
                                    /.htaclu            404
                                    /.htacl             404
                                    /.htaccess.bak-preipclear-...           404
```

`/_sync_tmp/ensure_sync_tables.php` returns 404 because the directory does not exist on the host
(confirmed by FTP `NLST`), not because of the new rules.

**Post-deletion second probe (18:12Z):** the three kit paths now answer **403** (bare 13-byte Apache
`403 Forbidden`) rather than 404, while a control path (`/zzz-nonexistent-check-9871/`) still returns
404. FTP `NLST` at the same moment reports `de`, `appeasy`, `easyapp` all **ABSENT**, so this is a
host/WAF block on those known-bad URLs, not the directories returning. Treat 403 as "not served" —
the payloads are gone from disk.

## Evidence kept

- `/tmp/gd/evidence/` — kit `index.php` ×3, `visit.txt`, `error_log`, compromised `.htaccess` (76,678 B),
  remediated `.htaccess` (4,306 B), `.htacl`, `.htaclu`
- `/tmp/gd/ftp.torontoevent.net-ftp_log-Nov-2026` (218 MB decompressed), `torontoevent.net-Nov-2026`,
  `torontoevent.net-ssl_log-Nov-2026`, `gd_listing.txt` (13,895-line recursive listing)
- Copy filed on the operator's desktop: `C:\Users\zerou\Desktop\VIRUS CLEANUP - torontoevent.net - godaddy\`

## Still open

1. **Rotate the FTP password and the `elton` Basic-auth password** — the MD5-crypt hash was publicly
   downloadable at `/.htaclu` until this change and is also present on 50webs and in its `BACKUPS_FEB012026/`.
2. **Find the deploy job** that wrote `de/index.php` from a runner; a password rotation alone does not
   remove a poisoned source tree that an automated FTP step copies to the docroot.
3. Decide whether to delete (not just 404) the 43 `.sql` dumps and the 52 MB repo zip. They are now
   unreachable over HTTP but still occupy the docroot and would be exposed again by any `.htaccess` reset.
4. `_db_import_tmp.php` remains token-protected in the docroot; consider moving the sync tooling
   outside `public_html`.
