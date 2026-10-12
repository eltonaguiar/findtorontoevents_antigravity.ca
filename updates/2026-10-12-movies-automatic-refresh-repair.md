# Movie database automatic refresh repair

## What was broken

The daily movie workflows were enabled, but their green status did not prove
that the database had been refreshed. The October 11 MOVIESHOWS3 run
(`38120297794`) logged that `MS2_SYNC_KEY` was missing and skipped the fetch with
exit code zero. Its subsequent status response said `DB connection failed`;
the workflow still succeeded with a title count of `unknown`.

Other problems in the scheduled paths:

- Refresh validation grepped for `Status: success` text, although the importer
  returns JSON with `success`, `summary`, and `log_entry`.
- Status validation read `stats.total_titles` rather than `total_records`.
- Legacy scheduled deploy helpers skipped missing source files and could
  reintroduce old scripts. The Kimi PHP fetcher contained only `<?php`.
- The separate GoDaddy database was not included in the daily refresh.
- A `discover` workflow input was not supported by the importer.

## What changed

- `fetch-movies-v3.yml` is the single daily database refresh, at **07:00 UTC**.
  GitHub may start scheduled jobs later than their nominal time.
- `tools/run_movies_refresh.py` calls the existing authenticated MOVIESHOWS3
  importer on `findtorontoevents.ca` and `torontoevent.net`. `tdotevent.ca`
  shares the first database and must not be redundantly imported.
- Missing authentication, HTTP/transport failures, invalid JSON, API failures,
  zero candidates, import errors, inconsistent counts, or missing durable logs
  fail the job explicitly. Both hosts are attempted, even if one fails.
- The added-title count must match the before/after database row-count delta.
  A duplicate-only refresh is valid when candidates and the saved log prove
  that an import actually ran.
- The two legacy workflows remain available as manual actions using the same
  verifier. Their duplicate schedules and stale FTP deployments are removed.
- All three actions share concurrency with cancellation disabled.
- The previously absent repository `MS2_SYNC_KEY` secret was configured from
  the existing deployed endpoint token, without printing or committing it.

Deployment remains separate from data refresh. Private database credentials and
the validated TMDB key remain on the hosts; scheduled refresh does not overwrite
them or redeploy HTML.

This importer discovers and inserts new titles; it skips existing titles. It
does **not** recalculate every existing rating or rebuild the static V1 catalogue.

## Verification

- Regression tests were introduced before implementation and initially failed
  because the verifier did not exist.
- `python3 -m pytest tests/test_run_movies_refresh.py -q --tb=short`:
  16 passed, including missing secrets, false-success JSON, old status schema,
  count/log mismatches, duplicate-only imports, host coverage, and token-safe
  transport errors.
- Independent review confirmed the PHP response contracts and quoted the
  pre-change false-green workflow lines. No high-confidence blockers.
- Live invocation of the new verifier with the private key:
  - 50webs: 120 candidates, 7 added, 113 skipped, **7,906 total records**.
  - GoDaddy: 120 candidates, 1 added, 119 skipped, **7,902 total records**.
  - Both passed count-delta and matching persisted-log verification.
- Merged repair deployment action `38199721462` succeeded. All six MS2/MS3
  APIs returned successful populated responses across the three domains;
  protected credential locations returned HTTP 403; V1 stayed on its own route.

No database passwords, TMDB credentials, or sync token values are included here.
