#!/usr/bin/env python3
"""Prompt-critique pre-step — single-engine review of a swarm prompt BEFORE fanout.

Per docs/SWARM_REVISED_METHODOLOGY_2026-05-13.md Pattern #2. Cheap pre-step
(~$0.001 single call vs ~$0.05 wasted on bad multi-engine fanout) that
critiques a swarm prompt for clarity, ambiguity, overlooked topics, and
variance-reduction scaffolding.

Usage:
  python tools/swarm/swarm_critique.py --prompt-file path/to/prompt.md
  python tools/swarm/swarm_critique.py --prompt-file p.md --engine xai
  python tools/swarm/swarm_critique.py --prompt-file p.md --auto-apply
    --out-improved p_improved.md

Engine recommendation: xai (Grok-4) — strongest at meta-reasoning per
reports/engine_meta_observations_20260513T015000Z.md (only engine to
flag swarm-reliability gaps across 4 sessions).

Output:
  reports/prompt_critique_<basename>_<utc>.md OR --out PATH
  (markdown structured with Summary verdict / Suggested rewrites /
   Overlooked topics / Ambiguities flagged / Estimated variance reduction)

Auto-apply:
  --auto-apply will write an improved version of the prompt to --out-improved
  by passing the critique back to the same engine. NOT recommended without
  human review first; experimental.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from tools.swarm.api_consult import (  # noqa: E402
    PROVIDERS,
    call_openai_compat,
)


CRITIQUE_TEMPLATE = """You are a senior prompt engineer reviewing a swarm prompt
that is about to be fanned out to 3-7 LLMs in parallel. Your job is to make
the prompt produce more consistent, less-variant, less-fabricated output.

The prompt below will be sent verbatim to each engine. Read it carefully + return:

# Prompt critique

## Summary verdict
One of: `NEEDS_REWRITE` | `OK_AS_IS` | `NEEDS_SCAFFOLDING`

(NEEDS_REWRITE = ambiguous to the point engines will give wildly different
answers; NEEDS_SCAFFOLDING = OK skeleton but missing output schema /
constraints / definitions; OK_AS_IS = ready to dispatch.)

## Suggested rewrites
Bullet list. For each, quote the original + propose the fix.

## Overlooked topics (consider adding)
Bullet list. Topics that the prompt creator probably did NOT think to
include but would meaningfully change the answer if surfaced.

## Ambiguities flagged
Bullet list. Words/phrases that different models will interpret differently.

## Estimated variance reduction
One of: `LOW (<10%)` | `MEDIUM (10-30%)` | `HIGH (>30%)` — how much variance
between engine responses would drop if your suggestions are applied?

## Best engine for THIS prompt
One of the swarm engines (xai / deepseek / groq / cerebras / kimi / opencode /
ollama_cloud / nous). Brief reason (1 line).

---

# The prompt to critique

{prompt_body}
"""


IMPROVE_TEMPLATE = """You previously critiqued a swarm prompt. Now apply your
own critique: rewrite the prompt to address every issue you flagged. Return
ONLY the improved prompt body, ready to copy-paste into a new file. Do NOT
include the critique itself or any commentary.

# Your prior critique

{critique_body}

---

# The original prompt

{prompt_body}

---

# Improved version (your output)
"""


def critique(prompt_text: str, engine: str = "xai",
             reasoning: str | None = None) -> tuple[str, dict]:
    body = CRITIQUE_TEMPLATE.format(prompt_body=prompt_text)
    sampling = None
    if reasoning:
        sampling = {"reasoning_effort": reasoning}
    return call_openai_compat(engine, body, model_override=None, sampling=sampling)


def improve(prompt_text: str, critique_text: str, engine: str = "xai") -> tuple[str, dict]:
    body = IMPROVE_TEMPLATE.format(
        critique_body=critique_text,
        prompt_body=prompt_text,
    )
    return call_openai_compat(engine, body, model_override=None, sampling=None)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prompt-file", required=True, type=Path)
    p.add_argument("--engine", default="xai",
                   choices=["xai", "deepseek", "groq", "cerebras", "kimi",
                            "opencode", "ollama_cloud", "ollama_local", "nous",
                            "openrouter"])
    p.add_argument("--out", type=Path, default=None,
                   help="Output critique md; default reports/prompt_critique_<base>_<utc>.md")
    p.add_argument("--reasoning", choices=["low", "medium", "high", "max"],
                   default=None, help="Inject reasoning_effort for engines that support it")
    p.add_argument("--auto-apply", action="store_true",
                   help="Apply critique back to engine to produce improved prompt")
    p.add_argument("--out-improved", type=Path, default=None,
                   help="Where to write the improved prompt (--auto-apply only)")
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args()

    if not args.prompt_file.exists():
        print(f"ERROR: prompt file {args.prompt_file} not found", file=sys.stderr)
        sys.exit(1)

    prompt_text = args.prompt_file.read_text(encoding="utf-8")
    if not args.quiet:
        print(f"# critiquing prompt ({len(prompt_text):,} chars) with engine={args.engine}",
              file=sys.stderr)
        if args.reasoning:
            print(f"# reasoning_effort={args.reasoning}", file=sys.stderr)

    try:
        critique_text, meta = critique(prompt_text, engine=args.engine,
                                        reasoning=args.reasoning)
    except Exception as exc:
        print(f"ERROR: critique call failed: {exc}", file=sys.stderr)
        sys.exit(2)

    if not args.out:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        base = args.prompt_file.stem
        args.out = ROOT / "reports" / f"prompt_critique_{base}_{ts}.md"

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(critique_text, encoding="utf-8")

    if not args.quiet:
        print(f"# critique -> {args.out} ({len(critique_text):,} chars)",
              file=sys.stderr)
        print(f"# tokens_in={meta.get('tokens_in')} tokens_out={meta.get('tokens_out')}",
              file=sys.stderr)
        # First 25 lines preview
        for line in critique_text.splitlines()[:25]:
            print(f"#   {line}", file=sys.stderr)

    if args.auto_apply:
        if not args.out_improved:
            args.out_improved = args.prompt_file.with_name(
                f"{args.prompt_file.stem}_improved{args.prompt_file.suffix}"
            )
        if not args.quiet:
            print(f"# applying critique -> improved prompt {args.out_improved}",
                  file=sys.stderr)
        try:
            improved_text, _ = improve(prompt_text, critique_text, engine=args.engine)
        except Exception as exc:
            print(f"ERROR: improve call failed: {exc}", file=sys.stderr)
            sys.exit(3)
        args.out_improved.write_text(improved_text, encoding="utf-8")
        if not args.quiet:
            print(f"# improved -> {args.out_improved} ({len(improved_text):,} chars)",
                  file=sys.stderr)


if __name__ == "__main__":
    main()
