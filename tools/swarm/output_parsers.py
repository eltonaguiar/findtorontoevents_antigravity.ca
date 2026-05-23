"""Engine-specific output cleaners.

Each CLI agent wraps the model response with its own tool-call /
session metadata. This module strips that wrapper and returns the
pure model prose for the schema validator + downstream consumers.

Usage:
    from tools.swarm.output_parsers import parse_engine_output
    cleaned = parse_engine_output("copilot", raw)
"""
from __future__ import annotations

import re

# GitHub Copilot CLI markers.
# Tool-call header: line starts with "● " (action) or "✗ " (failed action).
# Tool-call body:   line starts with "  │ " (args) or "  └ " (result).
_COPILOT_TOOL_HEADER = re.compile(r"^[●✗]\s")
_COPILOT_TOOL_BODY = re.compile(r"^\s*[│└]\s")

# Claude Code JSON envelope markers (when --output-format=json):
# We extract the `result` field upstream; this is a fallback for
# stream-json or text mode outputs.
_CLAUDE_TOOL_USE = re.compile(r"^\s*<tool_use>.*?</tool_use>\s*$", re.DOTALL)


def parse_copilot(raw: str) -> str:
    """Strip Copilot tool-call markup, keep prose only."""
    out_lines: list[str] = []
    skip_body = False
    for line in raw.splitlines():
        # Header line — skip and arm body skip until non-body line.
        if _COPILOT_TOOL_HEADER.match(line):
            skip_body = True
            continue
        if skip_body:
            if _COPILOT_TOOL_BODY.match(line) or not line.strip():
                # Body or blank between body lines — keep skipping.
                continue
            skip_body = False  # First non-body line ends tool-call block.
        out_lines.append(line)
    text = "\n".join(out_lines).strip()
    # Collapse 3+ blank lines.
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def parse_claude_envelope(raw: str) -> str:
    """If raw is the Claude --output-format=json envelope, extract `.result`.

    Falls back to raw if not parseable.
    """
    import json
    try:
        env = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return raw
    if isinstance(env, dict):
        for k in ("result", "text", "content", "message"):
            v = env.get(k)
            if isinstance(v, str) and v.strip():
                return v
    return raw


def parse_agent_envelope(raw: str) -> str:
    """If raw is the cursor-agent --output-format=json envelope, extract `.result`.

    Envelope shape (verified 2026-05-03 on cursor-agent 2026.05.01-eea359f):
        {"type":"result","subtype":"success","is_error":false,
         "duration_ms":2334,"result":"<prose>","session_id":"<uuid>",
         "request_id":"<uuid>","usage":{...}}

    `worker_runner.call_agent` extracts `.result` upstream, so this is a
    belt-and-suspenders fallback for the case where a future cursor-agent
    version emits stream-json frames or the upstream extract is bypassed.
    Falls back to raw if not a parseable JSON envelope.
    """
    import json
    try:
        env = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return raw
    if isinstance(env, dict):
        for k in ("result", "text", "content", "message"):
            v = env.get(k)
            if isinstance(v, str) and v.strip():
                return v
    return raw


def parse_engine_output(engine: str, raw: str) -> str:
    """Dispatch to the right parser for the given engine name."""
    if not raw:
        return raw
    if engine == "copilot":
        return parse_copilot(raw)
    if engine == "claude":
        return parse_claude_envelope(raw)
    if engine == "agent":
        return parse_agent_envelope(raw)
    return raw


def main() -> int:
    """CLI: parse a saved raw file. Useful for re-cleaning post-hoc."""
    import sys
    if len(sys.argv) < 3:
        print("usage: output_parsers.py <engine> <raw-file>", file=sys.stderr)
        return 2
    from pathlib import Path
    raw = Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.stdout.write(parse_engine_output(sys.argv[1], raw))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
