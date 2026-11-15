# 2026-11-15 — Ollama cloud models on the LiteLLM proxy as `ULTRA_PAID_OLLAMA_*` (no :4000 restart)

**Request:** add Ollama cloud models under the `ULTRA_PAID_*` family, without restarting the proxy on port 4000
(other agents are using it), and on boot query Ollama's cloud models and update the listing if it changed.

## Why not live-add to the running proxy

Three approaches were tested against the live process (pid 3518861, up 1+ day, `--port 4000`):

| Approach | Result |
|---|---|
| `POST /model/new` (LiteLLM admin hot-add) | **HTTP 500** — `No DB Connected … virtual_keys`; this proxy runs stateless (`store_model_in_db` unset, `database_url` absent), so admin writes are unavailable |
| Pass-through of an unregistered name (`ollama_chat/minimax-m3:cloud`, `minimax-m3:cloud`, `ULTRA_PAID_OLLAMA_MINIMAX_M3_CLOUD`) | **Rejected** — `/chat/completions: Invalid model name passed in model=… Call /v1/models to view available models` |
| Editing config + SIGHUP/reload | LiteLLM has no config-reload signal; a restart is the only way it re-reads `model_list` |

So: **the config is updated and the aliases will exist on the next start** (boot, or a deliberate restart at a quiet
moment). Nothing was restarted; the proxy PID was checked before and after and is unchanged.

## What was added

`tools/sync_ollama_cloud_models.py` — idempotent sync, four steps:

1. **Discovery** — `GET http://localhost:11434/api/tags`, keep cloud entries (name ends `-cloud`/`:cloud`, or the entry
   is a stub: `size < 100 MB`). Currently finds 3:
   `minimax-m3:cloud`, `gemma4:31b-cloud`, `artiku348/loker.v2.1-cld-cdr-480b:latest`.
2. **Persistence** — rewrites a marker block (`# BEGIN/END ollama-cloud-autosync`) inside the LiteLLM config, so a
   restart keeps the aliases. Target defaults to `litellm_config.runtime.yaml` if present, else `litellm_config.yaml`
   (the repo's canonical config, which is what `tools/start_litellm_proxy.sh` starts from).
3. **Live add** — `POST /model/new` for anything the running proxy doesn't serve yet (currently a no-op, see above;
   kept for installs that do have a DB).
4. **agy env** — appends the new aliases to `AGY_LLM_GATEWAY_MODELS` in `~/.config/agy-litellm/env`, so the CLI, the
   IDE extension and the App picker list them.

Resulting aliases:

```
ultra_paid_ollama_minimax_m3_cloud   <- ollama_chat/minimax-m3:cloud
ultra_paid_ollama_gemma4_31b_cloud   <- ollama_chat/gemma4:31b-cloud
ultra_paid_ollama_loker_v2_1_cld_cdr_480b <- ollama_chat/artiku348/loker.v2.1-cld-cdr-480b:latest
```
(all uppercase in the config; each entry is
`{model_name: …, litellm_params: {model: 'ollama_chat/<name>', api_base: http://localhost:11434, api_key: ollama}}`)

## Boot hook

- `~/.config/systemd/user/litellm-ollama-sync.service` — oneshot, runs the sync with `--no-live`.
- `~/.config/systemd/user/litellm-ollama-sync.timer` — `OnBootSec=45s`, `OnUnitActiveSec=30m`, `Persistent=true`.
- `litellm-4000.service` — new `ExecStartPre=-…sync_ollama_cloud_models.py --no-live` (the `-` prefix means a sync
  failure can never block the proxy from starting).

## Verification

- `minimax-m3:cloud` answers locally: `ollama run minimax-m3:cloud` → `OLLAMA-CLOUD-OK` (account is signed in, so the
  aliases are backed by a working upstream once the proxy restarts).
- Config block present and the YAML still parses; second run of the script reports `already current` and adds nothing
  (idempotent), and appends no duplicate entries to the agy env.
- Proxy PID identical before/after every step — **port 4000 was never restarted**.
- `agy` env model list grew from 32 → 35 entries.

## To make the running proxy serve them (only when it's quiet)

```bash
bash tools/start_litellm_proxy.sh            # or: systemctl --user restart litellm-4000.service
curl -s localhost:4000/v1/models -H 'Authorization: Bearer sk-1234' | grep -c ULTRA_PAID_OLLAMA   # expect 3
```

Note: the unit `litellm-4000.service` is *enabled* but currently *inactive* — the live proxy was started by hand, so a
plain reboot (or that unit) is what picks the new config up.
