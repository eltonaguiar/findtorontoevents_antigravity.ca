#!/usr/bin/env python3
"""Audit EVERY provider credential we hold and report which ones actually serve free inference.

Why
---
The LiteLLM proxy had drifted badly from reality:
  * NVIDIA (one of the most generous free tiers: build.nvidia.com credits) was
    wired to `meta/llama-3.1-8b-instruct`, retired 2026-08-26 -> HTTP 410 Gone
    on all 5 deployments, so NVIDIA was silently contributing nothing.
  * Google Gemini free tier was hammered until RPD quota exhaustion.
  * Kilo AI Gateway was not wired at all despite serving 11 free models with
    NO API KEY required.
Each of those was found by hand, one at a time. This tool does the sweep.

What it checks per provider
---------------------------
  1. CREDENTIAL   — is a key present in ~/dbpasses.txt?
  2. CATALOG      — GET {base}/models, how many models does the account see?
  3. FREE         — which models look free (explicit :free id, or zero price)?
  4. INFERENCE    — one real 8-token completion. A 200 from /models proves
                    nothing: models get retired (410), accounts run dry (402),
                    and free tiers get gated to first-party apps (429).

Secret handling
---------------
Keys are NEVER printed. Only a masked fingerprint (first 4 + last 3) is shown,
and the report is safe to commit.

Usage
-----
  python3 tools/free_provider_audit.py                 # full sweep, markdown
  python3 tools/free_provider_audit.py --json          # machine readable
  python3 tools/free_provider_audit.py --only gemini,nvidia
  python3 tools/free_provider_audit.py --out reports/free_provider_audit.md
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

KEYS_FILE = Path(os.environ.get("KEYS_FILE", Path.home() / "dbpasses.txt"))
TIMEOUT_LIST = 20
TIMEOUT_PROBE = 60
PROBE_TOKENS = 8

# Several gateways sit behind Cloudflare, which blocks the default
# `python-requests/2.x` agent with a bare 403/1010. That produced false
# "NO FUNDS/AUTH" verdicts against perfectly healthy accounts. Always send a
# browser-shaped UA.
USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")


# ---------------------------------------------------------------------------
# Provider registry.
#   key_labels: exact lines in ~/dbpasses.txt (parse_key() style: value is the
#               next non-empty, non-label line)
#   free_hint:  extra substrings that mark a model as free on that provider
# ---------------------------------------------------------------------------
def P(name: str, base: str, key_labels: list[str], **kw: Any) -> dict[str, Any]:
    return {"name": name, "base": base, "key_labels": key_labels,
            "free_hints": kw.get("free_hints", []),
            "probe_model": kw.get("probe_model"),
            "auth": kw.get("auth", "bearer"),
            "no_key": kw.get("no_key", False),
            "id_marker_only": kw.get("id_marker_only", False),
            "note": kw.get("note", "")}


SPECS: list[dict[str, Any]] = [
    # --- confirmed-good free tiers we should never lose -------------------
    P("kilo", "https://ai-gateway.kilo.ai/api/v1", ["KILOCODE_API_KEY"],
      no_key=True, id_marker_only=True,
      note="public catalog; :free models work anonymously (~200 req/h)"),
    P("nvidia", "https://integrate.api.nvidia.com/v1", ["NVIDIA:", "NVIDIA ALT KEY:"]),
    P("gemini", "https://generativelanguage.googleapis.com/v1beta/openai",
      ["GOOGLE GEMINI API KEY:", "GOOGLE GEMIINI API KEY ALT:", "GOOGLE GEMINI API KEY ALT2:"]),
    P("groq", "https://api.groq.com/openai/v1", ["GROQ FREE KEY:", "GROQ_API_KEY"]),
    P("cerebras", "https://api.cerebras.ai/v1", ["CEREBRAS_FREE_API_KEY:"]),
    P("openrouter", "https://openrouter.ai/api/v1", ["OPEN ROUTER API KEY (OPENROUTER)"],
      free_hints=[":free"], id_marker_only=True),
    P("together", "https://api.together.xyz/v1", ["TOGETHER AI API KEY:"]),
    P("fireworks", "https://api.fireworks.ai/inference/v1", ["FIREWORKS FREE API KEY:"]),
    P("deepinfra", "https://api.deepinfra.com/v1/openai",
      ["DEEPINFRA API KEY:", "DEEPINFRA API KEY ALT:", "DEEPINFRA API KEY_BEST:"]),
    P("nous", "https://inference-api.nousresearch.com/v1",
      ["NOUS API KEY (USE ONLY FREE MODELS):", "NOUS API KEY ALT USE ONLY FREE MODELS:"],
      free_hints=[":free"], id_marker_only=True),
    P("mistral", "https://api.mistral.ai/v1", ["MISTRAL API KEY:"]),
    P("github_models", "https://models.github.ai/inference",
      ["GITHUB MODELS API KEY:", "GITHUB MODELS API KEY2:"]),
    P("llm7", "https://api.llm7.io/v1", ["LLM7_API_KEY_FREE"]),
    # --- free tiers we suspected but never wired -------------------------
    P("sambanova", "https://api.sambanova.ai/v1", ["SAMBANOVA_API_KEY:",
                                                   "SAMBANOVA CLOUD API KEY(expires in 1 year after 2026-11-02 Nov 2 2026)"]),
    P("qwen_dashscope", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
      ["QWEN_API_KEY_FREE", "QWEN_API_KEY_PRO"]),
    P("wafer", "https://pass.wafer.ai/v1", ["WAFER_API_KEY:"]),
    P("chutes", "https://llm.chutes.ai/v1", ["CHUTES_API_KEY_FREE"]),
    P("zai", "https://api.z.ai/api/paas/v4", ["ZAI_API_KEY", "ZAI_API_KEY2:",
                                              "ZAI_API_KEY3_NOV2026:"], free_hints=["flash"]),
    P("venice", "https://api.venice.ai/api/v1", ["VENICE_INFERENCE_KEY"]),
    P("nscale", "https://inference.api.nscale.com/v1", ["NSCALE_API_KEY:"]),
    P("novita", "https://api.novita.ai/v3/openai", ["NOVITA API KEY:"]),
    P("hyperbolic", "https://api.hyperbolic.xyz/v1", ["HYPERBOLIC API KEY :"]),
    P("publicai", "https://api.publicai.co/v1", ["PUBLIC AI KEY"]),
    P("modelscope", "https://api-inference.modelscope.cn/v1", ["MODELSCOPE API KEY :"]),
    P("featherless", "https://api.featherless.ai/v1", ["FEATHER API KEY:"]),
    P("siliconflow", "https://api.siliconflow.cn/v1", ["SILICONFLOW.com API KEY:"]),
    P("requesty", "https://router.requesty.ai/v1", ["REQUESTY API KEY (200 free requests a day)"]),
    P("nararouter", "https://router.bynara.id/v1", ["NARAROUTER AI API KEY https://router.bynara.id/keys (15 req/min free tier)"]),
    P("agnes", "", ["AGNES AI API KEY (10 req/min tier)"], note="no documented base URL"),
    P("upstage", "https://api.upstage.ai/v1", ["UPSTAGE.AI API KEY"]),
    P("orca", "", ["ORCAROUTER.AI"], note="base URL undocumented"),
    P("opencode", "https://opencode.ai/zen/v1", ["OPENCODE_OPENAI_KEY_NOV112026",
                                                 "OPENCODE.AI API KEY test (try Big Pickle or other free models)",
                                                 "OPENCODE_API_KEY"]),
    # --- keyless providers -------------------------------------------------
    P("ovh_ai", "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1", [], no_key=True,
      note="anonymous free tier, ~2 req/min"),
    P("pollinations", "https://text.pollinations.ai/openai", [], no_key=True,
      note="anonymous free tier, ~1 req at a time"),
    # --- paid / not an LLM chat API ---------------------------------------
    P("deepseek", "https://api.deepseek.com", ["DEEPSEEK_API"]),
    P("moonshot", "https://api.moonshot.ai/v1", ["KIMI_MOONSHOT_APIKEY", "KIMI_MOONSHOT_APIKEY2"]),
    P("xai", "https://api.x.ai/v1", ["GROK NEW:", "GROK NEW2:"]),
    P("bluesmind", "https://api.bluesminds.com/v1", ["BLUESMIND API KEY"]),
    P("xiaomi_mimo", "https://token-plan-sgp.xiaomimimo.com/v1", ["XIAOMI_MIMO_TOKEN_PLAN"]),
    P("aimlapi", "https://api.aimlapi.com/v1", ["AIMLAPI.COM", "AIMLAPIKEY PAID ($20 limit):"]),
    P("hypereal", "https://api.hypereal.cloud/v1", ["HYPEREAL CLOUD API KEY:", "HYPEREAL CLOUD API KEY 2:"]),
    P("ofox", "", ["OFOX_API_KEY"], note="base URL undocumented"),
    P("openai", "https://api.openai.com/v1", ["OPENAI_KEY"]),
    P("anthropic", "https://api.anthropic.com/v1", ["ANTROPHIC"], note="not OpenAI-compatible"),
    P("cloudflare", "", ["Cloudflare account iD:"], note="needs account id + Workers AI path"),
]


# ---------------------------------------------------------------------------
# Credential parsing (mirrors parse_key() in tools/start_litellm_proxy.sh)
# ---------------------------------------------------------------------------
def load_labels() -> dict[str, str]:
    """label -> value, mirroring parse_key() in tools/start_litellm_proxy.sh.

    Rejects anything that is obviously not a credential. Two real mis-parses this
    guards against (both observed in this file):
        WAFER_API_KEY:            <- label
        ZAI_API_URL: https://...  <- inline "NAME: value" annotation line
        QWEN_API_URL: https://... <- same shape under QWEN_API_KEY_FREE
    """
    if not KEYS_FILE.exists():
        return {}
    lines = [l.strip() for l in KEYS_FILE.read_text(errors="replace").splitlines()]
    out: dict[str, str] = {}
    for i, line in enumerate(lines):
        if not line or line.startswith("="):
            continue
        key = re.sub(r"\s+", " ", line.rstrip(":").strip())
        for j in range(i + 1, min(i + 4, len(lines))):
            v = lines[j]
            if not v or v.startswith("=") or v.endswith(":") or v.isupper():
                continue
            if "://" in v or "TODO" in v.upper():
                continue
            if re.match(r"^[A-Z0-9_ ]{4,}:\s", v):   # inline "OTHER_KEY: value"
                continue
            if len(v) < 8:                            # not a plausible credential
                continue
            out.setdefault(key, v)
            break
    return out


def resolve_key(labels: dict[str, str], spec: dict[str, Any]) -> tuple[str | None, str | None]:
    for lab in spec["key_labels"]:
        want = re.sub(r"\s+", " ", lab.rstrip(":").strip())
        for have, val in labels.items():
            if have == want:
                return val, have
    return None, None


def mask(key: str | None) -> str:
    if not key:
        return "-"
    k = str(key)
    return f"{k[:4]}…{k[-3:]}(len {len(k)})"


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def _headers(spec: dict[str, Any], key: str | None) -> dict[str, str]:
    h = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if spec["auth"] == "anthropic":
        h.update({"x-api-key": key or "", "anthropic-version": "2023-06-01"})
        return h
    if key:
        h["Authorization"] = f"Bearer {key}"
    return h


def _model_ids(payload: Any) -> list[str]:
    rows: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        for k in ("data", "models", "results"):
            if isinstance(payload.get(k), list):
                rows = [x for x in payload[k] if isinstance(x, dict)]
                break
    elif isinstance(payload, list):
        rows = [x for x in payload if isinstance(x, dict)]
    ids: list[str] = []
    for r in rows:
        mid = r.get("id") or r.get("name") or r.get("model")
        if not mid:
            continue
        mid = str(mid)
        if mid.startswith("models/"):
            mid = mid.split("/", 1)[1]
        ids.append(mid)
    return ids


def _price_is_zero(row_pricing: Any) -> bool:
    if not isinstance(row_pricing, dict):
        return False
    vals = []
    for v in row_pricing.values():
        if isinstance(v, dict):
            vals.extend(v.values())
        else:
            vals.append(v)
    nums = []
    for v in vals:
        try:
            nums.append(float(v))
        except (TypeError, ValueError):
            continue
    return bool(nums) and max(nums) == 0.0


# Model families that are not chat-completions endpoints. Probing them produces
# a misleading 404 ("model_not_found") and hides whether the account works at all
# (OVH: the alphabetically first model was `nvr-tts-de-de`; NVIDIA: `adept/fuyu-8b`).
_NON_CHAT = re.compile(
    r"(embed|rerank|tts|asr|whisper|transcri|moderat|guard|safety|omni-moderation"
    r"|dall-e|stable-diffusion|flux|vision-only|-vl-\d|ocr)", re.I)


def _chat_likelihood(mid: str) -> int:
    """Rank candidates so the probe hits a real chat endpoint first."""
    score = 0
    low = mid.lower()
    if _NON_CHAT.search(mid):
        score -= 100
    if any(t in low for t in ("flash", "instruct", "chat", "turbo", "mini", "small", "8b", "20b")):
        score += 5
    if any(t in low for t in ("gpt-oss", "llama", "qwen", "glm", "nemotron", "deepseek", "gpt-4", "gpt-5")):
        score += 3
    if "pro" in low or "ultra" in low or "large" in low:
        score -= 2          # heavier, slower, more often quota-gated
    if any(t in low for t in ("preview", "exp", "alpha", "deprecat")):
        score -= 2
    return score


def _free_candidates(spec: dict[str, Any], rows: list[dict[str, Any]]) -> list[str]:
    hints = [h.lower() for h in spec["free_hints"]]
    marker_only = spec.get("id_marker_only", False)
    found: list[str] = []
    for row in rows:
        mid = str(row.get("id") or row.get("name") or "")
        if mid.startswith("models/"):
            mid = mid.split("/", 1)[1]
        if not mid:
            continue
        low = mid.lower()
        by_marker = ":free" in low or low.endswith("-free") or low.endswith("/free") \
            or any(h in low for h in hints)
        by_price = (not marker_only) and _price_is_zero(row.get("pricing"))
        if by_marker or by_price:
            found.append(mid)
    # de-dup, then rank so explicit ":free" markers and chat-shaped ids lead
    seen, ordered = set(), []
    for mid in found:
        if mid in seen:
            continue
        seen.add(mid)
        ordered.append(mid)
    ordered.sort(key=lambda m: (0 if (":free" in m.lower() or m.lower().endswith("-free")) else 1,
                                -_chat_likelihood(m)))
    return ordered


def audit(spec: dict[str, Any], labels: dict[str, str]) -> dict[str, Any]:
    res: dict[str, Any] = {
        "provider": spec["name"], "base": spec["base"] or "-",
        "key": None, "key_label": None, "key_fp": "-",
        "catalog": 0, "free": [], "probe": "-", "status": "UNKNOWN",
        "detail": "", "note": spec["note"],
    }
    key, lab = resolve_key(labels, spec)
    res["key_label"] = lab
    res["key_fp"] = mask(key)
    if not key and not spec["no_key"]:
        res["status"] = "NO KEY"
        return res
    if not spec["base"]:
        res["status"] = "NOT CHECKED"
        res["detail"] = spec["note"] or "no base URL"
        return res

    # 1. catalog
    try:
        r = requests.get(f"{spec['base']}/models", headers=_headers(spec, key), timeout=TIMEOUT_LIST)
    except Exception as exc:
        res["status"] = "UNREACHABLE"
        res["detail"] = str(exc)[:90]
        return res
    if r.status_code != 200:
        res["status"] = f"HTTP {r.status_code}"
        res["detail"] = r.text[:120].replace("\n", " ")
        return res

    rows: list[dict[str, Any]] = []
    raw = r.json()
    for k in ("data", "models", "results"):
        if isinstance(raw, dict) and isinstance(raw.get(k), list):
            rows = [x for x in raw[k] if isinstance(x, dict)]
            break
    ids = _model_ids(raw)
    res["catalog"] = len(ids)

    free = _free_candidates(spec, rows)
    res["free"] = free[:40]

    # 2. inference probe — the part that actually matters.
    #    Try several candidates: a single miss says nothing (the catalog may lead
    #    with a retired model, a TTS model, or a heavy quota-gated "pro" variant).
    candidates = (free or sorted(ids, key=lambda m: -_chat_likelihood(m)))[:4]
    if not candidates:
        res["status"] = "NO MODELS"
        return res
    attempts: list[str] = []
    for model_id in candidates:
        try:
            pr = requests.post(
                f"{spec['base']}/chat/completions",
                json={"model": model_id, "messages": [{"role": "user", "content": "ok"}],
                      "max_tokens": PROBE_TOKENS},
                headers={**_headers(spec, key), "Content-Type": "application/json"},
                timeout=TIMEOUT_PROBE,
            )
        except Exception as exc:
            attempts.append(f"{model_id}: ERR {str(exc)[:40]}")
            continue
        if pr.status_code == 200:
            res["status"] = "USABLE"
            res["probe"] = f"200 via {model_id}"
            return res
        body = pr.text[:150].replace("\n", " ")
        attempts.append(f"{model_id}: {pr.status_code} {body[:60]}")
        res["probe"] = f"{pr.status_code} via {model_id}: {body[:90]}"
        if pr.status_code in (401, 402, 403):
            res["status"] = "NO FUNDS/AUTH"
            return res
        if pr.status_code == 429:
            res["status"] = "RATE LIMITED"
        elif pr.status_code == 410:
            res["status"] = "RETIRED MODEL"
    if res["status"] == "UNKNOWN":
        res["status"] = "PROBE FAILED"
    res["detail"] = (res["detail"] + " | " + " ; ".join(attempts[:4])).strip(" |")
    return res


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def render(results: list[dict[str, Any]], as_json: bool) -> str:
    if as_json:
        return json.dumps(results, indent=2)
    order = {"USABLE": 0, "RATE LIMITED": 1, "RETIRED MODEL": 2, "MODEL GONE": 3,
             "NO FUNDS/AUTH": 4, "PROBE FAILED": 5, "NO KEY": 6, "NOT CHECKED": 7}
    results = sorted(results, key=lambda r: (order.get(r["status"], 9), r["provider"]))
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out = [f"# Free-provider audit — {ts}", "",
           "Keys are masked; this report is safe to publish.", "",
           "| Provider | Status | Catalog | Free models | Probed via | Key |",
           "|---|---|---:|---:|---|---|"]
    for r in results:
        out.append(
            f"| `{r['provider']}` | {r['status']} | {r['catalog']} | {len(r['free'])} | "
            f"{r['probe'][:60] or '-'} | {r['key_fp']} |")
    usable = [r for r in results if r["status"] == "USABLE"]
    out += ["", f"## USABLE ({len(usable)})", ""]
    for r in usable:
        out.append(f"- **{r['provider']}** — {r['catalog']} models, "
                   f"{len(r['free'])} free-ish, verified via `{r['probe'].split('via ')[-1]}`")
        if r["free"]:
            out.append(f"  - e.g. {', '.join('`'+m+'`' for m in r['free'][:6])}")
    broken = [r for r in results if r["status"] not in ("USABLE", "NO KEY")]
    if broken:
        out += ["", f"## CHECK ({len(broken)})", ""]
        for r in broken:
            out.append(f"- **{r['provider']}** [{r['status']}] {r['detail'][:120]} {r['probe'][:80]}")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit every provider credential for working free inference")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--only", default=None, help="comma separated provider names")
    ap.add_argument("--out", default=None)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    labels = load_labels()
    if not labels:
        print(f"[audit] could not read credentials from {KEYS_FILE}", file=sys.stderr)
        return 2

    specs = SPECS
    if args.only:
        want = {s.strip() for s in args.only.split(",")}
        specs = [s for s in SPECS if s["name"] in want]
    print(f"[audit] probing {len(specs)} providers from {KEYS_FILE.name}", file=sys.stderr)

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(audit, s, labels): s["name"] for s in specs}
        for fut in as_completed(futures):
            try:
                results.append(fut.result())
            except Exception as exc:
                results.append({"provider": futures[fut], "status": "ERROR", "catalog": 0,
                                "free": [], "probe": str(exc)[:60], "detail": "",
                                "key_fp": "-", "key_label": None, "base": "-", "note": ""})

    text = render(results, args.json)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"[audit] wrote {args.out}", file=sys.stderr)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
