#!/usr/bin/env python3
"""
Fast-track seed additional strategies into paper_trading.

Purpose:
- Increase the active forward-testing pool quickly using real-data-verified
  strategies that are not currently in paper/live/graduated.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
AGENTS = ROOT / "incubator" / "agents"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from incubator.backtest_team.generate_baby_strats_dashboard import _verification_payload


def _load(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _score(meta: Dict[str, Any]) -> float:
    m = meta.get("backtest_metrics", {}) if isinstance(meta.get("backtest_metrics"), dict) else {}
    trades = float(m.get("total_trades") or 0.0)
    wr = float(m.get("win_rate") or 0.0)
    sharpe = float(m.get("sharpe") or 0.0)
    return trades * 0.5 + wr * 100.0 + sharpe * 10.0


def discover_candidates() -> List[Tuple[Path, Dict[str, Any], float]]:
    out: List[Tuple[Path, Dict[str, Any], float]] = []
    for py_file in sorted(AGENTS.rglob("*.py")):
        if "__pycache__" in str(py_file).replace("\\", "/"):
            continue
        meta_path = Path(str(py_file) + ".meta.json")
        if not meta_path.exists():
            continue
        meta = _load(meta_path)
        status = str(meta.get("status", "")).lower()
        if status in {"paper_trading", "graduated", "live"}:
            continue
        verification = _verification_payload(py_file, meta)
        if verification.get("real_data_verified") is not True:
            continue
        out.append((meta_path, meta, _score(meta)))
    out.sort(key=lambda x: x[2], reverse=True)
    return out


def promote(meta_path: Path, meta: Dict[str, Any]) -> None:
    now = datetime.now(timezone.utc)
    meta["status"] = "paper_trading"
    meta["paper_trading"] = {
        "started_at": now.isoformat(),
        "end_date": (now + timedelta(days=30)).isoformat(),
        "days_remaining": 30,
        "days_elapsed": 0,
        "trades_count": 0,
        "current_pnl": 0.0,
        "progress_pct": 0.0,
        "daily_pnl": [],
    }
    meta["forward_metrics"] = {
        "win_rate": None,
        "sharpe": None,
        "max_drawdown": None,
        "total_trades": 0,
    }
    meta["forward_daily_pnl"] = []
    meta["forward_live_picks"] = []
    meta["forward_live_pick_count"] = 0
    _save(meta_path, meta)


def main() -> int:
    p = argparse.ArgumentParser(description="Fast-track additional strategies into paper_trading.")
    p.add_argument("--count", type=int, default=40, help="How many strategies to promote.")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    candidates = discover_candidates()
    picks = candidates[: max(0, int(args.count))]
    print(f"[FASTTRACK] candidates={len(candidates)} selected={len(picks)} dry_run={bool(args.dry_run)}")

    for meta_path, meta, score in picks:
        strategy = meta.get("strategy_name") or meta_path.stem.replace(".py.meta", "")
        agent = meta.get("agent_id") or meta_path.parent.name
        print(f" - {agent}/{strategy} score={score:.2f}")
        if not args.dry_run:
            promote(meta_path, meta)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
