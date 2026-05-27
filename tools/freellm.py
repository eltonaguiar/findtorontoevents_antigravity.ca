#!/usr/bin/env python3
"""
freellm.py — Universal FreeLLM CLI  (Windows + Linux)
======================================================

Entry-points (all identical behaviour):
  python freellm.py [command] [options]
  FreeLLM [command] [options]          # after alias/shim install

COMMANDS
--------
  -H  / help           Show this help
  -STA / start         Start the LiteLLM proxy server
  -STO / stop          Stop the LiteLLM proxy server
    -W  / wizard         Interactive wizard (menu-driven, auto-starts server)
    ui                   Alias for wizard mode (cross-platform text UI)

  CombineTeam          Ask N AIs simultaneously, collect all answers
  DebateTeam           Multi-round structured AI debate, output .MD files
  FileTeam             Divide a list of files across multiple AIs in parallel
    SpendReport          Show local spend totals from proxy response metadata

GLOBAL OPTIONS
--------------
  --base-url URL       LiteLLM proxy base URL  [default: http://localhost:4000/v1]
  --api-key KEY        Proxy bearer key        [default: anything]
  --results DIR        Output directory        [default: tools/FREELLM/RESULTS]
  --no-color           Disable rich colour output

COMBINETEAM OPTIONS
  -q / --query TEXT    Question to ask all AIs
  -n INT               Number of distinct AI replies  [default: 5]
  --aliases CSV        Override alias list
    --reply-mode MODE    Where replies go: chat|files  [default: files]

DEBATETEAM OPTIONS
------------------
  -q / --query TEXT    Topic or question to debate
  --rounds INT         Number of debate rounds  [default: 3]
  -n INT               Number of debaters       [default: 4]

FILETEAM OPTIONS
----------------
  --files FILE [...]   .md (or any text) files to process
  --prompt TEXT        Instruction applied to each file
  --chunk INT          Files handled concurrently  [default: 3]
  --model free|paid|large  Model tier override     [default: auto]
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime
import json
import os
import re
import sqlite3
import socket
import subprocess
import sys
import textwrap
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

# ── optional rich / prompt_toolkit (graceful fallback to plain text) ──────────
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich import box
    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False

try:
    from prompt_toolkit import prompt as pt_prompt
    from prompt_toolkit.completion import WordCompleter
    _HAS_PT = True
except ImportError:
    _HAS_PT = False

# ── constants ─────────────────────────────────────────────────────────────────
DEFAULT_BASE_URL = "http://localhost:4000/v1"
DEFAULT_RESULTS  = Path(__file__).parent.parent / "tools" / "FREELLM" / "RESULTS"
DEFAULT_SPEND_DB = Path(__file__).parent.parent / ".local" / "spend" / "spend.db"

DEFAULT_ALIASES = [
    "free-mode-fast",
    "free-mode",
    "free-mode-large",
    "paid-mode",
    "paid-mode-large",
    "nvidia-deepseek-v4-pro",
    "openrouter-ring-1t",
    "claude-haiku-direct",
    "deepseek-chat-direct",
]

# Cache: litellm model-info id -> upstream model name (e.g. hash -> groq/llama-3.1-8b-instant)
_MODEL_ID_MAP_CACHE: dict[str, str] = {}
_MODEL_ID_MAP_CACHE_TS: float = 0.0
_MODEL_ID_MAP_TTL_SEC = 60.0
_SPEND_LOCK = threading.Lock()
_SPEND_SCHEMA_READY = False

# ── console singleton ─────────────────────────────────────────────────────────
_console: "Console | None" = None

def con() -> "Console":
    global _console
    if _console is None:
        if _HAS_RICH:
            _console = Console()
        else:
            class _FallbackConsole:
                def print(self, *args, **kw): print(*args)
                def rule(self, t=""): print(f"\n{'─'*60} {t} {'─'*60}\n")
            _console = _FallbackConsole()  # type: ignore
    return _console  # type: ignore


def cprint(msg: str, style: str = "") -> None:
    if _HAS_RICH:
        con().print(msg, style=style)  # type: ignore
    else:
        print(msg)


def _spend_db_path() -> Path:
    raw = os.environ.get("FREELLM_SPEND_DB", "").strip()
    return Path(raw) if raw else DEFAULT_SPEND_DB


def _provider_from_model(upstream_model: str, model_api_base: str) -> str:
    if upstream_model and "/" in upstream_model:
        return upstream_model.split("/", 1)[0]
    if model_api_base:
        parsed = urlparse(model_api_base)
        host = (parsed.hostname or "").lower()
        if host:
            return host
    return "unknown"


def _as_int(v: object) -> int:
    try:
        return int(v) if v is not None else 0
    except Exception:
        return 0


def _as_float(v: object) -> float:
    try:
        return float(v) if v is not None else 0.0
    except Exception:
        return 0.0


def _ensure_spend_schema(db_path: Path) -> None:
    global _SPEND_SCHEMA_READY
    with _SPEND_LOCK:
        if _SPEND_SCHEMA_READY:
            return
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS spend_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_utc TEXT NOT NULL,
                    alias TEXT,
                    upstream_model TEXT,
                    provider TEXT,
                    status INTEGER,
                    prompt_tokens INTEGER,
                    completion_tokens INTEGER,
                    total_tokens INTEGER,
                    response_cost_usd REAL,
                    model_api_base TEXT,
                    model_group TEXT,
                    call_id TEXT,
                    error TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_spend_events_ts ON spend_events(ts_utc)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_spend_events_provider ON spend_events(provider)")
            conn.commit()
        finally:
            conn.close()
        _SPEND_SCHEMA_READY = True


def _record_spend_event(
    *,
    alias: str,
    upstream_model: str,
    status: int,
    hdrs: dict[str, str],
    data: dict,
    error: Optional[str],
) -> None:
    try:
        db_path = _spend_db_path()
        _ensure_spend_schema(db_path)

        usage = data.get("usage") if isinstance(data, dict) else {}
        usage = usage if isinstance(usage, dict) else {}

        prompt_tokens = _as_int(usage.get("prompt_tokens"))
        completion_tokens = _as_int(usage.get("completion_tokens"))
        total_tokens = _as_int(usage.get("total_tokens"))
        response_cost = _as_float(hdrs.get("x-litellm-response-cost"))
        model_api_base = str(hdrs.get("x-litellm-model-api-base") or "")
        model_group = str(hdrs.get("x-litellm-model-group") or "")
        call_id = str(hdrs.get("x-litellm-call-id") or "")
        provider = _provider_from_model(upstream_model, model_api_base)

        with _SPEND_LOCK:
            conn = sqlite3.connect(db_path)
            try:
                conn.execute(
                    """
                    INSERT INTO spend_events (
                        ts_utc, alias, upstream_model, provider, status,
                        prompt_tokens, completion_tokens, total_tokens,
                        response_cost_usd, model_api_base, model_group, call_id, error
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        alias,
                        upstream_model,
                        provider,
                        status,
                        prompt_tokens,
                        completion_tokens,
                        total_tokens,
                        response_cost,
                        model_api_base,
                        model_group,
                        call_id,
                        error or "",
                    ),
                )
                conn.commit()
            finally:
                conn.close()
    except Exception:
        # Spend tracking must never break core request flow.
        pass

# ── timestamp helpers ─────────────────────────────────────────────────────────
def ts() -> str:
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def results_dir(sub: str, base: Path) -> Path:
    d = base / sub
    d.mkdir(parents=True, exist_ok=True)
    return d


def _proxy_root(base_url: str) -> str:
    """Normalize to proxy root URL (strip trailing /v1 when present)."""
    u = base_url.rstrip("/")
    return u[:-3] if u.endswith("/v1") else u


def _looks_like_hash(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F]{32,128}", value or ""))


def _load_model_id_map(base_url: str, api_key: str) -> dict[str, str]:
    """Fetch LiteLLM /model/info and map model_info.id -> litellm_params.model."""
    global _MODEL_ID_MAP_CACHE, _MODEL_ID_MAP_CACHE_TS
    now = time.time()
    if _MODEL_ID_MAP_CACHE and (now - _MODEL_ID_MAP_CACHE_TS) < _MODEL_ID_MAP_TTL_SEC:
        return _MODEL_ID_MAP_CACHE

    url = _proxy_root(base_url) + "/model/info"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            raw = r.read().decode("utf-8", errors="replace")
        data = json.loads(raw)
        rows = data.get("data") or []
        mapped: dict[str, str] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            model_id = ((row.get("model_info") or {}).get("id") or "").strip()
            upstream = ((row.get("litellm_params") or {}).get("model") or "").strip()
            if model_id and upstream:
                mapped[model_id] = upstream
        if mapped:
            _MODEL_ID_MAP_CACHE = mapped
            _MODEL_ID_MAP_CACHE_TS = now
    except Exception:
        # Non-fatal: if this lookup fails we still return best-effort labels.
        pass

    return _MODEL_ID_MAP_CACHE


def _extract_upstream_model(base_url: str, api_key: str, alias: str, hdrs: dict[str, str], data: dict) -> Optional[str]:
    # 1) Direct human-readable header when available.
    header_model = (hdrs.get("x-litellm-model") or "").strip()
    if header_model and not _looks_like_hash(header_model):
        return header_model

    # 2) Response model if it is not just the alias.
    resp_model = str(data.get("model") or "").strip()
    if resp_model and resp_model != alias and not _looks_like_hash(resp_model):
        return resp_model

    # 3) Provider-specific served-model header (Azure/GitHub Models style).
    served_model = (hdrs.get("llm_provider-x-ms-served-model") or "").strip()
    if served_model:
        return served_model

    # 4) Resolve opaque model-id hash through /model/info mapping.
    model_id = (hdrs.get("x-litellm-model-id") or "").strip()
    if model_id:
        mapped = _load_model_id_map(base_url, api_key).get(model_id)
        if mapped:
            return mapped

    # 5) Last-resort parse from model-api-base for Gemini-style URLs.
    api_base = (hdrs.get("x-litellm-model-api-base") or "").strip()
    m = re.search(r"/models/([^/:?]+)", api_base)
    if m:
        return m.group(1)

    return None

# ── HTTP helper (reused from triple_ask_free logic) ───────────────────────────
@dataclass
class AskResult:
    alias: str
    status: int
    reply: str
    upstream_model: Optional[str] = None
    upstream_provider: Optional[str] = None
    error: Optional[str] = None


def _post_chat(
    base_url: str,
    api_key: str,
    alias: str,
    messages: list[dict],
    timeout: int = 90,
    max_tokens: int = 1500,
) -> AskResult:
    url = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": alias,
        "messages": messages,
        "temperature": 0.4,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", errors="replace")
            hdrs = {k.lower(): v for k, v in r.headers.items()}
            status = r.getcode()
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        hdrs = {}
        status = e.code
    except Exception as e:
        return AskResult(alias=alias, status=0, reply="", error=str(e))

    try:
        data = json.loads(raw)
        choice = ((data.get("choices") or [{}])[0])
        reply = (choice.get("message") or {}).get("content") or ""
    except Exception:
        reply = raw[:500]
        data = {}

    upstream_model = _extract_upstream_model(base_url, api_key, alias, hdrs, data)

    error = None
    if status != 200:
        error = str((data.get("error") or {}) or f"HTTP {status}")

    _record_spend_event(
        alias=alias,
        upstream_model=upstream_model or "",
        status=status,
        hdrs=hdrs,
        data=data,
        error=error,
    )

    return AskResult(alias=alias, status=status, reply=reply,
                     upstream_model=upstream_model, error=error)


def _ask_one(base_url: str, api_key: str, alias: str, messages: list[dict],
             timeout: int = 90, max_tokens: int = 1500) -> AskResult:
    return _post_chat(base_url, api_key, alias, messages, timeout, max_tokens)

# ── server management ─────────────────────────────────────────────────────────
def _find_proxy_script() -> Optional[Path]:
    candidates = [
        Path(__file__).parent / "start_litellm_proxy.sh",
        Path.home() / "FREELLM" / "tools" / "start_litellm_proxy.sh",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def cmd_start(args: argparse.Namespace) -> int:
    if _proxy_alive(args.base_url):
        cprint("[green]✓ Proxy already running.[/green]")
        return 0

    if _litellm_process_running():
        cprint("[green]✓ LiteLLM process already running.[/green]")
        return 0

    script = _find_proxy_script()
    if script is None:
        cprint("[red]✗ Cannot find start_litellm_proxy.sh[/red]")
        return 1
    cprint(f"[cyan]▶ Starting LiteLLM proxy via {script}…[/cyan]")
    if sys.platform == "win32":
        subprocess.Popen(["bash", str(script), "--background"], creationflags=subprocess.CREATE_NEW_CONSOLE)
    else:
        subprocess.Popen(["bash", str(script), "--background"])

    # Poll health for a few seconds to avoid false offline detections.
    for _ in range(20):
        if _proxy_alive(args.base_url):
            cprint("[green]✓ Proxy is up.[/green]")
            return 0
        time.sleep(0.5)

    cprint("[yellow]⚠ Proxy may still be starting — try again in a few seconds.[/yellow]")
    return 0


def cmd_stop(args: argparse.Namespace) -> int:
    cprint("[cyan]■ Stopping LiteLLM proxy…[/cyan]")
    if sys.platform == "win32":
        os.system("taskkill /F /IM litellm.exe 2>nul & taskkill /F /IM python.exe /FI \"WINDOWTITLE eq litellm*\" 2>nul")
    else:
        os.system("pkill -f 'litellm' 2>/dev/null || true")
        os.system("pkill -f 'start_litellm_proxy' 2>/dev/null || true")
    cprint("[green]✓ Stop signal sent.[/green]")
    return 0


def _proxy_alive(base_url: str) -> bool:
    if _proxy_port_open(base_url):
        return True

    health_urls = [
        base_url.replace("/v1", "/health"),
        base_url.replace("localhost", "127.0.0.1").replace("/v1", "/health"),
    ]
    for url in health_urls:
        try:
            with urllib.request.urlopen(url, timeout=8) as resp:
                if resp.getcode() == 200:
                    return True
        except Exception:
            continue
    return False


def _proxy_port_open(base_url: str) -> bool:
    parsed = urlparse(base_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except Exception:
        return False


def _litellm_process_running() -> bool:
    if sys.platform == "win32":
        return False
    try:
        cp = subprocess.run(
            ["pgrep", "-f", "litellm --config"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return cp.returncode == 0
    except Exception:
        return False

# ── HELP ──────────────────────────────────────────────────────────────────────
def cmd_help(_args: argparse.Namespace) -> int:
    if _HAS_RICH:
        con().print(Panel.fit(__doc__ or "", title="[bold cyan]FreeLLM Help[/bold cyan]", border_style="cyan"))  # type: ignore
    else:
        print(__doc__)
    return 0

# ── WIZARD ────────────────────────────────────────────────────────────────────
_WIZARD_MENU = [
    ("1", "CombineTeam  — Ask N AIs the same question"),
    ("2", "DebateTeam   — Multi-round AI structured debate"),
    ("3", "FileTeam     — Divide files across multiple AIs"),
    ("4", "Start server"),
    ("5", "Stop server"),
    ("6", "Verify all keys"),
    ("7", "Toggle source labels ON/OFF"),
    ("8", "Continue debate — Resume from a stalled debate folder"),
    ("H", "Help"),
    ("Q", "Quit"),
]


def _wizard_input(prompt_text: str, choices: list[str] | None = None) -> str:
    if _HAS_PT and choices and sys.stdin.isatty() and sys.stdout.isatty():
        completer = WordCompleter(choices, ignore_case=True)
        try:
            return pt_prompt(prompt_text, completer=completer).strip()
        except (EOFError, KeyboardInterrupt):
            return "Q"
    try:
        return input(prompt_text).strip()
    except (EOFError, KeyboardInterrupt):
        return "Q"


def cmd_wizard(args: argparse.Namespace) -> int:
    if _HAS_RICH:
        con().print(Panel.fit(  # type: ignore
            "[bold cyan]Welcome to FreeLLM Wizard[/bold cyan]\n"
            "Cross-platform multi-AI orchestration toolkit",
            border_style="cyan"
        ))
    else:
        print("\n=== FreeLLM Wizard ===\n")

    # Session-scoped preference (lives while wizard process runs).
    # If sticky is False, prompt every CombineTeam run.
    combine_reply_mode_pref: str = "files"
    combine_reply_mode_sticky = False
    debate_reply_mode_pref: str = "files"
    debate_reply_mode_sticky = False
    show_source_labels = bool(getattr(args, "show_source_labels", True))

    while True:
        if _HAS_RICH:
            t = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))  # type: ignore
            for key, label in _WIZARD_MENU:
                t.add_row(f"[bold yellow]{key}[/bold yellow]", label)
            con().print(t)  # type: ignore
        else:
            for key, label in _WIZARD_MENU:
                print(f"  [{key}] {label}")

        choice = _wizard_input("\nPick an option: ", [k for k, _ in _WIZARD_MENU]).upper()

        if choice == "Q":
            cprint("[cyan]Goodbye![/cyan]")
            return 0
        if choice == "H":
            cmd_help(args)
            continue
        if choice == "4":
            cmd_start(args)
            continue
        if choice == "5":
            cmd_stop(args)
            continue
        if choice == "6":
            script = Path(__file__).parent / "verify_all_keys.py"
            if script.exists():
                subprocess.run([sys.executable, str(script)], check=False)
            else:
                cprint("[red]verify_all_keys.py not found[/red]")
            continue
        if choice == "7":
            show_source_labels = not show_source_labels
            args.show_source_labels = show_source_labels
            state = "ON" if show_source_labels else "OFF"
            cprint(f"[green]Source labels are now {state}[/green]")
            continue
        if choice == "8":
            # List recent debate folders for convenience
            results_root = Path(args.results)
            recent = sorted(
                [d for d in results_root.glob("DebateTeam_*") if d.is_dir()],
                reverse=True
            )[:8]
            if recent:
                cprint("[bold]Recent debate folders:[/bold]")
                for d in recent:
                    prompt_f = d / "PROMPT.txt"
                    topic_hint = ""
                    if prompt_f.exists():
                        for line in prompt_f.read_text(encoding="utf-8").splitlines():
                            if line.startswith("topic:"):
                                topic_hint = line.split(":", 1)[1].strip()[:60]
                                break
                    completed = len(list(d.glob("Round_*/debater_01_*.md")))
                    cprint(f"  [yellow]{d.name}[/yellow]  rounds done: {completed}  topic: {topic_hint or '?'}")
            folder_raw = _wizard_input("Debate folder path (or folder name from list above): ").strip()
            if not folder_raw:
                cprint("[red]No folder specified.[/red]")
                continue
            folder_path = Path(folder_raw)
            if not folder_path.is_absolute() and not folder_path.is_dir():
                folder_path = results_root / folder_raw
            args.resume = str(folder_path)
            args.query = ""  # will be loaded from PROMPT.txt
            args.show_source_labels = show_source_labels
            cmd_debate(args)
            args.resume = ""
            continue

        # Ensure server is running before team commands
        if not _proxy_alive(args.base_url):
            cprint("[yellow]⚠ Proxy appears offline. Attempting to start…[/yellow]")
            cmd_start(args)

        if choice == "1":
            q = _wizard_input("Query: ")
            if not q.strip():
                cprint("[red]Query cannot be empty.[/red]")
                continue

            if combine_reply_mode_sticky:
                reply_mode = combine_reply_mode_pref
                cprint(f"[cyan]Using saved preference for this session: {reply_mode}[/cyan]")
            else:
                mode_raw = _wizard_input("Reply mode [chat/files] (default files): ").strip().lower()
                reply_mode = mode_raw if mode_raw in ("chat", "files") else "files"
                keep_raw = _wizard_input("Keep this preference for the rest of this session? [y/N]: ").strip().lower()
                if keep_raw in ("y", "yes"):
                    combine_reply_mode_pref = reply_mode
                    combine_reply_mode_sticky = True
                    cprint(f"[green]Saved session preference: {reply_mode}[/green]")

            n = _wizard_input("Number of AIs [5]: ") or "5"
            args.query = q
            args.n = int(n) if n.isdigit() else 5
            args.reply_mode = reply_mode
            args.show_source_labels = show_source_labels
            args.aliases = ",".join(DEFAULT_ALIASES)
            cmd_combine(args)
        elif choice == "2":
            q = _wizard_input("Debate topic: ")
            if not q.strip():
                cprint("[red]Debate topic cannot be empty.[/red]")
                continue

            if debate_reply_mode_sticky:
                reply_mode = debate_reply_mode_pref
                cprint(f"[cyan]Using saved DebateTeam preference for this session: {reply_mode}[/cyan]")
            else:
                mode_raw = _wizard_input("Debate reply mode [chat/files] (default files): ").strip().lower()
                reply_mode = mode_raw if mode_raw in ("chat", "files") else "files"
                keep_raw = _wizard_input("Keep this preference for the rest of this session? [y/N]: ").strip().lower()
                if keep_raw in ("y", "yes"):
                    debate_reply_mode_pref = reply_mode
                    debate_reply_mode_sticky = True
                    cprint(f"[green]Saved DebateTeam session preference: {reply_mode}[/green]")

            n = _wizard_input("Number of debaters [4]: ") or "4"
            r = _wizard_input("Number of rounds [3]: ") or "3"
            args.query = q
            args.n = int(n) if n.isdigit() else 4
            args.rounds = int(r) if r.isdigit() else 3
            args.reply_mode = reply_mode
            args.show_source_labels = show_source_labels
            args.aliases = ",".join(DEFAULT_ALIASES)
            cmd_debate(args)
        elif choice == "3":
            raw = _wizard_input("File paths (space-separated): ")
            p = _wizard_input("Instruction prompt: ")
            c = _wizard_input("Chunk size [3]: ") or "3"
            args.files = raw.split()
            args.prompt = p
            args.chunk = int(c) if c.isdigit() else 3
            args.model = "auto"
            args.aliases = ",".join(DEFAULT_ALIASES)
            cmd_fileteam(args)
        else:
            cprint("[red]Unknown choice.[/red]")


def _print_generated_paths(folder: Path) -> None:
    files = sorted([p for p in folder.rglob("*") if p.is_file()])
    cprint(f"[bold]Results folder:[/bold] {folder}")
    if not files:
        cprint("[yellow]No files generated in this folder.[/yellow]")
        return
    cprint("[bold]Generated files:[/bold]")
    for p in files:
        cprint(f"  - {p}")


def _source_label(res: AskResult) -> str:
    upstream = res.upstream_model or "unknown"
    return f"Upstream model: {upstream} | Alias: {res.alias}"


def cmd_spendreport(args: argparse.Namespace) -> int:
    days = max(1, int(getattr(args, "days", 1) or 1))
    db_path = _spend_db_path()
    if not db_path.exists():
        cprint(f"[yellow]No spend DB found yet at {db_path}[/yellow]")
        return 0

    conn = sqlite3.connect(db_path)
    try:
        since = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)).isoformat()
        total_row = conn.execute(
            """
            SELECT
                COUNT(*) AS reqs,
                COALESCE(SUM(response_cost_usd), 0),
                COALESCE(SUM(total_tokens), 0)
            FROM spend_events
            WHERE ts_utc >= ?
            """,
            (since,),
        ).fetchone()

        by_day = conn.execute(
            """
            SELECT
                substr(ts_utc, 1, 10) AS day,
                COUNT(*) AS reqs,
                COALESCE(SUM(response_cost_usd), 0) AS usd,
                COALESCE(SUM(total_tokens), 0) AS toks
            FROM spend_events
            WHERE ts_utc >= ?
            GROUP BY day
            ORDER BY day DESC
            """,
            (since,),
        ).fetchall()

        by_provider = conn.execute(
            """
            SELECT
                provider,
                COUNT(*) AS reqs,
                COALESCE(SUM(response_cost_usd), 0) AS usd
            FROM spend_events
            WHERE ts_utc >= ?
            GROUP BY provider
            ORDER BY usd DESC, reqs DESC
            LIMIT 20
            """,
            (since,),
        ).fetchall()
    finally:
        conn.close()

    reqs, usd, toks = total_row if total_row else (0, 0.0, 0)
    cprint(f"\n[bold cyan]Spend Report[/bold cyan] — last {days} day(s)")
    cprint(f"DB: {db_path}")
    cprint(f"Total requests: [bold]{reqs}[/bold]  |  Total tokens: [bold]{toks}[/bold]  |  Estimated USD: [bold]${usd:.6f}[/bold]\n")

    cprint("[bold]By day (UTC):[/bold]")
    if not by_day:
        cprint("  (no data)")
    for day, d_reqs, d_usd, d_toks in by_day:
        cprint(f"  {day}  reqs={d_reqs}  toks={d_toks}  usd=${d_usd:.6f}")

    cprint("\n[bold]By provider:[/bold]")
    if not by_provider:
        cprint("  (no data)")
    for provider, p_reqs, p_usd in by_provider:
        cprint(f"  {provider:<32} reqs={p_reqs:<5} usd=${p_usd:.6f}")
    return 0

# ── COMBINETEAM ───────────────────────────────────────────────────────────────
def cmd_combine(args: argparse.Namespace) -> int:
    n: int = getattr(args, "n", 5)
    query: str = getattr(args, "query", "")
    if not query or not query.strip():
        cprint("[red]Query cannot be empty. Use -q/--query with text.[/red]")
        return 2
    reply_mode: str = str(getattr(args, "reply_mode", "files") or "files").strip().lower()
    show_source_labels: bool = bool(getattr(args, "show_source_labels", True))
    if reply_mode not in ("chat", "files"):
        reply_mode = "files"
    aliases = [a.strip() for a in getattr(args, "aliases", ",".join(DEFAULT_ALIASES)).split(",") if a.strip()]
    out_dir: Path | None = results_dir(f"CombineTeam_{ts()}", Path(args.results)) if reply_mode == "files" else None
    messages = [{"role": "user", "content": query}]

    cprint(f"\n[bold cyan]CombineTeam[/bold cyan] — asking [yellow]{n}[/yellow] AIs: [italic]{query[:80]}[/italic]\n")

    results: list[AskResult] = []
    seen_upstream: set[str] = set()

    def try_alias(alias: str) -> AskResult:
        return _ask_one(args.base_url, args.api_key, alias, messages,
                        timeout=getattr(args, "timeout", 90),
                        max_tokens=getattr(args, "max_tokens", 1500))

    with cf.ThreadPoolExecutor(max_workers=min(n, len(aliases))) as ex:
        futures = {ex.submit(try_alias, a): a for a in aliases}
        for fut in cf.as_completed(futures):
            res = fut.result()
            key = res.upstream_model or res.alias
            if key in seen_upstream:
                continue
            if res.status != 200 or not res.reply.strip():
                continue
            seen_upstream.add(key)
            results.append(res)
            cprint(f"  [green]✓[/green] [{len(results)}/{n}] [cyan]{res.alias}[/cyan] → {(res.upstream_model or 'unknown')[:50]}")
            if len(results) >= n:
                break

    cprint("\n[bold cyan]CombineTeam Summary (chat)[/bold cyan]")
    for i, r in enumerate(results, 1):
        snippet = " ".join((r.reply or "").split())[:220]
        if len(" ".join((r.reply or "").split())) > 220:
            snippet += "..."
        if show_source_labels:
            cprint(f"  - AI {i} ({r.alias} | {r.upstream_model or 'unknown'}): {snippet or '(empty reply)'}")
        else:
            cprint(f"  - AI {i} ({r.alias}): {snippet or '(empty reply)'}")

    if reply_mode == "files" and out_dir is not None:
        # Write individual .md files + summary
        summary_lines: list[str] = [f"# CombineTeam Results\n\n**Query:** {query}\n\n**Date:** {datetime.datetime.now().isoformat()}\n"]
        for i, r in enumerate(results, 1):
            md = out_dir / f"response_{i:02d}_{r.alias.replace('/', '_')}.md"
            md.write_text(f"# Response {i}: {r.alias}\n\n**Upstream model:** {r.upstream_model or 'unknown'}\n\n---\n\n{r.reply}\n", encoding="utf-8")
            summary_lines.append(f"## AI {i}: {r.alias} ({r.upstream_model or 'unknown'})\n\n{r.reply}\n\n---\n")

        (out_dir / "SUMMARY.md").write_text("\n".join(summary_lines), encoding="utf-8")
        cprint(f"\n[green]✓ {len(results)} responses saved → {out_dir}[/green]")
        _print_generated_paths(out_dir)
    else:
        cprint(f"\n[green]✓ {len(results)} responses returned in chat[/green]")
        for i, r in enumerate(results, 1):
            cprint(f"\n[bold cyan]AI {i}[/bold cyan]")
            if show_source_labels:
                cprint(f"[dim]{_source_label(r)}[/dim]")
            cprint(r.reply.strip() or "(empty reply)")
    return 0

# ── DEBATETEAM ────────────────────────────────────────────────────────────────

def _load_debate_folder(folder: Path) -> tuple[str, int, int, list[str], list[list[dict]], dict[int, list], int]:
    """Load state from a DebateTeam results folder.
    Returns (query, rounds, n, aliases, history, round_results, last_completed_rnd).
    Raises ValueError with a human-readable message if the folder is invalid.
    """
    prompt_file = folder / "PROMPT.txt"
    if not prompt_file.exists():
        raise ValueError(f"No PROMPT.txt found in {folder}. Cannot resume (folder was created before prompt-saving feature).")

    meta: dict[str, str] = {}
    for line in prompt_file.read_text(encoding="utf-8").splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()

    query = meta.get("topic", "")
    rounds = int(meta.get("rounds", 3))
    n = int(meta.get("debaters", 4))
    aliases_raw = meta.get("aliases", ",".join(DEFAULT_ALIASES))
    aliases = [a.strip() for a in aliases_raw.split(",") if a.strip()]

    # Reconstruct round_results and history from saved MD files
    round_results: dict[int, list] = {}
    # Minimal AskResult-like namedtuple for loaded replies
    LoadedResult = __import__('collections').namedtuple("LoadedResult", ["alias", "upstream_model", "reply"])

    rnd = 1
    while True:
        rnd_dir = folder / f"Round_{rnd:02d}"
        if not rnd_dir.exists():
            break
        mds = sorted(rnd_dir.glob("debater_*.md"))
        if not mds:
            break
        results = []
        for md in mds:
            text = md.read_text(encoding="utf-8")
            # Parse alias from filename: debater_01_alias-name.md
            stem = md.stem  # e.g. debater_01_free-mode-fast
            parts = stem.split("_", 2)
            alias = parts[2].replace("_", "/") if len(parts) >= 3 else "unknown"
            # Parse upstream from header line "**Upstream:** ..."
            upstream = "unknown"
            for line in text.splitlines():
                if line.startswith("**Upstream:**"):
                    upstream = line.split("**Upstream:**", 1)[1].strip()
                    break
            # Body is everything after the first ---
            body_parts = text.split("\n---\n", 1)
            reply = body_parts[1].strip() if len(body_parts) > 1 else ""
            results.append(LoadedResult(alias=alias, upstream_model=upstream, reply=reply))
        round_results[rnd] = results
        rnd += 1

    last_completed_rnd = max(round_results.keys()) if round_results else 0

    # Rebuild history for each debater from scratch
    history: list[list[dict]] = [
        [{"role": "system", "content": (
            f"You are Debater {i+1} in a structured AI debate. "
            "Give clear, well-reasoned arguments. "
            "In critique rounds you MUST directly address the other responses shown to you."
        )},
         {"role": "user", "content": f"Debate topic: {query}\n\nPlease give your OPENING position."}]
        for i in range(n)
    ]
    for r in range(1, last_completed_rnd + 1):
        results = round_results.get(r, [])
        for i in range(n):
            res = results[i] if i < len(results) else LoadedResult(alias="?", upstream_model="?", reply="")
            history[i].append({"role": "assistant", "content": res.reply})
            # If there are more rounds after this, add the critique prompt
            if r < last_completed_rnd:
                prev_replies = "\n\n".join(
                    f"=== Debater {j+1} ({rr.alias}) ===\n{rr.reply}"
                    for j, rr in enumerate(results)
                )
                is_final_r = (r + 1 == rounds)
                if is_final_r:
                    history[i].append({"role": "user", "content": (
                        "All debaters have now responded. "
                        "As a judge/summarizer, synthesize the key points from all sides, "
                        "identify the strongest arguments, and declare what the debate consensus is (or explain remaining disagreement)."
                        f"\n\nAll responses so far:\n{prev_replies}"
                    )})
                else:
                    history[i].append({"role": "user", "content": (
                        f"Round {r+1}: Review the other debaters' Round {r} responses below "
                        "and write your critique and rebuttal.\n\n"
                        f"{prev_replies}"
                    )})

    return query, rounds, n, aliases, history, round_results, last_completed_rnd


def cmd_debate(args: argparse.Namespace) -> int:
    resume_folder: str = getattr(args, "resume", "") or ""
    if resume_folder.strip():
        # ── RESUME MODE ──────────────────────────────────────────────────────
        folder = Path(resume_folder.strip())
        if not folder.is_dir():
            cprint(f"[red]Resume folder not found: {folder}[/red]")
            return 2
        try:
            query, rounds, n, aliases, history, round_results, last_completed_rnd = _load_debate_folder(folder)
        except ValueError as exc:
            cprint(f"[red]{exc}[/red]")
            return 2
        cprint(f"[cyan]Resuming debate from round {last_completed_rnd + 1}/{rounds}[/cyan]")
        cprint(f"[italic]Topic: {query}[/italic]")
        if last_completed_rnd >= rounds:
            cprint("[yellow]All rounds already complete. Nothing to resume.[/yellow]")
            return 0
        reply_mode: str = str(getattr(args, "reply_mode", "files") or "files").strip().lower()
        if reply_mode not in ("chat", "files"):
            reply_mode = "files"
        show_source_labels: bool = bool(getattr(args, "show_source_labels", True))
        timeout = getattr(args, "timeout", 90)
        max_tokens = getattr(args, "max_tokens", 1500)
        out_base: Path | None = folder  # write remaining rounds into the same folder
        start_rnd = last_completed_rnd + 1
    else:
        # ── FRESH MODE ───────────────────────────────────────────────────────
        n: int = getattr(args, "n", 4)
        query: str = getattr(args, "query", "")
        if not query or not query.strip():
            cprint("[red]Debate topic cannot be empty. Use -q/--query with text.[/red]")
            return 2
        reply_mode: str = str(getattr(args, "reply_mode", "files") or "files").strip().lower()
        show_source_labels: bool = bool(getattr(args, "show_source_labels", True))
        if reply_mode not in ("chat", "files"):
            reply_mode = "files"
        rounds: int = getattr(args, "rounds", 3)
        aliases = [a.strip() for a in getattr(args, "aliases", ",".join(DEFAULT_ALIASES)).split(",") if a.strip()][:n]
        if len(aliases) < n:
            aliases = (aliases * ((n // len(aliases)) + 1))[:n]
        out_base: Path | None = results_dir(f"DebateTeam_{ts()}", Path(args.results)) if reply_mode == "files" else None
        timeout = getattr(args, "timeout", 90)
        max_tokens = getattr(args, "max_tokens", 1500)
        round_results: dict[int, list] = {}
        start_rnd = 1

        # Save prompt immediately so it survives a crash
        if out_base is not None:
            out_base.mkdir(parents=True, exist_ok=True)
            (out_base / "PROMPT.txt").write_text(
                f"topic: {query}\nrounds: {rounds}\ndebaters: {n}\naliases: {','.join(aliases)}\n",
                encoding="utf-8",
            )

        history: list[list[dict]] = [
            [{"role": "system", "content": (
                f"You are Debater {i+1} in a structured AI debate. "
                "Give clear, well-reasoned arguments. "
                "In critique rounds you MUST directly address the other responses shown to you."
            )},
             {"role": "user", "content": f"Debate topic: {query}\n\nPlease give your OPENING position."}]
            for i in range(n)
        ]

    cprint(f"\n[bold cyan]DebateTeam[/bold cyan] — [yellow]{n}[/yellow] debaters × [yellow]{rounds}[/yellow] rounds\n[italic]{query[:80]}[/italic]\n")

    for rnd in range(start_rnd, rounds + 1):
        rnd_dir: Path | None = None
        if out_base is not None:
            rnd_dir = out_base / f"Round_{rnd:02d}"
            rnd_dir.mkdir(exist_ok=True)
        is_final = (rnd == rounds)
        cprint(f"\n[bold yellow]── Round {rnd}/{rounds} {'(FINAL SUMMARY)' if is_final else ''} ──[/bold yellow]")

        if rnd > 1 and rnd > start_rnd:
            # Build cross-review context from previous round (skip on first resume
            # round because _load_debate_folder already appended it to history)
            prev_replies = "\n\n".join(
                f"=== Debater {j+1} ({r.alias}) ===\n{r.reply}"
                for j, r in enumerate(round_results[rnd - 1])
            )
            for i in range(n):
                if is_final:
                    new_msg = (
                        "All debaters have now responded. "
                        "As a judge/summarizer, synthesize the key points from all sides, "
                        "identify the strongest arguments, and declare what the debate consensus is (or explain remaining disagreement)."
                        f"\n\nAll responses so far:\n{prev_replies}"
                    )
                else:
                    new_msg = (
                        f"Round {rnd}: Review the other debaters' Round {rnd-1} responses below "
                        "and write your critique and rebuttal.\n\n"
                        f"{prev_replies}"
                    )
                history[i].append({"role": "user", "content": new_msg})

        def run_debater(i: int) -> AskResult:
            return _ask_one(args.base_url, args.api_key, aliases[i % len(aliases)],
                            history[i], timeout=timeout, max_tokens=max_tokens)

        with cf.ThreadPoolExecutor(max_workers=n) as ex:
            futs = list(ex.map(run_debater, range(n)))
        round_results[rnd] = list(futs)

        cprint(f"[bold cyan]Round {rnd} summary (chat)[/bold cyan]")
        for i, res in enumerate(futs):
            snippet = " ".join((res.reply or "").split())[:220]
            if len(" ".join((res.reply or "").split())) > 220:
                snippet += "..."
            if show_source_labels:
                cprint(f"  - Debater {i+1} ({res.alias} | {res.upstream_model or 'unknown'}): {snippet or '(empty reply)'}")
            else:
                cprint(f"  - Debater {i+1} ({res.alias}): {snippet or '(empty reply)'}")

            if reply_mode == "chat":
                cprint(f"\n[bold]Debater {i+1} full response[/bold]")
                if show_source_labels:
                    cprint(f"[dim]{_source_label(res)}[/dim]")
                cprint(res.reply.strip() or "(empty reply)")

            if rnd_dir is not None:
                md = rnd_dir / f"debater_{i+1:02d}_{res.alias.replace('/', '_')}.md"
                md.write_text(
                    f"# Round {rnd} — Debater {i+1}: {res.alias}\n\n"
                    f"**Upstream:** {res.upstream_model or 'unknown'}\n\n---\n\n{res.reply}\n",
                    encoding="utf-8"
                )
            # Append assistant reply to their history
            history[i].append({"role": "assistant", "content": res.reply})

    # Master summary
    summary = ["# DebateTeam Summary\n", f"**Topic:** {query}\n", f"**Rounds:** {rounds}  **Debaters:** {n}\n\n---\n"]
    for rnd in range(1, rounds + 1):
        summary.append(f"## Round {rnd}\n")
        for j, r in enumerate(round_results[rnd]):
            summary.append(f"### Debater {j+1} ({r.alias})\n\n{r.reply}\n\n")
    cprint("\n[bold cyan]DebateTeam Final Summary (chat)[/bold cyan]")
    for j, r in enumerate(round_results.get(rounds, []), 1):
        snippet = " ".join((r.reply or "").split())[:260]
        if len(" ".join((r.reply or "").split())) > 260:
            snippet += "..."
        if show_source_labels:
            cprint(f"  - Debater {j} ({r.alias} | {r.upstream_model or 'unknown'}): {snippet or '(empty reply)'}")
        else:
            cprint(f"  - Debater {j} ({r.alias}): {snippet or '(empty reply)'}")

    if out_base is not None:
        (out_base / "DEBATE_SUMMARY.md").write_text("\n".join(summary), encoding="utf-8")
        cprint(f"\n[green]✓ Debate complete — results saved to {out_base}[/green]")
        _print_generated_paths(out_base)
    else:
        cprint("\n[green]✓ Debate complete — full responses shown in chat mode.[/green]")
    return 0

# ── FILETEAM ──────────────────────────────────────────────────────────────────
CHAR_LIMIT_LARGE = 8_000   # chars — switch to free-mode-large above this

def _pick_alias_for_size(char_count: int, tier: str, aliases: list[str]) -> str:
    """Pick an appropriate alias based on file size / requested tier."""
    if tier == "large" or char_count > CHAR_LIMIT_LARGE:
        for a in aliases:
            if "large" in a:
                return a
    if tier == "paid":
        for a in aliases:
            if "paid" in a:
                return a
    return aliases[0]


def cmd_fileteam(args: argparse.Namespace) -> int:
    files: list[str] = getattr(args, "files", [])
    instruction: str = getattr(args, "prompt", "Summarize and extract key insights from the following document.")
    chunk: int = getattr(args, "chunk", 3)
    tier: str = getattr(args, "model", "auto")
    aliases = [a.strip() for a in getattr(args, "aliases", ",".join(DEFAULT_ALIASES)).split(",") if a.strip()]
    out_dir = results_dir(f"FileTeam_{ts()}", Path(args.results))
    timeout = getattr(args, "timeout", 120)
    max_tokens = getattr(args, "max_tokens", 2000)

    # Resolve paths
    resolved: list[Path] = []
    for f in files:
        p = Path(f)
        if not p.exists():
            cprint(f"[red]✗ File not found: {f}[/red]")
        else:
            resolved.append(p)

    if not resolved:
        cprint("[red]No valid files provided.[/red]")
        return 1

    cprint(f"\n[bold cyan]FileTeam[/bold cyan] — {len(resolved)} files, chunk={chunk}, tier={tier}\n")

    def process_file(fp: Path) -> tuple[Path, str]:
        content = fp.read_text(encoding="utf-8", errors="replace")
        char_count = len(content)
        alias = _pick_alias_for_size(char_count, tier, aliases)

        # Split into sections if very long (>12k chars)
        sections: list[str]
        if char_count > 12_000:
            size = 8_000
            sections = [content[i:i+size] for i in range(0, char_count, size)]
            cprint(f"  [yellow]→[/yellow] {fp.name} ({char_count} chars) split into {len(sections)} sections via [cyan]{alias}[/cyan]")
        else:
            sections = [content]
            cprint(f"  [cyan]→[/cyan] {fp.name} ({char_count} chars) via [cyan]{alias}[/cyan]")

        parts: list[str] = []
        for idx, section in enumerate(sections, 1):
            msg_content = f"{instruction}\n\n---\n\nFile: {fp.name}"
            if len(sections) > 1:
                msg_content += f" (section {idx}/{len(sections)})"
            msg_content += f"\n\n{section}"
            messages = [{"role": "user", "content": msg_content}]
            res = _ask_one(args.base_url, args.api_key, alias, messages, timeout=timeout, max_tokens=max_tokens)
            if res.error or not res.reply.strip():
                parts.append(f"[ERROR section {idx}: {res.error or 'empty reply'}]")
            else:
                parts.append(res.reply)

        combined = "\n\n---\n\n".join(parts)
        out_file = out_dir / (fp.stem + "_result.md")
        out_file.write_text(
            f"# FileTeam Result: {fp.name}\n\n"
            f"**Instruction:** {instruction}\n\n"
            f"**Model alias:** {alias}\n\n"
            f"**Sections:** {len(sections)}\n\n---\n\n{combined}\n",
            encoding="utf-8"
        )
        return fp, combined

    # Process in chunks
    all_results: list[tuple[Path, str]] = []
    for batch_start in range(0, len(resolved), chunk):
        batch = resolved[batch_start: batch_start + chunk]
        cprint(f"\n[bold]Processing chunk {batch_start//chunk + 1} — {[f.name for f in batch]}[/bold]")
        with cf.ThreadPoolExecutor(max_workers=len(batch)) as ex:
            batch_results = list(ex.map(process_file, batch))
        all_results.extend(batch_results)
        cprint(f"  [green]✓ Chunk done.[/green]")

    # Master index
    index_lines = [f"# FileTeam Index\n\n**Instruction:** {instruction}\n\n"]
    for fp, reply in all_results:
        index_lines.append(f"## {fp.name}\n\n{reply[:400]}{'...' if len(reply) > 400 else ''}\n\n---\n")
    (out_dir / "INDEX.md").write_text("\n".join(index_lines), encoding="utf-8")
    cprint(f"\n[green]✓ FileTeam complete — {len(all_results)} files processed → {out_dir}[/green]")
    _print_generated_paths(out_dir)
    return 0

# ── ARGUMENT PARSER ───────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="FreeLLM",
        description="FreeLLM — cross-platform multi-AI orchestration CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
    )
    p.add_argument("command", nargs="?", default=None,
                   help="Command: help/-H, start/-STA, stop/-STO, wizard/-W/ui, CombineTeam, DebateTeam, FileTeam, SpendReport")
    p.add_argument("-H", "-h", "--help", dest="show_help", action="store_true")
    p.add_argument("-STA", "--start", dest="do_start", action="store_true")
    p.add_argument("-STO", "--stop",  dest="do_stop",  action="store_true")
    p.add_argument("-W",   "--wizard",dest="do_wizard",action="store_true")
    # global
    p.add_argument("--base-url",  default=DEFAULT_BASE_URL)
    p.add_argument("--api-key",   default=os.environ.get("LITELLM_KEY", "anything"))
    p.add_argument("--results",   default=str(DEFAULT_RESULTS))
    p.add_argument("--no-color",  action="store_true")
    p.add_argument("--timeout",   type=int, default=90)
    p.add_argument("--max-tokens",type=int, default=1500)
    # CombineTeam
    p.add_argument("-q", "--query", default="")
    p.add_argument("-n",  type=int, default=5)
    p.add_argument("--aliases", default=",".join(DEFAULT_ALIASES))
    p.add_argument("--reply-mode", default="files", choices=["chat", "files"])
    p.add_argument("--show-source-labels", dest="show_source_labels", action=argparse.BooleanOptionalAction, default=True)
    # DebateTeam
    p.add_argument("--rounds", type=int, default=3)
    p.add_argument("--resume", default="", metavar="FOLDER",
                   help="Resume a DebateTeam from an existing results folder")
    # FileTeam
    p.add_argument("--files",  nargs="*", default=[])
    p.add_argument("--prompt", default="Summarize and extract key insights from this document.")
    p.add_argument("--chunk",  type=int, default=3)
    p.add_argument("--model",  default="auto", choices=["auto", "free", "paid", "large"])
    # SpendReport
    p.add_argument("--days", type=int, default=1)
    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    raw_argv = sys.argv[1:]
    query_flag_present = any(
        token in ("-q", "--query") or token.startswith("--query=")
        for token in raw_argv
    )

    if args.no_color:
        global _HAS_RICH
        _HAS_RICH = False

    # Resolve command from positional or flags
    cmd = (args.command or "").lower().lstrip("-")

    # Explicit help flag always shows help (never falls through to wizard)
    if args.show_help or cmd in ("h", "help"):
        return cmd_help(args)

    # Bare invocation with no flags → wizard
    if not cmd and not any([args.do_start, args.do_stop, args.do_wizard, args.query, args.files]):
        return cmd_wizard(args)

    if args.do_start or cmd in ("sta", "start"):
        return cmd_start(args)

    if args.do_stop or cmd in ("sto", "stop"):
        return cmd_stop(args)

    if args.do_wizard or cmd in ("w", "wizard", "ui"):
        return cmd_wizard(args)

    if cmd == "combineteam":
        if not args.query and not query_flag_present:
            args.query = _wizard_input("Query: ")
        if not args.query or not args.query.strip():
            cprint("[red]Query cannot be empty.[/red]")
            return 2
        return cmd_combine(args)

    if cmd == "debateteam":
        if not args.query and not query_flag_present:
            args.query = _wizard_input("Debate topic: ")
        if not args.query or not args.query.strip():
            cprint("[red]Debate topic cannot be empty.[/red]")
            return 2
        return cmd_debate(args)

    if cmd == "fileteam":
        if not args.files:
            raw = _wizard_input("File paths (space-separated): ")
            args.files = raw.split()
        if not args.prompt or args.prompt == parser.get_default("prompt"):
            args.prompt = _wizard_input("Instruction prompt: ")
        return cmd_fileteam(args)

    if cmd in ("spendreport", "spend", "spending"):
        return cmd_spendreport(args)

    cprint(f"[red]Unknown command: {args.command!r}. Run 'FreeLLM -H' for help.[/red]")
    return 1


if __name__ == "__main__":
    sys.exit(main())
