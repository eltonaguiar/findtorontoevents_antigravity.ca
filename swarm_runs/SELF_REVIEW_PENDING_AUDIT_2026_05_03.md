# Self-Review Pending Audit — 2026-05-03

**Auditor:** Antigravity (Opus 4.7 1M)
**Source doc:** `swarm_runs/SWARM_SELF_REVIEW.md` (real consensus-3 + red-team run @ 16:38:57Z)
**Method:** read-only cross-reference of every `imp-*` and side-finding against current `main`.
**Window:** SWARM_SELF_REVIEW dispatched 16:38Z; this audit covers code state at ~17:25Z.

---

## 1. Improvement × State Table

| ID | Title | State | Evidence | Remaining work |
|----|-------|-------|----------|----------------|
| **imp-A** | Wire personas into engine calls | **DONE** | Commit `792672ef111` (subagent S). `worker_runner.py:61-98` `_load_persona()` resolver; `worker_runner.py:111-115` prepends as preamble; `worker_runner.py:651-653` `--persona` flag; `swarm_run.py` per-engine YAML override (per commit body, smoke-verified `crypto-specialist` vs none). `INDEX.md:5-39` "How to use" section documents wire-in. | None — fully shipped including loud-fail on bogus name. |
| **imp-B** | Audit-trail completeness (`_calls.jsonl` enrichment) | **DONE** | Commit `792672ef111` (subagent Q). `swarm_log.py:11-22, 45-101, 113-181` adds `retry_count`, `model_fingerprint`, `tokens_in/out`, `transport_status` as top-level fields + `set_*` setters + `set_meta()` envelope. `api_consult.py` returns `(content, meta_dict)` 3-tuples. `worker_runner.py` pipes via `timer.set_meta()`. `swarm_stats.py` + `swarm_inspect.py` surface new columns. `METHODOLOGY.md` +53 LOC ("Section 9. Audit trail completeness (post-imp-B)"). | None for the schema. **Open downstream:** imp-C resolver still needs to *consume* `historical_ok_rate` derived from these fields. |
| **imp-C** | Auto-disagreement resolver (`tools/swarm/resolver.py`) | **NOT-STARTED** | `ls tools/swarm/` shows no `resolver.py`. Grep across `tools/swarm/` for `auto_resolve\|--auto-resolve\|weighted.*vote` returns zero matches in code (only persona-doc text mentions). `DISAGREEMENT_RESOLUTION.md` exists in `swarm_runs/` but is a **prior-run analysis output**, not the resolver module. | Build `tools/swarm/resolver.py` with `weight = self_conf * historical_ok_rate` primitive; opt-in `--auto-resolve` flag on `swarm_run.py`. Open Question #1 from SWARM_SELF_REVIEW (weight source) is resolved in the doc — implement multiplicatively. |
| **imp-D** | Cost/quota-aware engine scheduler | **NOT-STARTED** | No `tools/swarm/scheduler.py`. Grep `swarm_run.py` for `deepseek.*share\|0\.4\|cap.*deepseek\|round.robin\|quota` → zero matches. The 57% deepseek concentration is unmitigated. | Design pass first (Open Q #2 — rubric vs hard cap). Then implement hard cap (40%) as floor + complexity rubric for routing within cap. |
| **imp-E** | Followup-redundancy detector | **NOT-STARTED** | `swarm_followup.py:192-340` `main()` has no hash-of-prior-turn check. Grep for `hash\|delta\|no delta vs prior turn\|prior turn` returns zero matches in code (only frontmatter text). | Add `_normalize_consensus_hash(turn_output)` + skip-with-warning when turn N hash == turn N-1 hash; emit `[swarm-followup] STOP: no delta vs prior turn` and exit pre-N+1. ~40 LOC. |
| **side-1** | METHODOLOGY claim "auditable, timestamped reasoning traces" weaker than advertised | **DONE** | Closed by imp-B + `METHODOLOGY.md` +53 LOC adds Section 9 with falsification examples per field. Same commit `792672ef111`. | None. |
| **side-2** | Engine self-spoofing detection (xai/deepseek wrote `engine: claude-sonnet`, copied from prompt example block) | **NOT-STARTED** | Documented forensically in `swarm_runs/PR_REVIEW_ABORTED.md` (action U). `_pr_capture.py` shipped as a parallel fix (server-side `gh pr view`/`gh pr diff` capture, called from `swarm_dispatch.ps1:104`) which removes one root cause. But there is no audit-time check that flags `envelope.engine != dispatched_engine`. `model_fingerprint` is now populated (imp-B), so the data exists — needs a guard. | Add `swarm_inspect.py` rule: if `envelope_engine != dispatched_engine` → flag `SELF_SPOOFED`. ~10 LOC. |
| **side-3** | Run-id fabrication detection (xai cited `run-2023-10-15-03` not in `RUNS_LOG.md`) | **NOT-STARTED** | No mechanism in `swarm_inspect.py` or `schema_validate.py` cross-checks cited run-ids against `swarm_runs/RUNS_LOG.md`. Confirmed manually in Open Q #3 of SWARM_SELF_REVIEW; date format mismatch was the giveaway. | Add `_validate_run_ids(envelope, runs_log)` to `swarm_inspect.py`: regex extract `run-\d{4}-\d{2}-\d{2}-\d+` cites in answer text, intersect with `RUNS_LOG.md` ids, flag misses as `RUNID_FABRICATION_RISK`. ~25 LOC. |
| **side-4** | Voting-weight source for auto-resolver (Open Q #1) | **DONE-IN-DOCS / NOT-STARTED-IN-CODE** | SWARM_SELF_REVIEW.md:50-51 resolves the divergence: `weight = self_conf * historical_ok_rate`. Doc-level decision logged but no code consumes it because imp-C is not started. | Implement as part of imp-C. |
| **side-5** | kilo silent failure (231s, 0 B, transport drop) | **PARTIAL** | Documented in `SWARM_DESIGN_NOTES.md:56-62` (KFM-2). `swarm_log.py:73` now writes `transport_status="closed-by-peer"` sentinel when CLI returns rc=0 with 0 B (per imp-B commit body). No retry implemented — KFM-2 marks it as TODO ≤5 LOC, deferred because PONG legitimately returns 5 bytes. | (Optional) Add `rc=0 + empty + duration > 60s` retry to `call_opencode_or_kilo`. Low priority per design note. |
| **side-6** | Red-team JSON debug (claude opus 0 B in self-review run) | **DONE** | Commit `792672ef111` (subagent T) diagnosed Windows cmd.exe 8191-char limit; `worker_runner.call_claude` now pipes prompt via stdin when `prompt_bytes > 6000` (verified 73s/2421B output). See `worker_runner.py:328-352` (`_run` with `stdin_data`). | None for the root cause. Two unrelated downstream issues documented (`--max-turns 12` exhaustion, `--json-strict` no-op for claude) but not load-bearing. |
| **side-7** | PR-review prompt told API engines to run `gh pr view`/`gh pr diff` (root cause of 100% fabrication on 10/27 jobs) | **DONE** | `tools/swarm/_pr_capture.py` shipped (server-side capture); `swarm_dispatch.ps1:104` calls it; `prompts/pr_review_inline.md` is the new diff-embedded template. Forensics in `swarm_runs/PR_REVIEW_ABORTED.md`. | None. (side-2 self-spoofing detection is the residual hardening.) |

---

## 2. DONE-BY-PEER cross-reference

Peer session `reports/SESSION_SUMMARY_ANTIGRAVITY_2026_05_03_1340Z.md` and PR #739 audit `reports/HEDGE_FUND_PR_MERGE_AUDIT_2026_05_03.md` cover *production trading code* (BLACKLISTED_STRATEGIES enforcement at `smart_picks_engine.py:754` + `outcome_resolver.py:666`, JPY scope fix, etc.) — none of those PRs touch `tools/swarm/`. **No imp-* in this audit was handled by the peer thread.** All swarm-side improvements that landed today landed in commit `792672ef111` from a parallel Antigravity session at 13:10Z.

---

## 3. Pending Items — Ranked Priority Queue

Three items remain NOT-STARTED (imp-C, imp-D, imp-E) plus three side-findings (side-2, side-3, side-5 retry). Ranked by `(payoff × engine-agreement) / effort`:

### 1. imp-E — Followup-redundancy detector — Effort: **S** (~40 LOC, ~1.5h)

- **Payoff:** closes FOREX_DEEP_DIVE turn 3 + turn 4 waste flagged by both deepseek + xai independently (SWARM_SELF_REVIEW lines 23, 26). One known recurring issue — `swarm_runs/FOREX_DEEP_DIVE.md` confirms the pattern. Zero credit cost going forward.
- **Risk:** false positives if engines paraphrase same conclusion. Mitigate via JSON-key normalisation + numeric-tolerance hash, not raw-string hash.
- **Implementation steps:**
  1. Add `_normalize_for_hash(parsed_json)` → strip whitespace, sort keys, round floats to 3 sig figs, drop `timestamp`/`run_id` fields.
  2. After each turn in `swarm_followup.py:main()`, store `prior_hash`.
  3. If turn N's normalized hash == turn N-1's, log `[swarm-followup] STOP: no delta vs prior turn` and break loop before turn N+1.
  4. Wire env-var override `SWARM_FOLLOWUP_FORCE_CONTINUE=1` for explicit override.
- **Files to touch:** `tools/swarm/swarm_followup.py` only.
- **Test/verify:** replay `tools/swarm/examples/forex_deep_dive.yaml` — should stop after turn 3 instead of completing turn 4.

### 2. side-2 — Engine self-spoofing detection — Effort: **S** (~10 LOC, ~30 min)

- **Payoff:** closes PR_REVIEW_ABORTED.md root finding ("Wrote `engine: claude-sonnet` (copied from prompt example block — didn't self-identify)"). Data is already in `_calls.jsonl` post-imp-B. Pure additive guard. Cross-applies to every future `swarm_run.py` invocation, not just PR-review.
- **Risk:** very low — the dispatched-engine string is known at call time; envelope's claimed engine is a free-text field; mismatch is unambiguous.
- **Implementation steps:**
  1. In `swarm_inspect.py`, after parsing envelope, compare `envelope.get("engine", "").lower()` to `record["engine"]`.
  2. Mismatch → emit flag `SELF_SPOOFED` (joins existing `HEALTHY/TINY/ZERO/PARSE_FAILED/...` taxonomy).
  3. Update `tools/swarm/SPEC.md` § Inspector flags to document.
- **Files to touch:** `tools/swarm/swarm_inspect.py` + `SPEC.md`.
- **Test/verify:** run `swarm_inspect.py swarm_runs/pr_review_20260503T170445Z` — expect 6 `SELF_SPOOFED` flags on the deepseek/xai jobs.

### 3. side-3 — Run-id fabrication detection — Effort: **S** (~25 LOC, ~1h)

- **Payoff:** closes Open Q #3 (xai cited `run-2023-10-15-03`). One known false-citation; pattern is plausibly recurring on long-context engines. Same falsification class as side-2 but content-level rather than envelope-level.
- **Risk:** regex must accept both `run-\d{4}-\d{2}-\d{2}-\d+` and `run-\d{3}` formats. Don't false-positive on quoted prompt examples.
- **Implementation steps:**
  1. New helper `_validate_run_ids(answer_text, runs_log_path)` in `swarm_inspect.py`.
  2. Extract candidate ids via `re.findall(r"\brun-[0-9-]+\b", answer_text)`.
  3. Read `swarm_runs/RUNS_LOG.md` once, build set of valid ids.
  4. Any candidate not in the set → flag `RUNID_FABRICATION_RISK` with the cited id in detail field.
- **Files to touch:** `tools/swarm/swarm_inspect.py`.
- **Test/verify:** point at `swarm_runs/self_review_20260503T163857Z` — expect 1 flag on the xai answer for `run-2023-10-15-03`.

### 4. imp-D — Cost/quota-aware scheduler — Effort: **M** (~6h, design pass + impl)

- **Payoff:** breaks 57% deepseek concentration flagged by both engines (SWARM_SELF_REVIEW Q5). Cost-control benefit compounds per run; under-used `consensus-3` and `fast-cheap` presets get rotation. **However**, both engines diverge on mechanism (Open Q #2 unresolved in doc).
- **Risk:** quota cap may starve high-complexity tasks of best engine. Probable design: hard cap as floor + rubric within cap (per Open Q #2 likely answer).
- **Implementation steps:**
  1. **Design pass first** — write `tools/swarm/SCHEDULER_DESIGN.md` deciding rubric vs cap (or hybrid). 1h.
  2. New `tools/swarm/scheduler.py` with `pick_engines(task, budget, history)` → returns ordered engine list.
  3. Wire into `swarm_run.py` engine-selection block (currently grep-able via `engines` list in `swarm_run.py`).
  4. Add `swarm_stats.py` preset-usage tracker (action item ☆ from SWARM_SELF_REVIEW line 91-92, also unstarted) so we can verify rotation-fix landed.
- **Files to touch:** new `scheduler.py`, `swarm_run.py`, `swarm_stats.py`, new `SCHEDULER_DESIGN.md`.
- **Test/verify:** run 10× consecutive `swarm_run.py` invocations, assert deepseek share ≤ 40% and `consensus-3`/`fast-cheap` each used ≥ 1×.

### 5. imp-C — Automated disagreement resolver — Effort: **L** (>6h)

- **Payoff:** highest-value of all five but largest effort. Eliminates operator from ~80% of persistent splits (BOND case from CONSENSUS_v2). **Depends on imp-B (DONE) for `historical_ok_rate` data.** Data is now there but the resolver isn't.
- **Risk:** verbose engines may game evidence scoring. Cap argument tokens. Devil's-advocate round may double cost.
- **Implementation steps:**
  1. New `tools/swarm/resolver.py` exporting `resolve(question, answers, calls_jsonl)`.
  2. Stage 1: confidence-weighted vote with `weight = self_conf * historical_ok_rate` (per Open Q #1 resolution).
  3. Stage 2: if no clear winner (delta < 0.15), launch devil's-advocate round — pick the runner-up engine, ask it to argue against the leader.
  4. Stage 3: meta-engine (cerebras or inception) scores arg-quality on dimensions (citations, falsifiability, internal consistency).
  5. Opt-in `--auto-resolve` flag on `swarm_run.py`.
  6. Write `swarm_runs/DISAGREEMENT_RESOLUTION.md` v2 with the algorithm spec.
- **Files to touch:** new `resolver.py`, `swarm_run.py`, `SPEC.md`, refresh `DISAGREEMENT_RESOLUTION.md`.
- **Test/verify:** replay self-review run with `--auto-resolve` and confirm a tied-or-near-tied question gets resolved without operator input; round-trip cost < 1.5× the un-resolved run.

### 6. side-5 — kilo retry on rc=0 + empty — Effort: **S** (~5 LOC) — **DEFERRED**

Per `SWARM_DESIGN_NOTES.md:56-62`, deferred because PONG legitimately returns 5 bytes; needs a smarter heuristic than length gate. Park until an actual repeat of the silent-failure occurs.

---

## 4. If you only have 30 minutes

Ship **side-2 (self-spoofing detection)** + **side-3 (run-id fabrication detection)** together — both are ≤25 LOC additions to the same file (`swarm_inspect.py`), depend on already-shipped imp-B data, and close two of the three falsification gaps that `swarm_inspect.py` cannot currently catch (the third being content-fabrication, which is a model problem). Skip imp-E unless you also have time to replay `forex_deep_dive.yaml`.

---

## 5. Ambiguous / non-actionable items in SWARM_SELF_REVIEW.md

- **kilo `ZERO/PARSE_FAILED`** in this run was ultimately diagnosed as a transient backend hiccup (KFM-2). Not actionable as code — only as a heuristic note.
- **Action item "Document persona-wiring decision in `INDEX.md`...add 'Status: orphan pending wire-in (imp-A)' header"** is moot post-imp-A: INDEX.md now has a "How to use" section instead, which supersedes the orphan-status header. Mark resolved.
- **Action item "Add `consensus-3` and `fast-cheap` preset usage tracking to `swarm_stats.py`"** rolls up under imp-D step 4. No standalone implementation needed.
- **Effective-n disclaimer** ("Confidence on cross-engine consensus must be reduced one notch... on any item where only one engine spoke") is a methodological note, not an implementation task. Already reflected in the per-question CONVERGE/DIVERGE labels.
