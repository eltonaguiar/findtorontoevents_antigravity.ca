# -*- coding: utf-8 -*-
"""Mercury 2 — Weekly retraining pipeline.

Usage:
    python -m mercury2.trainer

Fetches 2 years of 1h candles for all symbols, trains:
  1. Three XGBoost classifiers (day-trade ensemble)
  2. LightGBM regressor (top-gainer ranking)
Validates with DSR/PSR gates, saves models to mercury2/models/.
"""

import logging, time, sys, json, numpy as np, pandas as pd
from datetime import datetime, timezone
from scipy import stats

from .config import (
    SYMBOLS, TIMEFRAME, HIST_DAYS, FEATURE_COLS,
    DSR_GATE, PSR_GATE, TARGET_SHARPE, DATA_DIR, MODEL_DIR,
    round_trip_cost, VERSION, ENSEMBLE_PARAMS,
)
from .data_fetcher import fetch_ohlcv, fetch_funding_rate, fetch_fear_greed, fetch_btc_dominance
from .features import add_features, add_labels_classification, add_labels_regression
from .ensemble import train_ensemble, save_ensemble, ensemble_predict
from .top_gainer import train_top_gainer, save_top_gainer, TOP_GAINER_FEATURES

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("mercury2.trainer")


def compute_psr(sharpe_hat: float, n: int, target: float = TARGET_SHARPE) -> float:
    """Probabilistic Sharpe Ratio (Bailey & Lopez de Prado, 2012)."""
    if n < 2:
        return 0.0
    se = np.sqrt((1 + sharpe_hat ** 2 / 2) / n)
    if se == 0:
        return 0.0
    return float(stats.norm.cdf((sharpe_hat - target) / se))


def compute_dsr(probs: np.ndarray, cost: float) -> float:
    """Deflated Sharpe Ratio approximation."""
    mean_p = probs.mean()
    if mean_p <= 0 or mean_p >= 1:
        return 0.0
    sharpe_hat = (mean_p - 0.5) / np.sqrt(mean_p * (1 - mean_p))
    n = len(probs)
    se = np.sqrt((1 + sharpe_hat ** 2 / 2) / max(1, n))
    if se == 0:
        return 0.0
    return float(stats.norm.cdf(sharpe_hat / se))


def run_training():
    """Full training pipeline."""
    now = datetime.now(timezone.utc)
    log.info(f"=== Mercury 2 Trainer v{VERSION} — {now.isoformat()} ===")

    # ── 1. Fetch data ──
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - HIST_DAYS * 24 * 60 * 60 * 1000
    fng = fetch_fear_greed()
    btc_dom = fetch_btc_dominance()
    log.info(f"  F&G={fng}, BTC dominance={btc_dom:.1f}%")

    frames = []
    for sym in SYMBOLS:
        log.info(f"  Fetching {sym}...")
        df = fetch_ohlcv(sym, TIMEFRAME, limit=1000, start_ms=start_ms)
        if df.empty:
            log.warning(f"  {sym}: no data, skipping")
            continue
        df["symbol"] = sym
        # Funding rates
        funding = fetch_funding_rate(sym, limit=1000)
        if not funding.empty:
            df["funding"] = funding.reindex(df.index, method="ffill")
        else:
            df["funding"] = 0.0
        df["funding_z"] = 0.0
        roll_mean = df["funding"].rolling(48).mean()
        roll_std = df["funding"].rolling(48).std()
        mask = roll_std > 0
        df.loc[mask, "funding_z"] = (df.loc[mask, "funding"] - roll_mean[mask]) / roll_std[mask]
        df["funding_std_30d"] = df["funding"].rolling(720).std().fillna(0)

        # Add features
        df = add_features(df, fng=fng, btc_dom=btc_dom)
        frames.append(df)
        time.sleep(0.1)

    if not frames:
        log.error("No data fetched, aborting training")
        sys.exit(1)

    data = pd.concat(frames)
    log.info(f"  Total rows: {len(data)} across {data['symbol'].nunique()} symbols")

    # ── 2. Pair ID encoding ──
    data["pair_id"] = pd.factorize(data["symbol"])[0]

    # ── 3. Train day-trade ensemble ──
    log.info("=== Training day-trade ensemble ===")
    clf_data = add_labels_classification(data.copy(), horizon=4)
    clf_data = clf_data.dropna(subset=["label"] + FEATURE_COLS)

    split = int(0.8 * len(clf_data))
    X_train = clf_data[FEATURE_COLS].iloc[:split]
    y_train = clf_data["label"].iloc[:split]
    X_test = clf_data[FEATURE_COLS].iloc[split:]
    y_test = clf_data["label"].iloc[split:]

    log.info(f"  Train: {len(X_train)}, Test: {len(X_test)}")
    models = train_ensemble(X_train, y_train, X_test, y_test)

    # Save as candidates first (not directly to production)
    save_ensemble(models, prefix="ensemble_candidate")

    # ── 4. Validate ensemble (DSR/PSR) — HARD GATE ──
    probs = ensemble_predict(models, X_test)
    mean_prob = probs.mean()
    sharpe_hat = (mean_prob - 0.5) / np.sqrt(mean_prob * (1 - mean_prob)) if 0 < mean_prob < 1 else 0
    dsr = compute_dsr(probs, round_trip_cost("BTCUSDT"))
    psr = compute_psr(sharpe_hat, len(probs))

    log.info(f"  Ensemble validation:")
    log.info(f"    Mean prob: {mean_prob:.4f}")
    log.info(f"    Sharpe={sharpe_hat:.3f}")
    log.info(f"    DSR={dsr:.3f} (gate={DSR_GATE}): {'PASS' if dsr >= DSR_GATE else 'FAIL'}")
    log.info(f"    PSR={psr:.3f} (gate={PSR_GATE}): {'PASS' if psr >= PSR_GATE else 'FAIL'}")

    ensemble_valid = dsr >= DSR_GATE and psr >= PSR_GATE

    # ── 4b. DSR hard gate (cross_aggregation shared module) ──
    dsr_gate_result = None
    try:
        from cross_aggregation.dsr_gate import validate_model_for_deployment
        pseudo_returns = (probs - 0.5).flatten()
        dsr_gate_result = validate_model_for_deployment(
            pseudo_returns, n_trials=len(SYMBOLS), min_dsr=DSR_GATE, min_psr=PSR_GATE
        )
        if dsr_gate_result["passed"]:
            log.info(f"    DSR Gate: PASSED (DSR={dsr_gate_result['dsr_pvalue']:.3f}, PSR={dsr_gate_result['psr_pvalue']:.3f})")
            ensemble_valid = True
        else:
            log.warning(f"    DSR Gate: FAILED -- {dsr_gate_result['reason']}")
            ensemble_valid = False
        dsr_gate_result["timestamp"] = now.isoformat()
        dsr_gate_result["model"] = "mercury2_ensemble"
        dsr_gate_result["version"] = VERSION
        with open(DATA_DIR / "validation_report.json", "w") as f:
            json.dump(dsr_gate_result, f, indent=2)
        log.info(f"    Validation report saved to data/validation_report.json")
    except Exception as e:
        log.warning(f"    DSR gate unavailable: {e}")
        # If gate module unavailable, fall back to local DSR/PSR check
        ensemble_valid = dsr >= DSR_GATE and psr >= PSR_GATE

    # Hard gate: promote candidate to production or keep previous
    import pathlib
    candidate_names = [f"ensemble_candidate_{name}.joblib" for name in ENSEMBLE_PARAMS]
    production_names = [f"ensemble_{name}.joblib" for name in ENSEMBLE_PARAMS]

    if ensemble_valid:
        for cand, prod in zip(candidate_names, production_names):
            cand_path = MODEL_DIR / cand
            prod_path = MODEL_DIR / prod
            if cand_path.exists():
                cand_path.replace(prod_path)
        log.info("    Validation PASSED -- ensemble promoted to production")
    elif any((MODEL_DIR / prod).exists() for prod in production_names):
        # Keep previous models, discard candidates
        for cand in candidate_names:
            cand_path = MODEL_DIR / cand
            if cand_path.exists():
                cand_path.unlink()
        log.warning("    Validation FAILED -- keeping previous ensemble models")
    else:
        # No previous models (bootstrap) — deploy candidate anyway
        for cand, prod in zip(candidate_names, production_names):
            cand_path = MODEL_DIR / cand
            prod_path = MODEL_DIR / prod
            if cand_path.exists():
                cand_path.replace(prod_path)
        log.warning("    Validation FAILED but no previous models -- deploying candidates (bootstrap)")

    # ── 5. Train top-gainer regressor ──
    log.info("=== Training top-gainer regressor ===")
    reg_data = add_labels_regression(data.copy(), horizon=24)
    reg_data = reg_data.dropna(subset=["next_ret"])
    # Ensure funding_std_30d exists
    for f in TOP_GAINER_FEATURES:
        if f not in reg_data.columns:
            reg_data[f] = 0.0
    reg_data = reg_data.dropna(subset=TOP_GAINER_FEATURES)

    split_r = int(0.8 * len(reg_data))
    X_train_r = reg_data[TOP_GAINER_FEATURES].iloc[:split_r]
    y_train_r = reg_data["next_ret"].iloc[:split_r]
    X_test_r = reg_data[TOP_GAINER_FEATURES].iloc[split_r:]
    y_test_r = reg_data["next_ret"].iloc[split_r:]

    # Clip extreme outlier labels to ±20% to prevent model from learning noise
    y_train_r = y_train_r.clip(-0.20, 0.20)
    y_test_r = y_test_r.clip(-0.20, 0.20)
    log.info(f"  Train: {len(X_train_r)}, Test: {len(X_test_r)}")
    log.info(f"  Label range after clip: [{y_train_r.min():.4f}, {y_train_r.max():.4f}]")
    reg_model = train_top_gainer(X_train_r, y_train_r, X_test_r, y_test_r)
    save_top_gainer(reg_model)

    # ── 6. Save training summary ──
    summary = {
        "timestamp": now.isoformat(),
        "version": VERSION,
        "symbols": len(SYMBOLS),
        "total_rows": len(data),
        "ensemble": {
            "train_size": len(X_train),
            "test_size": len(X_test),
            "mean_prob": round(float(mean_prob), 4),
            "sharpe": round(float(sharpe_hat), 3),
            "dsr": round(float(dsr), 3),
            "psr": round(float(psr), 3),
            "dsr_pass": bool(dsr >= DSR_GATE),
            "psr_pass": bool(psr >= PSR_GATE),
            "valid": bool(ensemble_valid),
        },
        "top_gainer": {
            "train_size": len(X_train_r),
            "test_size": len(X_test_r),
            "model": "lightgbm" if reg_model else "none",
        },
        "fear_greed": fng,
        "btc_dominance": round(float(btc_dom), 2),
    }
    with open(DATA_DIR / "training_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    log.info(f"  Training summary saved to data/training_summary.json")

    # ── 7. Reset feedback loop baseline after successful retrain ──
    if ensemble_valid:
        try:
            from ml_battleground.shared.feedback_loop import reset_baseline
            reset_baseline()
            log.info("  Feedback loop baseline reset after successful retrain")
        except Exception as e:
            log.warning(f"  Feedback loop baseline reset failed (non-fatal): {e}")

    log.info("=== Training complete ===")


if __name__ == "__main__":
    run_training()
