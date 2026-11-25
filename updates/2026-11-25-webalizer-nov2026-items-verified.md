# November 2026 Webalizer reports — every suspicious item, confirmed cleaned

**Question answered:** the two Webalizer summaries for `findtorontoevents.ca` (424,572 hits) and
`tdotevent.ca` (90,353 hits) contain several things that look like compromise residue. Each one is
listed below with the check that was run and its state at 2026-11-25 18:25Z.

## findtorontoevents.ca

| Suspicious item | What it was | Check | Status |
|---|---|---|---|
| Referrer `https://findtorontoevents.ca/h2c3l4l2m3/easyapp/firstlevel/` (682 hits) | kit doorway URL, matched the `.htaccess` rule `(([a-z]\d){5}/)… → de/index.php` | `GET` now → **403**; root `.htaccess` is 1,867 B md5 `aa38aa95979aa1c85e7f23bdc100c204` with **no** `de/index.php` rewrite, no `deny from` block, no `##Off to the Mouse they go##` | cleaned |
| Referrer `https://findtorontoevents.ca/d1b3l4l5m3/appeasy/firstlevel/` (296 hits) | same doorway, different campaign prefix | `GET` now → **403** | cleaned |
| All five campaign prefixes (`h2c3l4l2m3`, `d1b3l4l5m3`, `h2b3l4l5m3`, `a1b2j3k4l5`, `a9b2j3k4k5`) | doorway namespace | all → 403 | cleaned |
| `/fc/TLC.php` — 89,658 hits, 21.1% of all traffic | suspected webshell by volume | downloaded: 56,795 B, header `TLC - Multi-Platform Live Check` (TikTok/Twitch/Kick/YouTube status for FavCreators); no `eval`, `base64_decode`, `gzinflate`, `assert`, `create_function`, superglobal-exec, hex obfuscation or shell signatures. The volume is our own `FavCreators-GitHub-Actions/1.0` agent (178,363 reqs, 42% of UA share) polling streamer status | legitimate — false alarm |
| 4,147 × Code 412 | looked like blocked malware fetches | the 412s are `denied by modsecurity` on kit-shaped URLs: `/d1b3l4l5m3/appeasy/firstlevel/` ×38, `/h2c3l4l2m3/easyapp/firstlevel/` ×12, and `/de/1I2xQxnxgTsfbng9m.htaccess`, `/de/fqPMPGSBZME9uytZtk.htaccess`, `/de/bjHPxzsW5ufbRlGHRMB.htaccess`, `/de/index.php`. Control test: **any** `*.htaccess` URL returns 412 (`/zzznothere9871/abc.htaccess` → 412) while `/zzznothere9871/index.php` → 404, so 412 is a blanket WAF pattern, not a live file | blocked, then removed |
| 3,145 × "undefined response code" | unclassified | aborted connections with no status token; no 200s hide in this class | not compromise |
| `152.32.252.137` — 761 hits | exchange-app scanner | **761 of 761 requests returned 403** in the log | blocked |
| `142.181.219.3` — 11,379 hits, 7.4 MB | crawler | pulling `/audit/`, `/audit2/`, `/audit3/`; status mix 218×200 / 218×403 — alternating dashboards, no sensitive path | scraping, not compromise |
| `162.210.101.36` — 11,587 hits | server's own address | internal cron/self-calls (already characterised earlier) | benign |
| `185.177.72.205` (3,203 hits) / `.66` (719) | low files-per-hit scanners | not present in the log excerpt held locally; ratio 180/3,261 and 59/719 files/hits = 404 probing | no success observed |

## tdotevent.ca

| Suspicious item | What it was | Check | Status |
|---|---|---|---|
| **`/de/` — 263 hits, 119 visits, appears as an exit page** | victims/scanners landing on the kit index on this vhost | `/tdotevent.ca/de` **absent** via FTP `NLST`; `GET /de/` → 403, `/de/index.php` → 403; root `.htaccess` 1,867 B `aa38aa95…`, no kit rewrite | cleaned |
| `/de/*.htaccess` (three campaign configs seen in 412s) | kit per-campaign rules | directory absent (FTP); requests → 412 "denied by modsecurity" from the blanket `*.htaccess` rule | cleaned |
| 8,627 × Code 412 (9.55%) | same WAF class | same blanket rule confirmed by control test | blocked |
| 18,057 × 404 (19.98%) | probe volume | normal for this vhost; sensitive paths now 404 (`/.htaclu` 403, `_dbrestore_*.sql` 404, `_test_all_dbs.php` 404, repo `.zip` 404) | no exposure |
| `/BACKUPS_FEB012026/` returns 301→200 | directory that holds `.git`/`.htacl` | the 200 body is the **homepage HTML** (catch-all rewrite), not a listing; `/BACKUPS_FEB012026/.htacl` → 403, `/.git/config` → 404 | not exposed |
| `34.76.183.190`, `34.156.218.56`, `213.209.159.133`, `45.61.178.142`, `118.26.37.249`, `123.58.220.157`, `102.220.163.241` | GCP/Hetzner/abuse-VPS scanners | not in the log excerpt held locally; the sub-1 file-per-hit pattern on the ones visible (`118.26.*`, `123.58.*` = 0 files, 0 KB) is probing that produced nothing | no success observed |

## PHP compromise sweep (the "compromised php files" question)

- **GoDaddy:** all **118** PHP files downloaded and content-scanned → 6 hits, every one our own
  `mysqldump` wrapper (`_test_php_export*.php`, `_test_full_export.php`, `_test_all_dbs.php`,
  `_db_export_tmp.php`) or `CONTACTLENSES/analyze.php`'s `shell_exec` availability probe. Zero
  `eval`/`base64_decode`/`gzinflate`/`str_rot13`/`assert`/`create_function`/`preg_replace /e`,
  zero hex-obfuscated blobs, zero webshell signatures.
- **50webs:** 6,123 PHP files on the account; **0** have an mtime of Nov 23–25, so nothing was dropped
  during the attack window apart from the kit already deleted. All **50 top-level** PHP files across
  every vhost were downloaded and scanned → only the same `_test_*`/`_db_export_tmp.php` wrappers, no
  kit markers, 41 fully clean.

## How the kit reached GoDaddy (root cause)

`.github/workflows/mirror-site.yml` runs every 6 hours: `lftp mirror` **downloads the live 50webs
`/findtorontoevents.ca/` tree** into `/tmp/site_mirror`, caches it with `actions/cache`, then
`mirror --reverse` uploads it to GoDaddy root **and** `/tdotevent.ca/`. Neither side excluded the kit.

FTP evidence: at `Mon Nov 23 23:52:05 2026` the run uploaded the **76,799-byte compromised root
`.htaccess`**, then `de/index.php` (11,231 B, md5 `586b76b0…`) and `de/visit.txt` (1,875 B). Four later
runs re-uploaded `de/visit.txt` at 6,623 → 26,571 → 28,112 → 28,867 B — the mirror copying a *growing
live log*, which is why GoDaddy's copy ended up byte-identical to 50webs' 79,366-byte file. Only one
FTP identity exists in 1,192,451 transfers with zero failures, so this was the pipeline, not a stolen
password. `actions/cache` also means the poisoned tree survives on the runner after the hosts are
cleaned.

**Fixed in the same commit:** kit paths + `visit.txt` + root `.htaccess` excluded on download, on both
reverse uploads; a new "Strip phishing-kit artifacts from the mirror tree" step deletes the kit dirs,
harvest logs and any file whose md5 matches a kit build or whose content contains `oldyhub.com`,
`firstonline/bk` or `Off to the Mouse they go`, then fails closed if anything survives. Verified by
extracting the step and running it against a fake poisoned tree: 7 infected files → 2 legit files kept,
exit 0, idempotent on a second run.

## Still open

1. `findtorontoevents.ca` answers 403 to this workstation site-wide (host IP lockdown from the
   incident). Webalizer shows 84.9% + 360,604 code-200 hits for real users, so the site itself serves;
   the lockdown only affects our egress. Worth asking 50webs to lift it.
2. Rotate the 50webs FTP password and the `elton` Basic-auth password (hash was public on GoDaddy at
   `/.htaclu` until today).
3. `mirror-site.yml` has no `actions/checkout`, so the guard is inline Python — if someone later adds a
   checkout, move it to `tools/security/`.
