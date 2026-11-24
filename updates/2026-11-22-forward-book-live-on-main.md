# Forward paper book: ported to main so it can actually run

## What was broken

The forward paper book was built, seeded with 5 entries and wired into
`audit3-ledger.yml` — but every commit lived on the branch
`fix/dsr-baselines-h146-key-scrub-2026-11-21`, which was **pushed and never
merged**. `origin/main` had no `tools/forward_book.py` at all, so:

- the workflow never ran the resolve step (the step did not exist on main),
- `/audit3/forward_book.json` returned **404**,
- `/audit/audit3.html` returned **404** (the upload block was also branch-only),
- the deployed `/audit3/index.html` contained no forward-book section.

The scheduler was healthy the whole time (`audit3-ledger.yml` run
44994305292, success, 2026-11-22T06:34Z) — it was running main's older code.
"Pushed" was not "merged", and that gap was reported as if the feature were live.

## What changed

Branch `buffy/forward-book-live-2026-11-22`, cut from `origin/main` and carrying
**only** these changes (the old branch is 890 commits behind and carries other
agents' commits, so it could not be merged directly):

- `tools/forward_book.py` (new) — emit / resolve / publish / score.
- `tools/ohlc_bars.py` (new) — Binance daily klines, 6h cache in `/tmp`.
- `audit_dashboard/data/forward_book.json` (new) — 5 pre-registered entries.
- `.github/workflows/audit3-ledger.yml` — resolve+publish step before deploy;
  `forward_book.json` added to the `/audit3` upload list; the `/audit` block now
  stores `audit3.html` (that URL was previously written by no workflow at all).
- `audit_dashboard/audit3.html` — data fetches made absolute (`/audit3/*.json`) so
  the page works at both `/audit3/` and `/audit/audit3.html`; forward-book section
  renderer added.

Both shared files were ported as patches generated against main, so main's newer
content is preserved rather than overwritten by the older branch versions.

## Verification

- `git apply --check` on both patches against a fresh `origin/main` worktree: clean.
- `py_compile` on `forward_book.py` and `ohlc_bars.py`: OK.
- `yaml.safe_load` on the workflow: OK, one job (`ledger`).
- Wiring present on the ported tree: resolve step at line 288, upload tuple at 315,
  two `forward_book` references in `audit3.html`.
- `python3 tools/forward_book.py --resolve --publish`: exits 0, publishes
  `{"entries": 5, "open": 5, "resolved": 0}` — correct, because every entry is
  dated the current bar and nothing resolves until a later bar exists.
- `resolve()` exercised against real bars rather than assumed: a throwaway entry
  on BTC-USD dated 2026-11-01 resolved SL at exit 76786.92, 21 bars walked,
  gross −2.0% / net −2.2% after the 20bp crypto cost.

## Still unverified

The two live URLs cannot be checked from this machine (no FTP credentials).
They become verifiable after this branch merges to main and the next scheduled
`audit3-ledger.yml` run (cron `23 */6 * * *`) deploys.

## Note on the original docstring

`forward_book.py` described the entry price as coming from "the last CLOSED daily
bar". It is in fact the most recent bar, which is the current day's bar while it
is still forming. The docstring was corrected rather than the behaviour: a
forward entry must be priced at a price actually observable when it is
registered, and `resolve()` already skips the entry bar when walking exits.
