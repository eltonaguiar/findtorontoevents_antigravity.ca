"""Historical hygiene pass for predictions.db.

Goals:
- Backfill lightweight metadata (`asset_class`) where missing.
- Repair obviously broken resolved rows when the correct exit is inferable.
- Flag irreparable rows with `is_invalid_execution=1` and `quality_flags`.

Default mode is dry-run. Use `--apply` to persist changes.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from db import get_db, backfill_predictors, export_leaderboard_json

REPORT_PATH = Path(__file__).parent / "data" / "hygiene_report.json"
LEADERBOARD_PATH = Path(__file__).parent / "data" / "leaderboard.json"


def _norm_symbol(value: str | None) -> str:
    return str(value or "").upper().replace("/", "").replace("-", "").strip()


def _infer_asset_class(symbol: str | None) -> str | None:
    sym = _norm_symbol(symbol)
    if not sym:
        return None
    if sym.endswith(("USDT", "USDC", "BUSD")):
        return "crypto"
    if sym in {"BTC", "ETH", "SOL"}:
        return "crypto"
    if sym in {"XAUUSD", "XAGUSD", "USOIL", "UKOIL"}:
        return "commodity"
    if len(sym) == 6 and sym.isalpha():
        return "forex"
    return None


def _calc_capped_pnl(direction: str | None, entry: float | None, exit_price: float | None) -> float | None:
    if not entry or not exit_price:
        return None
    if entry == 0:
        return None
    if str(direction or "").upper() == "LONG":
        pnl = ((exit_price - entry) / entry) * 100.0
    else:
        pnl = ((entry - exit_price) / entry) * 100.0
    return round(max(min(pnl, 500.0), -100.0), 4)


def _geometry_flags(direction: str | None, entry: float | None, tp: float | None, sl: float | None) -> list[str]:
    flags: list[str] = []
    side = str(direction or "").upper()
    if not entry:
        return flags
    if side == "LONG":
        if tp is not None and tp <= entry:
            flags.append("tp_wrong_side")
        if sl is not None and sl >= entry:
            flags.append("sl_wrong_side")
    elif side == "SHORT":
        if tp is not None and tp >= entry:
            flags.append("tp_wrong_side")
        if sl is not None and sl <= entry:
            flags.append("sl_wrong_side")
    return flags


def _repair_row(row: dict) -> tuple[dict, list[str], bool]:
    updates: dict = {}
    flags = _geometry_flags(
        row.get("direction"),
        row.get("entry_price"),
        row.get("take_profit"),
        row.get("stop_loss"),
    )
    repaired = False

    if not row.get("asset_class"):
        inferred = _infer_asset_class(row.get("symbol"))
        if inferred:
            updates["asset_class"] = inferred

    status = str(row.get("status") or "").upper()
    entry = row.get("entry_price")
    tp = row.get("take_profit")
    sl = row.get("stop_loss")
    resolution_price = row.get("resolution_price")
    outcome = row.get("outcome_pnl_pct")

    if status == "TP_HIT" and resolution_price is None and tp is not None:
        updates["resolution_price"] = tp
        resolution_price = tp
        repaired = True
    elif status == "SL_HIT" and resolution_price is None and sl is not None:
        updates["resolution_price"] = sl
        resolution_price = sl
        repaired = True

    if outcome is not None and (outcome < -100 or outcome > 500):
        exit_price = resolution_price
        if exit_price is None:
            if status == "TP_HIT":
                exit_price = tp
            elif status == "SL_HIT":
                exit_price = sl
        recalculated = _calc_capped_pnl(row.get("direction"), entry, exit_price)
        if recalculated is not None:
            updates["outcome_pnl_pct"] = recalculated
            repaired = True
        else:
            flags.append("pnl_out_of_range")

    if outcome is not None and status == "TP_HIT" and "tp_wrong_side" in flags:
        flags.append("tp_hit_with_invalid_tp")
    if outcome is not None and status == "SL_HIT" and "sl_wrong_side" in flags:
        flags.append("sl_hit_with_invalid_sl")

    return updates, sorted(set(flags)), repaired


def run_hygiene(apply: bool = False) -> dict:
    conn = get_db()
    rows = conn.execute("SELECT * FROM predictions ORDER BY id").fetchall()
    reviewed_at = datetime.now(timezone.utc).isoformat()

    summary = {
        "reviewed_at": reviewed_at,
        "apply": apply,
        "rows_reviewed": len(rows),
        "asset_class_backfills": 0,
        "resolution_repairs": 0,
        "pnl_repairs": 0,
        "rows_flagged_invalid": 0,
        "flag_counts": {},
        "sample_invalid_rows": [],
    }

    for raw in rows:
        row = dict(raw)
        updates, flags, _ = _repair_row(row)

        if "asset_class" in updates:
            summary["asset_class_backfills"] += 1
        if "resolution_price" in updates:
            summary["resolution_repairs"] += 1
        if "outcome_pnl_pct" in updates:
            summary["pnl_repairs"] += 1

        invalid = 1 if flags else 0
        if invalid:
            summary["rows_flagged_invalid"] += 1
            for flag in flags:
                summary["flag_counts"][flag] = summary["flag_counts"].get(flag, 0) + 1
            if len(summary["sample_invalid_rows"]) < 20:
                summary["sample_invalid_rows"].append(
                    {
                        "id": row.get("id"),
                        "symbol": row.get("symbol"),
                        "direction": row.get("direction"),
                        "status": row.get("status"),
                        "outcome_pnl_pct": row.get("outcome_pnl_pct"),
                        "flags": flags,
                    }
                )

        if apply:
            set_parts: list[str] = []
            params: list = []
            for key in ("asset_class", "resolution_price", "outcome_pnl_pct"):
                if key in updates:
                    set_parts.append(f"{key} = ?")
                    params.append(updates[key])
            set_parts.extend(
                [
                    "is_invalid_execution = ?",
                    "quality_flags = ?",
                    "quality_reviewed_at = ?",
                ]
            )
            params.extend([invalid, json.dumps(flags), reviewed_at, row["id"]])
            conn.execute(
                f"UPDATE predictions SET {', '.join(set_parts)} WHERE id = ?",
                params,
            )

    if apply:
        conn.commit()
        backfill_predictors(conn)
        export_leaderboard_json(conn, LEADERBOARD_PATH)

    REPORT_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    conn.close()
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair and flag historical prediction rows")
    parser.add_argument("--apply", action="store_true", help="Persist changes to predictions.db")
    args = parser.parse_args()

    summary = run_hygiene(apply=args.apply)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
