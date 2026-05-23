# HERMES_PATCH.MD — Local Hermes Agent Bug Patches

> **For any IDE agent (Claude, Codex, Cursor, Copilot, freebuff, opencode, etc.)
> seeing Hermes Agent misbehave on this machine or another:** the fix lives in
> this repo. Run the patcher; do NOT file PRs upstream to NousResearch.

## Quick start (90 seconds)

```bash
# In WSL (or any POSIX shell with python3 + access to ~/.hermes/):
python3 tools/patch_local_hermes.py             # apply patches
python3 tools/patch_local_hermes.py --check     # verify status
python3 tools/patch_local_hermes.py --revert    # roll back
```

Re-run after every `hermes update` (Hermes does `git pull` which overwrites
our patches).

## What's broken in stock Hermes Agent v0.12.0

| Bug | Symptom | Fix shipped here? |
|---|---|---|
| **5** | Tool-arg previews leak GitHub PATs / `sk-` keys verbatim into chat output and logs | ✅ patched |
| **4** | Multi-agent swarms claim N agents but use 1 model under cosmetic labels | ✅ logged for downstream detection |
| 1 | Windows ↔ WSL path translation broken in file/terminal/browser tools | ⏳ workaround in `.ruflo/orchestrator.py` |
| 2 | `reasoning_content` not stripped per provider; Cerebras 400s after any reasoning model | ⏳ documented, not patched |
| 3 | Static system+tools+skills payload exceeds 8k context on llama3.1-8b | ⏳ documented, not patched |
| 6 | Compaction loops degrade fidelity (no max-compaction cap) | ⏳ documented, not patched |
| 7 | Launches with wrong cwd (e.g. `/mnt/c/Windows/System32`) | ⏳ documented, not patched |
| 8 | Provider fallback chain hides real error class | ⏳ documented, not patched |
| 9 | Memory store grows unbounded (no TTL) | ⏳ documented, not patched |

**Patches 5 and 4 are the highest-impact and shipped.** The rest are documented
in [`updates/2026-05-05-hermes-agent-bug-analysis-claude-opus-4-7.md`](updates/2026-05-05-hermes-agent-bug-analysis-claude-opus-4-7.md)
with code-level fix proposals; add them to `tools/patch_local_hermes.py`'s
`PATCHES` list as needed.

## Why local-only (no upstream PRs)

User directive 2026-05-05: **stop filing PRs against `NousResearch/hermes-agent`.**
The one existing upstream PR (#20076 — Bug 5) stays open as a courtesy to other
Hermes users but no further upstream work happens.

Local patches are faster to ship, easier to verify, and don't depend on upstream
review cycles. Maintenance cost: re-run after each `hermes update`.

## How the patcher works

[`tools/patch_local_hermes.py`](tools/patch_local_hermes.py) edits files in
`~/.hermes/hermes-agent/` (or `$HERMES_DIR`) in-place:

1. **Anchor-insert**: finds a unique substring in the target file, inserts our
   code immediately after it
2. **Literal-replacement**: changes specific lines (e.g. `args_preview = str(tool_args)[:80]`
   becomes the redacted version)
3. **Marker comment**: every patch carries `# [LOCAL-PATCH-CLAUDE-OPUS-4-7 v1]`
   so re-runs detect "already patched" and skip
4. **`.orig` backup**: created on first apply, used by `--revert`

## Adding a new patch (for future agents)

Edit `tools/patch_local_hermes.py`:

1. Bump `MARKER` version (e.g. `v1` → `v2`) so already-patched files re-apply
2. Add a dict to `PATCHES`:
   ```python
   {
       "file": "tools/some_file.py",
       "id": "bug-N-short-description",
       "find_anchor": "unique substring in the target",
       "insert_after_anchor": f"\n{MARKER} bug-N-...\n<your code>",
       "replacements": [("find_str", "replace_str"), ...],
   }
   ```
3. Smoke test: `python3 tools/patch_local_hermes.py --check` (should show `unpatched`)
4. Apply: `python3 tools/patch_local_hermes.py`
5. Verify: `--check` again (should show `patched`)
6. Document the new bug + fix in this file's table above

## Recovering from a botched patch

```bash
python3 tools/patch_local_hermes.py --revert    # restore .orig backups
# OR nuke and reinstall:
rm -rf ~/.hermes/hermes-agent
hermes update                                    # re-clones from NousResearch
python3 tools/patch_local_hermes.py             # re-apply
```

## On a new machine

If you (a future agent) are reading this on a fresh box:

1. Confirm Hermes is installed: `which hermes` or check `~/.hermes/hermes-agent/`
2. `python3 tools/patch_local_hermes.py --check` — see what's patched
3. `python3 tools/patch_local_hermes.py` — apply
4. Restart any running Hermes session

If a *new* Hermes bug appears that isn't in the patch list, add it to the
patcher + this file, then commit both. Keep patches narrow and reversible.

## Cross-references

- **Detailed bug analysis** (root causes, file:line, fix proposals for all 9 bugs):
  [`updates/2026-05-05-hermes-agent-bug-analysis-claude-opus-4-7.md`](updates/2026-05-05-hermes-agent-bug-analysis-claude-opus-4-7.md)
- **Patcher source** (where to add new patches):
  [`tools/patch_local_hermes.py`](tools/patch_local_hermes.py)
- **Long-form patcher docs** (alternative entry-point with same content):
  [`tools/HERMES_LOCAL_PATCHES.md`](tools/HERMES_LOCAL_PATCHES.md)
- **Workaround orchestrator** (avoids Bug 1/4/7 by wrapping `hermes chat -q`
  with explicit cwd, paths, model per-call):
  [`.ruflo/orchestrator.py`](.ruflo/orchestrator.py)
- **Codebuff↔WSL bridge protocol** (how to trigger swarms from Windows):
  [`BUFFTOHERMES.MD`](BUFFTOHERMES.MD)
- **Upstream PR (Bug 5 only, do not extend)**:
  https://github.com/NousResearch/hermes-agent/pull/20076

## Verification log

Last verified working on `/home/zerou/.hermes/hermes-agent/` at commit
`601e5f1d5` on 2026-05-05:
- `--check` before: both bugs `unpatched`
- `apply`: `[X] bug-5-args-preview-redaction applied`, `[X] bug-4-single-model-swarm-disclosure applied`
- `--check` after: both `patched`
- Re-apply: both `skipped` (idempotency confirmed)
- `.orig` backups present at `tools/code_execution_tool.py.orig` + `tools/delegate_tool.py.orig`
