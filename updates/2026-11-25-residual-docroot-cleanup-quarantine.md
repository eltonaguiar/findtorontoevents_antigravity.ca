# Residual docroot cleanup — torontoevent.net, tdotevent.ca, findtorontoevents.ca

**Date:** 2026-11-25
**Scope:** `torontoevent.net` (GoDaddy), `tdotevent.ca` and `findtorontoevents.ca` (50webs). `torontoevents.net` deliberately excluded — it is a GoDaddy parked/wildcard domain, not ours.
**Trigger:** follow-up to the phishing-kit cleanup ("cleanup everything remaining"). The kit itself was already gone; what remained were leftovers from the incident *and* older test/debug artifacts that had nothing to do with the kit but were still being served.

---

## Headline: three things were still live on torontoevent.net

Before this pass, these returned **200 with content** from `https://torontoevent.net/`:

| URL | Status before | What it exposed |
|-----|---------------|-----------------|
| `/_test_php_export.php` | 200 (9 B) | Plaintext credentials for **5 databases** (`ejaguiar1_sportsbet`, `ejaguiar1_tvmovietrailers`, `ejaguiar1_favcreators`, `ejaguiar1_deals`, `ejaguiar1_news`) plus a `mysqldump` / `mysql_connect` export path |
| `/_test_php_export2.php` | 200 (9 B) | Same family of export helper |
| `/_test_dbex_minimal.php` | 200 (27 B) | `{"status":"ok","test":true}` — DB-exec reachable through PHP |
| `/security_audit.php` | 200 (2,383 B) | Internal XSS/SQLi audit output |
| `/phpinfo.txt` | 200 (16,521 B) | Full `phpinfo()` dump — paths, PHP config, module/env detail |
| `/_test_full_export.php` | 500 | Fatal-ed but still reachable/executing |
| `/events_backup.json` | 200 (853,937 B) | Second copy of the events dataset |

The root `.htaccess` rule added earlier only covered `_test_all_dbs`, `_db_export_tmp` and `cursor_test_sql` by name, so the rest of the family slipped through. PHP executes server-side, so the credentials in those files were not readable as source; the exposure was an unauthenticated export/diagnostic endpoint plus the `phpinfo.txt` disclosure.

---

## What was done

### 1. Quarantine directories (nothing deleted)

Each of the three docroots got `_QUARANTINE_2026-11-25/` containing a deny-all `.htaccess`:

```apache
Options -Indexes
<IfModule mod_authz_core.c>
  Require all denied
</IfModule>
<IfModule !mod_authz_core.c>
  Order allow,deny
  Deny from all
</IfModule>
```

Leftovers were **renamed into** that directory (FTP `RNFR`/`RNTO`, same filesystem, instant even for the 382 MB / 542 MB archives) rather than deleted, because most of it is irreplaceable data: SQL dumps of every production database, `BACKUPS_FEB012026/`, `_backups/`, `backups/`, `db_backups/`, the full-site `.zip` archives, and ~45 historical `index.html.bak*` copies per 50webs vhost.

| Docroot | Items quarantined | Root entries before → after |
|---|---|---|
| GoDaddy `/` | 53 + 103 = **156** | 623 → 468 |
| `findtorontoevents.ca` | **37** (33 + 3 + `tmp/`) | 291 → 253 |
| `tdotevent.ca` | **45** (41 + 3 + `tmp/`) | 302 → 256 |

Representative contents now in quarantine on GoDaddy: `BACKUPS_FEB012026/`, `BACKUPS…`, `_dbrestore_*.sql` (28 files), `EJAGUIAR1_MEMECOIN_FIXED.sql`, `STOCKS_FEB162026_FIXED.sql`, `findtorontoevents_antigravity.ca.zip`, `.github/`, `.google-api-private/`, `.movies-db-private/`, `.easyssl_backup/`, `.htacl`, `.htaclu`, `_test_php_export*.php`, `_test_full_export.php`, `_test_dbex_minimal.php`, `_test_php52.php`, `security_audit.php`, `phpinfo.txt`, `_backups/`, `index.html.bak`, `events_backup.json`, all `debug*`/`temp*`/`test_output*`/`__next.*`/`chunk_*_context.txt` scratch files, and two files with Windows-path names (`efindtorontoevents_antigravity.ca…json`).

On the 50webs vhosts: `index.html.bak*` (22 per vhost), `index.html.bak2`, `index.backup-before-simple.html`, `events_backup.json`, `.htaccess.bak-20261125-{gitblock,pii}`, `.env.quarantine-2026-11-25`, `.htacl` + `.htaclu` (tdotevent.ca), `.github/`, `.google-api-private/`, `.movies-db-private/`, `BACKUPS_FEB012026/`, `_backups/`, `backups/`, `db_backups/` (tdotevent.ca), the `_test_*.php.quarantined-20261125` set, the two big `.zip.quarantine-2026-11-25` archives, `debug-events.html`, `index.txt`, `index_formatted.html`, and `tmp/`.

`tmp/` was checked before moving: it holds stale `hot_trending_*.json` / `cmc_trending.json` caches from Feb–Nov 2026 and an orphan `a2ac.js`. No page, script or workflow in the repo references any of them (the only mentions of those names are in `mirror-site.yml`'s malformed-name exclude and two historical update notes), so moving it cannot break a live fetch.

### 2. `.htaccess` — GoDaddy root

Appended a residual-sweep block; file grew **4,816 B → 5,337 B**:

```apache
# --- 2026-11-25 residual sweep: test/export scripts, info dumps, scratch files ---
RedirectMatch 404 (?i)^/_(test|tmp|db_restore|db_export)[^/]*
RedirectMatch 404 (?i)^/(security_audit|phpinfo)[^/]*
RedirectMatch 404 (?i)^/__next[.]
RedirectMatch 404 (?i)^/(test_output|test_results|final_check|final_text|page_content|proxied_output|ftp_list|index[.]txt|index_formatted|append_temp)
RedirectMatch 404 (?i)^/e.*findtorontoevents_antigravity[.]ca
RedirectMatch 404 (?i)[.]quarantined
RedirectMatch 404 (?i)^/_QUARANTINE
```

The 50webs root `.htaccess` (2,433 B, md5 `5f7c084b…`, identical on both vhosts) already covered this class — `.env`, `.bak`, `.sql`, `db_backups`, `BACKUPS_`, `_dbrestore_`, `_test|db_export|tmp`, `QUARANTINE` — so no change was needed there.

### 3. Leaked Basic-auth hash taken out of the docroot

`.htaclu` (42 B, MD5-crypt for user `elton`) and its `.htacl` config were present at the root of GoDaddy and `tdotevent.ca`, and the file had been publicly readable before the earlier 404 rule. Both are now in quarantine on all three domains. They were provably **inert**: `.htacl` points at a stale 50webs absolute path (`/services/users/z50websp3/ejaguiar1/www/findtorontoevents.ca/.htaclu`) that does not exist on GoDaddy, no `.htaccess` includes them, and every site root still returns 200/301 rather than 401 — so removing them breaks no authentication.

---

## Verification (measured after the change)

**torontoevent.net**

| Path | Result |
|---|---|
| `/`, `/index.html`, `/audit/`, `/fc/` | 200 |
| `/events.json`, `/robots.txt`, `/sitemap.xml.gz`, `/ads.txt` | 200 |
| `/WINDOWSFIXER/MiracleBoot_GitHub.zip` | 200 (1,568,175 B) |
| `/WINDOWSFIXER/MiracleBoot_Cursor.zip` | 200 (4,539,216 B) |
| `/_test_dbex_minimal.php`, `/_test_php_export.php`, `/_test_php_export2.php`, `/_test_full_export.php` | 404 |
| `/security_audit.php`, `/phpinfo.txt` | 404 |
| `/_backups/`, `/events_backup.json`, `/__next.__PAGE__.txt`, `/test_output.txt`, `/ftp_list.txt`, `/index.txt` | 404 |
| `/.htaclu`, `/.htacl`, `/.github/config`, `/index.html.bak`, `/findtorontoevents_antigravity.ca.zip` | 404 |
| `/_QUARANTINE_2026-11-25/` | 403 |

**tdotevent.ca**

| Path | Result |
|---|---|
| `/` | 301 → `/index.html` 200 |
| `/index.html`, `/events.json` (21,052,037 B), `WINDOWSFIXER/MiracleBoot_GitHub.zip` | 200 |
| `/tmp/`, `/tmp/a2ac.js`, `/index.txt`, `/debug-events.html`, `/index.html.bak.1777852084` | 404 |
| `/_QUARANTINE_2026-11-25/`, `/_QUARANTINE_2026-11-25/index.html.bak` | 403 |
| `/.htaclu`, `/.env.quarantine-2026-11-25`, `/.htaccess.bak-20261125-pii` | 403 |

**findtorontoevents.ca** — HTTP is unavailable from this workstation (the host 403s the whole vhost at the edge), so verification was done over FTPS:

| Item | State |
|---|---|
| `index.html`, `events.json`, `.htaccess`, both `WINDOWSFIXER` zips | present, byte sizes unchanged |
| `.htaclu`, `.htacl`, `.github`, `index.html.bak`, `.env.quarantine-2026-11-25` | gone from the docroot |

Kit-path re-check across all three domains stayed as before: `/de/`, `/de/index.php`, `/visit.txt`, `/easyapp/`, `/appeasy/` → 403; `/lander`, `/de-de/` → 404.

---

## Residual risk — credentials

1. **`phpinfo.txt` was downloadable (16,521 B).** Treat anything it showed — include paths, PHP config, any env-sourced values — as disclosed. If DB credentials live in environment variables rather than `db_config.php`, rotate them.
2. **The export scripts embed plaintext passwords for `ejaguiar1_sportsbet`, `ejaguiar1_tvmovietrailers`, `ejaguiar1_favcreators`, `ejaguiar1_deals`, `ejaguiar1_news`.** The source was not served (PHP executes), but the endpoint itself was public and executable until now, and the files sat in a web-readable directory. Rotating those five DB passwords is the only way to be certain.
3. **`.htaclu` held an MD5-crypt hash for `elton`.** If that password is reused for the 50webs/GoDaddy control panel or FTP, change it there — the hash itself is now out of the docroot, but reuse is the real exposure.

## Purging the quarantine later

Once the dumps above are confirmed unnecessary (they duplicate `BACKUPS_FEB012026` and the local MySQL exports), each host's `_QUARANTINE_2026-11-25/` can be removed wholesale; it is deny-all and `.htaccess`-blocked from the web in the meantime. Purging GoDaddy's copy reclaims roughly 450 MB.
