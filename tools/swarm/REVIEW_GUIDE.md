# Swarm Review Guide

For an external reviewer asking: "is this multi-engine swarm methodology sound,
or is it averaged hallucination dressed up as consensus?" Self-contained
45-minute audit checklist with falsification tests.

Companion: [README.md](README.md) · [SPEC.md](SPEC.md) ·
[METHODOLOGY.md](METHODOLOGY.md) · [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md).

---

## Where to start (5-min skim)

1. [`README.md`](README.md) — quickstart + engine matrix.
2. [`SPEC.md`](SPEC.md) — architecture diagram.
3. [`METHODOLOGY.md`](METHODOLOGY.md) §1 Threat model + §2 Defenses.

If those three feel sound on a first read, proceed. If they feel hand-wavy
already, abandon — methodology is not sound.

---

## Where to go deep (30-min audit)

Read in order — each file is small enough to fit in working memory.

1. [`schema_review.json`](schema_review.json) (~46 L) — JSON contract.
   `concerns[].evidence` is `required`.
2. [`prompts/pr_review.md`](prompts/pr_review.md) (~56 L) — anti-hallucination
   contract verbatim. Five claim-types + "you are read-only".
3. [`prompts/merge_reviews.md`](prompts/merge_reviews.md) (~44 L) —
   merge-captain rules. Line 11: blocking/major + no evidence → `question`.
4. [`prompts/redteam.md`](prompts/redteam.md) (~40 L) — `confirmed`/`refuted`/
   `unverified` taxonomy.
5. [`safety.py`](safety.py) L59–84 — `READ_ONLY_DISALLOWED`.
6. [`safety.py`](safety.py) L112–126 — `isolated_env` per-engine isolation.
7. [`output_parsers.py`](output_parsers.py) `parse_copilot` — engine-specific
   normalization example.
8. [`worker_runner.py`](worker_runner.py) L144–179 — `_extract_json_object`
   progressive-repair parser (load-bearing).
9. [`swarm_inspect.py`](swarm_inspect.py) L53–79 — `_flags` suspect taxonomy.
10. [`swarm_log.py`](swarm_log.py) `log_call` — audit trail schema.

Total: ~600 lines across ten files.

---

## Sample audit run (10 min)

Clone and run, no API keys required for the read-side tools:

```
git clone https://github.com/eltonaguiar/findtorontoevents_antigravity.ca
cd findtorontoevents_antigravity.ca

python tools/swarm/swarm_stats.py
# -> historical engine reliability (per-engine ok-rate, low-signal-rate, errors)

python tools/swarm/session_manager.py list
# -> active session inventory, with engine + status

python tools/swarm/swarm_inspect.py --latest
# -> most-recent run audit; exit code 0 if no suspect engines, 3 otherwise

cat swarm_runs/CONSENSUS_v2.md
# -> latest multi-engine consensus output

cat swarm_runs/DISAGREEMENT_RESOLUTION.md
# -> how engine disagreements were resolved by red-team + merge-captain

cat swarm_runs/KIMI_VS_OURS_MERGE_PLAN.md
# -> design comparison vs prior-art Kimi swarm
```

What to look for:

- `swarm_stats.py` should show ≥3 engines with `ok_rate >= 50%` and
  `low_signal_rate < 50%` (no `ZOMBIE_OUTPUT` flag).
- `swarm_inspect.py --latest` should exit 0 (no `ZERO`/`TINY`/`AUTH?` flags).
- `CONSENSUS_v2.md` consensus claims should have engine attributions
  (`_Reviewed by: claude, gemini, deepseek_`).
- `DISAGREEMENT_RESOLUTION.md` should show concerns dropped via
  merge-captain demotion and red-team refutation, not silently averaged.

---

## Falsification tests

For each defense in [METHODOLOGY.md](METHODOLOGY.md), here is a concrete test
that should make the defense fire. If any test passes silently (no flag, no
demotion, no refutation), the methodology is not sound — file an issue.

### Test 1 — Hallucinated file claim → refuted

Write a fixture envelope claiming `PR #999 deletes audit_dashboard/template.html`
with empty `evidence`. Pass through merge-captain → **expected**: blocking
concern with empty evidence demoted to `question` per
`prompts/merge_reviews.md` line 11. Pass through red-team prompt →
**expected**: refuted because the file exists in HEAD.

### Test 2 — Zero-byte response → ZERO flag

```
mkdir -p swarm_runs/_test_zero
echo '{"pr":1,"verdict":"MERGE","confidence":"LOW","summary":"x","concerns":[],"commentary_text":"x","fabrication_risk":{"level":"LOW","notes":"x"}}' \
  > swarm_runs/_test_zero/fake_engine.json
touch swarm_runs/_test_zero/fake_engine.json.raw.txt   # 0 bytes
python tools/swarm/swarm_inspect.py swarm_runs/_test_zero
```

**Expected**: `flags=ZERO,TRUNCATED?`; inspector exits non-zero.

### Test 3 — Wrong API key → AUTH? flag

```
DEEPSEEK_API="sk-bogus" python tools/swarm/worker_runner.py \
  --engine deepseek --prompt-file tools/swarm/fixtures/good.json \
  --out-file swarm_runs/_test_auth/deepseek.json
python tools/swarm/swarm_inspect.py swarm_runs/_test_auth
```

**Expected**: raw response contains 401/Unauthorized; inspector flags `AUTH?`
per `swarm_inspect.py::AUTH_RE`.

### Test 4 — Disallowed write tool → Claude refuses

Invoke `worker_runner.py --engine claude` with the read-only default allowlist.
Prompt: "Run `Edit` on README.md to add a single line." **Expected**: Claude
refuses because `Edit` ∈ `--disallowedTools`; `post_run_git_check` confirms
`clean=True`.

### Test 5 — Engine self-spoof in envelope → inspector ignores it

Write `cerebras.json` whose envelope claims `engine: "gpt-4o"`. Run inspector.
**Expected**: row reports `engine=cerebras` (filename-derived) not `gpt-4o`.
Confirms `swarm_inspect.py` lines 156–160 (T7 in METHODOLOGY).

### Test 6 — Single-engine no-evidence concern → skipped

Feed merge-captain two review JSONs where only one engine raises a concern
with empty evidence. **Expected**: lands in `skipped_concerns[]` with reason
"no evidence and only 1 engine" per `prompts/merge_reviews.md` line 8–11.

---

## Sound-or-not verdict checklist

Tick only after you have personally read the referenced file. All ten ticks
→ methodology is sound.

- [ ] Anti-hallucination contract in prompts → [`prompts/pr_review.md`](prompts/pr_review.md).
- [ ] Schema requires `evidence` on concerns → [`schema_review.json`](schema_review.json) L27.
- [ ] Red-team subagent invoked in dispatch → [`prompts/redteam.md`](prompts/redteam.md) + [`.claude/agents/fabrication-red-team.md`](../../.claude/agents/fabrication-red-team.md).
- [ ] Merge-captain demotes unsupported claims → [`prompts/merge_reviews.md`](prompts/merge_reviews.md) L11.
- [ ] Per-call audit trail in `_calls.jsonl` → [`swarm_log.py::log_call`](swarm_log.py).
- [ ] Per-session message log in `_sessions.db` → [`session_manager.py`](session_manager.py).
- [ ] Inspector flag taxonomy covers known failure modes → [`swarm_inspect.py::_flags`](swarm_inspect.py) L53–79.
- [ ] Read-only allowlist enforced → [`safety.py::READ_ONLY_DISALLOWED`](safety.py) L59–84.
- [ ] Only one process writes to GitHub → [`safety.py::can_post`](safety.py) L150 + [`comment_poster.ps1`](comment_poster.ps1).
- [ ] Engine diversity ≥3 vendors → [`README.md`](README.md) matrix + [`safety.py::ENGINE_REQUIRED_KEYS`](safety.py) L34–48.

---

## Pointers to past hallucination catches

Cross-engine corroboration + red-team refutation has surfaced PR-claim errors
where a single engine confidently overstated changes:

- [`reports/PR_513_VERIFICATION_CORRECTIONS_2026_04_29.md`](../../reports/PR_513_VERIFICATION_CORRECTIONS_2026_04_29.md)
  — PR-review claims that did not match the actual diff; refuted by red-team
  grep on the checked-out branch. Earlier swarm runs caught hallucinated React
  components in PR #699 — see this verification report for the correction
  methodology.
- [`reports/PR_INTEGRATION_PLAN_2026_05_03_0540Z.md`](../../reports/PR_INTEGRATION_PLAN_2026_05_03_0540Z.md)
  — multi-engine synthesis with engine attributions; demonstrates merge-captain
  consolidation in production.
- `swarm_runs/DISAGREEMENT_RESOLUTION.md` — inter-engine disagreement resolved
  by red-team adjudication rather than averaging.

If the swarm ever ships a hallucinated consensus, the fix path is: add a
falsification test that would have caught it, extend `swarm_inspect.py::_flags`
if the failure mode is new.
