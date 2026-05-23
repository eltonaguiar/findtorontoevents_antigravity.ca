# tools/swarm — Post-run options

After any swarm run (`swarm_run.py`, `swarm_dispatch.ps1`, or
`swarm_followup.py`), the dispatcher prints a short "NEXT STEPS" footer to
stdout. This doc is the long form of that footer: every flag, every flow,
every "I should re-run / resume / refine" decision.

If you only want the cheat sheet, look at the footer. If you're staring at
a borderline-consensus run and wondering what to do next, read sections
8 + 11 below.

---

## 1. Inspecting the run

```
python tools/swarm/swarm_inspect.py --latest
python tools/swarm/swarm_inspect.py swarm_runs/run_<TS>
```

Per-engine flags from [`swarm_inspect.py`](swarm_inspect.py): `HEALTHY`
(>=1KB, parses) / `SHORT` (<1KB) / `TINY` (<200B) / `ZERO` (no output) /
`CREDITS?` / `AUTH?` (401/403) /
`PARSE_FAILED` (stub envelope) / `TRUNCATED?` (ends mid-token).

Drill into raw bytes via `<engine>.json` + `<engine>.json.raw.txt`
(pre-parse stdout) under the run dir.

Historical engine reliability across runs:
[`swarm_stats.py`](swarm_stats.py) surfaces `ZOMBIE` / `LOW_OK_RATE` /
`ERRORING` flags.

```
python tools/swarm/swarm_stats.py
python tools/swarm/swarm_stats.py --since 2026-05-03 --json
```

---

## 2. Re-running with stronger contract

When the first pass didn't converge — or you want the strongest
adversarial check — re-run with these knobs.

- `--red-team` — opt-in claude opus refutation pass over the merged
  worker outputs. Cost ~$0.05-0.20 (opus is the priciest engine in the
  fleet). Writes `redteam.json` + `_redteam_input.json` /
  `_redteam_prompt.md` into the same run dir.
- `--strictness {strict,lenient,off}` — tightens or loosens the
  evidence-minLength enforcement in
  [`schema_validate.py`](schema_validate.py). Default `strict` rejects
  picks with empty `evidence` strings. Use `lenient` for early
  exploratory turns where you want signal even when contracts slip.
- `--json-strict` — wraps the prompt with the strict-JSON-only preamble
  for engines that ignore in-prompt contracts (gemini in particular).
- `--persist-sessions` — writes a session row per engine to
  `swarm_runs/_sessions.db` so later turns can `--from-session`.

YAML equivalents (top-level keys): `red_team: true`, `json_strict: true`,
`strictness: strict`. CLI flags always win on conflict.

---

## 3. Multiple iterations

Three orthogonal ways to "go again":

### Single-engine resume

```
python tools/swarm/worker_runner.py --engine deepseek \
    --from-session <sid> --prompt-file followup.md \
    --out-file swarm_runs/_retry/deepseek.json --persist-session
```

Routes (auto-selected by [`worker_runner.py`](worker_runner.py)):
1. **Native** — claude `--resume`, openclaude `--resume`, kimi `--resume`.
2. **API JSONL replay** — deepseek/xai/cerebras/inception/ollama_cloud:
   reads the prior `_calls.jsonl` for that session and replays as
   `messages[]` history.
3. **MD-context fallback** — for engines without native resume, prepends
   the prior assistant body as a `## Previous turn` block to the new
   prompt.

### Multi-engine resume

```
python tools/swarm/swarm_run.py --config <yaml> \
    --from-session-by-engine deepseek=<sid>,xai=<sid>
```

Each engine listed gets resumed; engines not in the map start fresh.
Resumed engines auto-set `--persist-session` so the chain can continue.

### Multi-turn chain

[`swarm_followup.py`](swarm_followup.py) runs N turns through one engine,
each using the prior turn's session via `--from-session`.

```
python tools/swarm/swarm_followup.py \
    --config tools/swarm/examples/forex_deep_dive.yaml
```

YAML declares `turns:` (priming → analysis → critique → final). Turn 1
starts a fresh session; turns 2..N auto-resume.

### Disagreement-resume pattern

When the merge plan has dissenters, target them specifically:

1. Open `final_merge_plan.json`, identify the dissenting engine + its
   specific objection.
2. Build a 1-2 paragraph follow-up prompt asking that engine to either
   defend its claim with evidence OR concede.
3. `worker_runner.py --engine <eng> --from-session <sid> --prompt-file <followup.md>`.
4. Append the response back into the dossier.

The proven template lives in
[`swarm_runs/DISAGREEMENT_RESOLUTION.md`](../../swarm_runs/DISAGREEMENT_RESOLUTION.md)
— used today on the asset-class question and worth copying.

---

## 4. Persona conditioning

`--persona <NAME>` prepends a specialist persona contract to the prompt.
Visibly shapes responses (specialists cite their domain conventions,
quote relevant tier thresholds, etc.).

```
python tools/swarm/swarm_run.py --prompt-file q.md \
    --engines deepseek,xai --persona crypto_specialist
```

Available personas live in
[`tools/swarm/agent_personas/INDEX.md`](agent_personas/INDEX.md):
asset-class specialists (`bond`, `commodity`, `crypto`, `equity`, `etf`,
`forex`), plus `ml-validation-specialist` and `regime-specialist`.

Kimi-dim-inspired personas (added 2026-05-03, derived from the Kimi
Agent Swarm 12-dim prediction-edge audit — see `INDEX.md` for the dim
mapping):
`score-methodology-auditor` (dim02 — score correlation/monotonicity),
`cross-verification-auditor` (cross_verification + insight — HIGH/MEDIUM/LOW
claim classification),
`risk-of-ruin-assessor` (dim06+07+08 — penny/meme/lottery Kelly + ruin),
`rr-band-optimizer` (dim01 §8 + dim08 §1 — 1.5-2.0R sweet spot enforcement),
`transaction-cost-modeler` (dim05 §1 + dim12 — net-of-cost PF re-derivation).

YAML supports per-engine persona override — each engine in `engines:`
can declare its own `persona:`. Resolution precedence:

> per-engine YAML `persona:` > top-level YAML `persona:` > CLI `--persona` > none

Worker resolves the name as `<name>.md` > `<name>_specialist.md` >
absolute path.

---

## 5. Engine selection presets

Curated bundles you can pass as `--preset <name>` (or `preset:` in YAML).

| Preset | Members | When to use |
|---|---|---|
| `consensus-3` | deepseek, xai, kilo | Default consensus shape — cheap, fast, three independent vendors. |
| `fast-cheap` | cerebras, deepseek | Quick triage runs; both are sub-cent. |
| `deep-strict` | claude, kilo, deepseek | Critical / production-blocking questions. Includes a Sonnet vote. |
| `all-paid-api` | deepseek, xai, cerebras, inception, ollama_cloud | Max coverage; bypasses OAuth-CLI flakiness. |
| `all-cli` | claude, gemini, kilo, opencode, copilot | OAuth-only fleet (no API spend). |

Preset list also visible via `--list-engines`.

Per-engine model override:
- CLI: `--model <model-id>` applies to all engines that accept it.
- Per-engine in YAML: `engines: - name: deepseek\n  model: deepseek-reasoner`.
- Env: `{ENGINE}_MODEL` (e.g. `OPENROUTER_MODEL=anthropic/claude-haiku-4.5`).

---

## 6. Cost control

- `--cost-cap-usd FLOAT` (default `$1.00`) — aborts with rc=4 if the
  pre-dispatch estimate exceeds the cap. Breakdown lists per-engine
  cost so you can pick what to drop.
- `swarm_runs/_calls.jsonl` records realized `tokens_in`/`tokens_out`
  per call (post-imp-B). Use to recalibrate `COST_PER_1K_TOKENS`.
- `python tools/swarm/swarm_janitor.py --hours 168 --vacuum` cleans up
  old run dirs + sqlite. Scheduled via
  [`.github/workflows/swarm-janitor.yml`](../../.github/workflows/swarm-janitor.yml).

OAuth-bundled CLIs are $0. Estimate is APPROXIMATE for openrouter /
openclaude when routed to non-default providers — see SPEC.md.

---

## 7. Hooks and automation

- `--pre-hook CMD` — runs before any worker dispatches. Env: `SWARM_OUT_DIR`.
- `--post-hook CMD` — runs after summary. Env: `SWARM_OUT_DIR`,
  `SWARM_OK_COUNT`, `SWARM_TOTAL`.

Both advisory (non-zero rc warns, doesn't abort). `shell=True`, so chain
`cmd1 && cmd2` freely. **Don't pass untrusted input.** YAML equivalents:
`pre_hook:` / `post_hook:` (CLI wins).

Use cases: pipe inspector to file, git-diff the run dir, auto-post to
Slack on failure.

---

## 8. Major-issue multi-cycle pattern

When the first run produces split verdicts or low-confidence consensus,
escalate through cycles:

| Cycle | Action | Tool |
|---|---|---|
| 1 | Initial fan-out (3-5 engines). | `swarm_run.py --preset consensus-3` |
| 2 | Merge-captain consolidates + drops unverified claims. | `swarm_dispatch.ps1` (auto) or manual `worker_runner --engine claude --model opus` against `prompts/merge_reviews.md`. |
| 3 | Red-team: claude opus tries to refute every concern. | `--red-team` flag. |
| 4 | Resume each dissenter with a tight follow-up demanding evidence or concession. | `--from-session-by-engine eng1=sid1,eng2=sid2` |
| 5 | Multi-turn deep-dive on the strongest engine. | `swarm_followup.py --config <yaml>` |
| 6 | (Deferred — imp-C) Auto-disagreement resolver with confidence x reliability voting. | TODO; not shipped. |

Today's asset-class question went through cycles 1-4 before reaching
consensus on ETF/FOREX (BOND remains 3-2 split, operationally aligned).

---

## 9. PR-review-specific options

Only relevant to [`swarm_dispatch.ps1`](swarm_dispatch.ps1) (the PR
fan-out pipeline).

- `-Prs N1,N2,...` — comma-separated PR list.
- `-AutoResume` — scans `_sessions.db` for the most-recent active
  session per (PR, engine) within the last 72 h and reuses each one.
  Mutually exclusive with explicit `-FromSessionsByPr`.
- `-FromSessionsByPr` — manual hashtable map
  `@{ <pr-int> = @{ <engine> = '<sid>'; ... }; ... }`.
- `-PersistSessions:$false` — disable session persistence (default on).
- `-NoInlineCapture` — fall back to legacy "every worker runs gh"
  flow. Only safe for shell-capable CLI engines.
- `-PromptFile` — override the inline-diff template
  (`prompts/pr_review_inline.md`).
- `-SkipMerge` / `-SkipRedteam` — exit early.

After the review run completes, post comments via:

```
pwsh tools/swarm/comment_poster.ps1 -RunDir swarm_runs/<TS> -DryRun
pwsh tools/swarm/comment_poster.ps1 -RunDir swarm_runs/<TS>     # interactive y/N
```

---

## 10. GitHub Actions / failing-jobs review (deferred)

Not shipped today. Pattern would mirror `_pr_capture.py`:
- `prompts/gh_actions_review.md` template.
- Capture helper for `gh run list --status failure --json` + per-run
  log fetch.
- Embed log + JSON server-side into the prompt before fan-out.

Track in `tools/swarm/SPEC.md` deferred-imp list.

---

## 11. Common follow-ups by run-result pattern

| Pattern | Recommended next step |
|---|---|
| `ok_count < 50%` | `swarm_inspect --latest` -> diagnose flags -> re-run with different preset (often `all-paid-api`). |
| All `HEALTHY` but disagreement | `--red-team`, then `--from-session-by-engine` on each dissenter with a targeted question. |
| Single engine `ZOMBIE` | Re-run that engine alone with `--debug` + raw stderr capture. |
| `AUTH?` flag | Check the env key for that engine; relogin OAuth (e.g. `claude /login`). |
| `CREDITS?` flag | Check engine billing. Drop engine from preset until topped up. |
| Cost-cap aborts (rc=4) | Lower preset or raise `--cost-cap-usd`, not blind re-run. |
| Schema validation fails for ALL engines | Prompt is broken, not engines — fix prompt first. |
| Single-engine `PARSE_FAILED` | Worker fell back to stub envelope; check `.raw.txt` to see if the engine returned prose. Add `--json-strict` for that engine. |

---

## 12. When NOT to re-run

- **Unanimous consensus on the same evidence.** Stop. Re-running burns
  tokens without changing the answer.
- **Cost-cap aborted.** Don't blindly raise the cap. Lower the preset
  or drop the priciest engine first.
- **All engines failed schema validation.** Fix the prompt before
  re-dispatching — the engines aren't broken if they all break the
  same way.
- **You haven't read the inspector output yet.** Don't re-run before
  you know what failed.

---

## See also

- [`README.md`](README.md) — quickstart + engine matrix.
- [`SPEC.md`](SPEC.md) — schema + slash-command contract.
- [`CHANGELOG.md`](CHANGELOG.md) — per-day commit log.
- [`SWARM_DESIGN_NOTES.md`](SWARM_DESIGN_NOTES.md) — architectural rationale.
- [`agent_personas/INDEX.md`](agent_personas/INDEX.md) — persona registry.
- [`swarm_runs/DISAGREEMENT_RESOLUTION.md`](../../swarm_runs/DISAGREEMENT_RESOLUTION.md)
  — disagreement-resume template.
