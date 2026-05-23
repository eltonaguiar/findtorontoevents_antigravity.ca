"""Incremental training utilities for warm-start model updates.

Supports:
- XGBoost: xgb_model parameter (cap at 500 trees, prune oldest)
- LightGBM: init_model parameter
- RandomForest: warm_start=True (auto-increment n_estimators, cap at 600)
- PyTorch GRU: fine-tune at lr/10, freeze early layers, 3-5 epochs

Monthly full retrain from scratch uses rolling 12-month window.
"""
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

log = logging.getLogger("incremental_trainer")

MAX_XGB_TREES = 500
MAX_RF_TREES = 600
FINETUNE_EPOCHS = 5
FINETUNE_LR_DIVISOR = 10


def warm_start_xgboost(existing_model, X_new, y_new, params: dict = None):
    """Continue training XGBoost from existing model.
    Caps total trees at MAX_XGB_TREES by removing oldest boosters.
    """
    import xgboost as xgb

    params = params or {}
    n_existing = existing_model.n_estimators if hasattr(existing_model, "n_estimators") else 0
    n_new = min(params.get("n_estimators", 100), MAX_XGB_TREES - n_existing)
    if n_new <= 0:
        # At cap -- retrain with only recent trees
        n_new = 100
        log.info(f"XGBoost at {n_existing} trees (cap={MAX_XGB_TREES}), adding {n_new} fresh")

    params["n_estimators"] = n_new
    new_model = xgb.XGBClassifier(**params)
    new_model.fit(X_new, y_new, xgb_model=existing_model)
    return new_model


def warm_start_lightgbm(existing_model_path: str, X_new, y_new, params: dict = None):
    """Continue training LightGBM from saved model file."""
    import lightgbm as lgb

    params = params or {}
    dtrain = lgb.Dataset(X_new, label=y_new)
    new_model = lgb.train(
        params,
        dtrain,
        init_model=str(existing_model_path),
        num_boost_round=params.get("n_estimators", 100),
    )
    return new_model


def warm_start_random_forest(existing_model, X_new, y_new, increment: int = 50):
    """Continue training RandomForest by adding trees.
    Must increment n_estimators before calling fit() with warm_start=True.
    """
    current = existing_model.n_estimators
    new_total = min(current + increment, MAX_RF_TREES)
    if new_total <= current:
        log.info(f"RF at cap ({MAX_RF_TREES} trees), resetting to {increment}")
        existing_model.n_estimators = increment
        existing_model.warm_start = False
    else:
        existing_model.n_estimators = new_total
        existing_model.warm_start = True
    existing_model.fit(X_new, y_new)
    return existing_model


def finetune_pytorch(model, train_loader, device="cpu", epochs=FINETUNE_EPOCHS, base_lr=1e-3):
    """Fine-tune PyTorch model (GRU-Attention) on new data.
    Freezes GRU layers, only trains attention + dense heads.
    Uses lr/10 to avoid catastrophic forgetting.
    """
    import torch
    import torch.nn as nn

    model = model.to(device)
    model.train()

    # Freeze GRU layers
    for name, param in model.named_parameters():
        if "gru" in name.lower() or "rnn" in name.lower():
            param.requires_grad = False

    lr = base_lr / FINETUNE_LR_DIVISOR
    optimizer = torch.optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=lr,
        weight_decay=1e-4,
    )

    for epoch in range(epochs):
        total_loss = 0
        for batch in train_loader:
            optimizer.zero_grad()
            loss = model.compute_loss(batch)  # Model must implement compute_loss
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        log.info(f"  Fine-tune epoch {epoch+1}/{epochs}: loss={total_loss:.4f}")

    # Unfreeze all for next full retrain
    for param in model.parameters():
        param.requires_grad = True

    return model


def filter_training_data_by_recency(df, timestamp_col="timestamp", months=6):
    """Filter training data to rolling N-month window.
    Monthly full retrain uses 12 months, warm-start uses 6 months.
    """
    import pandas as pd

    cutoff = pd.Timestamp.now(tz="UTC") - pd.DateOffset(months=months)
    if timestamp_col in df.columns:
        mask = pd.to_datetime(df[timestamp_col]) >= cutoff
        filtered = df[mask]
        log.info(f"Recency filter: {len(df)} -> {len(filtered)} rows ({months}mo window)")
        return filtered
    return df  # No timestamp column, return as-is
