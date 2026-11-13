#!/usr/bin/env python3
"""
check_retired_providers.py — fail fast when a retired LLM provider is re-introduced.

Why this exists
---------------
The Inception Labs "Mercury" API sunsets 2026-12-28. On 2026-11-12 the provider was
removed from 36 config/code files (branch scrub/inception-mercury-2026-11-12). Deleting
references is not the same as keeping them deleted: the usual regression is an older
example, a .env template, or a stale key list being copied back into a config surface,
after which the proxy routes live traffic at an API that no longer answers.

What it scans
-------------
Only files that DEFINE providers: the LiteLLM routing table, the model roster, the
engine -> env map, the config template, the launcher, the key-health matrix, the v2
client table, the ruflo model maps, and CI workflow env blocks. Documentation,
chatlogs and swarm run artifacts are deliberately excluded — they use the word in
prose and would drown the signal.

Two deliberate precision choices, both learned the hard way on this repo:

  1. "mercury" is ambiguous here. It is the retired Inception model name AND the name
     of a live local trading package (`python -m mercury2`, xgboost/joblib models in
     .github/workflows/mercury2-*.yml). A bare "mercury" hit would flag that strategy
     forever, so it is only reported when the same line carries provider context
     (inception, api_key, provider, inceptionlabs). "inception" itself has no other
     meaning in this repo and is always reported.

  2. JSON files are scanned STRUCTURALLY, not line by line. `config/api_model_roster.json`
     lists provider slugs as dict keys but also carries an OpenRouter model catalogue,
     where "inception/mercury-2" is a model id served by a live aggregator, not a
     provider entry. Scanning text there would flag the catalogue; scanning dict keys
     and provider-valued fields flags the thing that actually matters.

A hit is therefore: a non-comment line in a scoped text file naming a retired provider,
or a provider-shaped key/field in a scoped JSON file. Comment lines are skipped because
the retirement notes themselves live in comments. A line carrying RETIRED-PROVIDER-OK
is skipped, for a rare intentional mention in a non-comment position.

Usage
-----
    python3 tools/check_retired_providers.py             report; exit 1 on hits
    python3 tools/check_retired_providers.py --quiet     exit code only
    python3 tools/check_retired_providers.py --json      machine readable
    python3 tools/check_retired_providers.py --list      print the scan surface

Exit codes: 0 clean, 1 retired provider found, 2 internal error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterator

REPO_ROOT = Path(__file__).resolve().parent.parent

# Provider -> retirement facts. Add an entry here when the next vendor sunsets.
RETIRED: dict[str, dict[str, Any]] = {
    "inception": {
        "tokens": ("inception",),                     # unambiguous in this repo
        "context_tokens": ("mercury",),               # ambiguous: "Mercury 2" is a local strategy
        "context_requires": ("inception", "api_key", "provider", "inceptionlabs"),
        "sunset": "2026-12-28",
        "replacement": "cerebras",
        "note": "Inception Labs API sunset; route to the cerebras group on :4000",
    },
}

# JSON keys whose value names a provider (as opposed to naming a model).
PROVIDER_FIELDS = ("slug", "provider", "provider_name", "key_env_hit")

# (path or glob relative to repo root, why this file matters)
SCOPED: list[tuple[str, str]] = [
    ("litellm_config.yaml",
     "LiteLLM routing table - a retired provider here means live traffic to a dead API"),
    ("config/api_model_roster.json",
     "curated roster consumed by the dashboards"),
    (".env.example",
     "the env template people copy into a real .env"),
    ("tools/swarm/ENGINE_KEY_ENVS.py",
     "engine -> key env map for the swarm"),
    ("tools/swarm/swarm.config.example.json",
     "swarm config template"),
    ("tools/start_litellm_proxy.sh",
     "launcher; injects provider env at start"),
    ("tools/verify_all_keys.py",
     "key-health matrix; pings every listed provider"),
    ("tools/swarm_v2/swarms/core/llm_client.py",
     "v2 client provider table"),
    (".ruflo/orchestrator.py",
     "ruflo model maps (FREE_MODELS / LOCAL_MODELS / role_map)"),
    (".github/workflows/*.yml",
     "CI env blocks and pipeline provider lists"),
    (".github/workflows/*.yaml",
     "CI env blocks and pipeline provider lists"),
]

COMMENT_PREFIXES = ("#", "//", "/*", "*", "--", "<!--")
ALLOW_MARKER = "RETIRED-PROVIDER-OK"


def _word(aliases: tuple[str, ...]) -> re.Pattern[str]:
    """Word-ish matcher: letters/digits differ, underscores do not.

    Underscores must not break a match, because the most common shape of a
    regression here is an env-var name (MERCURY_API_KEY, INCEPTION_API_KEY).
    Digits must, because `mercury2` is a live local package (`python -m mercury2`)
    and is not a provider reference.
    """
    alts = "|".join(re.escape(a) for a in aliases)
    return re.compile(rf"(?<![A-Za-z0-9])(?:{alts})(?![A-Za-z0-9])", re.IGNORECASE)


def compile_patterns() -> dict[str, dict[str, re.Pattern[str] | None]]:
    out: dict[str, dict[str, re.Pattern[str] | None]] = {}
    for name, meta in RETIRED.items():
        ctx = meta.get("context_requires") or ()
        out[name] = {
            "strict": _word(tuple(meta["tokens"])),
            "ambiguous": _word(tuple(meta["context_tokens"])) if meta.get("context_tokens") else None,
            "context": _word(tuple(ctx)) if ctx else None,
        }
    return out


FILE_EXTS = (".html", ".htm", ".py", ".md", ".json", ".yml", ".yaml",
             ".js", ".ts", ".sh", ".txt", ".css", ".csv", ".joblib")
_WORD_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-/")


def _is_filename_ref(line: str, start: int, end: int) -> bool:
    """True when the match is part of a file name, not a provider setting.

    `audit_dashboard/inception_paper_trading.html` is a deployed page whose file name
    predates the retirement; the page itself was scrubbed. Its name appearing in a
    deploy list is not a provider re-introduction, so it must not fail the guard.
    """
    i, j = start, end
    while i > 0 and line[i - 1] in _WORD_CHARS:
        i -= 1
    while j < len(line) and line[j] in _WORD_CHARS:
        j += 1
    return line[i:j].lower().endswith(FILE_EXTS)


def match_text(line: str, patterns: dict[str, dict[str, re.Pattern[str] | None]]) -> tuple[str, str, int] | None:
    """Return (provider, token, column) for the first retired reference on this line."""
    for provider, p in patterns.items():
        strict, ambiguous, context = p["strict"], p["ambiguous"], p["context"]
        for kind, pat in (("strict", strict), ("ambiguous", ambiguous)):
            if pat is None:
                continue
            if kind == "ambiguous" and (context is None or not (context.search(line)
                                                               or (strict is not None and strict.search(line)))):
                continue
            for m in pat.finditer(line):
                if _is_filename_ref(line, m.start(), m.end()):
                    continue
                return provider, m.group(0), m.start() + 1
    return None


def expand(spec: str) -> list[Path]:
    if any(ch in spec for ch in "*?["):
        return sorted(REPO_ROOT.glob(spec))
    p = REPO_ROOT / spec
    return [p] if p.is_file() else []


def scan_text(path: Path, patterns: dict[str, Any]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"[warn] cannot read {path}: {exc}", file=sys.stderr)
        return hits
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith(COMMENT_PREFIXES) or ALLOW_MARKER in line:
            continue
        found = match_text(line, patterns)
        if found:
            provider, token, col = found
            hits.append({"provider": provider, "file": str(path.relative_to(REPO_ROOT)),
                         "line": lineno, "column": col, "token": token, "text": stripped[:160]})
    return hits


def _walk_provider_names(node: Any) -> Iterator[str]:
    """Yield provider-shaped names: every dict key, plus provider-valued fields."""
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(key, str):
                yield key
            if isinstance(value, str) and key in PROVIDER_FIELDS:
                yield value
            yield from _walk_provider_names(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_provider_names(item)


def scan_json(path: Path, patterns: dict[str, Any]) -> list[dict[str, Any]]:
    """Structural scan: provider slugs/fields only, never model ids."""
    hits: list[dict[str, Any]] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[warn] cannot parse {path}: {exc}", file=sys.stderr)
        return hits
    raw_lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    seen: set[tuple[str, str]] = set()
    for name in _walk_provider_names(data):
        found = match_text(name, patterns)
        if not found:
            continue
        provider, token, _col = found
        if (provider, name) in seen:
            continue
        seen.add((provider, name))
        needle = f'"{name}"'
        line_no = next((i for i, l in enumerate(raw_lines, 1) if needle in l), 0)
        hits.append({"provider": provider, "file": str(path.relative_to(REPO_ROOT)),
                     "line": line_no, "column": 1, "token": token, "text": needle[:160]})
    return hits


def build_surface() -> list[tuple[Path, str]]:
    surface: list[tuple[Path, str]] = []
    for spec, why in SCOPED:
        for path in expand(spec):
            surface.append((path, why))
    return surface


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="check_retired_providers.py",
        description="Fail if a retired LLM provider is re-introduced into provider config.",
    )
    ap.add_argument("--json", action="store_true", help="emit a machine-readable report")
    ap.add_argument("--quiet", action="store_true", help="exit code only, no report")
    ap.add_argument("--list", action="store_true", help="print the scan surface and exit")
    args = ap.parse_args(argv)

    if not REPO_ROOT.is_dir():
        print(f"[error] repo root not found: {REPO_ROOT}", file=sys.stderr)
        return 2

    surface = build_surface()
    if not surface:
        print("[error] scan surface is empty - are you running from the repo?", file=sys.stderr)
        return 2

    if args.list:
        for path, why in surface:
            print(f"{path.relative_to(REPO_ROOT)}  <- {why}")
        return 0

    patterns = compile_patterns()
    hits: list[dict[str, Any]] = []
    for path, _why in surface:
        scanner = scan_json if path.suffix.lower() == ".json" else scan_text
        hits.extend(scanner(path, patterns))

    if args.json:
        print(json.dumps({
            "clean": not hits,
            "scanned_files": len(surface),
            "retired": {n: {k: v for k, v in m.items()
                            if k not in ("tokens", "context_tokens", "context_requires")}
                        for n, m in RETIRED.items()},
            "hits": hits,
        }, indent=2))
    elif not args.quiet:
        if hits:
            print(f"FAIL: {len(hits)} retired-provider reference(s) in {len(surface)} scoped file(s)")
            for h in hits:
                meta = RETIRED[h["provider"]]
                print(f"  {h['file']}:{h['line']}  '{h['token']}' "
                      f"(sunset {meta['sunset']} -> use {meta['replacement']})")
                print(f"      {h['text']}")
            print("\nFix: delete the entry, or add RETIRED-PROVIDER-OK on the line if intentional.")
        else:
            print(f"OK: no retired provider ({', '.join(sorted(RETIRED))}) "
                  f"in {len(surface)} scoped file(s)")

    return 1 if hits else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:  # e.g. `--list | head`
        try:
            sys.stdout.close()
        finally:
            sys.exit(0)
