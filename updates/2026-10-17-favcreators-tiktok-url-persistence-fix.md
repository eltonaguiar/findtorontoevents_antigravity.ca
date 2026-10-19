# FavCreators TikTok Quick Add persistence investigation

Date: 2026-10-17

## Reported symptom

The signed-in user `zerounderscore@gmail.com` entered these values in the
FavCreators Quick Add field:

- `tiktok.com/@gurleen_dosanjh`
- `tiktok.com/@nikkibby11`

After refreshing `/fc/`, the expected TikTok creators were not present in the
followed-creators list.

## Root cause

The old Quick Add handler treated every input as the legacy
`creator-name:platform` format and unconditionally ran:

```javascript
input.split(":")
```

For `https://tiktok.com/@nikkibby11`, that produced:

```text
creator name: https
platform:     //tiktok.com/@nikkibby11
```

The platform-building loop only creates accounts for the supported platform
names `kick`, `twitch`, `youtube`, `tiktok`, and `instagram`. The malformed
`//tiktok.com/@nikkibby11` token matched none of them, so the account array was
empty. Quick Add therefore did not construct a TikTok account with username
`nikkibby11` for `save_creators.php` to persist.

The same deterministic parsing failure affected
`https://tiktok.com/@gurleen_dosanjh`.

## Why this looked like a database persistence failure

Quick Add continued far enough to create local creator state, but that state
did not contain the requested TikTok account. On refresh, the application
reloaded the signed-in user's authoritative list from `user_lists`, making the
missing account visible to the user.

The API paths themselves are session-protected:

- An anonymous read of user ID 2 through `get_my_creators.php` returned HTTP
  403.
- An anonymous write through `save_creators.php` returned HTTP 401.

This investigation found no evidence that the database rejected a correctly
formed `nikkibby11` TikTok account. The failure happened earlier, while parsing
the Quick Add input.

The historical contents of user ID 2 and the server's old `/tmp` save log could
not be inspected through the public API without the user's authenticated Google
session. Cloning the user or bypassing authentication was unnecessary and
would not have isolated this parser defect.

## Fix

The deployed FavCreators bundle now recognizes a full TikTok profile URL before
falling back to the legacy colon-delimited parser:

```javascript
const match = /^https?:\/\/(?:www\.)?tiktok\.com\/@([^/?#]+)/i.exec(input.trim());
```

With the fix:

```text
https://tiktok.com/@nikkibby11
  -> creator name: nikkibby11
  -> platform: tiktok
  -> username: nikkibby11
  -> URL: https://tiktok.com/@nikkibby11
```

`https://tiktok.com/@gurleen_dosanjh` is normalized the same way.

Authentication was not bypassed. Saving still requires the normal authenticated
session and only writes to that signed-in user's creator list.

## Verification

- `node favcreators/tests/quick_add_url_test.js` - passed.
- `node --check favcreators/docs/assets/main-DF_ZQ_dn.js` - passed.
- The live page references `assets/main-DF_ZQ_dn.js`.
- The live JavaScript bundle contains the TikTok URL parser shown above.
- A direct parser comparison confirmed:
  - old result for `nikkibby11`: name `https`, unsupported platform
    `//tiktok.com/@nikkibby11`;
  - fixed result: name `nikkibby11`, platform `tiktok`.

No production user record was cloned or mutated during this investigation.

## Cross-platform Quick Add audit

The current live bundle uses a URL normalizer before the legacy
`name:platform` parser. It prepends `https://` when the user enters a bare
domain and strips `www.`. Current accepted profile URL families are:

| Platform | Accepted URL examples | Result |
|---|---|---|
| TikTok | `tiktok.com/@user`, `https://www.tiktok.com/@user` | Extracts `user`; canonicalizes to a TikTok profile URL |
| YouTube | `youtube.com/@channel`, `/channel/ID`, `/c/name` | Extracts the channel identifier |
| Instagram | `instagram.com/user` | Extracts `user` |
| Kick | `kick.com/user` | Extracts `user` |
| Twitch | `twitch.tv/user` | Extracts `user` |
| Twitter/X | `twitter.com/user`, `x.com/user` | Extracts `user`; stores the canonical Twitter URL |

The URL normalizer deliberately does not treat post/video URLs as profile
URLs. For example, a TikTok `/video/...` URL is not accepted as a profile
follow, which is safer than silently following the wrong account.

### Major remaining gaps

1. **Reddit and Spotify are backend-supported but not Quick Add URL-supported.**
   The backend status endpoints allow both platforms, but the live Quick Add
   normalizer has no `reddit.com` or `open.spotify.com` branch. A user entering
   a Reddit or Spotify URL falls through to the legacy parser and can create
   an incorrectly named creator with no account, reproducing the original
   persistence symptom.
2. **YouTube `/user/<name>` URLs are not recognized.** The normalizer supports
   `@handle`, `/channel/`, and `/c/`, but not the still-common `/user/` form.
3. **Legacy `name:platform` input remains permissive.** Unknown platform tokens
   can still produce a local creator with an empty account list. The UI should
   reject unsupported platforms and show an error instead of saving that
   creator.
4. **Quick Add and the regular Add Creator form have separate normalization
   paths.** A future platform fix can easily update one path while leaving the
   other inconsistent.

### Recommended fix order

1. Extract one shared, tested `parseSocialProfileUrl()` helper used by both
   Quick Add and the regular Add Creator form.
2. Add explicit Reddit profile handling (`reddit.com/u/name` and
   `reddit.com/user/name`) and define the supported Spotify URL shape before
   implementing it; Spotify artist/show URLs are not equivalent to a user
   profile and need a product decision.
3. Add YouTube `/user/<name>` support.
4. Reject unknown platform tokens and empty account arrays at the frontend,
   then have `save_creators.php` validate every account's platform and required
   username before replacing the user's list.
5. Add table-driven tests for bare domains, `www`, `http`, `https`, query
   strings, trailing slashes, post/video URLs, and unsupported hosts. Verify
   both the immediate UI state and a fresh `get_my_creators.php` read after
   reload.

These are correctness and data-integrity improvements. They are not needed to
fix the reported TikTok case, which is now covered by the live normalizer.
