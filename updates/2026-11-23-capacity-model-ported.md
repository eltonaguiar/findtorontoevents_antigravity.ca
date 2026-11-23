# 2026-11-23 — port `tools/capacity_model.py` and its test to main (closes the HML provenance gap)

Base: `origin/main` at `0f9c35906e1`. (The block brief quoted `1bcddbf6eb86`; the remote had
advanced by the time of the fresh clone, which is expected on a busy main. The port branches
from whatever `origin/main` was at clone time.)
Worktree used for verification: `/tmp/port-capacity`, a fresh non-shallow clone
(`git rev-parse --is-shallow-repository` → `false`), never the shared working tree, which sits
on the local-only `push/phase2-round-2026-11-22` branch.

## What was broken / missing

`docs/preregistration/HML_VALUE_TEST_2026-11-22.md` cites `tools/capacity_model.py:49` for the
4.32% policy rate, but that file was **absent from `origin/main`**:

```
$ git cat-file -e origin/main:tools/capacity_model.py   # exit 128 (absent)
$ git ls-tree origin/main -- tools/capacity_model.py    # (no output)
$ git ls-tree origin/main -- tests/test_capacity_model.py  # (no output)
```

The file survives only on the remote branch `origin/push/phase2-round-2026-11-22`, added by
commit `1c15c5d7d07` ("research: phase-2 profitability round …"). The 4.32% hurdle was therefore
not reproducible from a clean clone of main. A provenance-gap blockquote was previously appended
to the frozen doc (in `updates/2026-11-23-provenance-and-stale-figure-corrections.md`, Fix 2a);
this update closes the gap properly by restoring the source.

The branch is **42 commits ahead of its merge-base with main** (`d1172ea42655`), measured with
`git rev-list --count $mb..origin/push/phase2-round-2026-11-22`. (An earlier figure of 169 was
wrong; 169 is the count of the local-only working-tree branch, not this remote branch.)

## What changed

- Added [`tools/capacity_model.py`](../tools/capacity_model.py) — the exact 579-line artifact
  from `origin/push/phase2-round-2026-11-22` (`sha256
  763951124f2ed6736c42d8a9d0cde3eb4ecfc2f91e18c8b00a965d1be8359f0e`), copied byte-for-byte with
  no reformatting.
- Added [`tests/test_capacity_model.py`](../tests/test_capacity_model.py) — the exact 103-line
  test from the same branch (`sha256
  d931e5259d1caf7cead90b671e9a57c7ba91af29f2c92397f03db320bdb524cf`).

`tools/capacity_model.py:49` now holds, verbatim:

```python
HURDLE_TBILL_APR = 0.0432          # 4.32% -- the programme hurdle, docs/edge_research/07
```

So the pre-registration's cited constant is now reproducible from a clean clone of main and the
**provenance gap is closed**. The frozen document's own annotation is left exactly as-is: we do
not edit a frozen document to reflect a later fix; this file is the forward reference.

**No AGENTS.md registry row was added.** `git grep -n 'capacity_model' origin/main` shows the
file referenced only in docs, reports and updates (as a `[SRC: …]` citation and the recorded gap),
never imported as code by the audit-dashboard pipeline. The module is a standalone research CLI
(`python3 tools/capacity_model.py`), not a pipeline dependency.

## How it was verified

Run inside `/tmp/port-capacity` on the branch, after copying:

```
$ sha256sum tools/capacity_model.py tests/test_capacity_model.py
763951124f2ed6736c42d8a9d0cde3eb4ecfc2f91e18c8b00a965d1be8359f0e  tools/capacity_model.py
d931e5259d1caf7cead90b671e9a57c7ba91af29f2c92397f03db320bdb524cf  tests/test_capacity_model.py

$ python3 -c "import py_compile; py_compile.compile('tools/capacity_model.py', doraise=True)"   # OK
$ python3 -c "import sys; sys.path.insert(0,'.'); import tools.capacity_model as m; print(m.HURDLE_TBILL_APR)"
0.0432

$ python3 -m pytest tests/test_capacity_model.py -q
16 passed in 0.11s

$ python3 tests/test_capacity_model.py
Ran 16 tests in 0.000s
OK
```

Imports are all stdlib (`argparse`, `bisect`, `glob`, `json`, `statistics`, `collections`,
`pathlib`, `__future__`), so nothing else needs to be ported. A secret / absolute-path scan
(`/home/`, `/Users/`, drive letters, `api_key`, `secret`, `token`, `password`, `bearer`, `sk-`)
returned no hits in either file.

## What remains

The frozen pre-registration still carries its 2026-11-23 provenance-gap blockquote; that is
intentional (frozen documents are not retro-edited). A reader arriving at the doc via the
`[SRC: tools/capacity_model.py:49]` citation will now find the line resolvable on main. The
peer-claim verification entries that recorded B11 as `NOT LANDED` are historical records and
are left unchanged; the claim is now true against `origin/main`.
