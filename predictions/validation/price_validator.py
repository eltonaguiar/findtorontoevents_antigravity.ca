"""Validate active predictions against live Binance prices."""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from db import get_db, get_active_predictions, resolve_prediction, export_analyst_json, export_leaderboard_json

# API failover: never rely on a single Binance endpoint
try:
    from alpha_engine import api_failover
except ImportError:
    pass  # sys.path already set above

MAX_HOLD_HOURS = 48  # 2 days — social media predictions are short-lived
LEADERBOARD_JSON = Path(__file__).parent.parent / "data" / "leaderboard.json"
ACTIVE_JSON = Path(__file__).parent.parent / "data" / "active_predictions.json"
ANALYST_LEADERBOARD_JSON = Path(__file__).parent.parent / "data" / "analyst_leaderboard.json"
ANALYST_ACTIVE_JSON = Path(__file__).parent.parent / "data" / "analyst_active_calls.json"


def fetch_binance_prices(symbols: list[str]) -> dict[str, float]:
    """Fetch prices for specific symbols with Binance mirror rotation + fallback."""
    params_str = json.dumps(symbols, separators=(',', ':'))
    for base in api_failover.BINANCE_SPOT_BASES:
        try:
            resp = requests.get(f"{base}/api/v3/ticker/price",
                               params={"symbols": params_str},
                               timeout=10)
            if resp.status_code == 451:
                continue  # geo-blocked, try next mirror
            resp.raise_for_status()
            return {t["symbol"]: float(t["price"]) for t in resp.json()}
        except Exception:
            continue
    # All Binance mirrors failed - fall back to individual api_failover.fetch_price()
    prices = {}
    for sym in symbols:
        p = api_failover.fetch_price(sym)
        if p is not None:
            prices[sym] = p
    return prices


def _export_prediction_jsons(conn, active_predictions: list[dict]) -> None:
    """Refresh all prediction payloads consumed by audit/dashboard surfaces."""
    export_leaderboard_json(conn, LEADERBOARD_JSON)
    export_analyst_json(conn, ANALYST_LEADERBOARD_JSON, ANALYST_ACTIVE_JSON)
    ACTIVE_JSON.parent.mkdir(parents=True, exist_ok=True)
    ACTIVE_JSON.write_text(json.dumps(active_predictions, indent=2, default=str))


def validate_all() -> dict:
    conn = get_db()
    active = get_active_predictions(conn)
    if not active:
        print("No active predictions to validate.")
        recalc_all_win_rates(conn)
        _export_prediction_jsons(conn, [])
        conn.close()
        return {"validated": 0, "closed": 0}

    symbols = list(set(p["symbol"] for p in active))
    prices = fetch_binance_prices(symbols)
    closed_count = 0
    still_active = []

    for pred in active:
        sym = pred["symbol"]
        if sym not in prices:
            still_active.append(pred)
            continue
        current = prices[sym]
        entry = pred.get("entry_price")
        tp = pred.get("take_profit")
        sl = pred.get("stop_loss")
        direction = pred["direction"]

        # ── Auto-fill missing entry price with current price on first validation ──
        if not entry:
            entry = current
            conn.execute(
                "UPDATE predictions SET entry_price = ? WHERE id = ? AND entry_price IS NULL",
                (current, pred["id"])
            )
            conn.commit()
            # Also auto-fill TP/SL if missing (default 5% TP, 3% SL)
            if not tp:
                if direction == "LONG":
                    tp = round(current * 1.05, 8)
                else:
                    tp = round(current * 0.95, 8)
                conn.execute("UPDATE predictions SET take_profit = ? WHERE id = ? AND take_profit IS NULL",
                             (tp, pred["id"]))
            if not sl:
                if direction == "LONG":
                    sl = round(current * 0.97, 8)
                else:
                    sl = round(current * 1.03, 8)
                conn.execute("UPDATE predictions SET stop_loss = ? WHERE id = ? AND stop_loss IS NULL",
                             (sl, pred["id"]))
            conn.commit()

        # ── BUG FIX 4: Sanity-check TP/SL direction consistency ──
        # SHORT TP must be below entry (price goes down); SHORT SL must be above entry.
        # LONG TP must be above entry (price goes up); LONG SL must be below entry.
        # If inverted, swap them or auto-correct with sensible defaults.
        if entry and tp and sl:
            if direction == "LONG":
                if tp < entry:
                    # TP below entry for a LONG is nonsensical — swap TP/SL if SL > entry
                    if sl > entry:
                        tp, sl = sl, tp
                        conn.execute("UPDATE predictions SET take_profit = ?, stop_loss = ? WHERE id = ?",
                                     (tp, sl, pred["id"]))
                        conn.commit()
                    else:
                        # Both are wrong, use defaults (5% TP, 3% SL)
                        tp = round(entry * 1.05, 8)
                        sl = round(entry * 0.97, 8)
                        conn.execute("UPDATE predictions SET take_profit = ?, stop_loss = ? WHERE id = ?",
                                     (tp, sl, pred["id"]))
                        conn.commit()
            elif direction == "SHORT":
                if tp > entry:
                    # TP above entry for a SHORT is nonsensical — swap TP/SL if SL < entry
                    if sl < entry:
                        tp, sl = sl, tp
                        conn.execute("UPDATE predictions SET take_profit = ?, stop_loss = ? WHERE id = ?",
                                     (tp, sl, pred["id"]))
                        conn.commit()
                    else:
                        # Both are wrong, use defaults (5% TP, 3% SL)
                        tp = round(entry * 0.95, 8)
                        sl = round(entry * 1.03, 8)
                        conn.execute("UPDATE predictions SET take_profit = ?, stop_loss = ? WHERE id = ?",
                                     (tp, sl, pred["id"]))
                        conn.commit()
        elif entry and tp and not sl:
            # Only TP provided — validate it
            if direction == "LONG" and tp < entry:
                tp = round(entry * 1.05, 8)
                conn.execute("UPDATE predictions SET take_profit = ? WHERE id = ?", (tp, pred["id"]))
                conn.commit()
            elif direction == "SHORT" and tp > entry:
                tp = round(entry * 0.95, 8)
                conn.execute("UPDATE predictions SET take_profit = ? WHERE id = ?", (tp, pred["id"]))
                conn.commit()

        # ── Additional PnL sanity guard: cap at +/- 100% ──
        # No single trade can lose more than 100% or gain more than 100% on spot.
        # This prevents the millions-of-percent PnL from garbage TP/SL values.

        # Time exit
        scraped = pred.get("scraped_at", "")
        if scraped:
            try:
                age = datetime.now(timezone.utc) - datetime.fromisoformat(scraped)
                if age > timedelta(hours=MAX_HOLD_HOURS):
                    pnl = _calc_pnl(direction, entry, current)
                    status = "EXPIRED_WIN" if pnl > 0 else "EXPIRED_LOSS"
                    resolve_prediction(conn, pred["id"], status, current, pnl)
                    _update_predictor_stats(conn, pred["predictor_id"], pnl > 0, pnl)
                    closed_count += 1
                    continue
            except Exception:
                pass

        # TP check
        if tp and entry:
            hit = (current >= tp) if direction == "LONG" else (current <= tp)
            if hit:
                pnl = _calc_pnl(direction, entry, tp)
                resolve_prediction(conn, pred["id"], "TP_HIT", tp, pnl)
                _update_predictor_stats(conn, pred["predictor_id"], True, pnl)
                closed_count += 1
                continue

        # SL check
        if sl and entry:
            hit = (current <= sl) if direction == "LONG" else (current >= sl)
            if hit:
                pnl = _calc_pnl(direction, entry, sl)
                resolve_prediction(conn, pred["id"], "SL_HIT", sl, pnl)
                _update_predictor_stats(conn, pred["predictor_id"], False, pnl)
                closed_count += 1
                continue

        still_active.append(pred)

    # Recalculate all win_rates from actual counts (fixes stale values from pre-fix bug)
    recalc_all_win_rates(conn)
    _export_prediction_jsons(conn, still_active)
    conn.close()
    print(f"Validated {len(active)}: {closed_count} closed, {len(still_active)} active")
    return {"validated": len(active), "closed": closed_count, "still_active": len(still_active)}


def _calc_pnl(direction: str, entry: float, exit_price: float) -> float:
    if not entry or entry == 0:
        return 0.0
    if direction == "LONG":
        pnl = round((exit_price - entry) / entry * 100, 4)
    else:
        pnl = round((entry - exit_price) / entry * 100, 4)
    # Cap PnL to sane range: no spot trade can lose > 100% or gain > 500%
    return max(min(pnl, 500.0), -100.0)


def _update_predictor_stats(conn, predictor_id: str, won: bool, pnl: float) -> None:
    if won:
        conn.execute("""
            UPDATE predictors SET wins = wins + 1,
                win_rate = CAST(wins + 1 AS REAL) / CASE WHEN total_predictions > 0 THEN total_predictions ELSE 1 END
            WHERE predictor_id = ?
        """, (predictor_id,))
    else:
        conn.execute("""
            UPDATE predictors SET losses = losses + 1,
                win_rate = CAST(wins AS REAL) / CASE WHEN total_predictions > 0 THEN total_predictions ELSE 1 END
            WHERE predictor_id = ?
        """, (predictor_id,))
    # Update PnL stats from all resolved predictions
    conn.execute("""
        UPDATE predictors SET
            avg_pnl_pct = (
                SELECT AVG(outcome_pnl_pct) FROM predictions
                WHERE predictor_id = ? AND outcome_pnl_pct IS NOT NULL
            ),
            best_pick_pnl = (
                SELECT MAX(outcome_pnl_pct) FROM predictions
                WHERE predictor_id = ? AND outcome_pnl_pct IS NOT NULL
            ),
            worst_pick_pnl = (
                SELECT MIN(outcome_pnl_pct) FROM predictions
                WHERE predictor_id = ? AND outcome_pnl_pct IS NOT NULL
            )
        WHERE predictor_id = ?
    """, (predictor_id, predictor_id, predictor_id, predictor_id))
    # Compute Sharpe ratio from resolved PnL values
    pnl_rows = conn.execute("""
        SELECT outcome_pnl_pct FROM predictions
        WHERE predictor_id = ? AND outcome_pnl_pct IS NOT NULL
    """, (predictor_id,)).fetchall()
    sharpe = 0.0
    if len(pnl_rows) >= 3:
        pnls = [r[0] for r in pnl_rows]
        mean_pnl = sum(pnls) / len(pnls)
        std_pnl = (sum((x - mean_pnl) ** 2 for x in pnls) / (len(pnls) - 1)) ** 0.5
        if std_pnl > 0:
            sharpe = round(mean_pnl / std_pnl, 4)
    conn.execute("UPDATE predictors SET sharpe = ? WHERE predictor_id = ?", (sharpe, predictor_id))
    # Update tier
    row = conn.execute("SELECT * FROM predictors WHERE predictor_id = ?", (predictor_id,)).fetchone()
    if row:
        t = row["total_predictions"]
        wr = row["win_rate"]
        s = sharpe
        tier = "UNRANKED"
        if t >= 5:
            if wr >= 0.65 and t >= 50:
                tier = "ELITE"
            elif wr >= 0.55 and t >= 25:
                tier = "PROVEN"
            elif wr >= 0.45:
                tier = "MIXED"
            else:
                tier = "LOSING"
        conn.execute("UPDATE predictors SET tier = ? WHERE predictor_id = ?", (tier, predictor_id))
    conn.commit()


def recalc_all_win_rates(conn) -> int:
    """Recalculate win_rate for all predictors from actual wins/total counts."""
    conn.execute("""
        UPDATE predictors SET win_rate = CASE
            WHEN total_predictions > 0 THEN CAST(wins AS REAL) / total_predictions
            ELSE 0.0
        END
    """)
    conn.commit()
    return conn.execute("SELECT changes()").fetchone()[0]


if __name__ == "__main__":
    validate_all()
