"""
ML drift guard + optional repair hook (offline / batch path).

Complements existing runtime pieces:
  - ``ml_battleground.shared.drift_monitor.DriftMonitor`` — sliding-window
    residual drift for live scoring loops (e.g. mercury2).
  - ``alpha_engine.feature_health.detect_feature_drift`` — KS + PSI on
    per-pick ML feature dicts.

This module targets **vector-level** checks (e.g. sequences of predicted
returns, price deltas, or probabilities) for nightly jobs or research
notebooks: KS two-sample test + PSI-style stability vs a frozen reference
window, then a small **repair plan** (no-op → shadow → retrain command).

Not financial advice; engineering utilities only.
"""
from __future__ import annotations

import json
import logging
import math
import os
import shlex
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

logger = logging.getLogger(__name__)


class RepairTier(str, Enum):
    NONE = "none"
    MONITOR = "monitor"
    RETRAIN = "retrain"
    HALT = "halt"


class DriftHaltError(RuntimeError):
    """Raised when drift breaches the critical threshold. Callers MUST stop
    model execution immediately (do not just log). Per memory feedback rule
    `feedback_halt_flag_must_be_hardcoded.md` — HALT is not advisory."""


class LookAheadBiasError(ValueError):
    """Raised when reference_end_time is not strictly before current_start_time.
    Prevents silent look-ahead bias when the caller passes overlapping windows."""


# Whitelist of allowed repair commands. Maps a short alias (set via
# ML_REPAIR_COMMAND env var) to the exact pre-split argv list. Adding to the
# whitelist requires a code change reviewed by a human. Free-form shell
# commands are NOT supported — prevents the command-injection surface flagged
# in review of this PR.
REPAIR_COMMAND_WHITELIST: dict[str, list[str]] = {
    # Examples; edit this dict when you add a real retrain target.
    # "retrain_crypto_15m": ["python", "alpha_engine/ml_trainer.py", "--model", "crypto_15m"],
    # "retrain_equity_1h":  ["python", "alpha_engine/ml_trainer.py", "--model", "equity_1h"],
}


def _psi_equal_frequency(
    expected: Sequence[float],
    actual: Sequence[float],
    n_bins: int = 10,
) -> float:
    """Population Stability Index; bins from expected (equal-frequency)."""
    exp = sorted(float(x) for x in expected if np.isfinite(x))
    act = [float(x) for x in actual if np.isfinite(x)]
    if len(exp) < n_bins or len(act) < 5:
        return 0.0

    n_exp = len(exp)
    bin_edges: list[float] = []
    for i in range(1, n_bins):
        idx = int(i * n_exp / n_bins)
        idx = min(idx, n_exp - 1)
        bin_edges.append(exp[idx])
    bin_edges = sorted(set(bin_edges))
    if not bin_edges:
        return 0.0

    def _props(values: list[float]) -> list[float]:
        n = len(values)
        if n == 0:
            return []
        counts = [0] * (len(bin_edges) + 1)
        for v in values:
            placed = False
            for j, edge in enumerate(bin_edges):
                if v <= edge:
                    counts[j] += 1
                    placed = True
                    break
            if not placed:
                counts[-1] += 1
        eps = 1e-4
        return [(c / n) + eps for c in counts]

    ep = _props(exp)
    ap = _props(act)
    if len(ep) != len(ap):
        return 0.0
    psi = 0.0
    for e, a in zip(ep, ap):
        psi += (a - e) * math.log(a / e)
    return max(0.0, float(psi))


def prediction_distribution_drift(
    reference: Sequence[float],
    current: Sequence[float],
    *,
    n_bins: int = 10,
    reference_end_time: datetime | None = None,
    current_start_time: datetime | None = None,
    strict_ordering: bool = True,
) -> dict[str, Any]:
    """
    Compare reference vs current prediction streams (or return residuals).

    Returns KS statistic / p-value when scipy is available; always returns PSI.

    Look-ahead-bias guard: when both ``reference_end_time`` and
    ``current_start_time`` are supplied, asserts reference_end_time <=
    current_start_time (strict when ``strict_ordering=True``). Passing
    overlapping windows silently hides real drift AND risks training a repair
    model on test-period data — both dangerous. Pass both or neither; if
    neither is passed, the caller accepts responsibility for temporal
    ordering (loudly warned in the docstring).
    """
    if reference_end_time is not None and current_start_time is not None:
        # Normalize to UTC-aware for comparison.
        ref_t = reference_end_time if reference_end_time.tzinfo else reference_end_time.replace(tzinfo=timezone.utc)
        cur_t = current_start_time if current_start_time.tzinfo else current_start_time.replace(tzinfo=timezone.utc)
        if strict_ordering and ref_t >= cur_t:
            raise LookAheadBiasError(
                f"reference_end_time ({ref_t.isoformat()}) must be strictly "
                f"before current_start_time ({cur_t.isoformat()}). Overlapping "
                "windows hide real drift and risk training on test-period data."
            )
        if not strict_ordering and ref_t > cur_t:
            raise LookAheadBiasError(
                f"reference_end_time ({ref_t.isoformat()}) is after "
                f"current_start_time ({cur_t.isoformat()}). Windows overlap."
            )
    ref = np.asarray(reference, dtype=float)
    cur = np.asarray(current, dtype=float)
    ref = ref[np.isfinite(ref)]
    cur = cur[np.isfinite(cur)]
    out: dict[str, Any] = {
        "reference_n": int(ref.size),
        "current_n": int(cur.size),
        "psi": None,
        "ks_statistic": None,
        "ks_pvalue": None,
    }
    if ref.size < 10 or cur.size < 5:
        out["note"] = "insufficient_samples"
        return out

    out["psi"] = round(_psi_equal_frequency(ref.tolist(), cur.tolist(), n_bins=n_bins), 6)

    try:
        from scipy.stats import ks_2samp

        ks = ks_2samp(ref, cur, alternative="two-sided", method="auto")
        out["ks_statistic"] = float(ks.statistic)
        out["ks_pvalue"] = float(ks.pvalue)
    except Exception as e:  # pragma: no cover - scipy optional in odd envs
        out["ks_note"] = f"scipy unavailable or ks failed: {e}"
    return out


def repair_recommendation(
    drift_report: Mapping[str, Any],
    *,
    ks_alpha: float = 0.01,
    psi_moderate: float = 0.10,
    psi_severe: float = 0.25,
    psi_critical: float = 0.40,
) -> dict[str, Any]:
    """
    Map drift metrics to a discrete repair tier + rationale.

    Thresholds: <0.10 stable, 0.10-0.25 moderate, 0.25-0.40 severe (retrain),
    >=0.40 critical (HALT). Callers receiving tier='halt' MUST stop model
    execution — see execute_repair_plan which raises DriftHaltError.
    """
    psi = drift_report.get("psi")
    pval = drift_report.get("ks_pvalue")

    reasons: list[str] = []
    tier = RepairTier.NONE

    if isinstance(psi, (int, float)):
        if psi >= psi_critical:
            tier = RepairTier.HALT
            reasons.append(f"psi>={psi_critical}_critical")
        elif psi >= psi_severe:
            tier = RepairTier.RETRAIN
            reasons.append(f"psi>={psi_severe}")
        elif psi >= psi_moderate:
            tier = RepairTier.MONITOR
            reasons.append(f"psi>={psi_moderate}")

    if isinstance(pval, (int, float)) and pval < ks_alpha:
        reasons.append(f"ks_pvalue<{ks_alpha}")
        if tier == RepairTier.NONE:
            tier = RepairTier.MONITOR
        if tier == RepairTier.MONITOR and pval < ks_alpha / 5:
            tier = RepairTier.RETRAIN
        # Extreme KS p-value (1/100th of alpha) also triggers HALT.
        if pval < ks_alpha / 100:
            tier = RepairTier.HALT
            reasons.append(f"ks_pvalue<{ks_alpha/100:.2e}_critical")

    if drift_report.get("note") == "insufficient_samples":
        tier = RepairTier.NONE
        reasons.append("insufficient_samples")

    return {
        "tier": tier.value,
        "reasons": reasons,
        "drift_report": dict(drift_report),
    }


def execute_repair_plan(
    plan: Mapping[str, Any],
    *,
    dry_run: bool = True,
    command_alias: str | None = None,
    env_var: str = "ML_REPAIR_COMMAND",
    timeout_sec: int = 3600,
    whitelist: Mapping[str, Sequence[str]] | None = None,
) -> dict[str, Any]:
    """
    Enforce the repair plan. Behavior depends on tier:

    - ``halt``   : raise DriftHaltError. Callers MUST NOT catch and continue.
    - ``retrain``: look up the command alias in the whitelist and run argv list
                   via subprocess.run (no shell). Free-form commands are
                   rejected — whitelist-only by design.
    - ``monitor``/``none``: log + return without action.

    ``command_alias`` (or env_var ``ML_REPAIR_COMMAND``) names a key in
    ``whitelist`` (default: REPAIR_COMMAND_WHITELIST). The value is an argv
    list already split — no shell parsing, no injection surface.
    """
    tier = plan.get("tier", RepairTier.NONE.value)
    wl = dict(whitelist) if whitelist is not None else dict(REPAIR_COMMAND_WHITELIST)
    out: dict[str, Any] = {"tier": tier, "dry_run": dry_run, "executed": False}

    # HALT: hardcoded refusal to continue. See memory feedback_halt_flag_must_be_hardcoded.md.
    if tier == RepairTier.HALT.value:
        msg = (
            "DRIFT HALT: critical threshold breached — model execution must "
            f"stop. reasons={plan.get('reasons', [])}"
        )
        logger.critical("[ml_drift_repair] %s", msg)
        if dry_run:
            out["would_halt"] = True
            out["halt_reason"] = msg
            return out
        raise DriftHaltError(msg)

    if tier != RepairTier.RETRAIN.value:
        out["skipped"] = "tier_not_retrain"
        return out

    alias = (command_alias or os.environ.get(env_var) or "").strip()
    if not alias:
        out["skipped"] = "no_command_alias"
        return out
    if alias not in wl:
        out["skipped"] = "alias_not_in_whitelist"
        out["alias"] = alias
        out["available_aliases"] = sorted(wl.keys())
        logger.warning("[ml_drift_repair] alias %r not in whitelist", alias)
        return out

    argv = list(wl[alias])
    if not argv:
        out["skipped"] = "empty_argv"
        return out

    if dry_run:
        out["would_run_argv"] = argv
        logger.info("[ml_drift_repair] dry_run would execute: %s", argv)
        return out

    try:
        proc = subprocess.run(
            argv,
            check=False,
            timeout=timeout_sec,
            capture_output=True,
            text=True,
            shell=False,  # explicit: never shell=True (injection safety)
        )
        out["executed"] = True
        out["argv"] = argv
        out["returncode"] = proc.returncode
        out["stdout_tail"] = (proc.stdout or "")[-4000:]
        out["stderr_tail"] = (proc.stderr or "")[-4000:]
    except subprocess.TimeoutExpired:
        out["error"] = "timeout"
    except Exception as e:
        out["error"] = str(e)
    return out


def write_drift_artifact(
    report: Mapping[str, Any],
    plan: Mapping[str, Any],
    path: str | Path,
) -> Path:
    """Persist drift + plan JSON for dashboards or CI artifacts."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {"drift": dict(report), "plan": dict(plan)}
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return p


@dataclass(frozen=True)
class CryptoDriftJobConfig:
    """Example config for a nightly crypto price-model check."""

    reference_path: Path
    current_path: Path
    value_key: str = "y_pred"
    out_path: Path | None = None


def _load_series_jsonl_or_json(path: Path, key: str) -> list[float]:
    """Load a list of floats from JSON array or JSONL with ``key`` field."""
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    rows: list[Any]
    if text[0] == "[":
        rows = json.loads(text)
    else:
        rows = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    out: list[float] = []
    for r in rows:
        if isinstance(r, dict) and key in r:
            try:
                out.append(float(r[key]))
            except (TypeError, ValueError):
                continue
        elif isinstance(r, (int, float)):
            out.append(float(r))
    return out


def run_crypto_price_drift_job(cfg: CryptoDriftJobConfig) -> dict[str, Any]:
    """
    End-to-end example: two files (reference vs last-7d scores), emit drift + plan.

    File format: JSON list of objects ``{"y_pred": 0.012, "as_of": "..."}`` or JSONL.
    """
    ref = _load_series_jsonl_or_json(cfg.reference_path, cfg.value_key)
    cur = _load_series_jsonl_or_json(cfg.current_path, cfg.value_key)
    drift = prediction_distribution_drift(ref, cur)
    plan = repair_recommendation(drift)
    if cfg.out_path:
        write_drift_artifact(drift, plan, cfg.out_path)
    return {"drift": drift, "plan": plan}


def _demo() -> None:
    rng = np.random.default_rng(0)
    ref = rng.normal(0, 1.0, size=500)
    cur = rng.normal(0.35, 1.0, size=200)
    rep = prediction_distribution_drift(ref, cur)
    plan = repair_recommendation(rep)
    print(json.dumps({"drift": rep, "plan": plan}, indent=2))


if __name__ == "__main__":
    _demo()
