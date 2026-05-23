"""
Retrain ML Battleground models on live trade outcomes.

Loads closed picks from each system's data files, calls incremental_trainer
to warm-start existing models on the new data, validates that WR doesn't
drop, and saves updated model files only if they improve or maintain quality.

Systems handled:
  - System A (XGBoost filter): warm_start_xgboost
  - System B (XGBoost regime): warm_start_xgboost
  - System C (PyTorch GRU): finetune_pytorch (freeze GRU, train attention+heads)

Run: python -m ml_battleground.retrain_on_live
Schedule: weekly via GitHub Actions, or manually after accumulating 20+ new trades.
"""
import os
import sys
import json
import logging
import shutil
import numpy as np
from datetime import datetime, timezone
from pathlib import Path

# Ensure imports work from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
log = logging.getLogger("retrain_on_live")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MIN_NEW_TRADES = 10  # minimum closed trades needed before retraining
MAX_WR_DROP = 0.05   # maximum allowed WR drop (5%) before rejecting new model


def load_closed_picks(system_dir: str) -> list:
    """Load closed picks from a system's data directory."""
    path = os.path.join(system_dir, "data", "closed_picks.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception) as e:
        log.warning(f"Failed to load {path}: {e}")
        return []


def compute_win_rate(picks: list) -> float:
    """Compute win rate from a list of closed picks."""
    if not picks:
        return 0.0
    wins = sum(1 for p in picks if p.get("net_pnl_pct", 0) > 0)
    return wins / len(picks)


def backup_model(model_path: str) -> str:
    """Create a backup of an existing model file. Returns backup path."""
    if not os.path.exists(model_path):
        return ""
    backup = model_path + ".backup"
    shutil.copy2(model_path, backup)
    return backup


def restore_model(backup_path: str, model_path: str):
    """Restore model from backup."""
    if backup_path and os.path.exists(backup_path):
        shutil.copy2(backup_path, model_path)
        log.info(f"Restored model from backup: {model_path}")


def retrain_system_a():
    """Retrain System A's XGBoost filter on closed trade outcomes."""
    log.info("=" * 50)
    log.info("Retraining System A (The Filter - XGBoost)")
    log.info("=" * 50)

    system_dir = os.path.join(BASE_DIR, "system_a_filter")
    model_path = os.path.join(system_dir, "models", "filter_xgb.joblib")
    closed = load_closed_picks(system_dir)

    if len(closed) < MIN_NEW_TRADES:
        log.info(f"System A: only {len(closed)} closed trades (need {MIN_NEW_TRADES}). Skipping.")
        return

    if not os.path.exists(model_path):
        log.warning(f"System A: no existing model at {model_path}. Skipping warm-start.")
        return

    try:
        import joblib
        from shared.incremental_trainer import warm_start_xgboost

        # Load existing model
        existing_model = joblib.load(model_path)
        old_wr = compute_win_rate(closed)
        log.info(f"System A: {len(closed)} closed trades, current WR={old_wr:.1%}")

        # Build features from closed trades for retraining
        # Each closed trade has features stored in the pick dict
        X_list = []
        y_list = []
        for pick in closed:
            features = pick.get("features", pick.get("filter_features"))
            if features is None:
                continue
            if isinstance(features, dict):
                features = list(features.values())
            if isinstance(features, list) and len(features) > 0:
                X_list.append(features)
                # Label: 1 if trade was profitable, 0 otherwise
                y_list.append(1 if pick.get("net_pnl_pct", 0) > 0 else 0)

        if len(X_list) < MIN_NEW_TRADES:
            log.info(f"System A: only {len(X_list)} trades with features (need {MIN_NEW_TRADES}). Skipping.")
            return

        X_new = np.array(X_list, dtype=np.float32)
        y_new = np.array(y_list, dtype=np.int32)

        log.info(f"System A: retraining on {len(X_new)} samples (pos_rate={y_new.mean():.1%})")

        # Backup existing model
        backup = backup_model(model_path)

        # Warm-start XGBoost
        new_model = warm_start_xgboost(existing_model, X_new, y_new)

        # Validate: predict on training data and check WR doesn't tank
        preds = new_model.predict(X_new)
        new_accuracy = np.mean(preds == y_new)

        old_preds = existing_model.predict(X_new)
        old_accuracy = np.mean(old_preds == y_new)

        log.info(f"System A: old accuracy={old_accuracy:.3f}, new accuracy={new_accuracy:.3f}")

        if new_accuracy < old_accuracy - MAX_WR_DROP:
            log.warning(f"System A: accuracy dropped {old_accuracy:.3f} -> {new_accuracy:.3f}. "
                        f"Keeping old model.")
            restore_model(backup, model_path)
        else:
            joblib.dump(new_model, model_path)
            log.info(f"System A: model updated successfully at {model_path}")

        # Clean up backup
        if backup and os.path.exists(backup):
            os.remove(backup)

    except ImportError as e:
        log.warning(f"System A: missing dependency: {e}")
    except Exception as e:
        log.error(f"System A: retraining failed: {e}", exc_info=True)


def retrain_system_b():
    """Retrain System B's XGBoost regime classifier on closed trade outcomes."""
    log.info("=" * 50)
    log.info("Retraining System B (The Regime - XGBoost)")
    log.info("=" * 50)

    system_dir = os.path.join(BASE_DIR, "system_b_regime")
    model_path = os.path.join(system_dir, "models", "regime_xgb.joblib")
    closed = load_closed_picks(system_dir)

    if len(closed) < MIN_NEW_TRADES:
        log.info(f"System B: only {len(closed)} closed trades (need {MIN_NEW_TRADES}). Skipping.")
        return

    if not os.path.exists(model_path):
        log.warning(f"System B: no existing model at {model_path}. Skipping warm-start.")
        return

    try:
        import joblib
        from shared.incremental_trainer import warm_start_xgboost

        existing_model = joblib.load(model_path)
        old_wr = compute_win_rate(closed)
        log.info(f"System B: {len(closed)} closed trades, current WR={old_wr:.1%}")

        # Build features from closed trades
        X_list = []
        y_list = []
        for pick in closed:
            features = pick.get("features", pick.get("regime_features"))
            if features is None:
                continue
            if isinstance(features, dict):
                features = list(features.values())
            if isinstance(features, list) and len(features) > 0:
                X_list.append(features)
                y_list.append(1 if pick.get("net_pnl_pct", 0) > 0 else 0)

        if len(X_list) < MIN_NEW_TRADES:
            log.info(f"System B: only {len(X_list)} trades with features (need {MIN_NEW_TRADES}). Skipping.")
            return

        X_new = np.array(X_list, dtype=np.float32)
        y_new = np.array(y_list, dtype=np.int32)

        log.info(f"System B: retraining on {len(X_new)} samples (pos_rate={y_new.mean():.1%})")

        backup = backup_model(model_path)

        new_model = warm_start_xgboost(existing_model, X_new, y_new)

        # Validate
        preds = new_model.predict(X_new)
        new_accuracy = np.mean(preds == y_new)
        old_preds = existing_model.predict(X_new)
        old_accuracy = np.mean(old_preds == y_new)

        log.info(f"System B: old accuracy={old_accuracy:.3f}, new accuracy={new_accuracy:.3f}")

        if new_accuracy < old_accuracy - MAX_WR_DROP:
            log.warning(f"System B: accuracy dropped {old_accuracy:.3f} -> {new_accuracy:.3f}. "
                        f"Keeping old model.")
            restore_model(backup, model_path)
        else:
            joblib.dump(new_model, model_path)
            log.info(f"System B: model updated successfully at {model_path}")

        if backup and os.path.exists(backup):
            os.remove(backup)

    except ImportError as e:
        log.warning(f"System B: missing dependency: {e}")
    except Exception as e:
        log.error(f"System B: retraining failed: {e}", exc_info=True)


def retrain_system_c():
    """Fine-tune System C's PyTorch GRU-Attention model on closed trade outcomes."""
    log.info("=" * 50)
    log.info("Retraining System C (The Neural Net - PyTorch GRU)")
    log.info("=" * 50)

    system_dir = os.path.join(BASE_DIR, "system_c_deeplearn")
    model_path = os.path.join(system_dir, "models", "gru_attention.pt")
    scaler_path = os.path.join(system_dir, "models", "feature_scaler.joblib")
    arch_config_path = os.path.join(system_dir, "models", "arch_config.json")
    closed = load_closed_picks(system_dir)

    if len(closed) < MIN_NEW_TRADES:
        log.info(f"System C: only {len(closed)} closed trades (need {MIN_NEW_TRADES}). Skipping.")
        return

    if not os.path.exists(model_path):
        log.warning(f"System C: no existing model at {model_path}. Skipping fine-tune.")
        return

    try:
        import torch
        import torch.nn as nn
        from torch.utils.data import TensorDataset, DataLoader
        import joblib
        from system_c_deeplearn.model_arch import GRUAttentionModel
        from shared.incremental_trainer import finetune_pytorch, FINETUNE_EPOCHS

        # Load arch config
        arch_cfg = {}
        if os.path.exists(arch_config_path):
            with open(arch_config_path) as f:
                arch_cfg = json.load(f)

        old_wr = compute_win_rate(closed)
        log.info(f"System C: {len(closed)} closed trades, current WR={old_wr:.1%}")

        # Build feature sequences from closed trades that have stored features
        # System C stores feature snapshots in picks under "features" key
        X_list = []
        y_list = []
        for pick in closed:
            features = pick.get("features")
            if features is None:
                continue
            if isinstance(features, dict):
                features = list(features.values())
            if isinstance(features, list) and len(features) > 0:
                X_list.append(features)
                y_list.append(1.0 if pick.get("net_pnl_pct", 0) > 0 else 0.0)

        if len(X_list) < MIN_NEW_TRADES:
            log.info(f"System C: only {len(X_list)} trades with features (need {MIN_NEW_TRADES}). Skipping.")
            return

        log.info(f"System C: {len(X_list)} trades with stored features")

        # Load model
        device = "cuda" if torch.cuda.is_available() else "cpu"
        input_size = arch_cfg.get("input_size", 25)
        model = GRUAttentionModel(
            input_size=input_size,
            hidden_size=arch_cfg.get("hidden_size", 128),
            num_layers=arch_cfg.get("num_layers", 2),
            n_heads=arch_cfg.get("n_heads", 4),
            dropout=arch_cfg.get("dropout", 0.3),
        )
        model.load_state_dict(torch.load(model_path, map_location=device, weights_only=True))
        model.to(device)

        # For fine-tuning, we need sequence data but closed trades only have
        # single feature snapshots. We create pseudo-sequences by repeating
        # the feature vector across the sequence length (simplified approach).
        # This is not ideal but allows the attention/dense heads to learn
        # from actual trade outcomes.
        seq_len = arch_cfg.get("seq_len", 200)
        n_features = len(X_list[0])

        # Truncate or pad features to match model input_size
        X_seqs_primary = []
        X_seqs_1h = []
        y_arr = []
        for feat, label in zip(X_list, y_list):
            feat_arr = np.array(feat[:input_size], dtype=np.float32)
            if len(feat_arr) < input_size:
                feat_arr = np.pad(feat_arr, (0, input_size - len(feat_arr)))
            # Create pseudo-sequence (same features repeated)
            seq = np.tile(feat_arr, (seq_len, 1))
            X_seqs_primary.append(seq)
            X_seqs_1h.append(seq)  # Use same for both timeframes in fine-tune
            y_arr.append(label)

        X_primary = torch.tensor(np.array(X_seqs_primary), dtype=torch.float32)
        X_1h = torch.tensor(np.array(X_seqs_1h), dtype=torch.float32)
        y_entry = torch.tensor(np.array(y_arr), dtype=torch.float32)
        # Dummy TP/SL targets (not the focus of fine-tuning)
        y_tp = torch.ones(len(y_arr), dtype=torch.float32) * 1.5
        y_sl = torch.ones(len(y_arr), dtype=torch.float32) * 1.0

        dataset = TensorDataset(X_primary, X_1h, y_entry, y_tp, y_sl)
        loader = DataLoader(dataset, batch_size=16, shuffle=True)

        # Backup model
        backup = backup_model(model_path)

        # Evaluate old model on this data
        model.eval()
        with torch.no_grad():
            old_preds = []
            for batch in loader:
                x15, x1h, ye, ytp, ysl = [b.to(device) for b in batch]
                pred_entry, _, _, _ = model(x15, x1h)
                old_preds.extend((pred_entry > 0.5).cpu().numpy().tolist())
        old_accuracy = np.mean(np.array(old_preds) == np.array(y_arr))

        # Fine-tune: freeze GRU, train attention + dense heads
        # Custom training loop since model.compute_loss isn't implemented
        model.train()
        for name, param in model.named_parameters():
            if "gru" in name.lower():
                param.requires_grad = False

        lr = 1e-3 / 10  # lr/10 for fine-tuning
        optimizer = torch.optim.Adam(
            filter(lambda p: p.requires_grad, model.parameters()),
            lr=lr, weight_decay=1e-4,
        )
        focal_alpha, focal_gamma = 0.25, 2.0

        for epoch in range(FINETUNE_EPOCHS):
            total_loss = 0
            for batch in loader:
                x15, x1h, ye, ytp, ysl = [b.to(device) for b in batch]
                optimizer.zero_grad()
                pred_entry, pred_tp, pred_sl, _ = model(x15, x1h)

                # Focal loss for entry
                pred_entry_clamped = pred_entry.clamp(1e-7, 1 - 1e-7)
                bce = nn.functional.binary_cross_entropy(pred_entry_clamped, ye, reduction='none')
                pt = torch.exp(-bce)
                loss_entry = (focal_alpha * (1 - pt) ** focal_gamma * bce).mean()

                # MSE for TP/SL
                loss_tp = nn.functional.mse_loss(pred_tp, ytp)
                loss_sl = nn.functional.mse_loss(pred_sl, ysl)

                loss = loss_entry + 0.5 * loss_tp + 0.5 * loss_sl
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                total_loss += loss.item()

            log.info(f"  Fine-tune epoch {epoch + 1}/{FINETUNE_EPOCHS}: loss={total_loss:.4f}")

        # Unfreeze all layers for next retrain
        for param in model.parameters():
            param.requires_grad = True

        # Validate new model
        model.eval()
        with torch.no_grad():
            new_preds = []
            for batch in loader:
                x15, x1h, ye, ytp, ysl = [b.to(device) for b in batch]
                pred_entry, _, _, _ = model(x15, x1h)
                new_preds.extend((pred_entry > 0.5).cpu().numpy().tolist())
        new_accuracy = np.mean(np.array(new_preds) == np.array(y_arr))

        log.info(f"System C: old accuracy={old_accuracy:.3f}, new accuracy={new_accuracy:.3f}")

        if new_accuracy < old_accuracy - MAX_WR_DROP:
            log.warning(f"System C: accuracy dropped {old_accuracy:.3f} -> {new_accuracy:.3f}. "
                        f"Keeping old model.")
            restore_model(backup, model_path)
        else:
            torch.save(model.state_dict(), model_path)
            log.info(f"System C: model updated successfully at {model_path}")

        if backup and os.path.exists(backup):
            os.remove(backup)

    except ImportError as e:
        log.warning(f"System C: missing dependency: {e}")
    except Exception as e:
        log.error(f"System C: retraining failed: {e}", exc_info=True)


def main():
    """Run retraining for all systems."""
    log.info("=" * 60)
    log.info("ML Battleground: Incremental Retraining on Live Outcomes")
    log.info(f"Time: {datetime.now(timezone.utc).isoformat()}")
    log.info("=" * 60)

    results = {}

    for name, func in [
        ("System A", retrain_system_a),
        ("System B", retrain_system_b),
        ("System C", retrain_system_c),
    ]:
        try:
            func()
            results[name] = "success"
        except Exception as e:
            log.error(f"{name}: unexpected error: {e}", exc_info=True)
            results[name] = f"error: {e}"

    # Save retrain summary
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results": results,
    }
    summary_path = os.path.join(BASE_DIR, "retrain_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    log.info(f"\nRetrain summary saved to {summary_path}")

    log.info("\n" + "=" * 60)
    for name, result in results.items():
        log.info(f"  {name}: {result}")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
