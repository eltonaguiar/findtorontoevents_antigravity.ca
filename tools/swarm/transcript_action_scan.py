#!/usr/bin/env python3
"""Transcript action-item scanner — find missed TODOs buried in a long chat.

A long Claude Code session (this repo routinely produces 4-12 MB JSONL
transcripts) far exceeds any single LLM context window, so action items the
user asked for mid-session can be silently dropped. This tool:

  1. parses a session JSONL transcript into clean user/assistant text turns
     (tool-call / tool-result / system-reminder noise is discarded — that is
     ~90% of the bytes and none of the intent),
  2. splits the turns into char-budgeted chunks (sized for the smallest
     provider — LLM7 anon tier caps input ~8000 chars),
  3. asks an LLM, per chunk, to enumerate every action item + a DONE / OPEN /
     UNCLEAR status,
  4. aggregates + de-duplicates into one report.

Backend: tools/swarm_v2 LLMClient — auto-detects a keyed provider, falls back
to the keyless LLM7.io provider, so it runs with zero configuration.

Usage:
    python tools/swarm/transcript_action_scan.py <transcript.jsonl> \
        [--chunk-chars 6000] [--out report.md] [--provider deepseek]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "swarm_v2"))

try:
    from swarms.core.llm_client import LLMClient  # noqa: E402
except Exception as exc:  # noqa: BLE001
    print(f"ERROR: cannot import swarm LLMClient: {exc}", file=sys.stderr)
    raise SystemExit(2)


_SCAN_SYSTEM = (
    "You audit Claude Code session transcripts. You are terse and literal."
)
_SCAN_PROMPT = """Below is an excerpt of a Claude Code session transcript
(user turns prefixed `USER:`, assistant turns `ASSISTANT:`).

List EVERY distinct action item: anything the USER explicitly requested, plus
any TODO / next-step / follow-up the assistant surfaced. For each, one line:

  - [DONE|OPEN|UNCLEAR] short description

Mark DONE only if the excerpt itself shows it finished (PR merged, file
written, command verified). Mark OPEN if requested but not shown done. Mark
UNCLEAR if you cannot tell from this excerpt alone. Do not invent items. If
the excerpt contains no action items, output exactly: NONE

EXCERPT:
---
{chunk}
---
"""


def extract_turns(jsonl_path: Path) -> list[tuple[str, str]]:
    """Parse a session JSONL into [(role, text)] — user + assistant text only.

    tool_use / tool_result blocks and harness `system-reminder` text are
    dropped; they are the bulk of the bytes and carry no request intent.
    """
    turns: list[tuple[str, str]] = []
    for line in jsonl_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        # Claude Code JSONL uses "type"; Cursor agent transcripts use "role".
        role = ev.get("type") or ev.get("role")
        if role not in ("user", "assistant"):
            continue
        msg = ev.get("message") or {}
        content = msg.get("content")
        parts: list[str] = []
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for blk in content:
                if not isinstance(blk, dict):
                    continue
                # keep only assistant/user prose; drop tool_use + tool_result
                if blk.get("type") == "text" and blk.get("text"):
                    parts.append(blk["text"])
        text = "\n".join(parts).strip()
        if not text:
            continue
        # Drop harness-injected system-reminder blocks (not user intent).
        if text.startswith("<system-reminder>") and text.endswith("</system-reminder>"):
            continue
        turns.append((role, text))
    return turns


def chunk_turns(turns: list[tuple[str, str]], max_chars: int) -> list[str]:
    """Pack turns into char-budgeted excerpt strings."""
    chunks: list[str] = []
    buf: list[str] = []
    size = 0
    for role, text in turns:
        block = f"{role.upper()}: {text}"
        if size + len(block) > max_chars and buf:
            chunks.append("\n\n".join(buf))
            buf, size = [], 0
        buf.append(block)
        size += len(block)
    if buf:
        chunks.append("\n\n".join(buf))
    return chunks


def scan(jsonl_path: Path, chunk_chars: int, provider: str | None) -> dict:
    turns = extract_turns(jsonl_path)
    chunks = chunk_turns(turns, chunk_chars)
    client = LLMClient(provider=provider) if provider else LLMClient()
    if not client.available:
        raise SystemExit("ERROR: no LLM provider available (no key + no keyless fallback)")
    print(f"# transcript_action_scan: {len(turns)} turns -> {len(chunks)} chunks "
          f"via provider '{client.provider_name}'", file=sys.stderr)

    per_chunk: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        reply = client.complete(
            _SCAN_PROMPT.format(chunk=chunk[:chunk_chars]),
            system=_SCAN_SYSTEM,
            max_tokens=1200,
            temperature=0.1,
        )
        status = "ok" if reply else "FAILED"
        print(f"#   chunk {i}/{len(chunks)} [{status}]", file=sys.stderr)
        per_chunk.append(reply or "(chunk scan failed)")
    return {
        "transcript": str(jsonl_path),
        "turns": len(turns),
        "chunks": len(chunks),
        "provider": client.provider_name,
        "per_chunk": per_chunk,
    }


def _dedupe_items(per_chunk: list[str]) -> list[str]:
    """Collect `- [STATUS] ...` lines across chunks, dedupe by description."""
    seen: dict[str, str] = {}
    order: list[str] = []
    for block in per_chunk:
        for raw in block.splitlines():
            ln = raw.strip()
            if not ln.startswith("- "):
                continue
            key = "".join(c for c in ln.lower() if c.isalnum())[:80]
            if not key:
                continue
            if key in seen:
                # An item DONE in any (typically later) chunk is done — DONE
                # wins over a prior OPEN/UNCLEAR mention of the same item.
                if "[DONE]" in ln and "[DONE]" not in seen[key]:
                    seen[key] = ln
                continue
            seen[key] = ln
            order.append(key)
    return [seen[k] for k in order]


def render(result: dict) -> str:
    items = _dedupe_items(result["per_chunk"])
    out = [
        "# Transcript action-item scan",
        "",
        f"- transcript: `{result['transcript']}`",
        f"- turns: {result['turns']} · chunks: {result['chunks']} · "
        f"provider: {result['provider']}",
        f"- deduped action items: {len(items)}",
        "",
        "## Action items (deduped across chunks)",
        "",
    ]
    out += items or ["(none found)"]
    open_items = [x for x in items if "[OPEN]" in x]
    out += ["", f"## OPEN ({len(open_items)})", ""]
    out += open_items or ["(none)"]
    return "\n".join(out)


def main() -> int:
    # Windows consoles default to cp1252 — transcripts carry arrows/em-dashes.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("transcript", type=Path)
    ap.add_argument("--chunk-chars", type=int, default=6000)
    ap.add_argument("--provider", default=None)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    if not args.transcript.exists():
        print(f"ERROR: {args.transcript} not found", file=sys.stderr)
        return 1
    result = scan(args.transcript, args.chunk_chars, args.provider)
    report = render(result)
    if args.out:
        args.out.write_text(report, encoding="utf-8")
        print(f"# wrote {args.out}", file=sys.stderr)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
