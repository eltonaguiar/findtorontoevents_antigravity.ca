"""Shared forward-stats helpers for verified paper pilots."""
from __future__ import annotations

import json
from pathlib import Path

FORWARD_N_TARGET = 100
SHADOW_N_TARGET = 30


def closed_rows_from_log(log_path: Path, strategy_id: str | None = None) -> list[dict]:
    if not log_path.exists():
        return []
    closed: list[dict] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("event") != "CLOSE":
            continue
        if strategy_id and row.get("strategy") != strategy_id:
            continue
        closed.append(row)
    return closed


def pf_wr_mean(closed: list[dict]) -> tuple[float, float, int, float]:
    if not closed:
        return 0.0, 0.0, 0, 0.0
    pnls = [float(r.get("pnl_pct") or 0) for r in closed]
    wins = sum(1 for p in pnls if p > 0)
    gross_win = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p < 0))
    pf = (gross_win / gross_loss) if gross_loss > 0 else (999.0 if gross_win > 0 else 0.0)
    return pf, wins / len(closed), len(closed), sum(pnls) / len(closed)


def promotion_gates(n: int, pf: float, wr: float, oos_pf: float = 0.0) -> list[str]:
    gates: list[str] = []
    if n < FORWARD_N_TARGET:
        gates.append(f"n<{FORWARD_N_TARGET}")
    if pf < 1.5:
        gates.append("pf<1.5")
    if wr < 0.5:
        gates.append("wr<50%")
    if oos_pf > 0 and pf < 0.85 * oos_pf:
        gates.append("pf<0.85*oos")
    return gates


def shadow_gates(n: int, pf: float, wr: float) -> tuple[list[str], bool]:
    gates: list[str] = []
    if n < SHADOW_N_TARGET:
        gates.append(f"n<{SHADOW_N_TARGET}")
    ready = len(gates) == 0 and pf >= 1.2 and wr >= 0.4
    return gates, ready


def forward_block(
    *,
    log_path: Path,
    strategy_id: str,
    oos_pf: float,
    open_position: dict | None = None,
) -> dict:
    closed = closed_rows_from_log(log_path, strategy_id)
    pf, wr, n, mean_pnl = pf_wr_mean(closed)
    gates = promotion_gates(n, pf, wr, oos_pf)
    sh_gates, sh_ready = shadow_gates(n, pf, wr)
    return {
        "source": "paper_pilot_virtual",
        "strategy_id": strategy_id,
        "n_closed": n,
        "wr": round(wr, 4),
        "pf": round(pf, 4),
        "mean_pnl_pct": round(mean_pnl, 4),
        "promotion_ready": len(gates) == 0 and n >= FORWARD_N_TARGET,
        "shadow_checkpoint_ready": sh_ready,
        "gates": gates,
        "shadow_gates": sh_gates,
        "open_position": open_position,
    }