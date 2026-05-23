"""Import backtest trades into the LOCAL SQLite audit_trail.db."""
import sqlite3
import json
import uuid
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "audit_trail.db"


def norm_dir(d):
    d = str(d).upper()
    if "BUY" in d or "LONG" in d:
        return "LONG"
    if "SELL" in d or "SHORT" in d:
        return "SHORT"
    return d


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def collect_trades():
    trades = []

    # 1. Battleground
    data = load_json(ROOT / "battleground/data/closed_picks.json")
    if data:
        for p in data:
            trades.append({
                "source_db": "battleground/data/closed_picks.json",
                "source_table": "closed_picks",
                "symbol": p.get("symbol", ""),
                "asset_class": "CRYPTO",
                "direction": norm_dir(p.get("direction", "")),
                "strategy": p.get("strategy", ""),
                "entry_price": p.get("entry_price"),
                "exit_price": p.get("exit_price"),
                "take_profit": p.get("take_profit"),
                "stop_loss": p.get("stop_loss"),
                "entry_time": p.get("entry_time"),
                "exit_time": p.get("exit_time"),
                "pnl_pct": float(p.get("pnl_pct", 0) or 0),
                "status": p.get("status", "CLOSED"),
                "confidence": p.get("confidence"),
            })
        print(f"  [battleground] {len(data)} trades")

    # 2. Alpha engine
    data = load_json(ROOT / "alpha_engine/data/closed_picks.json")
    if data:
        for p in data:
            cat = (p.get("category") or "CRYPTO").upper()
            if cat not in ("CRYPTO", "FOREX", "EQUITY"):
                cat = "CRYPTO"
            trades.append({
                "source_db": "alpha_engine/data/closed_picks.json",
                "source_table": "closed_picks",
                "symbol": p.get("symbol", ""),
                "asset_class": cat,
                "direction": norm_dir(p.get("signal_type", p.get("direction", ""))),
                "strategy": p.get("strategy", ""),
                "entry_price": p.get("entry_price"),
                "exit_price": p.get("exit_price"),
                "take_profit": p.get("take_profit"),
                "stop_loss": p.get("stop_loss"),
                "entry_time": p.get("entry_date"),
                "exit_time": p.get("exit_date"),
                "pnl_pct": float(p.get("pnl_pct", 0) or 0),
                "status": "CLOSED",
                "confidence": p.get("confidence"),
            })
        print(f"  [alpha_engine] {len(data)} trades")

    # 3. Paper trading
    try:
        pconn = sqlite3.connect(str(ROOT / "paper_trading/data/paper.db"))
        pconn.row_factory = sqlite3.Row
        rows = pconn.execute('SELECT * FROM positions WHERE status != "ACTIVE"').fetchall()
        for r in rows:
            trades.append({
                "source_db": "paper_trading/data/paper.db",
                "source_table": "positions",
                "symbol": r["symbol"],
                "asset_class": "CRYPTO",
                "direction": norm_dir(r["direction"]),
                "strategy": r["strategy_name"] or r["strategy"],
                "entry_price": r["entry_price"],
                "exit_price": r["exit_price"],
                "take_profit": r["tp"],
                "stop_loss": r["sl"],
                "entry_time": r["entry_date"],
                "exit_time": r["exit_date"],
                "pnl_pct": r["pnl_pct"],
                "status": r["status"],
                "confidence": r["confidence"],
            })
        print(f"  [paper_trading] {len(rows)} trades")
        pconn.close()
    except Exception as e:
        print(f"  [paper_trading] error: {e}")

    # 4. Mercury2
    data = load_json(ROOT / "mercury2/data/closed_picks.json")
    if data:
        for p in data:
            trades.append({
                "source_db": "mercury2/data/closed_picks.json",
                "source_table": "closed_picks",
                "symbol": p.get("symbol", ""),
                "asset_class": "CRYPTO",
                "direction": norm_dir(p.get("direction", p.get("signal_type", ""))),
                "strategy": p.get("strategy", ""),
                "entry_price": p.get("entry_price"),
                "exit_price": p.get("exit_price"),
                "take_profit": p.get("take_profit"),
                "stop_loss": p.get("stop_loss"),
                "entry_time": p.get("timestamp"),
                "exit_time": p.get("exit_time"),
                "pnl_pct": p.get("realized_pnl_pct", float(p.get("pnl_pct", 0) or 0)),
                "status": "CLOSED",
                "confidence": p.get("confidence"),
            })
        print(f"  [mercury2] {len(data)} trades")

    # 5. ML Battleground ClawsOfDoom
    data = load_json(ROOT / "ml_battleground/system_f_clawsofdoom/data/closed_picks.json")
    if data:
        for p in data:
            trades.append({
                "source_db": "ml_battleground/system_f_clawsofdoom/data/closed_picks.json",
                "source_table": "closed_picks",
                "symbol": p.get("symbol", ""),
                "asset_class": "CRYPTO",
                "direction": norm_dir(p.get("direction", "")),
                "strategy": p.get("strategy", ""),
                "entry_price": p.get("entry_price"),
                "exit_price": p.get("exit_price"),
                "take_profit": p.get("tp_price"),
                "stop_loss": p.get("sl_price"),
                "entry_time": None,
                "exit_time": p.get("exit_time_est"),
                "pnl_pct": p.get("realized_pnl_pct", 0),
                "status": p.get("status", "CLOSED"),
                "confidence": p.get("confidence"),
            })
        print(f"  [ml_bg_clawsofdoom] {len(data)} trades")
        # 7. Other ML Battleground systems
        ml_systems = [
            ("ml_battleground/system_a_filter/data/closed_picks.json", "ml_bg_system_a"),
            ("ml_battleground/system_b_regime/data/closed_picks.json", "ml_bg_system_b"),
            ("ml_battleground/system_c_deeplearn/data/closed_picks.json", "ml_bg_system_c"),
            ("ml_battleground/system_d_carry/data/closed_picks.json", "ml_bg_system_d"),
            ("ml_battleground/system_e_momentum/data/closed_picks.json", "ml_bg_system_e"),
            ("ml_battleground/ensemble_data/closed_picks.json", "ml_bg_ensemble")
        ]
        for path, sys_name in ml_systems:
            data = load_json(ROOT / path)
            if data:
                for p in data:
                    trades.append({
                        "source_db": f"{path}",
                        "source_table": "closed_picks",
                        "symbol": p.get("symbol", ""),
                        "asset_class": "CRYPTO",
                        "direction": norm_dir(p.get("direction", "")),
                        "strategy": p.get("strategy", ""),
                        "entry_price": p.get("entry_price"),
                        "exit_price": p.get("exit_price"),
                        "take_profit": p.get("take_profit"),
                        "stop_loss": p.get("stop_loss"),
                        "entry_time": p.get("entry_time"),
                        "exit_time": p.get("exit_time"),
                        "pnl_pct": float(p.get("pnl_pct", 0) or 0),
                        "status": "CLOSED",
                        "confidence": p.get("confidence")
                    })
                print(f"  [{sys_name}] {len(data)} trades")

    # 6. Sandbox opposite day
    try:
        sconn = sqlite3.connect(str(ROOT / "sandbox/data/opposite_day.db"))
        sconn.row_factory = sqlite3.Row
        rows = sconn.execute('SELECT * FROM opposite_picks WHERE status != "ACTIVE"').fetchall()
        for r in rows:
            trades.append({
                "source_db": "sandbox/data/opposite_day.db",
                "source_table": "opposite_picks",
                "symbol": r["symbol"],
                "asset_class": "CRYPTO",
                "direction": norm_dir(r["opposite_direction"]),
                "strategy": "opposite_day",
                "entry_price": r["entry_price"],
                "exit_price": r["close_price"],
                "take_profit": r["opposite_tp"],
                "stop_loss": r["opposite_sl"],
                "entry_time": r["picked_at"],
                "exit_time": r["closed_at"],
                "pnl_pct": r["pnl_pct"],
                "status": r["status"],
                "confidence": r["confidence"],
            })
        print(f"  [sandbox_opposite] {len(rows)} trades")
        sconn.close()
    except Exception as e:
        print(f"  [sandbox_opposite] error: {e}")

    # 7. KIMI trading picks (closed)
    try:
        kconn = sqlite3.connect(str(ROOT / "KIMI_RISEOFTHECLAW/data/kimi_trading.db"))
        kconn.row_factory = sqlite3.Row
        rows = kconn.execute('SELECT * FROM picks WHERE status IN ("WIN","LOSS","WON","LOST")').fetchall()
        for r in rows:
            sym = r["symbol"] if "symbol" in r.keys() else ""
            # Normalize X-USD to XUSDT
            if sym.endswith("-USD"):
                sym = sym.replace("-USD", "USDT")
            trades.append({
                "source_db": "KIMI_RISEOFTHECLAW/data/kimi_trading.db",
                "source_table": "picks",
                "symbol": sym,
                "asset_class": "CRYPTO",
                "direction": norm_dir(r["direction"] if "direction" in r.keys() else ""),
                "strategy": r["strategy"] if "strategy" in r.keys() else "kimi",
                "entry_price": r["entry_price"] if "entry_price" in r.keys() else None,
                "exit_price": r["exit_price"] if "exit_price" in r.keys() else None,
                "take_profit": r["take_profit"] if "take_profit" in r.keys() else None,
                "stop_loss": r["stop_loss"] if "stop_loss" in r.keys() else None,
                "entry_time": r["created_at"] if "created_at" in r.keys() else None,
                "exit_time": r["closed_at"] if "closed_at" in r.keys() else None,
                "pnl_pct": r["pnl_pct"] if "pnl_pct" in r.keys() else 0,
                "status": r["status"],
                "confidence": r["confidence"] if "confidence" in r.keys() else None,
            })
        print(f"  [kimi_trading] {len(rows)} trades")
        kconn.close()
    except Exception as e:
        print(f"  [kimi_trading] error: {e}")

    # 8. KIMI signal tracker (closed, deduplicated)
    try:
        stconn = sqlite3.connect(str(ROOT / "KIMI_RISEOFTHECLAW/data/signal_tracker.db"))
        stconn.row_factory = sqlite3.Row
        rows = stconn.execute('SELECT * FROM tracked_signals WHERE status IN ("WIN","LOSS","WON","LOST","TP_HIT","SL_HIT")').fetchall()
        seen = set()
        dedup_count = 0
        for r in rows:
            sym = r["symbol"] if "symbol" in r.keys() else ""
            if sym.endswith("-USD"):
                sym = sym.replace("-USD", "USDT")
            key = (sym, r["direction"] if "direction" in r.keys() else "",
                   str(r["entry_price"] if "entry_price" in r.keys() else ""))
            if key in seen:
                dedup_count += 1
                continue
            seen.add(key)
            trades.append({
                "source_db": "KIMI_RISEOFTHECLAW/data/signal_tracker.db",
                "source_table": "tracked_signals",
                "symbol": sym,
                "asset_class": "CRYPTO",
                "direction": norm_dir(r["direction"] if "direction" in r.keys() else ""),
                "strategy": r["algorithm"] if "algorithm" in r.keys() else "kimi_tracker",
                "entry_price": r["entry_price"] if "entry_price" in r.keys() else None,
                "exit_price": r["exit_price"] if "exit_price" in r.keys() else None,
                "take_profit": r["take_profit"] if "take_profit" in r.keys() else None,
                "stop_loss": r["stop_loss"] if "stop_loss" in r.keys() else None,
                "entry_time": r["created_at"] if "created_at" in r.keys() else None,
                "exit_time": r["resolved_at"] if "resolved_at" in r.keys() else None,
                "pnl_pct": r["pnl_pct"] if "pnl_pct" in r.keys() else 0,
                "status": r["status"],
                "confidence": r["confidence"] if "confidence" in r.keys() else None,
            })
        print(f"  [kimi_signal_tracker] {len(rows)-dedup_count} trades (deduped {dedup_count})")
        stconn.close()
    except Exception as e:
        print(f"  [kimi_signal_tracker] error: {e}")

    # 9. Predictions DB (closed)
    try:
        pconn = sqlite3.connect(str(ROOT / "predictions/data/predictions.db"))
        pconn.row_factory = sqlite3.Row
        rows = pconn.execute('SELECT * FROM predictions WHERE status IN ("SL_HIT","TP_HIT","CLOSED","EXPIRED")').fetchall()
        for r in rows:
            trades.append({
                "source_db": "predictions/data/predictions.db",
                "source_table": "predictions",
                "symbol": r["symbol"] if "symbol" in r.keys() else "",
                "asset_class": "CRYPTO",
                "direction": norm_dir(r["direction"] if "direction" in r.keys() else ""),
                "strategy": "predictions",
                "entry_price": r["entry_price"] if "entry_price" in r.keys() else None,
                "exit_price": r["exit_price"] if "exit_price" in r.keys() else None,
                "take_profit": r["take_profit"] if "take_profit" in r.keys() else None,
                "stop_loss": r["stop_loss"] if "stop_loss" in r.keys() else None,
                "entry_time": r["created_at"] if "created_at" in r.keys() else None,
                "exit_time": r["resolved_at"] if "resolved_at" in r.keys() else None,
                "pnl_pct": r["pnl_pct"] if "pnl_pct" in r.keys() else 0,
                "status": r["status"],
                "confidence": r["confidence"] if "confidence" in r.keys() else None,
            })
        print(f"  [predictions] {len(rows)} trades")
        pconn.close()
    except Exception as e:
        print(f"  [predictions] error: {e}")

    # 10. Meta-strategy permutation signals (closed)
    try:
        mconn = sqlite3.connect(str(ROOT / "meta_strategy/data/meta_strategy.db"))
        mconn.row_factory = sqlite3.Row
        rows = mconn.execute('SELECT * FROM permutation_signals WHERE status IN ("SL_HIT","TP_HIT","CLOSED")').fetchall()
        for r in rows:
            trades.append({
                "source_db": "meta_strategy/data/meta_strategy.db",
                "source_table": "permutation_signals",
                "symbol": r["symbol"] if "symbol" in r.keys() else "",
                "asset_class": "CRYPTO",
                "direction": norm_dir(r["direction"] if "direction" in r.keys() else ""),
                "strategy": r["strategy"] if "strategy" in r.keys() else "meta_permutation",
                "entry_price": r["entry_price"] if "entry_price" in r.keys() else None,
                "exit_price": r["exit_price"] if "exit_price" in r.keys() else None,
                "take_profit": r["take_profit"] if "take_profit" in r.keys() else None,
                "stop_loss": r["stop_loss"] if "stop_loss" in r.keys() else None,
                "entry_time": r["created_at"] if "created_at" in r.keys() else None,
                "exit_time": r["resolved_at"] if "resolved_at" in r.keys() else None,
                "pnl_pct": r["pnl_pct"] if "pnl_pct" in r.keys() else 0,
                "status": r["status"],
                "confidence": r["confidence"] if "confidence" in r.keys() else None,
            })
        print(f"  [meta_strategy] {len(rows)} trades")
        mconn.close()
    except Exception as e:
        print(f"  [meta_strategy] error: {e}")

    return trades


def main():
    print("Collecting trades from local sources...")
    trades = collect_trades()
    print(f"\nTotal trades: {len(trades)}")

    # Normalize statuses to canonical values
    _status_map = {
        "WON": "WIN", "TP_HIT": "WIN", "CLOSED_TP": "WIN",
        "LOST": "LOSS", "SL_HIT": "LOSS", "CLOSED_SL": "LOSS",
        "closed": "CLOSED", "RESOLVED": "CLOSED",
        "expired": "EXPIRED",
    }
    # Normalize symbols: X-USD → XUSDT
    for t in trades:
        t["status"] = _status_map.get(t["status"], t["status"])
        sym = t.get("symbol", "")
        if sym.endswith("-USD"):
            t["symbol"] = sym.replace("-USD", "USDT")

    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    # Clear existing data
    c.execute("DELETE FROM bt_backtest_trades")
    c.execute("DELETE FROM bt_backtest_runs")

    # Insert trades (deduplicated by symbol+direction+strategy+entry_time)
    seen = set()
    dedup_total = 0
    for t in trades:
        dedup_key = (t["symbol"], t["direction"], t["strategy"], t.get("entry_time", ""))
        if dedup_key in seen:
            dedup_total += 1
            continue
        seen.add(dedup_key)
        c.execute(
            """INSERT INTO bt_backtest_trades
            (source_db, source_table, symbol, asset_class, direction, strategy,
             entry_price, exit_price, take_profit, stop_loss, entry_time, exit_time,
             pnl_pct, status, confidence, imported_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, datetime('now'))""",
            (t["source_db"], t["source_table"], t["symbol"], t["asset_class"],
             t["direction"], t["strategy"], t["entry_price"], t["exit_price"],
             t["take_profit"], t["stop_loss"], t["entry_time"], t["exit_time"],
             t["pnl_pct"], t["status"], t["confidence"]),
        )

    # Compute runs
    strat_trades = defaultdict(list)
    for t in trades:
        if t["strategy"]:
            strat_trades[t["strategy"]].append(float(t["pnl_pct"] or 0))

    for strat, pnls in strat_trades.items():
        total = len(pnls)
        wins = sum(1 for p in pnls if p > 0)
        losses = total - wins
        wr = wins / total if total > 0 else 0
        total_return = sum(pnls)
        win_pnl = sum(p for p in pnls if p > 0)
        loss_pnl = sum(abs(p) for p in pnls if p < 0)
        pf = round(win_pnl / loss_pnl, 3) if loss_pnl > 0 else None
        avg = total_return / total if total > 0 else 0
        std = (sum((p - avg) ** 2 for p in pnls) / total) ** 0.5 if total > 1 else 0
        sharpe = round(avg / std, 3) if std > 0 else None
        cum = peak = max_dd = 0.0
        for p in pnls:
            cum += p
            if cum > peak:
                peak = cum
            dd = peak - cum
            if dd > max_dd:
                max_dd = dd

        c.execute(
            """INSERT INTO bt_backtest_runs
            (id, source_db, source_table, strategy, symbol, asset_class,
             total_trades, wins, losses, win_rate, profit_factor, total_return,
             sharpe, max_drawdown, imported_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?, datetime('now'))""",
            (str(uuid.uuid4()), "local_import", "mixed", strat, "ALL", "CRYPTO",
             total, wins, losses, round(wr, 4), pf, round(total_return, 4),
             sharpe, round(max_dd, 4) if max_dd else 0),
        )

    conn.commit()

    # Verify
    count_t = c.execute("SELECT COUNT(*) FROM bt_backtest_trades").fetchone()[0]
    count_r = c.execute("SELECT COUNT(*) FROM bt_backtest_runs").fetchone()[0]
    print(f"\nInserted into local SQLite ({DB_PATH}):")
    print(f"  bt_backtest_trades: {count_t}")
    print(f"  bt_backtest_runs:   {count_r}")
    conn.close()


if __name__ == "__main__":
    main()
