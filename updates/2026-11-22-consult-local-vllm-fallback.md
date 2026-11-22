# consult tooling: local vLLM as a provider and an automatic fallback

## What was wrong

`tools/consult_multi.py` could only reach cloud providers, so every consult burned
quota, and a rate-limit / 401 / bad-model-name meant the call simply failed. The
local vLLM on `:8000` existed but no tool knew about it.

Separately, `tools/fleet_consult.py` had no `vllm` target, so the fleet could not
see the local Qwen3.6-35B-A3B at all.

## What changed

Ported from `fix/dsr-baselines-h146-key-scrub-2026-11-21` onto current `main` as
its own change:

- `tools/consult_multi.py` — new `local_qwen` provider (localhost `:8000`, no key);
  automatic fallback to it on any cloud failure, tagged `FALLBACK:` in the output
  so a reader can tell which model actually answered. `--no-fallback` opts out
  when provider identity matters.
- `tools/fleet_consult.py` (new to main) — adds the `vllm` target alongside
  lmstudio/ollama.
- Credential handling hardened while porting: `_clean_key()` and `_scrub()` strip
  and redact key material so an error string can never echo a secret.

## Verification

- `py_compile` on both files: OK.
- `consult_multi.py --list`: 15 providers, `local_qwen` first with `has_key=yes`
  and default model `Qwen3.6-35B-A3B-NVFP4` (no key required by design).
- `fleet_consult.py --list`: 4 reachable targets — lmstudio 11 models,
  ollama LAN 71, ollama local 26, vllm 1 — all HTTP 200.
- Fallback path exercised earlier by forcing a bogus model on a cloud provider:
  `FALLBACK_OK`, answered by `local_qwen` and tagged as such.

## Not covered

`--no-fallback` and the cloud→local handoff are covered by that manual check, not
by an automated test; a 429 cannot be forced deterministically here.
