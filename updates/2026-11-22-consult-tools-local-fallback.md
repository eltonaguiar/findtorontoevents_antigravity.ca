# Consult tooling: local :8000 vLLM as provider and automatic fallback — 2026-11-22

## What was broken

Two consult CLIs existed and neither knew the 35B model now serving on
`127.0.0.1:8000` existed:

* `tools/consult_multi.py` — 14 cloud providers, all key/quota dependent. A
  single `--fanout diverse5` run on 2026-11-22 returned **5/5 failures**
  (NVIDIA 410 Gone, Groq 404, Cerebras 404, Together 401, Fireworks 404). The
  fan-out wrote five `ERROR:` files and no answer. There was no fallback, so a
  consult could cost a round trip and produce nothing.
* `tools/fleet_consult.py` — LM Studio + Ollama only. It could not reach the
  fastest capable engine on the LAN.

Separately, the :8000 server (Qwen3.6-35B-A3B-NVFP4, `--reasoning-parser qwen3`)
has a failure mode that looks like success: with a small `max_tokens` every
token is spent in `reasoning_content` and the response is **HTTP 200 with
`content: ""`**. Both tools would have recorded that as a healthy call that
produced nothing.

## What changed

`tools/consult_multi.py`

* `local_qwen` provider, no credential, `$LOCAL_LLM_BASE` (default
  `http://127.0.0.1:8000/v1`) + `$LOCAL_LLM_MODEL` (default
  `Qwen3.6-35B-A3B-NVFP4`).
* `_post_openai_compat` now takes an optional key and an `extra` body dict so
  the local server shares one transport instead of forking a second one.
* Automatic fallback: any cloud failure in `--provider` or `--fanout` is
  retried once on `local_qwen`, and the answer is kept with the cloud error
  preserved as a `FALLBACK:` note (fan-out files carry the note above the
  text; single calls print it to stderr). `--no-fallback` opts out.
* Thinking is requested only when `--max-tokens >= 1500`; otherwise
  `chat_template_kwargs.enable_thinking=false`. If a thinking-enabled call
  still comes back empty, it retries once with thinking off.
* The empty-completion error now reports `reasoning_tokens`, so the next
  occurrence is diagnosable from the message alone.

`tools/fleet_consult.py`

* `("vllm", "http://127.0.0.1:8000")` added to `DEFAULT_TARGETS`; discovery and
  the OpenAI-compatible call path handle it (`/v1/models`, `/v1/chat/completions`).
* Same `THINK_MIN_TOKENS = 1500` gate plus one retry with thinking disabled.
  The Ollama path is untouched.

## Verified

```
consult_multi --list                    local_qwen present, has_key=yes
--provider local_qwen --max-tokens 64   -> "OK" (thinking off path)
--provider local_qwen --max-tokens 1600 -> one-sentence answer (thinking on path)
--provider groq --model no-such-model   -> FALLBACK note on stderr, "FALLBACK_OK" on stdout, rc=0
fleet_consult --list                    vllm http 200 models 1
fleet_consult --model vllm:...          -> 200, 2 chars, 0.1s
fleet_consult --self-check              SELF-CHECK PASSED
py_compile both files                   clean
```

Not verified: a fan-out where *some* peers fall back and others answer (the
write path was changed to keep fallback text as an answer, but only the
single-provider fallback was exercised end to end).
