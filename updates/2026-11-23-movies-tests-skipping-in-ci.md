# Three test files were silently skipping in CI — "green" was hollow

**Date:** 2026-11-23
**Branch:** `copilot/hub-audit-2026-11-23`
**PR:** #1096

## What was broken

`tests/test_movies_db_config.py`, `tests/test_movies_legacy_wrapper.py` and
`tests/test_movies_rating_refresh.py` all carry:

```python
PHP = os.environ.get("PHP_BINARY") or shutil.which("php")
pytestmark = pytest.mark.skipif(not PHP, reason="PHP CLI not available (set PHP_BINARY)")
```

No PHP is installed on the `ubuntu-latest` runner, so **all 46 tests reported
`SKIPPED`** and the suite still exited `0`. CI was green while 631 lines of
coverage never executed.

The skip itself is correct and was a deliberate 2026-11-23 change (a missing PHP
should not inflate the failure count). The problem is that nothing made the
*consequence* visible: a green `test (3.11)` / `test (3.12)` read as proof that
those three files passed.

This was flagged twice earlier in the session and is the reason the writer work
in `updates/2026-11-23-stock-picks-writer-restored.md` was verified locally
against a real PHP binary rather than trusted to CI.

## What changed

`.github/workflows/ci-tests.yml` gains an install step before the suite runs:

```yaml
      - name: Install PHP CLI (movies tests skip without it)
        run: |
          set -euo pipefail
          sudo apt-get update -qq
          DEBIAN_FRONTEND=noninteractive sudo apt-get install -y -qq --no-install-recommends php-cli
          php -v | head -1
          php -n -r 'exit(extension_loaded("pdo") ? 1 : 0);' \
            || { echo "FAIL: PDO is built into this PHP; ..."; exit 1; }
```

No movies test is in the known-drift quarantine list and the suite does not
deselect them, so installing PHP is sufficient for them to run.

## Why `-n` / shared PDO matters (the trap)

These tests drive the real `db-config.php` with a **stubbed `class PDO`**, passing
`-n` (no ini) so the real extension is absent and the stub can be declared.

- Ubuntu/Debian `php-cli` loads PDO from `conf.d/*.ini` → `-n` hides it → the stub
  works. ✅
- The official `php:8.x-cli` docker image compiles PDO in **statically** → `-n`
  cannot hide it → `Fatal error: Cannot declare class PDO, because the name is
  already in use` (exit 255).

That mismatch produced 25 false failures during local verification before it was
identified, so the workflow now asserts `extension_loaded("pdo") === false` under
`-n` and fails loudly otherwise — a future change to the runner's PHP packaging
will name the actual problem instead of surfacing as 46 confusing test failures.

## How it was verified

- `ubuntu:24.04` + `apt-get install php-cli` → **PHP 8.3.6**, `-n` → `pdo=absent`.
- Ran the three files against that binary: **46 passed**.
- Cross-checked on Debian 12 `php-cli` → **PHP 8.2.36**, also `46 passed`.
- Version parity was checked *before* wiring, because the earlier verification used
  8.2 while `ubuntu-latest` ships 8.3.

Expected effect: the `test (3.11)` / `test (3.12)` jobs now report 46 additional
tests as **passed** rather than skipped.
