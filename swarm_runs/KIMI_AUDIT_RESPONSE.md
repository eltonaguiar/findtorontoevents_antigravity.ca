# Kimi Agent Swarm — Audit Response (2026-05-03)

External audit of our Claude-Code-driven swarm by Kimi Agent Swarm. Source materials in [`kimi_audit_2026_05_03/`](kimi_audit_2026_05_03/).

## Summary verdicts (13 pain points)

| # | Issue | Verdict | Confidence | Our action |
|---|-------|---------|------------|------------|
| 1 | API engines confabulate `gh` output | FIX_ADEQUATE | HIGH | shipped — keep |
| 2 | Claude Windows arg-length crash | FIX_ADEQUATE | HIGH | shipped — keep |
| 3 | Surrogate-escape stdin (cp1252) | FIX_ADEQUATE | HIGH | shipped — keep |
| 4 | Ollama wrap-replay corruption | FIX_ADEQUATE | MED | shipped — keep |
| 5 | Cursor agent WinError 206 | **FIX_INCOMPLETE** | HIGH | **OPEN** — unify under `_run_stdin_or_tempfile` helper |
| 6 | Codex usage-cap exhaustion | FIX_ADEQUATE | MED | KFM-doc'd; account-level |
| 7 | Engine self-spoofing | **FIX_INCOMPLETE** | HIGH | **OPEN** — `model_fingerprint` captured but not compared vs requested |
| 8 | freebuff TUI buffer clamp | **FIX_INCOMPLETE** | MED | **OPEN** — fileref mode untested end-to-end |
| 9 | Universal stdin-pipe fallback | **FIX_INCOMPLETE** | HIGH | **OPEN** — agent + openclaude lack temp-file fallback |
| 10 | Schema evidence minLength | FIX_ADEQUATE | HIGH | shipped — keep |
| 11 | Audit-trail completeness (imp-B) | FIX_ADEQUATE | HIGH | shipped — keep |
| 12 | Persona injection (imp-A) | FIX_ADEQUATE | MED | shipped — keep |
| 13 | Auto-disagreement resolver (imp-C) | **FIX_INCOMPLETE** | MED | **DEFERRED** — confidence-weighted voting + meta-engine arg-quality scoring |

## 5 issues we missed (Kimi caught)

| Rank | Severity | Issue |
|---|---|---|
| 1 | HIGH | **openrouter dead code** — wired but never live-smoked at audit time. *(Status now: PONG returned "Game!" via gpt-4o-mini; transport works. Still needs schema-validity smoke against full briefing.)* |
| 2 | HIGH | **swarm_inspect blind to per-engine subdir layout** — reports `engines=0 healthy=0 suspect=0` for `pr_review_<TS>/<engine>/` directory shape. No automated safety net. |
| 3 | MED | **deepseek ZOMBIE threshold too coarse** — 200B byte-count check passes empty JSON envelopes. Need schema-validity check, not byte count. |
| 4 | MED | **Duplicate comment-poster risk** — `safety.can_post(role)` checks role string but doesn't enforce *only one* comment-poster instance per run. |
| 5 | MED | **Emoji stripper destroys meaning** — `_pr_capture._ascii_safe` replaces 🟢🔴 with `?`, misrepresenting PR urgency in inline-diff prompts. |

## 3 architectural choices Kimi would undo

1. **PowerShell + Python hybrid dispatch → pure Python asyncio.** PS layer causes the per-engine subdir bug (#2 above), Windows encoding mismatches, and arg-length issues.
2. **6 ad-hoc prompt-delivery mechanisms → unified `_run_stdin_or_tempfile()` helper.** Each adapter shouldn't have bespoke delivery logic.
3. **Flat JSONL with no schema version → add `"v": "1"` to `_calls.jsonl` rows.** Future imp-C fields then don't break downstream parsers.

## Kimi feature to adopt

**Hierarchical 2-tier decomposition** — Tier-1 scoping agent → Tier-2 specialist workers. Benefits:
- Shrinks per-worker prompts (solves the 8KB/19KB ceiling for agent/openclaude — closes our open #5/#9).
- Reduces fabrication (workers see only relevant hunks instead of full 60KB diff).
- Enables persona-per-subtask (crypto-specialist gets only crypto files; ml-validation gets only test files; etc.).

## False-confidence claim Kimi caught

> *"schema_validate.py enforces evidence requirements for all concerns"*

**Wrong.** `schema_review.json:42-51` only enforces `evidence.minLength=10` for `severity: blocking|major`. A red-team agent can bypass the gate entirely by downgrading all fabrications to `severity: question`. Our doc misleads.

**Fix:** also require `evidence.minLength≥1` for `minor` and `question` severities, OR document the limitation clearly in METHODOLOGY.md.

## `_pr_capture.py` vs Kimi's `ai-swarm` approach

| Dimension | Our `_pr_capture.py` | Kimi's ai-swarm |
|---|---|---|
| Capture | PowerShell dispatch-time | Python in-process (not yet implemented) |
| Embedding | `{{PR_CAPTURE}}` placeholder in prompt template | Adapter pre-flight step |
| Pros | Works today; real `gh` output | Cross-platform; per-engine refresh |
| Cons | PS-specific; stale during long runs | Not yet built (theoretical) |
| Kimi verdict | **Keep, but Python-ify.** Move to a Python module importable by both `swarm_dispatch.ps1` AND `api_consult.py`. Add `--refresh-interval`. |

## Action queue (ranked by Kimi-flagged priority)

| Rank | Effort | Action | File pointers |
|---|---|---|---|
| 1 | M | Build unified `_run_stdin_or_tempfile()` helper; route all CLI engines (claude / agent / openclaude / kimi / codex / opencode / kilo) through it. Closes #5 + #9. | `tools/swarm/worker_runner.py` |
| 2 | S | Compare `model_fingerprint` (post-imp-B) vs the model the operator requested; flag mismatches as `MODEL_DOWNGRADED`. Closes #7. | `tools/swarm/swarm_inspect.py` + `swarm_log.py` |
| 3 | S | Fix swarm_inspect to recurse into per-engine subdir layout. Closes Kimi-missed-#2. | `tools/swarm/swarm_inspect.py::find_latest_run` |
| 4 | S | Replace ZOMBIE byte-count threshold with schema-validity check. Closes Kimi-missed-#3. | `tools/swarm/swarm_log.py::CallTimer.__exit__` |
| 5 | S | Preserve emoji in `_ascii_safe`; only strip non-renderable bytes (>U+10FFFF / unpaired surrogates). Closes Kimi-missed-#5. | `tools/swarm/_pr_capture.py` |
| 6 | S | Add `"v": "1"` to every `_calls.jsonl` row. Closes architectural-#3. | `tools/swarm/swarm_log.py` |
| 7 | M | Test freebuff fileref mode end-to-end with the asset-class brief. Closes #8. | `tools/swarm/pty_driver.py` |
| 8 | L | Build `tools/swarm/resolver.py` for auto-disagreement resolution (imp-C). Closes #13. | new file |
| 9 | L | Hierarchical Tier-1 → Tier-2 decomposition (Kimi-recommended feature). | new file + `worker_runner.py` |
| 10 | L | Migrate dispatch from PowerShell to pure Python asyncio. Closes architectural-#1. | new file replacing `swarm_dispatch.ps1` |

## Quick fixes (S effort, ~30 min total)

```bash
# Item 3 — fix per-engine subdir handling
# Item 4 — schema-validity check vs byte-count
# Item 5 — preserve emoji in _ascii_safe
# Item 6 — schema-version in JSONL
# Together: ~30 LOC across 3 files
```

## Confidence in Kimi's audit

HIGH — Kimi cited `schema_review.json:42-51` and `_pr_capture._ascii_safe` correctly (both verifiable in this commit). Their "openrouter dead code" claim was correct at audit-time; we've since smoke-tested live. The "schema_validate enforces all concerns" rebuttal is a real false-confidence catch that we now correct in METHODOLOGY.md.

## Next steps

- Operator decides which of the 10 action items to ship first.
- Subagent dispatch on items 3/4/5/6 (4 × S effort) ≈ 1 commit.
- Items 1/2/7 are the highest-leverage incomplete fixes — recommend dispatching a follow-up subagent to ship items 1+2 together.
- Items 8/9/10 are L-effort design work; need fresh design pass + operator sign-off.
