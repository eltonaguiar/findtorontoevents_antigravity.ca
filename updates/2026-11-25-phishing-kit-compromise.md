# 2026-11-25 — reCAPTCHA-gate phishing kit on the 50webs account

**Status:** confirmed compromise, **not yet eradicated** (read-only investigation only; no files changed).
**Trigger:** external notification that `https://findtorontoevents[.]ca/de/index.php?error=1` (162.210.101.36)
was hosting a phishing page targeting **easybank AT** (`http://www.easybank.at`).

## What it is

A single-file PHP **cloaking gate**. It shows a plausible "Security check" page, verifies the
visitor with reCAPTCHA v3, logs them, then 302-redirects to the real credential-harvesting page
on an attacker-controlled domain.

```
victim link  ->  <site>/(([a-z]\d){5}/)(.*/)(.*/)(.*)      <- .htaccess RewriteRule
             ->  de/index.php                              <- reCAPTCHA v3 gate (score >= 0.5 + honeypot)
             ->  visit.txt                                 <- appends "HUMAN VISIT" line
             ->  302 https://oldyhub.com/BQ2GS5/{firstonline|lfeind}/firstonline/bk/
```

Two builds were deployed:

| Build | Size | md5 | `ALLOWED_HOSTNAME` | `REDIRECT_URL` |
|---|---|---|---|---|
| A | 11,231 B | `586b76b00d80965e71182fadf67c2d76` | `findtorontoevents.ca` | `https://oldyhub.com/BQ2GS5/firstonline/bk/` |
| B | 11,449 B | `4ec0bec91eeb47d31ad895c9e6334067` | `tdotevent.ca` | `https://oldyhub.com/BQ2GS5/lfeind/firstonline/bk` |

Build A's reCAPTCHA site key: `6LcPqy8uAAAAAH2Q1xna1sW7ZMUovgXxfwVTjl2D`.
Build B's: `6LfVpC8uAAAAAEx69ILoPfTCng-Nb1hP9Gwfk4Cu`.
(Secrets redacted here; the full source is preserved as evidence, not in this repo.)

The gate writes victims to `de/visit.txt` — **only** IP, URI, user-agent. Credentials are
harvested on `oldyhub.com`, not on our servers.

## The `.htaccess` (both 50webs docroots)

`/findtorontoevents.ca/.htaccess` and `/tdotevent.ca/.htaccess`, both **76,799 bytes /
3,095 lines**, md5 `f0896d28c0d27e35ffd3c7360a2e319d`, mtime `2026-11-24 04:55:03`. It replaced the legitimate docroot file wholesale.
Only 8 lines are not `deny from`:

```
RewriteEngine on
RewriteRule (([a-z]\d){5}/)(.*/)(.*/)(.*) de/index.php [L]
<Files 403.shtml>
order allow,deny
allow from all
</Files>
Options -Indexes
##Off to the Mouse they go##
```

Followed by **3,088 unique `deny from` entries** (AWS/Azure/Google/scanner ranges) to hide the
phish from analysis tools. The trailing taunt string is a known kit marker.

## Full account inventory (swept all 12 vhosts)

| vhost | state |
|---|---|
| `findtorontoevents.ca` | **compromised** — `de/index.php`, `de/visit.txt`, `appeasy/index.php`, `easyapp/index.php`, `de-de`, malicious `.htaccess` |
| `tdotevent.ca` | **compromised** — identical set, identical `.htaccess` mtime/size |
| `ejaguiar1.50webs.com` | **compromised** — `de/index.php` (build B, 11,449 B, 05:03) |
| `torontoeventsvamp.50webs.org` | **compromised** — `e/index.php` (build B, 11,449 B, 05:01) |
| `torontoevent.net` (GoDaddy, 132.148.176.163) | **compromised** — `de/`, `appeasy/`, `easyapp/`, `de-de`, `de/visit.txt`, kit rewrite **active** |
| `fixwindows.50webs.org`, `surftorontoevents.50webs.org`, `friendpair2.50webs.org`, `ZZZ_OLD`, `mysqlbackup`, `servicenow`, `C:` | no kit artefacts found |

### Correction to the outside review

A second-opinion review concluded *"torontoevent.net is clean"* and *"torontoeventsvamp.50webs.org
clean"*. **Both are wrong**, as measured on 2026-11-25.

Evidence that torontoevent.net is compromised (live HTTP responses, not FTP inference):

```
/de/                    200  4,277 B  <title>Security check</title>
/de/index.php?error=1   200  2,810 B  <title>Security check</title>
/appeasy/index.php      200  4,277 B
/easyapp/index.php      200  4,277 B
/de-de                  200      0 B
/de/visit.txt           200 79,366 B   <-- victim log served publicly, byte-identical to 50webs
/a1b2c3d4e5/easybank/firstlevel/x/   200 4,277 B   <-- arbitrary letter-digit prefix rewrites to the gate
```

An arbitrary prefix rewriting to the gate proves the kit's `.htaccess` `RewriteRule` is installed
on that docroot too. The homepage (`/`, 363,720 B) and `/admin/` (`Admin - BESTIEJOB`) are intact,
which is why a surface check called it clean.

## Live victim volume

From `de/visit.txt` (79,366 B, identical md5 `5dd2330b…` on all three domains):

- **351** verified-human visits, **237** unique `ip=`, score range 0.70–0.90
- **2026-11-24 04:54:25 → 2026-11-25 11:39:20**
- campaign paths: `easyapp/firstlevel` 205, `easybank/firstlevel` 63, `appeasy/firstlevel` 38,
  `/de/` 20, `easybank/first` 18, `/de/index.php` 7

`visit.txt` is PII (victim IP + UA). It is downloadable without authentication on
`torontoevent.net`. Preserve it for the abuse report / law enforcement; do **not** commit it.

## Why every URL 403s on the 50webs sites

Not the deny list — our egress IP (142.181.219.3) does not appear in it. `tdotevent.ca` returns
`Server unable to read htaccess file, denying access to be safe`, i.e. the host can no longer read
the docroot `.htaccess` and denies the vhost. This is consistent with 50webs nulling the vhost
after the abuse report. FTP still works, which is why the files are still present.

## Homepage integrity

`index.html` is **not** defaced on either site. Deployed `index.html` (363,266 B) differs from the
repo copy only in the build-version string (`2026-11-25-40185c0b`) and the "Updated daily" date.
No phishing IOCs appear in the repo homepage.

## Attack timeline

| time (UTC) | event |
|---|---|
| 2026-11-24 04:55:03 | kit `.htaccess` (76,799 B) written to both docroots |
| 2026-11-24 05:01:18 | `torontoeventsvamp.50webs.org/e/index.php` (build B) |
| 2026-11-24 05:03:19 | `ejaguiar1.50webs.com/de/index.php` (build B) |
| 2026-11-24 06:21:12 | `de/index.php` (build A) on both sites |
| 2026-11-24 16:13:22 | `easyapp/index.php` (build A) on both sites |
| 2026-11-25 10:13:24 | `de-de` marker files |
| 2026-11-25 10:14:36 | `appeasy/index.php` (build A) on both sites |
| 2026-11-25 11:39:20 | last victim-log write |

The `visit.txt` counter is still growing, so the kit was live and receiving traffic at the time of
this review.

## Entry vector

Files carry FTP-style timestamps and were written straight into multiple docroots, including a
replacement `.htaccess`. Nothing in this repo creates `de/`, `appeasy/`, `easyapp/`, `de-de`, or an
oversized `.htaccess`, and no workflow deploys those paths — so this was out-of-band, consistent
with stolen FTP/control-panel credentials for the shared account rather than an app upload bug.

Contributing exposure worth closing regardless:

- `groksstuff.txt` is **tracked in this public repo** and contains plaintext MySQL credentials for
  `mysql.50webs.com`.
- `.env` (untracked, present locally) holds `FTP_SERVER/FTP_USER/FTP_PASS`.
- Ancient third-party apps remain deployed on the docroots (`cakephp/` from 2022, `luxcal/`),
  which are known-vulnerable and give a second path to write files.

## Remediation status

| step | state |
|---|---|
| Evidence captured (kit source, `.htaccess`, `visit.txt`) | done (local, outside repo) |
| Read-only sweep of all 12 vhosts | done |
| Remove kit files + dirs | **not done** — `tools/security/purge_phishing_kit.py` ready, dry-run first |
| Restore clean docroot `.htaccess` | **not done** — candidate: `/BACKUPS_FEB012026/.htaccess` (1,143 B) |
| Rotate FTP / control-panel / MySQL passwords | **not done** (50webs FTP password rotated; the value was exposed in this session's tool output and needs rotating again) |
| Ask 50webs to re-enable vhosts + supply access logs | **not done** |
| Report `oldyhub.com` (Cloudflare-fronted) + submit to Safe Browsing / PhishTank | **not done** |
| Purge `visit.txt` from any public exposure | **not done** — currently served publicly on torontoevent.net |

## Coordination

Findings published to the COMS bus on 2026-11-25 17:01Z:

- retained note `notes/buffy-phishing-kit-2026-11-25` (4,063 B, full IOC set)
- retained broadcast `mentions/all` (one-paragraph wake summary)
- seat `inbox/gx10-c9b9/findtorontoevents_antigravity-ca/buffy-dsv4flash-security`

`COMS guard` reported both payloads clean (no secrets). Victim PII was deliberately excluded from
the bus; `visit.txt` stays in the local evidence directory only. Note that `mentions/all` is
last-writer-wins, so this broadcast superseded the previous retained one (that content survives in
`inbox/.../all` and `reports/r01_fill_verdict_2026-11-23.md`).

## Verification performed

- HTTP status/size/title probes of 25+ kit paths on each of the three public domains.
- FTPS `MLSD` inventory of every vhost; md5 of every kit file and of `visit.txt`.
- Byte-level diff of deployed `index.html` vs `TORONTOEVENTS_ANTIGRAVITY/index.html` in this repo.
- urlscan.io record `01a21282-cb7a-75de-815d-84cbc98da25b` (2026-11-25 11:41) shows a SendGrid
  click-tracker redirect landing on `findtorontoevents.ca/d1b3l4l5m3/appeasy/firstlevel/` with a
  German locale and the localized 403 — confirming the campaign is being mailed out with our domain.
- `oldyhub.com` resolves to Cloudflare (172.64.80.1) and currently returns 403 / "Attention Required".

## Tooling validation

`tools/security/purge_phishing_kit.py` dry run on 2026-11-25 enumerated exactly the 12 expected
files plus both docroot `.htaccess` files, and reported md5 matches for every kit gate file:

```
would delete  /findtorontoevents.ca/de/index.php         (11231 B)
... 6 more build-A copies ...
would delete  /ejaguiar1.50webs.com/de/index.php         (11449 B)
would delete  /torontoeventsvamp.50webs.org/e/index.php  (11449 B)
would delete  .../de/visit.txt (79366 B) x2, .../de-de (0 B) x2
/findtorontoevents.ca/.htaccess  76799 B  md5=f0896d28...  <== kit
== would remove: 12 file(s)
```

## Tooling

`tools/security/purge_phishing_kit.py` — dry-run by default; hash-verifies each file before
deleting; writes evidence outside the repo; can restore a clean `.htaccess`:

```
python3 tools/security/purge_phishing_kit.py                      # dry run
python3 tools/security/purge_phishing_kit.py --execute            # delete kit
python3 tools/security/purge_phishing_kit.py --execute \
    --restore-htaccess /path/to/clean.htaccess
```
