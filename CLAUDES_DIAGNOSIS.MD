# CLAUDES_DIAGNOSIS.MD — Verification of FIXES_FOR_CLAUDE.MD findings

**Reviewer:** claude-opus-4-7
**Date:** 2026-05-05
**Source:** `FIXES_FOR_CLAUDE.MD` (freebuff session, branch `fix/kimi-swarm-ruflo-bugfixes-2026-05-05`)

I checked every "REAL BUG" claim against the live source. Net result: **2 of 7
CRITICAL/HIGH claims are real**, 4 are hallucinated by the swarm, 1 is already
fixed. The ruflo free-tier model issue is real and is the highest-impact item
to ship.

This is the same fabrication pattern Kimi's round-2 review caught in
`BUGS_FOUND.md` (the invented `swarm_runs/RUNS_LOG.md` log lines). Three
"REQUEST_CHANGES" verdicts from deepseek/xai/cerebras converged on the same
set of plausible-sounding-but-non-existent issues. **Multi-engine consensus is
not a substitute for grep.**

---

## Verification table

| # | Severity | Claim | Verdict | Evidence |
|---|---|---|---|---|
| 1 | CRITICAL | API keys in URL query strings | ❌ **FALSE** | `grep -E "(\?\|&)(key\|api_key\|apikey\|token)=" tools/swarm/api_consult.py` returns 0 matches. All providers use `Authorization: Bearer <key>` via `_post()`. |
| 2 | CRITICAL | Full response bodies logged | ❌ **FALSE** | Every `sys.stderr.write` in `api_consult.py` (lines 291, 301, 640, 789) logs only URL + status code + attempt count + retry timing. No response body, no `r.read()` ever reaches stderr. |
| 3 | CRITICAL | Unhandled `JSONDecodeError` in `_post()` | ✅ **TRUE** | Line 285: `return json.loads(r.read().decode("utf-8")), status` — bare call inside `with urlopen` block, no try/except. Provider returning HTML error page → JSONDecodeError → worker dies. |
| 4 | HIGH | `yaml.load()` arbitrary-code RCE | ✅ **Already fixed** | `config_loader.py` line ~120 uses `yaml.safe_load`. FIXES_FOR_CLAUDE.MD admits this. |
| 5 | HIGH | Unbounded dict cache → OOM in `session_manager.py` | ❌ **FALSE** | `session_manager.py` is SQLite-backed (file `swarm_runs/_sessions.db`), not a dict cache. Every operation uses `with _connect(...) as conn:` (line 60-63) which closes on scope exit. There is no in-memory `{}` cache to grow unbounded. |
| 6 | HIGH | SQLite connections not closed on shutdown | ❌ **FALSE** | Same context-manager pattern as #5. Connections close when each function exits. No persistent connection to leak. |
| 7 | HIGH | Worker-pool race conditions in `swarm_run.py` | ❌ **FALSE** | Line 637: `with ThreadPoolExecutor(max_workers=max_parallel) as ex:` — context manager auto-`shutdown(wait=True)` on exit. Line 661 uses `as_completed(future_map)`. There is no path where tasks are dispatched after shutdown. |
| 8 | MEDIUM | No exponential backoff in retry loops | ✅ **Already fixed** | `api_consult.py::_post()` line 289: `delay = base_delay * (1.5 ** attempt) * random.uniform(0.8, 1.2)`. `.ruflo/orchestrator.py::run_hermes_direct` line 398: `time.sleep(2 ** attempt)`. Both already shipped. |
| 9 | MEDIUM | Inadequate HTTP 429 handling | ✅ **Already fixed** | Same as #8 — exponential backoff in place; FIXES_FOR_CLAUDE.MD admits this. |
| 10 | MEDIUM | Cleanup may fail if exceptions occur mid-execution | ❌ **Speculative** | No specific code site cited. Generic "use try/finally" advice. Skip until concrete. |

**Real bugs from the list: 1 (Bug 3 — JSON decode).** Already-fixed: 3.
Hallucinated: 4. Speculative: 1. Plus ruflo free-tier (separate section,
**real**).

---

## What's actually worth shipping

### A. Bug 3 — `JSONDecodeError` in `_post()` (the only real new bug)

```python
# tools/swarm/api_consult.py, line ~285
with urllib.request.urlopen(req, timeout=timeout) as r:
    status = r.getcode() or 200
    return json.loads(r.read().decode("utf-8")), status   # ← unhandled
```

**Real failure mode:** when a provider returns an HTML error page (Cloudflare
challenge, 502 from gateway, OAuth redirect), `json.loads` raises
`JSONDecodeError`. The worker process crashes with a stack trace that's hard to
read. The fix freebuff suggests is correct:

```python
with urllib.request.urlopen(req, timeout=timeout) as r:
    status = r.getcode() or 200
    raw = r.read().decode("utf-8", errors="replace")
    try:
        return json.loads(raw), status
    except json.JSONDecodeError as e:
        preview = raw[:200].replace("\n", " ")
        raise RuntimeError(
            f"non-JSON response from {url} (status={status}): "
            f"line {e.lineno} col {e.colno} — preview: {preview!r}"
        ) from e
```

One file, ~10 lines. Ship.

### B. Ruflo free-tier model names return HTTP 404

This is real and high-impact (ruflo is currently 0% successful). The current
`FREE_MODELS` dict in `.ruflo/orchestrator.py`:

```python
FREE_MODELS = {
    "coordinator":    "meta-llama/llama-3.3-70b-instruct:free",
    "researcher":     "google/gemini-2.0-flash-exp:free",
    "coder":          "deepseek/deepseek-chat-v3.1:free",
    "reviewer":       "meta-llama/llama-3.3-70b-instruct:free",
    "lightweight":    "meta-llama/llama-3.2-3b-instruct:free",
    "fallback":       "meta-llama/llama-3.3-70b-instruct:free",
}
```

freebuff observed `google/gemini-2.0-flash-exp:free` and
`deepseek/deepseek-chat-v3.1:free` 404 in production. Both were chosen by me
in commit `8099803` based on OpenRouter's then-published list. They've been
deprecated/renamed since.

**Lower-risk fix:** swap to OpenRouter slugs that have been stable through
the whole 2026-05 window:

| Role | Replace with | Reason |
|---|---|---|
| coordinator | `meta-llama/llama-3.3-70b-instruct:free` | Already correct |
| researcher | `meta-llama/llama-3.3-70b-instruct:free` | Drop Gemini free tier (unreliable) |
| coder | `deepseek/deepseek-chat:free` (no version suffix) | Bare slug routes to current default |
| reviewer | `meta-llama/llama-3.3-70b-instruct:free` | Already correct |
| lightweight | `meta-llama/llama-3.2-3b-instruct:free` | Verified working |
| fallback | `tencent/hy3-preview:free` | Last entry in `FAILOVER_MODELS` — known working |

**Higher-impact fix (recommended):** make ruflo's default tier `hybrid` instead
of `free`. The hybrid tier prefers a paid provider when a key is set, falling
back to free models. You already have CEREBRAS / DEEPSEEK / XAI / GROQ / etc.
keys set on this machine, so hybrid mode would simply work. Free-only is the
unreliable path; nothing in the project actually requires it.

```python
# orchestrator.py argparse default change
parser.add_argument("--tier", choices=["free", "paid", "hybrid", "local", "auto"],
                    default="hybrid",   # was "free"
                    ...)
```

If you want to keep free as default, ship the model-slug swaps above as a
minimum.

### C. Strike fabricated content from `FIXES_FOR_CLAUDE.MD`

The document is going to be loaded by future agents as ground truth. Leaving
4 hallucinated CRITICAL/HIGH bugs in it primes the next swarm to "fix" things
that aren't broken, costing real time and review cycles. The doc should be
edited (or this `CLAUDES_DIAGNOSIS.MD` should sit beside it) to mark Claims
1, 2, 5, 6, 7 as REJECTED with the grep evidence above. Otherwise we get
another round of phantom-bug PRs.

---

## Why the swarm hallucinated

Pattern matches what Kimi's round-2 review caught in `BUGS_FOUND.md`:
plausible-sounding bugs that match common Python anti-patterns, but no
grep-anchored evidence ties them to *this* file. Three engines independently
converging on the same plausible bugs is not corroboration — it's the same
training-data prior firing in three weights. The fix is the same one that
PR #824's `bug-hunter.yaml` already specifies: every claim must include a
literal code quote that survives `grep -F`. The current swarm
`tools/swarm/prompts/audit_*.md` prompts don't enforce this for the
`api_consult.py` audit. Worth adding.

(Side note: this is the third time this week — RUFLO bug_hunter, original
Kimi `BUGS_FOUND.md`, freebuff's `FIXES_FOR_CLAUDE.MD` — that a swarm has
flagged "API keys in URLs" or "logs full responses" against `api_consult.py`
specifically. Neither claim has ever been substantiated by a code quote.
Probably wired into how LLMs talk about HTTP wrappers as a class. Add it to
the prompt as an explicit "DO NOT REPORT WITHOUT GREP EVIDENCE" item.)

---

## Recommended action plan

1. **Ship Bug 3 fix** (JSON decode try/except). One file, ten lines.
2. **Switch ruflo default tier to `hybrid`** (or at minimum swap the broken
   model slugs). Restores ruflo from 0% → working.
3. **Annotate or rewrite `FIXES_FOR_CLAUDE.MD`** to mark the 4 hallucinated
   CRITICAL/HIGH claims as REJECTED-WITH-EVIDENCE so the next agent doesn't
   re-spend cycles on them.
4. **Update `tools/swarm/prompts/audit_*.md`** to require literal-quote
   evidence on any "secret leakage" / "unbounded cache" / "race condition"
   claim. The contract from `bug-hunter.yaml` already exists; just doesn't
   reach the audit prompts.
5. **Don't** ship the unbounded-cache, response-body-logging, URL-key, or
   worker-pool-race fixes — they're fixes for bugs that don't exist and would
   add code complexity for zero real-world benefit.

---

## My answer to "want me to start fixing the bugs now?"

- Bug 3 (JSON decode): **yes, ship.**
- Bug 4 (yaml.load): **already done, no-op.**
- Bug 5 (session cache): **no, claim is wrong.**
- Ruflo free-tier endpoints: **yes, ship — switch to hybrid tier.**
- Bugs 1, 2, 7: **no — go grep first; you won't find them.**

---

## Update 2: end-to-end audit of `tools/swarm` + `.ruflo` (subagent-verified)

Round 3 review. Two parallel Explore subagents read every relevant file fully.
Findings re-checked by hand against the live tree on `main` (commit `7cb9c97`).

### Verifying the validation claims you forwarded

| Claim about ruflo | Verdict | Evidence |
|---|---|---|
| `--model` arg passed from YAML to Hermes CLI | ✅ TRUE | `.ruflo/orchestrator.py:383` (`run_hermes_direct`), `:465` (`run_hermes_tmux`) |
| `HERMES_BIN` resolves reliably | ✅ TRUE | `.ruflo/orchestrator.py:45` env → `shutil.which("hermes")` → fallback path |
| YAML merge replaces inline-overwrite logic | ✅ TRUE | `.ruflo/orchestrator.py:854-869` — per-field merge, post-PR-#824 |
| Robust failover system | ✅ TRUE | `get_failover_model()` line 153-164. Hand-traced: attempt=1 → candidates[0]; attempt=2 → candidates[1]; clamps; never repeats primary. Correct. |
| 5 tiers (free/paid/hybrid/local/auto) | ✅ TRUE | argparse `--tier` line 846; `run_agent()` dispatch line 604. Note: hybrid/auto rely on default `mode="direct"` to fall through; not an explicit fallback call. |
| All 5 YAML agents have `unable_to_verify` directive | ✅ TRUE | `grep -l "unable_to_verify" .ruflo/agents/*.yaml` matches all 5 files. |
| `unable_to_verify` clause actually reaches the model | ✅ TRUE | YAML `goal` field → `load_yaml_agents()` → AGENTS dict → `f"TASK: {agent['goal']}"` at line 372 → `hermes chat -q` at line 377. End-to-end traced. |

### What the subagents flagged that I had wrong in the earlier sections

#### 1. `run_hermes_tmux()` is **not** polling — my PR #825 fix was never merged

I claimed earlier (in this same session) that PR #825 added `tmux has-session`
polling and `-S -10000` capture. **PR #825 is CLOSED, not merged**
(`gh pr view 825` → `state: CLOSED, mergedAt: null`). The current code on
main still has:

- `.ruflo/orchestrator.py:481`: `time.sleep(timeout)` — full-duration blocking
  sleep, no poll loop.
- `.ruflo/orchestrator.py:485`: `tmux capture-pane -t {session} -p -S -500`
  — original 500-line truncation.

So the tmux mode still wastes the full timeout per call and silently truncates
multi-page agent outputs. Worth re-opening the patch as its own PR.

#### 2. Other PR #825 fixes also never landed

- `tools/swarm/config_loader.py` does not have the `return_source` kwarg → CLI
  still prints `envs[0]` regardless of which alias was actually used.
- `tools/swarm/swarm_run.py:532` still has the duplicated hardcoded
  `api_engines = {...}` set. Drift hazard remains.
- `ollama_cloud` still wired with `OLLAMA_CLOUD_KEY` env (an SSH push key, not
  chat auth) → still preflight-skipped on this machine.

### New bugs the subagents found (not in any prior review)

| File | Line | Bug | Severity |
|---|---|---|---|
| `tools/swarm/api_consult.py` | 309–322 | `JSONDecodeError` preview is taken AFTER `.decode("utf-8", errors="replace")`, so the error message references mangled-string line/col, not the original bytes. Cosmetic. | LOW |
| `tools/swarm/worker_runner.py` | 426 vs 550 | Inconsistent `getattr(args, "resume", None)` vs `args.resume` access — first call site can `AttributeError` if argparse path doesn't define it. | LOW |
| `tools/swarm/api_consult.py` | (silent path) | If a provider returns 200 with HTML body, `_extract_json_object()` returns None, envelope stubs to `COMMENT_ONLY`, swarm records `ok_count=1` despite garbage output. No stderr signal. | MEDIUM |
| `tools/swarm/api_consult.py` | 635/702 (ollama) | `shutil.which("ollama")` checks but does not detect "binary present, daemon dead" — subprocess hangs the full 400s timeout silently. | LOW |
| `tools/swarm/config_loader.py` | 97–98 | Raises bare `KeyError` on unresolved `${VAR}`, but `swarm_run.py:259` only catches `RuntimeError`. KeyError escapes uncaught. | LOW |

### Recurring claim I keep rejecting

The CEREBRAS env name `CERBRAS_FREE_ITHINK` (note: CERBRAS without the second
E) is the **literal env name the user set on this machine**, intentionally,
months ago. It's not a typo in our code — the typo is in their env, and our
code just respects the name they used. Confirmed via earlier `env | grep -i
CEREBRAS` output: `CEREBRAS_API_KEY_FREE`, `CEREBRAS_API_KEY_PAID` (these are
the canonical names; `CERBRAS_FREE_ITHINK` is a third legacy alias). All three
are in the resolver tuple. Subagent flagged this as a bug — it isn't.

### Updated ship-list (supersedes Update 1)

1. **Bug 3 — JSON decode try/except** in `api_consult.py` (still real, still
   not shipped).
2. **Re-open PR #825 as a fresh PR**: `tmux` polling + `-S -10000` capture +
   `return_source` kwarg + preflight drift fix + ollama_cloud reclassification.
   These are still all real, all unshipped.
3. **Ruflo `--tier hybrid` default** (or model-slug swap to known-working
   names). Still real.
4. **HTML-200 silent failure** in `api_consult.py` — add a content-type check
   or empty-extract-result warning before counting as `ok`. New finding.
5. **`config_loader.py` KeyError leakage** — wrap the bare KeyError in a
   `RuntimeError` so `swarm_run.py:259` catches it. One-line fix.

Things I am explicitly NOT recommending shipping (all hallucinated by prior
swarm runs): API keys in URLs, response body logging, unbounded session dict,
worker pool race, CEREBRAS env typo "fix".

---

## Update 3: live validation run (2026-05-05 ~17:10 UTC)

Multiple agents shipped fixes to `main` between updates 2 and 3:
`aa1f93e` (preflight sync), `45d29ec` (KeyError→RuntimeError + bytes preview),
`5b0cab7` (HTML-200 detection), `64531c7` (tmux `-S 0`), `a7e2b80` (12-bug
batch), `5510c0f` (session_manager `_connect`).

### Validation swarm I ran just now

`swarm_runs/validation_20260505T_claudeopus47/` — 3 engines verifying that 7
specific fixes from updates 1+2 are actually present.

| Engine | Verdict | Hallucination rate |
|---|---|---|
| **xai** | REJECT (1 false miss) | 14% — said `tmux -S 0` missing; it's at `.ruflo/orchestrator.py:485` |
| **deepseek** | REJECT (all-7 false misses) | 100% — claimed all 7 fixes missing, output reads as if it never received the source |
| **cerebras** | malformed (no `verdict` field) | N/A |

Hand-verified ground truth: **all 7 fixes are present on main.**
- `tools/swarm/api_consult.py:312` — JSON decode try/except ✅
- `tools/swarm/worker_runner.py:34` — `_HTML_SIGNALS` module-level ✅
- `tools/swarm/swarm_run.py:527` — preflight uses `ENGINE_KEY_ENVS` ✅
- `tools/swarm/config_loader.py:121` — RuntimeError on unresolved `${VAR}` ✅
- `.ruflo/orchestrator.py:485` — `tmux capture-pane -S 0` ✅ (xai missed)
- `.ruflo/orchestrator.py:846` — `--tier default="hybrid"` ✅
- `.ruflo/orchestrator.py:875+` — YAML overrides inline AGENTS ✅

The swarm code is in the best shape it's been all session. **The remaining
problem is RUFLO bug_hunter output quality**, not the plumbing.

### RUFLO end-to-end run — `--swarm bugs --tier paid`

Ran cleanly, no infrastructure errors. But the output is **100% hallucinated**:

```json
"file": "scripts/event_parser.py",      ← does not exist
"file": "cron/daily_sync.py",            ← does not exist
"file": "config/domain_settings.py",     ← does not exist
"file": "strategies/elite_config.json",  ← does not exist
```

All 7 file paths the agent reported — verified non-existent in the repo.
The `evidence:` field is filled with confabulated code quotes that also
don't exist.

**Why the YAML `unable_to_verify` directive didn't help:** in `--tier paid`
the model is a stateless chat-completion call via
`api_consult.py::call_openai_compat()`. It has **no file-reading tools**.
The directive says "If you cannot inspect the file path, return
`unable_to_verify`" — but the model interprets "inspect" as "reason about"
and reasons from training-data priors (typical Python-project file names).
It genuinely thinks it has access.

This is a scope bug, not a prompt-grammar bug. RUFLO's bug_hunter is
architecturally incapable of inspecting files in `--tier paid` mode, but
the prompt is written as if it could. Either:
- give it file-reading tools (heavy lift), or
- inline the source it should review into the prompt (cheap, what
  `tools/swarm/swarm_run.py` does for code-review prompts), or
- harden the prompt to "you have NO file access; return
  `unable_to_verify` for ANY file-based question."

### Round-3 ship list (supersedes prior lists)

1. **Fix RUFLO `bug_hunter` prompt** so it stops hallucinating bug claims.
   Highest-impact item by far. Prompt-only change, no code refactor.
2. **Add swarm-output sanity gate**: before recording `ok` in
   `_calls.jsonl`, regex-extract any `file:` paths from the output and verify
   at least one exists on disk. If 0/N exist, downgrade verdict to
   `low_signal`. ~20 lines in `tools/swarm/swarm_run.py`.
3. **Optional**: ship the `mysql_client.py` consistency pass currently
   uncommitted (4 except sites switched from `conn.close()` to
   `_return_conn(conn)`). Defensible; not urgent.

### Note on the manual commit / WSL git instructions

You said terminal git commands were failing and asked me to run the WSL
commands from `COMMIT_INSTRUCTIONS.MD`. I have **not** done that — the file
is staged locally but I'm holding off on git operations until you confirm
which side of the worktree should hold the canonical version. Earlier in this
session several branches got auto-rebased between commits, and I don't want
to push the freebuff session's three docs (`CEREBRAS_REVIEW_MAY5.MD`,
`CHATWITHCLAUDE.MD`, `COMMIT_INSTRUCTIONS.MD`) into a branch they shouldn't
be on. Tell me when to push and which branch.
