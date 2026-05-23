#!/usr/bin/env python3
"""
HC evaluator parity runner (Phase 3).

Pipes `audit_dashboard/data/dashboard_data.json::picks.recent_closed`
(full 3500 rows) into `node tools/hc_parity_test.js`, runs the Python port
from `tools.hc_gates_python` over the same picks, and diffs per-pick.

Writes `tools/data/hc_parity_baseline.json` with totals + first 10 divergences.
Exits 0 on zero divergence, 1 otherwise.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parent.parent
DASH = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
JS_CLI = REPO / "tools" / "hc_parity_test.js"
OUT = REPO / "tools" / "data" / "hc_parity_baseline.json"

sys.path.insert(0, str(REPO))
from tools.hc_gates_python import passes_high_conviction_pick  # noqa: E402


def _pick_id(pick: Dict[str, Any], idx: int) -> str:
    return str(
        pick.get("pick_id")
        or pick.get("id")
        or pick.get("uuid")
        or pick.get("signal_id")
        or f"{pick.get('symbol', 'SYM')}|{pick.get('strategy', 'STRAT')}|"
           f"{pick.get('timestamp') or pick.get('entry_time') or idx}|{idx}"
    )


def run_js(picks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    payload = json.dumps(picks).encode("utf-8")
    proc = subprocess.run(
        ["node", str(JS_CLI)],
        input=payload,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"node hc_parity_test.js exited {proc.returncode}: {proc.stderr.decode('utf-8', 'replace')}"
        )
    return json.loads(proc.stdout.decode("utf-8"))


def run_py(picks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    registry: Dict[str, str] = {}
    out: List[Dict[str, Any]] = []
    for idx, pick in enumerate(picks):
        pid = _pick_id(pick, idx)
        pass_ = passes_high_conviction_pick(pick, corr_registry=registry)
        hc_tier = None
        if pass_:
            t = str(pick.get("hf_conviction_tier") or "").upper()
            hc_tier = "grade-a" if t in ("S", "A") else ("grade-b" if t == "B" else "grade-a")
            sym = str(pick.get("symbol") or "").upper()
            direction = str(pick.get("direction") or pick.get("signal_type") or "LONG").upper()
            if sym:
                registry[sym] = direction
        out.append({"pick_id": pid, "hc_tier": hc_tier, "gates_failed": []})
    return out


def main() -> int:
    if not DASH.is_file():
        print(f"FATAL: {DASH} missing", file=sys.stderr)
        return 2
    data = json.loads(DASH.read_text(encoding="utf-8"))
    picks = (data.get("picks") or {}).get("recent_closed") or []
    if not picks:
        print("FATAL: no recent_closed picks", file=sys.stderr)
        return 2

    print(f"[hc-parity] evaluating {len(picks)} picks...")
    t0 = time.time()
    js_out = run_js(picks)
    t_js = time.time() - t0
    t1 = time.time()
    py_out = run_py(picks)
    t_py = time.time() - t1

    if len(js_out) != len(py_out):
        print(f"FATAL: length mismatch js={len(js_out)} py={len(py_out)}", file=sys.stderr)
        return 2

    divergences: List[Dict[str, Any]] = []
    for i, (j, p) in enumerate(zip(js_out, py_out)):
        j_pass = j.get("hc_tier") is not None
        p_pass = p.get("hc_tier") is not None
        if j_pass != p_pass:
            divergences.append({
                "index": i,
                "pick_id": j.get("pick_id"),
                "js_result": j,
                "py_result": p,
                "failing_gate": (j.get("gates_failed") or [None])[0],
            })

    report = {
        "total_picks": len(picks),
        "divergent_count": len(divergences),
        "runtime_js_sec": round(t_js, 2),
        "runtime_py_sec": round(t_py, 2),
        "sample_divergences": divergences[:10],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        f"[hc-parity] picks={len(picks)} divergent={len(divergences)} "
        f"js={t_js:.2f}s py={t_py:.2f}s -> {OUT}"
    )
    return 0 if not divergences else 1


if __name__ == "__main__":
    sys.exit(main())
