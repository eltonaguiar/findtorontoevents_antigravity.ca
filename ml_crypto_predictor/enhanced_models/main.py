#!/usr/bin/env python3
"""
Enhanced ML Crypto Predictor — Main Entry Point
=================================================
Orchestrates training, A/B testing, regime detection, and live prediction.

Usage:
  python -m ml_crypto_predictor.enhanced_models.main train          # Train all models
  python -m ml_crypto_predictor.enhanced_models.main train-quick    # Train 1h only
  python -m ml_crypto_predictor.enhanced_models.main predict        # Run live scan
  python -m ml_crypto_predictor.enhanced_models.main regime         # Detect regime
  python -m ml_crypto_predictor.enhanced_models.main status         # Show A/B test status
  python -m ml_crypto_predictor.enhanced_models.main full           # Train + predict
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime, timezone

from .config import CRYPTO_PAIRS, TIMEFRAMES, MODELS_DIR, RESULTS_DIR, AB_TEST_DIR


def cmd_train(quick: bool = False, massive: bool = False):
    """Train all model variants across pairs and timeframes."""
    from .model_trainer import train_full_suite
    
    if massive:
        # ALL 30 pairs × ALL 5 timeframes × 4 variants = 600 models
        pairs = None       # All 30
        timeframes = None  # All 5
        print("🔥 MASSIVE TRAINING MODE: 30 pairs × 5 timeframes × 4 variants = 600 models")
    elif quick:
        # Top 10 pairs × 3 key timeframes = 120 models  
        pairs = CRYPTO_PAIRS[:10]
        timeframes = ["1h", "4h", "1d"]
    else:
        # All 30 pairs × 3 key timeframes = 360 models
        pairs = None       # All 30
        timeframes = ["1h", "4h", "1d"]
    
    summary = train_full_suite(pairs=pairs, timeframes=timeframes)
    
    print("\n✅ Training complete!")
    print(f"   Models trained: {summary.get('total_models', 0)}")
    print(f"   A/B winner: {summary.get('ab_test_winner', 'N/A')}")
    return summary


def cmd_predict():
    """Run live prediction scan."""
    from .live_predictor import run_live_scan
    
    result = run_live_scan()
    
    picks = result.get("active_picks", [])
    print(f"\n✅ Scan complete: {len(picks)} picks generated")
    return result


def cmd_regime():
    """Detect and report current market regime."""
    from .regime_detector import RegimeDetector
    from .data_fetcher import fetch_klines
    
    detector = RegimeDetector()
    
    # Train on BTC daily data if model doesn't exist
    if detector.model is None:
        print("Training regime detector on BTC daily data...")
        btc_df = fetch_klines("BTCUSDT", "1d", 365)
        if not btc_df.empty:
            detector.train(btc_df)
    
    # Detect current regime
    btc_df = fetch_klines("BTCUSDT", "1d", 100)
    regime = detector.detect_current_regime(btc_df)
    
    print(f"\n{'='*50}")
    print(f"CURRENT MARKET REGIME")
    print(f"{'='*50}")
    print(f"  Regime: {regime['regime_label']}")
    print(f"  Confidence: {regime['confidence']:.1%}")
    if regime.get('features'):
        print(f"  20d Return: {regime['features']['return_20d']:.1f}%")
        print(f"  20d Volatility: {regime['features']['volatility_20d']:.1f}%")
        print(f"  RSI-14: {regime['features']['rsi_14']:.0f}")
        print(f"  ADX-14: {regime['features']['adx_14']:.0f}")
    if regime.get('recommendations'):
        rec = regime['recommendations']
        print(f"\n  Preferred Model: {rec.get('preferred_model', 'N/A')}")
        print(f"  TP Adjustment: {rec.get('tp_adjustment', 1.0):.1f}x")
        print(f"  SL Adjustment: {rec.get('sl_adjustment', 1.0):.1f}x")
        print(f"  Position Size: {rec.get('position_size_mult', 1.0):.1f}x")
        print(f"  Note: {rec.get('strategy_note', '')}")
    
    # Save regime data
    regime_path = RESULTS_DIR / "current_regime.json"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(regime_path, "w") as f:
        json.dump(regime, f, indent=2, default=str)
    
    return regime


def cmd_status():
    """Show current A/B test status and model performance."""
    ab_path = AB_TEST_DIR / "ab_test_report.json"
    summary_path = RESULTS_DIR / "training_summary.json"
    
    print(f"\n{'='*60}")
    print(f"ENHANCED ML CRYPTO PREDICTOR — STATUS REPORT")
    print(f"{'='*60}")
    
    if summary_path.exists():
        with open(summary_path) as f:
            summary = json.load(f)
        print(f"\nLast Training: {summary.get('trained_at', 'Never')}")
        print(f"Total Models: {summary.get('total_models', 0)}")
        print(f"Training Time: {summary.get('training_time_seconds', 0):.0f}s")
        print(f"A/B Winner: {summary.get('ab_test_winner', 'N/A')}")
        
        if summary.get('avg_scores'):
            print(f"\nAverage Composite Scores:")
            for v, s in sorted(summary['avg_scores'].items(), key=lambda x: -x[1]):
                print(f"  {v}: {s:.4f}")
        
        if summary.get('variant_wins'):
            print(f"\nVariant Wins:")
            for v, w in sorted(summary['variant_wins'].items(), key=lambda x: -x[1]):
                print(f"  {v}: {w} wins")
    else:
        print("\n⚠️  No training data found. Run 'train' first.")
    
    # Check model files
    model_count = len(list(MODELS_DIR.glob("*.joblib"))) if MODELS_DIR.exists() else 0
    print(f"\nModel files on disk: {model_count}")
    
    # Check data cache
    data_dir = Path(__file__).parent / "data" / "klines"
    cache_count = len(list(data_dir.glob("*.parquet"))) if data_dir.exists() else 0
    print(f"Cached data files: {cache_count}")
    
    return {"models": model_count, "cache": cache_count}


def cmd_full():
    """Full pipeline: train → regime → predict."""
    print("="*70)
    print("FULL PIPELINE: TRAIN → REGIME → PREDICT")
    print("="*70)
    
    print("\n[1/3] Training models (massive mode)...")
    train_result = cmd_train(massive=True)
    
    print("\n[2/3] Detecting market regime...")
    regime = cmd_regime()
    
    print("\n[3/3] Running live prediction...")
    predictions = cmd_predict()
    
    print("\n" + "="*70)
    print("PIPELINE COMPLETE")
    print("="*70)
    
    return {
        "training": train_result,
        "regime": regime,
        "predictions": predictions,
    }


def cmd_live_picks():
    """Run live prediction cycle."""
    from .live_picks_tracker import run_prediction_cycle
    return run_prediction_cycle()


def cmd_discord():
    """Post ANTIGRAVITY-CLAUDEOPUS status to Discord."""
    from .discord_antigravity import main as discord_main
    discord_main()


def cmd_feedback_train():
    """Train feedback model from closed trade outcomes across all systems."""
    from .feedback_trainer import run_feedback_training
    result = run_feedback_training()
    print(f"\nFeedback training: {result.get('status', 'unknown')}")
    return result


def cmd_feedback_status():
    """Show feedback model status and performance."""
    from .feedback_trainer import get_feedback_model_status
    status = get_feedback_model_status()
    print(json.dumps(status, indent=2))
    return status


def main():
    """CLI entry point."""
    args = sys.argv[1:] if len(sys.argv) > 1 else ["status"]
    command = args[0].lower()

    if command == "train":
        cmd_train(quick=False)
    elif command in ("train-quick", "quick"):
        cmd_train(quick=True)
    elif command in ("train-massive", "massive"):
        cmd_train(massive=True)
    elif command == "predict":
        cmd_predict()
    elif command == "regime":
        cmd_regime()
    elif command == "status":
        cmd_status()
    elif command == "full":
        cmd_full()
    elif command in ("live-picks", "picks", "live"):
        cmd_live_picks()
    elif command == "discord":
        cmd_discord()
    elif command in ("generate-html", "html"):
        from .generate_picks_html import generate_html
        generate_html()
    elif command in ("feedback-train", "feedback"):
        cmd_feedback_train()
    elif command == "feedback-status":
        cmd_feedback_status()
    else:
        print(f"Unknown command: {command}")
        print("Available: train, train-quick, train-massive, predict, regime, status, full, live-picks, discord, feedback-train, feedback-status")
        sys.exit(1)


if __name__ == "__main__":
    main()

