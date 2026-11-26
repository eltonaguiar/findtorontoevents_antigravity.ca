# Movie refresh back to green on both hosts (2026-11-26)

Follow-up to `updates/2026-11-26-movieshows3-api-status-500-fix.md`. Fixing
`api_status.php` exposed two more deployment-drift faults behind it. All three are
now fixed and `kimi-fetch-movies.yml` passes end to end.

## The chain, in the order the refresh hits it

1. **`log/api_status.php`** — returned 500 with a raw SQLSTATE because a stale copy
   built PDO inline with dead credentials. Fixed in #1199 (deployed file, plus the
   catch block no longer echoes the exception, which was leaking the SQLSTATE and the
   database user name). Added to both deploy lists.

2. **`fetch_new_content.php` on 50webs** — never deployed by the hotfix workflow at all,
   so 50webs still served an old copy that answered `Unauthorized` as plain text
   (13 bytes) where the repo answers JSON (58 bytes). The refresh script parses that
   endpoint, so it aborted with `did not return valid JSON`. Fixed in #1202 by adding
   the file to both deploy lists.

3. **`fetch_new_content.php` on PHP 5.2** — once deployed, 50webs returned an empty
   HTTP 500. Cause: line 23 called `http_response_code(403)`, which is PHP 5.4+, while
   50webs runs **PHP 5.2.17** (visible in the `x-powered-by` header). With
   `display_errors` off this is a fatal error with no body. The file header already
   claimed 5.2 compatibility. Fixed in #1203 with a `function_exists` guard and a raw
   `HTTP/1.1 403` fallback.

## Verification

- `fetch_new_content.php?key=invalid` returns the JSON 403 body on **both** hosts
  (it was an empty 500 on 50webs).
- `log/api_status.php` returns 200 with `total_records` on both hosts.
- `kimi-fetch-movies.yml` run 45777044885 → **success**:
  - `VERIFIED https://findtorontoevents.ca: {"added": 3, "fetched": 120, "ratings_verified": 18, "skipped": 117, "total_records": 8150}`
  - `VERIFIED https://torontoevent.net: {"added": 0, "fetched": 120, "ratings_verified": 18, "skipped": 120, "total_records": 8152}`

## Lesson

50webs still runs PHP 5.2.17, so anything under `MOVIESHOWS3/` must stay 5.2-safe.
`http_response_code()`, short array syntax, `??`, closures and arrow functions are all
off limits there, and a violation fails as an empty 500 rather than a useful error
because the scripts set `display_errors` to 0.
