"""
verify_all_keys.py — load every key from ~/dbpasses.txt via the launcher's
parser logic, then ping each provider's chat-completions endpoint with
"1+1?" to confirm the key is alive.

Output: a table with status per provider (OK / 401 DEAD / 402 NOFUNDS /
429 QUOTA / 4xx CONFIG / 5xx UPSTREAM / TIMEOUT / NOKEY) and the actual reply
(first 40 chars) for sanity.

Reads keys file-first (matching launcher behavior). Skips CLI-only tokens
(Cursor/Kilocode/Opencode) since those aren't HTTPS chat APIs.
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

KEYS_FILE = Path(os.environ.get("KEYS_FILE", os.path.expanduser("~/dbpasses.txt")))
PROMPT = "What is 1+1? Reply with just the digit."
TIMEOUT = 30

# (env_var, label_in_file)
LABELS: list[tuple[str, str]] = [
    ("NVIDIA_API_KEY",          "NVIDIA:"),
    ("NVIDIA_API_KEY_ALT",      "NVIDIA ALT KEY:"),
    ("GROQ_API_KEY",            "GROQ FREE KEY:"),
    ("GEMINI_API_KEY",          "GOOGLE GEMINI API KEY:"),
    ("GEMINI_API_KEY_ALT",      "GOOGLE GEMIINI API KEY ALT:"),
    ("GITHUB_MODELS_KEY",       "GITHUB MODELS API KEY:"),
    ("GITHUB_MODELS_KEY2",      "GITHUB MODELS API KEY2:"),
    ("TOGETHER_API_KEY",        "TOGETHER AI API KEY:"),
    ("TOGETHER_API_KEY_ALT",    "TOGETHER AI API KEY ALT:"),
    ("CEREBRAS_API_KEY",        "CEREBRAS_FREE_API_KEY:"),
    ("HF_API_TOKEN_ALT",        "HUGGING_FACE_TOKEN ALT(TRIED FINE GRAIN AND SETTING BUNCH OF CHECKBOXES):"),
    ("HF_API_TOKEN_READ",       "HUGGINF_FACE TOKEN ALT2(READ):"),
    ("FIREWORKS_API_KEY",       "FIREWORKS FREE API KEY:"),
    ("FIREWORKS_API_KEY_ALT",   "FIREWORKS FREE API KEY ALT:"),
    ("DEEPINFRA_API_KEY",       "DEEPINFRA API KEY:"),
    ("DEEPINFRA_API_KEY_ALT",   "DEEPINFRA API KEY ALT:"),
    ("NOUS_API_KEY",            "NOUS API KEY (USE ONLY FREE MODELS):"),
    ("NOUS_API_KEY_ALT",        "NOUS API KEY ALT USE ONLY FREE MODELS:"),
    ("MISTRAL_API_KEY",         "MISTRAL API KEY:"),
    ("MISTRAL_API_KEY_ALT",     "MISTRAL API KEY ALT:"),
    ("MISTRAL_API_KEY_ALT2",    "MISTRAL API KEY ALT2:"),
    ("AIMLAPI_FREE_KEY",        "AIMLAPI.COM"),
    ("AIMLAPI_PAID_KEY",        "AIMLAPIKEY PAID ($20 limit):"),
    ("HYPEREAL_API_KEY",        "HYPEREAL CLOUD API KEY:"),
    ("HYPEREAL_API_KEY_ALT",    "HYPEREAL CLOUD API KEY 2:"),
    ("CF_ACCOUNT_ID",           "Cloudflare account iD:"),
    ("CF_API_TOKEN",            "Cloudflare API key:"),
    ("OPENROUTER_API_KEY",      "OPEN ROUTER API KEY"),
    ("OFOX_AI_KEY",             "OFOX_API_KEY"),
    ("XAI_API_KEY",             "GROK:"),
    ("OLLAMA_CLOUD_KEY",        "OLLAMA_CLOUD_KEY"),
    ("ANTHROPIC_API_KEY",       "ANTROPHIC"),
    ("ANTHROPIC_API_KEY_ALT",   "ANTR_MAY2026"),
    ("DEEPSEEK_API_KEY",        "DEEPSEEK_API"),
    ("MOONSHOT_API_KEY",        "KIMI_MOONSHOT_APIKEY"),
    ("OPENAI_API_KEY",          "OPENAI_KEY"),
    ("QWEN_API_KEY",            "QWEN_API_KEY_PRO"),
    ("CHUTES_API_KEY",          "CHUTES"),
    ("LLM7_API_KEY",            "LLM7_API_KEY_FREE"),
    ("INCEPTION_API_KEY",       "INCEPTION_AI_KEY"),
    ("CURSOR_API_KEY",          "CURSOR_API_KEY"),
    ("KILOCODE_API_KEY",        "KILOCODE_API_KEY"),
    ("OPENCODE_API_KEY",        "OPENCODE_API_KEY"),
]


def load_keys() -> dict[str, str]:
    """Mirror launcher's awk parser in Python."""
    keys: dict[str, str] = {}
    if not KEYS_FILE.exists():
        return keys
    lines = KEYS_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
    for env_name, label in LABELS:
        found_idx = -1
        for i, raw in enumerate(lines):
            if raw.strip() == label:  # strip BOTH sides — file has indented sections
                found_idx = i
                break
        if found_idx < 0:
            continue
        for j in range(found_idx + 1, min(found_idx + 8, len(lines))):
            cand = lines[j].strip()
            if not cand:
                continue
            if re.fullmatch(r"[A-Z][A-Z0-9_]*", cand):
                continue
            if cand.endswith(":"):
                continue
            if cand.startswith("http://") or cand.startswith("https://"):
                continue
            if cand.startswith("==") or cand.startswith("--"):
                continue
            keys[env_name] = cand
            break
    return keys


def _post(url: str, headers: dict, body: dict) -> tuple[int, str]:
    data = json.dumps(body).encode("utf-8")
    # UA header: Cloudflare-fronted endpoints (Groq, Together, Cerebras, AIMLAPI,
    # LLM7) reject the default Python-urllib UA with HTTP 403 "error 1010".
    merged = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) consult-multi/1.0",
        "Accept": "application/json",
        **headers,
    }
    req = urllib.request.Request(url, data=data, headers=merged, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        try:
            body_text = e.read().decode("utf-8", errors="replace")
        except Exception:
            body_text = ""
        return e.code, body_text
    except Exception as e:
        return -1, str(e)


def _extract_reply(body: str) -> str:
    """Pull message.content from an OpenAI-format response, or first 80 chars."""
    try:
        d = json.loads(body)
        if "choices" in d and d["choices"]:
            c = d["choices"][0].get("message", {}).get("content") or d["choices"][0].get("text") or ""
            if c:
                return c.strip()[:50]
        if "content" in d and isinstance(d["content"], list):
            for c in d["content"]:
                if c.get("type") == "text":
                    return c.get("text", "").strip()[:50]
        if "result" in d and isinstance(d["result"], dict) and "response" in d["result"]:
            return str(d["result"]["response"])[:50]
        return body[:80].replace("\n", " ")
    except Exception:
        return body[:80].replace("\n", " ")


def _classify(status: int, body: str) -> str:
    if status == -1:
        return "TIMEOUT/NET"
    if 200 <= status < 300:
        return "OK"
    b = body.lower()
    if status == 401 or "unauthorized" in b or "invalid api key" in b or "invalid_api_key" in b:
        return f"{status} DEAD"
    if status == 402 or "insufficient" in b or "out of funds" in b or "monthly" in b or "credit" in b or "balance" in b:
        return f"{status} NOFUNDS"
    if status == 429 or "rate limit" in b or "too many" in b or "quota" in b or "neuron" in b:
        return f"{status} QUOTA"
    if status == 404:
        return "404 BADMODEL"
    if 400 <= status < 500:
        return f"{status} CONFIG"
    return f"{status} UPSTREAM"


# ---------- per-provider test functions ----------
def t_openai_compat(url: str, key: str, model: str, key_header: str = "Bearer ") -> tuple[str, str]:
    """Generic OpenAI /chat/completions test."""
    s, b = _post(url, {"Authorization": f"{key_header}{key}"}, {
        "model": model, "messages": [{"role": "user", "content": PROMPT}], "max_tokens": 50
    })
    return _classify(s, b), _extract_reply(b)


def t_nvidia(key: str) -> tuple[str, str]:
    return t_openai_compat("https://integrate.api.nvidia.com/v1/chat/completions", key, "meta/llama-3.1-8b-instruct")


def t_groq(key: str) -> tuple[str, str]:
    return t_openai_compat("https://api.groq.com/openai/v1/chat/completions", key, "llama-3.1-8b-instant")


def t_gemini(key: str) -> tuple[str, str]:
    # Gemini native uses ?key= query param
    s, b = _post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={key}",
        {},
        {"contents": [{"parts": [{"text": PROMPT}]}], "generationConfig": {"maxOutputTokens": 50}},
    )
    cls = _classify(s, b)
    reply = ""
    try:
        d = json.loads(b)
        reply = (d.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text") or "")[:50]
    except Exception:
        reply = b[:60]
    return cls, reply


def t_github_models(key: str) -> tuple[str, str]:
    return t_openai_compat("https://models.inference.ai.azure.com/chat/completions", key, "gpt-4o-mini")


def t_together(key: str) -> tuple[str, str]:
    return t_openai_compat("https://api.together.xyz/v1/chat/completions", key, "meta-llama/Meta-Llama-3-8B-Instruct-Lite")


def t_cerebras(key: str) -> tuple[str, str]:
    return t_openai_compat("https://api.cerebras.ai/v1/chat/completions", key, "llama3.1-8b")


def t_hf(key: str) -> tuple[str, str]:
    return t_openai_compat("https://router.huggingface.co/v1/chat/completions", key, "openai/gpt-oss-20b:cheapest")


def t_fireworks(key: str) -> tuple[str, str]:
    return t_openai_compat("https://api.fireworks.ai/inference/v1/chat/completions", key, "accounts/fireworks/models/kimi-k2p5")


def t_deepinfra(key: str) -> tuple[str, str]:
    return t_openai_compat("https://api.deepinfra.com/v1/openai/chat/completions", key, "meta-llama/Meta-Llama-3.1-8B-Instruct")


def t_nous(key: str) -> tuple[str, str]:
    return t_openai_compat("https://inference-api.nousresearch.com/v1/chat/completions", key, "deepseek/deepseek-v4-flash:free")


def t_mistral(key: str) -> tuple[str, str]:
    return t_openai_compat("https://api.mistral.ai/v1/chat/completions", key, "mistral-small-latest")


def t_aimlapi(key: str) -> tuple[str, str]:
    return t_openai_compat("https://api.aimlapi.com/v1/chat/completions", key, "gpt-4o-mini")


def t_hypereal(key: str) -> tuple[str, str]:
    return t_openai_compat("https://api.hypereal.cloud/v1/chat/completions", key, "gpt-5.5-instant")


def t_cloudflare(account_id: str, token: str) -> tuple[str, str]:
    s, b = _post(
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/meta/llama-3.1-8b-instruct",
        {"Authorization": f"Bearer {token}"},
        {"messages": [{"role": "user", "content": PROMPT}], "max_tokens": 50},
    )
    cls = _classify(s, b)
    reply = ""
    try:
        d = json.loads(b)
        reply = str(d.get("result", {}).get("response", b[:60]))[:50]
    except Exception:
        reply = b[:60]
    return cls, reply


def t_openrouter(key: str) -> tuple[str, str]:
    return t_openai_compat("https://openrouter.ai/api/v1/chat/completions", key, "openai/gpt-4o-mini")


def t_ofox(key: str) -> tuple[str, str]:
    return t_openai_compat("https://api.ofox.ai/v1/chat/completions", key, "z-ai/glm-4.7-flash:free")


def t_xai(key: str) -> tuple[str, str]:
    return t_openai_compat("https://api.x.ai/v1/chat/completions", key, "grok-code-fast-1")


def t_ollama_cloud(key: str) -> tuple[str, str]:
    # Ollama cloud uses ssh-ed25519 keys via signed JWT — REST chat at /api/chat
    s, b = _post(
        "https://ollama.com/api/chat",
        {"Authorization": f"Bearer {key}"},
        {"model": "kimi-k2.5:cloud", "messages": [{"role": "user", "content": PROMPT}], "stream": False},
    )
    cls = _classify(s, b)
    reply = ""
    try:
        d = json.loads(b)
        reply = d.get("message", {}).get("content", b[:60])[:50]
    except Exception:
        reply = b[:60]
    return cls, reply


def t_anthropic(key: str) -> tuple[str, str]:
    s, b = _post(
        "https://api.anthropic.com/v1/messages",
        {"x-api-key": key, "anthropic-version": "2023-06-01"},
        {"model": "claude-haiku-4-5-20251001", "max_tokens": 50, "messages": [{"role": "user", "content": PROMPT}]},
    )
    return _classify(s, b), _extract_reply(b)


def t_deepseek(key: str) -> tuple[str, str]:
    return t_openai_compat("https://api.deepseek.com/v1/chat/completions", key, "deepseek-chat")


def t_moonshot(key: str) -> tuple[str, str]:
    return t_openai_compat("https://api.moonshot.ai/v1/chat/completions", key, "moonshot-v1-8k")


def t_openai(key: str) -> tuple[str, str]:
    return t_openai_compat("https://api.openai.com/v1/chat/completions", key, "gpt-4o-mini")


def t_qwen(key: str) -> tuple[str, str]:
    return t_openai_compat("https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions", key, "qwen-turbo")


def t_chutes(key: str) -> tuple[str, str]:
    return t_openai_compat("https://llm.chutes.ai/v1/chat/completions", key, "deepseek-ai/DeepSeek-V3.2-TEE")


def t_llm7(key: str) -> tuple[str, str]:
    return t_openai_compat("https://api.llm7.io/v1/chat/completions", key, "gpt-4o-mini-2024-07-18")


def t_inception(key: str) -> tuple[str, str]:
    return t_openai_compat("https://api.inceptionlabs.ai/v1/chat/completions", key, "mercury")


# ---------- test plan ----------
TESTS: list[tuple[str, str, Any]] = [
    # (display name, env_var(s), test_fn taking the key value(s))
    ("nvidia",            "NVIDIA_API_KEY",          t_nvidia),
    ("nvidia (alt)",      "NVIDIA_API_KEY_ALT",      t_nvidia),
    ("groq",              "GROQ_API_KEY",            t_groq),
    ("gemini",            "GEMINI_API_KEY",          t_gemini),
    ("gemini (alt)",      "GEMINI_API_KEY_ALT",      t_gemini),
    ("github_models",     "GITHUB_MODELS_KEY",       t_github_models),
    ("github_models (2)", "GITHUB_MODELS_KEY2",      t_github_models),
    ("together",          "TOGETHER_API_KEY",        t_together),
    ("together (alt)",    "TOGETHER_API_KEY_ALT",    t_together),
    ("cerebras",          "CEREBRAS_API_KEY",        t_cerebras),
    ("hf (alt)",          "HF_API_TOKEN_ALT",        t_hf),
    ("hf (read)",         "HF_API_TOKEN_READ",       t_hf),
    ("fireworks",         "FIREWORKS_API_KEY",       t_fireworks),
    ("fireworks (alt)",   "FIREWORKS_API_KEY_ALT",   t_fireworks),
    ("deepinfra",         "DEEPINFRA_API_KEY",       t_deepinfra),
    ("deepinfra (alt)",   "DEEPINFRA_API_KEY_ALT",   t_deepinfra),
    ("nous",              "NOUS_API_KEY",            t_nous),
    ("nous (alt)",        "NOUS_API_KEY_ALT",        t_nous),
    ("mistral",           "MISTRAL_API_KEY",         t_mistral),
    ("mistral (alt)",     "MISTRAL_API_KEY_ALT",     t_mistral),
    ("mistral (alt2)",    "MISTRAL_API_KEY_ALT2",    t_mistral),
    ("aimlapi (free)",    "AIMLAPI_FREE_KEY",        t_aimlapi),
    ("aimlapi (paid)",    "AIMLAPI_PAID_KEY",        t_aimlapi),
    ("hypereal",          "HYPEREAL_API_KEY",        t_hypereal),
    ("hypereal (alt)",    "HYPEREAL_API_KEY_ALT",    t_hypereal),
    ("cloudflare",        ("CF_ACCOUNT_ID", "CF_API_TOKEN"), t_cloudflare),
    ("openrouter",        "OPENROUTER_API_KEY",      t_openrouter),
    ("ofox",              "OFOX_AI_KEY",             t_ofox),
    ("xai (grok)",        "XAI_API_KEY",             t_xai),
    ("ollama_cloud",      "OLLAMA_CLOUD_KEY",        t_ollama_cloud),
    ("anthropic",         "ANTHROPIC_API_KEY",       t_anthropic),
    ("anthropic (alt)",   "ANTHROPIC_API_KEY_ALT",   t_anthropic),
    ("deepseek",          "DEEPSEEK_API_KEY",        t_deepseek),
    ("moonshot (kimi)",   "MOONSHOT_API_KEY",        t_moonshot),
    ("openai",            "OPENAI_API_KEY",          t_openai),
    ("qwen",              "QWEN_API_KEY",            t_qwen),
    ("chutes",            "CHUTES_API_KEY",          t_chutes),
    ("llm7",              "LLM7_API_KEY",            t_llm7),
    ("inception",         "INCEPTION_API_KEY",       t_inception),
]


def main() -> int:
    keys = load_keys()
    print(f"loaded {len(keys)} keys from {KEYS_FILE}\n")
    results: list[tuple[str, str, str]] = []

    def run(item):
        name, env, fn = item
        try:
            if isinstance(env, tuple):
                vals = tuple(keys.get(e) for e in env)
                if not all(vals):
                    return (name, "NOKEY", "—")
                cls, reply = fn(*vals)
            else:
                k = keys.get(env)
                if not k:
                    return (name, "NOKEY", "—")
                cls, reply = fn(k)
            return (name, cls, reply)
        except Exception as e:
            return (name, "EXCEPTION", str(e)[:50])

    with cf.ThreadPoolExecutor(max_workers=10) as ex:
        for r in ex.map(run, TESTS):
            results.append(r)
            print(f"  {r[0]:<22} {r[1]:<14} {r[2]}")
    print()

    ok = [r for r in results if r[1] == "OK"]
    dead = [r for r in results if "DEAD" in r[1]]
    nofunds = [r for r in results if "NOFUNDS" in r[1]]
    quota = [r for r in results if "QUOTA" in r[1]]
    nokey = [r for r in results if r[1] == "NOKEY"]
    other = [r for r in results if r not in ok + dead + nofunds + quota + nokey]
    print(f"SUMMARY: {len(ok)} OK · {len(dead)} DEAD · {len(nofunds)} NOFUNDS · {len(quota)} QUOTA · {len(nokey)} NOKEY · {len(other)} OTHER")
    return 0


if __name__ == "__main__":
    sys.exit(main())
