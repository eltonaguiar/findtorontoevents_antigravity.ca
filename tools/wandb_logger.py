"""Optional Weights & Biases logging wrapper.

Silently no-ops when:
  - `wandb` package is not installed
  - `WANDB_API_KEY` env var is not set
  - `WANDB_DISABLED` env var is set (escape hatch for CI)

This keeps the call sites honest — instrument freely; the wrapper guarantees
no breakage when the dependency or auth is missing. Drift dashboards become
available the moment the secret is provisioned in GitHub Actions.

Usage at a backtest / walk-forward call site:

    from tools.wandb_logger import wb_init, wb_log, wb_finish

    wb_init(project="findtorontoevents-ml", name="walkforward_2026_05",
            config={"asset_class": "CRYPTO", "n_folds": 100})
    # ... compute metrics ...
    wb_log({"sharpe": s, "win_rate": wr, "profit_factor": pf,
            "asset_class": "CRYPTO"})
    wb_finish()

Hermes UNUSED_TOOLS_VALUE_ADD.md item #3 — catch model drift in real time
instead of discovering -2.343 Sharpe in a quarterly swarm.
"""
from __future__ import annotations

import os
from typing import Any, Mapping, Optional

_PROJECT_DEFAULT = "findtorontoevents-ml"


def _is_enabled() -> bool:
    if os.environ.get("WANDB_DISABLED"):
        return False
    if not os.environ.get("WANDB_API_KEY"):
        return False
    try:
        import wandb  # noqa: F401
    except Exception:
        return False
    return True


def wb_init(
    *,
    project: Optional[str] = None,
    name: Optional[str] = None,
    config: Optional[Mapping[str, Any]] = None,
    tags: Optional[list[str]] = None,
) -> bool:
    """Initialize a W&B run. Returns True if active, False if no-op."""
    if not _is_enabled():
        return False
    try:
        import wandb
        wandb.init(
            project=project or os.environ.get("WANDB_PROJECT", _PROJECT_DEFAULT),
            name=name,
            config=dict(config) if config else None,
            tags=list(tags) if tags else None,
            reinit=True,
        )
        return True
    except Exception:
        return False


def wb_log(metrics: Mapping[str, Any], step: Optional[int] = None) -> None:
    """Log a metric dict. Silent no-op if W&B is disabled."""
    if not _is_enabled():
        return
    try:
        import wandb
        if step is not None:
            wandb.log(dict(metrics), step=step)
        else:
            wandb.log(dict(metrics))
    except Exception:
        return


def wb_finish() -> None:
    """End the active run. Silent no-op if no run is active."""
    if not _is_enabled():
        return
    try:
        import wandb
        wandb.finish()
    except Exception:
        return
