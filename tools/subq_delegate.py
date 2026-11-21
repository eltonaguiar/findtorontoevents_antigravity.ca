#!/usr/bin/env python3
"""Fan a review or question out to SubQ models, one call per task, in parallel.

Built for delegating review work: hand it real file contents plus a prompt, it
writes one Markdown answer and one usage sidecar per task. Nothing is printed
that could leak a key, and prompt/response text never lands in the repo unless
you point --out inside it.

Auth: ``SUBQ_API_KEY`` from the environment, else the SUBQ block in
``~/dbpasses.txt`` via :func:`tools.subq_consult.resolve_key`. Required so this
works the same on CI and on the operator's box.

Model quirks (measured 2026-11-21, ``subq-savant-1.4``)
-------------------------------------------------------
* Endpoint is OpenAI-compatible: ``POST https://api.subq.ai/v1/chat/completions``.
  The decision endpoint used by ``tools/subq_consult.py`` (``/v1/systemone``) is a
  different API; this tool does not use it.
* ``temperature`` must be ``1`` or absent. Any other value is a 400.
* ``max_tokens`` must be generous. The model emits a real ``message.reasoning``
  stream *inside* the budget, so a tight cap (3000 was measured) is consumed
  entirely by reasoning and the call returns ``content: null`` with
  ``finish_reason: length``. Default here is 12000.
* The answer is ``choices[0].message.content``. When it is null the reasoning
  transcript is returned instead, so a truncated run still yields something
  reviewable — the sidecar records which one you got.
* Usage is reported under ``usage.completion_tokens_details.reasoning_tokens``.

Exit codes
----------
0  every task returned HTTP 200
1  at least one task failed (its error is written to ``<name>.md``)
2  no key, or bad arguments

Usage
-----
Single task::

    python3 tools/subq_delegate.py \
        --task "Find defects in this gate. Cite function and give patch text." \
        --files tools/qa_ledger.py tools/live_pnl_tracker.py \
        --out /tmp/review

Fan-out from a manifest (list of {name, prompt, files?, system?})::

    python3 tools/subq_delegate.py --manifest /tmp/review/tasks.json \
        --out /tmp/review --jobs 3

Reusable from Python::

    from tools.subq_delegate import ask
    text, meta = ask("gate", SYSTEM, "prompt", ["a.py", "b.py"])
"""
from __future__ import annotations

import argparse
import concurrent.futures as futures
import json
import pathlib
import sys
import time
from typing import Any, Sequence

import requests

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:  # direct-script invocation guard (AGENTS.md)
    sys.path.insert(0, str(REPO_ROOT))

from tools.subq_consult import resolve_key  # noqa: E402

CHAT_URL = "https://api.subq.ai/v1/chat/completions"
DEFAULT_MODEL = "subq-savant-1.4"
DEFAULT_MAX_TOKENS = 12000

DEFAULT_SYSTEM = (
    "You are a senior reviewer on a quant data pipeline. You get real file contents. "
    "Be concrete and skeptical: cite file+function, state severity, and give exact patch "
    "text. Do NOT invent APIs or assume behaviour you cannot see. If something is fine, "
    "say so in one line. No filler, no restating the prompt, no praise."
)


def _read(path: str) -> str:
    return pathlib.Path(path).read_text(encoding="utf-8", errors="replace")


def build_prompt(prompt: str, files: Sequence[str]) -> str:
    """Append each file verbatim after the prompt, fenced with its path."""
    parts = [prompt.strip()]
    for path in files:
        parts.append(f"\n\n===== FILE: {path} =====\n{_read(path)}")
    return "\n".join(parts)


def ask(
    name: str,
    system: str,
    prompt: str,
    files: Sequence[str] = (),
    *,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    out_dir: str | pathlib.Path | None = None,
    timeout: int = 900,
) -> tuple[str, dict[str, Any]]:
    """Run one delegation. Returns (answer_text, meta).

    Writes ``<out>/<name>.md`` and ``<out>/<name>.meta.json`` when *out_dir* is
    given. Raises RuntimeError on a missing key so callers fail loudly.
    """
    key = resolve_key()
    if not key:
        raise RuntimeError("no SubQ key: set SUBQ_API_KEY or add a SUBQ block to dbpasses.txt")

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": build_prompt(prompt, files)},
        ],
        "max_tokens": max_tokens,
    }
    started = time.time()
    resp = requests.post(
        CHAT_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=body,
        timeout=timeout,
    )
    elapsed = round(time.time() - started, 1)

    meta: dict[str, Any] = {
        "name": name,
        "model": model,
        "http_status": resp.status_code,
        "elapsed_s": elapsed,
        "files": list(files),
        "prompt_chars": len(body["messages"][1]["content"]),
    }

    if resp.status_code != 200:
        text = f"HTTP {resp.status_code}: {resp.text[:600]}"
        meta["ok"] = False
        _write(out_dir, name, text, meta)
        return text, meta

    payload = resp.json()
    choice = (payload.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    answer = message.get("content")
    used_reasoning = False
    if not answer:
        answer = message.get("reasoning") or ""
        used_reasoning = True

    usage = payload.get("usage") or {}
    meta.update(
        ok=bool(answer),
        finish_reason=choice.get("finish_reason"),
        answer_chars=len(answer),
        used_reasoning_fallback=used_reasoning,
        reasoning_chars=len(message.get("reasoning") or ""),
        usage=usage,
        reasoning_tokens=(usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
    )
    _write(out_dir, name, answer, meta)
    return answer, meta


def _write(out_dir: str | pathlib.Path | None, name: str, text: str, meta: dict) -> None:
    if not out_dir:
        return
    target = pathlib.Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    (target / f"{name}.md").write_text(text, encoding="utf-8")
    (target / f"{name}.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def _load_manifest(path: str) -> list[dict]:
    data = json.loads(_read(path))
    if not isinstance(data, list):
        raise ValueError("manifest must be a JSON list of {name, prompt, files?, system?}")
    for i, task in enumerate(data):
        if not isinstance(task, dict) or not task.get("name") or not task.get("prompt"):
            raise ValueError(f"manifest entry {i} needs 'name' and 'prompt'")
    return data


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--task", help="Prompt for a single delegation")
    ap.add_argument("--system", default=DEFAULT_SYSTEM, help="System prompt")
    ap.add_argument("--files", nargs="*", default=[], help="Files appended to the prompt")
    ap.add_argument("--manifest", help="JSON list of {name, prompt, files?, system?} tasks")
    ap.add_argument("--out", required=True, help="Directory for answers + meta")
    ap.add_argument("--jobs", type=int, default=3, help="Concurrent calls (default 3)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    ap.add_argument("--name", default="answer", help="Task name for single-task mode")
    args = ap.parse_args(argv)

    if args.manifest:
        tasks = _load_manifest(args.manifest)
    elif args.task:
        tasks = [{"name": args.name, "prompt": args.task, "files": args.files, "system": args.system}]
    else:
        ap.error("provide --task or --manifest")

    if not resolve_key():
        print("[error] no SubQ key (SUBQ_API_KEY or dbpasses.txt)", file=sys.stderr)
        return 2

    print(f"# delegating {len(tasks)} task(s) to {args.model} -> {args.out}", file=sys.stderr)

    results: list[tuple[str, str, dict]] = []

    def run(task: dict) -> tuple[str, str, dict]:
        text, meta = ask(
            task["name"],
            task.get("system") or DEFAULT_SYSTEM,
            task["prompt"],
            task.get("files") or [],
            model=args.model,
            max_tokens=args.max_tokens,
            out_dir=args.out,
        )
        print(
            f"  {task['name']}: HTTP {meta['http_status']} "
            f"{meta.get('answer_chars', 0)} chars in {meta['elapsed_s']}s "
            f"(reasoning_tokens={meta.get('reasoning_tokens')})",
            file=sys.stderr,
        )
        return task["name"], text, meta

    with futures.ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        for result in pool.map(run, tasks):
            results.append(result)

    failed = [name for name, _, meta in results if not meta.get("ok")]
    if failed:
        print(f"# FAILED: {', '.join(failed)}", file=sys.stderr)
        return 1
    print(f"# ok: {len(results)}/{len(tasks)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
