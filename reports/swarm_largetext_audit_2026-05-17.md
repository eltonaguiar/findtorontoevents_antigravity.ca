# Swarm Large-Text Handling Audit — 2026-05-17

**Scope:** read-only investigation of `tools/swarm/` (v1) and `tools/swarm_v2/` for
text truncation on the input and output side of swarm PR/plan reviews.

**Observed problem:** kilo/groq engine responses came back capped at exactly
~2000 characters in the `commentary_text` field, truncated mid-sentence;
8-item plan answers cut at item 4.

---

## TL;DR — Root Cause

The 2000-char cap is **NOT** a token limit, **NOT** schema validation, and
**NOT** an engine setting. It is a single hard-coded slice in the **parse-fail
fallback path** of the v1 worker:

```
tools/swarm/worker_runner.py:1196
    "commentary_text": raw[:2000] or "(empty)",
```

This line only executes when `_extract_json_object(raw)` returns `None` — i.e.
the engine returned output that was **not parseable as JSON**. When that
happens the worker synthesizes a stub envelope and stuffs the **first 2000
characters of the raw engine output** into `commentary_text`. The rest of the
answer (items 5-8 of a plan, the back half of a review) is silently discarded —
though the *full* text is still on disk at `<out>.raw.txt` (written at
`worker_runner.py:1186-1187`, uncapped).

So the symptom "capped at exactly ~2000 chars" is a **reliable fingerprint that
the engine produced non-JSON output** (prose, markdown, a code-fenced block,
reasoning preamble, etc.) and the worker fell back. kilo and groq are the
usual offenders because they tend to wrap JSON in ```json fences or emit a
reasoning preamble, which `_extract_json_object` does not always recover.

---

## (a) Every Cap — Exact Locations

| # | File:Line | Value | Side | What it caps |
|---|-----------|-------|------|--------------|
| 1 | `tools/swarm/worker_runner.py:1196` | `raw[:2000]` | **OUTPUT** | **THE BUG.** Parse-fail fallback slices raw engine output to 2000 chars into `commentary_text`. |
| 2 | `tools/swarm/_pr_capture.py:75,117-122` | `max_diff_chars=60_000` | INPUT | PR unified diff truncated to 60 KB before embedding into the prompt. Truncation note appended. |
| 3 | `tools/swarm/_pr_capture.py:82,129` | `[:4000]` | INPUT | PR body truncated to 4000 chars before embedding. |
| 4 | `tools/swarm/_pr_capture.py:175` | `files[:50]` | INPUT | Changed-files list capped at 50 entries. |
| 5 | `tools/swarm/worker_runner.py:1117` | `render_md_context(..., max_chars=4000)` | INPUT | Resumed-session markdown context capped at 4000 chars. |
| 6 | `tools/swarm/session_manager.py:324-326` | `per_cap = min(2000, max(256, budget//2))` | INPUT | Per-message tail-truncation when rebuilding session history context. |
| 7 | `tools/swarm/api_consult.py:142-156` | `max_tokens: 4000` (groq, deepseek, xai, etc.) | OUTPUT | LLM completion token ceiling. 4000 tokens ≈ 12–16 KB text — NOT the cause of a 2000-*char* cut. |
| 8 | `tools/swarm_v2/swarms/core/llm_client.py:219` | `max_tokens: int = 4000` | OUTPUT | v2 completion token ceiling. Same — not a char cap. |
| 9 | `tools/swarm_v2/swarms/core/models.py:61` | `max_tokens: int = 4096` | OUTPUT | v2 `ModelConfig` default. Token ceiling. |
| 10 | `tools/swarm_v2/swarms/core/memory.py:236` | `mem.content[:200]` | INPUT | Memory-recall snippet cap (cosmetic, in system prompt). |

### Schema check — NO cap there

`tools/swarm/schema_review.json:38` defines `commentary_text` as
`{"type": "string", "minLength": 1}` — **there is no `maxLength`**.
`schema_validate.py` enforces required keys, enums, and a `minLength: 10`
*floor* on blocking/major evidence. It never truncates and never imposes an
upper bound. Schema validation is exonerated.

---

## (b) Input vs Output Truncation

- **The reported symptom (2000-char `commentary_text`) is OUTPUT truncation** —
  cap #1, the parse-fail fallback.
- **Input is also capped** but generously: the ~13 KB prompts the caller sent
  were **not truncated on input**. The 13 KB sits under the 60 KB diff cap
  (#2) and the prompt is delivered to CLI engines via **stdin** (`stdin_data`
  in `_run()`, `worker_runner.py:348-351,468,520,669,804`), which deliberately
  avoids the Windows `CreateProcess` arg-length/quoting truncation documented
  in `INTEGRATION_GUIDE.md:226` and `SPEC.md:89`. API engines (groq) post the
  prompt in a JSON request body — no arg-length limit at all.
  **Conclusion: 13 KB input prompts arrive intact.** The loss is entirely on
  the response side.

---

## (c) Chunking / Map-Reduce — Does Either Swarm Have It?

**No. Neither swarm chunks large prompts or large responses, and neither
auto-splits a task into sub-tasks.**

- **v1 (`tools/swarm/`):** one prompt → one engine call → one envelope. No
  map-reduce, no continuation, no "respond in N parts" loop. `swarm_followup.py`
  exists for *multi-turn* chains but each turn is still a single uncapped call;
  it does not split by size.
- **v2 (`tools/swarm_v2/swarms/`):** `engines/pr_review_swarm.py` fans work to
  worker *roles* (impact analyzer, code reviewer, risk controller) but each
  worker still makes one `LLMClient.complete()` call. `coding_swarm.py` has a
  `DEFAULT_MAX_REVISIONS=3` *revision* loop, not a size-driven splitter.
  `code_reviewer.py:249` only *warns* "Large PR — consider splitting"; it does
  not split.

**The caller must currently pre-split large tasks by hand.** There is no
automatic continuation when an answer is cut.

---

## (d) Concrete Fixes — Highest Value First

### FIX 1 (HIGHEST VALUE) — Stop discarding 60%+ of the answer on parse-fail

**File:** `tools/swarm/worker_runner.py:1189-1207`
**Change:** before falling back, try harder to recover JSON; and when fallback
*is* unavoidable, do **not** truncate — carry the full raw text.

Two parts:

1. **Recover fenced / preambled JSON.** Replace the single
   `obj = _extract_json_object(raw)` call with a recovery ladder:
   - strip ```json / ``` code fences,
   - strip any leading reasoning preamble before the first `{`,
   - take the substring from the first balanced `{` to its matching `}`,
   - retry `_extract_json_object` on each candidate.
   This alone will eliminate most kilo/groq fallbacks, because their output
   *is* valid JSON — just wrapped.

2. **Uncapped fallback.** When recovery still fails, change line 1196 from
   `"commentary_text": raw[:2000] or "(empty)"` to carry the full text:
   ```python
   "commentary_text": raw or "(empty)",
   ```
   and add an explicit field so downstream consumers know it is unparsed:
   ```python
   "_parse_status": "non_json_fallback",
   ```
   The full raw text is already persisted at `<out>.raw.txt`; there is no
   reason the envelope should hold a lossy 2000-char prefix. If a hard ceiling
   is wanted for sanity, make it a named constant (`FALLBACK_COMMENTARY_CAP`)
   set to e.g. 50_000 and append a `[truncated at N chars; see raw_path]`
   note, mirroring the `_pr_capture.py` diff-truncation pattern.

**Impact:** fixes the exact reported symptom. ~5 lines + one helper function.

### FIX 2 — Add a continuation mode for genuinely long answers

**File:** `tools/swarm/worker_runner.py` (post-call, after line 1178) and
`tools/swarm/api_consult.py`.
**Change:** detect a length-limited completion and auto-continue:
- groq/OpenAI-style responses expose `choices[0].finish_reason`. When it is
  `"length"`, the answer hit `max_tokens` and is incomplete.
- `api_consult.py` currently discards `finish_reason`; surface it into the
  `call_meta` dict (alongside `tokens_out`).
- In `worker_runner.py`, if `finish_reason == "length"`, issue a follow-up
  call with the prior text plus "continue from where you stopped" and
  concatenate, up to a small `MAX_CONTINUATIONS` (e.g. 3).
This handles the case where an 8-item plan genuinely exceeds 4000 output
tokens (distinct from the parse-fail bug, but the same user-visible symptom).

### FIX 3 — Raise output token ceilings for review/plan workloads

**Files:** `tools/swarm/api_consult.py:142-156`,
`tools/swarm_v2/swarms/core/llm_client.py:219`,
`tools/swarm_v2/swarms/core/models.py:61`.
**Change:** PR/plan reviews are long-form. Bump the default `max_tokens` for
review-class calls from 4000 to 8000 (groq llama-3.3-70b, deepseek, xai all
support far more). Either raise `SAMPLING_DEFAULTS` directly, or have
`swarm_run.py` pass `<ENGINE>_MAX_TOKENS=8000` via the per-engine YAML
override that `_engine_overrides.load()` already supports — no code change,
just a config entry. Lower-risk to do via config.

### FIX 4 — Add an optional map-reduce splitter for oversized inputs

**File:** new `tools/swarm/_chunker.py`, wired into `swarm_run.py`.
**Change:** when an input artifact exceeds a threshold (e.g. diff > 60 KB so
`_pr_capture.py` would truncate it — cap #2), split the diff by file hunk,
dispatch one sub-review per chunk, then run a final reduce call that merges
the per-chunk envelopes into one. This removes silent input loss for very
large PRs. Lower priority than FIX 1 because 13 KB prompts are well under the
60 KB cap — this is for future-proofing 100 KB+ diffs.

---

## Single Highest-Value Fix

**FIX 1** — in `tools/swarm/worker_runner.py:1189-1207`: add a JSON-recovery
ladder (strip code fences / reasoning preamble / take first balanced object)
before the parse-fail fallback, and change line 1196 from `raw[:2000]` to the
full `raw`. The reported truncation is the worker silently dropping the back
half of an answer it failed to parse as JSON — kilo/groq almost always emit
*valid* JSON that is merely fenced or preambled, so recovery fixes the
common case, and the uncapped fallback fixes the rest. ~5 lines plus one
helper, no schema or engine changes needed.
