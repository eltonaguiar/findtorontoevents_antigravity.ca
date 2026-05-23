"""Main engine: orchestrates data fetch, prediction, risk filtering, and output.

Usage:
    python -m crypto_signal_engine.engine --mode scan     # Load models, generate picks
    python -m crypto_signal_engine.engine --mode retrain   # Train new models from scratch
"""
import sys
import json
import logging
import time
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from pathlib import Path

from . import config
from .data_fetcher import DataFetcher
from .features import add_features, create_labels
from .trainer import (
    train_xgb_ensemble, train_top_gainer_regressor,
    save_models, load_models, compute_cost,
)
from .risk_engine import evaluate_pick

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

EST = timezone(timedelta(hours=-5))


def now_est():
    return datetime.now(EST).strftime("%Y-%m-%d %H:%M:%S EST")


def now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def load_json(path):
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception:
        pass
    return []


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str))


class SignalEngine:
    """Orchestrates the full scan/retrain pipeline."""

    def __init__(self):
        self.fetcher = DataFetcher()
        self.xgb_models = None
        self.lgb_model = None
        self.features = config.FEATURES
        self.validation = {}

    def run_scan(self):
        """Scan mode: load models, fetch latest data, generate picks, track performance."""
        logger.info("=" * 60)
        logger.info("CRYPTO SIGNAL ENGINE — SCAN MODE")
        logger.info(f"Timestamp: {now_est()}")
        logger.info("=" * 60)

        # Load saved models
        self.xgb_models, self.lgb_model = load_models()
        if self.xgb_models is None:
            logger.warning("No saved models — running retrain first")
            self.run_retrain()
            return

        # Track performance of existing active picks FIRST
        self._track_performance()

        # Generate new day-trade picks
        picks = self._generate_daytrade_picks()

        # Merge into active picks (avoid duplicates)
        active_path = config.DATA_DIR / "active_picks.json"
        active = load_json(active_path)
        existing_keys = {f"{p['symbol']}_{p['direction']}" for p in active}

        # Emission gate: cooldown + daily cap (shared with alpha_engine).
        try:
            from alpha_engine.non_crypto_policy import check_emission_gates as _ceg
        except Exception:
            _ceg = None
        for pick in picks:
            key = f"{pick['symbol']}_{pick['direction']}"
            if key not in existing_keys:
                if _ceg is not None:
                    try:
                        _g = _ceg(str(pick.get("symbol") or ""))
                        if _g.get("blocked"):
                            logger.debug(
                                "emission_gate_blocked %s: %s",
                                pick.get("symbol"), _g.get("reason"),
                            )
                            continue
                    except Exception:
                        pass
                pick["opened_at"] = now_est()
                pick["opened_utc"] = now_utc()
                pick["status"] = "ACTIVE"
                active.append(pick)
                existing_keys.add(key)

        save_json(active_path, active)

        # Generate top-gainer predictions
        if self.lgb_model is not None:
            top_gainers = self._generate_top_gainers()
            save_json(config.DATA_DIR / "top_gainers.json", top_gainers)
        else:
            logger.info("No LightGBM model loaded — skipping top-gainers")

        # Save audit trail
        save_json(config.DATA_DIR / "audit.json", {
            "timestamp_est": now_est(),
            "timestamp_utc": now_utc(),
            "mode": "scan",
            "api_sources": self.fetcher.audit,
            "new_picks": len(picks),
            "total_active": len(active),
            "validation": self.validation,
        })

        self.fetcher.save_cache()

        logger.info(f"Scan complete: {len(picks)} new picks, {len(active)} total active")
        return active

    def run_retrain(self):
        """Retrain mode: fetch history, train all models, validate, save."""
        logger.info("=" * 60)
        logger.info("CRYPTO SIGNAL ENGINE — RETRAIN MODE")
        logger.info(f"Timestamp: {now_est()}")
        logger.info("=" * 60)

        # Fetch historical data for day-trade symbols
        frames = []
        for symbol in config.DAYTRADE_SYMBOLS:
            logger.info(f"Fetching {symbol}...")
            df = self.fetcher.fetch_ohlcv(symbol, config.TIMEFRAME, config.HIST_BARS)
            if df is not None:
                df["symbol"] = symbol
                frames.append(df)
            time.sleep(0.5)

        if not frames:
            logger.error("No data fetched — cannot train")
            return

        data = pd.concat(frames, ignore_index=False)

        # Add features
        fng = self.fetcher.fetch_fear_greed()
        btc_dom = self.fetcher.fetch_btc_dominance()

        # Fetch funding rates for each symbol
        for symbol in config.DAYTRADE_SYMBOLS:
            mask = data["symbol"] == symbol
            funding = self.fetcher.fetch_funding(symbol)
            data.loc[mask, "funding_rate_raw"] = funding

        data = add_features(data, fng_value=fng, btc_dom_value=btc_dom)
        data = create_labels(data)

        balance = data["label"].mean()
        logger.info(f"Training data: {len(data)} rows, "
                     f"label balance: {balance:.1%} positive / {1 - balance:.1%} negative")

        # Train XGBoost ensemble
        logger.info("Training XGBoost ensemble (3 models)...")
        self.xgb_models, self.features, self.validation = train_xgb_ensemble(data)
        save_models(self.xgb_models)

        # Train top-gainer regressor on ALL symbols
        logger.info("Training top-gainer regressor...")
        tg_frames = list(frames)  # start with what we already have
        for symbol in config.TOP_GAINER_SYMBOLS:
            if symbol in config.DAYTRADE_SYMBOLS:
                continue
            df = self.fetcher.fetch_ohlcv(symbol, config.TIMEFRAME, config.HIST_BARS)
            if df is not None:
                df["symbol"] = symbol
                tg_frames.append(df)
            time.sleep(0.3)

        if len(tg_frames) > 3:
            tg_data = pd.concat(tg_frames, ignore_index=False)
            tg_data["pair_id"] = pd.factorize(tg_data["symbol"])[0]
            tg_data = add_features(tg_data, fng_value=fng, btc_dom_value=btc_dom)

            self.lgb_model, _, precision = train_top_gainer_regressor(tg_data)
            save_models({}, self.lgb_model)
            self.validation["top_gainer_precision_at_5"] = round(precision, 4)

        # Save validation metrics
        self.validation["trained_at_est"] = now_est()
        self.validation["trained_at_utc"] = now_utc()
        self.validation["symbols_trained"] = len(frames)
        self.validation["total_rows"] = len(data)
        save_json(config.DATA_DIR / "validation.json", self.validation)

        self.fetcher.save_cache()
        logger.info("Retrain complete")

    def _generate_daytrade_picks(self):
        """Generate day-trade picks for core symbols."""
        picks = []
        fng = self.fetcher.fetch_fear_greed()
        btc_dom = self.fetcher.fetch_btc_dominance()

        for symbol in config.DAYTRADE_SYMBOLS:
            df = self.fetcher.fetch_ohlcv(symbol, config.TIMEFRAME, limit=250)
            if df is None:
                logger.warning(f"No data for {symbol} — skipping")
                continue

            funding = self.fetcher.fetch_funding(symbol)
            df["symbol"] = symbol
            df = add_features(df, fng_value=fng, btc_dom_value=btc_dom, funding_rate=funding)

            if df.empty:
                continue

            latest = df.iloc[-1]

            # Ensemble probability
            X = latest[self.features].to_frame().T.astype(float)
            try:
                probs = {
                    name: float(m.predict_proba(X)[:, 1][0])
                    for name, m in self.xgb_models.items()
                }
                prob = np.mean(list(probs.values()))
            except Exception as e:
                logger.error(f"Prediction failed for {symbol}: {e}")
                continue

            # Model agreement filter: at least 2/3 models must agree on direction
            bullish_votes = sum(1 for v in probs.values() if v > 0.5)
            bearish_votes = len(probs) - bullish_votes
            if bullish_votes < 2 and bearish_votes < 2:
                logger.info(f"  {symbol}: no consensus (votes: {bullish_votes}B/{bearish_votes}S)")
                continue

            # If majority says bearish but ensemble avg > 0.5, trust the majority
            if bearish_votes >= 2 and prob > 0.5:
                logger.info(f"  {symbol}: majority bearish ({bearish_votes}/3) overrides avg {prob:.2%}")
                prob = 1 - prob

            # Risk engine evaluation
            pick = evaluate_pick(latest, prob)
            if pick:
                pick["model_votes"] = {k: round(v, 4) for k, v in probs.items()}
                pick["btc_dom"] = round(btc_dom, 2)
                pick["pick_reason"] = self._build_pick_reason(pick, probs)
                picks.append(pick)
                logger.info(
                    f"PICK: {pick['direction']} {symbol} @ ${pick['entry']:.2f} "
                    f"(conf={pick['confidence']:.1%}, TP=${pick['tp']:.2f}, SL=${pick['sl']:.2f})"
                )
            else:
                logger.info(f"  {symbol}: no signal (prob={prob:.2%}, guards not met)")

        return picks

    def _build_pick_reason(self, pick, model_votes):
        """Build a human-readable explanation for why this pick was generated."""
        lines = []
        lines.append(f"Signal: {pick['direction']} {pick['symbol']}")
        lines.append(f"")
        lines.append(f"WHY THIS PICK:")
        lines.append(f"  Direction: {pick['direction_reason']}")
        lines.append(f"")
        lines.append(f"MODEL VOTES (3 XGBoost classifiers):")
        for name, vote in model_votes.items():
            lines.append(f"  {name}: {vote:.1%} probability of price increase")
        lines.append(f"  Ensemble average: {pick['confidence']:.1%}")
        lines.append(f"")
        lines.append(f"RISK MANAGEMENT:")
        lines.append(f"  Entry: ${pick['entry']:.2f}")
        lines.append(f"  TP (Take Profit): ${pick['tp']:.2f} = entry {'- ' if pick['direction'] == 'SHORT' else '+ '}{config.TP_ATR_MULT}x ATR")
        lines.append(f"  SL (Stop Loss): ${pick['sl']:.2f} = entry {'+ ' if pick['direction'] == 'SHORT' else '- '}{config.SL_ATR_MULT}x ATR")
        lines.append(f"  ATR (Average True Range): ${pick['atr']:.2f} (14-period volatility)")
        lines.append(f"  Position size: {pick['size']:.4f} units (1% equity risk)")
        lines.append(f"")
        lines.append(f"MARKET CONTEXT:")
        lines.append(f"  RSI (Relative Strength Index): {pick['rsi']:.1f}")
        lines.append(f"  F&G (Fear & Greed Index): {pick['fng']} {'(Extreme Fear)' if pick['fng'] < 20 else '(Fear)' if pick['fng'] < 40 else '(Neutral)' if pick['fng'] < 60 else '(Greed)' if pick['fng'] < 80 else '(Extreme Greed)'}")
        lines.append(f"  Funding Z-score: {pick['funding_z']:.3f} (leverage sentiment)")
        lines.append(f"  Above 200 SMA: {'Yes (bullish trend)' if pick['above_200_sma'] else 'No (below trend)'}")
        lines.append(f"")
        lines.append(f"GUARDS PASSED ({pick['guards_count']}/5):")
        for g in pick["guards_passed"]:
            lines.append(f"  ✓ {g}")
        return "\n".join(lines)

    def _generate_top_gainers(self):
        """Predict top-5 gainers from all symbols."""
        fng = self.fetcher.fetch_fear_greed()
        btc_dom = self.fetcher.fetch_btc_dominance()

        rows = []
        for symbol in config.TOP_GAINER_SYMBOLS:
            df = self.fetcher.fetch_ohlcv(symbol, config.TIMEFRAME, limit=250)
            if df is None:
                continue
            df["symbol"] = symbol
            df["pair_id"] = config.TOP_GAINER_SYMBOLS.index(symbol)
            df = add_features(df, fng_value=fng, btc_dom_value=btc_dom)
            if not df.empty:
                rows.append(df.iloc[-1])
            time.sleep(0.2)

        if not rows:
            return []

        latest = pd.DataFrame(rows)

        # 2026-04-17: align prediction features to MODEL's saved feature_name()
        # rather than current config.TOP_GAINER_FEATURES. Schema drift was
        # silently skipping predictions: "number of features in data (16) is
        # not the same as it was in training data (13)" — TOP_GAINER_FEATURES
        # grew to 16 (15 base + pair_id) but the saved model has 13. Until the
        # model is retrained, predict using exactly the features the model knows.
        model_feats = None
        try:
            if hasattr(self.lgb_model, "feature_name"):
                _mf = self.lgb_model.feature_name()
                if _mf and isinstance(_mf, list):
                    model_feats = _mf
        except Exception:
            model_feats = None

        if model_feats:
            available_feats = [f for f in model_feats if f in latest.columns]
            missing = [f for f in model_feats if f not in latest.columns]
            if missing:
                logger.warning(f"Top-gainer model expects features not in current data: {missing}")
                return []
        else:
            # Fallback to config when feature_name introspection unavailable
            available_feats = [f for f in config.TOP_GAINER_FEATURES if f in latest.columns]

        try:
            X_pred = latest[available_feats].astype(float)
            if hasattr(self.lgb_model, "predict"):
                preds = self.lgb_model.predict(X_pred)
            else:
                preds = self.lgb_model.predict(X_pred.values)
        except Exception as e:
            logger.error(f"Top-gainer prediction failed: {e}")
            return []

        # Clamp predictions to realistic range (-50% to +50% daily)
        preds = np.clip(preds, -0.5, 0.5)
        latest["predicted_return"] = preds
        top5 = latest.nlargest(5, "predicted_return")

        gainers = []
        for _, row in top5.iterrows():
            gainers.append({
                "rank": len(gainers) + 1,
                "symbol": row["symbol"],
                "predicted_return_pct": round(float(row["predicted_return"]) * 100, 2),
                "current_price": round(float(row["close"]), 6),
                "rsi": round(float(row.get("rsi_14", 0)), 1),
                "above_200_sma": bool(row.get("above_200", 0)),
                "vol_ratio": round(float(row.get("vol_ratio", 1)), 2),
                "timestamp_est": now_est(),
                "timestamp_utc": now_utc(),
                "reason": (
                    f"LightGBM regressor predicts {float(row['predicted_return']) * 100:.2f}% "
                    f"next-day return. RSI={float(row.get('rsi_14', 0)):.1f}, "
                    f"{'above' if row.get('above_200', 0) else 'below'} 200 SMA, "
                    f"volume {float(row.get('vol_ratio', 1)):.1f}x average."
                ),
            })

        return gainers

    def _track_performance(self):
        """Update active picks with current P&L, close TP/SL hits."""
        active_path = config.DATA_DIR / "active_picks.json"
        closed_path = config.DATA_DIR / "closed_picks.json"

        active = load_json(active_path)
        closed = load_json(closed_path)

        if not active:
            return

        symbols = list(set(p["symbol"] for p in active))
        prices = self.fetcher.fetch_current_prices(symbols)

        still_active = []
        for pick in active:
            symbol = pick["symbol"]
            current = prices.get(symbol)
            if current is None:
                still_active.append(pick)
                continue

            entry = pick["entry"]
            tp = pick["tp"]
            sl = pick["sl"]
            is_short = pick.get("direction") == "SHORT"

            # P&L calculation (inverted for SHORT)
            SL_BUFFER = 0.005  # 0.5% early trigger to prevent overshoot
            if is_short:
                pnl_pct = round((entry - current) / entry * 100, 2)
                tp_hit = current <= tp
                sl_hit = current >= sl * (1 - SL_BUFFER)
            else:
                pnl_pct = round((current - entry) / entry * 100, 2)
                tp_hit = current >= tp
                sl_hit = current <= sl * (1 + SL_BUFFER)

            pick["current_price"] = current
            pick["pnl_pct"] = pnl_pct
            pick["pnl_usd"] = round(
                pick.get("size", 0) * abs(current - entry) * (1 if pnl_pct > 0 else -1), 2
            )
            pick["last_checked"] = now_est()

            if tp_hit:
                pick["status"] = "TP_HIT"
                pick["closed_at"] = now_est()
                pick["exit_price"] = tp
                pick["result"] = "WIN"
                # Recalculate PnL using actual exit price (tp), not current price
                if is_short:
                    pick["pnl_pct"] = round((entry - tp) / entry * 100, 2)
                else:
                    pick["pnl_pct"] = round((tp - entry) / entry * 100, 2)
                pick["pnl_usd"] = round(
                    pick.get("size", 0) * abs(tp - entry) * (1 if pick["pnl_pct"] > 0 else -1), 2
                )
                closed.append(pick)
                logger.info(f"TP HIT: {symbol} {pick['direction']} → +{pick['pnl_pct']}%")
            elif sl_hit:
                pick["status"] = "SL_HIT"
                pick["closed_at"] = now_est()
                pick["exit_price"] = sl
                pick["result"] = "LOSS"
                # Recalculate PnL using actual exit price (sl), not current price
                if is_short:
                    pick["pnl_pct"] = round((entry - sl) / entry * 100, 2)
                else:
                    pick["pnl_pct"] = round((sl - entry) / entry * 100, 2)
                pick["pnl_usd"] = round(
                    pick.get("size", 0) * abs(sl - entry) * (1 if pick["pnl_pct"] > 0 else -1), 2
                )
                closed.append(pick)
                logger.info(f"SL HIT: {symbol} {pick['direction']} → {pick['pnl_pct']}%")
            else:
                still_active.append(pick)

        save_json(active_path, still_active)
        save_json(closed_path, closed[-500:])


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Crypto Signal Engine")
    parser.add_argument(
        "--mode", choices=["scan", "retrain"], default="scan",
        help="scan = load models + generate picks; retrain = train new models",
    )
    args = parser.parse_args()

    engine = SignalEngine()
    if args.mode == "retrain":
        engine.run_retrain()
    else:
        engine.run_scan()


if __name__ == "__main__":
    main()
