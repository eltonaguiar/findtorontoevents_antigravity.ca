"""Capture PR artifacts server-side for inline embedding into worker prompts.

API engines (deepseek/xai/cerebras/inception/ollama_cloud) cannot run
shell commands. The PR-review prompt previously told them to run
`gh pr view` / `gh pr diff` -- they fabricated the output from the title.
Capture the artifacts here and embed in the prompt before fan-out so
every engine (CLI or API) sees the same diff text.

Used by tools/swarm/swarm_dispatch.ps1 prior to worker dispatch and by
the inline-diff prompt template tools/swarm/prompts/pr_review_inline.md
which references {{PR_CAPTURE}}.

CLI:
    python tools/swarm/_pr_capture.py 724 [--max-diff 60000]
        -> writes JSON capture to stdout.

Library:
    from _pr_capture import capture_pr, embed_into_prompt
    cap = capture_pr(724)
    body = embed_into_prompt(open("prompts/pr_review_inline.md").read(), cap)
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

# Item 5 (2026-05-03): the original implementation stripped ALL non-BMP
# characters (including emoji urgency markers like 🟢/🔴) to avoid a
# downstream cp1252 encoding crash in the API-engine subprocess pipe.
# That root cause is now fixed at the env layer:
# `worker_runner.call_api_consultant` injects `PYTHONIOENCODING=utf-8`
# and `PYTHONUTF8=1` into the child env, so the emoji-strip workaround
# is no longer needed and was misrepresenting PR severity (Kimi-flagged
# missed-#5, MEDIUM). The new sanitiser only drops chars that are still
# genuinely hostile to the prompt assembly pipeline:
#
#   - C0 control chars (U+0000-001F) except \t \n \r — would corrupt
#     the markdown/JSON wrapper on the way to the engine.
#   - Lone surrogates (U+D800-DFFF) — invalid UTF-8 by definition; can
#     only appear via paired-surrogate decode bugs.
#   - Anything outside U+10FFFF — unreachable in valid Unicode but
#     defensive against malformed input.
#
# All printable Unicode including emoji and astral-plane CJK passes
# through unchanged.
_HOSTILE_CTRL_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")
_LONE_SURROGATE_RE = re.compile(r"[\uD800-\uDFFF]")


def _ascii_safe(text: str) -> str:
    """Drop only characters that are genuinely hostile to the prompt
    assembly pipeline (C0 controls minus \\t \\n \\r, and lone surrogates).

    Misnomer: the function name dates back to when we replaced ALL
    non-BMP with '?' to dodge a cp1252 encoding crash. That crash is
    now fixed at the worker_runner env layer (PYTHONIOENCODING=utf-8 +
    PYTHONUTF8=1 on the API-engine subprocess), so emoji + astral-plane
    Unicode now round-trip cleanly through every engine. The function
    is kept under its old name because callers in `embed_into_prompt`
    + `capture_pr` reference it; renaming is a separate refactor.

    See: tools/swarm/worker_runner.py::call_api_consultant for the env
    fix that obsoleted the original strip-emoji workaround.
    """
    if not text:
        return text
    out = _HOSTILE_CTRL_RE.sub("", text)
    out = _LONE_SURROGATE_RE.sub("", out)
    return out


def capture_pr(pr: int, max_diff_chars: int = 60_000) -> dict:
    """Fetch PR metadata + unified diff via `gh` and return a dict.

    Returns:
        {
          "pr": <int>,
          "title": str,
          "body": str (truncated to 4000 chars),
          "author": str (login),
          "base": str (baseRefName),
          "head": str (headRefName),
          "files": [path, ...],
          "mergeable": str,
          "diff": str (truncated to max_diff_chars; truncation note appended),
          "checks": [{"name": str, "conclusion": str}, ...],
        }
    All fields default to "" / [] / "UNKNOWN" if `gh` fails so downstream
    embedding is robust to private/closed PRs.
    """
    view = subprocess.run(
        [
            "gh", "pr", "view", str(pr), "--json",
            "title,body,author,headRefName,baseRefName,files,statusCheckRollup,mergeable",
        ],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=60, shell=False,
    )
    meta: dict = {}
    if view.returncode == 0 and view.stdout.strip():
        try:
            meta = json.loads(view.stdout)
        except json.JSONDecodeError:
            meta = {}

    diff = subprocess.run(
        ["gh", "pr", "diff", str(pr)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=60, shell=False,
    )
    diff_text = ""
    if diff.returncode == 0:
        full = diff.stdout
        if len(full) > max_diff_chars:
            diff_text = full[:max_diff_chars]
            diff_text += (
                f"\n\n[diff truncated at {max_diff_chars} chars; "
                f"full diff was {len(full)} chars]"
            )
        else:
            diff_text = full

    return {
        "pr": pr,
        "title": _ascii_safe(meta.get("title", "") or ""),
        "body": _ascii_safe((meta.get("body", "") or "")[:4000]),
        "author": ((meta.get("author") or {}).get("login", "") or ""),
        "base": meta.get("baseRefName", "") or "",
        "head": meta.get("headRefName", "") or "",
        "files": [f.get("path", "") for f in (meta.get("files") or [])],
        "mergeable": meta.get("mergeable", "UNKNOWN") or "UNKNOWN",
        "diff": _ascii_safe(diff_text),
        "checks": [
            {
                "name": _ascii_safe(c.get("name") or c.get("context") or ""),
                "conclusion": c.get("conclusion") or c.get("state") or "",
            }
            for c in (meta.get("statusCheckRollup") or [])
        ],
    }


def embed_into_prompt(template: str, pr_capture: dict) -> str:
    """Substitute {{PR_NUMBER}} and {{PR_CAPTURE}} in `template`.

    The {{PR_CAPTURE}} block contains every artifact in markdown form so
    pure text-to-text engines have everything they need without shell
    access.
    """
    pr = pr_capture.get("pr", "")
    title = pr_capture.get("title", "")
    author = pr_capture.get("author", "")
    base = pr_capture.get("base", "")
    head = pr_capture.get("head", "")
    mergeable = pr_capture.get("mergeable", "UNKNOWN")
    body = pr_capture.get("body", "")
    files = pr_capture.get("files") or []
    checks = pr_capture.get("checks") or []
    diff = pr_capture.get("diff", "") or ""

    block_parts: list[str] = []
    block_parts.append("\n## Captured PR artifacts (DO NOT run gh commands; everything is below)\n")
    block_parts.append(f"**PR #{pr}** -- {title}")
    block_parts.append(f"Author: {author} | base/head: {base} <- {head}")
    block_parts.append(f"Mergeable: {mergeable}\n")
    if body:
        block_parts.append("### Body\n```\n" + body + "\n```\n")
    block_parts.append(f"### Changed files ({len(files)})")
    for f in files[:50]:
        block_parts.append(f"- {f}")
    if len(files) > 50:
        block_parts.append(f"- ... [{len(files) - 50} more files truncated]")
    block_parts.append("")
    if checks:
        block_parts.append("### Status checks")
        for c in checks:
            block_parts.append(f"- {c.get('name', '')}: {c.get('conclusion', '')}")
        block_parts.append("")
    block_parts.append("### Diff\n```diff\n" + diff + "\n```\n")
    block = "\n".join(block_parts)

    out = template.replace("{{PR_NUMBER}}", str(pr))
    out = out.replace("{{PR_CAPTURE}}", block)
    return out


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("pr", type=int)
    ap.add_argument("--max-diff", type=int, default=60_000)
    ap.add_argument("--out-file", default=None,
                    help="If set, write JSON capture to this path (UTF-8). "
                         "Otherwise print to stdout.")
    args = ap.parse_args()
    cap = capture_pr(args.pr, args.max_diff)
    payload = json.dumps(cap, indent=2, ensure_ascii=False)
    if args.out_file:
        Path(args.out_file).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_file).write_text(payload, encoding="utf-8")
    else:
        # On Windows console, default cp1252 can mangle UTF-8 from `gh`.
        try:
            sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:
            pass
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
