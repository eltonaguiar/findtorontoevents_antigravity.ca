#!/usr/bin/env python3
"""
Hyro ↔ QuanEngine bridge
========================
Runs QuanEngine regime classification (Hurst), strategy pools, ensemble consensus,
mode dispatch, and risk gate on OHLCV from the same stack as Hyro backtests
(`tools/hyro_backtest.fetch_candles` — parallel Binance mirrors + KuCoin + cache).

Writes JSON for the Hyro audit page and for cross-checking prop-firm logic.

From repo root:
  python tools/hyro_quan_bridge.py --symbols BTCUSDT ETHUSDT SOLUSDT BNBUSDT --save
  python tools/hyro_quan_bridge.py --days 45 -v
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_TOOLS = Path(__file__).resolve().parent
for _p in (_ROOT, _TOOLS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np
import pandas as pd

from hyro_backtest import HYRO, fetch_candles, parse_candles

from quan_engine import config
from quan_engine.regime_router import RegimeRouter
from quan_engine.strategy_pool import StrategyPool
from quan_engine.ensemble_layer import QuanEnsemble, Vote
from quan_engine.mode_dispatcher import ModeDispatcher

try:
    from quan_engine.risk_gate import RiskGate

    _HAS_RISK = True
except Exception:
    RiskGate = None  # type: ignore
    _HAS_RISK = False

try:
    from quan_engine.scanner import compute_atr_pct, fetch_fear_greed
except Exception:

    def fetch_fear_greed() -> int:
        return 50

    def compute_atr_pct(df: pd.DataFrame, period: int = 14) -> float:
        if len(df) < period + 1:
            return 0.0
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values
        tr = np.zeros(len(df))
        tr[0] = high[0] - low[0]
        for i in range(1, len(df)):
            tr[i] = max(
                high[i] - low[i],
                abs(high[i] - close[i - 1]),
                abs(low[i] - close[i - 1]),
            )
        atr = np.mean(tr[-period:])
        cp = close[-1]
        return (atr / cp * 100) if cp > 0 else 0.0


DEFAULT_OUT = _ROOT / "audit_dashboard" / "data" / "hyro_quan_bridge.json"


def candles_to_df(candles: list[dict]) -> pd.DataFrame:
    ts = pd.to_datetime([c["open_time"] for c in candles], unit="ms", utc=True)
    return pd.DataFrame(
        {
            "open": [float(c["open"]) for c in candles],
            "high": [float(c["high"]) for c in candles],
            "low": [float(c["low"]) for c in candles],
            "close": [float(c["close"]) for c in candles],
            "volume": [float(c["volume"]) for c in candles],
        },
        index=ts,
    )


def load_ohlcv(symbol: str, days: int) -> tuple[list[dict], pd.DataFrame | None]:
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(now.timestamp() * 1000)
    raw = fetch_candles(symbol, "1h", start_ms, end_ms)
    candles = parse_candles(raw)
    if len(candles) < config.HURST_WINDOW + 5:
        return candles, None
    return candles, candles_to_df(candles)


def run_symbol(
    symbol: str,
    df: pd.DataFrame,
    router: RegimeRouter,
    trending_pool: StrategyPool,
    mr_pool: StrategyPool,
    prop_pool: StrategyPool,
    ensemble: QuanEnsemble,
    dispatcher: ModeDispatcher,
    risk_gate,
    fng: int,
    btc_df: pd.DataFrame,
) -> dict:
    close_prices = df["close"].values
    regime = router.classify(close_prices)
    hurst_val = float(
        router._hurst._compute_hurst(close_prices[-config.HURST_WINDOW :])
    )

    fgc = prop_pool.strategies.get("fear_greed_contrarian")
    if fgc and hasattr(fgc, "set_fear_greed"):
        try:
            fgc.set_fear_greed(fng)
        except Exception:
            pass

    trending_votes = trending_pool.get_votes(df, symbol)
    mr_votes = mr_pool.get_votes(df, symbol)
    prop_votes = prop_pool.get_votes(df, symbol)

    if regime == "RANDOM":
        for v in trending_votes + mr_votes:
            if v["direction"] != "ABSTAIN":
                v["confidence"] = v.get("confidence", 0) * 0.7
    elif regime == "TRENDING":
        for v in mr_votes:
            if v["direction"] != "ABSTAIN":
                v["confidence"] = v.get("confidence", 0) * 0.8
    else:
        for v in trending_votes:
            if v["direction"] != "ABSTAIN":
                v["confidence"] = v.get("confidence", 0) * 0.8

    votes_raw = trending_votes + mr_votes + prop_votes
    votes = [
        Vote(
            strategy=v["strategy"],
            direction=v["direction"],
            confidence=v.get("confidence", 0),
            metadata={
                "entry_price": v.get("entry_price"),
                "take_profit": v.get("take_profit"),
                "stop_loss": v.get("stop_loss"),
                "reason": v.get("reason", ""),
            },
        )
        for v in votes_raw
    ]

    signal = ensemble.vote(votes)

    # --- Always compute vote breakdown & leading direction ---
    active_votes_list = [v for v in votes_raw if v["direction"] != "ABSTAIN"]
    buy_votes = [v for v in active_votes_list if v["direction"] == "BUY"]
    sell_votes = [v for v in active_votes_list if v["direction"] == "SELL"]
    total_active = len(active_votes_list)

    if len(buy_votes) >= len(sell_votes):
        leading_dir = "BUY"
        leading_votes = buy_votes
        opposing_votes = sell_votes
    else:
        leading_dir = "SELL"
        leading_votes = sell_votes
        opposing_votes = buy_votes

    raw_consensus = len(leading_votes) / total_active if total_active > 0 else 0
    avg_conf = (
        sum(v.get("confidence", 0) for v in leading_votes) / len(leading_votes)
        if leading_votes
        else 0
    )
    consensus_met = signal is not None

    # Per-strategy vote detail for the UI
    vote_detail = []
    for v in votes_raw:
        vote_detail.append({
            "strategy": v["strategy"],
            "direction": v["direction"],
            "confidence": round(v.get("confidence", 0), 4),
        })

    atr_pct = compute_atr_pct(df)
    atr_abs = float(df["close"].values[-1] * atr_pct / 100)
    entry_price = float(df["close"].values[-1])

    out: dict = {
        "regime": regime,
        "hurst": round(hurst_val, 4),
        "active_votes": total_active,
        "total_votes": len(votes_raw),
        "buy_votes": len(buy_votes),
        "sell_votes": len(sell_votes),
        "consensus_met": consensus_met,
        "vote_detail": vote_detail,
        "ensemble": {
            "direction": leading_dir if total_active > 0 else None,
            "consensus_pct": round(raw_consensus, 4),
            "avg_confidence": round(avg_conf, 4),
            "strategies_agreed": [v["strategy"] for v in leading_votes],
        },
        "trade_setup": None,
        "risk_gate": None,
        "current_price": entry_price,
        "atr_pct": round(atr_pct, 4),
        "atr_abs": round(atr_abs, 8),
        "hyro_account_usdt": HYRO["account_size"],
        "hyro_max_risk_usdt_per_trade": HYRO.get(
            "max_risk_usdt",
            HYRO["account_size"] * HYRO.get("max_risk_pct", 3) / 100,
        ),
    }

    if total_active == 0:
        out["ensemble"]["direction"] = None
        return out

    # F&G extremes block
    if fng <= 25 and leading_dir == "SELL":
        out["blocked"] = "fear_greed_extreme_fear_no_short"
    elif fng >= 75 and leading_dir == "BUY":
        out["blocked"] = "fear_greed_extreme_greed_no_long"

    # Always compute trade setup from leading direction (even if sub-threshold)
    setup = dispatcher.create_setup(
        symbol=symbol,
        direction=leading_dir,
        entry_price=entry_price,
        confidence=avg_conf,
        consensus_pct=raw_consensus,
        strategies_agreed=[v["strategy"] for v in leading_votes],
        atr=atr_abs,
        hurst_value=hurst_val,
        atr_pct=atr_pct,
    )

    # SL floor: live Hyro trades today showed 4/12 stop-outs in <60s because SL distances
    # (~0.44-0.83%) were sub-ATR on 1h crypto (ATR 1.3-1.9%). Enforce a minimum stop distance
    # of 1.2x ATR_pct so normal bar wicks don't auto-stop us. Widen TP proportionally to keep R:R.
    _sl_out = setup.stop_loss
    _tp_out = setup.take_profit
    _rr_out = setup.rr_ratio
    try:
        if entry_price and _sl_out is not None and atr_pct and atr_pct > 0:
            _floor_pct = max(1.2 * atr_pct / 100.0, 0.006)  # at least 1.2x ATR or 0.6% absolute
            _cur_sl_pct = abs(_sl_out - entry_price) / entry_price
            if _cur_sl_pct < _floor_pct:
                _is_long = str(setup.direction or "").upper() in ("LONG", "BUY")
                _new_sl = entry_price * (1 - _floor_pct) if _is_long else entry_price * (1 + _floor_pct)
                _risk = abs(entry_price - _new_sl)
                _reward_mult = setup.rr_ratio if setup.rr_ratio and setup.rr_ratio > 0 else 2.0
                _new_tp = entry_price + _reward_mult * _risk if _is_long else entry_price - _reward_mult * _risk
                _sl_out = _new_sl
                _tp_out = _new_tp
                _rr_out = _reward_mult
    except Exception:
        pass

    out["trade_setup"] = {
        "mode": setup.mode,
        "direction": setup.direction,
        "entry_price": setup.entry_price,
        "take_profit": _tp_out,
        "stop_loss": _sl_out,
        "trailing_stop": setup.trailing_stop,
        "rr_ratio": _rr_out,
        "max_hold_bars": setup.max_hold_bars,
        "atr": setup.atr,
        "sl_floor_applied": _sl_out != setup.stop_loss,
    }

    if risk_gate is None:
        out["risk_gate"] = {
            "approved": False,
            "reason": "RiskGate unavailable (import ml_battleground?)",
        }
        return out

    symbol_returns = {symbol: df["close"].pct_change().dropna().values}
    risk_result = risk_gate.evaluate(
        setup=setup,
        fear_greed=fng,
        btc_df=btc_df if btc_df is not None and not btc_df.empty else None,
        symbol_returns=symbol_returns,
    )
    out["risk_gate"] = {
        "approved": risk_result.get("approved", False),
        "position_size": risk_result.get("position_size"),
        "reason": risk_result.get("reason", ""),
        "health": risk_result.get("health"),
    }
    if risk_result.get("approved") and consensus_met:
        risk_gate.add_position(setup)

    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Hyro + QuanEngine bridge JSON")
    ap.add_argument(
        "--symbols",
        nargs="+",
        default=["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "XRPUSDT", "BNBUSDT", "DOGEUSDT", "LINKUSDT", "ADAUSDT", "DOTUSDT", "NEARUSDT", "SUIUSDT", "ARBUSDT", "APTUSDT", "PEPEUSDT"],
    )
    ap.add_argument("--days", type=int, default=45, help="Lookback days for 1h candles")
    ap.add_argument("--output", type=str, default=str(DEFAULT_OUT))
    ap.add_argument("--save", action="store_true", help="Write hyro_quan_bridge.json")
    ap.add_argument(
        "--allow-symbol-regression",
        action="store_true",
        help=(
            "Allow overwriting an existing bridge with fewer symbols than "
            "before. Default: refuse (prevents the 'bridge truncated to 1 "
            "symbol' incident from 2026-04-18)."
        ),
    )
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    router = RegimeRouter()
    ensemble = QuanEnsemble()
    dispatcher = ModeDispatcher()
    risk_gate = RiskGate() if _HAS_RISK else None

    trending_pool = StrategyPool("TRENDING")
    mr_pool = StrategyPool("MEAN_REVERSION")
    prop_pool = StrategyPool("PROP")

    fng = fetch_fear_greed()
    _, btc_df_full = load_ohlcv("BTCUSDT", args.days)
    btc_df = btc_df_full

    symbols_payload: dict[str, dict] = {}
    errors: dict[str, str] = {}

    for symbol in args.symbols:
        try:
            candles, df = load_ohlcv(symbol, args.days)
            if df is None or df.empty:
                errors[symbol] = f"insufficient_data bars={len(candles)}"
                symbols_payload[symbol] = {
                    "error": errors[symbol],
                    "bars": len(candles),
                }
                if args.verbose:
                    print(f"{symbol}: {errors[symbol]}")
                continue

            # NOTE: Do NOT reset risk_gate.active_positions between symbols.
            # The risk gate must see positions from ALL previously-processed symbols
            # to enforce portfolio-level risk limits (max concurrent positions,
            # correlation limits, etc.).  Resetting between symbols meant the
            # gate only ever saw one position at a time, defeating its purpose.

            sym_out = run_symbol(
                symbol,
                df,
                router,
                trending_pool,
                mr_pool,
                prop_pool,
                ensemble,
                dispatcher,
                risk_gate,
                fng,
                btc_df if btc_df is not None else df,
            )
            sym_out["bars"] = len(df)
            symbols_payload[symbol] = sym_out

            if args.verbose:
                ens = sym_out.get("ensemble") or {}
                print(
                    f"{symbol}: regime={sym_out['regime']} H={sym_out['hurst']} "
                    f"dir={ens.get('direction', '—')} "
                    f"consensus={ens.get('consensus_pct', 0):.0%} "
                    f"met={sym_out.get('consensus_met')} "
                    f"votes={sym_out.get('buy_votes', 0)}B/{sym_out.get('sell_votes', 0)}S "
                    f"risk={sym_out.get('risk_gate')}"
                )
        except Exception as e:
            errors[symbol] = str(e)
            symbols_payload[symbol] = {"error": str(e), "trace": traceback.format_exc()}
            if args.verbose:
                print(f"{symbol}: ERROR {e}")

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_source": "hyro_backtest.fetch_candles (Binance mirrors + KuCoin)",
        "lookback_days": args.days,
        "fear_greed": fng,
        "hyro_challenge_params": {
            "account_size": HYRO["account_size"],
            "max_risk_pct": HYRO["max_risk_pct"],
            "max_daily_loss_usdt": HYRO["max_daily_loss_usdt"],
            "max_overall_loss_usdt": HYRO["max_overall_loss_usdt"],
            "profit_target_phase1_usdt": HYRO["profit_target_phase1"],
        },
        "quan_config": {
            "hurst_window": config.HURST_WINDOW,
            "consensus_threshold": config.CONSENSUS_THRESHOLD,
            "min_avg_confidence": config.MIN_AVG_CONFIDENCE,
        },
        "risk_gate_loaded": _HAS_RISK,
        "symbols": symbols_payload,
        "errors": errors,
    }

    if args.save:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        # Symbol-regression guard (Tier-B #6, 2026-05-04 — per
        # reports/audit_unified_implementation_queue_2026_05_04.md).
        # Refuse to overwrite an existing bridge with FEWER symbols than
        # before unless --allow-symbol-regression is passed. This is the
        # root cause of the 'bridge truncated to BTCUSDT only since Apr 18'
        # incident: a partial run (e.g. `--symbols BTCUSDT`) silently
        # replaced a full 15-symbol bridge.
        new_symbol_count = len(payload.get("symbols", {}))
        if out_path.exists() and not getattr(args, "allow_symbol_regression", False):
            try:
                with open(out_path, "r", encoding="utf-8") as _f:
                    prev = json.load(_f)
                prev_count = len(prev.get("symbols", {}))
            except Exception:
                prev_count = 0
            if prev_count > 0 and new_symbol_count < prev_count:
                print(
                    f"REFUSED to overwrite {out_path}: would shrink symbols "
                    f"{prev_count} -> {new_symbol_count}. Pass "
                    f"--allow-symbol-regression to force.",
                    file=sys.stderr,
                )
                return 2
        # Atomic write: serialize fully to a temp file then rename. Prevents
        # committing a truncated JSON if the CI job is cancelled mid-write
        # (root cause of prior corrupt hyro_quan_bridge.json incidents).
        tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")

        # Coerce numpy scalars (bool_/int64/float64) so json can serialize.
        # Root cause of 2026-05-09 22:09 fail: numpy.bool_ leaked from a
        # downstream filter (e.g. ATR threshold check). Stdlib json default
        # raises TypeError for any np.* type. Cheap recursive walker covers
        # bool_, integer types, floats, ndarray, and falls through to repr
        # for unknowns so the write never crashes mid-payload.
        def _np_safe(o):  # noqa: ANN001
            try:
                import numpy as _np  # type: ignore
            except Exception:  # pragma: no cover
                _np = None  # type: ignore
            if _np is not None:
                if isinstance(o, _np.bool_):
                    return bool(o)
                if isinstance(o, _np.integer):
                    return int(o)
                if isinstance(o, _np.floating):
                    return float(o)
                if isinstance(o, _np.ndarray):
                    return o.tolist()
            return repr(o)

        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=_np_safe)
            f.flush()
            try:
                import os as _os
                _os.fsync(f.fileno())
            except Exception:
                pass
        tmp_path.replace(out_path)
        print(f"Wrote {out_path} ({new_symbol_count} symbols)")

    if args.verbose:
        print(json.dumps(payload, indent=2)[:6000])
    return 0 if not errors or len(errors) < len(args.symbols) else 1


if __name__ == "__main__":
    raise SystemExit(main())
