# Kimi SWARM + RUFLO Code Review — Bug Fixes (2026-05-05)

**Review scope:** tools/swarm/, .ruflo/, audit_trail/mysql_client.py
**Root cause analysis:** Multi-engine audit (Copilot, OpenCode, Kilo, Kimi) + Claude-opus-4-7 review
**Bugs confirmed & fixed:** 4 (per REVIEWFORBUFF.MD verdict)
**Evidence:** REVIEWFORBUFF.MD (Claude-opus-4-7 review of Kimi's deliverables)

---

## Bug 1 — mysql_fetch_closed_non_crypto: Double-return race condition (HIGH)

**File:** audit_trail/mysql_client.py
**Reviewed by:** Claude-opus-4-7 (Ship #1)
**What was broken:**
cur.fetchall() materialises rows into a Python list, but _return_conn(conn) was
called immediately after — returning the connection to the pool while the function
still held it. If any exception occurred in the row-processing for-loop, the except
block's conn.close() could close a connection now owned by another concurrent
caller (race condition). No blast radius without special trigger — regraded HIGH.

**Fix applied:**
- Removed premature _return_conn(conn) after fetchall() — conn now returned only
  at the very end after all row processing completes.
- Added conn = None before try: block to prevent UnboundLocalError if
  _get_conn() itself raises (bonus bug from Claude's review).

---

## Bug 2 — _consensus_pick_exists: except block style (SKIP — not a bug)

**File:** audit_trail/mysql_client.py
**Reviewed by:** Claude-opus-4-7 (Skip #2)
**Verdict:** Per review, _return_conn(conn) in the except block was a style
preference, not a bug. The codebase is consistent with conn.close() for
exception paths (is_healthy, _execute_with_retry). Reverted to conn.close().

---

## Bug 3 — _consensus_pick_exists: conn=None after success (Ship #3)

**File:** audit_trail/mysql_client.py
**Reviewed by:** Claude-opus-4-7 (Ship #3)
**Fix:** Belt-and-suspenders conn = None after _return_conn on the success path.

---

## Bug 4 — orchestrator load_yaml_agents: validate YAML schema (MEDIUM)

**File:** .ruflo/orchestrator.py
**Reviewed by:** Claude-opus-4-7 (Ship #4, confirmed correct)
**Fix:** isinstance(data, dict) check + role/goal validation with warn-but-load
when key already in AGENTS (preserve original behavior).

---

## Bug 5 — orchestrator: copy.deepcopy vs dict(AGENTS) (SKIP — misunderstanding)

**File:** .ruflo/orchestrator.py
**Reviewed by:** Claude-opus-4-7 (Skip #5)
**Verdict:** deepcopy was based on misunderstanding of Python import semantics.
load_yaml_agents() only runs inside if __name__ == "__main__":, not on import.
Replaced with dict(AGENTS) shallow copy.

---

## Summary Table

| # | Severity | File | What | Status |
|---|----------|------|------|--------|
| 1 | HIGH | mysql_client.py | Double-return race in mysql_fetch_closed_non_crypto | FIXED |
| 2 | LOW | mysql_client.py | _consensus_pick_exists except block style | FIXED (conn.close) |
| 3 | LOW | mysql_client.py | conn=None belt-and-suspenders after _return_conn | FIXED |
| 4 | MEDIUM | orchestrator.py | YAML schema validation in load_yaml_agents | FIXED |
| 5 | LOW | orchestrator.py | copy.deepcopy vs dict(AGENTS) | FIXED (shallow copy) |

PR #828: fix/kimi-swarm-ruflo-bugfixes-2026-05-05
