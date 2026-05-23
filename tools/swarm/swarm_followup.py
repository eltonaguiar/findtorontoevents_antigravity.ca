#!/usr/bin/env python3
"""Multi-turn chain runner for the swarm (priming -> analysis -> critique -> final).

Distinct from `swarm_run.py`:
- `swarm_run.py`  = fan-out one prompt across N engines in PARALLEL.
- `swarm_followup.py` = one engine, sequence of N turns, each building on the
  prior turn's session via --from-session.

Each turn is a separate worker_runner.py subprocess. Turn 1 starts a fresh
session (worker auto-persists because we always pass --persist-session). Turns
2..N read the previous turn's `_swarm_meta.session_id_db` and pass it as
`--from-session` so the worker resumes (via claude native --resume, API JSONL
replay, or MD-context fallback, depending on the engine).

YAML shape:

    name: forex-deep-dive
    engine: deepseek                  # single engine for the whole chain
    model: deepseek-chat              # optional
    out_dir: swarm_runs/followup_${TS}
    pr: 669                           # optional, applied to every turn
    json_strict: false                # optional
    turns:
      - name: priming
        prompt_file: prompts/forex_priming.md
      - name: analysis
        prompt: |
          Now analyze the FOREX class against the data you just summarised.
          Focus on the kill rule from your prior turn.
      - name: critique
        prompt: |
          Critique your own analysis. What's the weakest claim?
      - name: final
        prompt: |
          Final JSON answer per the original contract.
        capture_to: final.json

CLI:

    python tools/swarm/swarm_followup.py --config tools/swarm/examples/forex_deep_dive.yaml

Outputs (under <out_dir>):
    turn_1_<name>.json + turn_1_<name>.json.raw.txt
    turn_2_<name>.json + ...
    _chain_summary.json     (engine, turns[], session_id, ok_count)
    <capture_to>            (optional alias copies)

Constraints:
- A turn must specify exactly one of `prompt:` (inline) or `prompt_file:` (path).
  Both or neither => SystemExit.
- Inline prompts get written to <out_dir>/_turn_<N>_<name>_prompt.md so the
  worker (which reads --prompt-file) can consume them.
- ${VAR} / ${VAR:-default} / ${TS} substitution from `config_loader.load_config`.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WORKER = REPO / "tools" / "swarm" / "worker_runner.py"

ALL_ENGINES = (
    "claude", "gemini", "opencode", "kilo", "copilot", "agent", "kimi",
    "openclaude",
    # freebuff (PTY engine) removed 2026-05-04.
    "deepseek", "cerebras", "xai", "inception", "ollama_cloud", "ollama_local", "openrouter",
    "nous", "groq", "huggingface", "gemini_api", "github_models", "pollinations",
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _load_yaml_config(path: Path, *, ts: str) -> dict:
    """Same env+TS interpolation as swarm_run._load_yaml_config."""
    os.environ["TS"] = ts
    try:
        from config_loader import load_config  # type: ignore
    except ImportError:
        # Fallback when running as a script (no `tools` package on sys.path).
        sys.path.insert(0, str(REPO))
        from config_loader import load_config  # type: ignore
    try:
        return load_config(path)
    except RuntimeError as e:
        raise SystemExit(
            f"[swarm-followup] cannot read YAML config {path}: {e}\n"
            f"             install pyyaml: pip install -r tools/swarm/requirements.txt"
        ) from e


def _resolve_turn_prompt(turn: dict, *, idx: int, name: str,
                         out_dir: Path) -> Path:
    """Return a Path to a prompt file for this turn.

    - If `prompt_file` is set, validate + return it (relative to repo root).
    - If `prompt:` (inline string) is set, write it to a sidecar under out_dir
      and return that path.
    - Both / neither => SystemExit.
    """
    has_file = bool(turn.get("prompt_file"))
    has_inline = "prompt" in turn and turn["prompt"] is not None
    if has_file and has_inline:
        raise SystemExit(
            f"[swarm-followup] turn {idx} ({name!r}): set EXACTLY ONE of "
            f"`prompt:` or `prompt_file:`, not both."
        )
    if not has_file and not has_inline:
        raise SystemExit(
            f"[swarm-followup] turn {idx} ({name!r}): missing both "
            f"`prompt:` and `prompt_file:`."
        )
    if has_file:
        pf = Path(turn["prompt_file"])
        if not pf.is_absolute():
            pf = REPO / pf
        if not pf.exists():
            raise SystemExit(
                f"[swarm-followup] turn {idx} ({name!r}): prompt_file "
                f"{pf} does not exist."
            )
        return pf
    # Inline prompt — write to a sidecar so worker can --prompt-file it.
    sidecar = out_dir / f"_turn_{idx}_{name}_prompt.md"
    sidecar.write_text(str(turn["prompt"]), encoding="utf-8")
    return sidecar


def _run_turn(*, engine: str, model: str | None, prompt_file: Path,
              out_file: Path, pr: int | None, json_strict: bool,
              from_session: str | None) -> dict:
    """Invoke worker_runner.py for one turn. Returns a result dict."""
    cmd = [sys.executable, str(WORKER),
           "--engine", engine,
           "--prompt-file", str(prompt_file),
           "--out-file", str(out_file),
           "--persist-session"]
    if model:
        cmd += ["--model", model]
    if pr is not None:
        cmd += ["--pr", str(pr)]
    if json_strict:
        cmd += ["--json-strict"]
    if from_session:
        cmd += ["--from-session", from_session]

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
    session_id_db = ""
    cli_session_id = ""
    if out_file.exists():
        try:
            out_size = out_file.stat().st_size
            obj = json.loads(out_file.read_text(encoding="utf-8",
                                                errors="replace"))
            meta = obj.get("_swarm_meta") or {}
            session_id_db = meta.get("session_id_db") or ""
            cli_session_id = meta.get("session_id") or ""
        except Exception:
            pass

    return {
        "rc": rc,
        "elapsed_s": elapsed,
        "out_file": str(out_file),
        "out_size": out_size,
        "stderr_tail": stderr_tail,
        "session_id_db": session_id_db,
        "cli_session_id": cli_session_id,
        "from_session": from_session or "",
    }


def _print_next_steps_footer(summary: dict, *, config_path: str = "") -> None:
    """Print a terse 'NEXT STEPS' reminder after the chain summary.

    Long-form details: tools/swarm/POST_RUN_OPTIONS.md.
    """
    out_dir = summary.get("out_dir", "<run_dir>")
    ok = summary.get("ok_count", 0)
    total = summary.get("total", 0)
    chain_sid = summary.get("chain_session_id") or ""
    engine = summary.get("engine") or "<engine>"
    cfg_hint = config_path or "<yaml>"
    print()
    print(f"[swarm-followup] complete. turns ok={ok}/{total} dir={out_dir}")
    if chain_sid:
        print(f"[swarm-followup] chain session id: {chain_sid}")
    print()
    print("NEXT STEPS (see tools/swarm/POST_RUN_OPTIONS.md for details):")
    print(f"  1. Inspect chain        python tools/swarm/swarm_inspect.py {out_dir}")
    if chain_sid:
        print(f"  2. Add another turn     python tools/swarm/worker_runner.py --engine {engine} --from-session {chain_sid} --prompt-file <next.md> --persist-session")
    else:
        print( "  2. Add another turn     python tools/swarm/worker_runner.py --engine <eng> --from-session <sid> --prompt-file <next.md> --persist-session")
    print(f"  3. Branch into red-team python tools/swarm/swarm_run.py --config {cfg_hint} --red-team")
    print( "  4. Cross-engine compare python tools/swarm/swarm_run.py --prompt-file <q.md> --preset consensus-3")
    print( "  5. Switch persona       set persona: in YAML, or --persona <name> on a fan-out")
    print( "  6. Resume specific dissent  swarm_run.py --from-session-by-engine eng=<sid>,...")
    print()
    print("Active sessions:  python tools/swarm/session_manager.py list")
    print("Stats / drift:    python tools/swarm/swarm_stats.py")


def main() -> int:
    # utf-8 stdout/stderr so help text + tracebacks don't crash on cp1252.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--config", type=Path, required=True,
                    help="YAML chain config (see module docstring).")
    args = ap.parse_args()

    if not args.config.exists():
        print(f"config not found: {args.config}", file=sys.stderr)
        return 2

    ts = _now()
    cfg = _load_yaml_config(args.config, ts=ts)

    engine = cfg.get("engine")
    if not engine:
        print(f"[swarm-followup] config missing required field `engine`",
              file=sys.stderr)
        return 2
    if engine not in ALL_ENGINES:
        print(f"[swarm-followup] unknown engine {engine!r}; "
              f"supported: {ALL_ENGINES}", file=sys.stderr)
        return 3

    turns_cfg = cfg.get("turns") or []
    if not turns_cfg:
        print(f"[swarm-followup] config has no `turns:`", file=sys.stderr)
        return 2

    out_dir = Path(cfg.get("out_dir") or
                   (REPO / "swarm_runs" / f"followup_{ts}"))
    out_dir.mkdir(parents=True, exist_ok=True)

    model = cfg.get("model") or None
    pr_number = cfg.get("pr")
    if pr_number is not None:
        pr_number = int(pr_number)
    fleet_json_strict = bool(cfg.get("json_strict", False))

    print(f"[swarm-followup] config: {args.config}")
    print(f"[swarm-followup] engine: {engine} model: {model or '(default)'}")
    print(f"[swarm-followup] out:    {out_dir}")
    print(f"[swarm-followup] turns:  {len(turns_cfg)}")

    chain_results: list[dict] = []
    prev_session_id: str | None = None
    chain_session_id: str | None = None  # the session id every turn shares

    for idx, turn in enumerate(turns_cfg, start=1):
        if not isinstance(turn, dict):
            print(f"[swarm-followup] turn {idx} is not a mapping: {turn!r}",
                  file=sys.stderr)
            return 4
        name = (turn.get("name") or f"turn{idx}").replace(" ", "_")
        per_strict = bool(turn.get("json_strict", fleet_json_strict))
        prompt_file = _resolve_turn_prompt(turn, idx=idx, name=name,
                                           out_dir=out_dir)
        out_file = out_dir / f"turn_{idx}_{name}.json"

        print(f"\n[swarm-followup] turn {idx}/{len(turns_cfg)}: {name}")
        if prev_session_id:
            print(f"  resuming from: {prev_session_id}")
        else:
            print(f"  fresh session")

        r = _run_turn(
            engine=engine, model=model, prompt_file=prompt_file,
            out_file=out_file, pr=pr_number, json_strict=per_strict,
            from_session=prev_session_id,
        )
        tag = "OK" if r["rc"] == 0 and r["out_size"] >= 200 else "FAIL"
        print(f"  [{tag:4}] rc={r['rc']:>3} {r['elapsed_s']:>6.1f}s "
              f"{r['out_size']:>7}B  -> {out_file.name}")
        if r["stderr_tail"] and r["rc"] != 0:
            print(f"        err: {r['stderr_tail'][:200]}")

        # capture_to: copy this turn's JSON to a stable filename.
        capture_to = turn.get("capture_to")
        captured_path = ""
        if capture_to and out_file.exists():
            cp_path = out_dir / str(capture_to)
            cp_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copyfile(out_file, cp_path)
                captured_path = str(cp_path)
                print(f"        captured: {cp_path}")
            except Exception as e:
                print(f"        capture_to FAILED ({type(e).__name__}: {e})",
                      file=sys.stderr)

        turn_meta = {
            "idx": idx,
            "name": name,
            "prompt_file": str(prompt_file),
            "out_file": r["out_file"],
            "rc": r["rc"],
            "elapsed_s": r["elapsed_s"],
            "out_size": r["out_size"],
            "session_id_db": r["session_id_db"],
            "cli_session_id": r["cli_session_id"],
            "from_session": r["from_session"],
            "stderr_tail": r["stderr_tail"],
            "captured_to": captured_path,
        }
        chain_results.append(turn_meta)

        # Hard stop: if a turn failed badly, don't keep chaining onto a
        # session that may not have been persisted.
        if not r["session_id_db"]:
            print(f"[swarm-followup] turn {idx} did not persist a session; "
                  f"cannot chain further. Stopping.", file=sys.stderr)
            break

        if chain_session_id is None:
            chain_session_id = r["session_id_db"]
        prev_session_id = r["session_id_db"]

    summary = {
        "ts_utc": ts,
        "config": str(args.config),
        "engine": engine,
        "model": model or "",
        "out_dir": str(out_dir),
        "pr": pr_number,
        "chain_session_id": chain_session_id or "",
        "turns": chain_results,
        "ok_count": sum(1 for t in chain_results
                        if t["rc"] == 0 and t["out_size"] >= 200),
        "total": len(chain_results),
    }
    (out_dir / "_chain_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n[swarm-followup] {summary['ok_count']}/{summary['total']} turns ok. "
          f"summary: {out_dir / '_chain_summary.json'}")

    # Surface follow-up options. See tools/swarm/POST_RUN_OPTIONS.md.
    try:
        _print_next_steps_footer(summary, config_path=str(args.config))
    except Exception as e:
        print(f"[swarm-followup] WARN: footer print failed: "
              f"{type(e).__name__}: {e}", file=sys.stderr)

    return 0 if summary["ok_count"] == summary["total"] and summary["total"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
