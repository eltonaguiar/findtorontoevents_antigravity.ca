# Hermes Agent — Observed Bugs + Fix Plan

**Agent:** claude-opus-4-7 (Claude Code, 1M context)
**Timestamp:** 2026-05-05T02:30Z
**Target:** [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) v0.12.0 (commit `8fabef9d` / `d35efb98`)
**Method:** Behavioral analysis from 5+ session pastes + Hermes's own first-party verification + repo source-listing via `gh api`

## Scope

Hermes Agent is a Nous Research multi-provider agent CLI. On the user's Windows + WSL setup it produced **zero usable output across 5+ sessions today** — broken tools, poisoned API state, context overflow, and one leaked GitHub PAT. This MD enumerates the bugs and proposes minimum-viable fixes.

**Three `swarm_runs/` directories observed on user's machine:**
- `C:\Windows\System32\swarm_runs` (Hermes WSL default — wrong, system path)
- `C:\findtorontoevents_antigravity.ca\swarm_runs` (this repo)
- `C:\fte-audit-chain-feedback-gpt55\swarm_runs` (sibling worktree)

The first one is a misconfiguration — Hermes is running from `C:\Windows\System32` because `cd /mnt/c/...` was failing and Hermes fell back to launching from its working directory. See Bug 7 below.

---

## Bug 1: Tool sandbox completely broken on Windows/WSL

### Symptom
- `terminal` returns `exit code 126` on every command
- `browser_navigate` fails with `WinError 193` (binary launch failure)
- `read C:\findtorontoevents_antigravity.ca\... [error]` — file reads all fail
- `write_file` silently fails (returns no error but doesn't write the file)
- `find` (search_files) errors — `ripgrep not installed`

### Likely root cause
Hermes runs in WSL (`zerou@Elton2026:/mnt/c/Users/zerou$`). When asked to read `C:\findtorontoevents_antigravity.ca\...`, the read_file tool either:
1. Tries the literal Windows path inside WSL (fails — WSL needs `/mnt/c/...`)
2. Tries to spawn a Windows binary that doesn't exist in WSL
3. Hits permission issues writing to a Windows path from WSL

`exit code 126` from `terminal` means "command found but not executable" — almost always a Windows-binary-from-Linux or missing exec bit.

`WinError 193` ("not a valid Win32 application") means Hermes is trying to launch a Windows .exe from a WSL Python that doesn't have the right wrapper.

### Files to inspect (in [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent))
- `tools/browser_tool.py` — 123KB, the browser launcher
- `tools/file_operations.py` — read/write logic
- `tools/code_execution_tool.py` — terminal command runner

### Fix
Add an OS-detection layer that translates Windows paths to WSL paths when running under WSL:

```python
import platform
import re

def normalize_path_for_wsl(p: str) -> str:
    """C:\\foo\\bar  ->  /mnt/c/foo/bar  when running in WSL."""
    if not p or "/" in p[:3]:  # already POSIX
        return p
    # Detect WSL by /proc/version or env
    is_wsl = "microsoft" in open("/proc/version").read().lower() if os.path.exists("/proc/version") else False
    if not is_wsl:
        return p
    m = re.match(r"^([A-Za-z]):[\\/](.*)$", p)
    if not m:
        return p
    drive, rest = m.group(1).lower(), m.group(2).replace("\\", "/")
    return f"/mnt/{drive}/{rest}"
```

Apply at the entry point of every file/terminal/browser tool. Add `wsl-detect` smoke test in CI.

For `browser_navigate`: launch Linux Chromium binary inside WSL instead of trying to invoke Windows Chrome. Or detect WSL and fall back to `wslview` for browser navigation.

For `ripgrep not installed`: bundle ripgrep in the install script or fall back to `grep -r`.

---

## Bug 2: Cerebras API breaks on `reasoning_content` field in chat history

### Symptom
After any reasoning model (DeepSeek-R1, Nous Hermes-3, qwen3-thinking) is used in a session, all subsequent Cerebras calls return:
```
HTTP 400: messages.2.assistant.reasoning_content: property unsupported
```

Hermes's auto-fallback then bounces to Tencent (`hy3-preview:free`) which often 401s, looking like Cerebras is "random".

### Root cause
Hermes stores assistant turns verbatim including the `reasoning_content` field that reasoning models emit. When sending the conversation to Cerebras (which doesn't support that field), the request 400s. Hermes does not strip the field before sending.

`/new` clears the history (works) but the user has to manually trigger it. `/reasoning none` doesn't help because past turns still contain the field.

### Files to inspect
- `agent/openrouter_adapter.py` (not in repo — likely lives in `agent/` under different name)
- `agent/anthropic_adapter.py` (84KB — adapter pattern)
- `agent/lmstudio_reasoning.py` (2KB — reasoning-specific handling)
- Provider routing logic (likely in `agent/` somewhere)

### Fix
Add per-provider message sanitization. Provider capability registry should know which fields each provider accepts:

```python
PROVIDER_ALLOWED_FIELDS = {
    "cerebras": {"role", "content", "name", "tool_calls", "tool_call_id"},
    "openrouter:anthropic/*": {"role", "content", "name", "tool_calls", "tool_call_id"},
    "openrouter:openai/*": {"role", "content", "name", "tool_calls", "tool_call_id", "function_call"},
    "openrouter:deepseek/*reasoner*": {"role", "content", "name", "tool_calls", "tool_call_id", "reasoning_content"},
    # ... per-model overrides
}

def sanitize_messages_for_provider(messages: list, provider: str, model: str) -> list:
    allowed = PROVIDER_ALLOWED_FIELDS.get(f"{provider}:{model}", PROVIDER_ALLOWED_FIELDS.get(provider, None))
    if allowed is None:
        return messages  # unknown provider — pass through, may 400
    return [{k: v for k, v in m.items() if k in allowed} for m in messages]
```

Call `sanitize_messages_for_provider` at the entry of every adapter's `chat_completion` method.

Bonus: warn when stripping reasoning_content so users know they're losing trace data on that hop.

---

## Bug 3: Context overflow because system+tools alone exceed model limit

### Symptom
After `/new` (empty user history), Cerebras `llama3.1-8b` 400s with:
```
context_length_exceeded: 17431 > 8192
```

User's input was 4 chars ("hey"). The 17,431 tokens is entirely Hermes's overhead: system prompt + 30 tools + 87 skills + manifests + routing metadata.

### Root cause
Hermes's "fully loaded agent" payload bundles **all** declared tools and skills regardless of the conversation's needs. With `llama3.1-8b`'s 8k cap, the agent literally can't say hello.

Hermes's UI shows "Context: 256,000 tokens" for the route but the underlying API enforces 8,192.

### Files to inspect
- `agent/context_engine.py` (probably exists — context-window manager)
- `agent/context_compressor.py` (66KB — compression logic, runs too late)
- Tool/skill bundling logic in `cli.py` or `agent/__init__.py`

### Fix
Three-layer approach:

1. **Per-model context awareness**: query the actual context limit for the chosen model from the provider (Cerebras returns it in `/v1/models`). Don't trust the hardcoded "256K" UI value.

2. **Lazy tool/skill bundling**: don't include tool definitions in the system prompt unless the user's intent matches. Cluster tools by category (`browser`, `git`, `file`, `code-execution`, etc.) and only ship the categories the model has used or the user has invoked.

3. **Hard preflight check**:
```python
def preflight_size_check(messages, provider, model, max_context):
    payload_tokens = estimate_tokens(messages, tools, skills)
    if payload_tokens > max_context * 0.85:  # 85% safety margin
        raise PayloadTooLargeError(
            f"Estimated {payload_tokens} tokens for {provider}:{model} "
            f"(cap {max_context}). Try a model with larger context, "
            f"or use --minimal-tools to drop browser/skills."
        )
```

Throw before calling the API instead of letting the provider 400.

Add `--profile minimal` / `--profile coding-only` / `--profile full` so users can pick.

---

## Bug 4: Multi-model swarm "60 models" is cosmetic — single model under labels

### Symptom (verified by Hermes itself this session)

Hermes's `multi-agent-swarm` skill explicitly recommends single-model swarms for 60+ agents. Quote from the skill (per Hermes's verification, not my own grep):

> "For swarms with 60+ models (10+ rounds × 6+ models per round): Use a single free model (e.g., `tencent/hy3-preview:free` via OpenRouter) for all agents to avoid rate limits and eliminate costs."

Labels like `Mercury-v1..v20`, `Grok-v1..v20`, `Claude-v1..v20` are cosmetic. All 60 calls hit the same model with different prompts. The user thinks they're getting cross-architecture consensus; they're getting one model with temperature variation.

Confirmed in repo files Hermes cited:
- `updates/index.html:179`
- `reports/session_log_2026_05_04_redacted.md:19486,19530`
- `reports/hermes_swarm_value_assessment_2026_05_04.md:46`

### Root cause
`multi-agent-swarm` skill has a single-model fast-path for cost reasons, but the *output labels* don't disclose this. The skill renders results as if they came from distinct models.

### Files to inspect
- `skills/<multi-agent-swarm>/SKILL.md` — the prompt template that names personas
- The swarm runner that fans out calls (likely under `tools/` or `skills/multi-agent-swarm/`)

### Fix
Two-part:

1. **Disclosure**: when running in single-model mode, label outputs as `Persona-1 (model=X)`, `Persona-2 (model=X)` ... so users see all 60 hit the same backend. Add a header to the consolidated output:
   ```
   ⚠️ All 60 agents ran on `tencent/hy3-preview:free`. Persona labels are
   prompt-only; cross-architecture consensus was NOT achieved.
   ```

2. **Optional real-multi-model mode**: `--mode true-multi-model` that distributes across actual distinct providers (cerebras + xai + deepseek + groq + openrouter), respecting per-provider rate limits. Slower and not free, but produces what the labels claim.

---

## Bug 5: Plaintext PAT leak in shell command output

### Symptom (observed twice this session)
When user told Hermes "use GH_AMPERE", Hermes pasted the literal token in plaintext into a curl command:
```
export GITHUB_TOKEN=github_pat_<82-char-token-REDACTED>; curl ...
```

That command then appeared in the user's terminal log → got pasted to other agents' chat → token burned. User had to rotate (`GH_AMPHERE_ORIG` → new `GH_AMPERE`).

### Root cause
Hermes resolved the env-var name `GH_AMPERE` to its value, then used `export VAR=<value>` literally in the shell command rather than relying on the env var staying set. The token then appears in the visible command line and any captured shell log.

### Files to inspect
- `tools/code_execution_tool.py` — terminal command runner
- Environment-variable resolution path (probably `tools/env_passthrough.py`)

### Fix
Three guards:

1. **Never inline secret values into shell commands**. If the env var is named `GH_AMPERE`, the shell command should be `curl -H "Authorization: token $GH_AMPERE" ...` and Hermes should `os.environ["GH_AMPERE"] = value` for the subprocess via `env=` kwarg, not via `export VAR=value;` in the command string.

2. **Secret-pattern redaction in displayed output**. Strip anything matching `github_pat_\w{82,}`, `sk-\w{20,}`, `gsk_\w{40,}`, `csk-\w{32,}`, etc. from the displayed command and from any saved log.

3. **Pre-execution warning**: if a command literal contains a string matching a secret pattern, refuse to display it and confirm with user first.

---

## Bug 6: Session compaction loop — "compressed 6 times — accuracy may degrade"

### Symptom
Long Hermes sessions show:
```
⚠️ Session compressed 2 times — accuracy may degrade. Consider /new to start fresh.
... (later) ...
⚠️ Session compressed 6 times — accuracy may degrade.
```

Hermes keeps summarizing then re-summarizing as context fills, losing fidelity each pass.

### Root cause
The compactor (`agent/context_compressor.py`, 66KB) is triggered by token-budget thresholds but doesn't have a "max compactions per session" cap. Each compaction re-summarizes the *previously compacted* summary, causing telephone-game drift.

### Fix
1. Cap at **2 compactions per session**. After cap, force a hard `/new` recommendation instead of degrading further.
2. After each compaction, write the full pre-compact transcript to disk (`session_<id>_pre_compact_<n>.json`) so users can resume from the un-degraded state.
3. Show compaction-fidelity-loss warning prominently, not as a passing tip.

---

## Bug 7: Working-directory drift — agent runs from `C:\Windows\System32`

### Symptom
User has 3 `swarm_runs/` directories:
- `C:\Windows\System32\swarm_runs` ← misplaced
- `C:\findtorontoevents_antigravity.ca\swarm_runs` ← intended
- `C:\fte-audit-chain-feedback-gpt55\swarm_runs` ← sibling worktree

Hermes splash shows `Directory: /mnt/c/Windows/System32` because the user launched `hermes` from that directory (default PowerShell pwd).

### Root cause
Hermes uses the *launch* directory as the project root unless told otherwise. There's no auto-detection of nearby `.git`, `package.json`, or project markers to find the actual repo.

### Fix
1. **Project-root auto-detect**: walk up from `pwd` looking for `.git/`, `pyproject.toml`, `package.json`, or `AGENTS.md`. Refuse to start if not found inside the user's home directory or a project root.
2. **Refuse to start in `/mnt/c/Windows/`, `/`, `/usr/`, `/etc/`** — clearly wrong locations.
3. **Show the resolved working dir in splash** with confirmation: `Working in: /mnt/c/findtorontoevents_antigravity.ca [Y/n]`.

---

## Bug 8: Provider fallback chain hides the real failure

### Symptom
A single Cerebras 400 cascades through:
```
zai-glm-4.7 → 400 reasoning_content
→ falls back to gpt-oss-120b → 400 same
→ falls back to qwen-3-235b → 400 same
→ falls back to claude-opus-4.7 (OpenRouter) → may 401
→ falls back to claude-sonnet-4.6 (Copilot) → may also fail
```

By the time the user sees the error, they've burned 5 model calls on a problem that was *the same root cause* (Bug 2's reasoning_content stripping).

### Fix
1. **Fail-fast on `wrong_api_format`**: don't retry the same payload on a different model if the error class is "your message is malformed". Surface immediately.
2. **Classify errors** (already partly in `agent/error_classifier.py` — 38KB):
   - `transport` (retry on next provider)
   - `rate_limit` (retry after backoff or next provider)
   - `wrong_api_format` (don't retry — fix payload)
   - `auth` (don't retry — surface to user)
   - `model_not_found` (mark model bad, retry)
3. **Show the chain** in error output so user knows what was attempted and why each failed.

---

## Bug 9: Skill memory grows but never compacts

### Symptom (Hermes self-reported)
> "memory store is limited to 8000 characters. Right now it's at ≈ 51% (about 4117 chars used)."

Hermes has a persistent memory store. It records facts across sessions. The store grows monotonically.

### Risk
Once full, useful memories will be evicted. There's no semantic deduplication or aging policy mentioned.

### Fix
1. **TTL** on memory entries (default 30 days; renew on access).
2. **Semantic dedup** before insert: if a new memory is >0.85 cosine to an existing one, merge instead of append.
3. **Tier**: short-term (last 30d), long-term (manually pinned), archive (compressed).

---

## Priority order for upstream PRs to NousResearch/hermes-agent

| # | Bug | Severity | Effort | Notes |
|---|---|---|---|---|
| 1 | **Bug 5** (PAT leak) | Critical | Low | Security; ship today |
| 2 | **Bug 2** (reasoning_content poisoning) | High | Low | Per-provider field allowlist, ~50 LOC |
| 3 | **Bug 1** (Windows/WSL path translation) | High | Med | Single helper + tool entry-point integration |
| 4 | **Bug 4** (multi-model swarm disclosure) | High | Low | Add disclaimer to consolidated output |
| 5 | **Bug 3** (preflight context check) | Med | Med | Token estimator + per-model lookup |
| 6 | **Bug 8** (fail-fast on format errors) | Med | Low | Extend `error_classifier.py` |
| 7 | **Bug 7** (project-root auto-detect) | Med | Low | Walk-up logic + refuse-list |
| 8 | **Bug 6** (compaction cap) | Low | Low | Counter + threshold |
| 9 | **Bug 9** (memory TTL) | Low | Med | Store schema migration |

## How to verify these against actual Hermes source

I have access to [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) via `gh api` but didn't fetch every file (each adapter is ~80KB). To validate this analysis, the next step is:

```bash
# Clone and grep for the actual implementations:
git clone https://github.com/NousResearch/hermes-agent.git ~/hermes-agent
cd ~/hermes-agent
grep -nE "reasoning_content|sanitize_messages|provider.*allowed_fields" agent/
grep -nE "exit.*126|browser_supervisor|win32" tools/
grep -nE "/mnt/c|wsl|microsoft" tools/ scripts/
grep -nE "compact|compression" agent/context_compressor.py | head
```

Each bug claim above should map to a concrete file:line. This MD is the planning artifact; the upstream PRs are the implementation.

## What I haven't claimed

- I did not verify in Hermes source whether `reasoning_content` stripping exists today. The behavioral evidence (consistent 400s post-reasoning-model use) suggests it doesn't, but there may be a partial implementation that fails for specific provider/model combos.
- I did not verify whether single-model swarm mode is *the only* mode. Hermes's own admission says it's the recommended pattern for 60+ agents; smaller swarms may legitimately use multiple models.
- The PAT leak fix proposal is conservative (always redact); a more nuanced version would only redact when commands cross security boundaries (network, log, file).

## Upstream-fix-already-exists status (verified via `gh search code` against NousResearch/hermes-agent)

After grep-verifying the upstream repo, **2 of the 3 critical bugs already have partial fixes** that the user's session couldn't reach:

| Bug | Upstream status | Evidence | Why it still failed in user's session |
|---|---|---|---|
| **5 (PAT redaction)** | ✅ FIXED | `agent/redact.py` — `_PREFIX_PATTERNS` includes `sk-*`, `ghp_*`, plus `HERMES_REDACT_SECRETS=true` env-var toggle (snapshotted at import time so LLM-generated `export` can't disable it). Called via `redact_sensitive_text` in `hermes_cli/debug.py`. | Redaction only applies to "upload-bound text" (debug uploads, telemetry) — **not to shell command display** in `tools/code_execution_tool.py`. The PAT was inlined into a `curl` command and shown in chat output, bypassing the redact layer. **Fix needed: apply `redact_sensitive_text(force=True)` to terminal command display before rendering, not only to upload paths.** |
| **2 (reasoning_content)** | ⚠️ PARTIAL | `agent/transports/chat_completions.py` — handles `reasoning_details` (OpenRouter unified format) and `reasoning_content` *inbound* preservation. `environments/agent_loop.py` — comment notes "Handles multiple provider formats: 1. message.reasoning_content field (some providers) 2. message.reasoning". | Code preserves the field on the way IN (fine) but does NOT strip it on the way OUT when targeting providers that don't accept it (Cerebras 8k models). **Fix needed: per-provider outbound message sanitizer before the API call.** |
| **1 (WSL path translation)** | ⚠️ PARTIAL | `hermes_constants.py` — `_wsl_detected: bool | None = None` cached flag exists. `ui-tui/src/lib/clipboard.ts` — `if (env.WSL_INTEROP) { attempts.push({cmd: 'powershell.exe', ...}) }` for clipboard. | WSL detection exists but **path translation isn't wired through the file/terminal/browser tools**. Symptom: `read C:\foo` failed even though `_wsl_detected` would be `True`. **Fix needed: every path-accepting tool should call `normalize_path_for_wsl(p)` using the existing flag.** |

**Verdict:** Hermes already started fixing the right things — architectural intent is correct. What's missing is **wiring the existing helpers into all the affected code paths**. Three targeted upstream PRs would close 3 of the 9 bugs:

1. `Apply redact.py to shell-command display` — call `redact_sensitive_text` in `tools/code_execution_tool.py`'s display path
2. `Strip reasoning_content per provider on outbound` — add capability registry + sanitizer in the adapter `chat_completion` entry
3. `Apply WSL path normalization to all tools` — single helper called at the entry of `tools/file_operations.py`, `tools/code_execution_tool.py`, `tools/browser_tool.py`

The remaining 6 bugs (3, 4, 6, 7, 8, 9) require new code, not just wiring.

## Post-fix validation steps

After landing fixes for any of the 9 bugs above, run the following sequence to confirm the fix and watch for regressions.

### Per-bug verification

| Bug | Validation command | Pass criteria |
|---|---|---|
| 1 (path translation) | `hermes -- read C:\\foo\\bar.txt` from WSL | File contents returned, no "exit 126" / WinError 193 |
| 2 (reasoning_content) | Use a reasoning model, then `/model cerebras:llama3.1-8b`, then "hi" | Response returned, no `wrong_api_format` 400 |
| 3 (preflight context) | `/model cerebras:llama3.1-8b` then "hi" with default agent profile | Either succeeds OR fails with friendly `PayloadTooLargeError` BEFORE hitting the API |
| 4 (swarm disclosure) | Run a 60-agent swarm with default settings | Output header explicitly says `⚠️ All N agents ran on <model>` |
| 5 (PAT leak) | `hermes` → "use GH_TOKEN to fetch X" | Command line shows `$GH_TOKEN` placeholder, never the literal value; no secret pattern in displayed output |
| 6 (compaction cap) | Long session → trigger 3rd compaction | Hermes refuses to compact a 3rd time, recommends `/new` |
| 7 (cwd auto-detect) | `cd C:\Windows\System32 && hermes` | Hermes refuses to start, prompts user to pick a project root |
| 8 (fail-fast) | Trigger a 400 wrong_api_format on cerebras | No fallback chain, immediate user-facing error |
| 9 (memory TTL) | Insert 10MB of fake memory entries, wait 31 days | Old entries auto-evicted, store stays under cap |

### Sample swarm run (Bug 4 + 8 cross-validation)

After Bug 4 disclosure fix lands AND Bug 8 fail-fast lands, this run should produce honest output:

```bash
# Setup: source the user-scope keys (Bash + PowerShell don't share Windows User env vars,
# observed in this session — workaround is `tmp/super_swarm/.envkeys`).
source tmp/super_swarm/.envkeys

# Single-model sanity (60 agents, all on hy3-preview):
hermes swarm run \
  --agents 60 \
  --model openrouter/tencent/hy3-preview:free \
  --rounds 10 \
  --personas-from skills/multi-agent-swarm/personas.yaml \
  --prompt "Review findtorontoevents.ca/audit and propose 3 P0 fixes" \
  --out swarm_runs/hermes_60_single_$(date -u +%Y%m%dT%H%M%SZ)/

# Expected output header (post-Bug-4 fix):
#   ⚠️ All 60 agents ran on `openrouter/tencent/hy3-preview:free`.
#   Persona labels (Mercury-1..20, Grok-1..20, Claude-1..20) are
#   prompt-only; cross-architecture consensus was NOT achieved.
#   For true multi-model run, use `--mode true-multi-model`.

# True-multi-model run (post-Bug-4 fix; uses cross-provider distinct architectures):
hermes swarm run \
  --mode true-multi-model \
  --providers cerebras,xai,deepseek,groq,openrouter \
  --models cerebras:gpt-oss-120b,xai:grok-code-fast-1,deepseek:deepseek-reasoner,groq:llama-3.3-70b-versatile,openrouter:anthropic/claude-sonnet-4.5 \
  --rounds 3 \
  --prompt "Review findtorontoevents.ca/audit and propose 3 P0 fixes" \
  --out swarm_runs/hermes_5x3_distinct_$(date -u +%Y%m%dT%H%M%SZ)/

# Expected behavior:
#   - 15 calls total (5 models × 3 rounds), each to a genuinely distinct architecture
#   - Per-call latency + cost shown in the per-model summary
#   - If any provider returns wrong_api_format (e.g. Cerebras + reasoning_content),
#     Bug 8's classifier surfaces it immediately instead of cascading
```

### Cross-engine cross-check using the brainstorm-review pattern

The `brainstorm_review_swarm.py` tool I built this session ([tools/brainstorm_review_swarm.py](tools/brainstorm_review_swarm.py)) demonstrates what Hermes's swarm should do natively. After the Hermes Bug 4 disclosure + Bug 2 reasoning_content stripping land, this should reproduce in Hermes:

```bash
# What we ran today (worked):
python tools/brainstorm_review_swarm.py tmp/some_prompt.md \
  --brainstorm cerebras:gpt-oss-120b,cerebras:llama3.1-8b,inception:mercury-2,xai:grok-code-fast-1,openrouter:openai/gpt-oss-20b:free \
  --reviewers deepseek:deepseek-reasoner,openrouter:openai/gpt-oss-120b:free

# Equivalent hermes invocation (post-fix):
hermes swarm review \
  --prompt-file tmp/some_prompt.md \
  --brainstorm-models cerebras:gpt-oss-120b,cerebras:llama3.1-8b,inception:mercury-2,xai:grok-code-fast-1,openrouter:openai/gpt-oss-20b:free \
  --review-models deepseek:deepseek-reasoner,openrouter:openai/gpt-oss-120b:free \
  --strip-reasoning-content-per-provider \
  --true-multi-model \
  --fail-fast wrong_api_format
```

### Regression watchlist

Add these to a Hermes upstream CI workflow:
- `tests/test_path_translation.py` — covers Windows ↔ WSL path normalization for read/write/exec/browser
- `tests/test_provider_message_sanitization.py` — for each provider × model, assert that disallowed fields are stripped
- `tests/test_secret_redaction.py` — assert `github_pat_*`, `sk-*`, `gsk_*`, `csk-*` patterns never appear in displayed command output
- `tests/test_swarm_disclosure.py` — assert output header names every distinct model that received traffic
- `tests/test_compaction_cap.py` — assert max 2 compactions per session
- `tests/test_cwd_refuse_list.py` — assert hermes refuses to start in `/`, `/usr`, `/etc`, `/mnt/c/Windows`

### Operational watchlist after landing fixes

- 24h after deploy: review error_classifier.py logs for new error categories that bypass the fast-fail
- 7d after deploy: sample 100 swarm runs, confirm output headers cite the actual models used
- 30d after deploy: confirm memory store stays under 8KB cap and TTL eviction works

## Related session work

- Session-wide observations: PAT rotation done by user (`GH_AMPERE` new, `GH_AMPHERE_ORIG` burned).
- Hermes self-verified Bug 4 in this session via `multi-agent-swarm` skill inspection + grep of repo files.
- Working alternatives observed on same machine: freebuff, GitHub Copilot, Cursor, opencode all functional. The bugs above are Hermes-specific config/architecture issues, not Windows-specific.
