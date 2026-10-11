# Model liveness probing + alive-first priority tiers (2026-10-11)

## Problem

`litellm_config.yaml` listed **127 deployments** across ~15 providers with no way to tell which were
actually working. Providers retire models, keys expire, quotas drain — and `simple-shuffle` picked
uniformly among the survivors.

Concretely, the user hit `litellm.NotFoundError: ... gemini-2.5-pro is no longer available to new
users` from `free-mode`. That specific model is fixed separately (see
`2026-10-11-retired-model-404-blacklist.md`), but nothing answered the general question: **which of
our models are alive?**

## What was added

### `tools/llm_alive_probe.py`

Probes every deployment **directly at the provider**, bypassing the proxy, so `simple-shuffle` cannot
hide a dead model behind a healthy one. Writes `reports/llm_alive_status.json`.

```bash
python3 tools/llm_alive_probe.py                    # probe all, print table + per-group summary
python3 tools/llm_alive_probe.py --failures         # only non-alive rows
python3 tools/llm_alive_probe.py --free-only        # free-*/hybrid-* groups
python3 tools/llm_alive_probe.py --recheck          # re-probe only the previously non-alive ones
python3 tools/llm_alive_probe.py --status           # show last report, no probing
python3 tools/llm_alive_probe.py --status --apply   # rank alive models -> weights in the config
```

### Alive-first priority tiers

`--apply` writes `weight:` into **every** deployment line, comment-preserving:

| tier | status | weight |
|---|---|---|
| **P1** validated-alive | `alive` | 1000 / 500 / 200 / 100 by latency |
| **P2** throttled | `throttled` (429) | 10 |
| **P3** error | `error` (5xx / timeout) | 1 |
| **P4** dead | `dead` (retired / dead key / no credential) | 0 |

**Anything with an issue is at least 10x below a validated model.** The first cut used alive
20–100 vs throttled 10 vs error 3 — only a 2x gap between a slow-but-working model and a
quota-exhausted one, which let throttled models get picked far too often. Hence the steepening.

### Skill

`.claude/skills/llm-alive-probe/SKILL.md` — `/llm-alive-probe`.

## Findings (127 deployments, ~32s, reproduced by a recheck pass)

```
alive=33-35   throttled=34-35   error=11-14   dead=46
```

| group | alive | thr | err | dead | total |
|---|---|---|---|---|---|
| `free-mode` | 13 | 6–8 | 6–8 | 12 | 39 |
| `free-mode-large` | 6–8 | 4–5 | 0–1 | 3 | 15 |
| `free-mode-tools` | 1 | 3 | 2 | 4 | 10 |
| `free-mode-fast` | 1 | 1 | 0 | 3 | 5 |
| `hybrid-model` | **0** | 1 | 1 | 3 | 5 |
| `hybrid-model-large` | 2 | 4 | 0 | 4 | 10 |
| `paid-mode` | 5 | 10 | 1 | 9 | 25 |
| `paid-mode-fast` | 3 | 1 | 0 | 2 | 6 |
| `paid-mode-large` | 1 | 2–3 | 0–1 | 2 | 6 |
| 4 × `*-direct` singletons | **0** | 0 | 0 | 1 each | 4 |

**`free-mode-fast`, `hybrid-model`, and all four `*-direct` singletons have zero alive deployments** —
those model names can only fail.

Notable: Groq `llama-3.1-8b-instant` → `model_not_found` for our keys (appears in 3 groups);
`anthropic/claude-haiku-4-5` dead in 3 groups; `openai/gpt-5.5-instant` dead in 4.

`dead` is scoped to **our key/account** — it is *not* a claim the model is globally retired. Groq
`llama-3.1-8b-instant` is normally widely available, so that is likely a key/account problem, not a
retirement. Do not delete entries on a `dead` verdict alone.

## Verification

- Weight distribution after apply: `1000×26, 500×8, 10×33, 1×14, 0×46`.
- **12/12 `free-mode` requests returned HTTP 200, and all 12 were served by the `alive` tier** — zero
  from throttled, error, or dead.
- Config parses (127 deployments); proxy healthy; blacklist regression tests still pass
  (`selftest` 7/7, `patchtest`).
- Confirming recheck reproduced the first pass, which is what makes the numbers trustworthy rather
  than probe/concurrency noise.

## Gotchas found while building this

1. **`simple-shuffle` reads the weight key name from `healthy_deployments[0]`** and then collects that
   key from *every* deployment in the group, defaulting missing entries to `0`. A partially-applied
   `weight` therefore silently zeroes everything else in the group. `--apply` always writes a weight
   for every line.
2. **Local servers need no API key.** `ollama_chat/*` and `hosted_vllm/*` have no `api_key`; treating
   a missing key as `dead` produced a false negative (`ollama_chat/qwen2.5:7b`).
3. Config entries are all single-line flow-style (`- {model_name: ...}`), which is what makes
   comment-preserving line-based weight injection safe. The probe asserts this shape
   (127 single-line entries == 127 parsed deployments) and refuses to guess otherwise.

## Paid groups: which paid models are actually alive?

37 paid deployments across `paid-mode` / `paid-mode-fast` / `paid-mode-large`:
**alive=9, dead=13, throttled=14, error=1.** Only **four distinct models** work:

| model | groups | latency |
|---|---|---|
| `deepseek/deepseek-chat` | paid-mode, paid-mode-fast, paid-mode-large | 633–1104 ms |
| `xai/grok-4-fast-non-reasoning` | paid-mode, paid-mode-fast | 627–929 ms |
| `xai/grok-code-fast-1` | paid-mode | 2515 ms |
| `xai/grok-3-mini` | paid-mode | 1968 ms |

Everything else is spent or broken, consistent with most paid subscriptions having lapsed:

- **14 throttled** — all `openai/`-prefixed aggregator routes returning 429 (`gpt-5-chat`,
  `gpt-5-2025-08-07`, `kimi-k2.6`, `kimi-k2.5`, `grok-4.20-fast`, `grok-code-fast-1`,
  `MiniMax-M2`, `gpt-oss-120b`, `step-3.5-flash`, `glm-5.1`).
- **13 dead** — `anthropic/claude-haiku-4-5` (dead key, 3 groups), `openai/gpt-5.5-instant`
  (dead key, 4 groups), `xiaomi-mimo`, `mimo-v2.5-pro`, `moonshot-v1-8k`, plus one
  `gpt-4o-mini` with no key.
- **1 error** — `openai/gpt-4o-mini`.

A routing detail worth keeping: the **direct `xai/` key works while the `openai/`-prefixed route
to the same Grok model is throttled** — route choice matters as much as model choice.

After weighting, paid traffic lands only on live models: `paid-mode` 5/5 and `paid-mode-fast`
3/3 returned HTTP 200, served exclusively by `deepseek-chat`, `grok-4-fast` and
`grok-code-fast-1`.

## Two more bugs found while probing paid groups

1. **A partial probe overwrote the whole report.** `--paid-only` replaced the 127-row report with
   37 rows, so a later `--status --apply` would silently act on a subset. Reports are now merged.
2. **Deployment identity was not unique.** Keying on `(group, model, api_base)` collapsed 20
   signatures covering 44 deployments that differ only by credential (`GEMINI_API_KEY` vs `_ALT`
   vs `_ALT2`, `GROQ_API_KEY` vs `_ALT`), dropping 24 rows from the report (127 → 103). Identity
   now includes the api_key reference.

   Honest caveat: at fix time **no** duplicate signature had siblings in different states, so no
   weight had actually been mis-assigned — the real impact was the lost report rows. The fix
   matters for the case where one key of a pair lapses while its sibling keeps working.

## Files

| File | Change |
|---|---|
| `tools/llm_alive_probe.py` | new — probe + tiering tool |
| `.claude/skills/llm-alive-probe/SKILL.md` | new — `/llm-alive-probe` skill |
| `litellm_config.yaml` | `weight:` applied to all 127 deployments |
| `reports/llm_alive_status.json` | generated status report |
