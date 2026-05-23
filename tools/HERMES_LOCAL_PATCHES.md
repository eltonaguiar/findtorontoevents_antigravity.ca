# Hermes Agent — Local Patches

> **For future IDE agents on a new machine:** if you're seeing Hermes Agent
> bugs (PAT leaks in shell command previews, "60 models" that's actually
> 1 model, broken WSL paths, broken cwd), read this file. The fix lives
> at [`tools/patch_local_hermes.py`](patch_local_hermes.py) and you re-apply
> it after every `hermes update`.

## TL;DR

```bash
# From WSL (or any POSIX shell with python3 + access to ~/.hermes/):
python3 tools/patch_local_hermes.py             # apply
python3 tools/patch_local_hermes.py --check     # status
python3 tools/patch_local_hermes.py --revert    # roll back from .orig backups
```

Run after every `hermes update` to re-apply (Hermes runs `git pull` on its
checkout at `~/.hermes/hermes-agent/` which overwrites our patches).

## Why this exists

Hermes Agent (NousResearch/hermes-agent) ships with bugs we observed in
production this week. Detailed analysis is at
[`updates/2026-05-05-hermes-agent-bug-analysis-claude-opus-4-7.md`](../updates/2026-05-05-hermes-agent-bug-analysis-claude-opus-4-7.md).

We have one upstream PR open (NousResearch/hermes-agent#20076 — Bug 5 PAT
redaction) but we don't want to wait for it to merge, and we don't want to
file more upstream PRs. Instead we patch the local install in-place and
re-apply after each update.

## What gets patched

| Bug | File | Effect |
|---|---|---|
| **Bug 5** | `~/.hermes/hermes-agent/tools/code_execution_tool.py` | Wraps `args_preview` in `redact_sensitive_text(force=True)` so GitHub PATs / `sk-` keys / etc. in shell commands don't leak into displayed previews and tool-call logs. |
| **Bug 4** | `~/.hermes/hermes-agent/tools/delegate_tool.py` | Adds a `LOCAL_PATCH_DELEGATE_MODEL=...` log line on every subagent spawn so a downstream summarizer can detect when "N agents" are all the same model. |

Patches are marked with `# [LOCAL-PATCH-CLAUDE-OPUS-4-7 v1]` so re-runs
detect "already patched" and skip.

## Idempotency contract

- Re-running `python3 tools/patch_local_hermes.py` on already-patched files
  reports `[skipped]` and changes nothing.
- `--revert` restores from the `.orig` backups created on first patch.
- After `hermes update` (which `git pull`s the upstream main and overwrites
  our patches), re-run the patcher; it'll detect the unpatched state and
  re-apply.

## Adding a new patch

Edit `tools/patch_local_hermes.py`:

1. Bump the marker version in `MARKER` (e.g. `v1` → `v2`) so re-runs re-apply.
2. Add a new dict to `PATCHES` with:
   - `file`: path relative to `HERMES_DIR`
   - `id`: short stable identifier
   - `find_anchor`: a unique substring in the target file (used for insertion)
   - `insert_after_anchor`: code to insert (must include the marker)
   - `replacements`: list of `(find, replace)` pairs for direct substitution
3. Run `--check` to confirm the file detects as `unpatched`.
4. Run without flags to apply.
5. Document the bug + fix in this file.

## Recovering from a botched patch

```bash
# Roll back all patches:
python3 tools/patch_local_hermes.py --revert

# Or nuke the install and re-update:
rm -rf ~/.hermes/hermes-agent
hermes update     # re-clones from NousResearch
python3 tools/patch_local_hermes.py    # re-apply
```

## Why we don't keep filing upstream PRs

User directive (2026-05-05): keep the existing PR #20076 open as a courtesy
to other Hermes users but stop filing new ones. Local patches are faster to
ship, easier to verify, and don't require waiting for an upstream review
cycle. The maintenance cost (re-running after each `hermes update`) is
acceptable for a single-developer install.

## Cross-references

- Full bug analysis: [`updates/2026-05-05-hermes-agent-bug-analysis-claude-opus-4-7.md`](../updates/2026-05-05-hermes-agent-bug-analysis-claude-opus-4-7.md)
- Upstream PR (Bug 5 only): https://github.com/NousResearch/hermes-agent/pull/20076
- Companion swarm orchestrator (workarounds at the wrapper layer): [`.ruflo/orchestrator.py`](../.ruflo/orchestrator.py)
- Freebuff's Hermes review + ruflo bridge protocol: [`BUFFTOHERMES.MD`](../BUFFTOHERMES.MD)

## On a new machine

If you (a future agent) are reading this on a fresh machine and Hermes is
behaving badly:

1. Confirm Hermes is installed: `which hermes` or check `~/.hermes/hermes-agent/`
2. Run `python3 tools/patch_local_hermes.py --check` — see what's patched
3. Run `python3 tools/patch_local_hermes.py` — apply
4. Restart the Hermes session
5. If a *new* bug appears that isn't in the patch list, add it to this file +
   patcher, then commit both. Keep the patches narrow and reversible.
