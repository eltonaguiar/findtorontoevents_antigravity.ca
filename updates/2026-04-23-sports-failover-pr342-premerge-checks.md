# PR #342 Pre-Merge Checks — Mergeability + Host-Guard Audit

**Date:** 2026-04-23
**PR:** `#342` → `origin/pr/sports-odds-api-failover`
**Head:** `70ff4891a97387c66ff18963ce38a0fb5cf72920`
**Base:** `8aa9c9b7906a7b88407ce91ce09048c1ef8f6265` (main)
**Status:** 357 commits on main since PR branched; 3 commits on PR branch.

### Post-merge addendum (2026-04-23)

The **secret-wiring workflow** and **#342** / **#349** merges to `main` have since **completed** (see [2026-04-23-sports-failover-deploy.md](2026-04-23-sports-failover-deploy.md)). The **TL;DR** mergeability and host-guard findings below remain valid as a historical record.

**Still open as follow-up (not blockers):** enable SSL peer verification in `sports_failover_proxy.php` (remove `verify_peer`/`verify_peer_name` false); re-evaluate CORS + `Cache-Control` if responses ever include user-specific data. The checklist in “Updated Checklist State” was written **before** that merge; treat remaining rows as **superseded** except the incidental Security/CORS items above.

---

## TL;DR

| Check | Result | Verdict |
|---|---|---|
| PR #342 mergeability (GitHub API) | **MERGEABLE** (after cache refresh) | ✅ Clear |
| `git merge-tree` conflict markers | **0** | ✅ Clean merge |
| `sports_failover_proxy.php` hardcoded hostnames | **None** — all URLs sourced via config | ✅ Clean |
| `sports_failover_config.php` hostnames | **6 legitimate public-API hosts**, no IPs, no localhost | ✅ Clean |
| Config uses env vars / `define()` for URLs | **No** — all URLs are baked in | 🟡 Minor — fine for public APIs, flag for future |
| SSL cert verification in proxy | **`verify_peer => false`** | 🟠 Security concern (separate issue) |
| CORS policy in proxy | **`Access-Control-Allow-Origin: *`** with 5-min public cache | 🟡 Over-permissive (separate issue) |

**Bottom line on the two asked questions:**
1. **Mergeability:** ✅ Clean. The earlier `UNKNOWN` was a GitHub cache artifact. After re-fetching the PR ref, GitHub recomputed to `MERGEABLE` within one poll. `git merge-tree` confirms zero conflicts despite 357 commits of divergence.
2. **Hardcoded hostnames in `sports_failover_proxy.php`:** ✅ None. The proxy is config-driven. All URLs live in `sports_failover_config.php` and all are legitimate public-API endpoints.

The other two 🔴 blockers from the earlier review (secret-wiring PR + deploy-window race) are **still blockers**. This check clears two of the 🟠-tier items.

---

## Check 1: Mergeability

### Initial state
```
gh pr view 342 --json mergeable,mergeStateStatus
→ mergeable: UNKNOWN, mergeStateStatus: UNKNOWN
```

### Forcing recomputation
```bash
git fetch origin 'refs/pull/342/head:pr-342-local' --force
# → * [new ref]   refs/pull/342/head  -> pr-342-local
```

### Poll results after refresh
| Attempt | `mergeable` | `mergeStateStatus` |
|---|---|---|
| 1 (immediately) | UNKNOWN | UNKNOWN |
| 2 (+5s) | **MERGEABLE** | *(clean)* |
| 3 (+10s) | **MERGEABLE** | *(clean)* |

GitHub just needed a poke. No actual merge conflict.

### Independent verification — `git merge-tree`
```bash
BASE=$(git merge-base origin/main origin/pr/sports-odds-api-failover)
git merge-tree $BASE origin/main origin/pr/sports-odds-api-failover \
  | grep -cE '^(<<<<<<<|=======|>>>>>>>)'
# → 0
```

**Zero conflict markers.** Despite main having moved 357 commits ahead since PR branched, none of those 357 commits touch the files #342 modifies (`live-monitor/api/*.php`, `live-monitor/*.js`, `live-monitor/*.html`, `live-monitor/nba_odds_scraper.py`, `updates/*.md`).

### Divergence stats
```
357 commits on origin/main since merge-base  (branch is very stale)
  3 commits on origin/pr/sports-odds-api-failover since merge-base
```

**Interpretation:** The PR hasn't had a rebase since it opened, but main's churn has all been elsewhere (almost certainly the hourly trading-system autocommits — 8 of them in the last 15 minutes per the git log). The PR is technically behind but semantically untouched. A rebase-before-merge is optional polish, not required.

### Recommendation
- **✅ Mergeability is not a blocker.** Merge when the secret-wiring PR lands first.
- Optional: `git rebase origin/main` on the PR branch before final merge for a cleaner history, but the squash-merge option avoids this entirely.

---

## Check 2: Host-Guard Audit of `sports_failover_proxy.php`

### Scope
File: `live-monitor/api/sports_failover_proxy.php` on branch `origin/pr/sports-odds-api-failover` (550 lines).

### Grep results

```bash
grep -nE 'https?://[a-zA-Z0-9._-]+' sports_failover_proxy.php
→ (zero matches)

grep -nE '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}' sports_failover_proxy.php
→ (zero matches)

grep -niE 'localhost|127\.0\.0\.1|\.local' sports_failover_proxy.php
→ (zero matches)
```

**Zero hardcoded URLs. Zero IP literals. Zero `localhost`/`.local` references.**

### How it actually sources URLs

```php
require_once __DIR__ . '/sports_failover_config.php';
// ...
foreach (get_supported_sports() as $sp) {
    foreach (get_data_types($sp) as $dt) {
        $chain = get_failover_chain($sp, $dt);
        // ← every URL comes from here
    }
}
```

All URLs are sourced from `get_failover_chain()` in `sports_failover_config.php`. The proxy itself is a pure router — it just loops, fetches, parses, and returns. This is the correct architecture.

### Verdict

✅ **Clean.** No SSRF vector in the proxy. If an attacker wanted to redirect outbound calls, they'd have to modify `sports_failover_config.php` — which is a file on disk, not a user-controllable parameter. The `$sport` and `$type` URL params select from a pre-computed chain; they cannot inject arbitrary URLs.

---

## Check 3: `sports_failover_config.php` Host Inventory

Since the proxy delegates to config, I audited the config too.

### Hostnames present

| Host | Providers | Keys required? | Risk level |
|---|---|---|---|
| `site.api.espn.com` | ESPN Standings, Scoreboards, Injuries (NBA/NHL/NFL/MLB) | No (public) | 🟢 |
| `cdn.nba.com` | NBA CDN Scoreboard | No (public) | 🟢 |
| `api.balldontlie.io` | BallDontLie Teams + Games | No (public tier) | 🟢 |
| `www.thesportsdb.com` | Team searches (all leagues) | Free tier = key `3` | 🟢 |
| `api-web.nhle.com` | NHL Web API Standings + Schedule | No (public) | 🟢 |
| `statsapi.mlb.com` | MLB Stats API Standings + Schedule | No (public) | 🟢 |

- **6 hosts, all legitimate public sports-data APIs.** No surprise third-party domains, no URL shorteners, no unknown CDNs.
- **No IP literals.** No `127.0.0.1`, no `0.0.0.0`, no RFC1918 ranges.
- **No `localhost` / `.local` refs.**
- **No env var or `define()` indirection** — URLs are baked into PHP literals.

### Is the baked-in hostnames a problem?

**Probably not, but worth flagging:**
- For **public APIs** (ESPN, NHL, MLB, NBA CDN), baked-in is fine and even preferable — you don't want secret indirection for known-stable public URLs.
- For **any future key-required provider** (e.g., if the odds-failover layer gets extended to reach paid adapters), the pattern should switch to pulling hosts from `db_config.php` or env vars, matching the pattern used for `THE_ODDS_API_KEY` / `ODDS_API_IO_KEY`.
- Today's keys in the existing `sports_odds.php` do use `db_config.php` via `require_once`, so the project already has the right pattern — it's just not extended to the failover config.

**Recommendation:** Leave as-is for #342. File a follow-up issue for "Migrate `sports_failover_config.php` URLs to env/config-file for cache-busting and dev/staging overrides" when there's a real need (staging, A/B, or rate-limited providers).

---

## Incidental Findings (Not Blockers, But Worth Flagging)

These came up during the audit and are not in the plan's scope, but the review would be incomplete without mentioning them:

### 🟠 1. SSL cert verification is disabled on outbound calls

```php
$ctx = stream_context_create([
    'http' => [ /* ... */ ],
    'ssl'  => ['verify_peer' => false, 'verify_peer_name' => false],  // ← here
]);
```

**Both** in the health-check branch and the main fetch branch. This is a **MITM vulnerability** — any attacker between the 50webs / torontoevent.net host and the upstream provider can substitute arbitrary JSON into the failover response. Given these hosts accept the data as authoritative for the betting dashboard, this is a real risk.

**Fix:** Remove the `ssl` section (default behavior verifies certs) or change to `'verify_peer' => true, 'verify_peer_name' => true`. If the hosting environment genuinely has CA-bundle issues, fix the CA bundle — don't disable verification.

**Recommendation:** Open a small follow-up PR *after* #342 lands. Do not block #342 on this, but don't let it linger — this is the kind of thing that becomes "technical debt we forgot about".

### 🟡 2. CORS is fully open with a 5-minute public cache

```php
header('Access-Control-Allow-Origin: *');
header('Cache-Control: public, max-age=300');
```

- `Access-Control-Allow-Origin: *` lets any website on the internet read the response. That's intentional if the dashboard is meant to be embeddable, but it also means any rate-limit budget can be burned by a malicious site.
- `public, max-age=300` means CDNs and shared proxies will cache the response. If any user-specific data is ever added to the response shape, this becomes a data-leak vector. Currently the response is pure public sports data, so it's fine — but pin this as a thing to re-evaluate if the response ever grows personalization.

**Recommendation:** Not a blocker. Add a comment in the file noting the deliberate CORS + cache choice so a future change doesn't accidentally leak something.

### 🟢 3. Good — URL masking before returning response

```php
'url' => preg_replace('/[a-f0-9-]{20,}/', '***', $source['url']),
```

This proactively redacts any embedded hex-string API keys from the URLs before echoing them back in the `failover_chain` response. Nice defensive coding.

---

## Updated Checklist State

From the original revised-execution-order list:

| Step | Status |
|---|---|
| 1. Secret audit across branches | ⏳ Pending (user hasn't requested yet) |
| 2. Commit workflow edit | ⏳ Pending (user hasn't requested yet) |
| 3. Peer check | ⏳ Pending |
| **4. Refresh mergeability** | **✅ Done — MERGEABLE, 0 conflicts** |
| 5. Diff audits | ✅ Done (previous report) |
| **6. Host-guard grep on proxy** | **✅ Done — clean** |
| 7. Rollback plan | ⏳ Pending |
| 8. Pre-merge deploy-queue check | ⏳ Pending (do right before merge) |
| 9. Merge + verify db_config.php | ⏳ Pending |
| 10. Force-fail failover test | ⏳ Pending |
| 11. Cherry-pick #345 bundle | ⏳ Pending |
| 12. Close #345 | ⏳ Pending |
| 13. Post-deploy PHP 5.2 validator | ⏳ Pending |
| 14. Final writeup | ⏳ Pending |

**Remaining 🔴 blockers:** (1) secret-wiring workflow edit, (2) deploy-window `isset($ODDS_API_IO_KEY)` race. These are still the only two things holding up the merge.

---

## Next Actions (Recommended)

1. **Draft the companion PR for the workflow secret-wiring edit** — this is blocker #1 and the user queued it as a followup.
2. **Quick secret-exposure scan** across the three PR branches — ~5 min of grep, closes blocker-adjacent risk.
3. **Write the rollback snippet** (15 min) and paste it into #342's description before merge.

After those three, #342 is ready to merge.
