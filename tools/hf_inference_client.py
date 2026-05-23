"""HuggingFace Inference Router client for swarm second-opinions.

Lightweight OpenAI-compatible REST wrapper around
https://router.huggingface.co/v1/chat/completions.

No local GPU/download — provider routing handled by HF (novita, fireworks,
together, etc.). Free tier rate-limited; paid for high volume.

Usage:
    export HF_TOKEN=hf_xxx
    python tools/hf_inference_client.py "What is 2+2?"
    python tools/hf_inference_client.py --model XiaomiMiMo/MiMo-V2-Flash:novita "..."
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request


HF_ROUTER = "https://router.huggingface.co/v1/chat/completions"
DEFAULT_MODEL = "XiaomiMiMo/MiMo-V2-Flash:novita"


def call_hf_router(
    prompt: str,
    model: str = DEFAULT_MODEL,
    *,
    system: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 800,
    timeout: int = 120,
    token: str | None = None,
) -> str:
    """Call the HF Inference Router. Returns assistant message content."""
    key = token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN") or ""
    key = key.strip()
    if not key:
        raise RuntimeError("HF token not set. Set HF_TOKEN or HUGGING_FACE_TOKEN env. Get one at https://huggingface.co/settings/tokens")
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    payload = {
        "model": model,
        "messages": msgs,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    req = urllib.request.Request(
        HF_ROUTER,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (hf-inference-client)",
        },
    )
    r = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    return r["choices"][0]["message"]["content"]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("prompt", nargs="?", default="Who are you?")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--system", default=None)
    p.add_argument("--max-tokens", type=int, default=800)
    args = p.parse_args()
    out = call_hf_router(args.prompt, model=args.model, system=args.system, max_tokens=args.max_tokens)
    print(out)


if __name__ == "__main__":
    main()
