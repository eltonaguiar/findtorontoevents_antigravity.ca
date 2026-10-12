# Correct stale perfect scores and expose rating confidence

## What was broken

The legacy `movies.imdb_rating` field actually stores TMDB's `vote_average`.
The importer skipped existing titles, so five playable titles retained old
10.0 scores even though their current TMDB scores had fallen. Other 10.0
scores were current, but were based on only one to five votes.

Verified directly against TMDB's detail API on October 12, 2026:

| Title | Old stored score | Current TMDB score | Votes |
| --- | --- | --- | --- |
| Love You Teacher | 10.0 | 8.6 | 14 |
| Born to Bowl | 10.0 | 7.5 | 4 |
| A Great Awakening | 10.0 | 7.4 | 29 |
| Fist of the North Star: HOKUTO NO KEN | 10.0 | 8.2 | 30 |
| The Other Side of Deep Space | 10.0 | 9.3 | 7 |

IMDb scores could not be independently verified from the retrieved title
pages. No search-summary claim was substituted for an IMDb rating.

## What changed

- The user approved refreshing stale TMDB scores and displaying vote counts.
  They selected **50 votes** as the provisional-label threshold.
- Authenticated `fetch_new_content.php?mode=ratings` refreshes the perfect-score
  playable cohort, then keeps refreshing those tracked titles after their scores
  fall below ten. It uses the existing private TMDB credentials and authentication.
- `movie_rating_details` stores vote counts and server-side verification
  timestamps. Scores and metadata are updated in a transaction; errors fail
  explicitly and identify affected records without disclosing credentials.
- TMDB title identity, score range, and nonnegative integer vote counts are
  checked before writing. Numeric scores are not clamped or confidence-adjusted.
- Both MS2/MS3 feeds and MS2 pagination/search/genre/random responses expose
  `rating_source`, `rating_vote_count`, `rating_provisional`, and
  `rating_checked_at`.
- MS2 slides, top-rated fallback cards, and MS3 cards/queues/browse surfaces
  label the source and confidence. Example:
  **TMDB 10.0 (5 votes; provisional)**.
- The existing daily verifier now refreshes the tracked ratings after importing
  new titles and compares the persisted scores/counts/timestamps to API results.
- Deployment initializes the helper/schema before dependent API files are
  replaced. All three deployments use encrypted FTPS. V2 script references
  are cache-busted while preserving the static export and enhancement scripts.

The initial diagnostic refresh included non-playable archived titles: 44/43
were successfully checked on the two databases, while two hidden records
(`Mr & Mrs Gao`, `Football 17776`) failed TMDB lookup. The final new-candidate
query is limited to the playable feed; previously successful tracked records
remain in the cohort. Those two unresolved archived titles were not assigned
invented ratings or hidden as successful refreshes.

This is not an IMDb integration or a whole-catalogue re-rating. V1's separate
static catalogue is unchanged.

## Verification

- Failing tests reproduced the missing refresh, missing vote labels, and
  missing top-rated fallback labels before those implementations.
- `PHP_BINARY=<local php8.3> python3 -m pytest tests/test_movies_rating_refresh.py tests/test_run_movies_refresh.py tests/test_movies_db_config.py tests/test_movies_legacy_wrapper.py -q --tb=short`:
  **64 passed**.
- `NODE_PATH=<existing repository node_modules> node --test tests/test_movies_rating_display.js`:
  **9 passed**, including Chromium DOM rendering, both frontend confidence
  formats, and V2 fallback mapping.
- PHP syntax checks passed for all five changed/new PHP files. Deployment YAML
  parsed and its embedded Python compiled after shell quote decoding.
- Independent review found a deployment ordering issue; the fix and regression
  test ensure initialization failures leave dependent APIs undeployed.
- All six live feeds across three domains returned corrected values and vote
  metadata. 50webs has 10 playable tracked titles; GoDaddy has nine.
- Remaining playable 10.0 scores: five on the shared 50webs database, four on
  GoDaddy; each is source-verified and labeled provisional.
- Live production V3 renderer produced both:
  `TMDB 10.0 (5 votes; provisional)` for Firefly Wedding and
  `TMDB 8.6 (14 votes; provisional)` for Love You Teacher.

No credential values are included in this documentation.
