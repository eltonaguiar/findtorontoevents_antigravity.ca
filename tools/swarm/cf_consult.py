"""
Cloudflare Workers AI consult CLI — single-model run + multi-model fan-out.

Usage:
  # Single model, non-streaming
  echo "your prompt" | python3 tools/swarm/cf_consult.py \\
      --model '@cf/openai/gpt-oss-120b'

  # Single model, streaming
  echo "your prompt" | python3 tools/swarm/cf_consult.py \\
      --model '@cf/qwen/qwen3-30b-a3b-fp8' --stream

  # Fan out to default panel (6 diverse models)
  echo "your prompt" | python3 tools/swarm/cf_consult.py --fanout

  # Fan out to a custom panel
  echo "your prompt" | python3 tools/swarm/cf_consult.py \\
      --fanout --models '@cf/meta/llama-3.3-70b-instruct-fp8-fast,@cf/openai/gpt-oss-120b'

  # List models matching a pattern
  python3 tools/swarm/cf_consult.py --list
  python3 tools/swarm/cf_consult.py --list --search llama

Env:
  CF_API_TOKEN     — Cloudflare API token with Workers AI scope (cfut_...)
  CF_ACCOUNT_ID    — 32-char hex account id
"""
import argparse, json, os, sys, time
import requests

DEFAULT_FANOUT = [
    "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
    "@cf/meta/llama-4-scout-17b-16e-instruct",
    "@cf/nvidia/nemotron-3-120b-a12b",
    "@cf/openai/gpt-oss-120b",
    "@cf/qwen/qwen3-30b-a3b-fp8",
    "@cf/zai-org/glm-4.7-flash",
    "@cf/mistralai/mistral-small-3.1-24b-instruct",
]


def _env():
    tok = os.environ.get("CF_API_TOKEN")
    acct = os.environ.get("CF_ACCOUNT_ID")
    if not tok or not acct:
        print("ERROR: set CF_API_TOKEN + CF_ACCOUNT_ID env vars", file=sys.stderr)
        sys.exit(2)
    return tok, acct


def list_models(search=None):
    tok, acct = _env()
    url = f"https://api.cloudflare.com/client/v4/accounts/{acct}/ai/models/search?per_page=200"
    if search:
        url += f"&search={search}"
    r = requests.get(url, headers={"Authorization": f"Bearer {tok}"}, timeout=30)
    data = r.json()
    if not data.get("success"):
        print(f"FAIL: {data.get('errors')}", file=sys.stderr); sys.exit(1)
    rows = [m for m in data["result"] if (m.get("task") or {}).get("name") == "Text Generation"]
    for m in sorted(rows, key=lambda x: x["name"]):
        desc = (m.get("description") or "")[:80]
        print(f"{m['name']:60s}  {desc}")
    print(f"\n[{len(rows)} text-generation models]", file=sys.stderr)


def run_one(model, prompt, stream=False, max_tokens=4096, temperature=0.4):
    tok, acct = _env()
    url = f"https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/{model}"
    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": stream,
    }
    headers = {"Authorization": f"Bearer {tok}"}
    if stream:
        chunks = []
        r = requests.post(url, headers=headers, json=payload, stream=True, timeout=240)
        for line in r.iter_lines():
            if not line:
                continue
            ln = line.decode("utf-8")
            if not ln.startswith("data: "):
                continue
            data = ln[6:].strip()
            if data == "[DONE]":
                break
            try:
                obj = json.loads(data)
            except Exception:
                continue
            piece = obj.get("response", "")
            if piece:
                chunks.append(piece)
                print(piece, end="", flush=True)
        print()
        return "".join(chunks)
    else:
        r = requests.post(url, headers=headers, json=payload, timeout=240)
        data = r.json()
        if not data.get("success"):
            return f"[ERROR {data.get('errors')}]"
        out = data["result"].get("response", "")
        print(out)
        return out


def fanout(prompt, models, max_tokens=4096):
    results = []
    for m in models:
        t0 = time.time()
        try:
            out = run_one(m, prompt, stream=False, max_tokens=max_tokens)
        except Exception as e:
            out = f"[ERROR {type(e).__name__}: {e}]"
        elapsed = time.time() - t0
        print(f"\n=== {m} ({elapsed:.1f}s · {len(out)} chars) ===\n{out}\n", file=sys.stderr)
        results.append((m, elapsed, out))
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", help="single model slug (e.g. @cf/openai/gpt-oss-120b)")
    ap.add_argument("--stream", action="store_true", help="SSE stream (single-model only)")
    ap.add_argument("--fanout", action="store_true", help="run across panel of models")
    ap.add_argument("--models", help="comma-separated slugs for --fanout (default 7-model panel)")
    ap.add_argument("--list", action="store_true", help="list available text-gen models")
    ap.add_argument("--search", help="filter --list by substring (e.g. llama, 120b, qwen)")
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--temperature", type=float, default=0.4)
    args = ap.parse_args()

    if args.list:
        list_models(args.search)
        return

    prompt = sys.stdin.read().strip()
    if not prompt:
        print("ERROR: pipe a prompt on stdin (e.g. `echo 'q' | python3 ...`)", file=sys.stderr)
        sys.exit(2)

    if args.fanout:
        panel = args.models.split(",") if args.models else DEFAULT_FANOUT
        fanout(prompt, panel, max_tokens=args.max_tokens)
    elif args.model:
        run_one(args.model, prompt, stream=args.stream,
                max_tokens=args.max_tokens, temperature=args.temperature)
    else:
        print("ERROR: pick one of --model, --fanout, or --list", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
