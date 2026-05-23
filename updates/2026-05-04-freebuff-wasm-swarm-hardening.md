# Freebuff WASM Swarm Hardening (2026-05-04)

## What was broken
- `freebuff` intermittently failed with `tree-sitter.wasm not found`.
- Even after user-level env fixes, swarm executions could still fail if the launch environment did not inherit `CODEBUFF_TREE_SITTER_WASM_PATH`.

## What changed
- Updated `tools/swarm/pty_driver.py` to set a deterministic fallback for `CODEBUFF_TREE_SITTER_WASM_PATH` before spawning Freebuff.
- Fallback path used: `%USERPROFILE%\\.config\\manicode\\tree-sitter.wasm`.
- Behavior is conservative: existing valid env value is preserved; fallback is only applied when missing or invalid.

## Why this is safe for swarm
- Scope is process-local to the spawned PTY process.
- No global env mutation and no side effects on other engines.
- Keeps existing overrides intact when they already point to a valid file.

## Verification
- `python -c "import py_compile; py_compile.compile('tools/swarm/pty_driver.py', doraise=True)"` succeeded.
- `python tools/swarm/pty_driver.py --help` works (argument parser intact).
- CLI path resolution confirms swarm still targets `%APPDATA%\\npm\\freebuff.cmd`.

## Notes
- End-to-end PTY smoke requires `pywinpty` to be installed in the active Python environment.
