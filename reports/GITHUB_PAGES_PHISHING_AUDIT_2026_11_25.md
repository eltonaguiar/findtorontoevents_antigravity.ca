# 2026-11-25 — GitHub Pages / GitHub account phishing audit (following the 50webs + GoDaddy kit)

**Question asked:** "our webpages were compromised, `.htaccess` hacked… can you check our GitHub Pages
for any signs of phishing also? e.g. https://github.com/eltonaguiar/"

**Answer in one line:** **No phishing kit, no kit artefact, and no attacker infrastructure was found on
any GitHub Pages site or repo.** The compromise did **not** reach GitHub. Two credential/access
hygiene issues were found that are unrelated to the phishing content and should still be closed.

Scope of this audit is **read-only**. Nothing was changed on GitHub.

---

## 1. What was checked

| Surface | Count | Method |
|---|---|---|
| Repos on `eltonaguiar` | **105** | `GET /user/repos` (REST), full name/metadata review |
| Pages-enabled repos | **34** | `GET /repos/{r}/pages`, live HTTP probe of each site |
| Live Pages URLs probed | **34** | `urllib`, 25 s timeout, 400 KB body cap |
| Kit-path probes per site | **6 each = 204** | `/de/`, `/de/index.php`, `/easyapp/index.php`, `/appeasy/index.php`, `/de/visit.txt`, `/de-de` |
| Local repo working tree | 1 tree | regex sweep for all kit IoCs |
| Local repo git history | **all branches** | `git log --all --diff-filter=A -- '*de/index.php' '*easyapp/*' '*appeasy/*' '*de-de' '*visit.txt' '*e/index.php'`, plus `git rev-list --all --objects | grep htaccess` |
| Tracked `.htaccess` files | 10 | size + md5 vs the 76,799 B kit payload |
| Mirror-repo workflows | 42 | host allowlist + exfiltration pattern grep |
| GitHub code search | account-wide | `oldyhub`, kit reCAPTCHA keys, `easybank`, `appeasy`, taunt string |

### IoC set used (recovered from the 2026-11-25 compromise)

`oldyhub.com` · `Off to the Mouse they go` · reCAPTCHA site keys `6LcPqy8uAAAAAH2Q1xna1sW7ZMUovgXxfwVTjl2D`
and `6LfVpC8uAAAAAEx69ILoPfTCng-Nb1hP9Gwfk4Cu` · `appeasy` · `easyapp` · `de/index.php` ·
`de/visit.txt` · `de-de` · a `.htaccess` of 76,799 B / 3,095 lines with `(([a-z]\d){5}/)` → `de/index.php`

---

## 2. Result per Pages site — all clean

All 34 sites returned **HTTP 200** (one is a dead site, see below), **zero IoC hits**, and **zero
non-404 responses** on the 6 kit-path probes.

Only three sites raised any generic indicator, and all three are benign:

| Site | Indicator | Triage |
|---|---|---|
| `eltonaguiar.github.io/findtorontoevents_antigravity.ca-archive-2026-05-23/` | `<meta http-equiv="refresh">` | Benign — 260 B stub redirecting to **`./hub/`** (same origin, "Redirecting to Trading Systems Hub") |
| `eltonaguiar.github.io/findtorontoevents.ca/` | `<input type="password">` | Benign — `<form id="signin-form" onsubmit="return false;" autocomplete="off">`, **no `action` attribute**, and `signin-password` is **never referenced by any JS**. No `fetch`/`XHR`/`sendBeacon` target leaves the origin. Nothing to harvest, nothing to exfiltrate. |
| `eltonaguiar.github.io/EBOND_ServiceNowSalesforce_RUN/` | HTTP 404 | Dead site (Pages reports `status: null`, never built). Not a risk — no content served. |

### External hosts referenced across all 34 sites

Every outbound host is legitimate and expected:

`findtorontoevents.ca`, `tdotevent.ca` (own domains) · `cdnjs.cloudflare.com`, `cdn.jsdelivr.net`,
`unpkg.com`, `fonts.googleapis.com/gstatic.com`, `img.shields.io`, `schema.org`, `w3.org` (CDNs /
standards) · `pagead2.googlesyndication.com` (AdSense) · `api.binance.com`, `api.okx.com`,
`alternative.me` (price feeds) · YouTube, TMDB, Eventbrite, Ticketmaster, BlogTO, NowToronto,
Toronto.ca (events/movies) · ServiceNow + Workday/CIBC/BMO/GDIT/Cognizant/Wipro/LinkedIn/Indeed
(job-hunt boards) · BetterHelp/Calm/7cups/crisistextline/Stanford/BMJ/JAMA/Wiley/Canada.ca
(mental-health resources).

**No `oldyhub.com`, no URL shortener, no unknown VPS/bulletproof domain, no Dynamic DNS host.**

---

## 3. Result per repo — the kit never entered source control

* **Working tree:** the only files containing kit IoCs are *my own* post-incident records —
  `updates/2026-11-25-*.md` and `tools/security/purge_phishing_kit.py`. No `de/`, `easyapp/`,
  `appeasy/` or `de-de` directories exist (the only `de` dirs found are `pycountry/locales/de` and
  git object shards).
* **Git history, all branches:** the path query returned **nothing**. No commit, on any branch, has
  ever added `de/index.php`, `easyapp/*`, `appeasy/*`, `de-de`, `visit.txt` or `e/index.php`.
* **Tracked `.htaccess` files (10):** largest is 2,433 B (`audit_dashboard/.htaccess`). **None is
  76,799 B**, none is md5 `f0896d28c0d27e35ffd3c7360a2e319d`, none contains the
  `(([a-z]\d){5}/)` rewrite rule.
* **Separate `eltonaguiar/findtorontoevents.ca` mirror repo:** root `.htaccess` is 2,235 B / 53
  lines of ordinary redirects (`api/`, `servicenow/`, `movieshows3` → `MOVIESHOWS3`, `next/static/*`
  → `_next/static/*`). Clean. No `de/`, `easyapp/`, `appeasy/` in the tree.
* **Account-wide code search** for the IoCs: empty.
* **Repo names:** 105 repos reviewed for bank/payment/lookalike naming — no hits. Forks are
  innocuous (`hermes-agent`, `bulbasaur`, and two 2018 Qlik repos).

---

## 4. Supply-chain / persistence checks

* **Webhooks:** none on `findtorontoevents_antigravity.ca`, `findtorontoevents.ca`,
  `TORONTOEVENTS_ANTIGRAVITY`, the archive repo, `BESTIEJOB`, or `GTA5TORONTOTRACKER`. No attacker
  callback channel.
* **Deploy keys:** none except one on the archive repo — **flagged below**.
* **Custom domains on Pages:** **none of the 34 sites has a `cname`.** This is good news: there is no
  brand subdomain pointed at GitHub Pages, so there is no subdomain-takeover path into our brand from
  this account.
* **`eltonaguiar.github.io` root:** returns GitHub's own *"Site not found"* 404. No
  `eltonaguiar.github.io` user-site repo exists, so the root cannot be impersonated by a third party.
* **Mirror-repo workflows:** 42 workflows; 8 exist only in the mirror repo
  (`alpha-suite-daily-refresh`, `daily-mutualfund-refresh`, `deploy-pages`, `forward-test-daily`,
  `refresh-stocks-portfolio`, `scraper_cron`, `send-event-notifications`, `send-goal-followups`).
  Every `curl`/`wget` in them resolves to exactly **two hosts**: `findtorontoevents.ca` (48 refs) and
  `eltonaguiar.github.io` (1 ref). Secrets used are `EVENT_NOTIFY_API_KEY`, `DB_USER`, `DB_PASS`,
  `DB_NAME`, `DB_HOST` — all consumed by calls to **our own** endpoints. No `base64 -d`, no `/dev/tcp`,
  no `eval`, no pastebin/transfer.sh/webhook.site/ngrok.

---

## 5. Two real findings (not phishing, still worth closing)

### F-1 — Write-enabled deploy key on the archive repo, titled `test`

```
repo:    eltonaguiar/findtorontoevents_antigravity.ca-archive-2026-05-23
id:      147815285
title:   test
read_only: false          <-- can PUSH
created: 2026-04-07T03:44:42Z
key:     ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEqjlrnzwMIJMdO1MILFw5ey…  (verified)
```

A write-capable key with a placeholder name on an archive repo is exactly the persistence shape an
incident responder looks for. **Verify you recognise it; if not, delete it.** Severity: medium
(limited to one archive repo, but it is unrotated since April).

### F-2 — Basic-auth password hash of the `elton` user is committed to a public repo

`eltonaguiar/findtorontoevents.ca` → `.htaclu` (43 B, public):

```
elton:$1$8JJV3VLo$sBUJ1jfK2VVV5T69MYokv0
```

That is an `htpasswd` MD5-crypt (`$1$`) entry for the `elton` Basic-auth account — the **same
credential class** listed as outstanding in `updates/2026-11-25-50webs-resweep-status.md`. `$1$` is
fast to crack offline; this belongs in the same rotation batch as the FTP and control-panel passwords.
The `^M^M$` line endings confirm it was FTP'd up from Windows, matching the compromise's delivery
pattern. Severity: medium-high if that realm is still live anywhere.

### F-3 (advisory) — two unlabelled SSH keys on the account

`id=141633572` and `id=152340062`, both `ssh-ed25519`, both with `title=null`. Listing them needs the
`admin:public_key` scope, so this audit could read the key material but not the titles/last-used
metadata. Confirm both are yours (the `gx10-c9b9-windows-081g9oh` key is expected to be one) and give
them titles so a future audit can tell an intrusion from your own fleet.

---

## 6. Why GitHub was not the weak link

The kit's delivery signature — files with FTP timestamps written straight into multiple docroots, a
wholesale `.htaccess` replacement, and a Windows-style CRLF payload — is a **credentials/panel-level**
compromise of the shared hosting accounts. GitHub Pages has no FTP, no `.htaccess`, no PHP, and cannot
serve `de/index.php` anywhere; the kit is functionally impossible to host there, which matches the
measurement: 204 kit-path probes, all 404.

The one propagation path that *did* exist — `.github/workflows/mirror-site.yml` copying the live
(poisoned) tree back into the repo and out to the other hosts — is already fixed on this branch
(commit `1b5a22c`): the workflow now `--exclude`s `^de/`, `^de-de/`, `^appeasy/`, `^easyapp/`, runs a
**"Strip phishing-kit artifacts from the mirror tree"** step, and `exit 1`s if any artifact survives
quarantine.

---

## 7. Recommended next actions

| # | Action | Owner | Priority |
|---|---|---|---|
| 1 | Delete or re-create the `test` deploy key on the archive repo (F-1) | you | **P1** |
| 2 | Rotate the `elton` Basic-auth password and remove `.htaclu`/`.htacl` from **both** public mirror repos and every docroot backup (F-2) | you | **P1** |
| 3 | Title/verify both account SSH keys; revoke the unknown one (F-3) | you | P2 |
| 4 | Re-run this audit after rotation — the probe script is `tools/security/pages_phishing_scan.py` | me | P2 |
| 5 | Request `admin:public_key` + `admin:gpg_key` scope so key metadata (created/last-used) is auditable | you | P3 |
| 6 | Delete the dead `EBOND_ServiceNowSalesforce_RUN` Pages site (404s, pure noise) | you | P3 |

---

## 8. Verification performed

Every claim above is backed by a command run in this session:

* `gh api /user/repos --paginate` → 105 repos, 34 with `has_pages: true`
* `gh api /repos/{r}/pages` for all 34 → no `cname` on any
* 34 live fetches + 204 kit-path probes → all IoC-free, kit paths all 404
* `grep -rIl` for IoCs over the working tree → only my own docs/tooling
* `git log --all --diff-filter=A --name-only -- '*de/index.php' …` → empty
* `git rev-list --all --objects | grep -i htaccess` → 16 paths, none oversized
* `gh api /users/eltonaguiar/keys`, `/user`, `/user/orgs`, `/repos/{r}/hooks`, `/repos/{r}/keys`
* `gh api /repos/{r}/git/trees/{branch}?recursive=1` on the three site repos
* Host-allowlist grep over 8 mirror-only workflow files → `findtorontoevents.ca`, `eltonaguiar.github.io`
* `gh api /users/eltonaguiar/gists` → none

**Not verified / out of scope:** whether `.htaclu`'s realm is still live on any host; whether the
`test` deploy key has ever been used (needs `admin` audit-log access); URL blocklist status of the
`.github.io` sites in Google Safe Browsing (no API key used in this audit).

**Verdict:** GitHub Pages and the GitHub account are **not** part of the phishing compromise. The
kit is confined to the 50webs and GoDaddy shared-hosting docroots documented in
`updates/2026-11-25-phishing-kit-compromise.md`. Close F-1 and F-2 and this surface is clean.
