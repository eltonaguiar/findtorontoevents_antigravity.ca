# Swarm Methodology

The soundness argument: why this swarm produces trustworthy multi-engine
consensus rather than averaged hallucination.

Companion: [README.md](README.md) · [SPEC.md](SPEC.md) ·
[INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) · [REVIEW_GUIDE.md](REVIEW_GUIDE.md).

---

## 1. Threat model

What can go wrong when N independent LLMs review code or data:

| # | Threat | Failure mode |
|--|-------|----------------------|
| T1 | Hallucination | Engine fabricates a file, function, commit, metric, or test result |
| T2 | Confidence inflation | `confidence: HIGH` with no supporting evidence |
| T3 | Stale snapshot | Engine cites a metric since changed in `dashboard_data.json` |
| T4 | Prompt injection | Hostile content in PR diff manipulates the worker |
| T5 | Cost runaway | Retry loops / unbounded fan-out blow through API credits |
| T6 | Silent failure | Zero-byte response looks like "no concerns found" |
| T7 | Engine self-spoofing | Output claims `engine: "gpt-4o"` when cerebras ran |
| T8 | Stale state leak | Resumed session inherits stale flags from prior turn |

If T1–T8 reach the user unflagged, "consensus" degrades to "average of
confidently-stated guesses" — worse than one careful engine.

---

## 2. Defenses

Each threat maps to a concrete mechanism backed by a file path.

### T1 — Hallucination

**Mechanism**: required `evidence` field on every `concerns[]` entry, schema-enforced.

- [`schema_review.json`](schema_review.json) lines 23–35 — `concerns[].evidence`
  is `required`. Validation in [`schema_validate.py`](schema_validate.py).
- [`prompts/pr_review.md`](prompts/pr_review.md) — anti-hallucination contract:
  every claim must be diff-backed, source-backed, test-backed, dashboard-data-backed,
  or marked `severity: "question"` if speculative.
- [`prompts/redteam.md`](prompts/redteam.md) — fabrication red-team agent
  attempts to disprove every aggregated concern. Verdicts: `confirmed`,
  `refuted`, `unverified`.
- [`.claude/agents/fabrication-red-team.md`](../../.claude/agents/fabrication-red-team.md)
  — subagent persona invoked in dispatch flow.
- [`prompts/merge_reviews.md`](prompts/merge_reviews.md) line 11 —
  merge-captain demotes blocking/major concerns with no evidence to `question`.

### T2 — Self-confidence inflation

**Mechanism**: cross-engine corroboration required.

- [`prompts/merge_reviews.md`](prompts/merge_reviews.md) lines 8–11:
  > Include a concern only if: it has non-empty `evidence`, OR it is
  > corroborated by ≥2 independent engines (different `engine` field).
- A single engine claiming `HIGH` confidence with no evidence and no
  corroboration is dropped to the `skipped_concerns` list.

### T3 — Stale snapshot

**Mechanism**: dashboard-data-backed claims must cite the key path.

- [`prompts/pr_review.md`](prompts/pr_review.md) line 26 — claim type
  `dashboard-data-backed` requires citing key path inside
  `audit_dashboard/data/dashboard_data.json`.
- The reviewer can re-evaluate by re-reading the cited path — a stale claim is
  immediately falsifiable.

### T4 — Prompt injection

**Mechanism**: read-only allowlist + per-engine env isolation.

- [`safety.py::READ_ONLY_DISALLOWED`](safety.py) L59–84 — Edit, Write,
  `git push/commit/reset/rebase/checkout`, `rm/mv/cp/chmod`,
  `gh pr merge/comment/review/edit/close`, `gh api -X POST/PATCH/DELETE`.
- [`safety.py::READ_ONLY_ALLOWED`](safety.py) L87–109 — explicit read-only
  allowlist.
- [`safety.py::isolated_env`](safety.py) L112–126 — worker subprocess sees only
  `ENGINE_REQUIRED_KEYS[engine]` + `ALWAYS_KEEP` (PATH, USERPROFILE, etc.).
  Every other secret (AWS_*, GH_TOKEN, sibling API keys) is dropped.
- [`safety.py::can_post`](safety.py) L150 + [`comment_poster.ps1`](comment_poster.ps1)
  — only `comment-poster` role may write to GitHub.

### T5 — Cost runaway

**Mechanism**: bounded fan-out + hard timeouts + no retries.

- `swarm_run.py:209` — `--max-parallel` default 4.
- `worker_runner.py:182` `_run` — 600 s default, per-engine up to 900 s.
- `api_consult.py:77` `_post` — 180 s per HTTP call.
- No retry loop. Failed engine returns `rc != 0`; run proceeds with N-1.

### T6 — Silent failure

**Mechanism**: byte-size flag taxonomy + zombie detection.

- [`swarm_inspect.py::_flags`](swarm_inspect.py) L53–79 — `ZERO`, `TINY` (<200 B),
  `SHORT` (<1 KB), `HEALTHY` (≥1 KB), `CREDITS?`, `AUTH?`, `TRUNCATED?`,
  `TUI_ONLY`, `PARSE_FAILED`.
- [`swarm_log.py::log_call`](swarm_log.py) L44 — `low_signal = output_bytes < 50 or rc != 0`.
- [`swarm_stats.py::aggregate`](swarm_stats.py) L73–80 — `low_signal_rate ≥ 50%`
  → `ZOMBIE_OUTPUT`; `ok_rate < 50%` → `LOW_OK_RATE`.
- `worker_runner.py:482` — non-JSON output yields a stub envelope marked
  `fabrication_risk.level = HIGH`, `verdict = COMMENT_ONLY`.

### T7 — Engine self-spoofing

**Mechanism**: filename-derived engine name overrides envelope claims.
[`swarm_inspect.py`](swarm_inspect.py) L156–160 prefers the filename stem
(what the worker invoked) over the envelope's `engine` field (which the model
can spoof, e.g. cerebras responses sometimes claim `engine="gpt-4o"`).

### T8 — Stale state leak

**Mechanism**: explicit session resume protocol.
[`session_manager.py`](session_manager.py) stores state in
`swarm_runs/_sessions.db` (sqlite); resume via `--from-session SID`.
[`worker_runner.py`](worker_runner.py) L392–438 has engine-specific paths:
claude native (`--resume`), API replay (history-as-preface), CLI fallback
(MD context). Cross-engine resume logs a warning at L434.

---

## 3. Audit trail

Every call writes to four locations. A consensus claim is always traceable.

```
+---- Worker call (one engine, one prompt) ----+
|                                              |
| 1. swarm_runs/_calls.jsonl                   |
|    {ts_utc, engine, latency_s, prompt_bytes, |
|     output_bytes, returncode, ok, low_signal}|
|                                              |
| 2. swarm_runs/_sessions.db (--persist)       |
|    sessions(id, engine, model, status)       |
|    messages(session_id, role, content, ...)  |
|                                              |
| 3. swarm_runs/<run_TS>/<engine>.json         |
|    parsed envelope + _swarm_meta             |
|                                              |
| 4. swarm_runs/<run_TS>/<engine>.json.raw.txt |
|    raw model output (post-cleaner)           |
+----------------------------------------------+
```

Replay: follow merge-captain's `corroborating_engines`, open each
`<engine>.json` in the run dir, read the raw sidecar to see exactly what the
model emitted. Multi-turn deep-dives write `_chain_summary.json` so the
inspector labels rows as `<engine>:turn_<N>` (see
[`swarm_followup.py`](swarm_followup.py)).

---

## 4. Anti-hallucination contract

Verbatim from [`prompts/pr_review.md`](prompts/pr_review.md):

```
## Anti-hallucination contract (MANDATORY)

Every claim in `strengths` and `concerns` must be one of:
- diff-backed (cite gh pr diff hunk lines)
- source-backed (cite `path:line` on checked-out commit)
- test-backed (cite test name + observed pass/fail)
- dashboard-data-backed (cite key path inside `audit_dashboard/data/dashboard_data.json`)
- explicitly marked `severity: "question"` if speculative

Do NOT claim a test passed unless CI was green or you ran it.
Do NOT claim a PR contains a file/component/function unless it appears in the diff or repo.
You are read-only. Never post comments.
```

Schema enforcement: blocking/major concerns with empty `evidence` are demoted
to `question` by the merge-captain (`prompts/merge_reviews.md` line 11) before
they reach the user.

---

## 5. Engine diversity

Cross-engine corroboration is only meaningful if the engines are independent.
The fleet covers four diversity axes:

- **Vendor** — Anthropic (claude), Google (gemini), xAI (grok), DeepSeek,
  Cerebras (gpt-oss-120b), Inception (mercury-2), Ollama Cloud, GitHub (copilot).
  Multiple independent providers. (MiniMax via TUI/freebuff was retired
  2026-05-04.)
- **Architecture** — dense transformer (claude, gpt-oss, copilot), MoE
  (deepseek-chat), diffusion (mercury-2).
- **Auth** — API keys (deepseek, xai, inception, cerebras), OAuth in CLI config
  (claude, gemini, copilot).
- **Reasoning depth** — deep (claude opus, kimi-k2-thinking), fast (haiku,
  gpt-oss-120b), code-edit specialist (mercury-2).

A single failure mode (vendor outage, shared training-data flaw) cannot bring
down the swarm because corroboration spans vendor + architecture boundaries.

---

## 6. Falsifiability check

The methodology is sound only if all three mechanisms work end-to-end:

1. **Red-team can disprove fabrications.** Tested 2026-05-03 (see
   `reports/PR_513_VERIFICATION_CORRECTIONS_2026_04_29.md` for an analogous
   catch where multi-engine corroboration refuted overstated PR claims).
2. **Merge-captain drops unsupported claims.** Verified by
   `prompts/merge_reviews.md` line 11 demotion rule + `skipped_concerns[]`
   audit trail.
3. **Inspector flags low-signal output.** Verified by
   `swarm_inspect.py::_flags` returning `ZERO` / `TINY` / `PARSE_FAILED`
   before the user trusts the run.

If any of these break, downgrade trust accordingly. The `swarm_stats.py`
`ZOMBIE_OUTPUT` flag and `swarm_inspect.py` `--latest` are the front-line
detectors of methodology-degradation.

---

## 7. Known limitations

- **Free-tier engines** may produce shorter responses than paid tiers —
  flagged `SHORT` when <1 KB.
- **Gemini in-prompt JSON contract bypass** — mitigated by `--json-strict`
  framing wrapper in `worker_runner._GEMINI_JSON_PREFIX`.
- **Copilot tool-call mixing** — mitigated by `output_parsers.parse_copilot()`.
- **No cross-run caching** — cost is linear in `(engines × prompt_size × runs)`.
- **Non-Claude CLI resume** is MD-context replay, not native — costs prompt
  tokens. Cross-engine resume logs a warning at `worker_runner.py:434`.

---

## 8. Comparison to Kimi swarm

We adopted three patterns from the Kimi swarm prototype (see
`swarm_runs/KIMI_VS_OURS_MERGE_PLAN.md`):

| Adopted from Kimi | Where |
|-------------------|-------|
| `${VAR}` / `${VAR:-default}` env-var substitution in YAML configs | [`config_loader.py::interpolate`](config_loader.py) |
| Centralised safety enforcement module | [`safety.py`](safety.py) |
| YAML configs + sqlite session persistence | [`session_manager.py`](session_manager.py) + `swarm.config.example.json` |

We retain three patterns Kimi lacks:

| Our advantage | Where |
|---------------|-------|
| Evidence-required JSON schema with `--json-strict` engine override | [`schema_review.json`](schema_review.json) + `prompts/pr_review.md` |
| Per-call audit trail with zombie/low-signal flags | [`swarm_log.py`](swarm_log.py) + [`swarm_stats.py`](swarm_stats.py) + [`swarm_inspect.py`](swarm_inspect.py) |
| Single-writer GitHub-comment isolation (`comment_poster.ps1` is the only thing that posts) | [`safety.py::can_post`](safety.py) + [`comment_poster.ps1`](comment_poster.ps1) |

The combined design is the merge plan written up in
`swarm_runs/KIMI_VS_OURS_MERGE_PLAN.md`.

---

## 9. Audit trail completeness (post-imp-B)

Until imp-B (landed 2026-05-03 from the swarm self-review action list),
`_calls.jsonl` could prove a call **happened** but couldn't falsify subtle
fabrications. The self-review surfaced the gap: 9/16 deepseek calls had no
reasoning trace, and the audit trail had no way to distinguish "engine
refused" from "engine timed out" from "engine answered but transport dropped
the output" — the kilo 0-byte / 231 s symptom in
`swarm_runs/self_review_20260503T163857Z/`.

Five new fields now ride on every JSONL row (top-level, not buried in
`extra`). Each closes a specific hallucination class:

| Field | Closes | Falsification example |
|-------|--------|------------------------|
| `latency_s` (existing — verified per-call) | "fast / cheap" claims with no per-call breakdown | a "consensus-3 finished in 90 s" boast collapses if one engine took 80 s alone. |
| `retry_count` | **silent retry success** | original 504 + retry 200 used to log as `ok=true` with no trace; now the row carries `retry_count=1`, so a reviewer can tell the engine answered on the second try (and ask why the first failed). |
| `model_fingerprint` | **self-spoofing** | requesting `cerebras --model gpt-oss-120b` and getting `data.model = "gpt-3.5-router"` would have looked indistinguishable before; now the fingerprint mismatch is visible to `swarm_inspect`. |
| `tokens_in` + `tokens_out` | **prompt-truncation hallucinations** | engine claims to have read a 6 KB briefing but `tokens_in=200` means it hit a context cap somewhere upstream; bogus "I reviewed the full diff" claims become falsifiable. |
| `transport_status` | **silent transport failures** | the kilo 0 B / 231 s case from the self-review now logs `transport_status="closed-by-peer"` (rc=0 with no output) instead of looking like a healthy short reply. HTTP `504` from a provider also lands here verbatim instead of being collapsed into `rc!=0`. |

Population matrix:

| Engine class | `model_fingerprint` | `tokens_in` / `tokens_out` | `transport_status` |
|---|---|---|---|
| deepseek / xai / inception (OpenAI-compat) | `data.model` from response | `usage.prompt_tokens` / `usage.completion_tokens` | HTTP status as string (`"200"`, `"504"`) |
| cerebras (SDK) | `resp.model` | `resp.usage.prompt_tokens/completion_tokens` | `"ok"` on success / exception class on fail |
| ollama_cloud (CLI) | requested model name (TODO: pull real fingerprint when CLI exposes it) | `0` (CLI doesn't surface usage) | `"ok"` / `rc=<n>` |
| claude / gemini / opencode / kilo / copilot (CLI) | `""` (CLI engines don't expose model id reliably) | `0` (no usage on CLI) | `"ok"` / `"timeout"` / `"closed-by-peer"` / `rc=<n>` |

Backward compatibility: rows logged before imp-B omit the five fields.
`swarm_stats.py` and `swarm_inspect.py` treat missing keys as `""` / `0` and
**suppress the new columns** when no record carries them, so legacy run dirs
render exactly as before.

Implementation pointers:

- [`swarm_log.py::CallTimer`](swarm_log.py) — adds `set_meta()` /
  `set_retry_count()` / `set_model_fingerprint()` / `set_tokens()` /
  `set_transport_status()`. Direct attribute assignment also works.
- [`api_consult.py`](api_consult.py) — every `call_*` function returns
  `(content, meta)`; `--meta-file <path>` writes the meta dict for
  out-of-band capture by the worker subprocess wrapper.
- [`worker_runner.py::call_api_consultant`](worker_runner.py) — reads the
  meta sidecar and pipes it into the outer `CallTimer` via `set_meta()`.
  CLI engines build their meta dict via the local `_cli_meta(rc)` helper.
- [`swarm_stats.py`](swarm_stats.py) — new `tok_in` / `tok_out` / `model_fp`
  columns rendered IFF at least one record carries the field.
- [`swarm_inspect.py`](swarm_inspect.py) — new `tok_used` / `model_fp`
  columns; pulls from `_swarm_meta` on the per-engine envelope.
