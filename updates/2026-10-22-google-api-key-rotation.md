# Google API credential rotation — 2026-10-22

**Follow-up:** [Live YouTube wiring](2026-10-22-youtube-live-key-wiring.md)
completes the production caller connection described as not yet active below.
Both movie-search versions now use the private replacement on all three sites.

## What was broken

The retired Google credential was hardcoded in both STOCKSUNIFY stock API
configuration modules. A nested copy was also deployed on findtorontoevents.ca,
tdotevent.ca, and torontoevent.net. TypeScript source is not executed by the
PHP/static hosting service and must not be downloadable as credential-bearing
source.

The stock fetchers do not currently read `GOOGLE_CUSTOM_SEARCH`; they use other
providers. The movie search APIs use their own `YOUTUBE_API_KEY` environment
setting and a separate public InnerTube key. FavCreators' latest-video endpoint
uses RSS. These unrelated configurations were not replaced.

## What changed

- Both Google Custom Search exports now resolve
  `GOOGLE_CUSTOM_SEARCH_API_KEY` lazily from the server environment. Access
  without configuration raises an explicit error; importing the module and
  using other stock providers still works without a Google key.
- Added Apache access controls blocking HTTP downloads of `stock-api-keys.ts`.
- Patched the three deployed copies over certificate-verified FTPS, preserving
  their other deployed differences instead of overwriting whole files.
- Read the replacement from the specifically labeled section of the private
  credential source. It was not placed in repository files, JavaScript,
  documentation, command arguments, or public API responses.
- Provisioned an owner-only private environment file on each FTP account.
  On 50webs it is outside the individual site roots; on GoDaddy it is in an
  Apache-denied directory. Verified denial with a disposable nonsecret canary
  before uploading the credential. The files use mode 600 and directories 700.
- Created an owner-only local environment file outside the repository at
  `$HOME/.config/findtorontoevents/google-api.env`. To run an optional stock
  search consumer locally, source that file before starting the Node process.
  Static FTP hosting does not execute these stock scripts; provisioning the
  private file does not activate a new Google-consuming production path.

## Verification

- `node --experimental-strip-types --test tests/google-api-key-config.test.mjs`
  — 2 tests passed. Covers both modules, missing/empty configuration, runtime
  rotation, unchanged stock-provider availability/CSE ID, no embedded Google
  key, and presence of source-download protection.
- Both modules loaded the actual provisioned replacement in memory without
  logging it.
- Real YouTube Data API request using an API-key header — HTTP 200, one video
  returned, no key echoed.
- Real Custom Search request with the existing CSE ID — HTTP 403:
  `This project does not have the access to Custom Search JSON API.`
  The replacement is valid for YouTube, but Custom Search requires Google-side
  project access. No claim is made that Custom Search is operational.
- Final FTPS scans: 959 application/source files across the two 50webs sites
  plus 1,106 on the GoDaddy mirror; zero retired- or replacement-key matches.
  These are scoped application scans, not every archive or Git object on the
  hosting accounts. The intentionally private credential files are outside
  this public-application scan.
- All three deployed source URLs return HTTP 403. Private credential URLs
  return 403/404, including checks through the 50webs account hostname and the
  GoDaddy `www` hostname.
- Live stock JSON and both movie-search endpoints retain HTTP 200 on all
  three domains; no retired or replacement credential appeared in the checked
  responses.
- Active-worktree scan, including ignored files — zero retired-key matches.
  Replacement-key scan across the active and other local worktrees — zero
  matches. Existing retired-key copies in other agents' historical worktrees
  were left untouched.
- `git diff --check` for the modified stock modules — passed.

## Remaining operational boundary

Removing a hardcoded key does not revoke it or erase Git history, existing
archives, or other agents' old worktrees. Retire/restrict the previous key in
Google Cloud. The replacement should remain restricted to the intended APIs
and server usage. Google Cloud administrative credentials were not used, and
no revocation or project-access changes are claimed.

*Not financial advice. Research/educational only. Past performance does not guarantee future results.*
