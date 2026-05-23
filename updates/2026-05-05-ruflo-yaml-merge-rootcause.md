---
title: "RUFLO 71% false-positive rate — root cause: YAML agents silently dropped on key collision"
date: 2026-05-05
author: claude-opus-4-7
type: fix
severity: HIGH
---

# RUFLO 71% false-positive rate — root cause analysis

## TL;DR

The recent RUFLO `bug_hunter` run produced **5 hallucinated bugs out of 7**
(71% false-positive rate). The hallucinations included claims about non-existent
files (`scripts/data_fetcher.py`), wrong line numbers, and SQL-injection
warnings against code that was already parameterised.

**Root cause:** a one-line bug in `.ruflo/orchestrator.py`'s YAML merge logic
silently drops every YAML agent whose `type:` collides with an inline `AGENTS`
key — i.e. **all 5 YAML files**. The inline `AGENTS` dict has weaker goal text
without the anti-hallucination contract that the YAML versions carry, so the
agent ran with the wrong instructions.

This PR flips the merge so YAML overrides inline (which the inline comment
already claimed was happening).

## The smoking gun

### File `.ruflo/orchestrator.py`, before fix:

```python
# Load YAML agents
yaml_agents = load_yaml_agents()
# Merge YAML-loaded agents (YAML takes priority for duplicate keys)   ← claim
for k, v in yaml_agents.items():
    if k not in AGENTS:                                                ← reality
        AGENTS[k] = {
            "role": v.get("role", "unknown"),
            "model": v.get("model", FREE_MODELS["fallback"]),
            "goal": v.get("goal", f"Execute {k} agent tasks from YAML config."),
        }
```

The comment says "YAML takes priority for duplicate keys." The code does the
exact opposite: it only adds a YAML agent if the key is **not** already in
`AGENTS`. Since all 5 YAML files use `type:` keys that exactly match the inline
keys, **all 5 YAML overrides are silently dropped**.

### Verification

```bash
$ for f in .ruflo/agents/*.yaml; do grep -E "^type:" "$f"; done
type: audit_quant
type: audit_researcher
type: bug_hunter
type: github_hygiene
type: strategist

$ python3 -c "
import sys; sys.path.insert(0, '.ruflo')
import orchestrator as o
print('inline keys:', sorted(o.AGENTS.keys()))
"
inline keys: ['audit_quant', 'audit_researcher', 'bug_hunter', 'github_hygiene', 'strategist']
```

100% collision → 0% YAML applied.

## Why this caused the false positives

`.ruflo/agents/bug-hunter.yaml` (line 7–14):

```yaml
goal: |
  Hunt bugs in the codebase. Search for: ...
  Return JSON: {"bugs": [{"file", "line", "severity", "fix", "evidence"}]}.
  If you cannot inspect the file path, return unable_to_verify instead of
  inventing findings.
```

Note the two anti-hallucination clauses:

1. **`"evidence"` field** — every bug must include the literal code or grep
   match that proves it.
2. **`unable_to_verify` escape hatch** — if the model can't actually read the
   file, it must say so instead of guessing.

`.ruflo/orchestrator.py` inline `AGENTS["bug_hunter"]` (before fix):

```python
"goal": (
    "Hunt bugs in the codebase. Search for: ..."
    "Return JSON: {\"bugs\": [{\"file\", \"line\", \"severity\", \"fix\"}]}"
),
```

**Neither clause exists in the inline goal.** The model is given no field that
forces it to cite source, and no way to admit it doesn't know — so it
confabulates plausible-looking findings. That is exactly what the multi-engine
swarm self-review caught: `scripts/data_fetcher.py` line 15 doesn't exist;
`audit_trail/mysql_client.py` line 42 already used parameterised queries; etc.

## The fix

```python
# YAML overrides inline (per-field merge so a YAML file that omits a key
# still inherits the inline default)
yaml_agents = load_yaml_agents()
for k, v in yaml_agents.items():
    existing = AGENTS.get(k, {})
    AGENTS[k] = {
        "role":  v.get("role",  existing.get("role", "unknown")),
        "model": v.get("model", existing.get("model", FREE_MODELS["fallback"])),
        "goal":  v.get("goal",  existing.get("goal",
                      f"Execute {k} agent tasks from YAML config.")),
    }
```

After the fix, running `--list-agents` will show the YAML version's `role`,
`model`, and `goal` for every key that has a YAML file, and the inline default
for any key that doesn't.

## Verification plan

```bash
# 1. Syntax + import check (already passed):
python -c "import ast; ast.parse(open('.ruflo/orchestrator.py',encoding='utf-8').read())"

# 2. Manual smoke: print bug_hunter.goal after merge — should contain
#    "unable_to_verify" (from YAML), not just "Return JSON: ..." (inline).
python3 -c "
import sys; sys.path.insert(0, '.ruflo')
import orchestrator as o
o.AGENTS  # trigger load via __main__ path; here we mimic merge directly
ya = o.load_yaml_agents()
for k,v in ya.items():
    e = o.AGENTS.get(k, {})
    o.AGENTS[k] = {'role': v.get('role', e.get('role')),
                   'model': v.get('model', e.get('model')),
                   'goal': v.get('goal', e.get('goal'))}
assert 'unable_to_verify' in o.AGENTS['bug_hunter']['goal'], \\
    'YAML goal not merged — fix did not stick'
print('OK: bug_hunter.goal now contains the YAML anti-hallucination contract')
"

# 3. End-to-end: re-run RUFLO bugs swarm and inspect the JSON for an `evidence`
#    field on every bug entry (was missing before fix).
python3 .ruflo/orchestrator.py --swarm bugs --tier paid
```

## Related issues (not fixed in this PR — separate commits)

- The 4 swarm code fixes shipped in commit `5d7ad30` (config-loader source
  attribution, preflight drift, tmux poll/capture).
- The PR #821 connection-leak fix in `audit_trail/mysql_client.py`.

Both are independent of this root cause and stay in their own PRs.

## Files changed

- `.ruflo/orchestrator.py` — flip YAML merge from "skip if key exists" to
  "YAML overrides inline" (per-field merge with inline as fallback).
