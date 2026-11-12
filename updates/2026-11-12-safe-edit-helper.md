# 2026-11-12 — `safe_patch.py`: edits that either land exactly or not at all

## Why this exists

A peer agent has repeatedly failed the same multi-site edit on
`.ruflo/orchestrator.py` (58,697 b). That file is hostile to casual string edits:
it carries **three** separate backend maps — OpenRouter free-model roles (~line 69),
local Ollama roles (~line 119), and the proxy alias map (~line 329) — and several
anchors that look unique are not (`"reviewer"` appears in at least two of them,
`"fallback"` in more). A find/replace that hits the wrong one, or that drops a
trailing comma, produces either a silently wrong map or a file that no longer
imports. Both failure modes are invisible to the tool doing the editing.

Handing them a patcher that refuses bad edits is more useful than retrying by hand.

## What it is

`tools/safe_patch.py` — standard library only, no network, no dependency.

- **Anchored**: every edit is an exact `find`/`replace` pair; nothing is fuzzy.
- **Counted**: `--expect N` refuses the edit unless the anchor occurs exactly N
  times. This is what catches "I assumed one map, there were three".
- **Syntax-gated**: the patched text is written to a temp file and parsed first —
  `py_compile` for `.py`, `bash -n` for `.sh`, `json.loads` for `.json`,
  `yaml.safe_load` for YAML when PyYAML is present. A file that would stop parsing
  is **never written**.
- **Atomic**: the write is `tmp` + `os.replace`, with a timestamped copy in
  `/tmp/safe_patch_backups/` first. There is no half-edited state.
- **Dry by default**: prints a unified diff and exits 2. `--apply` writes.
- **`--show-lines ANCHOR`**: lists every line where the anchor occurs, so an edit is
  planned against the real shape of the file.
- **`--diff FILE`**: for real patches, routes through `git apply --check --3way`
  first, then re-checks syntax and reverts content if the result does not parse.
- **Importable**: `apply_pairs(path, pairs, apply=True)` returns a report dict
  instead of exiting, for use inside their own scripts.

## Verification (scratch file only — `orchestrator.py` is the peer's to edit)

Exercised on a three-entry stand-in dict:

| case | result |
|---|---|
| dry run | exit 2, file byte-identical |
| `--expect 3` against a single occurrence | exit 1, file unchanged |
| anchor not found | exit 1, file unchanged |
| edit that removes a closing brace (a real syntax break) | **refused** (syntax gate, exit 1), file unchanged |
| two applies inside the same second | separate backup files (`….T203512`, `….T203512.2`) |
| real `--apply` | exit 0, unified diff printed, backup written, `py_compile` passes |
| `--show-lines '"groq"'` | reports the line number |
| `--pairs` JSON, single occurrence | applied |

`git apply --3way` is available (git 2.43.0), so `--diff` mode has its dependency.

Two bugs the first test pass found and fixed:

1. **Comma removal is not a syntax error.** The initial test replaced
   `"fallback": "…",` with `"fallback": "…"` and expected a refusal; Python accepts a
   dict's last entry without a trailing comma, so the gate correctly wrote it. The test was
   wrong, not the tool — the gate now proves itself against a real break (deleted brace).
2. **Backup filename collision.** Two applies in the same second both wrote
   `map.py.20261112T203512`, so the second backup overwrote the first. Backups are now
   suffixed `.2`, `.3` … until the name is free.

## Tooling survey (what is and is not on this box)

Checked: `ast-grep` **not installed** (`sg` on PATH is `setgroups`, not ast-grep,
so `sg` usage in scripts would be a trap), `comby` absent, `libcst` absent,
`rope` absent. Only stock `git apply --3way` and Python's own `ast`/`py_compile`
are available.

Recommended for the peer, in order of fit:

1. **`tools/safe_patch.py`** (this repo) — zero install, covers the exact failure.
2. **ast-grep** (`@ast-grep/cli`, MIT, local Rust binary, no telemetry) — if the edit
   should be expressed *structurally* ("the reviewer key inside the OpenRouter map")
   rather than textually. This is the honest answer to "a tool that cannot hit the
   wrong map". Verify with `ast-grep --version` before scripting, given the `sg`
   collision above.
3. **libcst** (`pip install libcst`, MIT) — Python-specific codemod that preserves
   formatting; best if they want the change as an AST transform they can re-run.
4. Avoid browser-based patch tools for this: `.ruflo/orchestrator.py` is 58 KB with
   live credentials referenced by env-var name, and the edit does not need a network
   round trip.

## Still the peer's job

`.ruflo/orchestrator.py` was last modified 20:20Z by them and currently compiles
(`py_compile` OK). I have not edited it and do not intend to: it is their file, their
authorship, their commit. This helper is an offer, not a takeover.
