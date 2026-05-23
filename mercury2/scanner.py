# -*- coding: utf-8 -*-
"""Mercury 2 — Live scanner (runs every 30 min via GitHub Actions).

Usage:
    python -m mercury2.scanner

Loads pre-trained models, fetches latest candles, runs inference through
the risk engine, outputs active_picks.json + top_gainers.json.
"""

import logging, json, sys, time, math, numpy as np, pandas as pd
from datetime import datetime, timezone

from .config import (
    SYMBOLS, TIMEFRAME, SCAN_BARS, FEATURE_COLS,
    MAX_CONCURRENT_PICKS, DEGRADED_MAX_PICKS, MIN_CONFIDENCE, TOP_K, DATA_DIR, VERSION, SYSTEM_NAME,
    DISCORD_WEBHOOK, round_trip_cost,
)
from .data_fetcher import (
    fetch_ohlcv, fetch_funding_rate, fetch_fear_greed, fetch_btc_dominance,
)
from .features import add_features
from .ensemble import load_ensemble, ensemble_predict
from .top_gainer import load_top_gainer, predict_top_gainers, TOP_GAINER_FEATURES
from .risk_engine import evaluate_signal

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("mercury2.scanner")

SCAN_STATE_PATH = DATA_DIR / "last_scan_state.json"


def pick_is_economic_win(p: dict) -> bool:
    """True if realized PnL is positive; else strict TP WIN status."""
    for key in ("pnl_pct", "realized_pnl_pct"):
        v = p.get(key)
        if v is None:
            continue
        try:
            return float(v) > 0.0
        except (TypeError, ValueError):
            continue
    return str(p.get("status", "")).upper() == "WIN"


def _check_candle_gate(reference_df) -> bool:
    """Returns True if a new 1h candle has closed since last scan.

    Uses the first symbol's 1h data as the reference candle clock. If the
    latest candle close timestamp matches the stored one, skip the scan to
    avoid computing features on incomplete (mid-candle) data.
    """
    if reference_df is None or reference_df.empty:
        return True  # No data = let it try
    latest_close = str(reference_df.index[-1])
    if SCAN_STATE_PATH.exists():
        try:
            with open(SCAN_STATE_PATH) as f:
                state = json.load(f)
            if state.get("last_candle_close") == latest_close:
                return False
        except (json.JSONDecodeError, OSError):
            pass
    # Update state
    SCAN_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SCAN_STATE_PATH, 'w') as f:
        json.dump({"last_candle_close": latest_close}, f)
    return True


def load_active_picks() -> list[dict]:
    path = DATA_DIR / "active_picks.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []


def load_closed_picks() -> list[dict]:
    path = DATA_DIR / "closed_picks.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []


def save_json(data, filename: str):
    path = DATA_DIR / filename
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def resolve_picks(active: list[dict], latest_prices: dict[str, float],
                  now: datetime) -> tuple[list[dict], list[dict], list[str]]:
    """Check active picks against TP/SL and resolve them.

    Returns:
        (still_active, newly_closed, resolution_messages)
    """
    still_active = []
    newly_closed = []
    messages = []

    for pick in active:
        sym = pick["symbol"]
        price = latest_prices.get(sym)
        if price is None:
            still_active.append(pick)
            continue

        entry = pick["entry_price"]
        tp = pick["take_profit"]
        sl = pick["stop_loss"]
        direction = pick.get("direction", "LONG")

        # Update unrealized P&L
        if direction == "LONG":
            pnl_pct = (price - entry) / entry * 100
            hit_tp = price >= tp
            hit_sl = price <= sl
        else:  # SHORT
            pnl_pct = (entry - price) / entry * 100
            hit_tp = price <= tp
            hit_sl = price >= sl

        pick["current_price"] = price
        pick["unrealized_pnl_pct"] = round(pnl_pct, 4)
        pick["last_checked"] = now.isoformat()

        if hit_tp:
            pick["status"] = "WIN"
            pick["exit_price"] = tp
            pick["exit_time"] = now.isoformat()
            pick["realized_pnl_pct"] = round(abs(tp - entry) / entry * 100, 4)
            pick["pnl_pct"] = pick["realized_pnl_pct"]  # feedback loop compatible field
            pick["exit_reason"] = "Take Profit (TP) hit: price reached target"
            newly_closed.append(pick)
            messages.append(f"  WIN: {sym} {direction} TP hit at {tp:.4f} (+{pick['realized_pnl_pct']:.2f}%)")
        elif hit_sl:
            pick["status"] = "LOSS"
            pick["exit_price"] = sl
            pick["exit_time"] = now.isoformat()
            pick["realized_pnl_pct"] = round(-abs(sl - entry) / entry * 100, 4)
            pick["pnl_pct"] = pick["realized_pnl_pct"]  # feedback loop compatible field
            pick["exit_reason"] = "Stop Loss (SL) hit: price breached protective level"
            newly_closed.append(pick)
            messages.append(f"  LOSS: {sym} {direction} SL hit at {sl:.4f} ({pick['realized_pnl_pct']:.2f}%)")
        else:
            still_active.append(pick)

    return still_active, newly_closed, messages


def _check_validation_gate() -> dict:
    """Check if the trained model passed DSR/PSR validation.

    Returns dict with 'passed' bool and diagnostics.
    """
    path = DATA_DIR / "validation_report.json"
    if not path.exists():
        return {"passed": False, "reason": "No validation report found (model never validated)"}
    try:
        with open(path) as f:
            report = json.load(f)
        if report.get("passed") or report.get("valid"):
            return {"passed": True, "reason": "DSR/PSR gates passed"}
        return {
            "passed": False,
            "reason": report.get("reason", "DSR/PSR validation failed"),
            "dsr": report.get("dsr_pvalue", 0),
            "psr": report.get("psr_pvalue", 0),
            "sharpe": report.get("sharpe", 0),
        }
    except Exception as e:
        return {"passed": False, "reason": f"Error reading validation report: {e}"}


def run_scan():
    """Main scan loop."""
    now = datetime.now(timezone.utc)
    log.info(f"=== Mercury 2 Scanner v{VERSION} — {now.isoformat()} ===")

    # ── 0. Validation gate — degrade if model failed DSR/PSR ──
    val_status = _check_validation_gate()
    validation_passed = val_status["passed"]
    degraded_mode = False

    degraded_max_picks = DEGRADED_MAX_PICKS
    degraded_min_conf = 0.58      # slightly below live MIN_CONFIDENCE so degraded mode can still emit

    if not validation_passed:
        log.warning(f"  VALIDATION GATE FAILED: {val_status['reason']}")
        log.warning(f"  DSR={val_status.get('dsr', 0):.3f}, PSR={val_status.get('psr', 0):.3f}, Sharpe={val_status.get('sharpe', 0):.2f}")
        log.warning("  Entering DEGRADED MODE: max_picks=%d, min_conf=%.2f (picks will carry validation_warning)",
                    degraded_max_picks, degraded_min_conf)
        degraded_mode = True

    # ── 1. Load models ──
    models = load_ensemble()
    if models is None:
        log.error("No pre-trained ensemble found. Run trainer first: python -m mercury2.trainer")
        sys.exit(1)

    top_model = load_top_gainer()  # May be None if LightGBM not available

    # ── 2. Load existing picks ──
    active = load_active_picks()
    closed = load_closed_picks()
    active_symbols = {p["symbol"] for p in active}
    log.info(f"  Active picks: {len(active)}, Closed: {len(closed)}")

    # ── 3. Fetch sentiment (once for all symbols) ──
    fng = fetch_fear_greed()
    btc_dom = fetch_btc_dominance()
    log.info(f"  F&G={fng}, BTC dominance={btc_dom:.1f}%")

    # ── 4. Candle-Close Gate: skip if no new candle closed ──
    _ref_sym = "BTCUSDT" if "BTCUSDT" in SYMBOLS else SYMBOLS[0]
    _ref_df = fetch_ohlcv(_ref_sym, TIMEFRAME, limit=SCAN_BARS)
    if not _check_candle_gate(_ref_df):
        log.info("  Skipping scan: no new 1h candle closed since last scan")
        # Still resolve existing picks (TP/SL check uses latest prices)
        # but skip new signal generation
        _ref_price = {}
        if not _ref_df.empty:
            _ref_price[_ref_sym] = float(_ref_df["close"].iloc[-1])
        still_active, newly_closed, resolution_msgs = resolve_picks(active, _ref_price, now)
        for msg in resolution_msgs:
            log.info(msg)
        closed.extend(newly_closed)
        save_json(still_active, "active_picks.json")
        save_json(closed, "closed_picks.json")
        _eff_max = degraded_max_picks if degraded_mode else MAX_CONCURRENT_PICKS
        _eff_min = degraded_min_conf if degraded_mode else MIN_CONFIDENCE
        _wtp = sum(1 for p in closed if str(p.get("status", "")).upper() == "WIN")
        _wec = sum(1 for p in closed if pick_is_economic_win(p))
        _tc = len(closed)
        _wr_tp = _wtp / _tc * 100 if _tc else 0.0
        _wr_ec = _wec / _tc * 100 if _tc else 0.0
        _pnl = 0.0
        for p in closed:
            v = p.get("realized_pnl_pct")
            if v is None:
                v = p.get("pnl_pct")
            try:
                _pnl += float(v)
            except (TypeError, ValueError):
                pass
        save_json(
            {
                "timestamp": now.isoformat(),
                "version": VERSION,
                "system": SYSTEM_NAME,
                "fear_greed": fng,
                "btc_dominance": round(btc_dom, 2),
                "active_picks": len(still_active),
                "closed_picks": _tc,
                "new_picks": 0,
                "resolved_this_scan": len(newly_closed),
                "top_gainers": 0,
                "win_rate": round(_wr_ec, 1),
                "win_rate_take_profit_hits_pct": round(_wr_tp, 1),
                "wins_economic": _wec,
                "wins_take_profit_status": _wtp,
                "total_pnl_pct": round(_pnl, 2),
                "symbols_scanned": 0,
                "validation_passed": validation_passed,
                "degraded_mode": degraded_mode,
                "validation_reason": val_status.get("reason", ""),
                "scan_note": "no_new_1h_candle",
                "max_concurrent_picks": _eff_max,
                "min_confidence_effective": _eff_min,
            },
            "scan_summary.json",
        )
        # Feedback loop — check even when no new candle (picks may have resolved)
        if newly_closed:
            try:
                from ml_battleground.shared.feedback_loop import check_and_trigger
                check_and_trigger()
                log.info("  Feedback loop check completed")
            except Exception as e:
                log.warning(f"  Feedback loop check failed (non-fatal): {e}")
        log.info("=== Scan complete (no new candle) ===")
        return


    # ── 5. Fetch data for all symbols ──
    latest_prices = {}
    symbol_data = {}
    for sym in SYMBOLS:
        df = fetch_ohlcv(sym, TIMEFRAME, limit=SCAN_BARS)
        if df.empty or len(df) < 200:
            log.warning(f"  {sym}: insufficient data ({len(df)} bars)")
            continue
            
        # Daily data for trend filter (MTF)
        df_daily = fetch_ohlcv(sym, "1d", limit=100)
        
        # Funding
        funding = fetch_funding_rate(sym, limit=100)
        if not funding.empty:
            df["funding"] = funding.reindex(df.index, method="ffill").fillna(0)
        else:
            df["funding"] = 0.0
        df["funding_z"] = 0.0
        roll_mean = df["funding"].rolling(48).mean()
        roll_std = df["funding"].rolling(48).std()
        mask = roll_std > 0
        df.loc[mask, "funding_z"] = (df.loc[mask, "funding"] - roll_mean[mask]) / roll_std[mask]
        df["funding_std_30d"] = df["funding"].rolling(min(720, len(df))).std().fillna(0)

        df = add_features(df, fng=fng, btc_dom=btc_dom, daily_df=df_daily)
        df["symbol"] = sym
        df["pair_id"] = SYMBOLS.index(sym)

        latest_prices[sym] = float(df["close"].iloc[-1])
        symbol_data[sym] = df
        time.sleep(0.05)

    log.info(f"  Fetched data for {len(symbol_data)} symbols")

    # ── 5. Resolve existing picks (TP/SL check) ──
    still_active, newly_closed, resolution_msgs = resolve_picks(active, latest_prices, now)
    for msg in resolution_msgs:
        log.info(msg)
    closed.extend(newly_closed)

    # ── 5b. Drift detection — feed closed picks to ADWIN monitor ──
    try:
        from ml_battleground.shared.drift_monitor import DriftMonitor
        _drift = DriftMonitor("mercury2", window_size=50)
        for cp in newly_closed:
            pred_prob = cp.get("confidence", 0.5)
            actual = 1.0 if pick_is_economic_win(cp) else 0.0
            if _drift.update(pred_prob, actual):
                log.warning("DRIFT DETECTED: Mercury2 model may be degrading — consider retrain")
        drift_status = _drift.get_status()
        if drift_status.get("drift_detected"):
            log.warning(f"  Drift state: {drift_status}")
    except Exception as e:
        log.debug(f"  Drift monitor skipped: {e}")

    # ── 6. Generate new signals: score universe, rank by prob, take top slots ──
    effective_max_picks = degraded_max_picks if degraded_mode else MAX_CONCURRENT_PICKS
    effective_min_conf = degraded_min_conf if degraded_mode else MIN_CONFIDENCE
    slots = max(0, effective_max_picks - len(still_active))
    pick_candidates: list[tuple[float, str, dict, pd.Series, pd.DataFrame]] = []

    for sym, df in symbol_data.items():
        if sym in active_symbols:
            continue

        row = df.iloc[-1]
        X = row[FEATURE_COLS].to_frame().T
        X = X.apply(pd.to_numeric, errors="coerce").fillna(0.0)

        prob = float(ensemble_predict(models, X)[0])

        log.info(
            f"  [{sym}] prob={prob:.4f} rsi={row.get('rsi_14', 0):.1f} "
            f"above_200={row.get('above_200', 0)} funding_z={row.get('funding_z', 0):.2f}"
        )

        if degraded_mode and prob < effective_min_conf:
            log.info(f"  [{sym}] SKIPPED — prob {prob:.4f} < degraded min_conf {effective_min_conf}")
            continue

        atr_avg_30 = float(df["atr"].tail(30).mean()) if "atr" in df.columns and len(df) >= 30 else 0.0

        trade = evaluate_signal(
            symbol=sym,
            price=float(row["close"]),
            atr_val=float(row["atr"]) if pd.notna(row.get("atr")) else 0,
            prob=prob,
            rsi=float(row["rsi_14"]) if pd.notna(row.get("rsi_14")) else 50,
            sma_200=float(row["sma_200"]) if pd.notna(row.get("sma_200")) else float(row["close"]),
            above_200=int(row.get("above_200", 0)),
            fng=fng,
            funding_z=float(row.get("funding_z", 0)),
            strategy="ensemble",
            atr_avg_30=atr_avg_30,
            vol_ratio=float(row.get("vol_ratio", 1.0)),
            daily_trend_up=int(row.get("daily_trend_up", -1)),
        )

        if trade:
            pick_candidates.append((prob, sym, trade, row, df))

    pick_candidates.sort(key=lambda t: t[0], reverse=True)
    new_picks = []
    for prob, sym, trade, row, df in pick_candidates[:slots]:
        _feat_snapshot = {}
        for col in df.columns:
            if col in ("symbol", "status", "timestamp"):
                continue
            val = row[col]
            if isinstance(val, (float, int, np.integer, np.floating)):
                if math.isnan(val) or math.isinf(val):
                    val = None
                else:
                    val = float(val) if isinstance(val, float) else int(val)
            else:
                val = str(val)
            _feat_snapshot[col] = val
        trade["features"] = _feat_snapshot
        trade["timestamp"] = now.isoformat()
        trade["timestamp_est"] = now.strftime("%Y-%m-%d %I:%M %p UTC")
        trade["system"] = SYSTEM_NAME
        trade["version"] = VERSION
        trade["status"] = "ACTIVE"
        if degraded_mode:
            trade["validation_warning"] = True
            trade["validation_reason"] = val_status.get("reason", "DSR/PSR validation failed")
            trade["dsr"] = val_status.get("dsr", 0)
            trade["psr"] = val_status.get("psr", 0)
        new_picks.append(trade)
        log.info(
            f"  NEW (ranked): {sym} {trade['direction']} | "
            f"conf={trade['confidence']:.3f} prob={prob:.4f} | "
            f"R:R={trade['risk_reward']} | TP={trade['take_profit']:.4f} SL={trade['stop_loss']:.4f}"
        )

    if slots == 0 and pick_candidates:
        log.info(
            "  Max concurrent picks (%d) already held; skipped %d lower-ranked candidates",
            effective_max_picks,
            len(pick_candidates),
        )
    elif len(pick_candidates) > slots:
        log.info(
            "  Ranked %d candidates by prob — kept top %d (slots=%d)",
            len(pick_candidates),
            len(new_picks),
            slots,
        )

    # ── 7. Top-gainer predictions ──
    top_gainers = []
    if top_model and symbol_data:
        # Build a single df with latest bar per symbol
        latest_rows = []
        for sym, df in symbol_data.items():
            row = df.iloc[[-1]].copy()
            row["symbol"] = sym
            latest_rows.append(row)
        latest_df = pd.concat(latest_rows)
        # Ensure pair_id and funding_std_30d
        latest_df["pair_id"] = latest_df["symbol"].apply(lambda s: SYMBOLS.index(s) if s in SYMBOLS else 0)
        for f in TOP_GAINER_FEATURES:
            if f not in latest_df.columns:
                latest_df[f] = 0.0

        top_df = predict_top_gainers(top_model, latest_df, TOP_GAINER_FEATURES)
        for _, row in top_df.iterrows():
            sym = row["symbol"]
            pred_ret = row.get("pred_next_ret", 0)
            top_gainers.append({
                "symbol": sym,
                "predicted_return_pct": round(float(pred_ret) * 100, 2),
                "current_price": latest_prices.get(sym, 0),
                "timestamp": now.isoformat(),
                "reason": (
                    f"LightGBM regressor predicts {pred_ret*100:.2f}% return over next 24h. "
                    f"Ranked by predicted next-day % return across all {len(SYMBOLS)} symbols. "
                    f"Features used: 12 causal indicators (momentum, RSI, MACD, ATR, BB width, "
                    f"volume ratio, 200-SMA trend, Fear & Greed, BTC dominance) + funding rate std."
                ),
            })
        log.info(f"  Top-{TOP_K} gainers: {[g['symbol'] for g in top_gainers]}")

    # ── 8. Merge and save ──
    all_active = still_active + new_picks
    # Update unrealized P&L for still-active picks
    for pick in all_active:
        sym = pick["symbol"]
        price = latest_prices.get(sym)
        if price:
            entry = pick["entry_price"]
            if pick.get("direction", "LONG") == "LONG":
                pick["unrealized_pnl_pct"] = round((price - entry) / entry * 100, 4)
            else:
                pick["unrealized_pnl_pct"] = round((entry - price) / entry * 100, 4)
            pick["current_price"] = price
            pick["last_checked"] = now.isoformat()

    save_json(all_active, "active_picks.json")
    save_json(closed, "closed_picks.json")
    save_json(top_gainers, "top_gainers.json")

    # ── 9. Scan summary ──
    wins_tp = sum(1 for p in closed if str(p.get("status", "")).upper() == "WIN")
    wins_ec = sum(1 for p in closed if pick_is_economic_win(p))
    total_closed = len(closed)
    wr_tp = wins_tp / total_closed * 100 if total_closed > 0 else 0
    wr_ec = wins_ec / total_closed * 100 if total_closed > 0 else 0
    total_pnl = 0.0
    for p in closed:
        v = p.get("realized_pnl_pct")
        if v is None:
            v = p.get("pnl_pct")
        try:
            total_pnl += float(v)
        except (TypeError, ValueError):
            pass

    summary = {
        "timestamp": now.isoformat(),
        "version": VERSION,
        "system": SYSTEM_NAME,
        "fear_greed": fng,
        "btc_dominance": round(btc_dom, 2),
        "active_picks": len(all_active),
        "closed_picks": total_closed,
        "new_picks": len(new_picks),
        "resolved_this_scan": len(newly_closed),
        "top_gainers": len(top_gainers),
        "win_rate": round(wr_ec, 1),
        "win_rate_take_profit_hits_pct": round(wr_tp, 1),
        "wins_economic": wins_ec,
        "wins_take_profit_status": wins_tp,
        "total_pnl_pct": round(total_pnl, 2),
        "symbols_scanned": len(symbol_data),
        "validation_passed": validation_passed,
        "degraded_mode": degraded_mode,
        "validation_reason": val_status.get("reason", ""),
        "max_concurrent_picks": effective_max_picks,
        "min_confidence_effective": effective_min_conf,
    }
    save_json(summary, "scan_summary.json")

    log.info(f"  Active: {len(all_active)} | Closed: {total_closed} | New: {len(new_picks)}")
    log.info(f"  Stats: WR_econ={wr_ec:.1f}% WR_tp_hit={wr_tp:.1f}% P&L={total_pnl:.2f}%")

    # ── 10. Discord notification ──
    if DISCORD_WEBHOOK and (new_picks or newly_closed):
        try:
            import requests
            embed = {
                "title": f"Mercury 2 — {len(new_picks)} new, {len(newly_closed)} resolved",
                "color": 0x00ff88 if new_picks else 0xff4444,
                "fields": [
                    {"name": "Active", "value": str(len(all_active)), "inline": True},
                    {"name": "Win rate (econ)", "value": f"{wr_ec:.1f}%", "inline": True},
                    {"name": "WR (TP status)", "value": f"{wr_tp:.1f}%", "inline": True},
                    {"name": "F&G", "value": str(fng), "inline": True},
                ],
            }
            if new_picks:
                picks_text = "\n".join(
                    f"**{p['symbol']}** {p['direction']} conf={p['confidence']:.3f}"
                    for p in new_picks[:5]
                )
                embed["fields"].append({"name": "New Picks", "value": picks_text})
            if top_gainers:
                tg_text = "\n".join(
                    f"**{g['symbol']}** {g['predicted_return_pct']:+.1f}%"
                    for g in top_gainers[:5]
                )
                embed["fields"].append({"name": "Top Gainers (24h)", "value": tg_text})

            import time as _dtime
            for _attempt in range(3):
                try:
                    _resp = requests.post(DISCORD_WEBHOOK, json={"embeds": [embed]}, timeout=8)
                    if _resp.status_code in (200, 204):
                        break
                    if _resp.status_code == 429:
                        _dtime.sleep(_resp.json().get("retry_after", 3))
                        continue
                    if _attempt < 2:
                        _dtime.sleep(2 * (_attempt + 1))
                        continue
                    break
                except Exception as e:
                    if _attempt == 2:
                        log.warning(f"  Discord notification failed after 3 attempts: {e}")
                    else:
                        _dtime.sleep(2 * (_attempt + 1))
        except Exception as e:
            log.warning(f"  Discord notification failed: {e}")

    # ── 11. Feedback loop — check for performance degradation ──
    try:
        from ml_battleground.shared.feedback_loop import check_and_trigger
        check_and_trigger()
        log.info("  Feedback loop check completed")
    except Exception as e:
        log.warning(f"  Feedback loop check failed (non-fatal): {e}")

    log.info("=== Scan complete ===")


if __name__ == "__main__":
    run_scan()
