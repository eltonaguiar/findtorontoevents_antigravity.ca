#!/usr/bin/env python3
"""Probe API providers listed in ~/dbpasses.txt for (a) vision input and
(b) server-side web search / browsing.

Keys are read from the user's ~/dbpasses.txt at runtime and never stored here.

Usage:
  python3 tools/model_capability_probe.py keys          # show resolved key map (masked)
  python3 tools/model_capability_probe.py list          # list models per provider
  python3 tools/model_capability_probe.py vision        # live vision probe
  python3 tools/model_capability_probe.py web           # live web-search probe

Results are appended to reports/model_capability_probe_<date>.json
"""
from __future__ import annotations

import base64
import io
import json
import os
import pathlib
import re
import sys
import tempfile
import time
from datetime import date

import requests

DB = pathlib.Path.home() / "dbpasses.txt"
TIMEOUT = 60
HERE = pathlib.Path(__file__).resolve().parent
REPORTS = HERE.parent / "reports"

# ---------------------------------------------------------------- key loading

_LINES: list[str] | None = None


def _lines() -> list[str]:
    global _LINES
    if _LINES is None:
        txt = DB.read_text(errors="ignore") if DB.exists() else ""
        _LINES = [ln.rstrip() for ln in txt.splitlines()]
    return _LINES


TOKEN_RE = re.compile(r"^[A-Za-z0-9_\-\.\+=/~]{16,}$")


def _looks_like_token(v: str) -> bool:
    if not v or "://" in v or " " in v:
        return False
    return bool(TOKEN_RE.match(v))


def key(label: str, occ: int = 0) -> str:
    """Token associated with the `occ`-th line containing `label`.

    Scans forward a few lines, skipping URLs and sub-labels, so both
    `LABEL: value` and `LABEL:\n<url>\n<token>` layouts resolve.
    """
    lines = _lines()
    hits = [i for i, ln in enumerate(lines) if label.lower() in ln.lower()]
    if len(hits) <= occ:
        return ""
    i = hits[occ]
    # inline value after a colon / equals
    m = re.match(r"^\s*[^:=]*[:=]\s*(\S.*)$", lines[i])
    if m and _looks_like_token(m.group(1).strip()):
        return m.group(1).strip()
    for j in range(i + 1, min(i + 7, len(lines))):
        v = lines[j].strip()
        if _looks_like_token(v):
            return v
    return ""


def mask(v: str) -> str:
    if not v:
        return "<missing>"
    return f"{v[:6]}…{v[-4:]} ({len(v)} chars)"


# ---------------------------------------------------------------- providers

def providers() -> dict[str, dict]:
    """name -> {base_url, key, style}"""
    cf_acct = "3c1f2867a7120334ef745ceb9345d9e6"
    p: dict[str, dict] = {}

    def add(name, base, k, style="openai"):
        if k:
            p[name] = {"base": base, "key": k, "style": style}

    add("nvidia", "https://integrate.api.nvidia.com/v1", key("NVIDIA:"))
    add("groq", "https://api.groq.com/openai/v1", key("GROQ FREE KEY"))
    add("cerebras", "https://api.cerebras.ai/v1", key("CEREBRAS_FREE_API_KEY"))
    add("together", "https://api.together.xyz/v1", key("TOGETHER AI API KEY:"))
    add("fireworks", "https://api.fireworks.ai/inference/v1", key("FIREWORKS FREE API KEY:"))
    add("deepinfra", "https://api.deepinfra.com/v1/openai", key("DEEPINFRA API KEY_BEST") or key("DEEPINFRA API KEY:"))
    add("huggingface", "https://router.huggingface.co/v1", key("HUGGING_FACE_TOKEN"))
    add("mistral", "https://api.mistral.ai/v1", key("MISTRAL API KEY:"))
    add("openrouter", "https://openrouter.ai/api/v1", key("OPEN ROUTER API KEY"))
    add("github_models", "https://models.github.ai/inference", key("GITHUB MODELS API KEY:"))
    add("qwen", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1", key("QWEN_API_KEY_FREE"))
    add("qwen_pro", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1", key("QWEN_API_KEY_PRO"))
    add("zai", "https://api.z.ai/api/paas/v4", key("ZAI_API_KEY"))
    add("moonshot", "https://api.moonshot.ai/v1", key("KIMI_MOONSHOT_APIKEY"))
    add("sambanova", "https://api.sambanova.ai/v1", key("SAMBANOVA_API_KEY"))
    add("scaleway", "https://api.scaleway.ai/v1", key("SCALEWAY_SECRET_KEY"))
    add("chutes", "https://llm.chutes.ai/v1", key("CHUTES_API_KEY_FREE"))
    add("novita", "https://api.novita.ai/openai/v1", key("NOVITA API KEY"))
    add("hyperbolic", "https://api.hyperbolic.xyz/v1", key("HYPERBOLIC API KEY"))
    add("siliconflow", "https://api.siliconflow.cn/v1", key("SILICONFLOW.com API KEY"))
    add("modelscope", "https://api-inference.modelscope.cn/v1", key("MODELSCOPE API KEY"))
    add("featherless", "https://api.featherless.ai/v1", key("FEATHER API KEY"))
    add("aimlapi", "https://api.aimlapi.com/v1", key("AIMLAPI.COM"))
    add("nararouter", "https://router.bynara.id/v1", key("NARAROUTER AI API KEY"))
    add("agnes", "https://api.agnesai.ai/v1", key("AGNES AI API KEY"))
    add("upstage", "https://api.upstage.ai/v1", key("UPSTAGE.AI API KEY"))
    add("venice", "https://api.venice.ai/api/v1", key("VENICE_INFERENCE_KEY"))
    add("xiaomi_mimo", "https://token-plan-sgp.xiaomimimo.com/v1", key("XIAOMI_MIMO_TOKEN_PLAN"))
    add("ollama_cloud", "https://ollama.com/v1", key("OLLAMA_CLOUD_KEY"))
    add("bluesminds", "https://api.bluesminds.com/v1", key("BLUESMIND API KEY"))
    add("requesty", "https://router.requesty.ai/v1", key("REQUESTY API KEY"))
    add("orcarouter", "https://api.orcarouter.ai/v1", key("ORCAROUTER.AI"))
    add("llm7", "https://api.llm7.io/v1", key("LLM7_API_KEY_FREE"))
    add("publicai", "https://api.publicai.co/v1", key("PUBLIC AI KEY"))
    add("tokenharbor", "https://api.tokenharbor.ai/v1", key("TOKEN HARBOR API KEY"))
    add("infron", "https://api.infront.ai/v1", key("INFRON API KEY(FREE"))
    add("aionlabs", "https://api.aionlabs.ai/v1", key("AIONLABS API KEY"))
    add("wafer", "https://api.wafer.ai/v1", key("WAFER_API_KEY"))
    add("vercel_ai", "https://api.v0.dev/v1", key("VERCEL AI API KEY"))
    add("ofox", "https://api.ofox.ai/v1", key("OFOX_API_KEY"))

    # first-party paid
    add("deepseek", "https://api.deepseek.com/v1", key("DEEPSEEK_API"))
    add("openai", "https://api.openai.com/v1", key("OPENAI_KEY"))
    add("xai", "https://api.x.ai/v1", key("GROK NEW:"))
    add("anthropic", "https://api.anthropic.com/v1", key("ANTR") or key("ANTROPHIC"), "anthropic")
    add("gemini", "https://generativelanguage.googleapis.com/v1beta", key("GOOGLE GEMINI API KEY:"), "gemini")
    return p


PROV = providers()

# known vision-capable model names, used when /models is unavailable or unhelpful
VISION_HINT = re.compile(
    r"""(?ix)
    (vision|vl|llava|pixtral|qwen[\d.]*-?vl|llama-?4|llama-?3\.2-\d+b-vision|
     scout|maverick|gpt-4o|gpt-4\.1|gpt-5|o3|o4-mini|claude|gemini|
     glm-4\.\dv|glm-4v|internvl|minicpm-v|cogvlm|idefics|molmo|paligemma|
     step-1v|yi-vl|kimi-latest|solar-pro|mistral-small|mistral-medium|
     nemotron.*vl|phi-?[34].*vision|gemma-?3|grok-4|mercury)
    """
)
NEGATIVE_HINT = re.compile(r"(?i)(embed|rerank|guard|moderation|whisper|tts|image-gen|flux|sd-?3|stable-diffusion)")


def _hdr(name: str, extra: dict | None = None) -> dict:
    k = PROV[name]["key"]
    h = {"Authorization": f"Bearer {k}", "Content-Type": "application/json"}
    if name in ("openrouter", "requesty"):
        h["HTTP-Referer"] = "https://findtorontoevents.ca"
        h["X-Title"] = "capability-probe"
    if extra:
        h.update(extra)
    return h


# ---------------------------------------------------------------- model lists

def list_models(name: str) -> list[str]:
    p = PROV[name]
    try:
        if p["style"] == "gemini":
            r = requests.get(f"{p['base']}/models", params={"key": p["key"]}, timeout=TIMEOUT)
            if r.status_code != 200:
                return []
            return [m["name"].split("/")[-1] for m in r.json().get("models", [])]
        if p["style"] == "anthropic":
            r = requests.get(f"{p['base']}/models", headers={"x-api-key": p["key"], "anthropic-version": "2023-06-01"}, timeout=TIMEOUT)
            if r.status_code != 200:
                return []
            return [m["id"] for m in r.json().get("data", [])]
        r = requests.get(f"{p['base']}/models", headers=_hdr(name), timeout=20)
        if r.status_code != 200:
            return []
        data = r.json()
        rows = data.get("data") or data.get("models") or []
        out = []
        for m in rows:
            mid = m.get("id") or m.get("name") or m.get("model") if isinstance(m, dict) else str(m)
            if mid:
                out.append(mid)
        return out
    except Exception as e:  # noqa: BLE001
        print(f"  [{name}] list error: {type(e).__name__}: {e}")
        return []


# ---------------------------------------------------------------- probe image

def probe_image() -> tuple[str, str]:
    """320x140 PNG: red circle + text BANANA-7841. Returns (b64, expected)."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (320, 140), "white")
    d = ImageDraw.Draw(img)
    d.ellipse((10, 20, 110, 120), fill=(220, 30, 40))
    d.text((130, 60), "BANANA-7841", fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode(), "BANANA-7841"


VISION_PROMPT = (
    "Look at the image. Reply with ONLY the exact text written next to the red circle, "
    "and say which colour the circle is. Format: TEXT=<text> COLOUR=<colour>"
)


def openai_chat(name: str, model: str, messages: list, max_tokens=60, extra_body=None):
    body = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0}
    if extra_body:
        body.update(extra_body)
    r = requests.post(f"{PROV[name]['base']}/chat/completions", headers=_hdr(name), json=body, timeout=TIMEOUT)
    return r


def vision_ok(text: str) -> tuple[bool, str]:
    t = (text or "").upper()
    digits = "7841" in t.replace(" ", "")
    word = "BANANA" in t or "BANAN" in t
    red = "RED" in t
    ok = digits and word and red
    return ok, ("text" if word else "-") + ("/digits" if digits else "/-") + ("/red" if red else "/-")


def probe_one(name: str, model: str, b64: str) -> dict:
    """Single image-understanding probe against one model."""
    data_url = f"data:image/png;base64,{b64}"
    style = PROV[name]["style"]
    t0 = time.time()
    status = None
    txt = ""
    try:
        if style == "anthropic":
            body = {
                "model": model, "max_tokens": 64,
                "messages": [{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                    {"type": "text", "text": VISION_PROMPT}]}],
            }
            r = requests.post(f"{PROV[name]['base']}/messages",
                              headers={"x-api-key": PROV[name]["key"], "anthropic-version": "2023-06-01",
                                       "Content-Type": "application/json"}, json=body, timeout=TIMEOUT)
            status = r.status_code
            txt = ("".join(b.get("text", "") for b in r.json().get("content", []))
                   if r.status_code == 200 else r.text[:220])
        elif style == "gemini":
            body = {"contents": [{"parts": [{"inline_data": {"mime_type": "image/png", "data": b64}},
                                            {"text": VISION_PROMPT}]}]}
            r = requests.post(f"{PROV[name]['base']}/models/{model}:generateContent?key={PROV[name]['key']}",
                              json=body, timeout=TIMEOUT)
            status = r.status_code
            if r.status_code == 200:
                j = r.json()
                txt = "".join(p.get("text", "") for p in
                              j.get("candidates", [{}])[0].get("content", {}).get("parts", []))
            else:
                txt = r.text[:220]
        else:
            body = {"model": model, "max_tokens": 64, "temperature": 0, "messages": [
                {"role": "user", "content": [
                    {"type": "text", "text": VISION_PROMPT},
                    {"type": "image_url", "image_url": {"url": data_url}}]}]}
            r = requests.post(f"{PROV[name]['base']}/chat/completions", headers=_hdr(name), json=body, timeout=TIMEOUT)
            status = r.status_code
            if r.status_code == 200:
                j = r.json()
                txt = (j["choices"][0]["message"].get("content") or "") if j.get("choices") else json.dumps(j)[:220]
            else:
                txt = r.text[:220]
        ok, why = vision_ok(txt)
        return {"provider": name, "model": model, "vision": ok, "why": why, "status": status,
                "secs": round(time.time() - t0, 1), "reply": txt[:200].replace("\n", " ")}
    except Exception as e:  # noqa: BLE001
        return {"provider": name, "model": model, "vision": False, "why": f"error:{type(e).__name__}",
                "status": status, "secs": round(time.time() - t0, 1), "reply": str(e)[:200]}


def run_vision(candidates: dict[str, list[str]], workers: int = 8):
    from concurrent.futures import ThreadPoolExecutor

    b64, _ = probe_image()  # BANANA-7841 + red circle
    pairs = [(n, m) for n, ms in candidates.items() for m in ms]
    print(f"probing {len(pairs)} models across {len(candidates)} providers (workers={workers})\n")
    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(lambda pm: probe_one(pm[0], pm[1], b64), pairs))
    for r in sorted(results, key=lambda x: (not x["vision"], x["provider"])):
        tag = "PASS" if r["vision"] else ("ERR " if str(r["why"]).startswith("error") else "FAIL")
        print(f"{tag} {r['provider']:13s} {r['model'][:48]:48s} {str(r['status']):>4s} {r['secs']:5.1f}s {r['why']:8s} :: {r['reply'][:80]!r}")
    return results


WEB_QUERY = "What is one news headline from today, 9 November 2026? Give the source URL."


def run_web() -> list[dict]:
    """Server-side browsing probes: evidence = citations returned by the API."""
    results: list[dict] = []

    def rec(name, model, status, urls, text, note=""):
        results.append({"provider": name, "model": model, "status": status,
                        "citations": urls, "browse": bool(urls), "text": (text or "")[:300], "note": note})
        print(f"{'PASS' if urls else 'FAIL'} {name:13s} {model[:34]:34s} {status} cites={len(urls)} :: {(text or note)[:90]!r}")

    # 1) Gemini native google_search grounding
    try:
        g = PROV["gemini"]
        r = requests.post(f"{g['base']}/models/gemini-2.5-flash:generateContent?key={g['key']}",
                          json={"contents": [{"parts": [{"text": WEB_QUERY}]}],
                                "tools": [{"google_search": {}}]}, timeout=TIMEOUT)
        j = r.json()
        cand = j.get("candidates", [{}])[0]
        gm = cand.get("groundingMetadata", {})
        urls = [c.get("web", {}).get("uri") for c in gm.get("groundingChunks", []) if c.get("web")]
        txt = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
        rec("gemini", "gemini-2.5-flash+google_search", r.status_code, urls, txt)
    except Exception as e:  # noqa: BLE001
        rec("gemini", "gemini-2.5-flash+google_search", None, [], "", f"error:{e}")

    # 2) OpenRouter :online (server-side search, returns url_citation annotations)
    try:
        o = PROV["openrouter"]
        r = requests.post(f"{o['base']}/chat/completions", headers=_hdr("openrouter"),
                          json={"model": "google/gemini-2.5-flash:online", "max_tokens": 250,
                                "messages": [{"role": "user", "content": WEB_QUERY}]}, timeout=TIMEOUT)
        m = (r.json().get("choices") or [{}])[0].get("message", {})
        urls = [a.get("url_citation", {}).get("url") for a in (m.get("annotations") or [])]
        rec("openrouter", "gemini-2.5-flash:online", r.status_code, urls, m.get("content", ""))
    except Exception as e:  # noqa: BLE001
        rec("openrouter", "gemini-2.5-flash:online", None, [], "", f"error:{e}")

    # 3) xAI Responses API + web_search tool (live search_parameters is deprecated)
    try:
        x = PROV["xai"]
        r = requests.post(f"{x['base']}/responses", headers=_hdr("xai"),
                          json={"model": "grok-4.3", "input": WEB_QUERY,
                                "tools": [{"type": "web_search"}]}, timeout=TIMEOUT)
        j = r.json()
        urls, txt = [], ""

        def walk(o):
            if isinstance(o, dict):
                if o.get("url"):
                    urls.append(o["url"])
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)

        walk(j)
        for item in j.get("output", []):
            for c in item.get("content", []) or []:
                if c.get("type") == "output_text":
                    txt += c.get("text", "")
        rec("xai", "grok-4.3+web_search", r.status_code, urls[:6], txt)
    except Exception as e:  # noqa: BLE001
        rec("xai", "grok-4.3+web_search", None, [], "", f"error:{e}")
    return results


def save(kind: str, payload) -> pathlib.Path:
    REPORTS.mkdir(exist_ok=True)
    out = REPORTS / f"model_capability_probe_{date.today().isoformat()}.json"
    existing = json.loads(out.read_text()) if out.exists() else {}
    existing[kind] = payload
    out.write_text(json.dumps(existing, indent=2))
    print(f"\nsaved -> {out}")
    return out


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "keys"

    if cmd == "keys":
        for n, v in sorted(PROV.items()):
            print(f"{n:14s} {mask(v['key']):40s} {v['base']}")
        print(f"\n{len(PROV)} providers resolved from {DB}")
        return 0

    if cmd == "web":
        save("web", run_web())
        return 0

    if cmd == "list":
        from concurrent.futures import ThreadPoolExecutor

        out = {}
        with ThreadPoolExecutor(max_workers=10) as ex:
            fetched = dict(zip(sorted(PROV), ex.map(list_models, sorted(PROV))))
        for n in sorted(PROV):
            models = fetched[n]
            out[n] = models
            vis = [m for m in models if VISION_HINT.search(m) and not NEGATIVE_HINT.search(m)]
            print(f"{n:14s} {len(models):4d} models | vision-ish {len(vis):3d} | e.g. {', '.join(vis[:5]) if vis else '-'}")
        save("models", out)
        return 0

    if cmd == "vision":
        cand_file = REPORTS / f"model_capability_probe_{date.today().isoformat()}.json"
        if not cand_file.exists():
            print("run `list` first")
            return 1
        # explicit candidate file: {"provider": ["model", ...]}
        if len(sys.argv) > 2 and sys.argv[2].endswith(".json"):
            cand = json.loads(pathlib.Path(sys.argv[2]).read_text())
        else:
            models = json.loads(cand_file.read_text()).get("models", {})
            cand = {}
            for n, ms in models.items():
                vis = [m for m in ms if VISION_HINT.search(m) and not NEGATIVE_HINT.search(m)]
                if vis:
                    cand[n] = vis[:6]
            if len(sys.argv) > 2:  # filter providers
                want = set(sys.argv[2].split(","))
                cand = {k: v for k, v in cand.items() if k in want}
        save("vision", run_vision(cand))
        return 0

    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
