# Investment Hub — goldmines existence report and root cause

**Date:** 2026-11-23 · Follow-up to `reports/INVESTMENT_HUB_AUDIT_ASSESSMENT_2026-11-23.md` (commit `69cd7943ea7`)

**Headline:** the four "dead" paths are **not dead — they are live and published**. My earlier report said
"dead in-repo", which was literally true but misleading in the way that matters: they are shipped, served,
and linked from the live site. The real finding is worse than a broken link: **the goldmines proof-tracking
system is live in HTML and dead in function.**

---

## 1. Correction to the previous report

| Previous claim | Status |
|---|---|
| "**Four links are dead in-repo**" | **Correct but misleading.** True of the repo; false of production. Should have been "missing from the repo **and** live on the host". |
| "They may exist on the FTP host" | **Confirmed.** All four exist. |
| Fix list item "Remove, or ship the files" | **Wrong action.** Nothing to remove. The files exist; they need *fixing*. |

I have marked this correction inline in the earlier report rather than rewriting history.

## 2. Existence matrix — live host vs repository

Probed `https://findtorontoevents.ca/...` (status, size, title).

| Path | Live | Repo | Note |
|---|---|---|---|
| `/audit/` | **200**, 1,443,688 B — "Unified Audit Dashboard" | `audit_dashboard/` (684 files) | OK |
| `/audit2/` | **200**, 7,229 B — "audit2 — candidate & methodology library" | `audit_dashboard/audit2.html` + `audit2.js` | OK |
| `/audit3/` | **200**, 47,756 B — "Audit3 — Quant Kill Tribunal" | `audit_dashboard/audit3.html` | OK |
| `/investments/` | **200**, 35,216 B | `investments/index.html` | OK |
| `/investments/all-dashboards.html` | **200**, 76,023 B | `investments/all-dashboards.html` | OK |
| `/investments/master_dashboard.html` | **200**, 11,957 B — "Master Dashboard" | **absent** | live-only |
| `/investments/goldmines/` | **200**, 5,483 B — "Goldmines \| Investment Hub" | **absent** | live-only |
| `/investments/goldmines/antigravity/` | **200**, 13,457 B | **absent** | live-only |
| `/investments/goldmines/kimi/kimi-goldmine-client.html` | **200**, 16,767 B | **absent** | live-only |
| `/investments/goldmines/windsurf/` | **200**, 63,398 B — "Windsurf AI Prediction Proof Tracker" | **absent** | live-only |

**So: 0 dead links, 5 paths live but unversioned.** `audit2`/`audit3` were never at risk — they are in
`audit_dashboard/` and healthy.

### Pages that exist but the hub menu never links

| Path | Live |
|---|---|
| `/investments/goldmines/antigravity/leaderboard.html` | **200**, 19,856 B |
| `/investments/goldmines/antigravity/risk_analytics.html` | **200**, 17,583 B |
| `/investments/goldmines/kimi/kimi-goldmine.html` | **200**, 46,357 B |

A leaderboard, a risk-analytics page and a full Kimi dashboard are published but **orphaned** — reachable
only by guessing the URL. The hub menu links 2 of 5 antigravity/kimi pages that exist.

## 3. The real defect: live in HTML, dead in data

### 3a. Antigravity API — database is down

```
GET /investments/goldmines/antigravity/api/unified_predictions.php
 -> 200, application/json, 49 bytes
    {"ok":false,"error":"Database connection failed"}
```

Fails identically for `?action=list` and `?action=leaderboard`, so it is not one bad query — the
connection itself is dead. `leaderboard.html` calls exactly these:

```js
fetch(API_BASE + '?action=leaderboard&min_trades=1')
fetch(API_BASE + '?action=hidden_winners')
fetch(API_BASE + '?action=system_summary')
```

...so the leaderboard renders its error state. The page contains 6 "Error" occurrences and no data.

### 3b. Kimi API — cannot even parse on this host

```
GET /investments/goldmines/kimi/kimi_goldmine_api.php
 -> Parse error: syntax error, unexpected T_FUNCTION, expecting ')' on line 21
GET /investments/goldmines/kimi/test.php
 -> {"php_version":"5.2.17","ok":true,"message":"Basic PHP test works"}
```

**Root cause: the host runs PHP 5.2.17.** `T_FUNCTION` in an argument position is a *closure*, which
requires PHP **5.3+**. On 5.2 the file cannot be compiled at all, so every `action=` on it 500s at the
parser before reaching any logic.

### 3c. Windsurf proof tracker — depends on the same dead backends

`/investments/goldmines/windsurf/` (63 KB) calls `.php?action=history`, `?action=list`,
`?action=performance`, `?action=prediction_history&days=30`, `?action=recent` — all of which land on the
broken PHP. The page renders **"NO DATA"** (3 occurrences) / "no data".

**Net effect: the entire "Goldmines — AI Proof-Tracking" section is cosmetic.** It is the one part of the
hub whose *stated purpose* (tracking whether AI predictions were actually right) is exactly what `/audit`
exists to do — and it cannot load a single row.

### The repo already owns a guard for this

`tools/validate_php52.py` **exists** (an earlier note claiming it was uncommitted is now outdated), and
`db_sync.py` references PHP 5.2. So the estate knows the host is PHP 5.2 — yet a published API file ships
a 5.3+ closure. **The validator is not gating the files under `investments/`.**

## 4. Source located on the Windows host

All three hinted paths exist on `DESKTOP-081G9OH` (`ssh win081g9oh`):

| Path | Status |
|---|---|
| `C:\Users\zerou\source\findtorontoevents.ca\fix_goldmines.js` | **EXISTS** (file) |
| `C:\Users\zerou\Downloads\findtorontoevents.ca (3)\findtorontoevents.ca\investments\goldmines` | **EXISTS** (dir) |
| `C:\Users\zerou\.kimi\sessions\15f1af50…\baseline\investments\goldmines` | **EXISTS** (dir) |

Tree (from the Downloads copy, 21 files):

```
index.html                                    5,483
antigravity\  index.html 13,457 | leaderboard.html 19,856 | risk_analytics.html 17,583
              api\unified_predictions.php 11,465 | check_dead_data.php 6,584
              unified_predictions_schema.sql 7,147 | phase4_advanced_analytics.sql 11,766
              DATA_INTEGRITY_AUDIT.md 11,646 | GOLDMINE_ANTIGRAVITY.md 14,365 | README.md 3,138
kimi\         kimi-goldmine-client.html 16,767 | kimi-goldmine.html 46,357
              kimi_goldmine_api.php 27,155 | kimi_goldmine_collector.php 25,593
              kimi_goldmine_schema.php 19,614 | setup_goldmine.php 8,411 | test.php 220
              ARCHITECTURE.md 9,102 | CRON_SETUP.md 5,601
windsurf\     index.html 62,527
```

Three copies exist (Downloads, `.kimi` session baseline, plus the live host). **That the live host serves
something is not a resolution of this finding — it IS the finding.** A HEAD request against the FTP host
does not put the file back in a clone, and asserting "the live site is authoritative" would paper over a
repo/production divergence rather than fix it. Recorded here as a **known divergence**: five published
paths have no tracked source, so no reviewer can diff, review, or revert them. Choosing which copy is
current requires a diff against the server, which I have not done.

## 5. What to do, ranked

| # | Action | Why |
|---|---|---|
| **1** | **Fix `kimi_goldmine_api.php:21`** — replace the closure with a PHP 5.2-compatible form (named function or `create_function`) | One line. Unblocks a 27 KB API. Cheapest real win available. |
| **2** | **Restore the antigravity DB connection** — `unified_predictions.php` returns "Database connection failed" | Cron collector (`kimi_goldmine_collector.php`) is presumably also failing; check whether the prediction table still exists |
| **3** | **Version-control the 5 unversioned paths** + the `fix_goldmines.js` | They are published, so they are production. Untracked production is how this drifted in the first place. Diff Windows copies against the server first — do not assume local is newer. |
| **4** | **Gate `investments/**/*.php` with `tools/validate_php52.py`** | The guard already exists and would have caught #1 at commit time |
| **5** | **Decide goldmines' fate** — repair or retire | If repaired, it is the closest thing in the estate to a *forward-test proof tracker*, which is `/audit`'s core need. If not repaired, delist it: a proof-tracker showing "NO DATA" is worse than no proof-tracker. |
| 6 | Link the 3 orphaned pages, or delete them | Leaderboard + risk analytics are published and undiscoverable |

## 6. Provenance

| Claim | Evidence |
|---|---|
| 10 live paths + sizes + titles | `curl -sSL -w '%{http_code} %{size_download} %{content_type}'` against `findtorontoevents.ca`, 2026-11-23 |
| live-only status | `git ls-files` over repo: 0 tracked paths under `investments/goldmines/` |
| DB failure | response body `{"ok":false,"error":"Database connection failed"}` on 3 actions |
| Parse error | `Parse error: syntax error, unexpected T_FUNCTION, expecting ')' ... line 21` |
| PHP version | `test.php` → `{"php_version":"5.2.17","ok":true,...}` |
| Leaderboard depends on API | `fetch(API_BASE + '?action=leaderboard&min_trades=1')` in `leaderboard.html` |
| Windows paths | `ssh win081g9oh` + `Test-Path -LiteralPath` → all 3 EXISTS; tree via `Get-ChildItem -Recurse` |
| `validate_php52.py` exists | `ls tools/validate_php52.py` → present |

**Not verified:** whether the Windows copies match what is deployed, and whether the goldmines DB still
holds rows (the connection fails before any query). Both need host credentials I did not use.

Zero capital sanctioned. Paper only. Not investment advice.
