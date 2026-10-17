"""
litellm_message_log.py — per-message JSONL log for the LiteLLM proxy.

WHY
---
`free-mode` / `free-mode-large` / `paid-mode` are LiteLLM *model groups* (labels).
On a successful call the proxy previously recorded NOTHING about which real
upstream served it, so you could not answer "this message contained `xyzdragon`
— which provider replied?" after the fact.

This CustomLogger writes one JSON object per line for every success and failure,
including the *resolved* model + provider, so a message marker can be mapped
back to the provider that answered.

    grep xyzdragon /tmp/litellm_messages.jsonl
    python3 tools/litellm_message_log.py --grep xyzdragon

Registration (litellm_config.yaml):

    litellm_settings:
      callbacks:
        - tools.litellm_smart_cooldown.smart_cooldown
        - tools.litellm_message_log.message_log

Env knobs
---------
  LITELLM_MESSAGE_LOG            log path           (default /tmp/litellm_messages.jsonl)
  LITELLM_MESSAGE_LOG_CONTENT    1|0 log message text (default 1)
  LITELLM_MESSAGE_LOG_MAX_CHARS  truncate prompt/response to N chars (default 2000)
  LITELLM_MESSAGE_LOG_MAX_BYTES  rotate to .1 when file exceeds N bytes (default 52428800)

Privacy: with CONTENT=1 message text (prompt + response snippet) is written to
disk in plaintext. Set LITELLM_MESSAGE_LOG_CONTENT=0 to keep metadata only
(timestamp / group / real model / provider / tokens) with no message bodies.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
from pathlib import Path
from typing import Any

try:  # litellm is only needed when loaded as a proxy callback
    from litellm.integrations.custom_logger import CustomLogger  # type: ignore
except Exception:  # pragma: no cover - allows the CLI to run without litellm
    class CustomLogger:  # type: ignore
        pass


LOG_PATH = Path(os.environ.get("LITELLM_MESSAGE_LOG", "/tmp/litellm_messages.jsonl"))
LOG_CONTENT = os.environ.get("LITELLM_MESSAGE_LOG_CONTENT", "1") not in ("0", "false", "False", "")
MAX_CHARS = int(os.environ.get("LITELLM_MESSAGE_LOG_MAX_CHARS", "2000"))
MAX_BYTES = int(os.environ.get("LITELLM_MESSAGE_LOG_MAX_BYTES", str(50 * 1024 * 1024)))


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _truncate(value: Any, limit: int = MAX_CHARS) -> Any:
    """Best-effort stringification + truncation for log safety."""
    if value is None:
        return None
    if not isinstance(value, str):
        try:
            value = json.dumps(value, ensure_ascii=False, default=str)
        except Exception:
            value = str(value)
    if len(value) > limit:
        return value[:limit] + f"...[+{len(value) - limit} chars]"
    return value


def _extract_text(messages: Any) -> str | None:
    """Flatten OpenAI-style messages into a single searchable string."""
    if messages is None:
        return None
    if isinstance(messages, str):
        return messages
    if isinstance(messages, dict):
        messages = [messages]
    if not isinstance(messages, list):
        return _truncate(messages)

    parts: list[str] = []
    for m in messages:
        if not isinstance(m, dict):
            parts.append(str(m))
            continue
        role = m.get("role", "?")
        content = m.get("content")
        if isinstance(content, list):  # multimodal / parts
            content = " ".join(
                p.get("text", "") if isinstance(p, dict) else str(p) for p in content
            )
        parts.append(f"[{role}] {content}")
    return "\n".join(parts)


def _last_user(messages: Any) -> str | None:
    """Return the most recent user message — the marker lives here, not in the
    85 KB system prompt that precedes it."""
    if isinstance(messages, dict):
        messages = [messages]
    if not isinstance(messages, list):
        return None
    for m in reversed(messages):
        if isinstance(m, dict) and m.get("role") == "user":
            content = m.get("content")
            if isinstance(content, list):
                return " ".join(
                    p.get("text", "") if isinstance(p, dict) else str(p) for p in content
                )
            return content if isinstance(content, str) else str(content)
    return None


def _truncate_tail(value: Any, limit: int = MAX_CHARS) -> Any:
    """Keep the END of a long string (the newest turns) rather than the start.

    Head-truncation silently dropped the user's message on opencode requests,
    which ship ~85 KB of system prompt + history ahead of it.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    if len(value) > limit:
        return f"[...{len(value) - limit} chars omitted...]" + value[-limit:]
    return value


def _response_text(response_obj: Any, payload: Any) -> str | None:
    """Pull the assistant text out of a ModelResponse (or the payload dict)."""
    try:
        choices = getattr(response_obj, "choices", None)
        if choices:
            msg = getattr(choices[0], "message", None)
            content = getattr(msg, "content", None)
            if content:
                return content
    except Exception:
        pass
    if isinstance(payload, dict):
        resp = payload.get("response")
        if resp is not None:
            return _extract_text(resp) if isinstance(resp, (list, dict)) else resp
    return None


def _api_base(payload: dict, kwargs: dict) -> str | None:
    base = payload.get("api_base")
    if not base:
        lp = kwargs.get("litellm_params") or {}
        base = lp.get("api_base") or kwargs.get("api_base")
    return base


def _rotate_if_needed(path: Path) -> None:
    try:
        if path.exists() and path.stat().st_size > MAX_BYTES:
            backup = path.with_suffix(path.suffix + ".1")
            backup.unlink(missing_ok=True)
            path.rename(backup)
    except Exception:
        pass


def _append(record: dict) -> None:
    """Append one JSON line, rotating if the file is oversized. Never raises."""
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        _rotate_if_needed(LOG_PATH)
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass


# --------------------------------------------------------------------------
# core extraction (verified against litellm 1.86.0 StandardLoggingPayload)
# --------------------------------------------------------------------------
def build_record(kwargs: dict, response_obj: Any, start_time: Any, end_time: Any,
                 status: str) -> dict:
    payload = kwargs.get("standard_logging_object") or {}
    if not isinstance(payload, dict):
        payload = {}

    real_model = payload.get("model") or kwargs.get("model")
    group = payload.get("model_group") or kwargs.get("model")
    base = _api_base(payload, kwargs)

    duration_ms = None
    try:
        if start_time is not None and end_time is not None:
            duration_ms = round((end_time - start_time).total_seconds() * 1000, 1)
    except Exception:
        pass
    if duration_ms is None:
        rt = payload.get("response_time")
        if isinstance(rt, (int, float)):
            duration_ms = round(float(rt) * 1000, 1)

    record: dict[str, Any] = {
        "ts": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "status": status,
        "call_id": payload.get("litellm_call_id") or kwargs.get("litellm_call_id"),
        "trace_id": payload.get("trace_id"),
        "requested_group": group,
        "real_model": real_model,
        "model_id": payload.get("model_id"),
        "provider": payload.get("custom_llm_provider"),
        "api_base": base,
        "prompt_tokens": payload.get("prompt_tokens"),
        "completion_tokens": payload.get("completion_tokens"),
        "total_tokens": payload.get("total_tokens"),
        "response_cost": payload.get("response_cost"),
        "duration_ms": duration_ms,
        "stream": payload.get("stream"),
    }

    if LOG_CONTENT:
        messages = payload.get("messages") or kwargs.get("messages")
        full = _extract_text(messages) or ""
        record["prompt_chars"] = len(full)
        # Tail-truncate so the newest turn survives; expose last_user separately
        # so a test marker is always searchable regardless of prompt size.
        record["prompt"] = _truncate_tail(full)
        record["last_user"] = _truncate(_last_user(messages))
        if status == "success":
            record["response"] = _truncate(_response_text(response_obj, payload))
        else:
            record["error"] = _truncate(payload.get("error_str") or kwargs.get("exception"))
    else:
        # Metadata-only mode: keep a stable content hash for correlation.
        import hashlib
        raw = _extract_text(payload.get("messages") or kwargs.get("messages")) or ""
        record["prompt_sha256_8"] = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]

    return record


class _MessageLog(CustomLogger):
    """LiteLLM custom logger — one JSONL line per request outcome."""

    # -- async variants (used by the proxy) --
    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        try:
            _append(build_record(kwargs, response_obj, start_time, end_time, "success"))
        except Exception:
            pass

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        try:
            _append(build_record(kwargs, response_obj, start_time, end_time, "failure"))
        except Exception:
            pass

    # -- sync variants (used by direct litellm.completion calls) --
    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        try:
            _append(build_record(kwargs, response_obj, start_time, end_time, "success"))
        except Exception:
            pass

    def log_failure_event(self, kwargs, response_obj, start_time, end_time):
        try:
            _append(build_record(kwargs, response_obj, start_time, end_time, "failure"))
        except Exception:
            pass


message_log = _MessageLog()


# --------------------------------------------------------------------------
# CLI — map a message marker back to the provider that answered
# --------------------------------------------------------------------------
def _iter_records(path: Path):
    if not path.exists():
        return
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


HEADERS = ["time", "status", "group", "real_model", "api_base", "call"]


def _row(rec: dict) -> list[str]:
    ts = (rec.get("ts") or "")[11:19]
    return [
        ts,
        str(rec.get("status") or "?"),
        str(rec.get("requested_group") or "?"),
        str(rec.get("real_model") or "?"),
        rec.get("api_base") or "default",
        str(rec.get("call_id") or "")[:8],
    ]


def _print_table(records: list[dict]) -> None:
    rows = [_row(r) for r in records]
    widths = [len(h) for h in HEADERS]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    widths[4] = min(widths[4], 60)  # cap the api_base column
    fmt = "  ".join("{:<%d}" % w for w in widths)
    print(fmt.format(*HEADERS))
    for row in rows:
        print(fmt.format(*[c[:w] for c, w in zip(row, widths)]))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Query the LiteLLM per-message JSONL log.")
    ap.add_argument("--path", default=str(LOG_PATH), help="JSONL path")
    ap.add_argument("--grep", "-g", help="case-insensitive substring to find in prompt/response")
    ap.add_argument("--tail", "-n", type=int, default=20, help="show last N matches (0 = all)")
    ap.add_argument("--json", action="store_true", help="emit raw JSON lines instead of a table")
    args = ap.parse_args(argv)

    path = Path(args.path)
    needle = (args.grep or "").lower()

    matches: list[dict] = []
    for rec in _iter_records(path):
        if needle:
            haystack = " ".join(
                str(rec.get(k) or "")
                for k in ("prompt", "last_user", "response", "error", "real_model")
            ).lower()
            if needle not in haystack:
                continue
        matches.append(rec)

    if args.tail and args.tail > 0:
        matches = matches[-args.tail:]

    if not matches:
        hint = f" containing {args.grep!r}" if args.grep else ""
        print(f"(no log entries{hint}) in {path}", file=sys.stderr)
        return 1

    if args.json:
        for rec in matches:
            print(json.dumps(rec, ensure_ascii=False))
        return 0

    _print_table(matches)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
