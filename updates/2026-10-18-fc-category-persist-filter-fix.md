# FavCreators — category "Apply" never persisted + case-sensitive filter (2026-10-18)

## Symptom (reported)

User **zerounderscore@gmail.com** created a category **TorontoStreamer**, added two
creators they already follow (Kick **Moxie**, TikTok **@a.r.a.moore**) to it, then
filtering by the category showed **nothing**.

## Root cause (verified against production data + bundle)

Confirmed in the live DB (`ejaguiar1_favcreators.user_lists`, user_id=2): zero
creators carried `TorontoStreamer`; both targets still had `Other`/`other`.

Three defects in the built SPA bundle (`favcreators/docs/assets/main-DF_ZQ_dn.js`):

1. **Bulk "Apply category" never persisted.** The handler (`Ss`) updated React
   state (`Je(...)`) but never called the save function `Ra()` — the only path
   that POSTs `save_creators.php`. The assignment looked applied on screen and
   evaporated on reload, where the server list won.
2. **Category rename had the same bug** (`yl`): updated state, no `Ra()`.
3. **Filter used exact-case `creator.category === filter`.** Stored categories
   are case-chaotic (`Other` vs `other`, `entertainment` vs `Entertainment` —
   the guest-seed fallback writes lowercase `other`), so even a persisted
   category could filter to zero creators. All 5 comparison sites patched to
   trimmed, case-insensitive comparison. (Rename now also matches
   case-insensitively, which heals the case split as users rename.)
4. Bonus (same lost-on-reload class): **Add-Creator modal save (`hi`)** also
   skipped `Ra()`; newly added creators vanished on refresh. Fixed.

The bundle is minified with no source tree in this repo (the Vite source lives
elsewhere); patches were applied surgically to the committed bundle with
exact-count assertions + `node --check`.

## Also fixed: production login was BROKEN (reverted deploy)

While verifying, `login.php` on production returned **HTTP 500 for every POST** —
all /fc/ email logins were down. `GET /fc/api/ensure_tables.php` showed the
**line-135 parse error again** (`json_encode([...])` on PHP 5.2.17): the server
copy of `ensure_tables.php` + `login.php` had been reverted to the pre-fix
May-31 versions (yesterday's fix c56f1af9ee had deployed them; `register.php`
survived because it's new). Re-deployed `ensure_tables.php`, `login.php` and the
patched bundle via FTP. **Follow-up for operator:** find whatever re-uploaded the
old `api/` files (manual FTP from a stale local copy is the likely cause) so this
doesn't revert a third time.

## Verification (production, real browser)

New E2E test `favcreators/tests/category_persist_filter_test.js`
(throwaway registered user; mirrors the exact reported scenario — Kick moxie +
TikTok a.r.a.moore):

```
SITE=https://findtorontoevents.ca node favcreators/tests/category_persist_filter_test.js
→ ALL PASS (16 assertions)
```

Covers: register → login → quick-add both creators (persisted) → create
"TorontoStreamer" → select both in Tabular view → bulk **Apply category** →
save_creators.php POST carries the category → **fresh DB read shows
category=TorontoStreamer on both** → reload → category survives → **filter by
TorontoStreamer shows both creators** → no page errors.

Also verified post-deploy: `ensure_tables.php` no longer parse-errors,
register+login roundtrip HTTP 200, live bundle contains the patch markers.

## Files changed

- `favcreators/docs/assets/main-DF_ZQ_dn.js` — 4 surgical patches (Ss, yl, hi, 5 filter sites)
- `favcreators/tests/category_persist_filter_test.js` — new E2E regression test
- `favcreators/docs/api/ensure_tables.php`, `favcreators/docs/api/login.php` — re-deployed to prod (restoring c56f1af9ee; no repo change, prod had reverted)

## Data note

The reported user's two creators still carry `other` on the server; the fix
makes re-applying stick (their "TorontoStreamer" category option still lives in
their browser). They just re-select the two creators → Apply category once.
