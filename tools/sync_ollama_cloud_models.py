#!/usr/bin/env python3
"""Sync Ollama *cloud* models into the LiteLLM proxy as ULTRA_PAID_OLLAMA_* aliases.

Why: the agy CLI / Antigravity IDE+App all talk to one endpoint (`http://localhost:4000/v1`),
so anything registered on that proxy is immediately usable there — Ollama cloud models included.

What it does (all steps idempotent):
  1. discovery  — GET $OLLAMA_BASE/api/tags and keep cloud entries
                  (name ends in `-cloud`/`:cloud`, or the entry is a stub: size < 100 MB)
  2. persistence — rewrite the auto-generated block in the LiteLLM config, so the aliases
                  survive a proxy restart (default target: litellm_config.runtime.yaml,
                  falling back to litellm_config.yaml)
  3. live add    — POST $LITELLM_BASE/model/new for aliases the running proxy does not
                  serve yet. NOTE: this never restarts the proxy; port 4000 stays up.
  4. agy env     — extend AGY_LLM_GATEWAY_MODELS in ~/.config/agy-litellm/env so the CLI,
                  IDE extension and App picker list the new aliases too.

Usage:
  .venv/bin/python tools/sync_ollama_cloud_models.py            # apply
  .venv/bin/python tools/sync_ollama_cloud_models.py --dry-run  # show the block only
  .venv/bin/python tools/sync_ollama_cloud_models.py --no-live --no-agy-env
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BEGIN = "# BEGIN ollama-cloud-autosync (managed by tools/sync_ollama_cloud_models.py)"
END = "# END ollama-cloud-autosync"
CLOUD_STUB_BYTES = 100 * 1024 * 1024  # cloud entries are a few hundred bytes, not GBs
ALIAS_PREFIX = "ULTRA_PAID_OLLAMA_"


def env(name: str, default: str) -> str:
    return os.environ.get(name, default).rstrip("/")


OLLAMA_BASE = env("OLLAMA_BASE", "http://localhost:11434")
LITELLM_BASE = env("LITELLM_BASE", "http://localhost:4000")
LITELLM_KEY = os.environ.get("LITELLM_KEY", "sk-1234")
AGY_ENV = os.path.expanduser("~/.config/agy-litellm/env")


def http_json(url: str, payload: dict | None = None, key: str | None = None, timeout: int = 20):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    if data:
        req.add_header("Content-Type", "application/json")
    if key:
        req.add_header("Authorization", f"Bearer {key}")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read().decode("utf-8", "replace")
    return json.loads(body) if body.strip().startswith(("{", "[")) else {}


def cloud_models() -> list[str]:
    try:
        tags = http_json(f"{OLLAMA_BASE}/api/tags")
    except Exception as exc:  # Ollama down on boot is normal — nothing to do
        print(f"  ollama unreachable ({exc}); nothing to sync")
        return []
    out = []
    for m in tags.get("models", []):
        name = (m.get("name") or "").strip()
        if not name:
            continue
        size = m.get("size") or 0
        if name.endswith("-cloud") or name.endswith(":cloud") or size < CLOUD_STUB_BYTES:
            out.append(name)
    return sorted(set(out))


def alias_for(model: str) -> str:
    base, _, tag = model.partition(":")
    base = base.split("/")[-1]  # drop namespace (e.g. artiku348/…)
    raw = f"{base}_{tag}" if tag and tag != "latest" else base
    return ALIAS_PREFIX + re.sub(r"[^A-Z0-9]+", "_", raw.upper()).strip("_")


def params_for(model: str) -> dict:
    return {"model": f"ollama_chat/{model}", "api_base": OLLAMA_BASE, "api_key": "ollama"}


def render_block(models: list[str]) -> str:
    lines = [BEGIN, "# auto-generated — do not edit by hand; re-run the sync script instead"]
    for m in models:
        lines.append(
            "  - {model_name: %s, litellm_params: {model: '%s', api_base: %s, api_key: ollama}}"
            % (alias_for(m), f"ollama_chat/{m}", OLLAMA_BASE)
        )
    lines.append(END)
    return "\n".join(lines) + "\n"


def config_path() -> str:
    runtime = os.path.join(REPO, "litellm_config.runtime.yaml")
    return runtime if os.path.exists(runtime) else os.path.join(REPO, "litellm_config.yaml")


def update_config(path: str, block: str) -> bool:
    text = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
    if BEGIN in text and END in text:
        new = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", block, text, flags=re.S)
    else:
        if not text:
            new = "model_list:\n" + block
        else:
            sep = "" if text.endswith("\n") else "\n"
            new = text + sep + "\n" + block
    if new == text:
        return False
    tmp = path + ".tmp"
    open(tmp, "w", encoding="utf-8").write(new)
    os.replace(tmp, path)
    return True


def served() -> set[str]:
    try:
        data = http_json(f"{LITELLM_BASE}/v1/models", key=LITELLM_KEY)
        return {m.get("id") for m in data.get("data", []) if m.get("id")}
    except Exception as exc:
        print(f"  proxy unreachable ({exc}); skipping live add")
        return set()


def add_live(models: list[str], have: set[str]) -> list[str]:
    added = []
    for m in models:
        a = alias_for(m)
        if a in have:
            continue
        try:
            http_json(
                f"{LITELLM_BASE}/model/new",
                {"model_name": a, "litellm_params": params_for(m), "model_info": {"id": a}},
                key=LITELLM_KEY,
            )
            added.append(a)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:160]
            print(f"  ! {a}: HTTP {exc.code} {detail}")
        except Exception as exc:
            print(f"  ! {a}: {exc}")
    return added


def update_agy_env(models: list[str]) -> list[str]:
    if not os.path.exists(AGY_ENV):
        return []
    lines = open(AGY_ENV, encoding="utf-8").read().splitlines()
    aliases = [alias_for(m) for m in models]
    for i, line in enumerate(lines):
        if line.startswith("AGY_LLM_GATEWAY_MODELS="):
            cur = [x.strip() for x in line.split("=", 1)[1].split(",") if x.strip()]
            merged = cur + [a for a in aliases if a not in cur]
            if merged == cur:
                return []
            lines[i] = "AGY_LLM_GATEWAY_MODELS=" + ",".join(merged)
            open(AGY_ENV, "w", encoding="utf-8").write("\n".join(lines) + "\n")
            return [a for a in aliases if a not in cur]
    return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-live", action="store_true", help="skip POST /model/new")
    ap.add_argument("--no-agy-env", action="store_true", help="do not touch ~/.config/agy-litellm/env")
    args = ap.parse_args()

    models = cloud_models()
    print(f"ollama cloud models found: {len(models)}")
    for m in models:
        print(f"  {m}  ->  {alias_for(m)}")
    if not models:
        return 0

    block = render_block(models)
    if args.dry_run:
        print("\n" + block)
        return 0

    path = config_path()
    changed = update_config(path, block)
    print(f"config {path}: {'updated' if changed else 'already current'}")

    if not args.no_live:
        added = add_live(models, served())
        print(f"live-add via /model/new: {len(added)} new alias(es)" + (f" -> {added}" if added else ""))

    if not args.no_agy_env:
        grew = update_agy_env(models)
        print(f"agy env: {len(grew)} alias(es) appended" + (f" -> {grew}" if grew else " (already present)"))

    return 0


if __name__ == "__main__":
    sys.exit(main())
