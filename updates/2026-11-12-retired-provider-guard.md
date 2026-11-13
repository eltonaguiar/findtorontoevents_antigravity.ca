# Retired-provider guard: `tools/check_retired_providers.py`

**Date:** 2026-11-12
**Branch:** `feat/retired-provider-guard-2026-11-12`
**Related:** `scrub/inception-mercury-2026-11-12` (the 36-file retirement this protects)

## The problem this fixes

The Inception Labs "Mercury" API sunsets **2026-12-28**. The retirement branch deletes the
provider from 36 config and code files. Deletion is not the hard part — keeping it deleted
is. The realistic regression is mundane: someone pastes an older `.env` example, restores a
saved roster, or copies a key list from a chatlog, and the LiteLLM proxy quietly starts
routing traffic at an API that no longer answers. Nothing fails loudly; the group just
returns errors under load.

There was no check that would notice. This adds one.

## What was added

`tools/check_retired_providers.py` — scans a fixed list of **provider-defining** files and
exits non-zero if a retired provider reappears.

Scan surface (369 files today): `litellm_config.yaml`, `config/api_model_roster.json`,
`.env.example`, `tools/swarm/ENGINE_KEY_ENVS.py`, `tools/swarm/swarm.config.example.json`,
`tools/start_litellm_proxy.sh`, `tools/verify_all_keys.py`,
`tools/swarm_v2/swarms/core/llm_client.py`, `.ruflo/orchestrator.py`, and every
`.github/workflows/*.yml`. Each entry carries its reason in the `SCOPED` table and
`--list` prints them.

Usage:

```
python3 tools/check_retired_providers.py            # report; exit 1 on hits
python3 tools/check_retired_providers.py --quiet    # exit code only (CI)
python3 tools/check_retired_providers.py --json     # machine readable
python3 tools/check_retired_providers.py --list     # the scan surface, with reasons
```

Exit codes: `0` clean, `1` retired provider found, `2` internal error.

To wire it into CI, add one step to any workflow that already runs repo checks:

```yaml
      - name: No retired providers
        run: python3 tools/check_retired_providers.py
```

That step was deliberately **not** added to a workflow in this change: workflow files here
are edited by other agents and by the retirement branch itself, and mixing an unrelated
one-line CI edit into either would make a review harder, not safer.

## Three precision decisions (each earned by a false positive)

1. **`mercury` alone is ambiguous.** In this repo it is both the retired Inception model
   name and a live local trading package (`python -m mercury2`, xgboost/joblib models
   driven by `.github/workflows/mercury2-scan.yml`). A bare `mercury` rule flagged that
   strategy 14 times. `mercury` is now reported only when the same line carries provider
   context (`inception`, `api_key`, `provider`, `inceptionlabs`). `inception` has no other
   meaning here and is always reported.

2. **JSON is scanned structurally, not line by line.** `config/api_model_roster.json` lists
   provider slugs as dict keys, but also carries an OpenRouter catalogue where
   `inception/mercury-2` is a model id served by a live aggregator. Text scanning flagged
   the catalogue. The guard now walks dict keys and provider-valued fields
   (`slug`, `provider`, `provider_name`, `key_env_hit`) and ignores model ids.

3. **File names are not provider settings.** `audit_dashboard/inception_paper_trading.html`
   is a deployed page whose name predates the retirement; it appears in three deploy lists
   inside `.github/workflows/audit-dashboard.yml`. A match whose enclosing token ends in a
   known file extension (`.html`, `.py`, `.json`, …) is skipped.

Underscores deliberately do **not** break a match — the most common regression shape is an
env-var name (`INCEPTION_API_KEY`, `MERCURY_API_KEY`) — while digits do, so `mercury2` is
never mistaken for a provider.

## How it was verified

`python3 -m py_compile` clean. Ten cases run against a synthetic repo (`/tmp/fakerepo`) so
the guard is proven to fire as well as to stay quiet:

| # | Input | Expected | Got |
|---|-------|----------|-----|
| 1 | clean config | 0 | 0 |
| 2 | `model: inception/mercury-2` | 1 | 1 |
| 3 | comment line mentioning inception | 0 | 0 |
| 4 | `name: "Mercury 2  Signal Scanner"` | 0 | 0 |
| 5 | `api_key: MERCURY_API_KEY` | 1 | 1 |
| 6 | `run: python -m mercury2` | 0 | 0 |
| 7 | JSON model id under `openrouter.models` | 0 | 0 |
| 8 | JSON `providers.inception` key | 1 | 1 |
| 9 | line with `RETIRED-PROVIDER-OK` | 0 | 0 |
| 10 | `"inception_paper_trading.html"` in a deploy list | 0 | 0 |

Against the live tree: `OK: no retired provider (inception) in 369 scoped file(s)`, rc=0 —
so the guard starts green and only fails on a real regression. `--list | head -3` exits 0
(broken pipe handled), and `--json` emits `clean`, `scanned_files`, `retired`, `hits`.

## Limits, stated plainly

- It scans a **fixed list**. A retired provider reintroduced in a file outside `SCOPED` is
  invisible to it. Add the path and a reason when a new config surface appears.
- It does not verify that the *replacement* (`cerebras`) is alive — that is
  `tools/verify_all_keys.py`'s job, which pings every provider.
- It says nothing about credentials. Revoking the Inception key at the vendor is an owner
  action; no script here can do it.
- `--json` reports an approximate line for structural hits (first occurrence of the quoted
  name), because JSON parsing does not retain offsets.

## Companion patches (not part of this branch)

Two defects relayed to the peer owner of `SWARM_CONSOLIDATED` / `.ruflo`, supplied as
patches in `/tmp` rather than commits, because those files are not mine to edit:

- `/tmp/patch_swarm_picker_help.diff` — `cli/swarm_picker.py --help` died with
  `EOFError: EOF when reading a line` (line 83): the script has no argument parsing, so
  `--help` falls straight through to `input()`. Patch adds a usage block, an early
  `-h/--help` return, and a non-TTY guard. Verified: `--help` rc=0 (18 lines),
  `/dev/null` stdin rc=0, `git apply --check` rc=0.
- `/tmp/patch_ruflo_template_yaml.diff` — `.ruflo/agents/TEMPLATE_agent.yaml` printed
  `unhashable type: 'dict'` on every ruflo run because `type: {agent_type}` is YAML
  flow-mapping syntax, so the loader keyed a dict and crashed. Five placeholders now
  quoted. Verified: all five fields parse as `str`, `git apply --check` rc=0.
