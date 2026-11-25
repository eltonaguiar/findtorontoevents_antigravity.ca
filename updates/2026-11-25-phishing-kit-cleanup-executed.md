# 2026-11-25 — Phishing-kit cleanup on the 50webs account (executed)

Companion to `updates/2026-11-25-phishing-kit-compromise.md` (detection + IOCs). This file records
what was actually **changed on the server**, what else the sweep turned up, and how each step was
verified. Operator-authorized in-session ("check for any more .htaccess or any other suspicious items
and perform cleanup").

Scope: the whole 50webs FTP account (`ftps2.50webs.com`, user `ejaguiar1`), 7 vhosts plus
`/ZZZ_OLD` and `/mysqlbackup`. `torontoevent.net` (GoDaddy) was **not** touched — no credentials.

## 1. What was broken

| # | Problem | Evidence |
|---|---|---|
| 1 | Phishing kit live in 8 directories across 4 vhosts | 2 builds: 11,231 B `586b76b00d80965e71182fadf67c2d76`, 11,449 B `4ec0bec91eeb47d31ad895c9e6334067` |
| 2 | `/tdotevent.ca/.htaccess` replaced with a 76,799 B kit file | md5 `f0896d28c0d27e35ffd3c7360a2e319d`, 3,088 `deny from` lines |
| 3 | 20 `.git` repositories inside web roots, being harvested | 17 × HTTP 200 on `.git/objects` + `.git/refs/heads` from 16 IPs, 00:06–07:30 |
| 4 | `.env` with **FTP credentials** at the findtorontoevents.ca docroot | 139 B, keys `FTP_HOST/FTP_USER/FTP_PASS/FTP_ROOT/INCLUDE_EXTS` |
| 5 | 1.4 GB of full-source ZIPs served from docroots | 382 MB + 542 MB × 3 copies |
| 6 | Database-export PHP scripts reachable | `_test_all_dbs.php`, `_test_full_export.php`, `_db_export_tmp.php`, `cursor_test_sql.php` |
| 7 | Basic-auth hash file in docroot (`elton:$1$…`, MD5-crypt) | `.htaclu`, referenced by `.htacl` |

Note on #3: `tdotevent.ca` was still **serving** content throughout (`/`, `/fc/`, `/audit/` = 200)
while `findtorontoevents.ca` was 403 site-wide, so `https://tdotevent.ca/favcreators/.git/HEAD`
returned **200 before this cleanup**. That exposure was live, not historical.

## 2. What was changed

### 2.1 Deleted — phishing kit (all hash-verified pure kit first)

| Path | Contents |
|---|---|
| `/findtorontoevents.ca/de` | `index.php` (kit), `visit.txt` (79,366 B victim log) |
| `/findtorontoevents.ca/appeasy` | kit `index.php` |
| `/findtorontoevents.ca/easyapp` | kit `index.php` |
| `/tdotevent.ca/de`, `/appeasy`, `/easyapp` | same three |
| `/ejaguiar1.50webs.com/de` | kit `index.php` (build B) |
| `/torontoeventsvamp.50webs.org/e` | kit `index.php` (build B) |
| `/findtorontoevents.ca/de-de`, `/tdotevent.ca/de-de` | 0-byte kit marker files |

Guard applied before deletion: every file in every target directory was downloaded, hashed and
confirmed to be one of the two kit builds or `visit.txt`; any unknown file or subdirectory would have
aborted that directory. Result: **10/10 targets pure kit**, 10 files removed.

### 2.2 Replaced — docroot `.htaccess`, both main vhosts

`/tdotevent.ca/.htaccess` (76,799 B kit file) replaced with the operator's known-good 1,062 B file
(`cb11d51c1001cb46f3f28706ca45ee82`, already live on findtorontoevents.ca) plus a hardening block.
`/findtorontoevents.ca/.htaccess` received the same hardening block. Final content on both:
**1,434 B, md5 `940530d4212d6ef500e4680c9d2a049f`**, verified by re-download after `STOR`.

```apache
# --- 2026-11-25 security hardening (phishing-kit incident, by buffy) ---
RedirectMatch 404 (?i)/\.(git|svn|hg)
RedirectMatch 404 (?i)QUARANTINE
RedirectMatch 404 (?i)/\.env
RedirectMatch 404 (?i)/\.(htacl|htaclu|htpasswd|netrc|my\.cnf)
RedirectMatch 404 (?i)\.(swp|swo|bak|old|orig)$
RedirectMatch 404 (?i)^/_(test|db_export|tmp)
RedirectMatch 404 (?i)^/cursor_test_sql
```

`RedirectMatch 404` was chosen over `Require all denied` because this host still honors 2.2-style
access directives, and it does not interfere with `.well-known` ACME renewals.

### 2.3 Quarantined — renamed, recoverable, not deleted

| Original | New name |
|---|---|
| 20 × `.git` dirs (see §3) | `.git_QUARANTINE_2026-11-25` |
| `/findtorontoevents.ca/.env` | `.env.quarantine-2026-11-25` |
| `/findtorontoevents.ca/findtorontoevents_antigravity.ca.zip` (382 MB) | `…zip.quarantine-2026-11-25` |
| `/tdotevent.ca/findtorontoevents_antigravity.ca.zip` (382 MB) | same |
| `/tdotevent.ca/TORONTOEVENTS_ANTIGRAVITY (2).zip` (542 MB) | same |
| `/tdotevent.ca/tdotevent.ca/TORONTOEVENTS_ANTIGRAVITY (2).zip` (542 MB) | same |
| `/torontoeventsvamp.50webs.org/tdotevent.ca/TORONTOEVENTS_ANTIGRAVITY (2).zip` | same |

Renaming rather than deleting follows the workspace rule *trash > rm*: the exposure is removed
instantly, the data stays recoverable, and the `QUARANTINE` 404 rule keeps every quarantined path
unreachable over HTTP even if a file is renamed back by hand.

The 20 `.git` directories quarantined: `BACKUPS_FEB012026`, `STOCKSUNIFY`,
`STOCKSUNIFY/STOCKSUNIFY2`, `TORONTOEVENTS_ANTIGRAVITY`, `WINDOWSFIXER/MiracleBoot_v7_1_1`,
`WINDOWSFIXER/MiracleBoot_v7_1_1 - Github code`, `favcreators`, `favcreators_source` on each of
findtorontoevents.ca and tdotevent.ca (16), plus two under `fixwindows.50webs.org`, one at
`surftorontoevents.50webs.org`, and one at
`torontoeventsvamp.50webs.org/tdotevent.ca/TORONTOEVENTS_ANTIGRAVITY`.

## 3. Verification (measured after each step)

| Check | Before | After |
|---|---|---|
| `tdotevent.ca/favcreators/.git/HEAD` | **200** | **404** |
| `tdotevent.ca/de/index.php` | 200 (kit) | **404** |
| `tdotevent.ca/appeasy/`, `/easyapp/` | 200 | **404** |
| `tdotevent.ca/de/visit.txt` | 200 | **404** |
| `ejaguiar1.50webs.com/de/index.php` | 200 (kit) | **404** |
| `tdotevent.ca/_test_all_dbs.php` | 403/412 | **404** |
| `tdotevent.ca/_db_export_tmp.php` | 412 | **404** |
| `tdotevent.ca/cursor_test_sql.php` | 412 | **404** |
| `tdotevent.ca/TORONTOEVENTS_ANTIGRAVITY (2).zip` | 412 | **404** |
| `tdotevent.ca/.env`, `.htacl`, `.htaclu` | 403 | 403 (plus rule) |
| `tdotevent.ca/` | 200 | 301 → `/index.html` **200** |
| `tdotevent.ca/index.html` | 200 | **200** |
| `tdotevent.ca/fc/`, `tdotevent.ca/audit/` | 200 | **200** |
| `findtorontoevents.ca/*` | 403 | 403 (host lockdown, unchanged) |

Site function preserved: the root redirect resolves to a 200, and `/fc/` + `/audit/` still serve.

## 4. Full `.htaccess` sweep result

147,319 unique entries (101,673 files) across all vhosts; **166 `.htaccess` files**, 50 distinct
contents, each downloaded and hashed:

- **1 compromised** — `/tdotevent.ca/.htaccess` (kit file). Now clean.
- **14 files / 7 contents flagged WAF-OFF** — all ours (`_next/.htaccess`, `favcreators/.htaccess`,
  `findevents/*/api/.htaccess`, `next/_next/**`). One of them,
  `favcreators/.htaccess`, contains `SecRuleRemoveById 1-999999`, which disables **every** ModSecurity
  rule for the directory holding the OAuth callback and the API. Worth narrowing to the specific rule
  IDs that Google OAuth actually trips.
- **0** `auto_prepend_file` / `auto_append_file` backdoors anywhere.
- **0** unknown PHP handlers outside the 4 known API `.htaccess` files.

The earlier "17 review" count dropped to 14 because the duplicate-path bug in the first scan is fixed
(the account root was being scanned three times).

## 5. Open items — not done here

1. **Rotate the FTP password and the Basic-auth password.** `.env` held `FTP_PASS` and `.htaclu`
   holds a crackable MD5-crypt hash for user `elton`. Both were exposed in a docroot; treat as
   compromised regardless of the 403s.
2. **`torontoevent.net` (GoDaddy)** still serves the kit and a public `de/visit.txt`. Needs GoDaddy
   credentials — no action taken.
3. **Attacker may still hold write access.** `easyapp/index.php` on both .ca vhosts carried an
   mtime of **16:13**, after the 13:22 HTTP lockdown, while `de/` was 06:21 and `appeasy/` 10:14.
   Content was byte-identical to the 06:21 build, so this was a copy rather than a new variant — but
   it means someone could still write over FTP after the host started blocking HTTP. **Rotate before
   trusting the cleanup.**
4. **Narrow `SecRuleRemoveById 1-999999`** to the rule IDs OAuth actually triggers.
5. **Ask 50webs for access logs / panel login IPs** for the window 2026-11-24 04:00 → 2026-11-25 18:00.
6. **Report `oldyhub.com`** to Cloudflare abuse and Google Safe Browsing / PhishTank.
7. Decide whether the quarantined `.git` dirs should be deleted outright once the rotation is done.

## 6. Artefacts

- Cleanup manifest (every rename, plus errors): `/tmp/clean/cleanup_manifest.json` on the analysis host.
- Evidence copies: `/tmp/clean/evidence/` — both `visit.txt` (md5 `5dd2330b2eb700f80a9c223d74fb20ee`),
  every kit `index.php`, the compromised `tdotevent.ca/.htaccess`, and the pre-change
  `findtorontoevents.ca/.htaccess`.
- Victim PII archive (unchanged by this work): `PII_law_archive_2026-11-25_<domain>.MD` on the
  operator desktop, one per domain.
