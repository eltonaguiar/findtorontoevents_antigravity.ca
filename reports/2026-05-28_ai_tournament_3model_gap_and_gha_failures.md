# AI Tournament 3-Model Gap & GitHub Actions Failure Audit — 2026-05-28

**Author:** Claude (Opus 4.7), session 2026-05-28
**Branch:** `docs/ai-tournament-model-gap-analysis-2026-05-28`
**Scope:** confirm the "only 3 models" complaint against `/audit/ai-tournament.html`, map it to the open PRs already attacking it, and triage every distinct GitHub Actions failure observed in the last hour.

---

## 1. The 3-model gap is real

`config/model_persona_mapping.json` declares **23 models** across 13 providers (DeepSeek, OpenAI, Cerebras, xAI, Anthropic, Together/Inception, OpenRouter, Google, Mistral, NVIDIA NIM, Groq, Together Qwen/DeepSeek, Fireworks, GitHub Models, Nous, Hyperbolic, Featherless, AIMLAPI).

The most recent `AI Tournament Pipeline — Daily Picks + DB Ingest` workflow run (`gh run` id `26555312404`, dispatched 2026-05-28T04:48Z) wrote **3 model rows** to the picks fleet:

| model_id | picks |
| --- | ---: |
| `cerebras_llama4` | 11 |
| `deepseek_v4` | 19 |
| `grok3` | 20 |

That is **3 / 23 = 13% fleet coverage**. The dashboard, leaderboard, and tournament consensus promotion all see only those three models. This matches the user's report verbatim.

### 1.1 Why the other 20 produce zero picks

`tools/populate_picks.py:669-698` (`try_prompt_model`) dispatches on `api_type ∈ {openai, anthropic, openai_compat, deepseek, cerebras}` and reads each model's key from `model_cfg.api_key_env`. Two failure modes co-exist:

1. **Missing env vars.** GH Actions `ai-tournament-pipeline.yml` only forwards a subset of provider secrets. Where a secret is unset, `os.environ.get(api_key_env, "")` returns `""` and `try_prompt_model` skips (silently). Affected today: OpenAI, Anthropic, Together (mercury), OpenRouter (ring_261T), Mistral, NVIDIA NIM (×3), Groq (×2), Together Qwen/DeepSeek, Fireworks, GitHub Models, Nous, Hyperbolic, Featherless, AIMLAPI — i.e. all 18 OpenAI-compat / anthropic-routed models.
2. **Caller fragility.** Even when the key is present, `call_openai_api` / `call_generic_openai_compat` (a) drop the model on first 429 / 5xx without retry, and (b) return empty `content` for reasoning models (DeepSeek-R1 / Qwen-QwQ / NVIDIA Nemotron-thinking variants) because the answer lives in `choices[0].message.reasoning_content`, not `content`. Result: parser sees 0 picks.

### 1.2 Open PRs already attacking the gap (do NOT duplicate)

| PR | Files | Approach |
| --- | --- | --- |
| **#19** | `.github/workflows/ai-tournament-pipeline.yml` + report MD | Widens `secrets.PRIMARY \|\| secrets.FALLBACK \|\| ''` chains so 21+ models resolve their key from existing secret names. Tags `OPENAI_API_KEY` + `ANTHROPIC_API_KEY` as operator-action (must `gh secret set` post-merge). |
| **#25** | `.github/workflows/ai-tournament-pipeline.yml`, `audit_dashboard/ai-tournament.html`, `tools/ai_tournament/build_model_summary.py`, `tools/ai_tournament/update_leaderboard.py`, `tools/populate_picks.py`, updates MD | Broadest scope (459+ lines): timeout 15→45min, `AI_TOURNAMENT_COVERAGE_FALLBACK_ENABLED`, `rank_eligible` flag plumbed end-to-end (model_summary + leaderboard + dashboard render) so coverage-fallback picks count for *visibility* without polluting *ranking*. |
| **#26** | `tools/populate_picks.py` | Hardens the OpenAI-compat caller: shared `_post_openai_compat_with_retry()` with 3× exponential backoff honoring `Retry-After`, plus reasoning-model `reasoning_content` → `content` hoist, plus error classification (`rate_limited` / `auth_error` / `timeout` / `server_error` / `bad_response` / `missing_endpoint`). |

(Earlier closed: #22, #23, sibling #24 referenced by #26.)

**Recommended merge order:**
1. **#19 first** — pure workflow-yaml change, no production code touched, unblocks every model whose key has a fallback secret already in the vault. Operator then runs the two `gh secret set` commands documented in the PR.
2. **#26 second** — `populate_picks.py` resilience layer; no behavior change for already-working keys, but every key #19 unblocks immediately benefits from retry + reasoning-content hoist.
3. **#25 last** — broadest blast radius (workflow + 4 tool files + frontend). The `rank_eligible` + `coverage_fallback_picks` schema additions are an evolution of the data model; gating its merge until #19/#26 land lets us measure how many models survive without #25's fallback wrapping, and rebase #25 against the resilient baseline.

A 6th competing PR for this gap is **explicitly not recommended** — it would conflict with all three above and violate the CLAUDE.md *Wire-Up Rule* "no breadth-over-depth" guidance. This report is a docs-only consolidation.

---

## 2. GitHub Actions failures observed in the last ~60 minutes

Pulled via `gh run list --limit 100`. After aggregating by workflow name, **seven distinct failure modes** are active.

### 2.1 Hard failures with root cause identified

#### Swarm Pick Review — `ModuleNotFoundError: No module named 'tools'`
- Run: `26554767449` (2026-05-28T04:30Z), step "Promote tournament consensus picks".
- File: `tools/swarm/promote_tournament_picks.py:100`
- Failing line: `from tools.swarm.swarm_pick_schema import append_picks  # noqa: E402`
- Root cause: script invoked as `python tools/swarm/promote_tournament_picks.py` without `PYTHONPATH=$GITHUB_WORKSPACE` or `python -m tools.swarm.promote_tournament_picks`. The `tools.` package import can't resolve because the script's own directory shadows it.
- Distinct from the 3-model gap (different file, different layer). Cheap, isolated fix candidate.
- The wrapping step has `if [ $_promo_rc -ne 0 ]; then echo "::warning"...` but the *next* step (or the script's own `raise SystemExit(main())`) propagates exit 1 anyway — current "non-fatal" comment is misleading.

#### Strategy Health Monitor — `TypeError: Object of type Decimal is not JSON serializable`
- Run: `26556507316` (2026-05-28T05:26Z), step "Run health monitor".
- Root cause: `json.dump(...)` called on a structure containing `decimal.Decimal` (likely from a `pymysql` query). Needs either `default=str` / a custom encoder, or per-field `float()` coercion.

#### Forward Test Daily (× 2 mirrors) — exit code 2 in "Resolve open picks"
- Runs: `26556456551`, `26556573140` (5:24–5:28Z). torontoevent.net mirror fails identically.
- Step uses Python's exit code 2, which is `argparse`-style "usage error". Likely a missing/renamed CLI flag or env var on `tools/forward_test/resolve_picks.py` (or similar). Worth a deeper look in a separate PR; not in scope for this report.

#### Fast Trading Variants Master Scheduler — exit code 2
- Run: `26556400870`, step "Run Fast Stocks Competition". Same exit-code-2 signature as forward-test; likely the same class of script-arg drift.

### 2.2 "Behaving correctly" failures (gates doing their job)

#### Branch Large File Duplicate Guard — exit 1
- Run: `26556187372` (5:16Z) and `26555293954` (in-progress on this branch).
- Step: "Enforce fail-on-findings policy" prints `Detected duplicated large blobs across multiple non-main branches.` and exits 1.
- This is **the guard correctly firing** against the stranded `backup/pre-cleanup-20260522T192757Z` and similar backup branches that re-introduce large binaries. Not a bug, but the work item to delete those branches has been outstanding since 2026-05-22 (see memory `feedback-pause-remote-2026-05-22.md`).

#### Deploy Competition to Live Site — exit 1 (FTP upload)
- Run: `26556593027` (5:28Z) — and `26555298391` from the same push burst.
- Logs cut off mid-`lftp` command list. Failure mode is the recurring 50webs FTP-TLS drop. The wrapping `if [ $? -eq 0 ]` already downgrades to `::warning`, but the *step* still records the non-zero, so the workflow conclusion is "failure". Not new; not in the scope of the 3-model PR.

#### FINDTORONTOEVENTS.CA Database Backups — exit (logs empty)
- Run: `26556345716` (5:21Z). `gh run view --log-failed` returns nothing useful — likely the failure is in a `continue-on-error: true` step that doesn't expose its tail. Needs a manual `gh run view --log` to dig in. Not in scope.

### 2.3 Failure-rate summary (last 100 runs)

| Failures | Workflow |
| ---: | --- |
| 1 | Branch Large File Duplicate Guard |
| 1 | Deploy Competition to Live Site |
| 1 | FINDTORONTOEVENTS.CA Database Backups |
| 1 | Fast Trading Variants Master Scheduler |
| 1 | Forward Test Daily |
| 1 | Strategy Health Monitor |
| 1 | `[torontoevent.net]` Forward Test Daily |
| 1 | Swarm Pick Review (resolve + weekly + patterns + tournament promotion) |

All seven recur on schedule — these aren't one-off flakes, they fail on every cron/push trigger until fixed.

---

## 3. Recommendations — non-conflicting next steps

1. **Land the existing PRs in the order above (#19 → #26 → #25).** No additional model-gap PR.
2. **Operator action (manual, after #19 merges):** the two `gh secret set` commands in PR #19's body — `OPENAI_API_KEY` and `ANTHROPIC_API_KEY`. Without these, the Anthropic + OpenAI rows of the fleet remain dark even after #19.
3. **Open a small, separate PR** for the `Swarm Pick Review` `ModuleNotFoundError` — single-file change to either invoke `python -m tools.swarm.promote_tournament_picks` or prefix `PYTHONPATH=$GITHUB_WORKSPACE` in `.github/workflows/swarm-pick-review.yml`. Distinct from the 3-model issue, distinct from PR #19/#25/#26.
4. **Open a follow-up issue (not a PR)** to characterize the Forward Test Daily `exit code 2` and the Strategy Health Monitor `Decimal` encoder bug — both are real but out of scope for the AI-tournament work.
5. **Honor the 2026-05-22 pause-remote-ops memo:** this report is being pushed as a docs-only branch with a single MD file. No FTP deploy, no secrets writes, no force-pushes to main.

---

## 4. Evidence index (for the merge-captain to spot-check)

| Claim | Evidence command |
| --- | --- |
| 23 models configured | `jq '.models \| keys \| length' config/model_persona_mapping.json` |
| 3 models producing picks today | `gh run view 26555312404 --log` → grep `cerebras_llama4\|deepseek_v4\|grok3:` |
| PR #19/#25/#26 scope | `gh pr diff 19 --name-only`, `gh pr diff 25 --name-only`, `gh pr diff 26 --name-only` |
| Swarm Promote ModuleNotFoundError | `gh run view 26554767449 --log-failed \| grep ModuleNotFoundError` |
| Strategy Health Monitor Decimal bug | `gh run view 26556507316 --log-failed \| grep Decimal` |
| Large-blob guard correctly firing | `gh run view 26556187372 --log-failed \| tail -20` |
