#!/usr/bin/env python3
"""One-shot swarm runner: fan a single prompt to N engines in parallel.

Lighter-weight alternative to swarm_dispatch.ps1 (which is PR-review specific
and PowerShell-only). Pure Python, cross-platform, no PR semantics.

Two invocation modes:

1. **Flag mode (legacy, still supported):**

       python tools/swarm/swarm_run.py \\
           --prompt-file path/to/prompt.md \\
           --engines deepseek,xai,kilo,gemini \\
           [--out-dir swarm_runs/<auto-ts>] \\
           [--max-parallel 4] [--json-strict] [--pr 123]

2. **YAML-config mode:**

       python tools/swarm/swarm_run.py --config tools/swarm/examples/asset_class_audit.yaml

   The YAML supports `${VAR}` / `${VAR:-default}` substitution (via
   `tools.swarm.config_loader.load_config`) plus a special `${TS}` token
   resolved to the current UTC stamp (`YYYYMMDDTHHMMSSZ`). Schema:

       name: <free-form label>
       prompt_file: <path>
       engines:
         - name: deepseek
           model: deepseek-chat        # optional → --model
           json_strict: true            # optional → --json-strict (per-engine)
         - name: xai
       max_parallel: 4
       out_dir: swarm_runs/run_${TS}
       pr: 669                          # optional
       json_strict: false               # optional fleet-wide default

Default --out-dir: swarm_runs/run_<UTC-timestamp>/
Per-engine output: <out-dir>/<engine>.json + <engine>.json.raw.txt
Run summary: <out-dir>/_summary.json (engines, ok-count, durations)
Stats: re-run python tools/swarm/swarm_stats.py to see ZOMBIE/LOW_OK_RATE flags.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WORKER = REPO / "tools" / "swarm" / "worker_runner.py"

ALL_ENGINES = (
    "claude", "gemini", "opencode", "kilo", "copilot", "agent", "kimi",
    "openclaude",
    # freebuff (PTY engine) removed 2026-05-04.
    "deepseek", "cerebras", "xai", "inception", "ollama_cloud", "ollama_local", "openrouter",
    "nous", "groq", "huggingface", "gemini_api", "github_models", "pollinations", "ofox",
)

# Named engine bundles. Selectable via --preset / YAML `preset:` and listed by
# --list-engines so users discover them without grepping. Curated by perf
# tier + cost; closes Subagent J's audit flag #1 ("expose presets").
ENGINE_PRESETS: dict[str, list[str]] = {
    "consensus-3":  ["deepseek", "xai", "kilo"],
    "fast-cheap":   ["cerebras", "deepseek"],
    "deep-strict":  ["claude", "kilo", "deepseek"],
    "all-paid-api": ["deepseek", "xai", "cerebras", "inception", "ollama_cloud", "groq", "huggingface"],
    "all-keyless-local": ["ollama_local"],
    "all-cli":      ["claude", "gemini", "kilo", "opencode", "copilot", "agent"],
    "all-free-api": ["groq", "gemini_api", "github_models", "pollinations", "ollama_local", "ofox"],
    # 2026-05-13 (Agent#3 finding): 10-persona swarm rounds were all Opus-4.7
    # underneath = fake diversity. Force non-Opus mix for genuine cross-vendor
    # consensus. xai=Grok-4 (xAI), deepseek=DeepSeek-V3, groq=Llama-3.3-70B (Meta),
    # cerebras=Llama-3.3-70B-instruct (Cerebras inference + Meta weights).
    "non-opus-4":   ["xai", "deepseek", "groq", "cerebras"],
}

# Approximate USD cost per 1K tokens by engine. Used for the pre-dispatch
# cost estimate gated by --cost-cap-usd. Numbers are public list prices
# snapshotted 2026-05; OAuth-bundled CLIs (gemini, kilo, opencode, copilot)
# are treated as $0 because they bill against existing subscriptions,
# not per-token API spend. Update this table in tandem with provider price
# changes — there is no auto-refresh.
COST_PER_1K_TOKENS: dict[str, dict[str, float]] = {
    "deepseek":     {"in": 0.00014, "out": 0.00028},  # V3 pricing
    "xai":          {"in": 0.005,   "out": 0.015},     # Grok 3
    "cerebras":     {"in": 0.0001,  "out": 0.0001},    # near-free tier
    "inception":    {"in": 0.001,   "out": 0.002},     # estimate
    "ollama_cloud": {"in": 0.0,     "out": 0.0},       # subscription
    "ollama_local": {"in": 0.0,     "out": 0.0},       # local daemon, no API key
    "groq":         {"in": 0.00059, "out": 0.00079},   # llama-3.3-70b
    "huggingface":  {"in": 0.0002,  "out": 0.0002},    # router estimate
    "gemini_api":   {"in": 0.0,     "out": 0.0},       # Google AI Studio free tier
    "github_models":{"in": 0.0,     "out": 0.0},       # free for GitHub users
    "pollinations": {"in": 0.0,     "out": 0.0},       # genuinely free, no key
    "claude":       {"in": 0.003,   "out": 0.015},     # Sonnet
    "gemini":       {"in": 0.0,     "out": 0.0},       # OAuth-bundled
    "kilo":         {"in": 0.0,     "out": 0.0},
    "opencode":     {"in": 0.0,     "out": 0.0},
    "copilot":      {"in": 0.0,     "out": 0.0},
    "agent":        {"in": 0.0,     "out": 0.0},  # Cursor subscription-bundled
    "kimi":         {"in": 0.0,     "out": 0.0},  # Moonshot OAuth-bundled
    # openclaude (@gitlawb/openclaude): cost depends on the provider it routes
    # to (--provider openai/gemini/deepseek/...). Conservative estimate uses
    # OpenAI gpt-4o-mini list price. Override per-run via --model openai|gemini
    # |deepseek|... (mapped to --provider) or set OPENCLAUDE_PROVIDER env.
    "openrouter":   {"in": 0.00015, "out": 0.0006},
    "openclaude":   {"in": 0.00015, "out": 0.0006},
    # Codex (OpenAI Codex CLI) — DISABLED 2026-05-05 per user request.
    # "codex":        {"in": 0.0,     "out": 0.0},
    # freebuff (PTY engine) — REMOVED 2026-05-04.
}

# Model-specific OpenRouter cost rates (per 1K tokens, USD).
# Source: https://openrouter.ai/docs#pricing — snapshot 2026-05.
# FIX 2026-05-05: used by _lookup_openrouter_cost() to give accurate estimates
# when the user has overridden OPENROUTER_MODEL to an expensive model.
# Previously, openrouter always used gpt-4o-mini rate regardless of model,
# causing 100x cost overruns (e.g. $0.01 estimate → $150 actual) when
# OPENROUTER_MODEL=anthropic/claude-opus-4.
OPENROUTER_MODEL_RATES: dict[str, dict[str, float]] = {
    # OpenAI models
    "openai/gpt-4o-mini":         {"in": 0.00015, "out": 0.0006},
    "openai/gpt-4o":              {"in": 0.0025,  "out": 0.01},
    "openai/gpt-4.5-preview":     {"in": 0.01,    "out": 0.03},
    # Anthropic models
    "anthropic/claude-opus-4":    {"in": 0.015,   "out": 0.075},
    "anthropic/claude-sonnet-4":  {"in": 0.003,   "out": 0.015},
    "anthropic/claude-3.5-sonnet":{"in": 0.003,   "out": 0.015},
    "anthropic/claude-3-opus":    {"in": 0.003,   "out": 0.015},
    "anthropic/claude-3-sonnet":  {"in": 0.003,   "out": 0.015},
    "anthropic/claude-3-haiku":   {"in": 0.00025, "out": 0.00125},
    # Google models
    "google/gemini-2.5-flash":    {"in": 0.000125, "out": 0.0005},
    "google/gemini-2.5-pro":      {"in": 0.00125,  "out": 0.005},
    "google/gemini-1.5-pro":      {"in": 0.00125,  "out": 0.005},
    # DeepSeek models
    "deepseek/deepseek-chat":     {"in": 0.00014, "out": 0.00028},
    "deepseek/deepseek-v3":       {"in": 0.00014, "out": 0.00028},
    "deepseek/deepseek-r1":       {"in": 0.00014, "out": 0.00028},
    # xAI models
    "xai/grok-3":                 {"in": 0.005,   "out": 0.015},
    "xai/grok-2":                 {"in": 0.002,   "out": 0.006},
    # Meta models
    "meta-llama/llama-3.3-70b":   {"in": 0.00088, "out": 0.00088},
    "meta-llama/llama-3.1-8b":    {"in": 0.00022, "out": 0.00022},
    # Mistral models
    "mistralai/mistral-7b-instruct":{"in": 0.00024, "out": 0.00024},
    "mistralai/mixtral-8x7b":     {"in": 0.00049, "out": 0.00049},
    # Per-plugin (free) models — exact-match fallback covers these:
    "tencent/hy3-preview:free":   {"in": 0.00015, "out": 0.0006},   # gpt-4o-mini equiv
    "nvidia/nemotron-3-nano-30b-a3b:free":  {"in": 0.0002, "out": 0.0002},
    "nvidia/nemotron-3-super-120b-a12b:free":{"in": 0.0008, "out": 0.0008},
    "minimax/minimax-m2.5:free":  {"in": 0.0002, "out": 0.0002},
    "google/gemini-2.5-flash":    {"in": 0.000125, "out": 0.0005},
}

# Safety multiplier applied to unknown openrouter models to prevent
# catastrophic underestimation. A model like claude-opus-4 is ~100x more
# expensive than gpt-4o-mini; we multiply the gpt-4o-mini rate by this
# factor so the cost cap can at least catch expensive model selections.
OPENROUTER_UNKNOWN_MULTIPLIER = 10.0

# Estimated assistant output tokens per engine. Used alongside prompt size to
# project per-run cost. 4000 mirrors api_consult.SAMPLING_DEFAULTS max_tokens.
ASSUMED_OUTPUT_TOKENS = 4000


def _get_openrouter_model() -> str:
    """Return the OpenRouter model from env (or default)."""
    return os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")


def _lookup_openrouter_cost(model_tag: str) -> dict[str, float]:
    """Return per-1K-token rates for an OpenRouter model.

    Resolution order:
      1. Exact match in OPENROUTER_MODEL_RATES
      2. Provider-prefix fallback (e.g. "anthropic/claude-opus-4" → "anthropic/*")
      3. OPENROUTER_UNKNOWN_MULTIPLIER × gpt-4o-mini rate (safe overestimate
         for completely unknown models — catches e.g. claude-opus-4 at 10x;
         this is the final fallback, no step 4)
    """
    # 1. Exact match
    if model_tag in OPENROUTER_MODEL_RATES:
        return OPENROUTER_MODEL_RATES[model_tag]
    # 2. Provider-prefix fallback (strip model name, match provider dir)
    provider_prefix = model_tag.split("/")[0] + "/"
    for known in OPENROUTER_MODEL_RATES:
        if known.startswith(provider_prefix):
            return OPENROUTER_MODEL_RATES[known]
    # 3. Unknown model — apply safety multiplier
    base = OPENROUTER_MODEL_RATES["openai/gpt-4o-mini"]
    return {
        "in":  base["in"] * OPENROUTER_UNKNOWN_MULTIPLIER,
        "out": base["out"] * OPENROUTER_UNKNOWN_MULTIPLIER,
    }


def estimate_cost_usd(engines: list[str], prompt_chars: int) -> tuple[float, list[dict]]:
    """Estimate the total swarm cost in USD given engine list + prompt size.

    Returns (total_usd, per_engine_breakdown). Token approximation: chars/4.
    Output tokens fixed at ASSUMED_OUTPUT_TOKENS per engine (worst case).

    FIX 2026-05-05: openrouter engine now uses _lookup_openrouter_cost() to
    give accurate estimates even when OPENROUTER_MODEL env is overridden to
    an expensive model (e.g. claude-opus-4). Previously, openrouter always
    used the gpt-4o-mini rate, causing 100x cost overruns when the actual
    model was expensive. Unknown openrouter models get a 10x safety margin.
    """
    in_tokens = prompt_chars / 4.0
    breakdown: list[dict] = []
    total = 0.0
    for eng in engines:
        if eng == "openrouter":
            rates = _lookup_openrouter_cost(_get_openrouter_model())
        else:
            rates = COST_PER_1K_TOKENS.get(eng, {"in": 0.0, "out": 0.0})
        cost = (in_tokens / 1000.0) * rates["in"] + (
            ASSUMED_OUTPUT_TOKENS / 1000.0) * rates["out"]
        total += cost
        breakdown.append({"engine": eng, "cost_usd": round(cost, 5)})
    return round(total, 4), breakdown


def run_hook(label: str, cmd: str, env_extra: dict[str, str]) -> int:
    """Run a pre/post hook command via shell. Advisory — non-zero -> warn only.

    `env_extra` is merged into os.environ for the child process (not parent).
    Hooks are intentionally shell=True so users can pass `cmd1 && cmd2`-style
    one-liners without quoting gymnastics. Caller responsibility: don't pass
    untrusted input via --pre-hook / --post-hook.
    """
    child_env = os.environ.copy()
    child_env.update({k: str(v) for k, v in env_extra.items()})
    print(f"[swarm-run] {label} hook: {cmd}")
    try:
        proc = subprocess.run(cmd, shell=True, env=child_env,
                              capture_output=True, text=True,
                              encoding="utf-8", errors="replace",
                              timeout=300)
    except subprocess.TimeoutExpired:
        print(f"[swarm-run] WARN: {label} hook timed out after 300s",
              file=sys.stderr)
        return -1
    except Exception as e:
        print(f"[swarm-run] WARN: {label} hook failed: {type(e).__name__}: {e}",
              file=sys.stderr)
        return -2
    if proc.stdout:
        sys.stdout.write(proc.stdout)
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        print(f"[swarm-run] WARN: {label} hook exited rc={proc.returncode} "
              f"(advisory; continuing)", file=sys.stderr)
    return proc.returncode


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def run_one(engine: str, prompt_file: Path, out_file: Path,
            *, pr: int | None, json_strict: bool, model: str | None,
            session_id: str | None = None,
            from_session: str | None = None,
            persist_session: bool = False,
            persona: str | None = None) -> dict:
    cmd = [sys.executable, str(WORKER),
           "--engine", engine,
           "--prompt-file", str(prompt_file),
           "--out-file", str(out_file)]
    if pr is not None:
        cmd += ["--pr", str(pr)]
    if json_strict:
        cmd += ["--json-strict"]
    if model:
        cmd += ["--model", model]
    if session_id:
        cmd += ["--session-id", session_id]
    if from_session:
        cmd += ["--from-session", from_session]
    if persist_session:
        cmd += ["--persist-session"]
    if persona:
        cmd += ["--persona", persona]
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              encoding="utf-8", errors="replace",
                              timeout=900, shell=False)
        rc = proc.returncode
        stderr_tail = (proc.stderr or "")[-300:].strip()
    except subprocess.TimeoutExpired:
        rc, stderr_tail = -1, "TIMEOUT after 900s"
    except Exception as e:
        rc, stderr_tail = -2, f"{type(e).__name__}: {e}"
    elapsed = round(time.time() - t0, 2)

    out_size = 0
    if out_file.exists():
        try:
            out_size = out_file.stat().st_size
        except Exception:
            pass

    return {
        "engine": engine,
        "rc": rc,
        "elapsed_s": elapsed,
        "out_file": str(out_file),
        "out_size": out_size,
        "stderr_tail": stderr_tail,
        "session_id": session_id or "",
        "from_session": from_session or "",
    }


def _load_yaml_config(path: Path, *, ts: str) -> dict:
    """Load a YAML config via config_loader; substitute ${TS} after env vars.

    `${TS}` is treated as an extra env var so it composes with the existing
    `${VAR:-default}` machinery without a second template pass.
    """
    # Inject TS into env so config_loader.interpolate() resolves it.
    os.environ.setdefault("TS", ts)
    os.environ["TS"] = ts  # always overwrite with the run's stamp
    try:
        from config_loader import load_config  # type: ignore
    except ImportError:
        # Fallback when running as a script (no `tools` package on sys.path).
        sys.path.insert(0, str(REPO))
        from tools.swarm.config_loader import load_config  # type: ignore
    try:
        return load_config(path)
    except RuntimeError as e:
        # pyyaml missing → actionable error and exit cleanly upstream.
        raise SystemExit(
            f"[swarm-run] cannot read YAML config {path}: {e}\n"
            f"            install pyyaml: pip install -r tools/swarm/requirements.txt"
        ) from e


def _parse_from_session_by_engine(spec: str | None) -> dict[str, str]:
    """Parse 'eng1=sid1,eng2=sid2' into {eng1: sid1, eng2: sid2}.

    Empty/None input returns {}. Whitespace tolerated. Bad pairs raise
    SystemExit so the user gets an actionable message instead of a silent
    no-resume.
    """
    if not spec:
        return {}
    out: dict[str, str] = {}
    for pair in spec.split(","):
        pair = pair.strip()
        if not pair:
            continue
        if "=" not in pair:
            raise SystemExit(
                f"--from-session-by-engine: bad pair {pair!r} "
                f"(expected ENGINE=SESSION_ID)"
            )
        eng, _, sid = pair.partition("=")
        eng = eng.strip()
        sid = sid.strip()
        if not eng or not sid:
            raise SystemExit(
                f"--from-session-by-engine: empty engine or sid in {pair!r}"
            )
        out[eng] = sid
    return out


def _engines_from_yaml(cfg: dict) -> list[dict]:
    """Normalize cfg['engines'] into [{name, model?, json_strict?}, ...]."""
    raw = cfg.get("engines") or []
    out: list[dict] = []
    for item in raw:
        if isinstance(item, str):
            out.append({"name": item})
        elif isinstance(item, dict):
            name = item.get("name") or item.get("engine")
            if not name:
                raise SystemExit(f"[swarm-run] engine entry missing 'name': {item}")
            entry: dict = {"name": name}
            if item.get("model"):
                entry["model"] = item["model"]
            if "json_strict" in item:
                entry["json_strict"] = bool(item["json_strict"])
            if item.get("from_session"):
                entry["from_session"] = str(item["from_session"])
            if item.get("persona"):
                entry["persona"] = str(item["persona"])
            out.append(entry)
        else:
            raise SystemExit(f"[swarm-run] bad engine entry type: {item!r}")
    return out


def _print_next_steps_footer(summary: dict, *, config_path: str = "") -> None:
    """Print a terse 'NEXT STEPS' reminder after the run summary.

    Reminds the operator of the standard follow-ups (inspect, red-team,
    resume, multi-turn, persona, preset switch) without forcing them to
    grep flags. Long-form details: tools/swarm/POST_RUN_OPTIONS.md.
    """
    out_dir = summary.get("out_dir", "<run_dir>")
    ok = summary.get("ok_count", 0)
    total = summary.get("total", 0)
    cost = summary.get("cost_estimate_usd", 0.0)
    cfg_hint = config_path or "<yaml>"
    print()
    print(f"[swarm-run] complete. ok={ok}/{total} cost~=${cost:.4f} dir={out_dir}")
    print()
    print("NEXT STEPS (see tools/swarm/POST_RUN_OPTIONS.md for details):")
    print(f"  1. Inspect output       python tools/swarm/swarm_inspect.py {out_dir}")
    print(f"  2. Re-run with red-team python tools/swarm/swarm_run.py --config {cfg_hint} --red-team")
    print( "  3. Resume a dissenter   python tools/swarm/worker_runner.py --engine <eng> --from-session <sid> ...")
    print( "  4. Multi-turn deep-dive python tools/swarm/swarm_followup.py --config tools/swarm/examples/<x>.yaml")
    print( "  5. Switch persona       --persona <name>  (see agent_personas/INDEX.md)")
    print( "  6. Stricter validation  --strictness strict  (default; see schema_validate.py)")
    print( "  7. Try different preset python tools/swarm/swarm_run.py --preset deep-strict ...")
    print()
    print("Active sessions:  python tools/swarm/session_manager.py list")
    print("Stats / drift:    python tools/swarm/swarm_stats.py")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", type=Path,
                    help="YAML config (alternative to --prompt-file/--engines)")
    ap.add_argument("--prompt-file", type=Path)
    ap.add_argument("--engines",
                    help="comma-separated engine names. Use 'all' for everything.")
    ap.add_argument("--preset",
                    choices=sorted(ENGINE_PRESETS.keys()),
                    help="named engine bundle (mutually exclusive with --engines)")
    ap.add_argument("--out-dir", type=Path)
    ap.add_argument("--max-parallel", type=int, default=4)
    ap.add_argument("--cost-cap-usd", type=float, default=1.0,
                    help="abort if estimated cost exceeds this (default $1.00)")
    ap.add_argument("--pre-hook",
                    help="shell command to run before any worker dispatches. "
                         "Receives env: SWARM_OUT_DIR. Advisory — non-zero rc warns.")
    ap.add_argument("--post-hook",
                    help="shell command to run after all workers + summary. "
                         "Receives env: SWARM_OUT_DIR, SWARM_OK_COUNT, SWARM_TOTAL.")
    ap.add_argument("--red-team", action="store_true",
                    help="auto-invoke claude-opus red-team after workers finish "
                         "(opt-in; opus is the priciest engine)")
    ap.add_argument("--pr", type=int, default=None,
                    help="PR number to substitute into {{PR_NUMBER}} in prompt")
    ap.add_argument("--json-strict", action="store_true",
                    help="add JSON-only framing for engines that ignore contracts (gemini)")
    ap.add_argument("--model", help="override model for all engines that accept --model")
    ap.add_argument("--persist-sessions", action="store_true",
                    help="record each engine run as a session in swarm_runs/_sessions.db")
    ap.add_argument("--from-session-by-engine",
                    help="resume specific engines from prior sessions. "
                         "Format: ENGINE=SID[,ENGINE=SID...]. Engines not in "
                         "the map start fresh. Resumed engines auto-set "
                         "--persist-session so the chain can continue.")
    ap.add_argument("--list-engines", action="store_true",
                    help="print supported engine names and exit")
    ap.add_argument("--persona", default=None,
                    help="default persona for all engines (per-engine YAML "
                         "`persona:` overrides). Name resolved by worker_runner: "
                         "<name>.md > <name>_specialist.md > path.")
    # Force utf-8 stdout/stderr so unicode in help text + tracebacks doesn't
    # crash on Windows cp1252.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    args = ap.parse_args()

    if args.list_engines:
        print("Engines:")
        for e in ALL_ENGINES:
            print(f"  {e}")
        print("\nPresets:")
        for name, members in ENGINE_PRESETS.items():
            print(f"  {name:<14} -> {','.join(members)}")
        return 0

    # --engines and --preset are mutually exclusive.
    if args.engines and args.preset:
        ap.error("--engines and --preset are mutually exclusive")

    ts = _now()

    # ---- mode resolution -----------------------------------------------------
    yaml_engines: list[dict] | None = None
    fleet_json_strict = bool(args.json_strict)
    fleet_model: str | None = args.model
    pr_number: int | None = args.pr
    out_dir: Path | None = args.out_dir
    prompt_file: Path | None = args.prompt_file
    max_parallel: int = args.max_parallel
    preset_name: str | None = args.preset
    cost_cap_usd: float = float(args.cost_cap_usd)
    pre_hook: str | None = args.pre_hook
    post_hook: str | None = args.post_hook
    red_team: bool = bool(args.red_team)
    fleet_persona: str | None = args.persona

    from_session_map = _parse_from_session_by_engine(args.from_session_by_engine)

    if args.config:
        if not args.config.exists():
            print(f"config not found: {args.config}", file=sys.stderr)
            return 2
        cfg = _load_yaml_config(args.config, ts=ts)
        # YAML preset: resolves to engines list when --engines/preset on CLI not set
        # AND the YAML doesn't list explicit engines either.
        yaml_preset = cfg.get("preset")
        if yaml_preset and cfg.get("engines"):
            print(f"[swarm-run] config has both 'preset' and 'engines'; "
                  f"using explicit engines list", file=sys.stderr)
        if not preset_name and yaml_preset and not cfg.get("engines"):
            preset_name = str(yaml_preset)
        yaml_engines = _engines_from_yaml(cfg)
        if not prompt_file:
            pf = cfg.get("prompt_file")
            if not pf:
                print(f"[swarm-run] config has no prompt_file and --prompt-file not given",
                      file=sys.stderr)
                return 2
            prompt_file = Path(pf)
        if not out_dir:
            od = cfg.get("out_dir")
            if od:
                out_dir = Path(od)
        if pr_number is None and cfg.get("pr") is not None:
            pr_number = int(cfg["pr"])
        if "json_strict" in cfg:
            fleet_json_strict = bool(cfg["json_strict"]) or fleet_json_strict
        if cfg.get("max_parallel"):
            # CLI flag wins only if user passed a non-default; else use YAML.
            if args.max_parallel == 4:  # argparse default
                max_parallel = int(cfg["max_parallel"])
        # CLI --model still overrides; otherwise leave to per-engine.
        if not fleet_model and cfg.get("model"):
            fleet_model = cfg["model"]
        # YAML knobs introduced for cost-cap / hooks / red-team (CLI wins).
        if cfg.get("cost_cap_usd") is not None and args.cost_cap_usd == 1.0:
            cost_cap_usd = float(cfg["cost_cap_usd"])
        if not pre_hook and cfg.get("pre_hook"):
            pre_hook = str(cfg["pre_hook"])
        if not post_hook and cfg.get("post_hook"):
            post_hook = str(cfg["post_hook"])
        if not red_team and cfg.get("red_team"):
            red_team = bool(cfg["red_team"])
        # Top-level YAML persona is the fleet default; per-engine YAML
        # `persona:` (handled in _engines_from_yaml) overrides per engine.
        # Precedence: per-engine YAML > top-level YAML > CLI flag.
        if cfg.get("persona"):
            fleet_persona = str(cfg["persona"])
    else:
        if not prompt_file or not (args.engines or preset_name):
            ap.error("--prompt-file plus --engines or --preset required "
                     "(or use --config / --list-engines)")

    if not prompt_file or not prompt_file.exists():
        print(f"prompt file not found: {prompt_file}", file=sys.stderr)
        return 2

    # ---- engine list -------------------------------------------------------
    # Precedence: explicit YAML engines > CLI --engines > CLI/YAML --preset.
    if yaml_engines:
        engines_meta = yaml_engines
        engines = [e["name"] for e in engines_meta]
    elif args.engines:
        if args.engines.lower() == "all":
            engines = list(ALL_ENGINES)
        else:
            engines = [e.strip() for e in args.engines.split(",") if e.strip()]
        engines_meta = [{"name": e} for e in engines]
    elif preset_name:
        if preset_name not in ENGINE_PRESETS:
            print(f"[swarm-run] unknown preset {preset_name!r}; available: "
                  f"{sorted(ENGINE_PRESETS.keys())}", file=sys.stderr)
            return 3
        engines = list(ENGINE_PRESETS[preset_name])
        engines_meta = [{"name": e} for e in engines]
        print(f"[swarm-run] preset '{preset_name}' -> {','.join(engines)}")
    else:
        ap.error("no engines resolved (need --engines, --preset, or YAML engines)")

    bad = [e for e in engines if e not in ALL_ENGINES]
    if bad:
        print(f"unknown engines: {bad}; supported: {ALL_ENGINES}", file=sys.stderr)
        return 3

    # ---- pre-flight API key check (skip engines guaranteed to fail) ---------
    # API engines need at least one key env var set. If none are present,
    # skip the engine with a clear warning instead of burning time on a
    # subprocess that will fail with "no key in env". Evidence:
    # swarm_runs/_calls.jsonl 2026-05-05 shows deepseek/cerebras/xai/nous
    # all failing with missing keys, wasting 2-10s per retry attempt.
    try:
        from config_loader import ENGINE_KEY_ENVS  # type: ignore
    except ImportError:
        sys.path.insert(0, str(REPO))
        from config_loader import ENGINE_KEY_ENVS  # type: ignore

    # api_engines: engines in ENGINE_KEY_ENVS that need a key to succeed.
    # Must exactly match keys present in config_loader.ENGINE_KEY_ENVS.
    # BUG FIX (2026-05-05): added missing kimi; removed github_models
    # (it's in api_engines but not in ENGINE_KEY_ENVS, so its .get() always
    # returned () and it always passed through — the opposite of intended).
    # Codex disabled 2026-05-05 per user request.
    api_engines = {
        "deepseek", "cerebras", "xai", "inception", "ollama_cloud",
        "openrouter", "nous", "groq", "huggingface", "kimi",
        "gemini_api", "github_models",
    }
    skipped = []
    kept_meta = []
    for em in engines_meta:
        eng = em["name"]
        if eng in api_engines:
            envs = ENGINE_KEY_ENVS.get(eng, ())
            if envs and not any(os.environ.get(k) for k in envs):
                skipped.append(eng)
                print(f"[swarm-run] SKIP {eng}: no API key in env (checked {envs})", file=sys.stderr)
                continue
        kept_meta.append(em)
    engines_meta = kept_meta
    engines = [e["name"] for e in engines_meta]
    if skipped:
        print(f"[swarm-run] skipped {len(skipped)} engine(s) due to missing keys: {skipped}")
    if not engines:
        print("[swarm-run] all engines skipped; nothing to run.", file=sys.stderr)
        return 5

    # Merge per-engine from_session from YAML into the CLI map. CLI wins on
    # conflict so users can override a config file from the command line.
    for em in engines_meta:
        yaml_fs = em.get("from_session")
        if yaml_fs and em["name"] not in from_session_map:
            from_session_map[em["name"]] = yaml_fs

    # Surface stale map entries that don't match any engine in the run.
    unmatched = [e for e in from_session_map if e not in engines]
    if unmatched:
        print(
            f"[swarm-run] warning: --from-session-by-engine entries for "
            f"{unmatched} have no matching engine in this run; ignored.",
            file=sys.stderr,
        )

    if not out_dir:
        out_dir = REPO / "swarm_runs" / f"run_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[swarm-run] out: {out_dir}")
    print(f"[swarm-run] engines: {','.join(engines)} (parallel={max_parallel})")
    if args.persist_sessions:
        print(f"[swarm-run] persist-sessions: ON (db: swarm_runs/_sessions.db)")

    # ---- cost estimate + cap -----------------------------------------------
    try:
        prompt_chars = prompt_file.stat().st_size  # rough chars approx
    except Exception:
        prompt_chars = 0
    est_total, est_breakdown = estimate_cost_usd(engines, prompt_chars)
    print(f"[swarm-run] estimated cost: ${est_total:.4f} "
          f"(cap ${cost_cap_usd:.2f}; prompt ~{prompt_chars}B)")
    if est_total > cost_cap_usd:
        print(
            f"[swarm-run] estimated cost ${est_total:.2f} exceeds cap "
            f"${cost_cap_usd:.2f}. Use --cost-cap-usd Z to raise the cap or "
            f"pick a cheaper preset.",
            file=sys.stderr,
        )
        # Per-engine breakdown helps the user pick what to drop.
        for row in est_breakdown:
            if row["cost_usd"] > 0:
                print(f"  {row['engine']:<13} ${row['cost_usd']:.4f}",
                      file=sys.stderr)
        return 4

    # ---- pre-hook ----------------------------------------------------------
    if pre_hook:
        run_hook("pre", pre_hook, {"SWARM_OUT_DIR": str(out_dir)})

    # ---- session pre-allocation -------------------------------------------
    prompt_text = ""
    sessions_by_engine: dict[str, str] = {}
    if args.persist_sessions:
        try:
            from tools.swarm import session_manager  # type: ignore
        except ImportError:
            sys.path.insert(0, str(REPO))
            from tools.swarm import session_manager  # type: ignore
        try:
            prompt_text = prompt_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            prompt_text = ""
        for em in engines_meta:
            # Skip pre-allocation for engines that are resuming a prior
            # session — the worker will append turns to that session via
            # --from-session, so creating a new one here would split the
            # message log across two records.
            if em["name"] in from_session_map:
                continue
            sid = session_manager.new_session(
                engine=em["name"],
                prompt=prompt_text,
                model=em.get("model") or fleet_model or "",
                metadata={
                    "config": str(args.config) if args.config else "",
                    "out_dir": str(out_dir),
                    "pr": pr_number,
                },
            )
            sessions_by_engine[em["name"]] = sid

    # ---- dispatch ----------------------------------------------------------
    results = []
    with ThreadPoolExecutor(max_workers=max_parallel) as ex:
        future_map = {}
        for em in engines_meta:
            eng = em["name"]
            per_model = em.get("model") or fleet_model
            per_strict = em.get("json_strict") if "json_strict" in em else fleet_json_strict
            per_from = from_session_map.get(eng)
            # Persona precedence: per-engine YAML > top-level YAML > CLI flag.
            # `fleet_persona` already collapses (top-level YAML > CLI flag)
            # in the YAML-load block above; per-engine entry trumps it here.
            per_persona = em.get("persona") or fleet_persona
            # Resumed engines auto-persist so the chain can continue. Otherwise
            # respect the fleet --persist-sessions flag for fresh runs.
            per_persist = bool(per_from)
            future_map[ex.submit(
                run_one, eng, prompt_file,
                out_dir / f"{eng}.json",
                pr=pr_number, json_strict=per_strict,
                model=per_model,
                session_id=sessions_by_engine.get(eng),
                from_session=per_from,
                persist_session=per_persist,
                persona=per_persona,
            )] = eng
        for fut in as_completed(future_map):
            r = fut.result()
            tag = "OK" if r["rc"] == 0 and r["out_size"] >= 200 else "FAIL"
            print(f"  [{tag:4}] {r['engine']:<13} rc={r['rc']:>3} "
                  f"{r['elapsed_s']:>6.1f}s  {r['out_size']:>7}B")
            if r["stderr_tail"] and r["rc"] != 0:
                print(f"           err: {r['stderr_tail'][:200]}")
            results.append(r)

    # ---- post-run session bookkeeping --------------------------------------
    if args.persist_sessions:
        try:
            from tools.swarm import session_manager  # type: ignore
        except ImportError:
            from tools.swarm import session_manager  # type: ignore
        for r in results:
            sid = r.get("session_id") or ""
            if not sid:
                continue
            cli_sid = ""
            try:
                if r["out_size"] and Path(r["out_file"]).exists():
                    obj = json.loads(Path(r["out_file"]).read_text(
                        encoding="utf-8", errors="replace"))
                    cli_sid = (obj.get("_swarm_meta") or {}).get("session_id") or ""
                    # Record assistant message body for later replay.
                    # Try common envelope keys (PR-review uses commentary_text;
                    # generic QA uses answer; some agents return content/text).
                    body = (
                        obj.get("commentary_text")
                        or obj.get("summary")
                        or obj.get("answer")
                        or obj.get("content")
                        or obj.get("text")
                        or ""
                    )
                    # If none of the structured keys present but the raw output
                    # looks substantive, try the .raw.txt sidecar.
                    if not body:
                        raw_path = Path(str(r["out_file"]) + ".raw.txt")
                        if raw_path.exists():
                            try:
                                body = raw_path.read_text(
                                    encoding="utf-8", errors="replace"
                                ).strip()[:4000]
                            except Exception:
                                pass
                    if body:
                        session_manager.record_message(
                            sid, "assistant", str(body),
                            output_bytes=r["out_size"],
                            latency_s=r["elapsed_s"],
                        )
            except Exception:
                pass
            session_manager.update_session(
                sid,
                status="done" if r["rc"] == 0 else "error",
                cli_session_id=cli_sid or None,
            )

    summary = {
        "ts_utc": ts,
        "out_dir": str(out_dir),
        "prompt_file": str(prompt_file),
        "prompt_bytes": prompt_file.stat().st_size,
        "engines": engines,
        "json_strict": fleet_json_strict,
        "config": str(args.config) if args.config else "",
        "persist_sessions": bool(args.persist_sessions),
        "from_session_by_engine": from_session_map,
        "results": results,
        "ok_count": sum(1 for r in results if r["rc"] == 0 and r["out_size"] >= 200),
        "total": len(results),
    }
    summary["cost_estimate_usd"] = est_total
    summary["cost_cap_usd"] = cost_cap_usd
    summary["preset"] = preset_name or ""
    summary["red_team"] = red_team
    (out_dir / "_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n[swarm-run] {summary['ok_count']}/{summary['total']} ok. "
          f"summary: {out_dir / '_summary.json'}")

    # ---- post-hook ---------------------------------------------------------
    if post_hook:
        run_hook("post", post_hook, {
            "SWARM_OUT_DIR": str(out_dir),
            "SWARM_OK_COUNT": str(summary["ok_count"]),
            "SWARM_TOTAL": str(summary["total"]),
        })

    # ---- red-team auto-invoke ---------------------------------------------
    # Concatenate engine outputs into a synthetic merge plan, then run
    # claude opus against prompts/redteam.md. Opt-in (-$$$). Closes Subagent
    # J's audit flag #1.
    if red_team:
        redteam_prompt = REPO / "tools" / "swarm" / "prompts" / "redteam.md"
        if not redteam_prompt.exists():
            print(f"[swarm-run] WARN: redteam prompt missing at {redteam_prompt}; "
                  f"skipping --red-team", file=sys.stderr)
        else:
            try:
                merged_payload: dict = {"pr": pr_number, "engines": []}
                for r in results:
                    out_p = Path(r["out_file"])
                    if out_p.exists() and r["out_size"] >= 50:
                        try:
                            obj = json.loads(out_p.read_text(
                                encoding="utf-8", errors="replace"))
                        except Exception:
                            obj = {"_parse_error": True}
                        merged_payload["engines"].append(
                            {"engine": r["engine"], "envelope": obj})
                merge_plan_path = out_dir / "_redteam_input.json"
                merge_plan_path.write_text(
                    json.dumps(merged_payload, indent=2), encoding="utf-8")

                redteam_concat = (
                    redteam_prompt.read_text(encoding="utf-8", errors="replace")
                    + "\n\n## final_merge_plan input\n\n```json\n"
                    + json.dumps(merged_payload, indent=2)
                    + "\n```\n"
                )
                rt_prompt_path = out_dir / "_redteam_prompt.md"
                rt_prompt_path.write_text(redteam_concat, encoding="utf-8")

                rt_out = out_dir / "redteam.json"
                print(f"[swarm-run] red-team: dispatching claude opus "
                      f"-> {rt_out}")
                rt_result = run_one(
                    "claude", rt_prompt_path, rt_out,
                    pr=pr_number, json_strict=True, model="opus",
                )
                tag = ("OK" if rt_result["rc"] == 0
                       and rt_result["out_size"] >= 200 else "FAIL")
                print(f"  [{tag:4}] redteam       rc={rt_result['rc']:>3} "
                      f"{rt_result['elapsed_s']:>6.1f}s "
                      f"{rt_result['out_size']:>7}B")
            except Exception as e:
                print(f"[swarm-run] WARN: red-team dispatch failed: "
                      f"{type(e).__name__}: {e}", file=sys.stderr)

    # ---- next-steps reminder ---------------------------------------------
    # Surface follow-up options (red-team, resume, multi-turn, persona, etc.)
    # so operators don't have to remember the flag list. Long-form details in
    # tools/swarm/POST_RUN_OPTIONS.md.
    try:
        _print_next_steps_footer(
            summary,
            config_path=str(args.config) if args.config else "",
        )
    except Exception as e:  # never let a footer crash mask the real summary
        print(f"[swarm-run] WARN: footer print failed: "
              f"{type(e).__name__}: {e}", file=sys.stderr)

    return 0 if summary["ok_count"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
