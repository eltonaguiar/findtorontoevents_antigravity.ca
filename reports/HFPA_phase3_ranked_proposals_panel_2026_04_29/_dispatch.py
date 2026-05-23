"""Dispatch Phase 3 ranked-proposal prompt to 7 AI panel members concurrently.

Retroactive Phase 3 of THEASK 5-phase plan: re-rank 28 session PRs by expected impact.

3 Cerebras: qwen-3-235b-a22b-instruct-2507, gpt-oss-120b, zai-glm-4.7
4 Ollama Cloud: gpt-oss:120b-cloud, glm-4.6:cloud, kimi-k2.5:cloud, deepseek-v3.1:671b-cloud

Saves verbatim to reports/HFPA_phase3_ranked_proposals_panel_2026_04_29/<provider>_<model>.md
"""
from __future__ import annotations

import concurrent.futures
import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PANEL_DIR = REPO / "reports" / "HFPA_phase3_ranked_proposals_panel_2026_04_29"
PROMPT_PATH = PANEL_DIR / "_PROMPT.md"

CEREBRAS_KEY = os.environ.get("CEREBRAS_API") or os.environ.get("CEREBRAS_API_KEY")

CEREBRAS_MODELS = [
    "qwen-3-235b-a22b-instruct-2507",
    "gpt-oss-120b",
    "zai-glm-4.7",
]
OLLAMA_MODELS = [
    "gpt-oss:120b-cloud",
    "glm-4.6:cloud",
    "kimi-k2.5:cloud",
    "deepseek-v3.1:671b-cloud",
]

SYSTEM = (
    "You are a senior quant on a hedge-fund-grade PR-prioritization panel. "
    "Respond with VALID JSON ONLY. No markdown fences, no commentary. "
    "Cite PR numbers before any recommendation. Use baselines in the briefing."
)

OLLAMA_URL = "http://localhost:11434/api/chat"
CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"


def call_cerebras(model: str, prompt: str, timeout: int = 240) -> dict:
    t0 = time.time()
    if not CEREBRAS_KEY:
        return {"provider": "cerebras", "model": model, "ok": False, "error": "no key", "elapsed_s": 0}
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_completion_tokens": 6144,
    }).encode("utf-8")
    req = urllib.request.Request(
        CEREBRAS_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {CEREBRAS_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "curl/8.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        return {
            "provider": "cerebras",
            "model": model,
            "ok": True,
            "content": content,
            "elapsed_s": round(time.time() - t0, 1),
            "usage": data.get("usage", {}),
        }
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            pass
        return {"provider": "cerebras", "model": model, "ok": False,
                "error": f"HTTP {e.code}: {body}", "elapsed_s": round(time.time() - t0, 1)}
    except Exception as e:
        return {"provider": "cerebras", "model": model, "ok": False,
                "error": f"{type(e).__name__}: {e}", "elapsed_s": round(time.time() - t0, 1)}


def call_ollama(model: str, prompt: str, timeout: int = 360) -> dict:
    t0 = time.time()
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": {"temperature": 0.2, "num_ctx": 16384},
    }).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = data.get("message", {}).get("content", "")
        return {
            "provider": "ollama_cloud",
            "model": model,
            "ok": True,
            "content": content,
            "elapsed_s": round(time.time() - t0, 1),
            "tokens": data.get("eval_count", 0),
        }
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            pass
        return {"provider": "ollama_cloud", "model": model, "ok": False,
                "error": f"HTTP {e.code}: {body}", "elapsed_s": round(time.time() - t0, 1)}
    except Exception as e:
        return {"provider": "ollama_cloud", "model": model, "ok": False,
                "error": f"{type(e).__name__}: {e}", "elapsed_s": round(time.time() - t0, 1)}


def safe_filename(provider: str, model: str) -> str:
    return f"{provider}_{model}".replace("/", "_").replace(":", "_")


def validate_response(content: str) -> dict:
    REQUIRED = {
        "model_id", "reranked_priority", "ordering_critiques",
        "missing_actions_we_didnt_ship", "overall_session_grade",
        "ONE_BIG_LESSON_FOR_NEXT_SESSION",
    }
    txt = content.strip()
    if txt.startswith("```"):
        lines = txt.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        txt = "\n".join(lines).strip()
    if not txt.startswith("{"):
        idx = txt.find("{")
        if idx >= 0:
            txt = txt[idx:]
    if not txt.endswith("}"):
        idx = txt.rfind("}")
        if idx >= 0:
            txt = txt[:idx + 1]
    try:
        parsed = json.loads(txt)
    except json.JSONDecodeError as e:
        return {"valid": False, "reason": f"JSON parse error: {e}", "parsed": None, "missing_fields": []}
    missing = REQUIRED - set(parsed.keys())
    if missing:
        return {"valid": False, "reason": f"missing required fields: {sorted(missing)}",
                "parsed": parsed, "missing_fields": sorted(missing)}
    issues = []
    rr = parsed.get("reranked_priority", [])
    if not isinstance(rr, list) or len(rr) < 5:
        issues.append(f"reranked_priority has {len(rr) if isinstance(rr, list) else 'not a list'} entries; expected >=5")
    crit = parsed.get("ordering_critiques", [])
    if not isinstance(crit, list) or len(crit) < 1:
        issues.append("ordering_critiques expected >=1")
    miss = parsed.get("missing_actions_we_didnt_ship", [])
    if not isinstance(miss, list) or len(miss) < 1:
        issues.append("missing_actions_we_didnt_ship expected >=1")
    if issues:
        return {"valid": False, "reason": "; ".join(issues), "parsed": parsed, "missing_fields": []}
    return {"valid": True, "reason": "ok", "parsed": parsed, "missing_fields": []}


def main():
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    print(f"Prompt: {len(prompt):,} chars")
    print(f"Cerebras key: {'YES' if CEREBRAS_KEY else 'NO'}")
    print(f"Dispatching to {len(CEREBRAS_MODELS)} Cerebras + {len(OLLAMA_MODELS)} Ollama models...")

    tasks = []
    for m in CEREBRAS_MODELS:
        tasks.append(("cerebras", m))
    for m in OLLAMA_MODELS:
        tasks.append(("ollama", m))

    summary = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(tasks)) as ex:
        futures = {}
        for provider, model in tasks:
            if provider == "cerebras":
                f = ex.submit(call_cerebras, model, prompt)
            else:
                f = ex.submit(call_ollama, model, prompt)
            futures[f] = (provider, model)
        for f in concurrent.futures.as_completed(futures):
            provider, model = futures[f]
            r = f.result()
            tag = "OK" if r.get("ok") else "FAIL"
            print(f"  [{tag}] {provider:12s} {model:48s} {r.get('elapsed_s', 0):>5.1f}s", flush=True)
            fname = safe_filename(provider, model)
            out_path = PANEL_DIR / f"{fname}.md"
            if r.get("ok"):
                content = r["content"]
                v = validate_response(content)
                header = (
                    f"# {provider} / {model}\n\n"
                    f"- elapsed_s: {r['elapsed_s']}\n"
                    f"- valid_json: {v['valid']}\n"
                    f"- validation_reason: {v['reason']}\n"
                    f"- missing_fields: {v['missing_fields']}\n\n"
                    f"## Verbatim Response\n\n```\n{content}\n```\n"
                )
                if v["valid"]:
                    header += f"\n## Parsed JSON\n\n```json\n{json.dumps(v['parsed'], indent=2)}\n```\n"
                out_path.write_text(header, encoding="utf-8")
                summary.append({
                    "provider": provider, "model": model, "ok": True,
                    "valid_json": v["valid"], "validation_reason": v["reason"],
                    "elapsed_s": r["elapsed_s"], "file": str(out_path.relative_to(REPO)),
                })
            else:
                err = r.get("error", "unknown")
                out_path.write_text(
                    f"# {provider} / {model}\n\n**FAILED:** {err}\n\nelapsed: {r.get('elapsed_s', 0)}s\n",
                    encoding="utf-8",
                )
                summary.append({
                    "provider": provider, "model": model, "ok": False,
                    "error": err, "elapsed_s": r.get("elapsed_s", 0),
                    "file": str(out_path.relative_to(REPO)),
                })

    summary_path = PANEL_DIR / "_dispatch_summary.json"
    summary_path.write_text(json.dumps({
        "panel": "HFPA_PHASE-3-RANKED-PROPOSALS",
        "dispatched_at": datetime.now(timezone.utc).isoformat(),
        "n_dispatched": len(tasks),
        "n_succeeded": sum(1 for s in summary if s.get("ok")),
        "n_valid_json": sum(1 for s in summary if s.get("valid_json")),
        "results": summary,
    }, indent=2), encoding="utf-8")
    print(f"\nSummary -> {summary_path.relative_to(REPO)}")
    print(f"Succeeded: {sum(1 for s in summary if s.get('ok'))}/{len(tasks)}")
    print(f"Valid JSON: {sum(1 for s in summary if s.get('valid_json'))}/{len(tasks)}")


if __name__ == "__main__":
    main()
