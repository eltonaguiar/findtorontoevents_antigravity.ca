"""
Local Ollama swarm PR-spec reviewer.

Fans out same PR spec to 5 diverse local models, collects structured JSON
verdicts, writes per-model outputs to .planning/prs_2026_05_12/swarm_reviews/.
Designed for 12GB VRAM: sequential model load with keep_alive=0 between models.

Usage:
    python tools/local_swarm_review.py --pr PR-A
    python tools/local_swarm_review.py --all
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SPECS = REPO / ".planning" / "prs_2026_05_12" / "PR_SPECS.md"
OUT_DIR = REPO / ".planning" / "prs_2026_05_12" / "swarm_reviews"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PANEL = [
    {"name": "qwen2.5-coder:14b",  "role": "code-specialist (Alibaba)",   "kind": "ollama", "num_gpu": -1, "num_ctx": 8192},
    {"name": "deepseek-r1:14b",    "role": "reasoning (DeepSeek)",        "kind": "ollama", "num_gpu": -1, "num_ctx": 8192},
    {"name": "devstral-small-2",   "role": "code-patches (Mistral)",      "kind": "ollama", "num_gpu": -1, "num_ctx": 8192},
    {"name": "ernie-coder",        "role": "thinking (Baidu)",            "kind": "ollama", "num_gpu": 0,  "num_ctx": 6144},
    {"name": "glm-4.7-flash",      "role": "alt-lineage (Zhipu)",         "kind": "ollama", "num_gpu": -1, "num_ctx": 8192},
]

# Cloud-API tier — appended when --cloud flag passed. Requires env vars.
CLOUD_PANEL = [
    {"name": "grok-4-latest",                       "role": "frontier (X_AI/Grok)",       "kind": "xai",      "env": "X_AI_KEY"},
    {"name": "llama3.1-8b",                         "role": "fast-Llama (Cerebras)",      "kind": "cerebras", "env": "CEREBRAS_API"},
    {"name": "gpt-oss-120b",                        "role": "OpenAI-OSS (Cerebras)",      "kind": "cerebras", "env": "CEREBRAS_API"},
    {"name": "qwen-3-235b-a22b-instruct-2507",      "role": "frontier-Qwen (Cerebras)",   "kind": "cerebras", "env": "CEREBRAS_API"},
    {"name": "mercury-2",                           "role": "Mercury 2 (Inception Labs)", "kind": "inception","env": "INCEPTION_AI_KEY"},
    {"name": "moonshot-v1-32k",                     "role": "Kimi K2 (Moonshot)",         "kind": "moonshot", "env": "KIMI_MOONSHOT_APIKEY"},
    # MiMo via HF Router removed — free tier depleted (HTTP 402). Re-enable
    # if HF credits/PRO added.
]

REVIEW_PROMPT = """You are reviewing a software-engineering PR spec for a multi-asset trading dashboard. Be terse, blunt, evidence-based.

ROLE: {role}

PR SPEC:
---
{spec}
---

Output ONLY valid JSON, no preamble, no markdown fences:

{{
  "verdict": "approve" | "needs_changes" | "reject",
  "must_fix": ["short concern with file:line if relevant"],
  "should_fix": ["short concern"],
  "questions": ["clarifying question"],
  "risk_score_0_10": 0,
  "frontend_impact": true | false
}}

Limits: max 3 items per list. Score 0=trivial, 10=production-breaking.
"""


def load_specs() -> dict[str, str]:
    """Parse PR_SPECS.md into {PR-A: spec_text, ...}."""
    text = SPECS.read_text(encoding="utf-8")
    sections = re.split(r"^## (PR-[A-Z])\b", text, flags=re.MULTILINE)
    out = {}
    for i in range(1, len(sections), 2):
        pr_id = sections[i]
        body = sections[i + 1].split("\n---")[0].strip()
        out[pr_id] = f"## {pr_id}\n{body}"
    return out


def unload(model_cfg: dict) -> None:
    if model_cfg.get("kind", "ollama") != "ollama":
        return  # cloud models stateless
    try:
        urllib.request.urlopen(
            urllib.request.Request(
                "http://localhost:11434/api/generate",
                data=json.dumps({"model": model_cfg["name"], "keep_alive": 0}).encode(),
                headers={"Content-Type": "application/json"},
            ),
            timeout=30,
        ).read()
    except Exception:
        pass


def query(model_cfg: dict, prompt: str, timeout: int = 900) -> str:
    kind = model_cfg.get("kind", "ollama")
    if kind == "ollama":
        payload = {
            "model": model_cfg["name"],
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_ctx": model_cfg["num_ctx"],
                "num_predict": 1536,
                "num_gpu": model_cfg["num_gpu"],
            },
        }
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        return json.loads(urllib.request.urlopen(req, timeout=timeout).read())["response"]
    # Env fallback chains (multiple names per provider)
    env_name = model_cfg["env"]
    key = (os.environ.get(env_name) or "").strip()
    if not key:
        _ENV_FALLBACKS = {
            "HF_TOKEN":             ["HUGGING_FACE_TOKEN", "HUGGINGFACE_TOKEN"],
            "X_AI_KEY":             ["GROK_SUPER", "XAI_API_KEY"],
            "KIMI_MOONSHOT_APIKEY": ["KIMI_API_KEY", "MOONSHOT_API_KEY"],
        }
        for alt in _ENV_FALLBACKS.get(env_name, []):
            key = (os.environ.get(alt) or "").strip()
            if key:
                break
    if not key:
        raise RuntimeError(f"missing env {env_name}")
    urls = {
        "xai":       "https://api.x.ai/v1/chat/completions",
        "cerebras":  "https://api.cerebras.ai/v1/chat/completions",
        "hf":        "https://router.huggingface.co/v1/chat/completions",
        "inception": "https://api.inceptionlabs.ai/v1/chat/completions",
        "moonshot":  "https://api.moonshot.ai/v1/chat/completions",
    }
    payload = {
        "model": model_cfg["name"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 1024,
    }
    req = urllib.request.Request(
        urls[kind],
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            "User-Agent": "Mozilla/5.0 (swarm-review)",
        },
    )
    r = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    return r["choices"][0]["message"]["content"]


def extract_json(text: str) -> dict | None:
    # Strip ERNIE thinking/response wrappers + DeepSeek-R1 think blocks
    if "</think>" in text:
        text = text.split("</think>", 1)[1]
    if "</thought_process>" in text:
        text = text.split("</thought_process>", 1)[1]
    # ERNIE wraps final answer in <response>...</response>
    m = re.search(r"<response>\s*(.+?)\s*</response>", text, flags=re.DOTALL)
    if m:
        text = m.group(1)
    # Strip code fences; brace-balanced scan below handles strings + nested braces
    text = re.sub(r"```(?:json)?\s*|\s*```", "", text.strip(), flags=re.MULTILINE)
    start = text.find("{")
    if start < 0:
        return None
    depth, in_str, esc, end = 0, False, False, -1
    for i in range(start, len(text)):
        ch = text[i]
        if esc:
            esc = False
            continue
        if ch == "\\":
            esc = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end < 0:
        return None
    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError:
        # Last-ditch: trailing-comma cleanup
        cleaned = re.sub(r",\s*([}\]])", r"\1", text[start:end])
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return None


def review_one(pr_id: str, spec: str, panel: list[dict] | None = None) -> dict:
    results = {"pr_id": pr_id, "reviews": {}}
    for cfg in (panel if panel is not None else PANEL):
        model = cfg["name"]
        t0 = time.time()
        print(f"  [{model}] reviewing {pr_id}...", flush=True)
        try:
            raw = query(cfg, REVIEW_PROMPT.format(role=cfg["role"], spec=spec))
            parsed = extract_json(raw)
            results["reviews"][model] = {
                "role": cfg["role"],
                "kind": cfg.get("kind", "ollama"),
                "elapsed_s": round(time.time() - t0, 1),
                "parsed": parsed,
                "raw_tail": raw[-1500:] if not parsed else None,
            }
            ok = "OK" if parsed else "PARSE-FAIL"
            print(f"    -> {ok} ({results['reviews'][model]['elapsed_s']}s)", flush=True)
        except urllib.error.HTTPError as e:
            results["reviews"][model] = {"role": cfg["role"], "error": f"HTTP {e.code}"}
            print(f"    -> ERROR HTTP {e.code}", flush=True)
        except Exception as e:
            results["reviews"][model] = {"role": cfg["role"], "error": str(e)}
            print(f"    -> ERROR {e}", flush=True)
        unload(cfg)
        time.sleep(2)
    return results


def captain_merge(all_results: list[dict]) -> str:
    lines = ["# Swarm Consensus — Merge Captain", ""]
    for r in all_results:
        pr_id = r["pr_id"]
        verdicts = [rv["parsed"]["verdict"] for rv in r["reviews"].values()
                    if rv.get("parsed") and "verdict" in rv["parsed"]]
        must_fix = {}
        should_fix = {}
        questions = {}
        scores = []
        for model, rv in r["reviews"].items():
            p = rv.get("parsed") or {}
            for item in (p.get("must_fix") or [])[:3]:
                must_fix.setdefault(item, []).append(model)
            for item in (p.get("should_fix") or [])[:3]:
                should_fix.setdefault(item, []).append(model)
            for item in (p.get("questions") or [])[:3]:
                questions.setdefault(item, []).append(model)
            if isinstance(p.get("risk_score_0_10"), (int, float)):
                scores.append(p["risk_score_0_10"])
        if not verdicts:
            lines.append(f"## {pr_id} — NO VERDICTS PARSED")
            continue
        approve = verdicts.count("approve")
        needs = verdicts.count("needs_changes")
        reject = verdicts.count("reject")
        consensus = ("APPROVE" if approve > (needs + reject)
                     else "REJECT" if reject > approve
                     else "NEEDS CHANGES")
        avg_risk = round(sum(scores) / len(scores), 1) if scores else "?"
        lines += [
            f"## {pr_id} — {consensus} (risk avg={avg_risk}/10)",
            f"Verdicts: approve={approve}, needs_changes={needs}, reject={reject}",
            "",
        ]
        # corroborated concerns (≥2 models)
        corr_must = {k: v for k, v in must_fix.items() if len(v) >= 2}
        if corr_must:
            lines.append("**MUST-FIX (≥2 models agree):**")
            for k, models in corr_must.items():
                lines.append(f"- {k}  _({', '.join(models)})_")
            lines.append("")
        corr_should = {k: v for k, v in should_fix.items() if len(v) >= 2}
        if corr_should:
            lines.append("**SHOULD-FIX (≥2 models agree):**")
            for k, models in corr_should.items():
                lines.append(f"- {k}  _({', '.join(models)})_")
            lines.append("")
        if questions:
            top_q = sorted(questions.items(), key=lambda x: -len(x[1]))[:5]
            lines.append("**Top questions:**")
            for k, models in top_q:
                lines.append(f"- {k}  _({len(models)} model{'s' if len(models) > 1 else ''})_")
            lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr", help="single PR id e.g. PR-A")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    specs = load_specs()
    if not specs:
        sys.exit(f"no PR specs found in {SPECS}")

    targets = list(specs.keys()) if args.all else ([args.pr] if args.pr else [])
    if not targets:
        sys.exit("specify --pr PR-A or --all")

    all_results = []
    for pr_id in targets:
        if pr_id not in specs:
            print(f"skip unknown {pr_id}")
            continue
        print(f"\n=== {pr_id} ===")
        result = review_one(pr_id, specs[pr_id])
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = OUT_DIR / f"{pr_id}_swarm.json"
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"  wrote {out_path}")
        all_results.append(result)

    consensus_path = OUT_DIR / "CONSENSUS.md"
    consensus_path.write_text(captain_merge(all_results), encoding="utf-8")
    print(f"\nconsensus -> {consensus_path}")


if __name__ == "__main__":
    main()
