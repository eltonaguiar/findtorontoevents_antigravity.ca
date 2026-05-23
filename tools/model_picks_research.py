"""Multi-model picks research — per asset class.

For each model (local Ollama + cloud APIs), ask:
  1. Top 3 picks for {asset_class} right now
  2. Factors / data points referenced
  3. What additional data would they fetch for swing/short-term entry

Aggregates into reports/model_picks_research_<UTC>.md grouped by asset class.

Designed for sequential execution (12GB VRAM constraint on local models).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "reports"
OUT_DIR.mkdir(exist_ok=True)

# Local Ollama panel — sequential to fit 12GB VRAM
LOCAL_PANEL = [
    {"name": "qwen2.5-coder:14b",   "role": "code-specialist (Alibaba)",   "kind": "ollama", "num_gpu": -1, "num_ctx": 8192},
    {"name": "qwen3:14b",            "role": "Qwen3 general (Alibaba)",    "kind": "ollama", "num_gpu": -1, "num_ctx": 8192},
    {"name": "deepseek-r1:14b",      "role": "reasoning (DeepSeek)",        "kind": "ollama", "num_gpu": -1, "num_ctx": 8192},
    {"name": "devstral-small-2",     "role": "code-patches (Mistral)",      "kind": "ollama", "num_gpu": -1, "num_ctx": 8192},
    {"name": "ernie-coder",          "role": "thinking (Baidu)",            "kind": "ollama", "num_gpu": 0,  "num_ctx": 6144},
    {"name": "glm-4.7-flash",        "role": "alt-lineage (Zhipu)",         "kind": "ollama", "num_gpu": -1, "num_ctx": 8192},
    {"name": "phi3.5:latest",        "role": "compact reasoning (Microsoft)", "kind": "ollama", "num_gpu": -1, "num_ctx": 4096},
    {"name": "gemma3:4b",            "role": "compact (Google)",            "kind": "ollama", "num_gpu": -1, "num_ctx": 4096},
]

# Ollama Cloud (free tier, runs via local ollama with :cloud suffix)
OLLAMA_CLOUD_PANEL = [
    {"name": "kimi-k2-thinking:cloud",  "role": "Moonshot Kimi K2 Thinking (Ollama Cloud)", "kind": "ollama", "num_gpu": -1, "num_ctx": 8192},
    {"name": "qwen3-coder:480b-cloud",  "role": "Qwen3 Coder 480B (Ollama Cloud)",          "kind": "ollama", "num_gpu": -1, "num_ctx": 8192},
    {"name": "deepseek-v3.1:671b-cloud","role": "DeepSeek V3.1 671B (Ollama Cloud)",        "kind": "ollama", "num_gpu": -1, "num_ctx": 8192},
    {"name": "gpt-oss:120b-cloud",       "role": "GPT-OSS 120B (Ollama Cloud)",              "kind": "ollama", "num_gpu": -1, "num_ctx": 8192},
    {"name": "glm-4.6:cloud",            "role": "GLM-4.6 (Ollama Cloud)",                    "kind": "ollama", "num_gpu": -1, "num_ctx": 8192},
]

# REST cloud panel
REST_CLOUD_PANEL = [
    {"name": "grok-4-latest",      "role": "Grok-4 (X_AI)",            "kind": "xai",       "env": "X_AI_KEY"},
    {"name": "mercury-2",          "role": "Mercury 2 (Inception)",    "kind": "inception", "env": "INCEPTION_AI_KEY"},
    {"name": "moonshot-v1-32k",    "role": "Kimi K2 (Moonshot REST)",  "kind": "moonshot",  "env": "KIMI_MOONSHOT_APIKEY"},
]

ASSET_CLASSES = ["CRYPTO", "EQUITY", "FOREX", "COMMODITY", "ETF", "BOND"]

PROMPT_TEMPLATE = """You are a quant analyst. Asset class: {asset_class}

Current live state from /audit dashboard:
{state}

Please answer in STRICT JSON, no preamble, no markdown fences:

{{
  "top_picks": [
    {{"symbol": "...", "direction": "LONG|SHORT", "rationale": "1-sentence why", "timeframe": "swing|short-term"}}
  ],
  "factors_used": ["list 3-5 specific factors/indicators you would weight"],
  "data_points_to_fetch": ["list 3-5 specific data feeds you would pull for entry decision"],
  "swing_trade_setup": "1-2 sentences on entry/exit logic for swing trades on this asset class",
  "short_term_setup": "1-2 sentences on entry/exit logic for 1-3 day trades"
}}

Limits: max 3 top_picks, 5 factors, 5 data points. Symbols must be tradeable (e.g. BTCUSDT, SPY, EURUSD, ZC=F).
"""


def call_ollama(model_cfg: dict, prompt: str, timeout: int = 600) -> str:
    payload = {
        "model": model_cfg["name"],
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_ctx": model_cfg.get("num_ctx", 6144),
            "num_predict": 1024,
            "num_gpu": model_cfg.get("num_gpu", -1),
        },
    }
    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())["response"]


def call_rest(model_cfg: dict, prompt: str, timeout: int = 120) -> str:
    urls = {
        "xai":       "https://api.x.ai/v1/chat/completions",
        "inception": "https://api.inceptionlabs.ai/v1/chat/completions",
        "moonshot":  "https://api.moonshot.ai/v1/chat/completions",
    }
    env_name = model_cfg["env"]
    key = (os.environ.get(env_name) or "").strip()
    if not key:
        # Multi-env fallback
        for alt in {
            "X_AI_KEY":             ["GROK_SUPER", "XAI_API_KEY"],
            "KIMI_MOONSHOT_APIKEY": ["KIMI_API_KEY", "MOONSHOT_API_KEY"],
        }.get(env_name, []):
            key = (os.environ.get(alt) or "").strip()
            if key:
                break
    if not key:
        raise RuntimeError(f"missing env {env_name}")
    payload = {
        "model": model_cfg["name"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 1024,
    }
    req = urllib.request.Request(
        urls[model_cfg["kind"]],
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            "User-Agent": "Mozilla/5.0 (model-picks-research)",
        },
    )
    r = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    return r["choices"][0]["message"]["content"]


def unload_ollama(name: str) -> None:
    try:
        urllib.request.urlopen(
            urllib.request.Request(
                "http://localhost:11434/api/generate",
                data=json.dumps({"model": name, "keep_alive": 0}).encode(),
                headers={"Content-Type": "application/json"},
            ),
            timeout=30,
        ).read()
    except Exception:
        pass


def extract_json(text: str) -> dict | None:
    if "</think>" in text:
        text = text.split("</think>", 1)[1]
    m = re.search(r"<response>\s*(.+?)\s*</response>", text, flags=re.DOTALL)
    if m:
        text = m.group(1)
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
        cleaned = re.sub(r",\s*([}\]])", r"\1", text[start:end])
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return None


def load_asset_state() -> dict[str, str]:
    """Build a state-summary string per asset class from dashboard_data.json."""
    p = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
    if not p.exists():
        return {ac: "(no live data)" for ac in ASSET_CLASSES}
    d = json.loads(p.read_text(encoding="utf-8"))
    ach = d.get("performance", {}).get("asset_class_health", {})
    out = {}
    for ac in ASSET_CLASSES:
        m = ach.get(ac, {}) or {}
        out[ac] = (
            f"n={m.get('resolved_n','?')}, "
            f"WR={m.get('win_rate','?')}%, "
            f"PF={m.get('profit_factor','?')}, "
            f"status={m.get('status','?')}, "
            f"sizing_allowed={m.get('sizing_allowed','?')}"
        )
    return out


def run_panel(panel: list[dict], asset_class: str, state: str) -> dict:
    """Run one panel against one asset class."""
    prompt = PROMPT_TEMPLATE.format(asset_class=asset_class, state=state)
    results = {}
    for cfg in panel:
        name = cfg["name"]
        t0 = time.time()
        print(f"    [{name}] {asset_class}...", flush=True)
        try:
            if cfg["kind"] == "ollama":
                raw = call_ollama(cfg, prompt)
            else:
                raw = call_rest(cfg, prompt)
            parsed = extract_json(raw)
            results[name] = {
                "role": cfg["role"],
                "kind": cfg["kind"],
                "elapsed_s": round(time.time() - t0, 1),
                "parsed": parsed,
                "raw_tail": raw[-1500:] if not parsed else None,
            }
            ok = "OK" if parsed else "PARSE-FAIL"
            print(f"      -> {ok} ({results[name]['elapsed_s']}s)", flush=True)
        except Exception as e:
            results[name] = {"role": cfg["role"], "kind": cfg["kind"], "error": str(e)[:200]}
            print(f"      -> ERR {str(e)[:80]}", flush=True)
        if cfg["kind"] == "ollama":
            unload_ollama(name)
            time.sleep(1)
    return results


def write_report(all_results: dict, out_path: Path) -> None:
    lines = [
        "# Multi-Model Picks Research — Per Asset Class",
        "",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "Each model was given the live `asset_class_health` snapshot and asked: top 3 picks,",
        "factors used, data points to fetch, swing-trade setup, short-term setup.",
        "",
        "## Live state (asset_class_health input)",
        "",
        "| Class | Snapshot |",
        "|---|---|",
    ]
    state = load_asset_state()
    for ac in ASSET_CLASSES:
        lines.append(f"| {ac} | {state[ac]} |")
    lines.append("")
    for ac in ASSET_CLASSES:
        lines += [f"## {ac}", ""]
        per_class = all_results.get(ac, {})
        for model, r in per_class.items():
            p = r.get("parsed") or {}
            lines.append(f"### {model} — {r.get('role','?')}  (elapsed {r.get('elapsed_s','?')}s)")
            if "error" in r:
                lines.append(f"- ERROR: {r['error']}")
                lines.append("")
                continue
            if not p:
                lines.append("- PARSE-FAIL")
                lines.append(f"- tail: `{(r.get('raw_tail') or '')[:300]}`")
                lines.append("")
                continue
            picks = p.get("top_picks") or []
            if picks:
                lines.append("**Top picks:**")
                for pk in picks[:3]:
                    if isinstance(pk, dict):
                        lines.append(
                            f"- **{pk.get('symbol','?')}** {pk.get('direction','?')} "
                            f"({pk.get('timeframe','?')}) — {pk.get('rationale','?')}"
                        )
            for k in ("factors_used", "data_points_to_fetch"):
                vs = p.get(k) or []
                if vs:
                    lines.append(f"**{k.replace('_',' ').title()}:**")
                    for v in vs[:5]:
                        lines.append(f"- {v}")
            for k in ("swing_trade_setup", "short_term_setup"):
                v = p.get(k)
                if v:
                    lines.append(f"**{k.replace('_',' ').title()}:** {v}")
            lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nwrote {out_path.relative_to(REPO)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default="all", choices=["local", "cloud-rest", "cloud-ollama", "all"])
    ap.add_argument("--classes", default="", help="comma-separated; default all 6")
    args = ap.parse_args()

    panels = []
    if args.panel in ("local", "all"):
        panels.append(("local", LOCAL_PANEL))
    if args.panel in ("cloud-rest", "all"):
        panels.append(("cloud-rest", REST_CLOUD_PANEL))
    if args.panel in ("cloud-ollama", "all"):
        panels.append(("cloud-ollama", OLLAMA_CLOUD_PANEL))

    classes = [c.strip() for c in args.classes.split(",") if c.strip()] or ASSET_CLASSES

    state = load_asset_state()
    all_results: dict = {}
    for ac in classes:
        print(f"\n=== {ac} === ({state.get(ac, '?')})")
        all_results[ac] = {}
        for label, panel in panels:
            print(f"  panel={label}")
            partial = run_panel(panel, ac, state.get(ac, "?"))
            all_results[ac].update(partial)

    stamp = datetime.now(timezone.utc).strftime("%Y_%m_%d_%H%MZ")
    out_path = OUT_DIR / f"model_picks_research_{stamp}.md"
    write_report(all_results, out_path)


if __name__ == "__main__":
    main()
