# Swarm Self-Review

## Run metadata

- **UTC timestamp:** 2026-05-03T16:38:57Z (dispatch) → 16:42:54Z (red-team complete)
- **Run dir:** `swarm_runs/self_review_20260503T163857Z/`
- **Preset:** `consensus-3` (deepseek, xai, kilo) + `--red-team` (claude opus)
- **Engines OK:** 2 of 3 (deepseek HEALTHY, xai HEALTHY, **kilo ZERO/PARSE_FAILED**)
- **Red-team:** FAILED — claude opus returned non-JSON, marked `fabrication_risk: HIGH` by the
  red-team auto-wrapper itself (it caught its own schema failure, ironic but appropriate).
- **Estimated cost:** $0.0653 (cap was $0.50). Well under budget.
- **Inspector flags:**
  - deepseek → HEALTHY (5226B raw)
  - xai → HEALTHY (2984B raw)
  - kilo → ZERO,PARSE_FAILED (0B raw, 492B fallback envelope)
- **Effective n:** 2 engines responded substantively. Confidence on cross-engine consensus
  must be reduced one notch (e.g. HIGH→MEDIUM) on any item where only one engine spoke.

## Per-question consensus

| Q | deepseek | xai | kilo | Convergence |
|---|----------|-----|------|-------------|
| Q1 weakest claim | "all engines produce auditable, timestamped reasoning traces" — only 3/16 deepseek calls have a trace | "95% consensus reliability across asset classes" lacks empirical backing | — | **CONVERGE** on audit-trail incompleteness; both flag the same missing signals (timing, retries, model fingerprint). Different specific claim cited but same root cause. |
| Q1 audit sufficient | false | false | — | CONVERGE: false |
| Q2 least valuable | "run-007 (FOREX_DEEP_DIVE turn 3-4)" | "run-2023-10-15-03" (likely fabricated id) | — | **PARTIAL.** deepseek cites a real run id from `RUNS_LOG`; xai's id is suspicious (date format mismatches the repo's). Treat xai's specific run-ids as low-trust. |
| Q2 redundant followups | FOREX_DEEP_DIVE turn 3, BOND turn 4 | FOREX_DEEP_DIVE turns 3-4 | — | CONVERGE: FOREX_DEEP_DIVE late turns added no signal. |
| Q3 personas verdict | wire-in | wire-in | — | **CONVERGE: wire-in.** Neither argues for keep-as-reference or drop. |
| Q4 weakness | no automated arbitration; merge-captain summarizes but can't break ties | merge-captain lacks escalation criteria; operator is bottleneck | — | CONVERGE on the structural gap. |
| Q4 proposal | 3-tier: confidence-weighted vote → devil's advocate round → meta-engine arg-quality scoring | weighted vote by reliability score from `_calls.jsonl` + designated tiebreaker engine | — | **PARTIAL CONVERGE.** Both want weighted voting but disagree on weight source (self-reported confidence vs. historical reliability). See Open Questions. |
| Q5 overrelied | deepseek (16/28 = 57%) | deepseek (16 calls) | — | CONVERGE. |
| Q5 underused | fast-cheap, consensus-3, claude-haiku | fast-cheap, consensus-3 | — | CONVERGE. (Note: ironically *this* run finally used `consensus-3`.) |
| Q5 rotation | cost-aware scheduler with task-complexity rubric; reserve deepseek for high-complexity | round-robin with per-engine daily cap (10 calls); cheap presets default for first round | — | **DIVERGE in mechanism.** Both agree something must throttle deepseek; deepseek wants quality-routed, xai wants quota-routed. |

## Top 5 improvements (ranked)

Aggregated from `q6_improvements` across both engines. Rank = (engine agreement) × (effort^-1) × (payoff signal).

| Rank | id | Title | Files | Effort | Payoff | Risk | Why this rank |
|------|----|-------|-------|--------|--------|------|---------------|
| 1 | imp-A | **Wire personas into engine calls** (persona_selector dispatch step) | `tools/swarm/swarm_run.py`, `tools/swarm/agent_personas/INDEX.md`, `tools/swarm/SPEC.md` | M | Converts authoring sunk-cost into operational lift; both engines independently called this out as the highest-leverage change. | Latency from long persona prompts; mitigate via top-2 selector + caching. | Both engines agree (deepseek's imp-1, xai's imp-2). High-confidence fix to a documented orphan. |
| 2 | imp-B | **Enforce audit-trail completeness** (mandatory timing, retry count, model fingerprint, token usage in `_calls.jsonl`) | `tools/swarm/swarm_log.py`, `tools/swarm/METHODOLOGY.md`, `tools/swarm/SPEC.md` | S | Closes claimed-vs-actual auditability gap at minimal cost; unblocks downstream cost analysis and reliability-weighted voting (imp-C). | Trivial (~50ms/call metadata). | Cheap, prerequisite for imp-C, both engines agree. |
| 3 | imp-C | **Automated disagreement resolution** (confidence-weighted voting + devil's-advocate round + meta-engine arg-quality scoring) | New `tools/swarm/resolver.py`, `tools/swarm/SPEC.md`, `swarm_runs/DISAGREEMENT_RESOLUTION.md` | L | Eliminates operator from ~80% of persistent splits (BOND case). | Verbose engines may game evidence scoring; cap argument tokens. | Highest payoff but largest effort + dependent on imp-B (needs reliability signal); both engines agree on the gap. |
| 4 | imp-D | **Cost/quota-aware engine scheduler** (cap deepseek share, default to fast-cheap for round-1 consensus, force consensus-3 rotation) | New `tools/swarm/scheduler.py`, `tools/swarm/swarm_run.py` | M | Breaks 57% deepseek concentration; both engines flag overreliance. | Quota cap may starve high-complexity tasks of best engine. | Engines diverge on mechanism (rubric vs round-robin) — needs design pass before build. |
| 5 | imp-E | **Followup-redundancy detector** (kill late turns that produce identical conclusions to prior turn, e.g. FOREX_DEEP_DIVE t3/t4) | `tools/swarm/swarm_followup.py`, `tools/swarm/SPEC.md` | S | Both engines independently flagged the same wasted turns; cheap diff-on-conclusions check would have saved them. | False positives if engines paraphrase same point. | Small effort, both engines validated the symptom; minor compared to imp-A/B/C. |

## Open questions (engine divergence)

1. **Voting weight source.** deepseek wants weights from each engine's *self-reported* confidence
   per call; xai wants weights from *historical* reliability stored in `_calls.jsonl`. These can
   conflict — a confidently-wrong engine wins under deepseek's scheme. **Resolution path:** combine
   them (multiplicative: `weight = self_conf * historical_ok_rate`).
2. **Engine rotation mechanism.** deepseek proposes a task-complexity rubric (route by problem),
   xai proposes a hard daily cap (route by budget). These imply different scheduler designs.
   Probable answer: hard cap as floor + rubric for routing within cap.
3. **xai cited run id `run-2023-10-15-03` not present in `RUNS_LOG.md`.** Possible mild
   fabrication — flagged but not load-bearing because deepseek's run citation (FOREX_DEEP_DIVE
   turn 3-4) is independently confirmable in the log. Lowers xai's confidence-weight one notch
   for this run.
4. **kilo silent failure.** Took 231s and returned ZERO bytes. Not a model error — a CLI/transport
   issue. The audit trail does not currently distinguish "engine refused" vs "engine answered but
   transport dropped output" vs "engine timed out". This is itself a finding for imp-B.

## Action items

- [ACTION] Wire personas: add a `--persona` flag (or auto-selector) to `tools/swarm/swarm_run.py`
  that injects the chosen persona's system prompt before dispatching to engines. Cmd:
  `grep -n "system_prompt" tools/swarm/swarm_run.py` to find the injection site.
- [ACTION] Enrich `_calls.jsonl` with `latency_s`, `retry_count`, `model_fingerprint`,
  `tokens_in`, `tokens_out`, and `transport_status` (ANSWERED/REFUSED/TIMEOUT/DROPPED).
  Cmd: `grep -n "jsonl" tools/swarm/swarm_log.py`.
- [ACTION] Build `tools/swarm/resolver.py` with weighted-vote primitive
  `weight = self_conf * historical_ok_rate`. Cmd: stub the module, ship behind opt-in flag
  `--auto-resolve` on `swarm_run.py`.
- [ACTION] Add followup-redundancy guard to `tools/swarm/swarm_followup.py`: if turn N's
  consensus JSON normalises to the same hash as turn N-1, refuse turn N+1 with
  `[swarm-followup] STOP: no delta vs prior turn`. Cmd:
  `grep -n "def main" tools/swarm/swarm_followup.py`.
- [ACTION] Investigate kilo silent failure (0B raw after 231s in this run). Compare
  `swarm_runs/_sessions.db` row for session `e85d61e9-ec12-4ede-aec2-edca7608404b` against a
  known-healthy kilo session. Cmd:
  `python -c "import sqlite3;c=sqlite3.connect('swarm_runs/_sessions.db');print(list(c.execute('select * from sessions where session_id=?',('e85d61e9-ec12-4ede-aec2-edca7608404b',))))"`.
- [ACTION] Cap deepseek share at <=40% of fanout calls. Quick first cut: when generating a fanout
  engine list in `swarm_run.py`, if `engines.count("deepseek") / len(engines) > 0.4`, swap one
  for `xai` or `inception`. Cmd: `grep -n "engines" tools/swarm/swarm_run.py | head -30`.
- [ACTION] Investigate red-team failure: claude opus returned non-JSON in this run despite
  `--red-team` working in prior runs. Check `redteam.json.raw.txt` size (0B here). Cmd:
  `python tools/swarm/swarm_inspect.py swarm_runs/self_review_20260503T163857Z`.
- [ACTION] Document persona-wiring decision in `tools/swarm/agent_personas/INDEX.md` so
  the next agent doesn't re-author orphans. Cmd: edit `INDEX.md` to add a "Status: orphan
  pending wire-in (imp-A)" header.
- [ACTION] Add `consensus-3` and `fast-cheap` preset usage tracking to `swarm_stats.py` so we
  can verify rotation-fix landed. Cmd: `grep -n "preset" tools/swarm/swarm_stats.py`.

## Methodology bug surfaced?

**Yes (one moderate).** The METHODOLOGY.md claim that the swarm produces "auditable, timestamped
reasoning traces" is materially weaker than advertised: per deepseek's review, only 3/16 deepseek
calls in today's logs carry a reasoning trace, and `_calls.jsonl` does not record retry counts,
model fingerprints, transport status, or token usage. This is a documentation/implementation
mismatch — the audit trail can demonstrate that *a call happened* but cannot, in its current
shape, falsify subtle fabrications (e.g. xai's run-id `run-2023-10-15-03` mentioned above would
not surface as a flag automatically). imp-B closes this.

The kilo silent failure (231s wall-time, 0B output) is a related symptom — the current trail
can't tell us *why* it failed. Same fix pattern.
