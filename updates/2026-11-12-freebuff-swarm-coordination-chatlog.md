# Session chatlog — Freebuff ↔ Ollama-Claude swarm coordination (2026-11-12)

**Purpose:** durable record of the two-agent work that removed the Inception (Mercury)
provider from the domain repo, restarted the LiteLLM proxy, and agreed a
"core vs domain" split for `SWARM_CONSOLIDATED`.
**Status:** domain scrub committed; peer blocked only on signals + alias list.
**Companion doc:** `updates/2026-11-12-inception-mercury-api-sunset-migration.md`.

---

## 1. Surfaces used

| Surface | Owner | Purpose |
|---|---|---|
| `/tmp/freebuff.txt` | Freebuff | outbound status, health report, agreements |
| `/tmp/claude_ollama.txt` | Ollama-Claude | inbound plan, SPLIT_ACK, holding-pattern notes |
| `SWARM_CONSOLIDATED/FREEBUFF_SWARM_2026-11-12.MD` | Freebuff | the shared plan of record (§1–§14) |
| `SWARM_CONSOLIDATED/OLLAMA_CLAUDE_2026-11-12.md` | Ollama-Claude | their plan + `REMAINING_TASKS.md` |
| `testing123.md` (domain repo root, untracked) | Ollama-Claude | their session export — written into my scope, left in place |

Rule the two sides settled on: **append-only**, never edit the other agent's file.

## 2. Timeline (UTC)

- **~17:00** Audit begins. 2,259 files match "mercury", but almost all are the
  *Mercury strategy family* (`mercury2/`, `baby_strategies/mercury_*`) or `genome/**`
  provenance. Six registries carried a real dependency.
- **17:3x** Six registries patched (18 runtime files + 16 doc/skill/config files).
- **17:54** Proxy restarted through `litellm-4000.service`. Readiness 200 in ~40 s,
  PID 525411, `NRestarts=0`, 242 deployments / 36 groups, zero mercury groups.
- **18:0x** GitHub `INCEPTION_API_KEY` secret already absent (25 secrets, none inception).
  My delete returned 404 because it had already gone.
- **18:2x** Proxy health probe: 21 free groups, `max_tokens=4`, 6-way, 39.6 s →
  **16/21 HTTP 200**. Calibration trap recorded: at `max_tokens=4` eleven healthy
  groups return empty `content` with only `reasoning_content` populated.
- **18:21:56** Peer sends `SPLIT_ACK`, accepting amendments 2–4 and going silent
  on the domain repo.
- **18:2x–18:4x** Six amendments published (file gates, preserved deltas, proxy
  ownership, signal definitions, do-not-touch list). Dialog declared closed.
- **18:4x** Owner directive: `~/dbpasses.txt` is **not** deleted and its
  `INCEPTION_AI_KEY` entry stays; revocation at the dashboard is the whole action.
- **19:2x** Peer publishes `testing123.md` + `FINAL COORDINATION SYNC`; moves to a
  HOLDING PATTERN awaiting `DOMAIN_SCRUB_COMPLETE`.
- **19:4x** Freebuff: commit `ff57065587f` — 35 files, 3,833 insertions on branch
  `scrub/inception-mercury-2026-11-12` (cut from `origin/main`, not from the dirty
  `job-search` HEAD, which carried six unrelated doc commits).
- **19:5x** Root causes measured for the five dead proxy groups (see §4).

## 3. Decisions worth keeping

1. **Remove, don't alias.** Repointing would leave two names for one dead backend.
2. **Restart only via the systemd unit.** An ad-hoc restart during the 60–180 s
   discovery window produces random-port ghosts; `timeout`-wrapping the launcher kills
   the proxy it just started.
3. **`/health/readiness`, never `/health`.** The latter fans out to every deployment
   and false-negatives on a working proxy.
4. **Probe with `max_tokens >= 100`.** Otherwise thinking models look dead.
5. **Do not copy `litellm_config.yaml` into `SWARM_CONSOLIDATED`.** FREELLM owns it;
   pin a commit sha and document the contract.
6. **The proxy is not a repo file.** It is a process on this host with one owner.
7. **Proxy-first for every swarm.** No swarm reads `~/dbpasses.txt`; only
   `tools/start_litellm_proxy.sh` does, and it exports what the proxy needs.

## 4. Measured state of the proxy (the numbers behind the alias list)

Live, fast, safe as defaults: `ULTRA_FREE_NVIDIA` 185 ms · `ULTRA_FREE_LOCAL_MULTI` 341 ms ·
`ULTRA_FREE_TOOLS` 351 ms · `ULTRA_FREE_OPENROUTER` 382 ms · `ULTRA_FREE_CLOUD_FAST` 430 ms ·
`ULTRA_FREE_TOGETHER_BONSAI` 641 ms · `ULTRA_FREE_CLOUD_LARGE` 872 ms ·
`ULTRA_ALL_DAY_LONG_KILO_1/2/3` ~0.9–1.1 s.

Dead, with cause:

| Group | Symptom | Cause found 19:5x |
|---|---|---|
| `ULTRA_FREE_CLOUD_TOOLS` | 401 `OpenrouterException: No cookie auth credentials found` | `OPENROUTER_API_KEY` is **absent from the running proxy's environment** (`/proc/525411/environ`), while its three deployments are all `openrouter/*:free`. Not a rate limit and not the NVIDIA JWT story. |
| `ULTRA_FREE_LOCAL_CHAT` / `_CODE` | >30 s timeout | `ollama_chat/qwen3.5:35b-a3b` (23 GB) — cold load competing with the resident models, not dead |
| `ULTRA_FREE_LOCAL_CODE_1FALLBACK` | >30 s timeout | points at `qwen2.5-coder:14b`, which does not appear in `ollama list` |
| `ULTRA_FREE_LOCAL_FAST` | >30 s timeout | points at `llama3.2:3b`, likewise not in `ollama list` |

## 5. What is verified, what is not

Verified: proxy serves 36 aliases with zero mercury groups; 16/21 free groups return
200; the domain repo has zero live inception references; commit `ff57065587f` passes
`py_compile`/`bash -n`/`yaml.safe_load`.

**Not yet verified — and it is the gap that matters:** no swarm has been *run* end to
end since the provider was removed. `tools/swarm/swarm_run.py`,
`tools/swarm_v2/swarms/core/llm_client.py`, `.ruflo/orchestrator.py` and the
`SWARM_CONSOLIDATED` core have been edited or never exercised; a dispatch list that
lost `inception` can still raise at runtime, and `ruflo`'s `reviewer` now depends on
`groq` actually answering. Smoke-testing each swarm type against a live alias is the
next task, not a completed one.

## 6. Open items

- Owner: revoke the key at `dashboard.inceptionlabs.ai` (the only action that matters).
- Owner: merge FREELLM PR #1.
- Freebuff: add `OPENROUTER_API_KEY` to the proxy environment, then re-probe TOOLS.
- Freebuff: warm `qwen3.5:35b-a3b`; repoint or install the two missing local models.
- Freebuff: scrub `hermesbackup` (`config.yaml` "Api.inceptionlabs.ai" provider block,
  `auth.json` → `credential_pool["custom:api.inceptionlabs.ai"]`).
- Peer: `CORE_READY` only after `requirements.txt` + `cli/swarm_picker.py` are **on main**
  and `core/worker.py:9` is fixed there (still 1 `inception` ref on main at 19:4x).

## 7. Addendum — 19:5x UTC, the five dead groups were two real bugs

Both were found by measuring instead of guessing, and neither was what the earlier notes
assumed.

**A. `ULTRA_FREE_CLOUD_TOOLS` 401 — a label mismatch, not a dead provider and not the
NVIDIA JWT story.** Live error: `OpenrouterException - {"message":"No cookie auth
credentials found","code":401}`. All three deployments in that group are
`openrouter/*:free` with `api_key: os.environ/OPENROUTER_API_KEY`, and the running
proxy had **no `OPENROUTER_API_KEY` in its environment at all**. Cause: `parse_key()`
compares whole lines, the launcher passed `"OPEN ROUTER API KEY"`, and dbpasses spells
the line `OPEN ROUTER API KEY (OPENROUTER)`. Fixed in `tools/start_litellm_proxy.sh`;
after a unit restart the key is present and the group answers. Blast radius was larger
than one group: `TOOLS` is the fallback for `ULTRA_FREE_NVIDIA` and
`ULTRA_FREE_CLOUD_LARGE`.

**B. The four local groups were never dead.** All three models
(`qwen3.5:35b-a3b`, `qwen2.5-coder:14b`, `llama3.2:3b`) are installed. Direct ollama
calls: 8.6 s (6.8 s of that is the 23 GB load), 3.7 s, 1.6 s. The >30 s timeouts were
cold-load contention against already-resident models, so the fix is a warm-up, not a
config change.

**C. `hermesbackup` scrubbed and pushed** — commit `875f448` on `master`: provider block
removed from `config.yaml` (4 lines, YAML re-validated) and
`credential_pool["custom:api.inceptionlabs.ai"]` removed from `auth.json` (re-parses,
0 remaining hits). History still holds the old value, so this is cosmetic until the key
is revoked at the dashboard — which remains the only action that matters.
