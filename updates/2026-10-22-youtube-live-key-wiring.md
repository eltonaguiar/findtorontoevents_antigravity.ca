# Live YouTube replacement-key wiring — 2026-10-22

## What was incomplete

The first credential-rotation change removed the old hardcoded stock key and
provisioned a private replacement, but did not connect the movie-search
endpoints to that replacement. Static FTP hosting does not automatically source
an environment file into PHP. Live diagnostics confirmed that PHP could not
read the account-level configuration path on 50webs.

Custom Search was an unused configuration entry: no active application caller
was found. Its Google project-access rejection does not break an existing
feature. The separate public InnerTube key is not the retired user credential;
it remains unchanged. The unrelated TMDB credential also remains unchanged.

## Changes

- Both `MOVIESHOWS2/api/freestyle-search.php` and
  `MOVIESHOWS3/api/freestyle-search.php` load `YOUTUBE_API_KEY` from the server
  environment or a private `credentials.php` array with `youtube_api_key`.
- Private configuration lookup supports an account-level directory and a
  protected directory inside the site root, following the existing movies
  database configuration pattern. The loader requires a readable access guard.
  Missing or invalid configuration is logged without credential values.
- Provisioned the replacement inside each site's `.google-api-private`
  directory using a deny-all Apache guard, mode 700 on the directory and mode
  600 on the PHP credential file. A nonsecret canary was verified inaccessible
  before the key was uploaded. The private file is not in Git.
- Official YouTube search is now the first provider. Existing public search,
  proxy, Dailymotion, and Internet Archive fallbacks remain available.
- The new official request sends the key in `X-Goog-Api-Key`, not the URL.
  TLS certificate and hostname verification are enabled, redirects are not
  followed, and upstream error bodies are not returned or logged.
- Existing frontend result fields are retained, with `source: youtube_official`
  identifying successful official API responses. A legitimate empty result is
  not treated as a provider failure.
- Existing deployment manifests already include both changed handlers, so
  no new public dependency file or deployment-manifest changes are necessary.

## Verification

The test suite is [test_youtube_official.php](../tests/test_youtube_official.php).
With a PHP CLI it can be run as:

```sh
php tests/test_youtube_official.php
```

A local PHP CLI was unavailable. The same suite was executed on the actual
hosting PHP runtimes through temporary, header-authenticated test wrappers.
Wrappers returned 404 without authentication and were deleted after each run.
The previous source failed the regression with missing wiring; the candidate
passed **25 checks on each of the three domains**. Checks cover private-path
lookup, environment precedence, invalid/missing credentials, result shape,
empty/malformed upstream data, transport failure, fallback behavior, TLS,
header-only credentials, and secret-free output/logging.

Certificate-verified FTPS uploads and byte-for-byte readback were followed by
real production searches for both versions on:

- `findtorontoevents.ca`
- `tdotevent.ca`
- `torontoevent.net`

All six returned HTTP 200, `success: true`, `source: youtube_official`, and
20 video results with valid 11-character video IDs. Each response was checked
for both old and replacement key values without printing them.

Authenticated, temporary runtime diagnostics on each host also confirmed that
the exact replacement was loaded (digest comparison only), with no environment
override, and the host's upstream Google request returned HTTP 200 with cURL
error number zero. Those diagnostic endpoints were removed immediately.

Final checks: all three private-config URLs and their encoded-dot equivalents
return HTTP 403, as do the stock credential source URLs. Missing-query behavior
is unchanged. Public-source scans of 959 files on 50webs and 1,106 on GoDaddy
found zero old/replacement key matches. A repository scan, including ignored
files and the replacement-key check across other worktrees, found no replacement
literal. Other agents' historical worktrees were not modified. Only explicitly
private credential files are intended to contain the new key.

## Operational notes

Each official search uses YouTube's search quota, unlike the public scraping
fallbacks. Google quota/authorization failures are logged by HTTP status and
fall through to the existing providers without exposing the key. Do not copy
the private credential into browser JavaScript or deploy it with public files.

Custom Search remains unavailable to this Google project and has no production
caller to repair. No new Custom Search feature or Gemini caller was introduced.

*Not financial advice. Research/educational only. Past performance does not guarantee future results.*
