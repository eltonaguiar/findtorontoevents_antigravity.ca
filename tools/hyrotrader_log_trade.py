#!/usr/bin/env python3
"""Append-only trade logger for audit_dashboard/data/hyrotrader_journal.json.
Opens new trades or closes existing open trades by pick_id. Never overwrites closed entries.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
JOURNAL_PATH = WORKSPACE / "audit_dashboard" / "data" / "hyrotrader_journal.json"
PICKS_PATH = WORKSPACE / "audit_dashboard" / "data" / "hyrotrader_picks.json"

RISK_PCT = 0.01  # 1% of baseline equity per trade


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_journal(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_journal_atomic(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def _calc_position_size(entry_price: float, stop_loss: float, baseline_equity: float) -> tuple[float, float]:
    price_risk = abs(entry_price - stop_loss)
    if price_risk <= 0:
        return 0.0, 0.0
    risk_amount = baseline_equity * RISK_PCT
    size_units = risk_amount / price_risk
    position_size_usdt = size_units * entry_price
    return round(position_size_usdt, 4), round(risk_amount, 4)


def _load_json_or_empty(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _sync_pick_open(picks_doc: dict, trade: dict) -> bool:
    changed = False
    for pick in picks_doc.get("picks", []):
        if pick.get("id") != trade.get("pick_id"):
            continue
        # 2026-05-05 PR #5: SL/TP population gate. Refuse to mark a pick
        # `status: "open"` if any of entry / SL / TP is None — protects the
        # Hyrotrader prop-firm challenge (SL required within 5 min of entry)
        # from phantom-active rows. `is None` (not `> 0`) so legit zero stops
        # for market-making strategies still pass.
        entry = trade.get("entry_price")
        sl = trade.get("stop_loss")
        tp = trade.get("take_profit")
        if entry is None or sl is None or tp is None:
            print(
                f"WARN: hyro SL/TP gate: refusing 'open' write for pick_id={pick.get('id')!r} "
                f"— entry={entry} sl={sl} tp={tp}; pick stays at status={pick.get('status')!r}",
                file=sys.stderr,
            )
            return False
        pick["symbol_hint"] = trade.get("symbol") or pick.get("symbol_hint")
        pick["entry_price"] = entry
        pick["stop_loss"] = sl
        pick["take_profit"] = tp
        pick["status"] = "open"
        pick["opened_at"] = trade.get("entry_time")
        pick["closed_at"] = None
        pick["pnl_pct"] = None
        pick["sl_confirmed"] = True
        if trade.get("position_size_usdt") is not None:
            pick["position_size_usdt"] = trade.get("position_size_usdt")
        if trade.get("risk_amount_usdt") is not None:
            pick["risk_amount_usdt"] = trade.get("risk_amount_usdt")
        changed = True
        break
    return changed


def _sync_pick_close(picks_doc: dict, trade: dict) -> bool:
    changed = False
    for pick in picks_doc.get("picks", []):
        if pick.get("id") != trade.get("pick_id"):
            continue
        pick["status"] = "closed"
        pick["closed_at"] = trade.get("closed_at")
        pick["pnl_pct"] = trade.get("pnl_pct")
        pick["pnl_usdt"] = trade.get("pnl_usdt")
        pick["exit_price"] = trade.get("exit_price")
        pick["exit_reason"] = trade.get("exit_reason")
        changed = True
        break
    return changed


def sync_picks_file(trade: dict, *, closed: bool, picks_path: Path = PICKS_PATH) -> bool:
    picks_doc = _load_json_or_empty(picks_path)
    if not picks_doc:
        return False
    changed = _sync_pick_close(picks_doc, trade) if closed else _sync_pick_open(picks_doc, trade)
    if changed:
        write_journal_atomic(picks_path, picks_doc)
    return changed


def open_trade(journal: dict, args: argparse.Namespace) -> dict:
    trades = journal.setdefault("trades", [])
    for existing in trades:
        if existing.get("pick_id") == args.pick_id and existing.get("status") == "open":
            print(f"ERROR: open trade already exists for pick_id={args.pick_id}", file=sys.stderr)
            sys.exit(2)
    trade_id = f"hyro-trade-{len(trades) + 1:05d}-{args.pick_id}"
    baseline = float(journal.get("baseline_equity_usdt", 5000))
    position_size_usdt, risk_amount_usdt = _calc_position_size(float(args.entry_price), float(args.stop_loss), baseline)
    trade = {
        "id": trade_id,
        "pick_id": args.pick_id,
        "symbol": args.symbol,
        "direction": args.direction.upper(),
        "entry_price": float(args.entry_price),
        "entry_time": args.entry_time or _now_iso(),
        "stop_loss": float(args.stop_loss),
        "take_profit": float(args.take_profit),
        "position_size_usdt": position_size_usdt,
        "risk_amount_usdt": risk_amount_usdt,
        "status": "open",
    }
    trades.append(trade)
    return trade


def close_trade(journal: dict, args: argparse.Namespace) -> dict:
    trades = journal.get("trades", [])
    baseline = float(journal.get("baseline_equity_usdt", 5000))
    target = None
    for t in trades:
        if t.get("pick_id") == args.close_pick_id and t.get("status") == "open":
            target = t
            break
    if target is None:
        print(f"ERROR: no open trade found for pick_id={args.close_pick_id}", file=sys.stderr)
        sys.exit(2)

    entry = float(target["entry_price"])
    sl = float(target["stop_loss"])
    exit_price = float(args.exit_price)
    direction = target["direction"]

    price_risk = abs(entry - sl)
    if price_risk == 0:
        print("ERROR: price_risk is zero, cannot compute PnL", file=sys.stderr)
        sys.exit(2)
    risk_amount = baseline * RISK_PCT
    size = risk_amount / price_risk

    if direction == "LONG":
        price_diff = exit_price - entry
    else:
        price_diff = entry - exit_price
    pnl_usdt = price_diff * size
    # M8 NOTE: kept in PERCENT form to match dashboard's existing mixed
    # convention. Hygiene pipeline (closed_picks_hygiene.normalize_pnl_units)
    # converges at analysis time. See CURSOR_QUANT_AUDIT_FINDINGS_2026-04-11.md
    pnl_pct = (price_diff / entry) * 100.0

    target["closed_at"] = args.exit_time or _now_iso()
    target["exit_price"] = exit_price
    target["exit_reason"] = args.exit_reason
    target["pnl_usdt"] = round(pnl_usdt, 4)
    target["pnl_pct"] = round(pnl_pct, 4)
    target["won"] = pnl_pct > 0
    target["bars_held"] = args.bars_held
    target["status"] = "closed"
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Append-only trade logger for hyrotrader journal")
    parser.add_argument("--pick-id", help="Pick ID (required to open a trade)")
    parser.add_argument("--symbol")
    parser.add_argument("--direction", choices=["LONG", "SHORT", "long", "short"])
    parser.add_argument("--entry-price", type=float)
    parser.add_argument("--entry-time")
    parser.add_argument("--stop-loss", type=float)
    parser.add_argument("--take-profit", type=float)

    parser.add_argument("--close-pick-id", help="Pick ID of open trade to close")
    parser.add_argument("--exit-price", type=float)
    parser.add_argument("--exit-time")
    parser.add_argument("--exit-reason", choices=["take_profit", "stop_loss", "manual", "timeout", "trailing_stop"])
    parser.add_argument("--bars-held", type=int, default=None)

    parser.add_argument("--journal", default=str(JOURNAL_PATH))
    parser.add_argument("--picks", default=str(PICKS_PATH))
    args = parser.parse_args()

    path = Path(args.journal)
    journal = load_journal(path)
    picks_path = Path(args.picks)

    if args.close_pick_id:
        if args.exit_price is None or args.exit_reason is None:
            print("ERROR: --exit-price and --exit-reason required to close", file=sys.stderr)
            return 2
        closed = close_trade(journal, args)
        write_journal_atomic(path, journal)
        sync_picks_file(closed, closed=True, picks_path=picks_path)
        print(f"CLOSED {closed['id']} {closed['symbol']} {closed['direction']} pnl={closed['pnl_usdt']} ({closed['pnl_pct']}%) reason={closed['exit_reason']}")
        return 0

    required = [args.pick_id, args.symbol, args.direction, args.entry_price, args.stop_loss, args.take_profit]
    if any(v is None for v in required):
        print("ERROR: opening a trade requires --pick-id --symbol --direction --entry-price --stop-loss --take-profit", file=sys.stderr)
        return 2
    opened = open_trade(journal, args)
    write_journal_atomic(path, journal)
    sync_picks_file(opened, closed=False, picks_path=picks_path)
    print(f"OPENED {opened['id']} {opened['symbol']} {opened['direction']} entry={opened['entry_price']} SL={opened['stop_loss']} TP={opened['take_profit']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
