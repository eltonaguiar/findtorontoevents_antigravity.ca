"""
Build ai_tournament_model_diagnostics.json from config + submissions + model summary.

This powers the fleet-status panel on /audit/ai-tournament.html so the page can
show the real tournament coverage gap: configured models, keys available on the
runner, which models produced picks today, and which ones are blocked.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / "config" / "model_persona_mapping.json"
SUBMISSIONS = REPO / "data" / "ai_tournament" / "submissions"
MODEL_SUMMARY = REPO / "audit_dashboard" / "data" / "ai_tournament_model_summary.json"
OUT = REPO / "audit_dashboard" / "data" / "ai_tournament_model_diagnostics.json"


def _today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return default


def _status_from_model(
    model_id: str,
    model_cfg: dict[str, Any],
    submission: dict[str, Any] | None,
    summary_by_model: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    api_key_env = model_cfg.get("api_key_env", "")
    has_api_key = bool(os.environ.get(api_key_env, "")) if api_key_env else False
    assignments = model_cfg.get("assignments", {})
    assignment_count = sum(len(personas) for personas in assignments.values())
    summary = summary_by_model.get(model_id, {})

    status = "blocked_missing_key"
    reason = f"Missing {api_key_env}" if api_key_env else "No api_key_env configured"
    picks_today = 0
    submission_status = None
    submitted_at = None

    if submission:
        submission_status = submission.get("status")
        submitted_at = submission.get("submitted_at")
        picks_today = len(submission.get("picks") or [])
        if picks_today > 0:
            status = "active_today"
            reason = f"{picks_today} picks generated in latest submission"
        elif has_api_key:
            status = "configured_no_picks"
            reason = submission.get("reason") or "Key available, but no valid picks were generated"
        else:
            status = "blocked_missing_key"
            reason = f"Submission recorded without {api_key_env} present on runner"
    elif has_api_key:
        status = "configured_no_submission"
        reason = "Key available, but no submission envelope was written"
    elif summary:
        status = "historical_only"
        reason = "Historical picks exist, but today's runner had no key/submission"

    return {
        "model_id": model_id,
        "provider": model_cfg.get("provider", ""),
        "api_key_env": api_key_env,
        "model_name": model_cfg.get("model_name", model_id),
        "assignment_count": assignment_count,
        "asset_classes": sorted(assignments.keys()),
        "has_api_key": has_api_key,
        "status": status,
        "reason": reason,
        "submission_status": submission_status,
        "submission_picks_today": picks_today,
        "submitted_at": submitted_at,
        "historical_total_picks": summary.get("total_picks", 0),
        "historical_resolved": summary.get("resolved", 0),
        "historical_last_pick": summary.get("last_pick"),
    }


def build() -> dict[str, Any]:
    config = _load_json(CONFIG, {})
    models = config.get("models", {})
    summary = _load_json(MODEL_SUMMARY, {})
    summary_by_model = {
        model.get("model_id"): model
        for model in summary.get("models", [])
        if model.get("model_id")
    }

    today = _today_str()
    submissions_by_model: dict[str, dict[str, Any]] = {}
    if SUBMISSIONS.exists():
        for path in sorted(SUBMISSIONS.glob(f"*_{today}.json")):
            payload = _load_json(path, None)
            if isinstance(payload, dict) and payload.get("model_id"):
                submissions_by_model[payload["model_id"]] = payload

    models_out = [
        _status_from_model(mid, cfg, submissions_by_model.get(mid), summary_by_model)
        for mid, cfg in sorted(models.items())
    ]

    counts = {
        "configured_total": len(models_out),
        "active_today": sum(1 for model in models_out if model["status"] == "active_today"),
        "configured_with_key": sum(1 for model in models_out if model["has_api_key"]),
        "configured_no_picks": sum(1 for model in models_out if model["status"] == "configured_no_picks"),
        "configured_no_submission": sum(1 for model in models_out if model["status"] == "configured_no_submission"),
        "blocked_missing_key": sum(1 for model in models_out if model["status"] == "blocked_missing_key"),
        "historical_only": sum(1 for model in models_out if model["status"] == "historical_only"),
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "date_utc": today,
        "counts": counts,
        "models": models_out,
    }


def main() -> None:
    diagnostics = build()
    OUT.write_text(json.dumps(diagnostics, indent=2))
    counts = diagnostics["counts"]
    print(
        "[model_diagnostics] wrote "
        f"{OUT.relative_to(REPO)} ({counts['active_today']} active today / "
        f"{counts['configured_total']} configured / "
        f"{counts['configured_with_key']} with keys)"
    )


if __name__ == "__main__":
    main()
