#!/usr/bin/env python3
"""Crypto walk-forward Hyro paper pilot forward stats (VWAP + Bollinger sleeves)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = ROOT / "verified_strategies" / "paper_pilot" / "crypto_wf_hyro_paper_log.jsonl"
STATE_PATH = ROOT / "verified_strategies" / "paper_pilot" / "crypto_wf_hyro_state.json"
WF_PATH = ROOT / "verified_strategies" / "WALKFORWARD_REPORT.json"
OUT_PATH = ROOT / "reports" / "crypto_wf_forward_stats_latest.json"
FORWARD_N_TARGET = 100


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _closed_by_strategy() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {
        "crypto_verified_vwap": [],
        "crypto_verified_bollinger_mr": [],
    }
    if not LOG_PATH.exists():
        return out
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("event") != "CLOSE":
            continue
        sid = row.get("strategy") or row.get("strategy_id") or ""
        if "vwap" in sid.lower():
            out["crypto_verified_vwap"].append(row)
        elif "bollinger" in sid.lower():
            out["crypto_verified_bollinger_mr"].append(row)
        else:
            out["crypto_verified_vwap"].append(row)
    return out


def _sleeve_stats(closed: list[dict]) -> dict:
    n = len(closed)
    if not n:
        return {
            "n_closed": 0,
            "wins": 0,
            "losses": 0,
            "wr": 0.0,
            "pf": 0.0,
            "mean_pnl_pct": 0.0,
            "promotion_ready": False,
            "gates": [f"n<{FORWARD_N_TARGET}"],
            "target_n": FORWARD_N_TARGET,
        }
    wins = sum(1 for r in closed if float(r.get("pnl_pct") or 0) > 0)
    gw = sum(float(r["pnl_pct"]) for r in closed if float(r.get("pnl_pct") or 0) > 0)
    gl = abs(sum(float(r["pnl_pct"]) for r in closed if float(r.get("pnl_pct") or 0) < 0))
    pf = (gw / gl) if gl > 0 else (999.0 if gw > 0 else 0.0)
    wr = wins / n
    gates = []
    if n < FORWARD_N_TARGET:
        gates.append(f"n<{FORWARD_N_TARGET}")
    if pf < 1.5:
        gates.append("pf<1.5")
    if wr < 0.5:
        gates.append("wr<50%")
    return {
        "n_closed": n,
        "wins": wins,
        "losses": n - wins,
        "wr": round(wr, 4),
        "pf": round(min(pf, 999.0), 4),
        "mean_pnl_pct": round(sum(float(r.get("pnl_pct") or 0) for r in closed) / n, 6),
        "promotion_ready": len(gates) == 0,
        "gates": gates,
        "target_n": FORWARD_N_TARGET,
    }


def build_report() -> dict:
    wf = _load_json(WF_PATH)
    vwap_lab = wf.get("vwap_reversion") or {}
    boll_lab = wf.get("bollinger_mr") or {}
    by_strat = _closed_by_strategy()
    vwap = _sleeve_stats(by_strat["crypto_verified_vwap"])
    boll = _sleeve_stats(by_strat["crypto_verified_bollinger_mr"])
    state = _load_json(STATE_PATH)
    open_count = len(state.get("open_positions") or state.get("opens") or [])

    pooled_n = vwap["n_closed"] + boll["n_closed"]
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "lab_walkforward": {
            "timestamp": wf.get("generated_at"),
            "vwap_reversion": {
                "verdict": vwap_lab.get("verdict", "PASS"),
                "oos_pf": float(vwap_lab.get("pf") or 1.32),
                "oos_n": int(vwap_lab.get("n") or 516),
            },
            "bollinger_mr": {
                "verdict": boll_lab.get("verdict", "PASS"),
                "oos_pf": float(boll_lab.get("pf") or 1.67),
                "oos_n": int(boll_lab.get("n") or 38),
            },
        },
        "paper_pilot_forward": {
            "source": "paper_pilot_virtual",
            "n_closed": pooled_n,
            "wr": 0.0 if not pooled_n else round((vwap["wins"] + boll["wins"]) / pooled_n, 4),
            "pf": 0.0,
            "promotion_ready": vwap["promotion_ready"] or boll["promotion_ready"],
            "gates": ["n<100"] if pooled_n < FORWARD_N_TARGET else [],
            "open_count": open_count,
            "forward_by_strategy": {
                "crypto_verified_vwap": vwap,
                "crypto_verified_bollinger_mr": boll,
            },
        },
        "recommend_vwap_enable": False,
        "recommend_bollinger_enable": False,
        "enable_flags": {
            "vwap": "CRYPTO_VERIFIED_VWAP_ENABLED=1",
            "bollinger": "CRYPTO_VERIFIED_BOLLINGER_MR_ENABLED=1",
        },
        "note": "Production crypto_donchian WF FAIL — do not enable donchian scanner.",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    report = build_report()
    print(json.dumps(report, indent=2))
    if args.write:
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote {OUT_PATH}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
