---
name: llm-alive-probe
description: Probe every model in litellm_config.yaml against its real provider and report which are ALIVE, then rank them into routing weights so the router prefers validated models over retired/broken ones. Use when the user says "/llm-alive-probe", "are our models alive", "which free models are down", "probe all our models", "why is free-mode failing", "re-rank/prioritise our models", or after any provider outage / model retirement. Aliases — alive-probe, llm-alive, probe-models, model-health.
---

# /llm-alive-probe — health-check every configured model

`litellm_config.yaml` lists ~127 deployments across ~15 providers. Providers retire models, keys
expire, and quotas drain — and nothing told you *which* ones were actually working. This probes each
deployment **directly at the provider** (bypassing the proxy, so `simple-shuffle` noise can't hide a
dead model), writes a status report, and can rank the alive ones into routing weights.

## Run it

```bash
python3 tools/llm_alive_probe.py                     # probe everything, print table + group summary
python3 tools/llm_alive_probe.py --failures          # only the non-alive rows
python3 tools/llm_alive_probe.py --free-only         # only free-*/hybrid-* groups
python3 tools/llm_alive_probe.py --group free-mode   # one group
python3 tools/llm_alive_probe.py --recheck           # re-probe ONLY the previously non-alive ones
python3 tools/llm_alive_probe.py --status            # show the last report (no probing)
python3 tools/llm_alive_probe.py --status --apply    # rank alive models -> weights in the config
python3 tools/llm_alive_probe.py --json > /tmp/alive.json
```

`--apply` writes `weight:` into every deployment, so restart the proxy afterwards
(`bash tools/start_ai_servers.sh restart`, or `tools/start_litellm_proxy.sh --background`).

## Status vocabulary

| status | meaning | weight |
|---|---|---|
| `alive` | got a completion back | 100 / 70 / 40 / 20 by latency (`<=1.5s / <=4s / <=10s / slower`) |
| `throttled` | the model exists and the key works, but the provider returned 429 | 10 |
| `error` | 5xx / timeout / unknown provider error — may be transient | 3 |
| `dead` | retired model, dead key, or exhausted quota — will not recover alone | 0 |

Categories come from the shared classifier (`tools/litellm_smart_cooldown._classify`), so the probe,
the runtime blacklist, and the config all speak the same language.

## Workflow: "make free-mode prefer the good models"

```bash
python3 tools/llm_alive_probe.py --failures          # 1. see what is broken
python3 tools/llm_alive_probe.py --recheck           # 2. re-probe just those (filters transients)
python3 tools/llm_alive_probe.py --status --apply    # 3. rank alive -> weights
bash tools/start_ai_servers.sh restart               # 4. reload the proxy
```

Always run the **recheck** step before acting on the numbers. In the first full run,
`alive=35 dead=46 error=11 throttled=35`; the recheck reproduced it almost exactly
(`35/46/12/34`), which is what makes the result trustworthy rather than probe noise.

## Two gotchas worth knowing

**1. `simple-shuffle` will silently zero out a partially-weighted group.** LiteLLM reads the weight
*key name* from `healthy_deployments[0]`, then collects that key from **every** deployment in the
group, defaulting missing ones to `0`. So if `weight` is set on some entries but not others, the
unweighted ones get weight 0 and never picked. `--apply` therefore always writes a weight for
**every** deployment line — do not hand-edit weights for just a few entries.

**2. Local servers need no API key.** `ollama_chat/*` and `hosted_vllm/*` deployments have no
`api_key`; treating a missing key as "dead" is a false negative. The probe special-cases these
providers. (This bit once — `ollama_chat/qwen2.5:7b` was wrongly reported dead.)

## What "dead" does and does not mean

`dead` is scoped to **our key/account**, which is the thing that matters operationally — but it is
*not* a claim the model is globally retired. Example: Groq returned
`model_not_found` for `llama-3.1-8b-instant`, so it is dead *for this key* even though the model
is normally widely available. Check whether it is a key/account issue before deleting an entry.

A `dead` verdict does **not** mean you must delete the entry: the runtime blacklist
(`tools/litellm_call_blacklist.py`) parks broken deployments automatically, and `weight: 0` keeps
them out of selection. Delete only when you want to reclaim the config line.

## Output

- `reports/llm_alive_status.json` — `{meta: {probed_at_utc, total, elapsed_s, summary, mode}, rows: [...]}`
  where each row is `{group, model, api_base, status, category, latency_ms, detail}`.
  `--status` and `--status --apply` read this, so you can inspect and apply without re-probing.
- Full runs take ~30s at `--concurrency 8`; a recheck of ~90 entries takes ~11s.

## Related

- `tools/litellm_call_blacklist.py` — runtime parking of failing deployments (catches deaths between probes).
- `.claude/skills/litellm-proxy/SKILL.md` — proxy internals, provider chain, rotation.
- `.claude/skills/startaiservers/SKILL.md` — bringing the local stack up/down.
