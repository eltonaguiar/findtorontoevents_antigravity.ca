# 50webs account — post-cleanup re-sweep (2026-11-25, after the GoDaddy comparison)

Re-checked the 50webs host against the attack landscape recovered from the GoDaddy logs
(`torontoevent.net-Nov-2026`, `torontoevent.net-ssl_log-Nov-2026`,
`ftp.torontoevent.net-ftp_log-Nov-2026`) to answer: *is anything from that landscape still
deployed on 50webs?*

## Result: no kit remains; 50webs is the clean host of the two

Same kit family, already removed earlier today:

| Vhost | `/de/` | `/de/index.php` | `/de/visit.txt` | `/appeasy/` | `/easyapp/` |
|---|---|---|---|---|---|
| tdotevent.ca | 404 | 404 | 404 | 404 | 404 |
| ejaguiar1.50webs.com | 404 | 404 | 404 | 404 | 404 |
| findtorontoevents.ca | 403 | 403 | 403 | 403 | 403 — host-level lockdown, file confirmed gone by FTP |

`findtorontoevents.ca` 403s site-wide from the host's IP lockdown (unchanged since this morning);
FTP inspection is the authority there and shows the directories deleted.

A later probe at 18:14Z returned **403** (not 404) for `/de/`, `/appeasy/`, `/easyapp/` on
`tdotevent.ca` and `ejaguiar1.50webs.com` as well, while unrelated missing paths still 404. The host
now blocks those known-bad URL patterns at platform level; the directories are deleted on disk either
way (FTP-verified during the cleanup). 403 and 404 are both "not served" here — the difference is only
which layer answers.

## Exposure re-probe (same list used on GoDaddy)

| Path | findtorontoevents.ca | tdotevent.ca | ejaguiar1.50webs.com |
|---|---|---|---|
| `/.htaclu` | 403 | 403 | 404 |
| `/.htacl` | 403 | 403 | 404 |
| `/_test_all_dbs.php` | 403 | 404 | 404 |
| `/_db_export_tmp.php` | 403 | 404 | 404 |
| `/cursor_test_sql.php` | 403 | 404 | 404 |
| `/findtorontoevents_antigravity.ca.zip` | 403 | 404 | 404 |
| `/_dbrestore_ejaguiar1_stocks.sql` | 403 | 404 | 404 |
| `/EJAGUIAR1_MEMECOIN_FIXED.sql` | 403 | 404 | 404 |
| `/.github/config` | 403 | 404 | 404 |
| `/BACKUPS_FEB012026/` | 403 | 301 (dir exists) | 404 |

Nothing is downloadable, but the 403s on `findtorontoevents.ca` are the host lockdown, not our rules —
if that lockdown is lifted, those paths need the same `RedirectMatch 404` block that was just added to
GoDaddy's `.htaccess`.

## Differences worth noting between the two hosts

- **Delivery:** on GoDaddy the kit was uploaded through the account's own FTP identity from
  GitHub-Actions runner IPs (Nov 23 23:53 and Nov 24 11:46). The 50webs FTP/upload path showed no such
  transfer record in what we could inspect, so the shared root cause is best treated as "a poisoned
  source tree that a deploy job copies out", not "an FTP password was guessed".
- **Impact:** 227 real victim redirects on 50webs, zero kit requests on GoDaddy.
- **`.htaccess`:** both hosts had the identical compromised payload (3,083 `deny from` lines +
  `(([a-z]\d){5}/)` → `de/index.php`). 50webs' was replaced during the earlier cleanup; GoDaddy's was
  replaced by the kilo agent at 12:35 and its compromised backup was still downloadable until today.

## Still outstanding on 50webs

1. Rotate the 50webs FTP password and the `elton` Basic-auth password (hash sits in `.htaclu`,
   `BACKUPS_FEB012026/`, `backups/20260131-190426/`).
2. `.htaclu`/`.htacl` (and their backup copies) should leave the docroots entirely.
3. `favcreators/.htaccess` still carries `SecRuleRemoveById 1-999999` — narrow it to the rule IDs the
   OAuth/API endpoints actually need.
4. Quarantined items are de-exposed but not deleted: 20 `.git` dirs (`.git_QUARANTINE_2026-11-25`),
   `.env.quarantine-2026-11-25`, the 1.4 GB ZIPs.
5. Add the GoDaddy-style `RedirectMatch 404` exposure block to the 50webs `.htaccess` so the 403s do not
   depend on the host's IP lockdown.
