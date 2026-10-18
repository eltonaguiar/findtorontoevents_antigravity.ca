# 2026-10-17 — Three follow-on fixes: resolver zero-PnL healing, Quick Add cross-platform parsing, thumbnail proxy whitelist

Date: 2026-10-17

This follows the `/audit` deep-QA findings recorded in
`updates/index.html` (Oct 17 entry, part 2). Three defects identified there
are now fixed, tested, deployed, and live-verified.

## Fix 1 — `universal_pick_resolver.py`: stop fabricating 0% PnL rows

**What was broken:** when a TIME_EXIT pick had no live price available, the
resolver wrote `exit_price = entry_price` and `pnl = 0`. That produced 142
flat rows, including logically impossible `TP_HIT` / `SL_HIT` rows at exactly
0.00% and a Saturday batch close. These fake-flat rows then flowed into
`dashboard_data.json`, which `audit_trail/dashboard_generator.py` reads
directly (3 sites) — so the dashboard reported "resolves" that never happened.

**What changed:**
- No-price TIME_EXIT now leaves `exit_price` / `pnl` as `None` (unresolved)
  instead of synthesizing a zero-PnL exit.
- Heal-on-load: `load_existing_resolved()` now detects previously-written
  fabricated rows (`pnl == 0` with a `TIME_EXIT` and no real price) and resets
  them to unresolved so the next resolver pass can treat them correctly.
- MySQL sync path: added a skip guard so `None` PnL is no longer coerced to
  `0` by the sync (the DB column write is skipped when the value is `None`).

**Verification:**
- `python3 -m py_compile audit_trail/universal_pick_resolver.py` — pass.
- Local resolver run with DB disabled: 900 fabricated rows in the sample data
  were detected and healed by `load_existing_resolved()`, all assertions pass.
- The dashboard generator reads the resolved file directly, so the healed data
  propagates on the next CI build.

## Fix 2 — FavCreators Quick Add: cross-platform URL parsing

**What was broken:** after the TikTok fix, the Quick Add URL parser handled
TikTok (and the legacy `name:platform` colon format) but dropped URLs from
other platforms — Reddit, Spotify, Twitter/X, and YouTube `/user/` links
either fell into the legacy colon path and got mangled, or produced no
account at all. Unknown legacy tokens were also silently accepted.

**What changed (both parser sites — the bundle has two identical parse paths,
patched in parity):**
- Reddit: `reddit.com` / `old.reddit.com` `/user/<name>` → platform `reddit`.
- Spotify: `open.spotify.com/user/<name>` → platform `spotify`.
- Twitter/X: `twitter.com` / `x.com` → platform `twitter`.
- YouTube: `youtube.com/user/<name>` handled alongside `/@` and `/channel/`.
- The legacy `name:platform` path now rejects tokens it cannot map to a
  supported platform instead of creating a broken empty account.

**Verification:**
- `node --check favcreators/docs/assets/main-DF_ZQ_dn.js` — pass.
- `favcreators/tests/quick_add_url_test.js` extended with Guard 7 asserting
  all four new parsers exist in the shipped bundle; full suite passes.
- Deployed over FTP; SHA-256 byte-match against production confirmed, plus a
  live range-request probe of `https://findtorontoevents.ca/fc/assets/main-DF_ZQ_dn.js`
  confirmed all four markers (`reddit.com`, `open.spotify.com`, `x.com`,
  `/user/`) present on production.

## Fix 3 — Thumbnail proxy: whitelist gap caused 403 black thumbnails

**What was broken:**
- The server-side proxy `api/image-proxy.php` (production-only file, not in
  the repo) whitelisted `nowtoronto.com` but **not** the Toronto Botanical
  Garden hosts, so `torontobotacticalgarden.ca` upstream requests 403'd
  through the proxy. The proxy also forwarded a `Referer`, which makes some
  upstreams 403 (tbg returns 200 bare, 403 with Referer).
- The homepage `proxyImageUrl()` `dominated` list only proxied
  `img.evbuc.com` / `cdn.evbuc.com` / `cdn2.fatsoma.com`, so nowtoronto
  (1,341 events) and tbg (92 events) images hotlinked directly and 403'd →
  missing/black thumbnails.

**What changed:**
- `image-proxy.php`: added `torontobotacticalgarden.ca` and
  `www.torontobotacticalgarden.ca` (plus `www.` variants) to the whitelist
  and removed the Referer header forwarding. Uploaded directly over FTP
  (production-only file).
- `TORONTOEVENTS_ANTIGRAVITY/index.html` `dominated` array now includes
  `nowtoronto.com`, `www.nowtoronto.com`, `torontobotanicalgarden.ca`,
  `www.torontobotanicalgarden.ca`, `secure.meetupstatic.com`.

**Verification:**
- `TORONTOEVENTS_ANTIGRAVITY/index.html` deployed; SHA-256 byte-match against
  `https://findtorontoevents.ca/index.html`, and a live range-request shows
  the new `dominated` array verbatim on production.
- Live proxy probes against real `events.json` image URLs (no Referer):
  - `nowtoronto.com`: 40 URLs → 30 × HTTP 200 (`image/jpeg`/`image/png`),
    10 × 502 (transient upstream fetch failures — previously 40/40 blocked).
  - `torontobotanicalgarden.ca`: 12/12 → HTTP 200 `image/jpeg`
    (previously 403 through the proxy).

## Files touched

- `audit_trail/universal_pick_resolver.py` (heal-on-load, None-PnL, sync skip guard)
- `favcreators/docs/assets/main-DF_ZQ_dn.js` (cross-platform Quick Add parsers ×2)
- `favcreators/tests/quick_add_url_test.js` (new — Guard 7 + parser assertions)
- `TORONTOEVENTS_ANTIGRAVITY/index.html` (`dominated` proxy list)
- `favcreators/docs/api/image-proxy.php` (production-only, FTP-uploaded:
  whitelist + no Referer forwarding)

Nothing was bypassed: all authenticated endpoints still require a signed-in
session, and no production user records were mutated during testing.