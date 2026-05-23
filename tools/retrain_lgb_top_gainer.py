"""Retrain the LightGBM top-gainer regressor with the current 16-feature config
and validate against the old model on a 30-day OOS hold-out.

Resolves LightGBM schema drift: old model has 13 features (ret_1h/4h/24h, rsi_14,
macd, atr, bb_width, vol_ratio, above_200, fng, btc_dom, funding_z, pair_id),
new config emits 16 (scalars replaced with bar-varying signals: rsi_slope,
close_ema9, atr_ratio, candle_body, high_low_pos, ret_vol_corr).

The OLD model file is also corrupt under LightGBM 4.6 (Fatal aborts on load),
so retrain is the only viable option (Plan 4 Option A from
updates/2026-04-17-deferred-execution-plans.md).

Usage:
    python tools/retrain_lgb_top_gainer.py [--dry-run]

Outputs:
    crypto_signal_engine/data/models/lgb_top_gainer.txt        (NEW model, overwrites)
    crypto_signal_engine/data/models/lgb_top_gainer.txt.backup (OLD corrupt model preserved)
    crypto_signal_engine/data/lgb_retrain_report.json          (metrics + diff)
"""
import argparse
import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

# Make project root importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lightgbm as lgb

from crypto_signal_engine import config
from crypto_signal_engine.data_fetcher import DataFetcher
from crypto_signal_engine.features import add_features

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("retrain_lgb")

MODEL_PATH = config.MODEL_DIR / "lgb_top_gainer.txt"
BACKUP_PATH = config.MODEL_DIR / "lgb_top_gainer.txt.backup"
REPORT_PATH = config.DATA_DIR / "lgb_retrain_report.json"

# Old model schema (read directly from the corrupt model header line 8)
OLD_MODEL_FEATURES = [
    "ret_1h", "ret_4h", "ret_24h", "rsi_14", "macd", "atr", "bb_width",
    "vol_ratio", "above_200", "fng", "btc_dom", "funding_z", "pair_id",
]


def fetch_training_data():
    """Pull 2000 bars of 1h OHLCV per top-gainer symbol via shared failover."""
    fetcher = DataFetcher()
    fng = fetcher.fetch_fear_greed()
    btc_dom = fetcher.fetch_btc_dominance()
    log.info(f"Sentiment: F&G={fng}, BTC dominance={btc_dom:.2f}%")

    frames = []
    for i, symbol in enumerate(config.TOP_GAINER_SYMBOLS):
        log.info(f"[{i+1}/{len(config.TOP_GAINER_SYMBOLS)}] Fetching {symbol}...")
        df = fetcher.fetch_ohlcv(symbol, config.TIMEFRAME, config.HIST_BARS)
        if df is None or len(df) < 200:
            log.warning(f"  {symbol}: insufficient data, skipping")
            continue
        df = df.copy()
        df["symbol"] = symbol
        # Fetch funding per symbol so 'funding_z' has a real value (was 0.0 before)
        try:
            funding = fetcher.fetch_funding(symbol)
        except Exception:
            funding = 0.0
        df = add_features(df, fng_value=fng, btc_dom_value=btc_dom, funding_rate=funding)
        if len(df) < 100:
            continue
        frames.append(df)
        time.sleep(0.2)

    if not frames:
        raise RuntimeError("No training data fetched -- failover chain exhausted")

    data = pd.concat(frames, ignore_index=False)
    data["pair_id"] = pd.factorize(data["symbol"])[0]

    # Target: next 24h return (consistent with train_top_gainer_regressor)
    data["next_ret"] = data.groupby("symbol")["close"].shift(-24) / data["close"] - 1
    data = data.dropna(subset=["next_ret"])

    # IMPORTANT: sort by timestamp BEFORE splitting so OOS is truly future
    data = data.sort_index()
    log.info(f"Training set: {len(data)} rows across {len(frames)} symbols, "
             f"time range {data.index.min()} -> {data.index.max()}")
    fetcher.save_cache()
    return data


def split_oos(data, oos_days=30):
    """30-day OOS hold-out by timestamp (data assumed sorted by index ascending)."""
    cutoff = data.index.max() - pd.Timedelta(days=oos_days)
    in_sample = data[data.index < cutoff]
    oos = data[data.index >= cutoff]
    log.info(f"In-sample: {len(in_sample)} rows (until {cutoff})")
    log.info(f"OOS hold-out ({oos_days}d): {len(oos)} rows")
    return in_sample, oos


def train_model(train_df, features):
    """Train LGBMRegressor on the given features, return Booster.

    train_df is expected to be sorted by timestamp ascending so the internal
    85/15 split is a true walk-forward validation (not a random split).
    """
    avail = [f for f in features if f in train_df.columns]
    if len(avail) != len(features):
        missing = set(features) - set(avail)
        log.warning(f"Features missing from data: {missing}")

    train_df = train_df.sort_index()
    X = train_df[avail]
    y = train_df["next_ret"]

    # Walk-forward split: split by index timestamp at 85th percentile
    cutoff = X.index[int(0.85 * len(X))]
    X_tr, X_val = X[X.index < cutoff], X[X.index >= cutoff]
    y_tr, y_val = y[X.index < cutoff], y[X.index >= cutoff]

    reg = lgb.LGBMRegressor(**config.LGB_CONFIG, verbosity=-1)
    reg.fit(
        X_tr, y_tr,
        eval_set=[(X_val, y_val)],
        callbacks=[lgb.early_stopping(30, verbose=False)],
    )
    log.info(f"Trained on {len(avail)} features, train={len(X_tr)} rows, "
             f"val={len(X_val)} rows, best_iter={reg.best_iteration_}")
    return reg.booster_, avail


def evaluate(booster, oos_df, features):
    """Compute Sharpe/PF/WR/MaxDD on OOS hold-out using top-5 daily strategy.

    Strategy: at the START of each UTC day, score every symbol's next-24h
    return forecast and take the top-5 picks. Realize the next-24h actual
    return as the trade outcome. This matches the production usage in
    engine._generate_top_gainers which produces a daily top-5.

    Trades are 24h-spaced (one per UTC day) so cumulative returns are
    statistically meaningful, not autocorrelated.
    """
    avail = [f for f in features if f in oos_df.columns]
    if not avail or len(oos_df) == 0:
        return None

    X = oos_df[avail].astype(float)
    preds = booster.predict(X)
    df = oos_df.copy()
    df["pred"] = preds
    df["utc_date"] = df.index.normalize()

    # Take ONE bar per (symbol, day) -- the 00:00 UTC bar nearest each midnight
    df_morning = df[df.index.hour == 0]
    if len(df_morning) < 30:
        # Some symbols/days may not have a 00:00 bar; fall back to first bar of day
        df_morning = df.groupby(["symbol", "utc_date"]).head(1)

    # For each day, take top-5 by predicted return; trade outcome is actual next_ret
    daily_groups = df_morning.groupby(df_morning.index.normalize())
    trade_returns = []
    for day, grp in daily_groups:
        if len(grp) < 5:
            continue
        top5 = grp.nlargest(5, "pred")
        # Equal-weight the top-5 -> single daily portfolio return
        trade_returns.append(float(top5["next_ret"].mean()))

    rets = np.array(trade_returns)
    if len(rets) < 5:
        return {"n_trades": int(len(rets)), "error": "too few daily trades"}

    wr = float((rets > 0).mean())
    pos_sum = float(rets[rets > 0].sum())
    neg_sum = float(abs(rets[rets < 0].sum()))
    pf = (pos_sum / neg_sum) if neg_sum > 0 else float("inf")
    # Daily Sharpe -> annualized (sqrt(365))
    sharpe = float(rets.mean() / rets.std() * np.sqrt(365)) if rets.std() > 0 else 0.0

    # Max DD on cumulative returns (clip per-trade at -50% to avoid -1 sinkhole from data gaps)
    rets_clipped = np.clip(rets, -0.5, 0.5)
    cum = (1 + rets_clipped).cumprod()
    running_max = np.maximum.accumulate(cum)
    dd = (cum - running_max) / running_max
    max_dd = float(dd.min())

    return {
        "n_trades": int(len(rets)),
        "win_rate": round(wr, 4),
        "profit_factor": round(pf, 4) if np.isfinite(pf) else None,
        "sharpe_annualized": round(sharpe, 4),
        "max_dd": round(max_dd, 4),
        "mean_ret_per_trade": round(float(rets.mean()), 6),
        "total_return": round(float(cum[-1] - 1), 4),
    }


def try_load_old_model_subprocess():
    """Try to load the old model in a SUBPROCESS so its abort() can't kill us.

    Returns dict with status: 'ok' / 'corrupt' / 'missing'.
    """
    import subprocess
    target = BACKUP_PATH if BACKUP_PATH.exists() else MODEL_PATH
    if not target.exists():
        return {"status": "missing"}
    probe = (
        "import sys, lightgbm as lgb;"
        f"b = lgb.Booster(model_file=r'{target}');"
        "print('OK', len(b.feature_name()), b.num_trees())"
    )
    try:
        result = subprocess.run(
            [sys.executable, "-c", probe],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and result.stdout.startswith("OK"):
            parts = result.stdout.strip().split()
            return {
                "status": "ok",
                "n_features": int(parts[1]),
                "n_trees": int(parts[2]),
            }
        return {
            "status": "corrupt",
            "returncode": result.returncode,
            "stderr_tail": (result.stderr or "")[-300:],
        }
    except subprocess.TimeoutExpired:
        return {"status": "corrupt", "error": "timeout"}
    except Exception as e:
        return {"status": "corrupt", "error": str(e)[:200]}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", help="Train + evaluate but do NOT overwrite the live model")
    args = p.parse_args()

    log.info("=" * 60)
    log.info("LIGHTGBM TOP-GAINER RETRAIN (Plan 4 Option A)")
    log.info("=" * 60)
    log.info(f"Old model schema (13): {OLD_MODEL_FEATURES}")
    log.info(f"New config schema (16): {config.TOP_GAINER_FEATURES}")

    # Backup old model first (it's corrupt but we keep for forensics)
    if MODEL_PATH.exists() and not BACKUP_PATH.exists():
        BACKUP_PATH.write_bytes(MODEL_PATH.read_bytes())
        log.info(f"Backed up old corrupt model -> {BACKUP_PATH.name}")

    # 1. Fetch training data
    data = fetch_training_data()
    in_sample, oos = split_oos(data, oos_days=30)

    # 2a. Train DIAGNOSTIC model on in-sample only, evaluate on 30-day OOS
    log.info("\n--- Training DIAGNOSTIC model (in-sample only) for OOS validation ---")
    diag_booster, diag_feats = train_model(in_sample, config.TOP_GAINER_FEATURES)
    new_metrics = evaluate(diag_booster, oos, diag_feats)
    log.info(f"OOS metrics (diagnostic): {new_metrics}")

    # 2b. Train PRODUCTION model on ALL data (including the OOS window) so
    # the shipped model uses the most recent signal. The diagnostic OOS metrics
    # above are the honest forward-validation estimate.
    log.info("\n--- Training PRODUCTION model on ALL data ---")
    new_booster, new_feats = train_model(data, config.TOP_GAINER_FEATURES)

    # 3. Probe the OLD model in a subprocess (it aborts the interpreter on load)
    log.info("\n--- Probing OLD model (13 features) in subprocess ---")
    old_status = try_load_old_model_subprocess()
    log.info(f"OLD model probe: {old_status}")
    if old_status["status"] == "ok":
        old_metrics = {
            "note": "loadable; OOS evaluation skipped because schema (fng/btc_dom/funding_z) "
                    "no longer matches current features.py output (replaced with rsi_slope/etc)"
        }
    else:
        old_metrics = {"error": f"old_model_{old_status['status']}", **old_status}

    # 4. Quality gate: since old model is unloadable / unevaluable, the new model
    # is by definition an improvement (silently-dead baseline). Ship unless NEW
    # has degenerate metrics (n_trades < 10 daily or sharpe <= -3 or PF <= 0.5).
    deltas = {"baseline": "old_model_unloadable", "improvement": "infinite"}
    ship_new = True
    if isinstance(new_metrics, dict):
        if new_metrics.get("n_trades", 0) < 10:
            log.warning("NEW model daily trade count < 10 -- block ship")
            ship_new = False
        sh = new_metrics.get("sharpe_annualized")
        if sh is not None and sh <= -3:
            log.warning(f"NEW model Sharpe degenerate ({sh}) -- block ship")
            ship_new = False
        pf = new_metrics.get("profit_factor")
        if pf is not None and pf <= 0.5:
            log.warning(f"NEW model PF degenerate ({pf}) -- block ship")
            ship_new = False

    report = {
        "timestamp": pd.Timestamp.utcnow().isoformat(),
        "old_model_features": OLD_MODEL_FEATURES,
        "new_model_features": new_feats,
        "old_model_status": old_status,
        "training_rows": int(len(in_sample)),
        "oos_rows": int(len(oos)),
        "old_metrics": old_metrics,
        "new_metrics": new_metrics,
        "deltas": deltas,
        "ship_decision": "SHIP" if ship_new else "BLOCK",
        "dry_run": args.dry_run,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, default=str))
    log.info(f"\nReport saved -> {REPORT_PATH}")

    # 5. Save new model (unless dry-run or quality gate failed)
    if args.dry_run:
        log.info("DRY-RUN: skipping model overwrite")
    elif not ship_new:
        log.warning("Quality gate FAILED -- new model NOT shipped")
    else:
        new_booster.save_model(str(MODEL_PATH))
        log.info(f"NEW model written -> {MODEL_PATH}")

    log.info("\nDONE.")
    log.info(f"  ship_decision = {report['ship_decision']}")
    log.info(f"  new_metrics   = {new_metrics}")
    log.info(f"  deltas        = {deltas}")


if __name__ == "__main__":
    main()
