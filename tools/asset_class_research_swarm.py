"""Per-asset-class deep-research swarm.

For each asset class, queries multiple models (Grok-4, Cerebras qwen-3-235b,
Cerebras gpt-oss-120b) for: (1) candidate new strategies; (2) what is broken;
(3) external data sources; (4) backtest priorities.

Writes per-class report to reports/asset_class_research_<CLASS>_<UTC>.md.
"""
import json
import os
import re
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "reports"
OUT_DIR.mkdir(exist_ok=True)

ASSET_DATA = {
    "FOREX":     {"n": 1343, "wr": 45.6, "pf": 0.29, "status": "stressed"},
    "CRYPTO":    {"n": 7860, "wr": 47.1, "pf": 1.36, "status": "stable"},
    "COMMODITY": {"n": 412,  "wr": 66.7, "pf": 3.77, "status": "stable"},
    "EQUITY":    {"n": 442,  "wr": 53.8, "pf": 1.59, "status": "stable"},
    "ETF":       {"n": 100,  "wr": 60.0, "pf": 1.48, "status": "stable"},
    "BOND":      {"n": 11,   "wr": 54.5, "pf": 0.66, "status": "thin_sample"},
}

PROMPT_TEMPLATE = """You are a quant researcher reviewing a multi-asset trading system.

Asset class: {cls}
Current live numbers: n={n} closed trades, WR={wr}%, PF={pf}, status={status}
Tier 2 target: PF>1.5, WR>50, MDD<20
Tier 1 (Renaissance) target: PF>2, WR>55, MDD<10

Existing infrastructure available:
- alpha_engine/anti_overfit_validator.py (CPCV/PBO/DSR)
- alpha_engine/per_source_volume_cap.py (caps per-source volume share)
- audit_trail/quality_gates.py (BLOCKED_ASSET_STRATEGY_PAIRS, BLACKLISTED_STRATEGIES)
- COT data (CFTC commercial signal already running for COMMODITY)
- yfinance OHLCV; Binance/CoinGecko crypto

Free external data: FRED, Quandl, OANDA, CoinGecko, CME, USDA, Glassnode

Goal: get this class to Tier 2 (PF>1.5, WR>50, MDD<20) over the next 30-60 days.

Respond ONLY with valid JSON, no preamble, no markdown fences:
{{
  "diagnosis": "1-sentence what is broken (or for working class: what is at risk)",
  "candidate_strategies": [
    {{"name": "...", "factor": "...", "expected_pf": 0.0, "data_source": "...", "implementation_effort_hours": 0}}
  ],
  "external_data_to_integrate": ["..."],
  "backtest_priorities_30d": ["..."],
  "kill_or_rehab_existing": ["..."],
  "tier2_attainability_pct": 0
}}

Limits: 3-5 candidates, 2-4 external sources, 3 priorities, 2 kill/rehab items.
"""


def call_grok(prompt, timeout=120):
    key = os.environ.get("X_AI_KEY", "")
    if not key:
        raise RuntimeError("X_AI_KEY missing")
    req = urllib.request.Request(
        "https://api.x.ai/v1/chat/completions",
        data=json.dumps({
            "model": "grok-4-latest",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 1500,
        }).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    r = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    return r["choices"][0]["message"]["content"]


def call_cerebras(model, prompt, timeout=120):
    key = os.environ.get("CEREBRAS_API", "")
    if not key:
        raise RuntimeError("CEREBRAS_API missing")
    req = urllib.request.Request(
        "https://api.cerebras.ai/v1/chat/completions",
        data=json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 1500,
        }).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    r = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    return r["choices"][0]["message"]["content"]


def extract_json(text):
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
        return None


def research_class(cls):
    data = ASSET_DATA[cls]
    prompt = PROMPT_TEMPLATE.format(cls=cls, **data)
    panel = [
        ("grok-4", lambda p: call_grok(p)),
        ("cerebras-llama3.1-8b", lambda p: call_cerebras("llama3.1-8b", p)),
    ]
    results = {}
    for name, fn in panel:
        t0 = time.time()
        print(f"  [{name}] {cls}...", flush=True)
        try:
            raw = fn(prompt)
            parsed = extract_json(raw)
            results[name] = {
                "elapsed_s": round(time.time() - t0, 1),
                "parsed": parsed,
                "raw_tail": raw[-1000:] if not parsed else None,
            }
            print(f"    -> {'OK' if parsed else 'PARSE-FAIL'} ({results[name]['elapsed_s']}s)", flush=True)
        except Exception as e:
            results[name] = {"error": str(e)}
            print(f"    -> ERR {e}", flush=True)
    return results


def write_report(cls, results):
    lines = [f"# Asset-Class Research Swarm - {cls}", ""]
    lines.append(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}")
    d = ASSET_DATA[cls]
    lines.append(f"**Live state:** n={d['n']}, WR={d['wr']}%, PF={d['pf']}, status={d['status']}")
    lines.append("")
    all_candidates = []
    attainabilities = []
    for model, r in results.items():
        p = r.get("parsed") or {}
        lines.append(f"## {model}  (elapsed {r.get('elapsed_s','?')}s)")
        if "error" in r:
            lines.append(f"- ERROR: {r['error']}")
            lines.append("")
            continue
        if not p:
            lines.append(f"- PARSE-FAIL")
            lines.append(f"- tail: `{(r.get('raw_tail') or '')[:300]}`")
            lines.append("")
            continue
        lines.append(f"- **Diagnosis:** {p.get('diagnosis','?')}")
        lines.append(f"- **Tier-2 attainability:** {p.get('tier2_attainability_pct','?')}%")
        for c in (p.get("candidate_strategies") or [])[:5]:
            if isinstance(c, dict):
                lines.append(f"  - candidate: **{c.get('name','?')}** ({c.get('factor','?')}) - expected PF {c.get('expected_pf','?')}, data {c.get('data_source','?')}, ~{c.get('implementation_effort_hours','?')}h")
                all_candidates.append(str(c.get("name","?")))
        for e in (p.get("external_data_to_integrate") or [])[:4]:
            lines.append(f"  - external: {e}")
        for pr in (p.get("backtest_priorities_30d") or [])[:3]:
            lines.append(f"  - priority: {pr}")
        for k in (p.get("kill_or_rehab_existing") or [])[:2]:
            lines.append(f"  - kill/rehab: {k}")
        if isinstance(p.get("tier2_attainability_pct"), (int, float)):
            attainabilities.append(p["tier2_attainability_pct"])
        lines.append("")
    lines.append("## Consensus")
    cand_count = Counter(all_candidates)
    for name, n in cand_count.most_common(5):
        if n >= 2:
            lines.append(f"- candidate **{name}** named by {n} models")
    if attainabilities:
        avg = round(sum(attainabilities) / len(attainabilities), 1)
        lines.append(f"- avg Tier-2 attainability: **{avg}%** across {len(attainabilities)} models")
    out_path = OUT_DIR / f"asset_class_research_{cls}_{time.strftime('%Y_%m_%d_%H%MZ', time.gmtime())}.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  -> {out_path.relative_to(REPO)}")
    return out_path


def main():
    targets = sys.argv[1:] if len(sys.argv) > 1 else ["FOREX", "CRYPTO", "EQUITY", "COMMODITY"]
    for cls in targets:
        if cls not in ASSET_DATA:
            print(f"unknown class: {cls}")
            continue
        print(f"\n=== {cls} ===")
        results = research_class(cls)
        write_report(cls, results)


if __name__ == "__main__":
    main()
