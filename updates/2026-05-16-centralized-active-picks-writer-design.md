# Design: Centralized active_picks.json Writer

**Status:** Design doc — implementation pending operator review  
**Priority:** P1 (follow-up to P0 blocked-symbol leak fix)  
**Source:** Cerebras multi-model consultation 2026-05-16

---

## Problem

`active_picks.json` is written by 11+ independent emitter files without a shared gate or lock. Current fixes (PR #1106) add filtering to `forward_validator.py::save_active_picks()`, but 10 other emitters still bypass it.

---

## Recommended Architecture

### 1. Single write API

Create `audit_trail/active_picks_writer.py` with:

```python
def write_active_picks(picks: List[Dict], path: str = ..., emitter: str = "unknown") -> None:
    # 1. Apply BLOCKED_SYMBOLS filter (with UEPS data-quality exemption)
    # 2. Apply schema validation
    # 3. Acquire file lock
    # 4. Write to temp file
    # 5. Atomic rename
    # 6. Log count + filtered count
```

### 2. Migration

Replace all direct JSON writes in the 11 emitter files with calls to `write_active_picks()`.

### 3. Enforcement

Add a CI lint rule that bans `json.dump` or `open(.*active_picks` outside of `active_picks_writer.py`.

---

## Why This Beats the Current Patch

| Concern | PR #1106 (3-part) | Centralized Writer |
|---------|-------------------|-------------------|
| Race conditions | Possible (concurrent unfiltered writes) | Eliminated (lock + atomic rename) |
| Future leaks | Likely (new emitters forget to filter) | Impossible (all go through one gate) |
| Maintenance | 2+ files to update per symbol change | 1 file |
| Kill-switch | Only covers `passes_active_gate()` path | Covers ALL paths |

---

## Immediate Next Step

Create `audit_trail/active_picks_writer.py` and migrate `forward_validator.py` first. Then migrate emitters one-by-one in follow-up PRs.
