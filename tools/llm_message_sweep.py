"""
llm_message_sweep.py — trace a test marker across ALL local LLM surfaces.

Answers: "I sent a message containing <marker> — which provider/model served it?"

Surfaces covered
----------------
  1. litellm   /tmp/litellm_messages.jsonl                 (tools/litellm_message_log.py)
  2. opencode  ~/.local/share/opencode/opencode.db         (part.data -> message -> model)
  3. openwebui open-webui container webui.db               (chat.chat JSON)
  4. vllm      /tmp/vllm_serve.log
  5. ollama    journalctl -u ollama                        (request level only, no content)

Usage
-----
  python3 tools/llm_message_sweep.py --marker xyzdragon
  python3 tools/llm_message_sweep.py -m zzmarker999 --json

Exit code 0 if the marker was found on at least one surface, 1 otherwise.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

LITELLM_LOG = Path(os.environ.get("LITELLM_MESSAGE_LOG", "/tmp/litellm_messages.jsonl"))
OPENCODE_DB = Path.home() / ".local/share/opencode/opencode.db"
VLLM_LOG = Path(os.environ.get("VLLM_LOG", "/tmp/vllm_serve.log"))
WEBUI_CONTAINER = os.environ.get("OPENWEBUI_CONTAINER", "open-webui")


def _utc(ms: float) -> str:
    return _dt.datetime.fromtimestamp(ms / 1000, _dt.timezone.utc).strftime("%H:%M:%S.%f")[:-3]


# --------------------------------------------------------------------------
# 1. LiteLLM proxy
# --------------------------------------------------------------------------
def sweep_litellm(marker: str) -> list[dict]:
    hits: list[dict] = []
    if not LITELLM_LOG.exists():
        return hits
    with LITELLM_LOG.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            hay = " ".join(
                str(rec.get(k) or "") for k in ("prompt", "last_user", "response", "error")
            ).lower()
            if marker.lower() in hay:
                hits.append({
                    "surface": "litellm",
                    "time": (rec.get("ts") or "")[11:23],
                    "group": rec.get("requested_group"),
                    "real_model": rec.get("real_model"),
                    "api_base": rec.get("api_base"),
                    "status": rec.get("status"),
                    "call_id": rec.get("call_id"),
                })
    return hits


# --------------------------------------------------------------------------
# 2. opencode session DB
# --------------------------------------------------------------------------
def sweep_opencode(marker: str) -> list[dict]:
    hits: list[dict] = []
    if not OPENCODE_DB.exists():
        return hits
    try:
        con = sqlite3.connect(f"file:{OPENCODE_DB}?mode=ro", uri=True)
        rows = con.execute(
            "select id, message_id, session_id, time_created, data "
            "from part where data like ? limit 25", (f"%{marker}%",)
        ).fetchall()
    except Exception:
        return hits

    for pid, mid, sid, tc, data in rows:
        role = kind = model = None
        try:
            d = json.loads(data)
            kind = d.get("type")
            role = d.get("role")
        except Exception:
            pass
        # resolve the owning message (role + model live there)
        try:
            m = con.execute("select data from message where id=?", (mid,)).fetchone()
            if m:
                md = json.loads(m[0])
                role = md.get("role") or role
                model = md.get("modelID")
        except Exception:
            pass
        hits.append({
            "surface": "opencode",
            "time": _utc(tc),
            "part_type": kind,
            "role": role,
            "model": model,
            "session": sid,
        })
    return hits


# --------------------------------------------------------------------------
# 3. Open WebUI (copy DB out of the container, then query)
# --------------------------------------------------------------------------
def sweep_openwebui(marker: str) -> list[dict]:
    hits: list[dict] = []
    if not shutil.which("docker"):
        return hits
    tmp = Path(tempfile.mkdtemp(prefix="webui_sweep_"))
    try:
        cp = subprocess.run(
            ["docker", "cp", f"{WEBUI_CONTAINER}:/app/backend/data/.", str(tmp)],
            capture_output=True, text=True, timeout=60,
        )
        db = tmp / "webui.db"
        if cp.returncode != 0 or not db.exists():
            return hits
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        for cid, title, updated, chat in con.execute(
            "select id, title, updated_at, chat from chat "
            "where chat like ? limit 25", (f"%{marker}%",)
        ):
            models: list[str] = []
            try:
                d = json.loads(chat)
                models = d.get("models") or []
            except Exception:
                pass
            hits.append({
                "surface": "openwebui",
                "time": _utc(updated * 1000),
                "title": title,
                "models": models,
                "chat_id": cid,
            })
    except Exception:
        pass
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return hits


# --------------------------------------------------------------------------
# 4. vLLM server log
# --------------------------------------------------------------------------
def sweep_vllm(marker: str) -> list[dict]:
    hits: list[dict] = []
    if not VLLM_LOG.exists():
        return hits
    try:
        text = VLLM_LOG.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return hits
    for m in re.finditer(re.escape(marker.lower()), text.lower()):
        line = text[:m.start()].splitlines()[-1] if m.start() else ""
        hits.append({"surface": "vllm", "time": "", "context": line[:160]})
    return hits[:10]


# --------------------------------------------------------------------------
# 5. Ollama journal (request level only — Ollama does not log prompt text)
# --------------------------------------------------------------------------
def sweep_ollama(marker: str) -> list[dict]:
    """Ollama never logs prompt content, so this only reports chat requests
    that happened — useful for time-correlation, never for a text match."""
    if not shutil.which("journalctl"):
        return []
    try:
        out = subprocess.run(
            ["journalctl", "-u", "ollama", "--since", "3 hours ago", "--no-pager"],
            capture_output=True, text=True, timeout=30,
        ).stdout
    except Exception:
        return []
    reqs = [l for l in out.splitlines() if "/api/chat" in l or "/api/generate" in l]
    hits = []
    for l in reqs[-5:]:
        tm = re.search(r"(\d{2}:\d{2}:\d{2})", l)
        hits.append({
            "surface": "ollama",
            "time": tm.group(1) if tm else "",
            "context": "chat request seen (Ollama does not log prompt text)",
        })
    return hits


# --------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Trace a test marker across all local LLM surfaces.")
    ap.add_argument("--marker", "-m", required=True, help="unique string to search for")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    args = ap.parse_args(argv)

    mark = args.marker
    results = {
        "litellm": sweep_litellm(mark),
        "opencode": sweep_opencode(mark),
        "openwebui": sweep_openwebui(mark),
        "vllm": sweep_vllm(mark),
        "ollama": sweep_ollama(mark),
    }
    # Ollama cannot match message text, so it is advisory only.
    MATCHING = ("litellm", "opencode", "openwebui", "vllm")
    matched = [s for s in MATCHING if results.get(s)]

    if args.json:
        print(json.dumps({"marker": mark, "matched_on": matched, "results": results}, indent=2, default=str))
        return 0 if matched else 1

    print(f"marker: {mark!r}\n")
    print(f"{'SURFACE':10} {'MATCH':7} DETAIL")
    print("-" * 100)
    for surface in MATCHING:
        hits = results.get(surface) or []
        if not hits:
            print(f"{surface:10} {'no':7} -")
            continue
        for i, h in enumerate(hits):
            label = surface if i == 0 else ""
            detail = " | ".join(
                f"{k}={v}" for k, v in h.items() if k != "surface" and v not in (None, "", [])
            )
            print(f"{label:10} {'YES':7} {detail}")

    if results.get("ollama"):
        print("\nADVISORY (cannot match text - use for time-correlation only):")
        for h in results["ollama"]:
            print(f"  ollama chat request at {h['time']}")

    print()
    if matched:
        print(f"=> marker found on: {', '.join(matched)}")
    else:
        print("=> marker NOT found on any local surface "
              "(message may have gone to a remote/cloud endpoint)")
    return 0 if matched else 1


if __name__ == "__main__":
    raise SystemExit(main())
