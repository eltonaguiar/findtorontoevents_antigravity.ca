# SWARM + RUFLO Complete Bug Report (2026-05-05)

**Scope:** `tools/swarm/`, `.ruflo/`, `audit_trail/mysql_client.py`
**Review sources:** Kimi Agent SWARM Code Review, Kimi Agent SWARM Tools Review,
  OpenCode Desktop session, Claude-opus-4-7 REVIEWFORBUFF.MD + REVIEWFORBUFF_V2.MD
**Bugs confirmed & fixed:** 8 (5 code bugs + 3 defensive improvements)
**Observations documented:** 3 (not fixed, low-priority)

---

## Bug 1 — `mysql_fetch_closed_non_crypto`: Double-return race condition (HIGH → CRITICAL)

**File:** `audit_trail/mysql_client.py` lines 717 + 790
**Severity:** CRITICAL (upgraded per REVIEWFORBUFF_V2.MD — race fires without exception trigger)
**Found by:** Kimi Agent (independent deep-dive missed by prior consensus swarm runs)

### What was broken

`_return_conn(conn)` was called immediately after `rows = cur.fetchall()` (line 717),
returning the connection to the pool while the function still held a reference.
If another concurrent thread called `_get_conn()` during the row-processing loop,
it could receive the **same physical pymysql.Connection object**. Both threads
would then share the connection, producing interleaved results or
`Commands out of sync` errors.

The race does **not** require an exception — it fires on the baseline success path.

### Fix applied

- Removed premature `_return_conn(conn)` after `fetchall()` — connection now
  returned only at the very end after all row processing completes (line 790).
- Added `conn = None` before the `try:` block (line 700) to prevent
  `UnboundLocalError` if `_get_conn()` itself raises — bonus catch from
  REVIEWFORBUFF.MD.

```python
# Before (race condition):
rows = cur.fetchall()
_return_conn(conn)          # ← conn back in pool; function still holds reference
# ... 70+ lines of row processing ...
_return_conn(conn)          # ← second return: same conn goes to queue twice

# After (safe):
conn = None  # init so except block's `if conn:` is safe even if _get_conn raises
try:
    conn = _get_conn()
    ...
    rows = cur.fetchall()
    # NOTE: do NOT return conn here — rows still being processed.
    picks = []
    for row in rows:
        # ... process all rows ...
    _return_conn(conn)      # ← only return after row loop complete
    conn = None
    return picks, meta
```

---

## Bug 2 — `_consensus_pick_exists`: Missing `conn = None` guard after success return (LOW)

**File:** `audit_trail/mysql_client.py` lines 494–496
**Severity:** LOW (latent hazard — no active trigger, but breaks if code is added after return)
**Found by:** Kimi Agent + verified by REVIEWFORBUFF.MD

### What was broken

After `_return_conn(conn)` on the success path, no `conn = None` guard was set.
If any code ran after the `return` statement (debug print, exception re-raise,
future extension), the except block's `conn.close()` would close an already-returned
connection.

### Fix applied

```python
_return_conn(conn)
conn = None  # prevent double-close if any code runs after return
return row is not None and row[0] > 0
```

---

## Bug 3 — `load_yaml_agents()`: No schema validation (MEDIUM)

**File:** `.ruflo/orchestrator.py` lines 292–320
**Severity:** MEDIUM
**Found by:** Kimi Agent; confirmed by REVIEWFORBUFF.MD

### What was broken

`yaml.safe_load(f)` was called with no subsequent type check. A YAML file whose
root is a list or scalar throws `AttributeError` on `data.get(...)` and gets
silently dropped. A file with an empty `goal:` produces a runtime agent that
wastes API calls on every invocation.

### Fix applied

```python
if not isinstance(data, dict):
    print(f[...]); continue
...
# Per-field validation — warn but load if key already in AGENTS
for k, v in yaml_agents.items():
    existing = _base.get(k, {})
    AGENTS[k] = {
        k2: v.get(k2) or existing.get(k2) or _defaults.get(k2)
        for k2 in _mandatory_fields
    }
    # Warn if role/goal missing (still load for robustness)
    if k not in existing and (not v.get('role') or not v.get('goal')):
        print(f[...]); warnings += 1
```

---

## Bug 4 — Orchestrator YAML merge: `copy.deepcopy` replaced with `dict(AGENTS)` (LOW)

**File:** `.ruflo/orchestrator.py` line 872
**Severity:** LOW (mild under importlib.reload / test isolation)
**Found by:** Kimi Agent; partially revised by REVIEWFORBUFF_V2.MD

### What was broken

`copy.deepcopy(AGENTS)` was used as the base for the YAML merge loop.
This was a style preference, not a correctness bug — but under
`importlib.reload()` or pytest test isolation, the mutations compound.

### Fix applied

Replaced `copy.deepcopy(AGENTS)` with `dict(AGENTS)` shallow copy.
Removed `import copy`. The shallow copy is sufficient because the merge
loop always assigns **new dicts** to `AGENTS[k]` (not `AGENTS[k].update(...)`).

---

## Bug 5 — `bug_hunter` goal: Malformed JSON example (MEDIUM)

**File:** `.ruflo/orchestrator.py` line 248
**Severity:** MEDIUM (increases chance bug_hunter emits invalid JSON)
**Found by:** OpenCode Desktop session

### What was broken

The `bug_hunter` agent's goal string contained a malformed JSON example:
```
Return JSON: {\"bugs\": [{\"file\", \"line\", \"severity\", \"fix\"}]}
```
The object keys were comma-separated instead of colon-separated.
A misleading example increases the chance the agent emits similarly malformed
JSON, triggering expensive fallback parsing in `worker_runner.py:_extract_json_object()`.

### Fix applied

```python
# Before:
\"Return JSON: {\\\"bugs\\\": [{\\\"file\\\", \\\"line\\\", \\\"severity\\\", \\\"fix\\\"}]}\"

# After:
\"Return JSON: {\\\"bugs\\\": [{\\\"file\\\": \\\"<path>\\\", \\\"line\\\": \\\"<num>\\\", \\\"severity\\\": \\\"<HIGH|MEDIUM|LOW>\\\", \\\"fix\\\": \\\"<description>\\\"}]}\"
```

---

## Bug 6 — `session_manager.py`: Undefined `get_connection` (HIGH)

**File:** `tools/swarm/session_manager.py` lines 47, 55, 117, 150, 189, 216
**Severity:** HIGH (NameError on first `new_session()` call — full crash)
**Found by:** OpenCode Desktop session; confirmed during actions_failure_review.md
  swarm test run

### What was broken

The function was defined as `_connect()` but all 8 internal call sites referenced
`get_connection()` — the function name was never aliased or renamed consistently.
First call to `new_session()` → `NameError: name 'get_connection' is not defined`.

### Fix applied

Renamed the function definition from `_connect` back to `get_connection`.
All 8 internal callers already used `get_connection` — no other changes needed.

```python
# Before:
def _connect(db_path: Path | str | None = None) -> sqlite3.Connection:

# After:
def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
```

---

## Bug 7 — `api_consult.py`: Empty `choices` IndexError risk (MEDIUM)

**File:** `tools/swarm/api_consult.py` lines 311, 344
**Severity:** MEDIUM (IndexError crash on malformed API response)
**Found by:** OpenCode Desktop session

### What was broken

```python
# If API returns `choices: []` or `choices: null`:
data.get('choices', [{}])[0]  # → IndexError: list index out of range
```

The default `[{}]` only applies when `choices` is missing (key not present),
not when it's an empty list.

### Fix applied

```python
# Before:
content = data.get('choices', [{}])[0].get('message', {}).get('content', '') or ''

# After:
choices = data.get('choices') or [{}]
content = choices[0].get('message', {}).get('content', '') or ''
```

---

## Bug 8 — `swarm_run.py`: `json_strict` bool logic reversed (MEDIUM)

**File:** `tools/swarm/swarm_run.py` line 642
**Severity:** MEDIUM (engine-level `json_strict: false` ignored; always uses fleet default)
**Found by:** OpenCode Desktop session

### What was broken

```python
per_strict = bool(em.get('json_strict')) or fleet_json_strict
```

`bool(False)` is `False`, so `False or fleet_json_strict` → `fleet_json_strict`.
The engine-level override for `json_strict: false` was always ignored;
`false or True` → `True`, `false or False` → `False` (works by accident).
`json_strict: true` worked correctly.

### Fix applied

```python
per_strict = em.get('json_strict') if 'json_strict' in em else fleet_json_strict
```

Now engine-level `json_strict: false` is respected (returns `False`),
and engine-level `json_strict: true` is respected (returns `True`).

---

## Bug 9 — `swarm_followup.py`: Stale `ALL_ENGINES` list (CRITICAL)

**File:** `tools/swarm/swarm_followup.py` lines 70–77
**Severity:** CRITICAL (agent validation fails for 14 missing engines)
**Found by:** OpenCode Desktop session; also confirmed by PR #822

### What was broken

`ALL_ENGINES` in `swarm_followup.py` was missing 14 engines present in
`swarm_run.py`'s list: `agent`, `kimi`, `openclaude`, `codex`, `ollama_local`,
`openrouter`, `nous`, `groq`, `huggingface`, `gemini_api`, `github_models`,
`pollinations`. Any agent using one of these engines would fail the
`engine in ALL_ENGINES` validation check.

### Fix applied

Updated `ALL_ENGINES` in `swarm_followup.py` to match `swarm_run.py` exactly,
adding all 14 missing engines.

---

## Bug 10 — `worker_runner.py`: Missing session context file cleanup (LOW)

**File:** `tools/swarm/worker_runner.py` end of `main()`
**Severity:** LOW (temp files accumulate in `swarm_runs/` over time)
**Found by:** OpenCode Desktop session

### What was broken

When `--from-session` is used, `worker_runner.py` creates temporary `_session_<id>_ctx.md`
files but never deletes them after the run completes. Over many runs, the
`swarm_runs/` directory accumulates orphaned context files.

### Fix applied

Added cleanup block at the end of `main()`:
```python
if args.from_session:
    for suffix in ('_ctx.md',):
        tmp_ctx = SWARM_DIR / f'_session_{args.from_session[:8]}{suffix}'
        try:
            if tmp_ctx.exists():
                tmp_ctx.unlink()
        except OSError:
            pass
```

---

## Bug 11 — `swarm_run.py`: Pre-flight API key check (DEFENSIVE)

**File:** `tools/swarm/swarm_run.py` after engine validation
**Severity:** INFORMATIONAL (prevents wasted time on guaranteed-to-fail engines)
**Found by:** REVIEWFORBUFF_V2.MD gap analysis; added during this review cycle

### What was added

Pre-flight check that skips engines in `api_engines` (deepseek, cerebras, xai,
inception, ollama_cloud, openrouter, nous) if no API key is present in the
environment. Evidence from `_calls.jsonl` shows these engines fail with
`no key in env` on every run, wasting 2–10s per attempt.

```python
api_engines = {'deepseek', 'cerebras', 'xai', 'inception',
               'ollama_cloud', 'openrouter', 'nous'}
for em in engines_meta:
    eng = em['name']
    if eng in api_engines:
        envs = ENGINE_KEY_ENVS.get(eng, ())
        if envs and not any(os.environ.get(k) for k in envs):
            skipped.append(eng)
            print(f'[swarm-run] SKIP {eng}: no API key in env...')
            continue
    kept_meta.append(em)
```

---

## Bug 12 — `worker_runner.py`: Empty-output retry on rc=0 (DEFENSIVE)

**File:** `tools/swarm/worker_runner.py` — `call_gemini`, `call_opencode_or_kilo`,
  `call_copilot`
**Severity:** INFORMATIONAL (fixes transient CLI init race causing silent failures)
**Found by:** REVIEWFORBUFF_V2.MD gap analysis

### What was added

Added retry-once for rc=0 empty output in three call functions:
- `call_gemini()` — Gemini CLI occasionally returns rc=0 with no output
- `call_opencode_or_kilo()` — kilo/opencode showed rc=0 with 0 bytes in
  `_calls.jsonl` on 2026-05-04 (evidence of CLI init race)
- `call_copilot()` — same pattern possible

```python
rc, out, err = _run(cmd, ...)
if rc == 0 and not out.strip():
    time.sleep(1)
    rc, out, err = _run(cmd, ...)  # retry once
```

---

## Observations (not fixed — low priority)

### Observation 1 — `verify_hermes()` unreachable `return False`

`.ruflo/orchestrator.py` lines 313–328: when `returncode != 0`, the function
falls through to the error print but returns `None` (truthy). The `return False`
on line ~328 is unreachable. Current behavior still works because `None` is
falsy in the `if not verify_hermes()` check. Fix is cosmetic/defensive.

### Observation 2 — `run_hermes_tmux()` always waits full timeout

`.ruflo/orchestrator.py` lines 426–484: uses `time.sleep(timeout)` to wait for
tmux session completion even if the agent finishes early. Not worth fixing —
tmux path is already a last-resort fallback.

### Observation 3 — `_extract_json_object()` may return None silently

`tools/swarm/worker_runner.py` lines 273–308: 4 fallback strategies; if all fail,
returns `None`. The caller handles this with a fallback envelope. Behavior is
defensive — a false negative (saying not JSON when it was) is better than a
false positive. No change needed.

---

## Deferred: `_consensus_pick_exists` + `mysql_fetch_closed_non_crypto` exception path — `conn.close()` vs `_return_conn`

The exception path in both functions uses `conn.close()` instead of `_return_conn(conn)`,
which is consistent with `is_healthy()`, `_execute_with_retry()`, and line 798
in `mysql_fetch_closed_non_crypto` itself. The `_get_conn()` self-heals by calling
`conn.ping(reconnect=True)` on retrieval, so returning a possibly-broken conn
to the pool is safe — the next consumer sanitises it.

**Recommendation:** Open a separate consistency-pass PR that decides the canonical
exception-path policy (`_return_conn` or `conn.close()`) and applies it to all
four call sites uniformly.

---

## Summary

| # | Severity | File | Bug | Status |
|---|----------|------|-----|--------|
| 1 | CRITICAL | mysql_client.py | Double-return race in mysql_fetch_closed_non_crypto | FIXED |
| 2 | LOW | mysql_client.py | Missing conn=None after _return_conn success | FIXED |
| 3 | MEDIUM | orchestrator.py | No YAML schema validation in load_yaml_agents | FIXED |
| 4 | LOW | orchestrator.py | copy.deepcopy → dict(AGENTS) shallow copy | FIXED |
| 5 | MEDIUM | orchestrator.py | Malformed JSON in bug_hunter goal | FIXED |
| 6 | HIGH | session_manager.py | Undefined get_connection (NameError on first call) | FIXED |
| 7 | MEDIUM | api_consult.py | Empty choices IndexError risk | FIXED |
| 8 | MEDIUM | swarm_run.py | json_strict bool logic reversed | FIXED |
| 9 | CRITICAL | swarm_followup.py | Stale ALL_ENGINES (14 engines missing) | FIXED |
| 10 | LOW | worker_runner.py | Missing session context file cleanup | FIXED |
| 11 | INFO | swarm_run.py | Pre-flight API key check (skip engines without keys) | ADDED |
| 12 | INFO | worker_runner.py | Empty-output retry on rc=0 for gemini/kilo/copilot | ADDED |
| O1 | INFO | orchestrator.py | verify_hermes unreachable return False | OBSERVATION |
| O2 | INFO | orchestrator.py | run_hermes_tmux waits full timeout | OBSERVATION |
| O3 | INFO | worker_runner.py | _extract_json_object may return None silently | OBSERVATION |
| D1 | — | mysql_client.py | conn.close() vs _return_conn exception path consistency | DEFERRED |

**PR #828:** `fix/kimi-swarm-ruflo-bugfixes-2026-05-05` → `main`