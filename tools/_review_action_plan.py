"""One-shot script: send the action plan to 5 LLMs in parallel for review.

Each provider gets the same prompt + plan; replies saved to
reports/feedback/<provider>-2026-05-01.md.

Stdlib-only HTTP via urllib (mirrors alpha_engine/adversarial_debate.py
provider registry pattern).
"""
from __future__ import annotations

import concurrent.futures as _fut
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLAN = REPO / "reports" / "ACTION_PLAN_2026_05_01_DRAFT.md"
OUT_DIR = REPO / "reports" / "feedback"
OUT_DIR.mkdir(parents=True, exist_ok=True)


PROVIDERS = [
    {
        "name": "deepseek",
        "url": "https://api.deepseek.com/v1/chat/completions",
        "model": "deepseek-chat",
        "key_env": ["DEEPSEEK_API_KEY", "DEEPSEEK_API"],
    },
    {
        "name": "xai-grok",
        "url": "https://api.x.ai/v1/chat/completions",
        "model": "grok-3",
        "key_env": ["XAI_API_KEY", "X_AI_KEY", "GROK_SUPER"],
    },
    {
        "name": "cerebras-qwen-235b",
        "url": "https://api.cerebras.ai/v1/chat/completions",
        "model": "qwen-3-235b-a22b-instruct-2507",
        "key_env": ["CEREBRAS_API_KEY", "CEREBRAS_API"],
    },
    {
        "name": "cerebras-glm-4.7",
        "url": "https://api.cerebras.ai/v1/chat/completions",
        "model": "zai-glm-4.7",
        "key_env": ["CEREBRAS_API_KEY", "CEREBRAS_API"],
    },
    {
        "name": "kimi-k2-6",
        "url": "https://api.moonshot.ai/v1/chat/completions",
        "model": "kimi-k2.6",
        "key_env": ["MOONSHOT_API_KEY", "KIMI_API_KEY"],
    },
]


SYSTEM_PROMPT = """You are a senior quant engineering reviewer evaluating an action plan for a multi-asset hedge-fund-style alpha pipeline. The codebase has the following constraints:

- Wire-Up Rule: every new integration must have a production caller OR be opt-in with explicit wiring plan
- Default-OFF for any new gate or scoring change; 14-day shadow before flip-on
- Each PR ships small (1-3 files typical), with tests + per-PR doc
- safe_push.sh handles concurrency for auto-commit workflows

Reply in 4 sections, total 300-500 words:
A. Confirmed strengths of the plan (what should not change)
B. Surfaced contradictions, blockers, missing prerequisites
C. Recommended deltas to the sequence (move X up, add Y, drop Z)
D. Net verdict: ready-to-execute / needs-rewrite / blocked-by-X

Be specific. Cite item numbers from the plan's sequence table when proposing changes. Don't repeat the plan; assume the operator already read it."""


def _resolve_key(env_list: list[str]) -> str | None:
    for env in env_list:
        v = os.environ.get(env)
        if v and v.strip():
            return v.strip()
    return None


def _post(url: str, key: str, body: dict, timeout: float = 60.0) -> dict:
    raw = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=raw,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (action-plan-reviewer/1.0)",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _ollama_post(url: str, key: str, body: dict, timeout: float = 90.0) -> dict:
    """Ollama Cloud uses /api/chat with a slightly different shape."""
    raw = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=raw,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def review_with(provider: dict, plan_text: str) -> tuple[str, str]:
    """Returns (provider_name, review_markdown_or_error)."""
    key = _resolve_key(provider["key_env"])
    if not key:
        return provider["name"], f"ERROR: no key for {provider['key_env']}"

    user_msg = (
        "Review this draft action plan and reply per the system instructions:\n\n"
        + plan_text
    )

    if provider["name"] == "ollama-cloud":
        body = {
            "model": provider["model"],
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            "stream": False,
        }
        try:
            resp = _ollama_post(provider["url"], key, body)
            content = (resp.get("message") or {}).get("content", "")
            if not content:
                return provider["name"], f"ERROR: empty content; raw={str(resp)[:300]}"
            return provider["name"], content
        except Exception as e:
            return provider["name"], f"ERROR: {e!r}"

    # Provider-specific quirks
    is_reasoning_model = "glm-4.7" in provider["model"] or "thinking" in provider["model"]
    is_kimi = "kimi" in provider["model"].lower()

    body = {
        "model": provider["model"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "max_tokens": 4000 if is_reasoning_model else 800,
        "temperature": 1.0 if is_kimi else 0.2,
    }
    try:
        resp = _post(provider["url"], key, body)
        choices = resp.get("choices") or []
        if not choices:
            return provider["name"], f"ERROR: no choices; raw={str(resp)[:300]}"
        msg = choices[0].get("message") or {}
        content = msg.get("content", "") or msg.get("reasoning_content", "") or msg.get("reasoning", "")
        if not content:
            return provider["name"], f"ERROR: empty content; raw={str(resp)[:300]}"
        return provider["name"], content
    except urllib.error.HTTPError as e:
        body_preview = e.read()[:200].decode("utf-8", errors="replace")
        return provider["name"], f"ERROR HTTP {e.code}: {body_preview}"
    except Exception as e:
        return provider["name"], f"ERROR: {e!r}"


def main():
    plan_text = PLAN.read_text(encoding="utf-8")

    with _fut.ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(review_with, p, plan_text) for p in PROVIDERS]
        results = [f.result(timeout=180) for f in futures]

    summary_lines = ["# AI Review Round 1 — 2026-05-01\n"]
    for name, content in results:
        out = OUT_DIR / f"{name}-action-plan-r1.md"
        out.write_text(content, encoding="utf-8")
        is_err = content.startswith("ERROR")
        status = "ERROR" if is_err else f"OK ({len(content)} chars)"
        print(f"  {name}: {status}")
        summary_lines.append(f"\n## {name}\n\n{content[:5000]}\n\n---\n")

    summary = OUT_DIR / "ROUND1_SUMMARY.md"
    summary.write_text("\n".join(summary_lines), encoding="utf-8")
    print(f"\nFull summary: {summary}")


if __name__ == "__main__":
    main()
