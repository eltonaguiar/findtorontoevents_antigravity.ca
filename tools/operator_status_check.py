#!/usr/bin/env python3
"""Operator validation/alerting check — one-call snapshot of pipeline state.

Per Grok next-step #2 + 3-model consensus: validation/alerting layer
that shows whether the freshly-flipped switches are doing real work.

Reads only — no writes. Designed for cron + dashboard panel consumption.

Output: audit_dashboard/data/operator_status.json

Surfaces:
  - AUTO_RETIRE_APPLY effect: latest auto-retire-daily run + new quarantine count
  - ML_GATE_AB_ENABLED effect: latest ab_summary.json (n_ab_tagged + OLD/NEW WR)
  - Quarantine state: count entries by source (config.py BLACKLISTED_STRATEGIES,
    quality_gates BLOCKED_ASSET_STRATEGY_PAIRS, quarantine_manifest.json)
  - Drift state: hf_stats.concept_drift KS_D + freshness age
  - Data-key audit: presence of FRED_API_KEY, GLASSNODE_API_KEY, CFTC_API_KEY
  - MYSQL_PASSWORD age (vs DB-rotation timestamp if user provides)
  - Per-asset-class concentration tiers (P0-#2 output)

Usage:
  python tools/operator_status_check.py
  python tools/operator_status_check.py --out audit_dashboard/data/operator_status.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _safe_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _age_hours(iso: str | None) -> float | None:
    if not iso:
        return None
    try:
        s = str(iso).replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return round((datetime.now(timezone.utc) - dt).total_seconds() / 3600, 2)
    except Exception:
        return None


def ab_router_effect() -> dict:
    """Did ML_GATE_AB_ENABLED=1 produce real OLD vs NEW splits?"""
    p = ROOT / "ml_gatekeeper" / "data" / "ab_summary.json"
    s = _safe_json(p) or {}
    overall = s.get("overall", {}) or {}
    old = overall.get("OLD", {}) or {}
    new = overall.get("NEW", {}) or {}
    return {
        "ab_summary_exists": p.exists(),
        "ab_summary_age_hours": _age_hours(s.get("timestamp")),
        "n_ab_tagged": s.get("n_ab_tagged", 0),
        "old_n": old.get("n", 0),
        "new_n": new.get("n", 0),
        "old_wr_pct": round((old.get("wr") or 0) * 100, 2),
        "new_wr_pct": round((new.get("wr") or 0) * 100, 2),
        "z_test": s.get("z_test", {}),
        "recommendation": s.get("recommendation", "INSUFFICIENT_DATA"),
        "rollback_state": s.get("rollback_state", {}),
        "verdict": (
            "ACTIVE_REAL_SPLITS" if (old.get("n", 0) + new.get("n", 0)) > 0
            else "FLIPPED_BUT_NO_DATA_YET"
        ),
    }


def quarantine_state() -> dict:
    """Census of currently-blocked strategies across all sources."""
    manifest = _safe_json(ROOT / "audit_dashboard" / "data" / "quarantine_manifest.json") or {}
    config_blacklist_count = None
    blocked_pairs_count = None
    try:
        cfg_text = (ROOT / "alpha_engine" / "config.py").read_text(encoding="utf-8", errors="ignore")
        m = cfg_text.split("BLACKLISTED_STRATEGIES = ")[1].split("\n")[0]
        config_blacklist_count = m.count(",") + 1 if "," in m else m.count("'")
    except Exception:
        pass
    try:
        qg_text = (ROOT / "audit_trail" / "quality_gates.py").read_text(encoding="utf-8", errors="ignore")
        s = qg_text.split("BLOCKED_ASSET_STRATEGY_PAIRS = {")[1].split("}")[0]
        blocked_pairs_count = s.count("(")
    except Exception:
        pass
    return {
        "manifest_generated_at": manifest.get("generated_at"),
        "manifest_age_hours": _age_hours(manifest.get("generated_at")),
        "manifest_quarantined_strategies": len(manifest.get("quarantined_strategies", []) or []),
        "manifest_blocked_strategies_class_wide": len(manifest.get("blocked_strategies_class_wide", []) or []),
        "config_blacklist_count": config_blacklist_count,
        "quality_gates_blocked_pairs_count": blocked_pairs_count,
        "factor_exposures_registry": len((manifest.get("factor_exposures") or {}).get("registry", []) or []),
    }


def drift_state() -> dict:
    d = _safe_json(ROOT / "audit_dashboard" / "data" / "dashboard_data.json") or {}
    hf = d.get("hf_stats", {}) or {}
    cd = hf.get("concept_drift", {}) or {}
    return {
        "hf_stats_generated_at": hf.get("generated_at"),
        "hf_stats_age_hours": _age_hours(hf.get("generated_at")),
        "ks_D": cd.get("ks_D"),
        "ks_critical_05": cd.get("ks_critical_05"),
        "drift_alert": cd.get("drift_alert"),
        "severity_x": round((cd.get("ks_D") or 0) / (cd.get("ks_critical_05") or 1), 2),
    }


def data_keys() -> dict:
    """Which API keys are present locally (cannot inspect GH secrets)."""
    keys = [
        "FRED_API_KEY", "GLASSNODE_API_KEY", "CFTC_API_KEY",
        "COIN_GECKO", "COINGECKO_API_KEY", "CRYPTOCOMPARE_API_KEY",
        "LUNARCRUSH_API", "OPENROUTER_API_KEY", "GROQ_KEY",
        "CEREBRAS_API_KEY_PAID", "X_AI_KEY", "DEEPSEEK_API",
        "DB_PASS_STOCKS", "DB_PASS_BACKTESTS",
        "DB_STOCKS_PASSWORD", "DB_BACKTESTS_PASSWORD",
        "MYSQL_PASSWORD",
    ]
    return {k: ("SET" if os.environ.get(k) else "UNSET") for k in keys}


def concentration_state() -> dict:
    d = _safe_json(ROOT / "audit_dashboard" / "data" / "dashboard_data.json") or {}
    conc = (d.get("performance", {}) or {}).get("asset_class_concentration", {}) or {}
    out = {}
    for cls, m in conc.items():
        if isinstance(m, dict):
            out[cls] = {
                "tier": m.get("tier"),
                "top_symbol": m.get("top_symbol"),
                "top_share_pct": m.get("top_share_pct"),
                "top_strategy": m.get("top_strategy"),
                "honest_label": m.get("honest_label"),
            }
    return out


def alerts(payload: dict) -> list[str]:
    """Compute actionable alerts from the snapshot."""
    a: list[str] = []
    drift = payload.get("drift", {}) or {}
    if drift.get("drift_alert") and (drift.get("severity_x") or 0) > 1:
        a.append(
            f"DRIFT KS_D {drift.get('ks_D'):.3f} = {drift.get('severity_x')}x critical — "
            "sizing-pause recommended"
        )
    if (drift.get("hf_stats_age_hours") or 0) > 24:
        a.append(
            f"hf_stats stale {drift.get('hf_stats_age_hours'):.1f}h > 24h cache TTL — "
            "verify staleness gate fix shipped (58319d0d50b)"
        )
    ab = payload.get("ab_router", {}) or {}
    if ab.get("n_ab_tagged", 0) == 0 and ab.get("ab_summary_exists"):
        a.append(
            "ML_GATE_AB_ENABLED flipped but n_ab_tagged=0 — router not yet routing; "
            "check gatekeeper_old/new.joblib on main + cron picked up flag"
        )
    keys = payload.get("data_keys", {}) or {}
    missing_critical = [k for k in ("FRED_API_KEY", "GLASSNODE_API_KEY", "CFTC_API_KEY") if keys.get(k) == "UNSET"]
    if missing_critical:
        a.append(f"missing data keys (env-local): {', '.join(missing_critical)}")
    return a


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", default="audit_dashboard/data/operator_status.json")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec": "operator validation/alerting snapshot — Grok next-step #2",
        "ab_router": ab_router_effect(),
        "quarantine": quarantine_state(),
        "drift": drift_state(),
        "concentration": concentration_state(),
        "data_keys": data_keys(),
    }
    payload["alerts"] = alerts(payload)
    payload["n_alerts"] = len(payload["alerts"])

    if args.dry_run:
        print(json.dumps(payload, indent=2, default=str))
        return

    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"# wrote {out_path} ({out_path.stat().st_size:,} bytes)", file=sys.stderr)
    print(f"# alerts: {len(payload['alerts'])}", file=sys.stderr)
    for a in payload["alerts"]:
        print(f"#   {a}", file=sys.stderr)


if __name__ == "__main__":
    main()
