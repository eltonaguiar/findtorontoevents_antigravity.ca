# FREEBUFF chatlog — 2026-11-12 1959 UTC (chatlog dumped on request)

**Agent:** Buffy (Freebuff, DeepSeek V4.1 Flash Fast)
**Repo:** `eltonaguiar/findtorontoevents_antigravity.ca`
**Branch:** `scrub/inception-mercury-2026-11-12` @ `df2eadf054cb` (36 files)
**File:** `updates/2026-11-12-FREEBUFF-chatlog-1959UTC.md`
**Peer agent:** Ollama-Claude, coordinating through `/tmp/claude_ollama.txt` ↔ `/tmp/freebuff.txt`

---

## 1. Why this session happened

Inception Labs sunsets the Mercury API on **2026-12-28**. The owner asked where the key is
used across `github.com/eltonaguiar`, including `.github/workflows`, then authorised the
scrub. A second agent is extracting the swarm core into `eltonaguiar/SWARM_CONSOLIDATED`,
so the two had to agree on who owns which files.

Hard constraints carried through the whole session:

- `~/dbpasses.txt` must **not** be deleted. Its `INCEPTION_AI_KEY` entry stays; only the
  vendor dashboard can actually revoke a key.
- Never print secret values.
- Only push branches where every changed file is mine — the domain repo had 6,567 dirty
  paths from other agents, so a wildcard `git add` was never an option.
- Every fix gets an `.md` in `updates/` (repo rule).

## 2. Retiring the provider

Removed **outright**, in all six registries that carried it — no aliasing, because a dead
provider left as an alias is worse than no provider: it looks configured and fails at
runtime.

| Surface | File | Replacement |
|---|---|---|
| LiteLLM pin + key plumbing | `litellm_config.yaml`, `tools/start_litellm_proxy.sh` | — |
| swarm v1 | `tools/swarm/*` (`swarm_run.py`, `worker_runner.py`, `api_consult.py`, …) | cerebro/groq peers |
| swarm v2 | `tools/swarm_v2/swarms/core/llm_client.py` | — |
| ruflo | `.ruflo/orchestrator.py`, `.ruflo/wizard.py` | `reviewer` → `groq` |
| second-opinion skill | `.claude/skills/second-opinion/**` | cerebras / `gpt-oss-120b` |
| key tooling + roster | `tools/verify_all_keys.py`, `config/api_model_roster.json`, … | — |
| CI | `.github/workflows/research-orchestrator.yml`, `ai-tournament-pipeline.yml` | env var dropped |

Also scrubbed **`hermesbackup`** (separate repo, pushed as `875f448` on `master`): provider
block out of `config.yaml`, and `credential_pool["custom:api.inceptionlabs.ai"]` out of
`auth.json`. YAML and JSON both re-parsed afterwards. That scrub is cosmetic only — the
value still sits in git history until the key is revoked.

## 3. The bug the verification found

Five of the 21 free proxy groups were failing. Neither cause was "provider is dead":

**a) `ULTRA_FREE_CLOUD_TOOLS` → HTTP 401, and it was not about quota or NVIDIA.**
`tools/start_litellm_proxy.sh` looked for the label `OPEN ROUTER API KEY`, but
`dbpasses.txt` spells it `OPEN ROUTER API KEY (OPENROUTER)`. `parse_key` compares whole
lines, so the match failed, `OPENROUTER_API_KEY` was never exported, and all three
`openrouter/*:free` deployments 401'd. Blast radius was larger than one group: `TOOLS` is
the declared fallback for `NVIDIA` **and** `CLOUD_LARGE`, so three groups were quietly
degraded. Fixed the label, restarted via `litellm-4000.service` (readiness 200 after 34 s),
key present in the proxy environment.

**b) The four `ULTRA_FREE_LOCAL_*` groups were cold, not dead.**
All three Ollama models were installed; direct calls took 8.6 s / 3.7 s / 1.6 s and
timed out only under concurrent first-load. After warm-up every group answers.

**Result:** 21/21 free groups HTTP 200 (was 16/21).

### Calibration trap worth remembering

At `max_tokens=100`, `ULTRA_FREE_LOCAL_CHAT`, `ULTRA_FREE_LOCAL_CODE` and
`ULTRA_FREE_TOOLS` return **0 characters of `content`** and ~400–540 of
`reasoning_content`. They are healthy. Any health gate that only reads `content`, or that
caps `max_tokens` low, will mark live engines dead and — through a health-gated debate
mode — refuse to run for the wrong reason. Gate on `content` *or* `reasoning_content`, and
never set `max_tokens` below 300 for reasoning models.

## 4. Publishing, and why `git push` was not used

`git push` hangs on this repo: it stalls after `Pushing to github.com:...` and never
finishes pack enumeration, while SSH auth itself is fine (`ssh -T` → "Hi eltonaguiar") and
`ls-remote` returns instantly. Rather than keep waiting on a 40k-file pack negotiation,
the branch was published through the **Git Data API** — blobs → tree against
`base_tree=main` → commit → ref — then verified path by path with the contents API:

```
tip  df2eadf054cb
     updates/2026-11-12-freebuff-swarm-coordination-chatlog.md   7947 b
     updates/2026-11-12-inception-mercury-api-sunset-migration.md 8927 b
     tools/swarm/worker_runner.py                               58080 b
     .claude/skills/second-opinion/scripts/ask.py                6992 b
```

One commit on top of `main`. Not a force-push, not a history rewrite.

## 5. Peer coordination, and one collision avoided

Signals exchanged: **`DOMAIN_SCRUB_COMPLETE`** (fired at publish time) ↔ their
**`CORE_READY`**, which is still **not** met as defined — requirements + picker + clean
`core/worker.py` on `main`.

Verified on `origin/main` (`8d15148`, identical to `feat/v2-engine-extraction`):

- `requirements.txt` — PRESENT
- `cli/swarm_picker.py` — PRESENT
- `core/v2/` — PRESENT, 12 modules
- `REMAINING_TASKS.md` — **ABSENT**
- `core/worker.py` line 9 — **still lists `inception`**, despite commit `aa4a43e` being
  titled "fix worker docstring". `96a4471` or the merge restored the old text. Most likely
  the wrong file was edited: `tools/swarm/worker_runner.py` (domain, mine) carries the same
  engine listing as `core/worker.py` (core, theirs).

Their wiring spec targets three files that exist **only** on this branch —
`.ruflo/orchestrator.py`, `tools/swarm/swarm_run.py`,
`tools/swarm_v2/swarms/core/llm_client.py` (to delete). Patching or deleting them from
`main`'s copies would reverse the retirement. The instruction given: cut the wiring branch
from `df2eadf054cb`, not from `main`.

Also corrected two of my own earlier flags so they would not chase ghosts: ruflo's three
`reviewer` entries are three separate transport maps (openrouter / local / proxy), not a
bug; and swarm_v2's lone `inception` is a retirement comment, not a code path.

## 6. Alias contract handed to the core agent

36 groups, 19 of them `ULTRA_FREE`. Guaranteed stable:
`ULTRA_FREE_CLOUD_FAST`, `ULTRA_FREE_CLOUD`, `ULTRA_FREE_CLOUD_TOOLS`, `ULTRA_FREE_NVIDIA`,
`ULTRA_FREE_LOCAL_FAST`. Existing failover chains are left in place, e.g.
`CLOUD_FAST → CLOUD → CLOUD_LARGE → KILO/GEMINI/OPENROUTER`, `NVIDIA → CLOUD_TOOLS`.
Proxy-first is absolute: the core never parses `dbpasses.txt`. One inherited exception —
ruflo's openrouter map reads `OPENROUTER_FREE_KEY` directly.

## 7. Open items

**Owner only:** revoke the Inception key at the vendor dashboard (the only effective
action) · merge FREELLM PR #1 · decide the `mercury` tournament persona · **rotate the
OpenRouter key**, which surfaced once in terminal output while the label bug was being
diagnosed.

**Peer only:** fix `core/worker.py` line 9 · push `REMAINING_TASKS.md` · confirm which file
they actually edited · cut the wiring branch from the scrub commit.

**Mine:** one real end-to-end smoke per swarm type. Import-level and CLI-level checks pass
(v1 `PROVIDERS` clean, `swarm_run.py --help` exit 0, 8 presets intact, a live
`ULTRA_FREE_CLOUD_FAST` call answered) — but **no full swarm run has been executed**, so
none of them is claimed as "working" yet.

## 8. Reproduction

```bash
systemctl --user restart litellm-4000.service
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:4000/health/readiness   # 200
curl -s http://localhost:4000/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"ULTRA_FREE_CLOUD_FAST","messages":[{"role":"user","content":"ok"}],"max_tokens":300}'
git grep -in 'inception\|mercury' -- '*.py' '*.yml' '*.sh'   # expect: retirement comments only
```

---

## 9. Files for review

Everything a reviewer needs, and what each artifact proves. Branch
`scrub/inception-mercury-2026-11-12`, **37 files changed vs `main`**, in two commits:
`df2eadf054cb` (36 files — the retirement) and `83787bd97b` (this chatlog). Tip at time of
writing: `83787bd97b079fff1a40840d4e6aa98b64de7179`.

The exact commit path list, in order: `/tmp/scrublist.txt` (36 lines).

```
tools/litellm_dynamic_models.py            tools/free_provider_audit.py
tools/start_litellm_proxy.sh               tools/free_model_discovery.py
litellm_config.yaml                        tools/api_model_roster.py
tools/swarm/api_consult.py                 tools/model_picks_research.py
tools/swarm/swarm_run.py                   tools/model_capability_probe.py
tools/swarm/worker_runner.py               tools/local_swarm_review.py
tools/swarm/swarm_followup.py              tools/_graphify_docs_multibackend.py
tools/swarm/invent_personas.py             tools/swarm/README.md
tools/swarm/safety.py                      tools/swarm/SPEC.md
tools/swarm/ENGINE_KEY_ENVS.py             tools/swarm/PORTING.md
tools/swarm_v2/swarms/core/llm_client.py   tools/swarm/swarm.config.example.json
.ruflo/orchestrator.py                     .claude/skills/second-opinion/scripts/ask.py
.ruflo/wizard.py                           .claude/skills/second-opinion/SKILL.md
.github/workflows/research-orchestrator.yml .claude/skills/graphify-map/SKILL.md
.github/workflows/ai-tournament-pipeline.yml .claude/skills/consult-multi/SKILL.md
tools/verify_all_keys.py                   .env.example
config/api_model_roster.json               audit_dashboard/inception_paper_trading.html
```

**Fix records** (repo rule — every fix gets one):

| File | Size | What it is |
|---|---|---|
| `updates/2026-11-12-inception-mercury-api-sunset-migration.md` | 8,927 b | The fix record proper. §5 = the OPENROUTER label bug, §7 = hermesbackup addendum. |
| `updates/2026-11-12-freebuff-swarm-coordination-chatlog.md` | 7,947 b | Earlier coordination log; superseded by this dated one. |
| `updates/2026-11-12-FREEBUFF-chatlog-1959UTC.md` | 8,022 b | This file. |

**Other repositories touched or consulted**

- `eltonaguiar/hermesbackup` @ `875f448` (`master`) — provider block and
  `credential_pool["custom:api.inceptionlabs.ai"]` removed; YAML and JSON re-parsed; 0
  residual hits. Cosmetic only: history still holds the value until the key is revoked.
- `eltonaguiar/SWARM_CONSOLIDATED` @ `8d15148` — peer-owned. `core/worker.py` line 9 still
  lists `inception`; `REMAINING_TASKS.md` absent.
- `eltonaguiar/FREELLM` PR #1 — unmerged, owner-side, **not** a wiring precondition.
- `SWARM_CONSOLIDATED/FREEBUFF_SWARM_2026-11-12.MD` — the shared plan of record.

**Peer artifact reviewed:** `testing123.md` (3,369 B, untracked in the domain repo root) —
the other agent's export.

**Never for review:** `~/dbpasses.txt`. It holds keys; only label *names* appear in these
notes, never values.

**Local-only, will not survive the session:** `/tmp/scrublist.txt` (the 36 paths),
`/tmp/api_push2.py` (blobs → tree → commit → ref, how the branch was published),
`/tmp/api_commit_one.py` (adds one file on top), `/tmp/scrubwt` (the worktree),
`/tmp/freebuff.txt` and `/tmp/claude_ollama.txt` (the two coordination logs).

**Shape caveat for reviewers:** the local worktree still carries the original four-commit
history while GitHub shows the two squashed commits above. Same content, different shape —
diff the branch, not my worktree.
