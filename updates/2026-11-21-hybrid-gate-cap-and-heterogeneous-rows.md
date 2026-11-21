# Gate the two large artifacts, and fix the crash the cap was hiding

## What was broken

`tools/detect_merge_hybrid.py` skipped any artifact over 12 MB. Two committed
artifacts were over it, so they were never gated at all:

| artifact | size | before |
|---|---|---|
| `audit_dashboard/data/pf_registry.json` | 15.9 MB | skipped every run |
| `alpha_engine/data/expired_picks_archive.json` | 32.1 MB | skipped every run |

The skip was one line of stdout in a 60-minute job log, which is close to silent.

Raising the cap then exposed a second bug: `inspect()` indexed `r[key]` for the
identity field chosen by `identity_key()`, which only requires that field in 90% of
rows. `expired_picks_archive.json` has rows both with and without `symbol`, so
inspecting it raised `KeyError: 'symbol'`. The 12 MB cap had been hiding that by
never inspecting the file.

## Measured first

| artifact | load | inspect | findings | peak RSS |
|---|---|---|---|---|
| `pf_registry.json` (15.9 MB) | 0.06 s | 0.11 s | 0 | 56 MB |
| `expired_picks_archive.json` (32.1 MB) | 0.11 s | 0.00 s | 0 | 136 MB |

Streaming would have been pointless work for those numbers, so the cap is the
right lever.

## What changed

* `MAX_BYTES` 12 MB -> **64 MB**, with the measurements recorded in a comment.
* **`--max-mb`** flag, so the cap is adjustable without a code change.
* A skipped artifact now prints `-- NOT gated`, and `main()` emits a
  `WARNING: N artifact(s) were NOT gated (over the X MB cap): ...` summary on
  stderr. A skip can no longer be a quiet line in the middle of the log.
* `inspect()` ignores rows that lack the identity key instead of indexing them,
  and reads the display name with `.get()`. Rows without the key simply do not
  participate in duplicate detection.
* Four tests: the 90%-coverage fixture that used to raise `KeyError`, the cap
  floor, the `NOT gated` warning, and the under-cap path.

## How verified

* `pytest tests/test_detect_merge_hybrid.py` -- 16 pass.
* The real archive that raised `KeyError`: inspected without error, 0 findings.
* Both large artifacts inspected in-process under the new default cap, 0 findings.
* The real gate invocation over the last hourly refresh commit
  (`8f01ba22ce7c`): `no hybridised artifacts (43 inspected)`, **0 skipped**.

## Limits

* 64 MB is still a cap: a larger artifact would be skipped, though now loudly.
* Peak RSS for a 32 MB artifact is ~136 MB; a 64 MB artifact would be a few
  hundred MB, which is fine on a GitHub runner but worth knowing.
* The detector still only walks two levels of nesting, and still only compares a
  count with an array whose name it carries (see the scan report for why).
