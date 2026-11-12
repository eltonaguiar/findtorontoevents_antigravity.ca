# ast_reviewer_codemod.py — structural editing for a file with three look-alike maps

**Date:** 2026-11-12
**Tool:** `tools/ast_reviewer_codemod.py` (new)
**Depends on:** ast-grep 0.51.2, installed user-local at `~/.local/ast-grep`

## What was broken

`.ruflo/orchestrator.py` carries the same role keys in three different dicts:

| Line | Dict | Entry | Meaning |
|---|---|---|---|
| 71 | `FREE_MODELS` | `"reviewer": "nvidia/nemotron-3-super-120b-a12b:free"` | OpenRouter pool |
| 119 | `LOCAL_MODELS` | `"reviewer": "llama3.2:3b"` | local Ollama pool |
| 329 | `role_map` | `"reviewer": "groq"` | LiteLLM proxy alias |

A peer agent failed this edit repeatedly. The cause is not carelessness: a textual
find/replace for `"reviewer"` matches all three, and the entries differ in quoting
and whitespace, so "replace the reviewer line" has no unique meaning. Worse, the
failure is silent — the file still imports, and the wrong pool quietly serves a
different model.

## What was added

`tools/ast_reviewer_codemod.py` selects the entry by **AST position**, not by text,
so "the reviewer entry in the OpenRouter map" is finally expressible:

```bash
# where does the key actually live? (no writes, no --value needed)
python3 tools/ast_reviewer_codemod.py .ruflo/orchestrator.py --key reviewer

# change only the OpenRouter one (dry run prints a diff, exit 2)
python3 tools/ast_reviewer_codemod.py .ruflo/orchestrator.py \
    --dict FREE_MODELS --key reviewer --value 'vendor/model:free'

# ...and --apply to write
```

Safety properties, all enforced in code:

- refuses unless exactly `--expect N` (default 1) matching pairs sit inside the named dict;
- parses the patched text (`ast.parse`) **before** writing anything;
- writes atomically, with a timestamped backup in `/tmp/safe_patch_backups/`;
- after writing, re-checks that every non-target entry is still byte-identical;
- default is a dry run that exits 2 when it produced a diff.

## Three bugs found while building it (all fixed, all covered by the checks below)

1. **A dict entry is not an expression.** `ast-grep run --pattern '"reviewer": $V'`
   fails with *"Multiple AST nodes are detected"* — a `key: value` entry is a `pair`
   node. Pairs must go through `ast-grep scan --rule` with `kind: pair` and a
   `field: key` regex; `run --pattern` only accepts expressions/statements.
2. **ast-grep offsets are UTF-8 byte offsets.** Slicing a Python `str` with them
   corrupts this file, which is full of multi-byte box-drawing characters. The
   first version landed the replacement inside `PAID_MODELS`; the syntax gate
   refused to write, which is the correct failure. Fixed by splicing `bytes`.
3. **`$NAME = { $$$BODY }` also matches set literals** (e.g. `BUILT_IN_KEYS` at
   line 1243). Requiring at least one `key: value` pair — `$NAME = {$K: $V, $$$REST}`
   — excludes sets.

Also worth recording: the `sg` shim shipped in the same npm package is broken on
this box (`Error: Os { code: 2, kind: NotFound }` in 0 ms), on top of the pre-existing
trap that bare `sg` is `setgroups(1)`. Always call `ast-grep` by its full name.

## Verification (scratch copy of the live file; the live file was never written to)

| # | Check | Result |
|---|---|---|
| T1 | report mode, `--key reviewer` | 3 matches attributed: line 71 `FREE_MODELS`, 119 `LOCAL_MODELS`, 329 `role_map`; rc=0 |
| T2 | dry run against `FREE_MODELS` | correct one-line diff, rc=2, file byte-identical afterwards |
| T3 | `--apply` | rc=0, backup `orch_copy.py.20261112T212525` written |
| T4 | diff vs original | exactly one line changed (line 71) |
| T5 | other two maps | lines 119 and 329 unchanged; patched copy compiles; `ast.dump` comparison confirms the only structural difference is that value |
| T6 | nonexistent dict | refused, rc=1 |
| T7 | ambiguous key (`AGENTS`, key `role`, 2 hits) | refused, rc=1 |
| T8 | value already present | no-op, rc=0 |
| T9 | live `.ruflo/orchestrator.py` | untouched, still compiles |

## Scope limits

- Rewrites string values of quoted keys only (not bare identifiers, not f-strings).
- One target dict per invocation; `--expect N` allows a deliberate multi-edit.
- Does not touch the live `orchestrator.py` — that file belongs to the peer agent,
  and this tool is an offer, not a takeover.
