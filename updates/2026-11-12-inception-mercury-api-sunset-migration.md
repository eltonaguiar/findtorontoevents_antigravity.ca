# Inception (Mercury) API sunset — audit + migration off the vendor

**Date:** 2026-11-12
**Trigger:** Vendor email from The Inception Team — the Mercury API is being wound down.
The service stays fully available through **2026-12-28**, after which the key stops
working and all data on their platform is gone.
**Status:** Migration complete in-repo. Two manual actions remain (see bottom).

---

## 1. What was broken / at risk

Inception Labs' Mercury API was wired as a first-class provider in **six independent
subsystems**, each with its own registry. Nothing "fails loudly" when a provider dies:
every call site either probes a catalog, skips a provider with no key, or falls through
a provider list. So the failure mode was **silent capability loss plus 401/404 noise**,
not a crash.

The audit first had to separate real dependencies from a large false positive: this repo
contains **2,259 files matching "mercury"**, but almost all are the *strategy family*
named after Mercury (`mercury2/`, `baby_strategies/mercury_*.py`), provenance metadata
(`genome/**` `"source": "mercury_inceptionlabs"`), or historical docs. None of those call
the API. `gh search code --owner eltonaguiar` was used to find the real ones.

### Live call sites found

| Subsystem | Location | Failure mode after shutdown |
|---|---|---|
| LiteLLM proxy | `tools/litellm_dynamic_models.py` — `PinSpec("PAID-MERCURY","inception")` + `_PIN_SOURCES["inception"]` | `PAID-MERCURY` group silently absent on next proxy restart |
| LiteLLM key plumbing | `tools/start_litellm_proxy.sh` — `parse_key "INCEPTION_AI_KEY"`, export list | dead key exported, 401s |
| swarm v1 | `tools/swarm/api_consult.py` — `PROVIDERS["inception"]`, `SAMPLING_DEFAULTS["inception"]` | provider 401/404 |
| swarm v1 env | `tools/swarm/ENGINE_KEY_ENVS.py`, `tools/swarm/safety.py` | env allowlist passing a dead key |
| swarm v2 | `tools/swarm_v2/swarms/core/llm_client.py` — `Provider("inception", …, "mercury-2")` | drops from auto-detected providers |
| ruflo | `.ruflo/orchestrator.py` (`PAID_MODELS`, **`"reviewer": "inception"`**), `.ruflo/wizard.py` | **reviewer stage** had no working provider |
| second-opinion skill | `.claude/skills/second-opinion/scripts/ask.py` — pinned `mercury-3` | peer vanished from every fan-out |
| key tooling | `tools/verify_all_keys.py`, `tools/api_model_roster.py`, `tools/free_model_discovery.py` | permanent failing row / dead roster entries |
| GitHub Actions | `.github/workflows/research-orchestrator.yml` (`INCEPTION_AI_KEY`), `ai-tournament-pipeline.yml` (`INCEPTION_API_KEY`) | provider loss in daily research runs |
| Docs/config | `.env.example`, `litellm_config.yaml` comment, `tools/swarm/PORTING.md`, two skill docs | stale onboarding pointers |

### Already insulated — no change needed

`config/model_persona_mapping.json` (`mercury` persona) routes to **`inception/mercury-2`
on `api.together.xyz`** using `TOGETHER_API_KEY`. It never touched the Inception API.
⚠️ Confirm with Together that resold Mercury stays hosted past December — if it does not,
that persona needs a new model (see mapping below).

### `~/dbpasses.txt`

Exactly **one** entry: line 293 `INCEPTION_AI_KEY` (no MERCURY-labelled entry). It was
being loaded and exported by `tools/start_litellm_proxy.sh`. The `parse_key` line has
been removed, so nothing reads it any more.

### Other repos under `eltonaguiar`

- `FREELLM` — same three files (`free_provider_audit.py`, `litellm_dynamic_models.py`,
  `start_litellm_proxy.sh`). **Not migrated** (separate repo, separate branch).
- `hermesbackup` — `auth.json` (`"custom:api.inceptionlabs.ai"`) **and** `config.yaml`
  (`base_url: https://api.inceptionlabs.ai/v1`). **Stores credential material — revoke
  before 2026-12-28.**

---

## 2. What changed

Retire the vendor outright rather than repoint to a duplicate: every registry keeps its
existing providers, so no code path gains a second alias for the same backend.

1. `tools/litellm_dynamic_models.py` — removed `PAID-MERCURY` PinSpec, the `inception`
   `_PIN_SOURCES` entry, `inception` from the version-sort provider tuple; alias comment
   marked RETIRED.
2. `tools/start_litellm_proxy.sh` — removed the `INCEPTION_AI_KEY` `parse_key` line and
   `INCEPTION_API_KEY` from the export list.
3. `tools/swarm/api_consult.py` — removed the `inception` provider block, its sampling
   defaults, and the docstring/env-override references.
4. `tools/swarm/ENGINE_KEY_ENVS.py`, `tools/swarm/safety.py` — removed the `inception`
   key-allowlist entries.
5. `tools/swarm_v2/swarms/core/llm_client.py` — removed the `Provider("inception", …)`.
6. `.ruflo/orchestrator.py` + `.ruflo/wizard.py` — removed the provider config, the
   setup link, and repointed **`reviewer` → `groq`** (researcher stays `cerebras`,
   coder stays `deepseek`, so role diversity is preserved).
7. `.claude/skills/second-opinion/scripts/ask.py` — `inception`/`mercury-3` peer replaced
   by **`cerebras`/`gpt-oss-120b`** (the closest latency match at ~600 tok/s).
8. `tools/verify_all_keys.py` — removed `t_inception`, its results row, and the key alias.
9. `tools/api_model_roster.py`, `tools/free_model_discovery.py` — removed the provider
   specs.
10. `.github/workflows/research-orchestrator.yml` — removed the `INCEPTION_AI_KEY` env
    line + updated the header note.
11. `.github/workflows/ai-tournament-pipeline.yml` — dropped `INCEPTION_API_KEY`; the
    comment now records that the `mercury` persona routes via Together.
12. `.env.example`, `litellm_config.yaml`, `tools/swarm/PORTING.md`,
    `.claude/skills/second-opinion/SKILL.md`, `.claude/skills/graphify-map/SKILL.md` —
    stale pointers removed / annotated as retired.
13. **Second sweep** (a residual grep caught call sites the first pass's capped
    searches missed): `tools/free_provider_audit.py`, `tools/model_picks_research.py`,
    `tools/model_capability_probe.py`, `tools/local_swarm_review.py`,
    `tools/_graphify_docs_multibackend.py` (backend dict + `BACKENDS` tuple + comments),
    `tools/swarm/README.md`, `tools/swarm/SPEC.md`, and
    `tools/swarm/swarm.config.example.json` (key removed, JSON re-validated).
14. **Third sweep** (cost table + dispatch lists + generated snapshot):
    `tools/swarm/swarm_run.py` `COST_PER_1K_TOKENS` row **and all three engine lists
    (default list, `all-paid-api` preset, line-622 list)** — leaving `inception` in a
    dispatch list would have raised at run time now the provider is gone; plus
    `tools/swarm/SPEC.md` sampling snippet and the generated `config/api_model_roster.json`
    snapshot (provider entry stripped, JSON re-validated, 742→722 lines).

**No behaviour change for any surviving provider.** Mercury's only unique property was
its diffusion architecture; nothing in the pipeline depends on diffusion semantics, so
the loss is a vendor, not a capability. Cerebras is the closest latency substitute.

---

## 3. Verification

- `python3 -m py_compile` on all 17 edited Python files — pass.
- `bash -n tools/start_litellm_proxy.sh` — pass.
- `yaml.safe_load` on both edited workflows + `litellm_config.yaml` — pass.
- Import smoke: `api_consult`, `ENGINE_KEY_ENVS`, `safety` import clean and
  `'inception' not in api_consult.PROVIDERS`; `ask.py --help` exits 0 and its provider
  list no longer contains `inception`.
- Residual grep over live paths (`tools/`, `.ruflo/`, `.github/`, `.claude/skills/`,
  `config/`, `litellm_config.yaml`, `.env.example`) returns **only** the retirement
  comments added here — no live endpoint, key env var, or model ID remains.

Not run (out of scope for this change): live API calls to Together/Cerebras to confirm
current quotas, and a full LiteLLM proxy restart (per the `litellm-port-4000-debug`
skill, restarts must go through `litellm-4000.service`, not an ad-hoc launcher).

---

## 4. Remaining manual actions (need the operator)

1. **Before 2026-12-28:** revoke the key at `dashboard.inceptionlabs.ai`. **That is the
   whole action** — a revoked credential is inert wherever it sits. Per owner directive
   (2026-11-12) `~/dbpasses.txt` is **not** deleted and the `INCEPTION_AI_KEY` entry
   (label on line 293, value on the next line) is left in place. Nothing reads it: the
   only loader (`parse_key` in `tools/start_litellm_proxy.sh`) was removed, and the
   domain repo has zero live references.
2. **Before 2026-12-28:** remove `INCEPTION_AI_KEY` / `INCEPTION_API_KEY` GitHub secrets
   (`gh secret delete`) so no workflow holds a dead credential.
3. **Optional:** purge `eltonaguiar/hermesbackup` (`auth.json`, `config.yaml`) of the
   credential copy, and migrate `eltonaguiar/FREELLM` with the same patch set.
4. **Confirm with Together** whether `inception/mercury-2` survives December; if not,
   repoint the `mercury` persona in `config/model_persona_mapping.json` to
   `cerebras`/`gpt-oss-120b`.
