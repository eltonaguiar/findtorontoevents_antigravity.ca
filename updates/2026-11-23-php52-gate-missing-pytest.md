# PHP 5.2 gate failed on a missing dependency, not a code defect

**Date:** 2026-11-23
**Branch:** `copilot/hub-audit-2026-11-23`
**PR:** #1096

## What was broken

The `php52` check on PR #1096 failed in 25 seconds with:

```
/opt/hostedtoolcache/Python/3.12.16/x64/bin/python3: No module named pytest
##[error]Process completed with exit code 1.
```

`.github/workflows/php52-gate.yml` used `actions/setup-python@v5` and then ran
`python3 -m pytest tests/test_php52_goldmines.py -q`, but never installed pytest.
`setup-python` provides the interpreter only — it does not ship pytest.

The failure mode is misleading: a red required check named "Regression tests for the
goldmine API defect" reads like the goldmine fix regressed, when in fact the test
binary was never present. The same gate on `push: main` would have failed the same way.

## What changed

Added an explicit install step between `setup-python` and the validator:

```yaml
      - name: Install pytest
        run: python3 -m pip install --quiet --disable-pip-version-check pytest
```

Nothing else in the workflow was touched. The gate remains read-only — no secrets, no
commits, no deploys — and still gates only served PHP (`investments/**/*.php`,
`tools/validate_php52.py`, `tests/test_php52_goldmines.py`).

## How it was verified

- The 7 tests in `tests/test_php52_goldmines.py` pass locally on the merged tree
  (`origin/main` `1bcddbf6eb8` + this branch): `7 passed`.
- Full local run of all 6 modified pytest files on the merged tree: **82 passed, 0 failed**.
- The failure was reproduced from the actual failing check log
  (`gh run view 45127569436 --log-failed`), not inferred.

## Related

The `movies` test files (`test_movies_db_config.py`, `test_movies_legacy_wrapper.py`,
`test_movies_rating_refresh.py`) skip when no PHP CLI is present. That is by design —
the skip was added 2026-11-23 so a missing PHP does not inflate the failure count. The
consequence is that CI green on those three files does **not** prove they executed.
