"""
benchmark_providers.py — measure tokens-per-second (TPS) for each free-mode
upstream, hitting each one DIRECTLY (not via proxy shuffle).

Each provider gets the same prompt designed to elicit ~150-200 tokens output.
Wall time is measured from request start to last byte. TPS = completion_tokens
/ wall_seconds. Time-to-first-token is also captured when streaming is used.

Sorted descending by TPS. Run with `--rounds N` to average multiple trials.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

KEYS_FILE = Path("/home/eaguiar2015/dbpasses.txt")
PROMPT = ("Write a single paragraph of exactly 4 sentences describing the "
          "city of Toronto's downtown waterfront. Be specific and concrete. "
          "Do not add bullets, headings, or follow-up questions.")
MAX_TOKENS = 220


def load_keys() -> dict[str, str]:
    """Mirror launcher parser — file-first, sub-label skip, indented-section safe."""
    LABELS = {
        "NVIDIA_API_KEY":          "NVIDIA:",
        "NVIDIA_API_KEY_ALT":      "NVIDIA ALT KEY:",
        "GROQ_API_KEY":            "GROQ FREE KEY:",
        "GROQ_API_KEY_ALT":        "GROQ_API_KEY",
        "GEMINI_API_KEY":          "GOOGLE GEMINI API KEY:",
        "GEMINI_API_KEY_ALT":      "GOOGLE GEMIINI API KEY ALT:",
        "GITHUB_MODELS_KEY":       "GITHUB MODELS API KEY:",
        "GITHUB_MODELS_KEY2":      "GITHUB MODELS API KEY2:",
        "TOGETHER_API_KEY":        "TOGETHER AI API KEY:",
        "TOGETHER_API_KEY_ALT":    "TOGETHER AI API KEY ALT:",
        "CEREBRAS_API_KEY":        "CEREBRAS_FREE_API_KEY:",
        "FIREWORKS_API_KEY":       "FIREWORKS FREE API KEY:",
        "FIREWORKS_API_KEY_ALT":   "FIREWORKS FREE API KEY ALT:",
        "DEEPINFRA_API_KEY_ALT":   "DEEPINFRA API KEY ALT:",
        "NOUS_API_KEY":            "NOUS API KEY (USE ONLY FREE MODELS):",
        "NOUS_API_KEY_ALT":        "NOUS API KEY ALT USE ONLY FREE MODELS:",
        "MISTRAL_API_KEY":         "MISTRAL API KEY:",
        "OPENROUTER_API_KEY":      "OPEN ROUTER API KEY",
        "OFOX_AI_KEY":             "OFOX_API_KEY",
        "LLM7_API_KEY":            "LLM7_API_KEY_FREE",
        "HYPEREAL_API_KEY":        "HYPEREAL CLOUD API KEY:",
        "BLUESMIND_API_KEY":       "BLUESMIND API KEY",
        "KILOCODE_API_KEY":        "KILOCODE_API_KEY",
        "OPENCODE_API_KEY":        "OPENCODE_API_KEY",
        # Paid-mode keys for the extended benchmark
        "ANTHROPIC_API_KEY_ALT":   "ANTR_MAY2026",
        "ANTHROPIC_API_KEY":       "ANTROPHIC",
        "DEEPSEEK_API_KEY":        "DEEPSEEK_API",
        "MOONSHOT_API_KEY":        "KIMI_MOONSHOT_APIKEY",
        "XAI_API_KEY":             "GROK:",
        "XAI_API_KEY_ALT":         "GROK NEW2:",
        "AIMLAPI_PAID_KEY":        "AIMLAPIKEY PAID ($20 limit):",
    }
    keys: dict[str, str] = {}
    lines = KEYS_FILE.read_text().splitlines()
    for env, label in LABELS.items():
        idx = next((i for i, l in enumerate(lines) if l.strip() == label), -1)
        if idx < 0:
            continue
        for j in range(idx + 1, min(idx + 8, len(lines))):
            cand = lines[j].strip()
            if not cand: continue
            if re.fullmatch(r"[A-Z][A-Z0-9_]*", cand): continue
            if cand.endswith(":"): continue
            if cand.startswith(("http://", "https://", "==", "--")): continue
            keys[env] = cand
            break
    return keys


def _post(url, headers, body, timeout=60):
    data = json.dumps(body).encode()
    merged = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 benchmark/1.0",
        "Accept": "application/json",
        **headers,
    }
    req = urllib.request.Request(url, data=data, headers=merged, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")[:300]
    except Exception as e:
        return -1, str(e)[:200]


def _extract_tokens(body):
    """Pull completion_tokens from OpenAI-format usage block."""
    try:
        d = json.loads(body)
        u = d.get("usage", {})
        ct = u.get("completion_tokens") or u.get("output_tokens") or 0
        c = d.get("choices", [{}])[0].get("message", {}).get("content") or ""
        if not ct and c:
            ct = max(1, len(c) // 4)  # rough estimate
        return int(ct), c[:60]
    except Exception:
        return 0, body[:60]


# Test functions — return (status_code, body, label)
def t_openai_chat(url, key, model, key_header="Bearer "):
    s, b = _post(url, {"Authorization": f"{key_header}{key}"},
                 {"model": model, "messages": [{"role": "user", "content": PROMPT}], "max_tokens": MAX_TOKENS})
    return s, b


def t_anthropic(key, model="claude-haiku-4-5-20251001"):
    s, b = _post(
        "https://api.anthropic.com/v1/messages",
        {"x-api-key": key, "anthropic-version": "2023-06-01"},
        {"model": model, "max_tokens": MAX_TOKENS, "messages": [{"role": "user", "content": PROMPT}]},
    )
    if s == 200:
        try:
            d = json.loads(b)
            txt = next((c.get("text", "") for c in d.get("content", []) if c.get("type") == "text"), "")
            ct = d.get("usage", {}).get("output_tokens") or max(1, len(txt) // 4)
            b = json.dumps({"choices": [{"message": {"content": txt}}], "usage": {"completion_tokens": ct}})
        except Exception:
            pass
    return s, b


def t_gemini(key):
    s, b = _post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={key}",
        {},
        {"contents": [{"parts": [{"text": PROMPT}]}], "generationConfig": {"maxOutputTokens": MAX_TOKENS}},
    )
    # Convert gemini format to common parsing path
    if s == 200:
        try:
            d = json.loads(b)
            txt = d.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            ct = d.get("usageMetadata", {}).get("candidatesTokenCount") or max(1, len(txt) // 4)
            b = json.dumps({"choices": [{"message": {"content": txt}}], "usage": {"completion_tokens": ct}})
        except Exception:
            pass
    return s, b


# (name, fn_partial) — closures bind key + model
def build_tests(keys):
    tests = []
    def add(name, fn):
        tests.append((name, fn))

    if keys.get("GROQ_API_KEY"):
        add("groq llama-3.1-8b",
            lambda: t_openai_chat("https://api.groq.com/openai/v1/chat/completions", keys["GROQ_API_KEY"], "llama-3.1-8b-instant"))
    if keys.get("GROQ_API_KEY_ALT"):
        add("groq llama-3.1-8b (alt)",
            lambda: t_openai_chat("https://api.groq.com/openai/v1/chat/completions", keys["GROQ_API_KEY_ALT"], "llama-3.1-8b-instant"))
    if keys.get("NVIDIA_API_KEY"):
        add("nvidia llama-3.1-8b",
            lambda: t_openai_chat("https://integrate.api.nvidia.com/v1/chat/completions", keys["NVIDIA_API_KEY"], "meta/llama-3.1-8b-instruct"))
    if keys.get("NVIDIA_API_KEY_ALT"):
        add("nvidia llama-3.1-8b (alt)",
            lambda: t_openai_chat("https://integrate.api.nvidia.com/v1/chat/completions", keys["NVIDIA_API_KEY_ALT"], "meta/llama-3.1-8b-instruct"))
    if keys.get("CEREBRAS_API_KEY"):
        add("cerebras llama3.1-8b",
            lambda: t_openai_chat("https://api.cerebras.ai/v1/chat/completions", keys["CEREBRAS_API_KEY"], "llama3.1-8b"))
    if keys.get("FIREWORKS_API_KEY"):
        add("fireworks kimi-k2p5",
            lambda: t_openai_chat("https://api.fireworks.ai/inference/v1/chat/completions", keys["FIREWORKS_API_KEY"], "accounts/fireworks/models/kimi-k2p5"))
    if keys.get("DEEPINFRA_API_KEY_ALT"):
        add("deepinfra llama-3.1-8b",
            lambda: t_openai_chat("https://api.deepinfra.com/v1/openai/chat/completions", keys["DEEPINFRA_API_KEY_ALT"], "meta-llama/Meta-Llama-3.1-8B-Instruct"))
    if keys.get("TOGETHER_API_KEY"):
        add("together llama-3-8b-lite",
            lambda: t_openai_chat("https://api.together.xyz/v1/chat/completions", keys["TOGETHER_API_KEY"], "meta-llama/Meta-Llama-3-8B-Instruct-Lite"))
    if keys.get("MISTRAL_API_KEY"):
        add("mistral small-latest",
            lambda: t_openai_chat("https://api.mistral.ai/v1/chat/completions", keys["MISTRAL_API_KEY"], "mistral-small-latest"))
    if keys.get("GEMINI_API_KEY"):
        add("gemini flash-latest", lambda: t_gemini(keys["GEMINI_API_KEY"]))
    if keys.get("GEMINI_API_KEY_ALT"):
        add("gemini flash (alt)", lambda: t_gemini(keys["GEMINI_API_KEY_ALT"]))
    if keys.get("GITHUB_MODELS_KEY"):
        add("github_models gpt-4o-mini",
            lambda: t_openai_chat("https://models.inference.ai.azure.com/chat/completions", keys["GITHUB_MODELS_KEY"], "gpt-4o-mini"))
    if keys.get("GITHUB_MODELS_KEY2"):
        add("github_models (alt)",
            lambda: t_openai_chat("https://models.inference.ai.azure.com/chat/completions", keys["GITHUB_MODELS_KEY2"], "gpt-4o-mini"))
    if keys.get("NOUS_API_KEY"):
        add("nous deepseek-v4-flash:free",
            lambda: t_openai_chat("https://inference-api.nousresearch.com/v1/chat/completions", keys["NOUS_API_KEY"], "deepseek/deepseek-v4-flash:free"))
    if keys.get("OPENROUTER_API_KEY"):
        add("openrouter ring-1t",
            lambda: t_openai_chat("https://openrouter.ai/api/v1/chat/completions", keys["OPENROUTER_API_KEY"], "inclusionai/ring-2.6-1t"))
    if keys.get("OFOX_AI_KEY"):
        add("ofox glm-4.7-flash:free",
            lambda: t_openai_chat("https://api.ofox.ai/v1/chat/completions", keys["OFOX_AI_KEY"], "z-ai/glm-4.7-flash:free"))
    if keys.get("LLM7_API_KEY"):
        add("llm7 gpt-4o-mini",
            lambda: t_openai_chat("https://api.llm7.io/v1/chat/completions", keys["LLM7_API_KEY"], "gpt-4o-mini-2024-07-18"))
    if keys.get("HYPEREAL_API_KEY"):
        add("hypereal gpt-5.5-instant",
            lambda: t_openai_chat("https://api.hypereal.cloud/v1/chat/completions", keys["HYPEREAL_API_KEY"], "gpt-5.5-instant"))
    if keys.get("BLUESMIND_API_KEY"):
        add("bluesmind llama-3.1-8b",
            lambda: t_openai_chat("https://api.bluesminds.com/v1/chat/completions", keys["BLUESMIND_API_KEY"], "meta/llama-3.1-8b-instruct"))
    if keys.get("KILOCODE_API_KEY"):
        add("kilocode nemotron-120b:free",
            lambda: t_openai_chat("https://kilocode.ai/api/openrouter/chat/completions", keys["KILOCODE_API_KEY"], "nvidia/nemotron-3-super-120b-a12b:free"))
    if keys.get("OPENCODE_API_KEY"):
        add("opencode nemotron-super-free",
            lambda: t_openai_chat("https://opencode.ai/zen/v1/chat/completions", keys["OPENCODE_API_KEY"], "nemotron-3-super-free"))

    # ----- PAID providers -----
    if keys.get("ANTHROPIC_API_KEY_ALT"):
        add("anthropic claude-haiku-4-5",
            lambda: t_anthropic(keys["ANTHROPIC_API_KEY_ALT"]))
    if keys.get("DEEPSEEK_API_KEY"):
        add("deepseek chat",
            lambda: t_openai_chat("https://api.deepseek.com/v1/chat/completions", keys["DEEPSEEK_API_KEY"], "deepseek-chat"))
    if keys.get("MOONSHOT_API_KEY"):
        add("moonshot kimi-v1-8k",
            lambda: t_openai_chat("https://api.moonshot.ai/v1/chat/completions", keys["MOONSHOT_API_KEY"], "moonshot-v1-8k"))
    if keys.get("XAI_API_KEY"):
        add("xai grok-code-fast-1",
            lambda: t_openai_chat("https://api.x.ai/v1/chat/completions", keys["XAI_API_KEY"], "grok-code-fast-1"))
        add("xai grok-4-fast-non-reason",
            lambda: t_openai_chat("https://api.x.ai/v1/chat/completions", keys["XAI_API_KEY"], "grok-4-fast-non-reasoning"))
        add("xai grok-3-mini",
            lambda: t_openai_chat("https://api.x.ai/v1/chat/completions", keys["XAI_API_KEY"], "grok-3-mini"))
    if keys.get("AIMLAPI_PAID_KEY"):
        add("aimlapi-paid gpt-4o-mini",
            lambda: t_openai_chat("https://api.aimlapi.com/v1/chat/completions", keys["AIMLAPI_PAID_KEY"], "gpt-4o-mini"))
    # Bluesmind premium models (credit-backed paid)
    if keys.get("BLUESMIND_API_KEY"):
        add("bluesmind gpt-5-chat",
            lambda: t_openai_chat("https://api.bluesminds.com/v1/chat/completions", keys["BLUESMIND_API_KEY"], "gpt-5-chat"))
        add("bluesmind moonshotai/kimi-k2.6",
            lambda: t_openai_chat("https://api.bluesminds.com/v1/chat/completions", keys["BLUESMIND_API_KEY"], "moonshotai/kimi-k2.6"))
        add("bluesmind grok-4.20-fast",
            lambda: t_openai_chat("https://api.bluesminds.com/v1/chat/completions", keys["BLUESMIND_API_KEY"], "grok-4.20-fast"))
    return tests


def run_one(name, fn):
    t0 = time.time()
    s, b = fn()
    elapsed = time.time() - t0
    if s != 200:
        return name, "ERR", s, 0, elapsed, 0.0, ""
    ct, sample = _extract_tokens(b)
    tps = ct / elapsed if elapsed > 0 else 0
    return name, "OK", s, ct, elapsed, tps, sample


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=1, help="number of trials per provider (averaged)")
    args = ap.parse_args()

    keys = load_keys()
    tests = build_tests(keys)
    print(f"Benchmarking {len(tests)} providers — {args.rounds} round(s) each")
    print(f"Prompt: '{PROMPT[:60]}...'  max_tokens={MAX_TOKENS}\n")

    # Per-provider aggregated results across rounds
    agg: dict[str, list] = {}
    for r in range(args.rounds):
        if args.rounds > 1:
            print(f"--- round {r+1}/{args.rounds} ---")
        with cf.ThreadPoolExecutor(max_workers=10) as ex:
            futs = {ex.submit(run_one, n, fn): n for n, fn in tests}
            for fut in cf.as_completed(futs):
                name, status, code, ct, el, tps, sample = fut.result()
                agg.setdefault(name, []).append((status, code, ct, el, tps, sample))

    # Average and sort
    rows = []
    for name, runs in agg.items():
        ok_runs = [r for r in runs if r[0] == "OK"]
        if not ok_runs:
            last = runs[-1]
            rows.append((name, "FAIL", 0, 0.0, 0.0, str(last[1])[:40]))
            continue
        avg_tps = statistics.mean(r[4] for r in ok_runs)
        avg_el = statistics.mean(r[3] for r in ok_runs)
        avg_ct = statistics.mean(r[2] for r in ok_runs)
        sample = ok_runs[-1][5]
        rows.append((name, "OK", avg_ct, avg_el, avg_tps, sample))

    # Sort: OK first by TPS descending, then FAIL
    rows.sort(key=lambda r: (r[1] != "OK", -r[4]))
    print()
    print(f"{'PROVIDER':<35} {'STATUS':<8} {'TOKENS':>7} {'SEC':>7} {'TPS':>7}  SAMPLE")
    print("-" * 110)
    for name, status, ct, el, tps, sample in rows:
        sample_disp = sample.replace("\n", " ")[:30]
        if status == "OK":
            print(f"{name:<35} {'OK':<8} {ct:>7.0f} {el:>7.2f} {tps:>7.1f}  {sample_disp}")
        else:
            print(f"{name:<35} {'FAIL':<8} {'':>7} {'':>7} {'':>7}  {sample[:40]}")

    ok = [r for r in rows if r[1] == "OK"]
    if ok:
        print()
        print(f"FASTEST: {ok[0][0]} @ {ok[0][4]:.1f} tok/s")
        print(f"SLOWEST: {ok[-1][0]} @ {ok[-1][4]:.1f} tok/s")
        print(f"MEDIAN:  {statistics.median(r[4] for r in ok):.1f} tok/s across {len(ok)} working providers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
