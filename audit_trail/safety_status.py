"""Safety Status Endpoint — real-time kill-switch and gate status for dashboard.

Provides a JSON consumable by the audit dashboard showing:
- Binance circuit breaker status
- Geo-block detection
- Drift auto-pause status per asset class
- Weak system block counts
- Crypto short gate status
- Last evaluation timestamp
- Overall safety verdict (GO / CAUTION / STOP)
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def get_binance_circuit_breaker_status() -> dict:
    """Check if the Binance circuit breaker is tripped."""
    # Check score_booster's circuit breaker state
    breaker_file = ROOT / "alpha_engine" / "data" / "binance_breaker_state.json"
    default = {"open": False, "reason": "unknown", "fail_count": 0}

    if breaker_file.exists():
        try:
            with open(breaker_file) as f:
                return json.load(f)
        except Exception:
            return default

    # No breaker state file means score_booster never tripped the breaker this
    # session — the breaker is NOT open. 2026-05-19: the old fallback returned
    # `open: True` for any CI run ("always blocked in CI"). But a CI runner
    # being geo-blocked from Binance is a *data-source* availability problem —
    # handled by the 3+ API failover chain (CoinGecko/KuCoin/CryptoCompare per
    # the API Failover Rule) — NOT a circuit-breaker trip. That invented halt
    # made the M-049 safety gate (quality_gates.py) reject 100% of picks and
    # zeroed every /audit asset-class tile on every scheduled run. Report the
    # geo-block via `reason` for visibility, but do not flag the breaker open.
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return {"open": False, "reason": "CI_GEO_BLOCK", "fail_count": 0}

    return default


def get_drift_status() -> dict:
    """Get current concept drift status from dashboard payload."""
    drift_payload = ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
    default = {"system_breached": False, "system_severe": False,
               "by_class": {}, "payload_age_hours": None}

    if not drift_payload.exists():
        return default

    try:
        with open(drift_payload) as f:
            data = json.load(f)
        hf = data.get("hf_stats", {})
        cd = hf.get("concept_drift", {})
        return {
            "system_breached": cd.get("ks_D", 0) > 2 * cd.get("ks_critical_05", 1),
            "system_severe": cd.get("ks_D", 0) > 3 * cd.get("ks_critical_05", 1),
            "by_class": _extract_class_drift(hf.get("by_asset_class", {})),
            "payload_age_hours": _get_payload_age(hf.get("generated_at")),
            "ks_D": cd.get("ks_D"),
            "ks_critical_05": cd.get("ks_critical_05"),
        }
    except Exception:
        return default


def _extract_class_drift(by_ac: dict) -> dict:
    result = {}
    for ac, data in by_ac.items():
        cd = data.get("concept_drift", {})
        if cd:
            result[ac] = {
                "breached": cd.get("ks_D", 0) > 2 * cd.get("ks_critical_05", 1),
                "ks_D": cd.get("ks_D"),
                "critical": cd.get("ks_critical_05"),
            }
    return result


def _get_payload_age(gen_at) -> float | None:
    if not gen_at:
        return None
    try:
        dt = datetime.fromisoformat(str(gen_at).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds() / 3600
    except Exception:
        return None


def get_weak_system_blocks() -> dict:
    """Count of currently active weak-system-blocked picks."""
    from alpha_engine.score_booster import WEAK_SYSTEMS_SET
    active_path = ROOT / "alpha_engine" / "data" / "active_picks.json"
    count = 0
    blocked_systems = {}

    if active_path.exists():
        try:
            with open(active_path) as f:
                picks = json.load(f)
            for pick in picks:
                src = str(pick.get("source_system", "") or "").lower()
                for sys_name in WEAK_SYSTEMS_SET:
                    if sys_name in src:
                        count += 1
                        blocked_systems[sys_name] = blocked_systems.get(sys_name, 0) + 1
                        break
        except Exception:
            pass

    return {"count": count, "by_system": blocked_systems}


def get_crypto_short_gate_status() -> dict:
    """Check crypto short gate status."""
    enabled = os.environ.get("CRYPTO_SHORT_DISABLED", "0") == "1"
    regime_gate = os.environ.get("CRYPTO_SHORT_REGIME_GATE_ENABLED", "1") == "1"

    # Check regime
    regime_file = ROOT / "alpha_engine" / "data" / "regime_report.json"
    is_bull = True
    regime_label = "UNKNOWN"
    if regime_file.exists():
        try:
            with open(regime_file) as f:
                reg = json.load(f)
            regime_label = str(reg.get("regime", "UNKNOWN"))
            btc_trend = str(reg.get("btc_trend", ""))
            bull_labels = {"BULL", "BULLISH", "TRENDING_UP", "STRONG_BULL"}
            is_bull = regime_label in bull_labels or btc_trend in ("UP", "BULLISH")
        except Exception:
            pass

    return {
        "globally_disabled": enabled,
        "regime_gate_enabled": regime_gate,
        "regime": regime_label,
        "is_bull_regime": is_bull,
        "blocking_active": enabled or (regime_gate and is_bull),
    }


def get_safety_status() -> dict:
    """Aggregate safety status for the dashboard."""
    binance = get_binance_circuit_breaker_status()
    drift = get_drift_status()
    weak = get_weak_system_blocks()
    short_gate = get_crypto_short_gate_status()

    # Determine overall verdict
    issues = []
    if binance.get("open"):
        issues.append(f"Binance CB OPEN ({binance.get('reason', 'unknown')})")
    if drift.get("system_severe"):
        issues.append(f"DRIFT SEVERE (D={drift.get('ks_D', '?')})")
    if drift.get("system_breached") and not drift.get("system_severe"):
        issues.append(f"DRIFT BREACHED (D={drift.get('ks_D', '?')})")
    if weak["count"] > 0:
        issues.append(f"{weak['count']} picks from weak systems")
    if short_gate["blocking_active"]:
        issues.append("Crypto SHORT gate BLOCKING")

    # Payload staleness check
    stale = False
    if drift.get("payload_age_hours") and drift["payload_age_hours"] > 36:
        stale = True
        issues.append(f"Payload stale ({drift['payload_age_hours']:.1f}h)")

    if any("Binance CB OPEN" in i for i in issues):
        verdict = "STOP"
        color = "red"
    elif any("DRIFT SEVERE" in i for i in issues):
        verdict = "STOP"
        color = "red"
    elif len(issues) > 0:
        verdict = "CAUTION"
        color = "yellow"
    else:
        verdict = "GO"
        color = "green"

    return {
        "verdict": verdict,
        "color": color,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "issues": issues,
        "binance": binance,
        "drift": drift,
        "weak_systems": weak,
        "crypto_short_gate": short_gate,
        "payload_stale": stale,
    }


def generate_dashboard_widget() -> str:
    """Generate HTML widget for the audit dashboard sidebar."""
    status = get_safety_status()

    def badge(text, color):
        bg = {"green": "var(--green)", "yellow": "var(--yellow)", "red": "var(--red)"}.get(color, "var(--text-dim)")
        return f'<span style="background:{bg};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700;">{text}</span>'

    verdict_badge = badge(status["verdict"], status["color"])
    drift_badge = badge("DRIFT", "red") if status["drift"].get("system_breached") else badge("DRIFT OK", "green")
    cb_badge = badge("CB OPEN", "red") if status["binance"].get("open") else badge("CB CLOSED", "green")

    issue_rows = ""
    for issue in status["issues"]:
        issue_rows += f'<div style="font-size:11px;color:var(--red);padding:2px 0;">⚠ {issue}</div>'
    if not status["issues"]:
        issue_rows = '<div style="font-size:11px;color:var(--green);padding:4px 0;">✓ All gates clear</div>'

    return f'''
<div id="safety-status-widget" style="
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 12px;
">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
    <h4 style="margin:0;color:var(--text);font-size:14px;">🛡️ Safety Status</h4>
    {verdict_badge}
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px;">
    <div style="text-align:center;padding:8px;background:var(--bg);border-radius:6px;">
      <div style="font-size:11px;color:var(--text-dim);">Binance CB</div>
      {cb_badge}
    </div>
    <div style="text-align:center;padding:8px;background:var(--bg);border-radius:6px;">
      <div style="font-size:11px;color:var(--text-dim);">Concept Drift</div>
      {drift_badge}
    </div>
    <div style="text-align:center;padding:8px;background:var(--bg);border-radius:6px;">
      <div style="font-size:11px;color:var(--text-dim);">Weak-System Blocks</div>
      <div style="font-size:18px;font-weight:700;color:var(--text);">{status['weak_systems']['count']}</div>
    </div>
    <div style="text-align:center;padding:8px;background:var(--bg);border-radius:6px;">
      <div style="font-size:11px;color:var(--text-dim);">Crypto Short Gate</div>
      <div style="font-size:11px;color:{'var(--red)' if status['crypto_short_gate']['blocking_active'] else 'var(--green)'};">
        {'BLOCKING' if status['crypto_short_gate']['blocking_active'] else 'PASS'}
      </div>
    </div>
  </div>

  <div style="font-size:11px;color:var(--text-dim);margin-bottom:8px;">Active Issues:</div>
  {issue_rows}

  <div style="font-size:10px;color:var(--text-dim);margin-top:8px;border-top:1px solid var(--border);padding-top:8px;">
    Last updated: {status['timestamp'][:19]}
  </div>
</div>
'''


if __name__ == "__main__":
    status = get_safety_status()
    print(json.dumps(status, indent=2, default=str))
    print("\n--- Dashboard Widget ---")
    print(generate_dashboard_widget())