# FavCreators /fc/#/guest — why follows vanished on refresh (root cause + fix log)

Date: 2026-10-17

## Reported symptoms

The signed-in user `zerounderscore@gmail.com` reported, on
`findtorontoevents.ca/fc/#/guest`:

1. Quick Add of `tiktok.comm/@nikkibby11` did not stick — after refresh the
   creator was not in the followed list.
2. Earlier the same day, `https://tiktok.com/@gurleen_dosanjh` and
   `https://tiktok.com/@nikkibby11` behaved the same way.
3. A full URL (`https://www.tiktok.com/@ellamarisue`) followed fine, but the
   TikTok live notification appeared late/inaccurate on first load.

## Root cause — three stacked defects (only the first one is a "DB bug", and it isn't data loss)

### 1. Backend: PHP 5.2 parse error silently 500'd every save (THE root cause)

`favcreators/docs/api/ensure_tables.php` used the `[]` short-array literal,
which is a **parse error on the host's PHP 5.2**. `save_creators.php` and
`login.php` both include it, so every write request died with HTTP 500 while
plain reads continued to work. Quick Add therefore appeared to succeed
(locally rendered card) but nothing ever reached the `user_lists` table — and
the refresh reloaded the authoritative list from the DB, making the creator
disappear.

A second bug in `login.php`: `$data` (the decoded request body containing
`email`) was overwritten by `ensure_tables.php` at include scope, so login ran
`WHERE email = ''` → "User not found" for **every** login on the PHP 5.2 host.
The SPA's `register.php` route also didn't exist at all.

**Fix (commit `c56f1af9ee`, 2026-10-17 21:59):** `ensure_tables.php` made
PHP 5.2-safe, `login.php` no longer lets the include clobber `$data`, new
`register.php` (PHP 5.2-safe, session-backed), seeded users given
`created_at`, and a real-browser test `favcreators/tests/follow_persist_ui_test.js`
covering 2 users × both add methods (Quick Add and the Add Creator form),
asserting a fresh DB read after reload. Verified against production:
`login → save_creators {"status":"success"}` → fresh `get_my_creators`
contains the TikTok account.

### 2. Frontend: Quick Add parsed URLs with the legacy `name:platform` splitter

The old handler ran `input.split(":")` on everything. For
`https://tiktok.com/@nikkibby11` that yields name `https` / platform
`//tiktok.com/@nikkibby11`, which matches none of the supported platform
names (`kick`, `twitch`, `youtube`, `tiktok`, `instagram`), so the account
array was empty and no `nikkibby11` account was ever built for
`save_creators.php` to persist.

**Fix A (earlier session, in the bundle):** a `urlMatch` regex recognizes a
full TikTok profile URL before the colon parser — but it **requires a
scheme** (`https?://`).

**Fix B (this session):** the reported input `tiktok.comm/@nikkibby11` has no
scheme and a typo'd domain, so it matched neither `sb()` (hostname not in the
platform map) nor `urlMatch` (no scheme) and still fell through to the legacy
colon parser, creating a garbage creator keyed on the literal string
`tiktok.comm/@nikkibby11`. The handler now pre-parses with:

```javascript
ttm=/^(?:https?:\/\/)?(?:www\.)?tiktok\.com+\/?@([^/?#]+)/i.exec(qaIn)
```

and falls back to a synthetic `{platform:"tiktok", username, url}` result
before the colon parser runs. Result for the reported input:

```text
tiktok.comm/@nikkibby11 -> username: nikkibby11 / platform: tiktok /
                           url: https://www.tiktok.com/@nikkibby11 /
                           checkLive: yes (default live platforms include tiktok)
```

`scheme-less` `tiktok.com/@handle`, `www.tiktok.comm/@handle`,
`http(s)://...`, and trailing-whitespace variants all normalize the same way;
`kick.com/...`, `twitch.tv/...` and junk strings are untouched.

### 3. Why it "worked after refreshing the cache"

Two staging effects, not data corruption:

- **Stale bundle:** at one point production's `assets/main-DF_ZQ_dn.js` lacked
  the `urlMatch` parser that was already fixed in the repo — once the browser
  cache expired, the correct bundle loaded and following worked.
- **Live-status scan order:** live checks start ~2 s after creators load and
  then re-run every 180 s, iterating sequentially with 500 ms spacing, in
  priority order (already-live → recently active → bell-enabled → others).
  New TikTok follows therefore show an accurate live state only after the
  first full pass completes; the first-seen notification can look late or
  mis-ordered. This is scan latency by design, not a wrong-state bug.

## GitHub modifications today related to `/fc/#/guest`

- `c56f1af9ee` — `fix: restore FavCreators login + follow persistence on PHP 5.2 hosting`
  - `favcreators/docs/api/ensure_tables.php` (PHP 5.2 parse-error fix)
  - `favcreators/docs/api/login.php` ($data clobber fix)
  - `favcreators/docs/api/register.php` (new)
  - `favcreators/tests/follow_persist_ui_test.js` (new real-browser test)
  - `updates/2026-10-17-favcreators-follow-persistence-fix.md`
- Working tree (deployed this session):
  - `favcreators/docs/assets/main-DF_ZQ_dn.js` — `urlMatch` full-URL parser +
    new `ttm` scheme-less/typo-domain pre-parse in the Quick Add handler
  - `favcreators/tests/quick_add_url_test.js` — extended to assert both
    parsers and to execute the shipped regex against the reported inputs
  - `updates/2026-10-17-favcreators-tiktok-url-persistence-fix.md`
  - this file + the summary entry on `updates/index.html`

## Follow-up (same day): Quick Add success toast now mentions the bell icon

After a successful Quick Add, both success paths (URL branch and the
name/legacy branch) now append:

> Tap the 🔔 bell on their card to track live notifications.

to the green `role="status"` toast that appears under the Quick Add control
(the same toast that already shows `Added <name> with platforms: ...` and
clears after 8 s). This nudges users to enable the per-creator bell icon so
live/Discord notifications actually fire for the creator they just added.

Guard 3 in `favcreators/tests/quick_add_url_test.js` asserts the hint text is
present in the deployed bundle for both branches; tests and `node --check`
pass, and the re-deployed bundle was verified byte-identical over FTP.

## Follow-up (same day): guest follows wiped on refresh + no online status for Kick creators

Reported: a **signed-out** guest Quick Added `kick.com/kaneljoseph` and
`kick:kaneljoseph`; after refresh neither follow survived, and Kaneljoseph's
Kick online status never showed. Three compounding defects:

1. **Guest load replaced instead of merged.** The guest path fetches
   `get_my_creators.php?user_id=0` (a *shared* server list) and did a hard
   `Je(td(He))` replace whenever that list was non-empty — wiping anything
   the guest had just added locally (guests never server-save: `Ra` no-ops
   `if(!r)`, and every save effect is `r`-gated). Now the guest load merges:
   server creators first, then local-only creators (by id) appended.
2. **Pasting a streamer URL didn't enable live tracking.** Quick Add computed
   `isLiveStreamer`/`checkLive` from `defaultLivePlatforms`, whose default is
   `["tiktok"]` **only** (guests never load server prefs — that load is
   `r`-gated). A guest-added Kick creator got `isLiveStreamer:false`, and the
   live checker excludes any creator with an explicit `false` → online status
   could never appear even if the follow had survived. Quick-added
   kick/twitch/youtube accounts are now unioned with the live-capable set in
   all three places (URL-branch `Ke`, legacy `checkLive`, legacy
   `isLiveStreamer`), since pasting a streamer-platform URL is explicit
   live-tracking intent.
3. **`kick:kaneljoseph` (platform-first) parsed as the wrong shape.** The
   legacy parser only understands `name:platform`, so this produced creator
   name "kick" with zero matching accounts (platform token `kaneljoseph`
   matched no platform ⇒ empty `accounts[]`). The parser now swaps
   platform-first pairs (`[t[1],t[0]]`) when token 0 is a platform name and
   token 1 is not.

**Verification:** `node --check` bundle ✓; `quick_add_url_test.js` extended
with Guard 5a/5b/5c (all pass); `follow_persist_ui_test.js` ALL PASS (signed-in
paths unaffected); bundle redeployed and byte-verified over FTP + live HTTP.

Guest server-side persistence deliberately NOT added: `save_creators.php`
anonymous writes were previously observed to 401, and blindly pushing a
guest's full local list to the shared `user_id=0` row would let any stale
localStorage overwrite the shared list. Same-browser refresh persistence is
restored by the merge; cross-device persistence remains what the toast
("sign in to persist") tells guests to do.

## Follow-up (same day, part 2): the actual guest boot wipe — `if(qn)return ii`

A new real-browser E2E (`favcreators/tests/guest_follow_ui_test.js`) proved
the merge alone was **not** enough: quick-add worked, the warning toast
fired, but a reload still dropped the follow (2/8 failing).

Root cause: the creators-state initializer was

```javascript
useState(()=>{ if (qn) return ii;   // qn = URL contains #/guest
  // ... otherwise: version check + hydrate from localStorage ...
```

On the guest route it **deliberately skipped localStorage** and booted from
the default pack `ii` (13 creators). The always-on save effect then
immediately rewrote `fav_creators` from that state — erasing the 14th entry
the guest had just added — and the server merge afterwards could never see
it (`prev` no longer contained it).

Fix: removed the `(qn) return ii` short-circuit so the guest route hydrates
from localStorage exactly like every other route (version check +
`td(fl(JSON.parse(w)))` retained), then the guest fetch merges the server
`user_id=0` rows on top of it — so local adds and server rows both survive.

Some observations from the E2E diagnostics:
- `sync_creators_table.php` returns **401 for guests** (harmless — wrapped
  in try/catch, the flow continues to `get_my_creators` 200).
- After reload, localStorage stays at n=14/15 across 4s and 13s checkpoints,
  and the card is present at first render.

**Verification:** Guard 6 added to `quick_add_url_test.js` (asserts
`if(qn)return ii` count === 0 and hydration pattern present) — all guards
pass; `guest_follow_ui_test.js` **8/8 ALL PASS, exit 0**;
`follow_persist_ui_test.js` ALL PASS (signed-in unaffected); bundle
deployed and SHA-256 matched over live FTP + live HTTP range probe confirms
the hydrated initializer and absence of the `qn` bypass.

## Verification

- `node --check favcreators/docs/assets/main-DF_ZQ_dn.js` — passed.
- `node favcreators/tests/quick_add_url_test.js` — all assertions passed,
  including `tiktok.comm/@nikkibby11 → nikkibby11` and negative cases
  (twitch/kick/junk inputs are not hijacked by the TikTok regex).
- `node favcreators/tests/follow_persist_ui_test.js` — ALL PASS (2 users ×
  2 add methods, fresh DB read after reload, exit 0), run after the bundle
  edit.
- Live deploy via `tools/deploy_to_ftp.py --favcreators-only` /
  `--updates-only`; remote touches confirmed by grepping the live bundle for
  the `ttm=` pre-parse marker.

No production user record was cloned or mutated during this investigation;
authentication was never bypassed — saves still require the normal session
and only write to the signed-in user's own list.