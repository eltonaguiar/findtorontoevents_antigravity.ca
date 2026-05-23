# Ruflo CLI Parity Fixes — Evidence & Methodology

**Date:** 2026-05-05  
**Branch:** `fix/ruflo-cli-parity-2026-05-05`  
**Files changed:** `.ruflo/orchestrator.py`, `.ruflo/wizard.py`  

---

## Issues Found

### 1. Documentation-Code Mismatch (CRITICAL)

**What was broken:**  
The documentation (`RUFLO_SWARM_GUIDE.MD`, `BUFFTOHERMES.MD`, `HERMESTOFREEBUFF.MD`), slash commands (`.claude/commands/swarm-ruflo.md`), and the interactive wizard (`.ruflo/wizard.py`) all described CLI flags that **did not exist** in `.ruflo/orchestrator.py`:

- `--tier free|paid|hybrid` — referenced everywhere, not implemented
- `--check-keys` — referenced in `swarm-ruflo.md` and `swarm-ruflo-help.md`
- `--swarm all` — referenced in `wizard.py` and `RUFLO_SWARM_GUIDE.MD`

**Evidence:**
- `RUFLO_SWARM_GUIDE.MD` line 93: `python3 .ruflo/orchestrator.py --swarm all`
- `RUFLO_SWARM_GUIDE.MD` lines 96-98: `--tier free`, `--tier paid`, `--tier hybrid`
- `RUFLO_SWARM_GUIDE.MD` line 104: `--check-keys`
- `.claude/commands/swarm-ruflo.md` line 17: `python3 .ruflo/orchestrator.py --check-keys`
- `.ruflo/wizard.py` line 130: generates `python3 .ruflo/orchestrator.py --swarm audit --tier free`

Running any of these commands before this fix produced:
```
usage: orchestrator.py [-h] [--swarm {audit,github,strategy,bugs}] ...
orchestrator.py: error: argument --swarm: invalid choice: 'all' (choose from 'audit', 'github', 'strategy', 'bugs')
```

---

### 2. `wizard.py` Hardcoded REPO_ROOT (MEDIUM)

**What was broken:**  
Same issue as `orchestrator.py` — hardcoded to `/mnt/c/findtorontoevents_antigravity.ca`.

**Fix applied:** Replaced with `Path(__file__).resolve().parent.parent`.

---

## Fixes Applied

### `--tier` Implementation

Added three tier modes to `orchestrator.py`:

- **`free`** (default): Current behavior — `hermes chat -q` with OpenRouter free models.
- **`paid`**: Bypasses Hermes entirely. Calls `tools/swarm/api_consult.py --provider <provider> -` directly with the agent's goal as stdin. Maps roles to providers:
  - researcher → cerebras
  - coder → deepseek
  - reviewer → inception
  - architect/security-architect/coordinator → xai
  - fallback → openrouter
- **`hybrid`**: Tries `paid` first. If the API call fails (missing key, timeout, empty output), prints a warning and falls back to `free` automatically.

### `--check-keys` Implementation

Added `check_paid_keys()` and `print_key_status()` functions. Iterates over `PAID_KEY_ENVS` (mirroring `tools/swarm/config_loader.py`) and prints a ✅/❌ table.

### `--swarm all` Implementation

Added `"all"` as a valid choice for `--swarm`. Runs audit → github → strategy → bugs sequentially, then compiles insights (same as one cycle of `--continuous` without the sleep loop).

### Thread Safety in Parallel Audit (bonus)

While editing `run_swarm_audit()`, added `threading.Lock()` around the shared `results` dict when running in parallel (both tmux and paid tiers use threads).

---

## Methodology

1. **Cross-reference audit:** Read `RUFLO_SWARM_GUIDE.MD`, `BUFFTOHERMES.MD`, `HERMESTOFREEBUFF.MD`, `.claude/commands/swarm-ruflo.md`, and `.ruflo/wizard.py`. Extracted every CLI flag referenced.
2. **Code comparison:** Compared extracted flags against `orchestrator.py`'s `argparse` definition. Found 3 missing flags and 1 invalid choice.
3. **Implementation:** Added the missing functionality with minimal changes to existing code paths. The `paid` tier reuses the same prompt construction as the free tier, just routed through `api_consult.py` instead of `hermes chat`.
4. **Verification:**
   - `python3 -c "import py_compile; py_compile.compile('.ruflo/orchestrator.py', doraise=True)"` ✓
   - `python3 -c "import py_compile; py_compile.compile('.ruflo/wizard.py', doraise=True)"` ✓
   - `python3 .ruflo/orchestrator.py --check-keys` prints expected table
   - `python3 .ruflo/orchestrator.py --help` shows new flags

---

## Regression Risk

- **Low.** The default tier is `free`, which preserves 100% of existing behavior. `--check-keys` and `--swarm all` are purely additive. The `paid`/`hybrid` paths only activate when explicitly requested.
