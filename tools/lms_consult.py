#!/usr/bin/env python3
"""Query the local LM Studio server for code review and second opinions.

The box serves several models at once (LM Studio keeps them resident), so a
review can be fanned across a fast general model, a reasoner and a small model
without spending cloud quota. No API key: the server is LAN-only.

    python3 tools/lms_consult.py --list
    python3 tools/lms_consult.py --model gpt-oss-20b --prompt "review this"
    python3 tools/lms_consult.py --models gpt-oss-20b,deepseek-r1-distill-qwen-32b-uncensored \
        --prompt-file /tmp/q.md --out-dir /tmp/lms_review

Endpoints: the native `/api/v1/chat` (what LM Studio documents) with the
OpenAI-compatible `/v1/chat/completions` as a fallback, because the native shape
has moved between builds. Replies are written as one file per model so a long
answer is never lost to a timeout in the middle of a fan-out.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HOST = os.environ.get("LMS_HOST", "http://192.168.2.32:1234").rstrip("/")


def _post(path: str, payload: dict, timeout: int) -> dict:
    req = urllib.request.Request(
        HOST + path, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", "replace")[:300]
        except Exception:                             # noqa: BLE001
            pass
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc


def _text(body: dict) -> str:
    """Pull the assistant text out of either response shape."""
    if isinstance(body.get("output"), list):            # native /api/v1/chat
        parts = []
        for item in body["output"]:
            if isinstance(item, dict):
                parts.append(str(item.get("content") or ""))
        if any(parts):
            return "".join(parts)
    if isinstance(body.get("choices"), list):           # OpenAI-compatible
        out = []
        for ch in body["choices"]:
            msg = ch.get("message") or ch.get("delta") or {}
            if isinstance(msg, dict):
                out.append(str(msg.get("content") or ""))
        return "".join(out)
    return json.dumps(body)[:2000]


def ask(model: str, prompt: str, system: str, max_tokens: int, timeout: int) -> dict:
    """OpenAI-compatible first (proven on this build), native second.

    Reasoning models on this box spend output tokens on hidden reasoning, so a
    small max_tokens returns an empty message with finish_reason="length" --
    budget for it. Context is also capped by however the model was loaded, not by
    max_context_length, so long prompts get a bare 400; keep prompts small.
    """
    attempts = [
        ("/v1/chat/completions", {"model": model, "max_tokens": max_tokens,
                                  "temperature": 0.3,
                                  "messages": [{"role": "system", "content": system},
                                               {"role": "user", "content": prompt}]}),
        ("/api/v1/chat", {"model": model, "system_prompt": system, "input": prompt,
                          "temperature": 0.3, "max_output_tokens": max_tokens}),
    ]
    t0 = time.time()
    errors = []
    for path, payload in attempts:
        try:
            body = _post(path, payload, timeout)
            text = _text(body)
            if text.strip():
                return {"model": model, "ok": True, "endpoint": path,
                        "elapsed_s": round(time.time() - t0, 1), "text": text}
            errors.append(f"{path}: empty text (token budget spent on reasoning?)")
        except Exception as exc:                       # noqa: BLE001
            errors.append(f"{path}: {exc}")
    return {"model": model, "ok": False, "elapsed_s": round(time.time() - t0, 1),
            "error": " | ".join(errors)[:400], "text": ""}


def list_models(timeout: int = 15) -> list[str]:
    with urllib.request.urlopen(HOST + "/v1/models", timeout=timeout) as r:
        body = json.loads(r.read())
    return [m.get("id") for m in body.get("data", []) if m.get("id")]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--model", help="single model id")
    ap.add_argument("--models", help="comma-separated model ids (fan-out)")
    ap.add_argument("--prompt")
    ap.add_argument("--prompt-file")
    ap.add_argument("--system",
                    default="You are a meticulous code reviewer. Answer only with concrete, "
                            "checkable findings: file, line, what breaks, severity. No praise, "
                            "no restating the code, no style nits.")
    ap.add_argument("--max-tokens", type=int, default=1400)
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--parallel", type=int, default=3)
    ap.add_argument("--out-dir", default="/tmp/lms_review")
    args = ap.parse_args()

    if args.list:
        for m in list_models():
            print(m)
        return 0

    prompt = args.prompt
    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    if not prompt:
        print("FATAL: give --prompt or --prompt-file", file=sys.stderr)
        return 2
    models = ([args.model] if args.model else []) + \
             ([m.strip() for m in (args.models or "").split(",") if m.strip()])
    models = list(dict.fromkeys(models))
    if not models:
        print("FATAL: give --model or --models", file=sys.stderr)
        return 2

    print(f"# {HOST}: {len(models)} model(s), prompt {len(prompt)} chars", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=max(1, args.parallel)) as pool:
        results = list(pool.map(
            lambda m: ask(m, prompt, args.system, args.max_tokens, args.timeout), models))

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for r in results:
        safe = r["model"].replace("/", "_").replace(":", "_")
        body = (f"# {r['model']}\n\nendpoint: {r.get('endpoint', '-')} · "
                f"{r.get('elapsed_s')}s · ok={r['ok']}\n\n{r['text']}\n"
                if r["ok"] else
                f"# {r['model']}\n\nFAILED: {r['error']}\n")
        (out / f"{safe}.md").write_text(body, encoding="utf-8")
        status = "ok" if r["ok"] else f"FAILED ({r.get('error')})"
        chars = len(r["text"])
        print(f"  {r['model']:<52} {status:<28} {chars:>6} chars  {r.get('elapsed_s')}s")
    print(f"\nreplies -> {out}")
    return 0 if any(r["ok"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
