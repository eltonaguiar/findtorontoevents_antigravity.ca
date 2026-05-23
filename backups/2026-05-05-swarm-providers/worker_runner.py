#!/usr/bin/env python3
"""Engine adapter for the swarm.

Routes one prompt to a CLI/API engine, captures response, and writes
result + raw sidecar. Logging/timing via swarm_log.CallTimer.

Supported engines:
    CLI:  claude, gemini, opencode, kilo, copilot, agent (Cursor), kimi (Moonshot), openclaude, codex (OpenAI)
    API:  deepseek, cerebras, xai, inception, ollama_cloud, ollama_local, openrouter (driven via tools/swarm/api_consult.py)

Usage:
    python tools/swarm/worker_runner.py --engine claude --pr 123 \\
        --prompt-file tools/swarm/prompts/pr_review.md \\
        --out-file swarm_runs/<TS>/pr_123.claude.json [--model sonnet]

Excluded: freebuff (TUI-only), codebuff (TUI-only + out of credits).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from swarm_log import CallTimer, log_call  # noqa: E402
import _engine_overrides  # noqa: E402
from safety import (  # noqa: E402
    isolated_env,
    READ_ONLY_ALLOWED,
    READ_ONLY_DISALLOWED,
)
from output_parsers import parse_engine_output  # noqa: E402
from session_manager import (  # noqa: E402
    get_session,
    new_session as sm_new_session,
    record_message,
    render_md_context,
    replay_messages,
    update_session,
)

REPO = Path(__file__).resolve().parents[2]
SWARM_DIR = REPO / "swarm_runs"
API_CONSULT = REPO / "tools" / "swarm" / "api_consult.py"

CLI_ENGINES = {"claude", "gemini", "opencode", "kilo", "copilot", "agent", "kimi", "openclaude", "codex"}
PTY_ENGINES = {"freebuff"}
API_ENGINES = {"deepseek", "cerebras", "xai", "inception", "ollama_cloud", "ollama_local", "openrouter", "nous", "groq", "huggingface", "gemini_api", "github_models", "pollinations"}

# Cursor `agent` CLI ships outside %APPDATA%/npm — its installer drops a
# .cmd shim under %LOCALAPPDATA%/cursor-agent/. _resolve_cli() only probes
# %APPDATA%/npm + PATH, so we add an explicit override here so the
# resolver picks the .cmd shim deterministically without requiring the
# user to mutate their PATH. Order: env override > LOCALAPPDATA shim >
# PATH ("cursor-agent" / "agent").
def _resolve_cursor_agent() -> list[str]:
    cached = _CLI_RESOLVE_CACHE.get("agent")
    if cached:
        return cached
    explicit = os.environ.get("CURSOR_AGENT_CLI")
    candidates: list[list[str]] = []
    if explicit:
        candidates.append([explicit])
    local_app = Path(os.environ.get("LOCALAPPDATA", "")) / "cursor-agent"
    cmd_shim = local_app / "cursor-agent.cmd"
    if cmd_shim.exists():
        candidates.append([str(cmd_shim)])
    candidates.append(["cursor-agent"])  # PATH fallback
    candidates.append(["agent"])           # legacy / *nix install
    for cand in candidates:
        if _smoke_check(cand):
            _CLI_RESOLVE_CACHE["agent"] = cand
            return cand
    fallback = candidates[0] if candidates else ["cursor-agent"]
    _CLI_RESOLVE_CACHE["agent"] = fallback
    return fallback


def _resolve_kimi_cli() -> list[str]:
    """Resolve the Kimi CLI binary.

    Kimi (Moonshot AI) ships as `kimi.exe` bundled with the VS Code extension
    `moonshot-ai.kimi-code`, NOT in `%APPDATA%/npm`. Default install path:
        %APPDATA%/Code/User/globalStorage/moonshot-ai.kimi-code/bin/kimi/kimi.exe
    On macOS / Linux the bundled binary lives at
        ~/.vscode/extensions/moonshot-ai.kimi-code-*/bin/kimi/kimi
    Resolution order: explicit `KIMI_CLI` env override > VS Code extension
    binary > PATH (`kimi` / `kimi-cli`).

    Auth model: OAuth via `kimi login`; token stored under `~/.kimi/`.
    No API key env var is required for headless `--print` runs.
    """
    cached = _CLI_RESOLVE_CACHE.get("kimi")
    if cached:
        return cached
    explicit = os.environ.get("KIMI_CLI")
    candidates: list[list[str]] = []
    if explicit:
        candidates.append([explicit])
    # VS Code extension bundled binary (Windows).
    appdata = Path(os.environ.get("APPDATA", ""))
    vscode_bin = (
        appdata / "Code" / "User" / "globalStorage"
        / "moonshot-ai.kimi-code" / "bin" / "kimi" / "kimi.exe"
    )
    if vscode_bin.exists():
        candidates.append([str(vscode_bin)])
    # macOS / Linux: ~/.vscode/extensions/moonshot-ai.kimi-code-*/bin/kimi/kimi
    home = Path(os.environ.get("USERPROFILE") or os.environ.get("HOME") or "")
    if home:
        ext_root = home / ".vscode" / "extensions"
        if ext_root.exists():
            for ext_dir in sorted(ext_root.glob("moonshot-ai.kimi-code-*")):
                for binname in ("kimi", "kimi.exe"):
                    cand = ext_dir / "bin" / "kimi" / binname
                    if cand.exists():
                        candidates.append([str(cand)])
                        break
    candidates.append(["kimi"])      # PATH fallback
    candidates.append(["kimi-cli"])  # legacy alias
    for cand in candidates:
        if _smoke_check(cand):
            _CLI_RESOLVE_CACHE["kimi"] = cand
            return cand
    fallback = candidates[0] if candidates else ["kimi"]
    _CLI_RESOLVE_CACHE["kimi"] = fallback
    return fallback


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _load_persona(name: str | None) -> str:
    """Resolve `name` to a persona body and strip YAML frontmatter.

    Resolution candidates (cross-platform via `pathlib.Path`):
      1. `tools/swarm/agent_personas/<name>.md`
      2. `tools/swarm/agent_personas/<name>_specialist.md`
      3. `<name>` treated as an absolute or relative path.

    Returns the trimmed body (frontmatter stripped). Raises FileNotFoundError
    if no candidate resolves — so a typo in `--persona` fails loudly rather
    than silently dropping the persona contract.
    """
    if not name:
        return ""
    base = Path(__file__).resolve().parent / "agent_personas"
    # Personas advertise hyphenated names in YAML frontmatter (`name: crypto-specialist`)
    # but ship as underscored files (`crypto_specialist.md`). Try both.
    norm = name.replace("-", "_")
    candidates = [
        base / f"{name}.md",
        base / f"{name}_specialist.md",
        base / f"{norm}.md",
        base / f"{norm}_specialist.md",
        Path(name),  # absolute or relative fallback
    ]
    for p in candidates:
        try:
            if p.exists():
                text = p.read_text(encoding="utf-8")
                # Strip YAML frontmatter (3-dash delimiter only).
                if text.startswith("---"):
                    end = text.find("\n---", 3)
                    if end >= 0:
                        text = text[end + 4:]
                return text.strip()
        except OSError:
            continue
    raise FileNotFoundError(f"persona not found: {name}")


def _read_prompt(args: argparse.Namespace) -> str:
    base = Path(args.prompt_file).read_text(encoding="utf-8")
    if args.pr is not None:
        base = base.replace("{{PR_NUMBER}}", str(args.pr))
    if args.context_md:
        ctx = Path(args.context_md).read_text(encoding="utf-8")
        base = (
            "Prior conversation context (read carefully, do NOT re-do work "
            "already covered):\n---\n" + ctx + "\n---\n\nNew task:\n" + base
        )
    persona_text = _load_persona(getattr(args, "persona", None))
    if persona_text:
        base = (
            "## You are operating under this persona contract\n"
            + persona_text
            + "\n\n## Task\n"
            + base
        )
    return base


def _strip_code_fences(s: str) -> str:
    s = s.strip()
    m = re.match(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", s, re.DOTALL)
    return m.group(1).strip() if m else s


# Smart-quote / typographic punctuation -> ASCII. The local `ollama` CLI on
# Windows wraps text at terminal width even when piped, and some cloud models
# emit U+2018/2019/201C/201D/2011 (non-breaking hyphen) which break json.loads.
_SMART_PUNCT = {
    "‘": "'",  # left single quote
    "’": "'",  # right single quote / apostrophe
    "‚": "'",  # single low-9 quote
    "‛": "'",
    "“": '"',  # left double quote
    "”": '"',  # right double quote
    "„": '"',  # double low-9 quote
    "‟": '"',
    "′": "'",  # prime
    "″": '"',  # double prime
    "‑": "-",  # non-breaking hyphen (ollama emits this)
    "–": "-",  # en dash
    "—": "-",  # em dash
    "…": "...",  # ellipsis
}


def _normalize_smart_punct(s: str) -> str:
    if not s:
        return s
    for src, dst in _SMART_PUNCT.items():
        if src in s:
            s = s.replace(src, dst)
    return s


def _try_parse_unwrapped(s: str) -> dict | None:
    """Last-ditch fix for terminal line-wrap corruption: when an `ollama` /
    similar CLI emits 80-col line wraps that landed inside a JSON string,
    we get bare LFs (or duplicated wrap-words) inside string literals.
    Strategy: walk the candidate string; while inside a JSON string ("..."),
    rewrite raw \n/\r/\t to escaped form so json.loads accepts them.
    """
    if not s:
        return None
    out: list[str] = []
    in_str = False
    escape = False
    for ch in s:
        if escape:
            out.append(ch)
            escape = False
            continue
        if ch == "\\" and in_str:
            out.append(ch)
            escape = True
            continue
        if ch == '"':
            in_str = not in_str
            out.append(ch)
            continue
        if in_str and ch in ("\n", "\r", "\t"):
            out.append({"\n": "\\n", "\r": "\\r", "\t": "\\t"}[ch])
            continue
        out.append(ch)
    fixed = "".join(out)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        return None


def _extract_json_object(s: str) -> dict | None:
    s = _strip_code_fences(s)
    s = _normalize_smart_punct(s)
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    # Aggressive slice: first '{' to last '}'.
    first = s.find("{")
    last = s.rfind("}")
    if first >= 0 and last > first:
        slice_ = s[first : last + 1]
        try:
            return json.loads(slice_)
        except json.JSONDecodeError:
            pass
        # Repair line-wrap corruption inside JSON strings.
        repaired = _try_parse_unwrapped(slice_)
        if repaired is not None:
            return repaired
    # Fallback: balanced-brace walker (handles concatenated outputs).
    depth = 0
    start = -1
    for i, ch in enumerate(s):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    return json.loads(s[start : i + 1])
                except json.JSONDecodeError:
                    start = -1
    return None


def _run(cmd: list[str], stdin_data: str | None = None, timeout: int = 600,
         env: dict[str, str] | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(
        cmd, input=stdin_data, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout, shell=False,
        env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


_CLI_RESOLVE_CACHE: dict[str, list[str]] = {}


def _smoke_check(cmd: list[str], timeout: int = 8) -> bool:
    """Run `<cmd> --version` (then `--help` as fallback) and return True
    if the launch itself succeeded — i.e. CreateProcess found the file
    and we got SOME output. We don't require rc=0 because some CLIs
    (notably gemini under transient API errors) can return non-zero
    even when the binary works; we only want to detect the
    "system cannot find file" CreateProcess failure.
    """
    for probe in (["--version"], ["--help"]):
        try:
            r = subprocess.run(
                cmd + probe, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=timeout, shell=False,
            )
        except (FileNotFoundError, OSError):
            return False
        except subprocess.TimeoutExpired:
            # Process launched but is hanging — treat as launch-OK.
            return True
        # CreateProcess succeeded if we got either stdout or recognizable stderr.
        if r.stdout or r.stderr:
            return True
    return False


def _resolve_cli(name: str) -> list[str]:
    """Windows: prefer .cmd shim from %APPDATA%/npm; fall back to .ps1 then PATH.

    Adds a smoke check the first time a name is resolved: if the .cmd
    resolves but fails to launch (e.g., npm shim broken after an update),
    we fall through to the .ps1 path via powershell. Result is cached
    per-process to avoid re-probing on every call_*.
    """
    if name in _CLI_RESOLVE_CACHE:
        return _CLI_RESOLVE_CACHE[name]

    npm_dir = Path(os.environ.get("APPDATA", "")) / "npm"
    cmd_path = npm_dir / f"{name}.cmd"
    ps1_path = npm_dir / f"{name}.ps1"
    ps1_invocation = [
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", str(ps1_path),
    ]

    candidates: list[list[str]] = []
    if cmd_path.exists():
        candidates.append([str(cmd_path)])
    if ps1_path.exists():
        candidates.append(ps1_invocation)
    candidates.append([name])  # fall back to PATH

    for cand in candidates:
        if _smoke_check(cand):
            _CLI_RESOLVE_CACHE[name] = cand
            return cand

    # All probes failed; return the best-guess so the caller can surface
    # a real error rather than silently swap to PATH.
    fallback = candidates[0] if candidates else [name]
    _CLI_RESOLVE_CACHE[name] = fallback
    return fallback


def _cli_meta(rc: int) -> dict:
    """Build a minimal imp-B meta dict for CLI engines. CLI engines don't
    expose model fingerprints or token usage reliably; transport_status is
    derived from subprocess rc."""
    if rc == 0:
        status = "ok"
    elif rc == 4:
        status = "timeout"
    else:
        status = f"rc={rc}"
    return {
        "model_fingerprint": "",
        "tokens_in": 0,
        "tokens_out": 0,
        "transport_status": status,
    }


def call_claude(prompt: str, args: argparse.Namespace) -> tuple[str, str, dict]:
    base = _resolve_cli("claude")
    # Always pipe prompt via stdin. Previously, prompts <=6000 bytes went
    # through `-p <prompt>` argv. PR-review prompts are 5-8 KB (5 KB raw +
    # ~3 KB of allowedTools / disallowedTools flag list pushed argv past
    # the cmd.exe 8191-char ceiling on some shim paths). Symptom: claude
    # launched, returned ~32-59 raw bytes containing only its system
    # banner ("Ready. Awaiting PR review task." or similar), then exited
    # rc=0 with the per-task prompt silently dropped. Verified against
    # 3/3 claude jobs in swarm_runs/PR_REVIEW_ABORTED.md (2026-05-03).
    # Stdin pipe is supported by `claude -p` for any size and removes the
    # threshold class of failure entirely. Net: we lose nothing (claude
    # always respects stdin when -p has no argument) and gain reliability.
    cmd = base + ["-p"]
    cmd += [
        "--model", args.model or "sonnet",
        "--output-format", "json",
        "--max-turns", "12",
        "--permission-mode", "default",
    ]
    if args.session_id:
        cmd += ["--session-id", args.session_id]
    if args.resume:
        cmd += ["--resume", args.resume]
    cmd += ["--allowedTools", *READ_ONLY_ALLOWED,
            "--disallowedTools", *READ_ONLY_DISALLOWED]
    rc, out, err = _run(cmd, stdin_data=prompt, timeout=900)
    if rc != 0:
        sys.stderr.write(f"[claude rc={rc}] {err[-500:]}\n")
    sid = ""
    text = out
    try:
        env = json.loads(out)
        sid = env.get("session_id") or env.get("session", "")
        text = env.get("result") or env.get("text") or out
    except json.JSONDecodeError:
        text = out
    return text, sid, _cli_meta(rc)


_GEMINI_JSON_PREFIX = (
    "STRICT MODE: respond with VALID JSON ONLY. "
    "No prose, no markdown, no code fences, no explanation before or after. "
    "First character of your response MUST be '{'. "
    "Last character MUST be '}'. "
    "If the user task does not specify a JSON shape, default to "
    "{\"answer\": \"<your answer text>\"}. "
    "Begin task:\n\n"
)


def call_gemini(prompt: str, args: argparse.Namespace) -> tuple[str, str, dict]:
    """Drive Gemini CLI. Wrap prompt in JSON-only framing because Gemini
    ignores in-prompt JSON contracts when --output-format is unset.
    """
    base = _resolve_cli("gemini")
    wrapped = _GEMINI_JSON_PREFIX + prompt if args.json_strict else prompt
    cmd = base + ["-p", wrapped, "--approval-mode", "plan"]
    if args.model:
        cmd += ["-m", args.model]
    rc, out, err = _run(cmd, timeout=900)
    if rc != 0:
        sys.stderr.write(f"[gemini rc={rc}] {err[-500:]}\n")
    return out, "", _cli_meta(rc)


def call_opencode_or_kilo(engine: str, prompt: str, args: argparse.Namespace) -> tuple[str, str, dict]:
    """Pipe prompt via stdin if possible; positional fallback. Windows arg
    quoting drops content past first newline on long prompts, so we feed
    via stdin and pass an empty-string trigger arg."""
    base = _resolve_cli(engine)
    # Use stdin path to dodge Windows arg-length / quoting issues.
    cmd = base + ["run"]
    if args.model:
        cmd += ["--model", args.model]
    rc, out, err = _run(cmd, stdin_data=prompt, timeout=900)
    if rc != 0:
        sys.stderr.write(f"[{engine} rc={rc}] {err[-500:]}\n")
    meta = _cli_meta(rc)
    # If subprocess returned 0 but produced no output (the kilo silent-failure
    # symptom from self-review run), record it as "closed-by-peer" so the
    # audit trail distinguishes it from genuine `ok` rc=0 calls.
    if rc == 0 and not out:
        meta["transport_status"] = "closed-by-peer"
    return out, "", meta


def _resolve_copilot_cli() -> list[str]:
    """Thin wrapper around `_resolve_cli('copilot')` so tests can patch the
    copilot-specific resolver in isolation without affecting other engines.

    Kept stable for `tests/test_swarm_tooling.py::test_copilot_prompt_preserves_metacharacters`
    which uses `mock.patch.object(worker_runner, '_resolve_copilot_cli', ...)`.
    """
    return _resolve_cli("copilot")


def call_copilot(prompt: str, args: argparse.Namespace) -> tuple[str, str, dict]:
    base = _resolve_copilot_cli()
    cmd = base + ["-p", prompt]
    rc, out, err = _run(cmd, timeout=900)
    if rc != 0:
        sys.stderr.write(f"[copilot rc={rc}] {err[-500:]}\n")
    return out, "", _cli_meta(rc)


def call_agent(prompt: str, args: argparse.Namespace) -> tuple[str, str, dict]:
    """Drive Cursor `agent` CLI (cursor-agent).

    Cursor agent is OAuth-authenticated (`cursor-agent login`) and exposes a
    headless `-p / --print` flag. JSON envelope (`--output-format json`)
    yields `{"type":"result","result":"...","session_id":"...","usage":{...}}`
    -- nearly identical to claude's envelope, so we extract `.result` here
    and stash `session_id` for resume support. `--trust` is required in
    headless mode for any tool use; we pass `--force` (alias `--yolo`)
    so the read-only allowlist semantics are deferred to the model rather
    than inducing approval prompts that hang the headless run.

    Stdin piping does NOT work for cursor-agent (verified 2026-05-03 on
    2026.05.01-eea359f) -- the binary blocks waiting for a tty. We pass
    the prompt as a single positional arg via subprocess.run (shell=False),
    which preserves embedded newlines + UTF-8 in args.

    LARGE-PROMPT FALLBACK: Windows CreateProcessW caps the command line at
    ~32 KB. PR-review prompts can hit 40-50 KB once the diff + checks
    output is interpolated. For prompts >24 KB we write the prompt to a
    temp .md file under the system TEMP dir and pass a shorter prompt
    that instructs cursor-agent to Read that file. Verified empirically:
    on 2026-05-03 a 46 KB prompt for PR #676 review hit
    `[WinError 206] The filename or extension is too long` from
    CreateProcess; the fallback path avoids this entirely.
    """
    import tempfile
    base = _resolve_cursor_agent()
    cmd = base + ["-p", "--output-format", "json", "--force"]
    if args.model:
        cmd += ["--model", args.model]
    if args.resume:
        cmd += ["--resume", args.resume]
    elif getattr(args, "session_id", None):
        # cursor-agent has no --session-id flag; --resume is the closest
        # equivalent for chained turns.
        cmd += ["--resume", args.session_id]

    # Conservative threshold: 24 KB leaves headroom for the resolver
    # prefix + flag args + cursor-agent's own command-line padding before
    # CreateProcessW's ~32k limit kicks in.
    prompt_bytes = len(prompt.encode("utf-8", errors="replace"))
    tmp_path: str | None = None
    if prompt_bytes > 24_000:
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", prefix="swarm_agent_prompt_",
            encoding="utf-8", delete=False,
        )
        tmp.write(prompt)
        tmp.flush()
        tmp.close()
        tmp_path = tmp.name
        marker_prompt = (
            f"The full task prompt is in the file at:\n\n  {tmp_path}\n\n"
            f"Read that file with your Read tool, then perform the task "
            f"described inside it. Respond per the instructions in the file."
        )
        cmd += [marker_prompt]
    else:
        # Positional prompt (last arg). cursor-agent treats trailing args
        # as the prompt joined by spaces, but a single arg preserves
        # whitespace.
        cmd += [prompt]

    try:
        rc, out, err = _run(cmd, timeout=900)
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    if rc != 0:
        sys.stderr.write(f"[agent rc={rc}] {err[-500:]}\n")
    sid = ""
    text = out
    try:
        env = json.loads(out)
        if isinstance(env, dict):
            sid = env.get("session_id") or ""
            text = env.get("result") or env.get("text") or out
    except json.JSONDecodeError:
        # Output may be plain text if user passes --output-format text via
        # CURSOR_AGENT_FORMAT or older versions; keep raw.
        text = out
    return text, sid, _cli_meta(rc)


def call_kimi(prompt: str, args: argparse.Namespace) -> tuple[str, str, dict]:
    """Drive Kimi CLI (Moonshot AI).

    Kimi is the Moonshot AI coding agent (`kimi.exe`, v1.23.0+). Auth is
    OAuth via `kimi login`; token stored under `~/.kimi/`. No API key env
    var is required.

    Headless invocation: `--quiet` is an alias for
    `--print --output-format text --final-message-only` and yields a clean
    final assistant message with no banner / spinner / step output. We pass
    `-p` (`--prompt`) with the prompt body, plus `--quiet` for clean stdout.
    `--print` implies `--yolo`, so no approval prompts.

    Stdin handling: kimi's `-p` flag accepts a positional TEXT value. For
    long prompts (>800 B) we still pass via `-p` because `--input-format`
    requires `--print` and reading from stdin needs `--input-format text`
    AND a piped stdin. Empirically `-p <prompt>` works fine for prompts up
    to the Windows 32K command-line ceiling — sufficient for swarm briefs.
    """
    base = _resolve_kimi_cli()
    cmd = base + ["--quiet", "-p", prompt]
    if args.model:
        cmd += ["--model", args.model]
    if args.session_id:
        cmd += ["--session", args.session_id]
    elif args.resume:
        cmd += ["--continue"]
    rc, out, err = _run(cmd, timeout=900)
    if rc != 0:
        sys.stderr.write(f"[kimi rc={rc}] {err[-500:]}\n")
    # Kimi emits a clean final-message in --quiet mode (no JSON envelope).
    # Session id is not surfaced in headless output; resume requires the
    # caller to track the session id externally via `kimi -S <id>`. We pass
    # an empty sid for now.
    return out, "", _cli_meta(rc)


def call_openclaude(prompt: str, args: argparse.Namespace) -> tuple[str, str, dict]:
    """Drive openclaude CLI (`@gitlawb/openclaude`).

    OpenClaude is a third-party fork of Claude Code with a `--provider` flag
    that routes to OpenAI / Gemini / DeepSeek / Ollama / GitHub Models /
    Bedrock / Vertex / Foundry in addition to Anthropic. It re-uses Claude's
    `-p / --print` headless mode and JSON envelope, so the integration mirrors
    `call_claude` shape but defaults `--provider openai` to give the swarm
    actual model diversity (vs duplicating the native `claude` engine slot).

    Auth: provider-dependent — reads OPENAI_API_KEY / GEMINI_API_KEY /
    DEEPSEEK_API_KEY / ANTHROPIC_API_KEY / GH_TOKEN from env. Override the
    provider per-run via `--model openai|gemini|deepseek|...` (passed through
    as `--provider`). The optional `OPENCLAUDE_PROVIDER` env var sets a
    default if `--model` is not provided.

    Long-prompt handling: `-p <prompt>` is positional and tested up to ~6 KB
    on Windows without truncation. Stdin piping is NOT used because openclaude
    inherits Claude Code's stdin reservation for `--input-format stream-json`.

    Trust caveat: third-party multi-provider router (`@gitlawb/openclaude` on
    npm; source: github.com/Gitlawb/openclaude). Audit `package.json` before
    upgrading. v0.7.0 (verified 2026-05-03) ships clean: no postinstall hook,
    no install scripts on disk, single bundled `dist/cli.mjs`. Do not install
    on production-secret hosts without re-audit.
    """
    base = _resolve_cli("openclaude")
    # `--model` in swarm parlance = LLM model name; for openclaude we map it
    # onto `--provider` because the CLI's own `--model` arg is the model
    # within a provider (e.g. "gpt-4o", "deepseek-chat"). Provider precedence:
    # explicit args.model > OPENCLAUDE_PROVIDER env > "openai" default.
    provider = args.model or os.environ.get("OPENCLAUDE_PROVIDER") or "openai"
    cmd = base + ["-p", prompt, "--provider", provider, "--output-format", "json"]
    if args.resume:
        cmd += ["--resume", args.resume]
    elif getattr(args, "session_id", None):
        cmd += ["--session-id", args.session_id]
    rc, out, err = _run(cmd, timeout=900)
    if rc != 0:
        sys.stderr.write(f"[openclaude rc={rc}] {err[-500:]}\n")
    sid = ""
    text = out
    try:
        env = json.loads(out)
        if isinstance(env, dict):
            sid = env.get("session_id") or ""
            text = env.get("result") or env.get("text") or out
    except json.JSONDecodeError:
        # Older builds or non-JSON providers return plain text; keep raw.
        text = out
    return text, sid, _cli_meta(rc)


def call_codex(prompt: str, args: argparse.Namespace) -> tuple[str, str, dict]:
    """Drive OpenAI `codex` CLI (`@openai/codex`).

    Codex (OpenAI Codex CLI v0.128.0+) ships at `%APPDATA%/npm/codex.cmd`;
    standard `_resolve_cli("codex")` finds it. Auth: OAuth via `codex login`
    (ChatGPT-bundled) is the primary path -- no env var required. The
    `OPENAI_API_KEY` env var is an OPTIONAL alternate auth that codex picks up
    automatically when present, but the swarm does not require it; we leave
    `ENGINE_REQUIRED_KEYS["codex"]` empty + pass-through OPENAI_API_KEY in the
    isolated env so either auth model works.

    Headless invocation: `codex exec` is the non-interactive subcommand.
    Critical flags:
      * `--skip-git-repo-check` -- otherwise codex aborts when launched in a
        non-git workdir (matters for `swarm_runs/_codex_smoke/` paths).
      * `--sandbox read-only` -- swarm contract is read-only by default;
        codex's default sandbox is `workspace-write` which would let the model
        edit files. Hard-coded to `read-only` here to mirror the read-only
        allowlist semantics applied to claude / agent / kimi.
      * `--json` -- emits JSONL events on stdout. We parse `agent_message`
        items for the response text and `turn.completed.usage` for token
        counts. Without `--json`, codex interleaves telemetry banners
        (workdir/model/session id), tool-call traces, and the assistant
        message in plain text -- requires fragile post-hoc cleanup. JSONL is
        machine-stable.
      * `-c approval_policy="never"` -- defensive belt-and-suspenders so the
        agent never tries to escalate to interactive approval (which would
        hang the headless subprocess).

    Stdin: codex `exec` accepts stdin when prompt is `-` or absent. Passing
    via stdin avoids Windows arg-quoting issues for long swarm briefs (5-8
    KB). Verified 2026-05-03 on 0.128.0.

    Session resume: codex has `exec resume` but the session id is not surfaced
    in the JSONL event stream's first event reliably across versions; we
    capture `thread_id` from `thread.started` events as the session id for
    forward compatibility. Native `--resume` wiring is left for a follow-up
    PR; right now the worker passes through `args.resume` unchanged so a
    caller that knows the codex session id can re-launch.
    """
    base = _resolve_cli("codex")
    cmd = base + [
        "exec",
        "--skip-git-repo-check",
        "--sandbox", "read-only",
        "--json",
        "-c", 'approval_policy="never"',
    ]
    if args.model:
        cmd += ["-m", args.model]
    if args.resume:
        # `codex exec resume <id>` is a subcommand-of-subcommand; we splice it
        # in instead of as a flag.
        cmd = base + ["exec", "resume", args.resume,
                      "--skip-git-repo-check",
                      "--sandbox", "read-only",
                      "--json",
                      "-c", 'approval_policy="never"']
        if args.model:
            cmd += ["-m", args.model]
    # Pass prompt via stdin. codex reads from stdin when no positional PROMPT
    # arg is present. Avoids 32K Windows command-line ceiling for long briefs.
    rc, out, err = _run(cmd, stdin_data=prompt, timeout=900)
    if rc != 0:
        sys.stderr.write(f"[codex rc={rc}] {err[-500:]}\n")
    sid = ""
    text_parts: list[str] = []
    tokens_in = 0
    tokens_out = 0
    model_fp = ""
    # JSONL parser: each line is a discrete event.
    #   {"type":"thread.started","thread_id":"<uuid>"}
    #   {"type":"turn.started"}
    #   {"type":"item.completed","item":{"id":"...","type":"agent_message","text":"..."}}
    #   {"type":"item.completed","item":{"type":"command_execution",...}}  # ignore
    #   {"type":"turn.completed","usage":{"input_tokens":N,"output_tokens":M,...}}
    for line in (out or "").splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(ev, dict):
            continue
        et = ev.get("type", "")
        if et == "thread.started":
            sid = ev.get("thread_id") or sid
        elif et == "item.completed":
            item = ev.get("item") or {}
            if isinstance(item, dict) and item.get("type") == "agent_message":
                t = item.get("text") or ""
                if isinstance(t, str) and t.strip():
                    text_parts.append(t)
        elif et == "turn.completed":
            usage = ev.get("usage") or {}
            if isinstance(usage, dict):
                tokens_in = int(usage.get("input_tokens") or 0)
                tokens_out = int(usage.get("output_tokens") or 0)
        elif et == "session.configured":
            # Some codex versions emit a session.configured event with the
            # model fingerprint; capture if present.
            model_fp = ev.get("model") or model_fp
    text = "\n".join(text_parts).strip()
    if not text:
        # JSON parse failed or no agent_message events -- return raw stdout
        # so the caller can still inspect it. Schema fallback in main()
        # captures non-JSON output gracefully.
        text = out
    meta = _cli_meta(rc)
    if model_fp:
        meta["model_fingerprint"] = model_fp
    if tokens_in:
        meta["tokens_in"] = tokens_in
    if tokens_out:
        meta["tokens_out"] = tokens_out
    return text, sid, meta


def call_pty_engine(engine: str, prompt: str, args: argparse.Namespace) -> tuple[str, str, dict]:
    """Drive freebuff (or other TUI-only engines) via pty_driver.py.

    Auto-selects mode: prompts >800 bytes use --mode fileref (writes the
    prompt to a temp file and instructs the TUI to Read it); otherwise
    --mode single. The TUI input buffer empirically clamps at ~512-1024
    chars, so single-shot fails on long briefs.
    """
    pty_script = REPO / "tools" / "swarm" / "pty_driver.py"
    prompt_bytes = len(prompt.encode("utf-8", errors="replace"))
    mode = "fileref" if prompt_bytes > 800 else "single"
    cmd = [sys.executable, str(pty_script), "--cli", engine, "--mode", mode,
           "-", "--hard-timeout", "300", "--idle-secs", "15"]
    rc, out, err = _run(cmd, stdin_data=prompt, timeout=420)
    if rc != 0:
        sys.stderr.write(f"[{engine} pty mode={mode} rc={rc}] {err[-500:]}\n")
    return out, "", _cli_meta(rc)


def call_api_consultant(engine: str, prompt: str, args: argparse.Namespace) -> tuple[str, str, dict]:
    """Drive tools/swarm/api_consult.py with stdin prompt + isolated env.

    Returns ``(output, sid, meta)``. The ``meta`` dict carries imp-B audit
    fields (model_fingerprint, tokens_in, tokens_out, transport_status,
    retry_count) read from a sidecar file written by ``api_consult.py``
    via the ``--meta-file`` flag.

    Implements a retry loop:
      - retries = `args.retries` (default 1; 0 disables).
      - retry on (rc != 0) OR (output bytes < 200).
      - linear 2s backoff between attempts (0s before attempt 1, 2s before 2,
        4s before 3, ...).
      - intermediate retry attempts are logged to swarm_runs/_calls.jsonl
        via `log_call(retry_count=N, ...)`; the FINAL attempt is logged by
        the outer CallTimer in main().
      - timeout (subprocess.TimeoutExpired) is NOT retried — re-raised so
        the outer handler in main() flags it as rc=4. Schema-validation
        failures happen downstream and are not retried here either.

    Per-engine sampling/retries from a YAML config (if `args.config_yaml`
    is set) override the CLI defaults via `_engine_overrides.load(...)`.
    """
    if not API_CONSULT.exists():
        raise FileNotFoundError(f"missing {API_CONSULT}")

    # Per-engine YAML override merge (yaml < CLI flag, since CLI is explicit).
    overrides = _engine_overrides.load(getattr(args, "config_yaml", None), engine)
    yaml_retries = overrides.get("retries")
    yaml_sampling = overrides.get("sampling") or {}

    # Effective retries: CLI wins if explicitly set, else yaml, else default 1.
    cli_retries = getattr(args, "retries", None)
    effective_retries = cli_retries if cli_retries is not None else (
        yaml_retries if yaml_retries is not None else 1
    )

    # Per-call sidecar meta-file. api_consult writes a JSON dict with imp-B
    # audit fields; we read it back into the in-process dict the caller
    # passes to CallTimer.set_meta().
    meta_path = SWARM_DIR / f"_meta_{os.getpid()}_{engine}.json"
    meta_path.parent.mkdir(parents=True, exist_ok=True)

    def _read_meta() -> dict:
        try:
            if meta_path.exists():
                d = json.loads(meta_path.read_text(encoding="utf-8"))
                return d if isinstance(d, dict) else {}
        except Exception:
            pass
        return {}

    # Build base command; only append sampling flags when a value is set.
    def _build_cmd() -> list[str]:
        cmd = [sys.executable, str(API_CONSULT), "--provider", engine,
               "--meta-file", str(meta_path), "-"]
        if args.model:
            cmd += ["--model", args.model]
        # Sampling precedence: CLI flag > YAML > unset (api_consult applies its
        # own defaults). Don't add unset flags so default behavior is unchanged.
        temp = getattr(args, "temperature", None)
        if temp is None:
            temp = yaml_sampling.get("temperature")
        if temp is not None:
            cmd += ["--temperature", str(temp)]
        max_tok = getattr(args, "max_tokens", None)
        if max_tok is None:
            # Accept either alias from the YAML.
            max_tok = (yaml_sampling.get("max_tokens")
                       or yaml_sampling.get("max_completion_tokens")
                       or yaml_sampling.get("num_predict"))
        if max_tok is not None:
            cmd += ["--max-tokens", str(max_tok)]
        top_p = getattr(args, "top_p", None)
        if top_p is None:
            top_p = yaml_sampling.get("top_p")
        if top_p is not None:
            cmd += ["--top-p", str(top_p)]
        return cmd

    cmd = _build_cmd()
    env = isolated_env(engine)
    # Force UTF-8 for the api_consult.py child's stdin/stdout/stderr. On
    # Windows, default sys.stdin.encoding is cp1252 with
    # errors='surrogateescape' -- any UTF-8 multi-byte sequence (PR diffs
    # routinely contain typographic punctuation, accented chars, table-
    # drawing) gets read as lone surrogate halves (U+DC80-U+DCFF).
    # json.dumps(ensure_ascii=True) then emits them as \uDCXX, which
    # deepseek/xai reject with HTTP 400 "lone leading surrogate in hex
    # escape". Forcing UTF-8 on the child process eliminates the class.
    # Verified against PR #739 (5.7 KB rendered prompt with table-drawing
    # chars) post-fix: 200 OK on both providers.
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")

    last_rc, last_out, last_err = 0, "", ""
    last_meta: dict = {}
    total_attempts = max(1, effective_retries + 1)
    prompt_bytes = len(prompt.encode("utf-8", errors="replace"))
    for attempt in range(total_attempts):
        if attempt > 0:
            # Linear backoff: 2s before attempt 1 (i.e. retry #1), 4s before #2.
            time.sleep(2 * attempt)
        # Clear stale sidecar so we never inherit a previous attempt's meta.
        try:
            if meta_path.exists():
                meta_path.unlink()
        except Exception:
            pass
        attempt_t0 = time.time()
        try:
            rc, out, err = _run(cmd, stdin_data=prompt, timeout=600, env=env)
        except subprocess.TimeoutExpired:
            # Don't retry timeouts — re-raise so the outer handler in main()
            # records rc=4 via CallTimer.set_rc(4).
            raise
        last_rc, last_out, last_err = rc, out, err
        last_meta = _read_meta()
        out_bytes = len(out.encode("utf-8", errors="replace"))
        success = (rc == 0 and out_bytes >= 200)

        # Log every NON-final attempt to _calls.jsonl with retry metadata.
        # The final attempt is logged by the outer CallTimer in main(), so we
        # explicitly skip it here to avoid double-counting.
        is_final = (attempt == total_attempts - 1) or success
        if not is_final:
            try:
                log_call(
                    engine=engine, prompt_bytes=prompt_bytes,
                    output_bytes=out_bytes,
                    latency_s=time.time() - attempt_t0,
                    returncode=rc,
                    error=(err or "")[-300:] if rc != 0 else "",
                    run_dir="", out_file="",
                    model=args.model or "", pr=args.pr,
                    retry_count=attempt,
                    model_fingerprint=last_meta.get("model_fingerprint", ""),
                    tokens_in=last_meta.get("tokens_in", 0),
                    tokens_out=last_meta.get("tokens_out", 0),
                    transport_status=last_meta.get("transport_status", "")
                    or (f"rc={rc}" if rc != 0 else "ok"),
                    extra={"retry_attempt": True, "retry_total": total_attempts},
                )
            except Exception:
                pass

        if rc != 0:
            sys.stderr.write(f"[{engine} attempt={attempt+1}/{total_attempts} rc={rc}] {err[-500:]}\n")
        if success:
            # Tag retry_count = number of failed prior attempts for outer
            # CallTimer.
            last_meta["retry_count"] = attempt
            try:
                meta_path.unlink()
            except Exception:
                pass
            return out, "", last_meta
        # Continue to next attempt unless we've exhausted retries.

    # All attempts exhausted — return the last attempt's output (caller's
    # downstream JSON-extract / fallback envelope handles bad output).
    last_meta = last_meta or {}
    last_meta.setdefault("transport_status",
                         f"rc={last_rc}" if last_rc != 0 else "low_signal")
    last_meta["retry_count"] = total_attempts - 1
    try:
        meta_path.unlink()
    except Exception:
        pass
    return last_out, "", last_meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", required=True)
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--out-file", required=True)
    ap.add_argument("--pr", type=int, default=None)
    ap.add_argument("--session-id")
    ap.add_argument("--resume")
    ap.add_argument("--context-md")
    ap.add_argument("--model")
    ap.add_argument("--json-strict", action="store_true",
                    help="prepend a JSON-only framing to prompts for engines that ignore in-prompt contracts (gemini)")
    ap.add_argument("--from-session",
                    help="resume from a swarm_runs/_sessions.db session id. "
                         "Auto-routes to claude --resume (native), API replay, "
                         "or MD-context fallback based on the session's engine.")
    ap.add_argument("--persist-session", action="store_true",
                    help="record this turn in swarm_runs/_sessions.db. "
                         "Required for --from-session on follow-up calls.")
    # API engine retry + sampling overrides.
    ap.add_argument("--retries", type=int, default=None,
                    help="API-engine retry budget. Default 1 (one initial + "
                         "one retry on rc!=0 OR output<200B). 0 disables. "
                         "Linear 2s backoff. Skipped on timeout / schema-fail. "
                         "If unset, falls back to per-engine YAML `retries:`, "
                         "else 1.")
    ap.add_argument("--temperature", type=float, default=None,
                    help="Per-call sampling temperature override (API engines).")
    ap.add_argument("--max-tokens", type=int, default=None,
                    help="Per-call max-tokens override (API engines). "
                         "Auto-mapped to max_completion_tokens (cerebras) / "
                         "num_predict (ollama_cloud).")
    ap.add_argument("--top-p", type=float, default=None,
                    help="Per-call top_p override (API engines).")
    ap.add_argument("--config-yaml", default=None,
                    help="Optional path to the swarm YAML config; per-engine "
                         "`sampling:` and `retries:` are read for this engine "
                         "and applied unless overridden by explicit CLI flags.")
    ap.add_argument("--persona", default=None,
                    help="path or persona name from tools/swarm/agent_personas/. "
                         "When set, the persona body (frontmatter stripped) is "
                         "prepended to the task prompt as a system-style preamble. "
                         "Resolution: <name>.md > <name>_specialist.md > path.")
    args = ap.parse_args()

    # Apply --from-session BEFORE _read_prompt so resume context becomes part
    # of the rendered prompt (for fallback path) or claude-CLI args (native).
    resumed_session_id: str | None = None
    if args.from_session:
        sess = get_session(args.from_session)
        if not sess:
            print(f"--from-session: unknown session id {args.from_session!r}",
                  file=sys.stderr)
            return 6
        resumed_session_id = args.from_session
        sess_engine = sess.get("engine") or ""
        if args.engine == "claude" and sess.get("cli_session_id"):
            # Native claude resume — pass through.
            args.resume = args.resume or sess["cli_session_id"]
        elif args.engine in API_ENGINES:
            # JSONL replay: prepend conversation as a system+history preface.
            history = replay_messages(args.from_session)
            if history:
                preface_lines = [
                    "Prior conversation history (most recent last). "
                    "DO NOT re-do work already covered. Resume from here.",
                    "---",
                ]
                for m in history:
                    role = m["role"].upper()
                    preface_lines.append(f"[{role}]")
                    preface_lines.append(m["content"])
                    preface_lines.append("")
                preface_lines.append("---")
                preface_lines.append("New task follows.")
                preface = "\n".join(preface_lines) + "\n\n"
                # Inject by writing to a temp file we hand off via context_md.
                tmp_ctx = SWARM_DIR / f"_session_{args.from_session[:8]}_ctx.md"
                tmp_ctx.parent.mkdir(parents=True, exist_ok=True)
                tmp_ctx.write_text(preface, encoding="utf-8")
                args.context_md = str(tmp_ctx)
        else:
            # CLI engine without native resume — render compact MD context.
            md_ctx = render_md_context(args.from_session, max_chars=4000)
            if md_ctx.strip():
                tmp_ctx = SWARM_DIR / f"_session_{args.from_session[:8]}_ctx.md"
                tmp_ctx.parent.mkdir(parents=True, exist_ok=True)
                tmp_ctx.write_text(md_ctx, encoding="utf-8")
                args.context_md = str(tmp_ctx)
        if sess_engine and sess_engine != args.engine:
            sys.stderr.write(
                f"--from-session: cross-engine resume "
                f"({sess_engine!r} -> {args.engine!r}); using fallback path\n"
            )

    prompt = _read_prompt(args)
    out_path = Path(args.out_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    eng = args.engine
    raw, sid = "", ""
    call_meta: dict = {}
    with CallTimer(
        engine=eng, model=args.model or "", pr=args.pr,
        run_dir=str(out_path.parent), out_file=str(out_path),
        prompt_bytes=len(prompt.encode("utf-8", errors="replace")),
    ) as timer:
        try:
            if eng == "claude":
                raw, sid, call_meta = call_claude(prompt, args)
            elif eng == "gemini":
                raw, sid, call_meta = call_gemini(prompt, args)
            elif eng in ("opencode", "kilo"):
                raw, sid, call_meta = call_opencode_or_kilo(eng, prompt, args)
            elif eng == "copilot":
                raw, sid, call_meta = call_copilot(prompt, args)
            elif eng == "agent":
                raw, sid, call_meta = call_agent(prompt, args)
            elif eng == "kimi":
                raw, sid, call_meta = call_kimi(prompt, args)
            elif eng == "openclaude":
                raw, sid, call_meta = call_openclaude(prompt, args)
            elif eng == "codex":
                raw, sid, call_meta = call_codex(prompt, args)
            elif eng in PTY_ENGINES:
                raw, sid, call_meta = call_pty_engine(eng, prompt, args)
            elif eng in API_ENGINES:
                raw, sid, call_meta = call_api_consultant(eng, prompt, args)
            else:
                print(f"unknown engine: {eng}", file=sys.stderr)
                timer.set_rc(2)
                timer.set_error(f"unknown engine: {eng}")
                return 2
        except subprocess.TimeoutExpired:
            print(f"[{eng}] timeout", file=sys.stderr)
            timer.set_rc(4)
            timer.set_error("timeout")
            timer.set_transport_status("timeout")
            return 4
        except Exception as e:
            print(f"[{eng}] exception: {e}", file=sys.stderr)
            timer.set_rc(5)
            timer.set_error(str(e))
            timer.set_transport_status("error")
            return 5
        # Clean engine-specific wrappers (Copilot tool-call markup, etc.)
        raw = parse_engine_output(eng, raw)
        timer.set_output(raw or "")
        # Apply imp-B audit-trail fields onto the timer so log_call writes
        # them at top level of the JSONL row.
        timer.set_meta(call_meta)
        if not raw or len(raw.strip()) < 50:
            timer.set_error("output suspiciously short or empty")

    raw_path = out_path.with_suffix(out_path.suffix + ".raw.txt")
    raw_path.write_text(raw, encoding="utf-8")

    obj = _extract_json_object(raw)
    if obj is None:
        obj = {
            "pr": args.pr, "engine": eng,
            "verdict": "COMMENT_ONLY", "confidence": "LOW",
            "summary": "Worker did not return valid JSON. See raw output.",
            "strengths": [], "concerns": [],
            "commentary_text": raw[:2000] or "(empty)",
            "fabrication_risk": {"level": "HIGH", "notes": "non-JSON output, schema-invalid"},
            "_swarm_meta": {
                "raw_path": str(raw_path), "engine": eng, "ts": _now(),
                # imp-B audit fields — preserved on parse-fail too.
                "model_fingerprint": call_meta.get("model_fingerprint", ""),
                "tokens_in": call_meta.get("tokens_in", 0),
                "tokens_out": call_meta.get("tokens_out", 0),
                "transport_status": call_meta.get("transport_status", ""),
                "retry_count": call_meta.get("retry_count", 0),
            },
        }
    else:
        obj.setdefault("engine", eng)
        if args.pr is not None:
            obj.setdefault("pr", args.pr)
        obj["_swarm_meta"] = {
            "raw_path": str(raw_path), "engine": eng, "ts": _now(),
            "session_id": sid,
            # imp-B audit-trail fields surfaced into the envelope so
            # swarm_inspect.py can show tokens / model fingerprint without
            # having to cross-reference _calls.jsonl.
            "model_fingerprint": call_meta.get("model_fingerprint", ""),
            "tokens_in": call_meta.get("tokens_in", 0),
            "tokens_out": call_meta.get("tokens_out", 0),
            "transport_status": call_meta.get("transport_status", ""),
            "retry_count": call_meta.get("retry_count", 0),
        }

    out_path.write_text(json.dumps(obj, indent=2), encoding="utf-8")

    # Persist session if requested. New session created if no resume; otherwise
    # append turn to the resumed session.
    if args.persist_session or resumed_session_id:
        try:
            target_sid = resumed_session_id
            if not target_sid:
                target_sid = sm_new_session(
                    engine=eng, prompt=prompt, model=args.model or "",
                    cli_session_id=sid or "",
                    metadata={"out_file": str(out_path)},
                )
            record_message(target_sid, "user", prompt)
            # Prefer cleaned raw text; fall back to JSON envelope summary.
            assistant_body = raw.strip()
            if not assistant_body:
                assistant_body = (
                    obj.get("commentary_text")
                    or obj.get("summary")
                    or obj.get("answer")
                    or "(empty)"
                )
            record_message(
                target_sid, "assistant", assistant_body,
                output_bytes=len(assistant_body.encode("utf-8", errors="replace")),
            )
            update_session(target_sid, status="active",
                           cli_session_id=sid or None)
            obj.setdefault("_swarm_meta", {})["session_id_db"] = target_sid
            out_path.write_text(json.dumps(obj, indent=2), encoding="utf-8")
        except Exception as e:
            sys.stderr.write(f"[session persist] {type(e).__name__}: {e}\n")

    print(str(out_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
