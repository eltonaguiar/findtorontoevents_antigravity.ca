#!/usr/bin/env python3
"""
Alpha Engine - Concentration & Data-Lag Alert Service

Monitors portfolio picks for concentration risk and data freshness.
Dispatches alerts to Slack/Discord webhooks.
Stdlib only: urllib.request, json, csv.
"""

import json
import csv
import os
import sys
import io
import argparse
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from typing import List, Dict, Any, Optional


# ---------------------------------------------------------------------------
# Config defaults
# ---------------------------------------------------------------------------
DEFAULT_CONFIG: Dict[str, Any] = {
    "max_symbol_exposure_pct": 5.0,
    "max_daily_var_pct": 10.0,
    "concentration_hhi_warn": 2500,
    "data_lag_warn_hours": 1,
    "max_pick_age_hours": 2,
    "top_n_systems": 3,
    "max_system_share": 0.60,
}


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    """Load config from JSON file, falling back to defaults for missing keys."""
    cfg = dict(DEFAULT_CONFIG)
    if path and os.path.isfile(path):
        with open(path, "r") as f:
            user = json.load(f)
        cfg.update(user)
    return cfg


# ---------------------------------------------------------------------------
# Alert data structure
# ---------------------------------------------------------------------------
def make_alert(alert_type: str, severity: str, message: str,
               details: Optional[Dict[str, Any]] = None,
               action: str = "") -> Dict[str, Any]:
    return {
        "alert_type": alert_type,
        "severity": severity.upper(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": message,
        "details": details or {},
        "action": action,
    }


# ---------------------------------------------------------------------------
# Concentration alerts
# ---------------------------------------------------------------------------
class ConcentrationAlert:
    """Check portfolio picks for concentration risk."""

    @staticmethod
    def check_symbol_exposure(picks: List[Dict[str, Any]],
                              max_pct: float = 5.0) -> List[Dict[str, Any]]:
        """Flag symbols whose weight exceeds *max_pct* percent."""
        alerts: List[Dict[str, Any]] = []
        for p in picks:
            pct = float(p.get("weight_pct", 0) or p.get("allocation_pct", 0))
            sym = p.get("symbol", "?")
            if pct > max_pct * 2:
                alerts.append(make_alert(
                    "symbol_exposure", "CRITICAL",
                    f"Symbol {sym} exposure {pct:.2f}% exceeds 2x limit ({max_pct*2:.1f}%)",
                    {"symbol": sym, "pct": pct, "max_pct": max_pct},
                    f"Reduce {sym} position immediately",
                ))
            elif pct > max_pct:
                alerts.append(make_alert(
                    "symbol_exposure", "WARNING",
                    f"Symbol {sym} exposure {pct:.2f}% exceeds limit ({max_pct:.1f}%)",
                    {"symbol": sym, "pct": pct, "max_pct": max_pct},
                    f"Review and trim {sym} position",
                ))
        return alerts

    @staticmethod
    def check_strategy_concentration(picks: List[Dict[str, Any]],
                                     hhi_warn: float = 2500) -> List[Dict[str, Any]]:
        """HHI (Herfindahl-Hirschman Index) of strategy weights. Warns if > *hhi_warn*."""
        alerts: List[Dict[str, Any]] = []
        strat_weights: Dict[str, float] = {}
        for p in picks:
            strat = p.get("strategy", "unknown")
            w = float(p.get("weight_pct", 0) or p.get("allocation_pct", 0))
            strat_weights[strat] = strat_weights.get(strat, 0.0) + w

        total = sum(strat_weights.values())
        if total == 0:
            return alerts

        # Normalize to 100%
        shares = [(s, w / total * 100) for s, w in strat_weights.items()]
        hhi = sum(s ** 2 for _, s in shares)

        if hhi > hhi_warn * 2:
            alerts.append(make_alert(
                "strategy_concentration", "CRITICAL",
                f"Strategy HHI {hhi:.0f} severely above threshold ({hhi_warn:.0f})",
                {"hhi": hhi, "threshold": hhi_warn,
                 "strategies": {s: round(w, 2) for s, w in shares}},
                "Diversify across strategies urgently",
            ))
        elif hhi > hhi_warn:
            alerts.append(make_alert(
                "strategy_concentration", "WARNING",
                f"Strategy HHI {hhi:.0f} above threshold ({hhi_warn:.0f})",
                {"hhi": hhi, "threshold": hhi_warn,
                 "strategies": {s: round(w, 2) for s, w in shares}},
                "Consider diversifying across strategies",
            ))
        return alerts

    @staticmethod
    def check_system_concentration(picks: List[Dict[str, Any]],
                                   top_n: int = 3,
                                   max_share: float = 0.60) -> List[Dict[str, Any]]:
        """Flag if top-*N* systems hold more than *max_share* of total allocation."""
        alerts: List[Dict[str, Any]] = []
        sys_weights: Dict[str, float] = {}
        for p in picks:
            sys_name = p.get("system", p.get("source", "unknown"))
            w = float(p.get("weight_pct", 0) or p.get("allocation_pct", 0))
            sys_weights[sys_name] = sys_weights.get(sys_name, 0.0) + w

        total = sum(sys_weights.values())
        if total == 0:
            return alerts

        sorted_sys = sorted(sys_weights.items(), key=lambda x: x[1], reverse=True)
        top = sorted_sys[:top_n]
        top_share = sum(w for _, w in top) / total

        if top_share > max_share + 0.20:
            alerts.append(make_alert(
                "system_concentration", "CRITICAL",
                f"Top {top_n} systems hold {top_share:.1%} (limit {max_share:.0%})",
                {"top_systems": {s: round(w / total * 100, 2) for s, w in top},
                 "top_share": round(top_share, 4), "max_share": max_share},
                "Rebalance system allocations",
            ))
        elif top_share > max_share:
            alerts.append(make_alert(
                "system_concentration", "WARNING",
                f"Top {top_n} systems hold {top_share:.1%} (limit {max_share:.0%})",
                {"top_systems": {s: round(w / total * 100, 2) for s, w in top},
                 "top_share": round(top_share, 4), "max_share": max_share},
                "Review system diversification",
            ))
        return alerts


# ---------------------------------------------------------------------------
# Data-lag alerts
# ---------------------------------------------------------------------------
class DataLagAlert:
    """Check payload and pick freshness."""

    @staticmethod
    def _parse_ts(ts_str: str) -> Optional[datetime]:
        """Best-effort ISO timestamp parse."""
        if not ts_str:
            return None
        ts_str = ts_str.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(ts_str)
        except (ValueError, TypeError):
            return None

    @classmethod
    def check_payload_lag(cls, generated_at: str,
                          warn_hours: float = 1) -> List[Dict[str, Any]]:
        """Check how old the generated_at timestamp is."""
        alerts: List[Dict[str, Any]] = []
        ts = cls._parse_ts(generated_at)
        if ts is None:
            alerts.append(make_alert(
                "payload_lag", "WARNING",
                "Cannot parse generated_at timestamp",
                {"generated_at": generated_at},
                "Verify payload timestamp format",
            ))
            return alerts

        now = datetime.now(timezone.utc)
        age_h = (now - ts).total_seconds() / 3600.0

        if age_h > warn_hours * 3:
            alerts.append(make_alert(
                "payload_lag", "CRITICAL",
                f"Payload is {age_h:.1f}h old (>{warn_hours*3:.0f}h critical)",
                {"generated_at": generated_at, "age_hours": round(age_h, 2)},
                "Investigate data pipeline immediately",
            ))
        elif age_h > warn_hours:
            alerts.append(make_alert(
                "payload_lag", "WARNING",
                f"Payload is {age_h:.1f}h old (threshold {warn_hours}h)",
                {"generated_at": generated_at, "age_hours": round(age_h, 2)},
                "Check upstream data feed",
            ))
        return alerts

    @classmethod
    def check_pick_lag(cls, picks: List[Dict[str, Any]],
                       max_age_hours: float = 2) -> List[Dict[str, Any]]:
        """Flag picks whose timestamp exceeds *max_age_hours*."""
        alerts: List[Dict[str, Any]] = []
        now = datetime.now(timezone.utc)
        stale: List[Dict[str, Any]] = []

        for p in picks:
            ts = cls._parse_ts(p.get("timestamp") or p.get("generated_at"))
            if ts is None:
                stale.append({"symbol": p.get("symbol", "?"), "age_hours": None,
                              "note": "missing timestamp"})
                continue
            age_h = (now - ts).total_seconds() / 3600.0
            if age_h > max_age_hours:
                stale.append({"symbol": p.get("symbol", "?"),
                              "age_hours": round(age_h, 2)})

        if stale:
            sev = "CRITICAL" if len(stale) > len(picks) * 0.5 else "WARNING"
            alerts.append(make_alert(
                "pick_lag", sev,
                f"{len(stale)} of {len(picks)} picks exceed {max_age_hours}h age limit",
                {"stale_picks": stale, "max_age_hours": max_age_hours},
                "Refresh stale picks or investigate source",
            ))
        return alerts


# ---------------------------------------------------------------------------
# Webhook dispatcher
# ---------------------------------------------------------------------------
def send_alert(alert: Dict[str, Any], webhook_url: str) -> bool:
    """POST a single alert to a Slack/Discord webhook. Returns True on success."""
    try:
        if "hooks.slack.com" in webhook_url:
            payload = _slack_payload([alert])
        else:
            payload = _discord_payload(alert)

        data = json.dumps(payload).encode("utf-8")
        req = Request(webhook_url, data=data,
                      headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=15) as resp:
            return resp.status in (200, 204)
    except (URLError, HTTPError, OSError) as e:
        print(f"[alerts] webhook send failed: {e}", file=sys.stderr)
        return False


def send_batch(alerts: List[Dict[str, Any]], webhook_url: str) -> int:
    """Send multiple alerts. Returns count of successfully sent."""
    if not alerts:
        return 0
    try:
        if "hooks.slack.com" in webhook_url:
            payload = _slack_payload(alerts)
        else:
            payload = {"content": "\n".join(
                _discord_line(a) for a in alerts
            )}
        data = json.dumps(payload).encode("utf-8")
        req = Request(webhook_url, data=data,
                      headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=15) as resp:
            return len(alerts) if resp.status in (200, 204) else 0
    except (URLError, HTTPError, OSError) as e:
        print(f"[alerts] batch send failed: {e}", file=sys.stderr)
        return 0


# -- Slack formatting -------------------------------------------------------
_SEVERITY_COLOR = {
    "WARNING": "#daa038",   # gold
    "CRITICAL": "#e01e5a",  # red
}


def _slack_payload(alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
    attachments = []
    for a in alerts:
        sev = a.get("severity", "WARNING")
        color = _SEVERITY_COLOR.get(sev, "#cccccc")
        fields = [
            {"title": "Type", "value": a["alert_type"], "short": True},
            {"title": "Severity", "value": sev, "short": True},
            {"title": "Timestamp", "value": a["timestamp"], "short": False},
            {"title": "Action", "value": a.get("action", "-"), "short": False},
        ]
        if a.get("details"):
            fields.append({
                "title": "Details",
                "value": "```" + json.dumps(a["details"], indent=2) + "```",
                "short": False,
            })
        attachments.append({
            "color": color,
            "fallback": a["message"],
            "pretext": "",
            "text": a["message"],
            "fields": fields,
        })
    return {"attachments": attachments}


# -- Discord formatting -----------------------------------------------------
def _discord_line(a: Dict[str, Any]) -> str:
    sev = a.get("severity", "WARNING")
    icon = "🔴" if sev == "CRITICAL" else "🟡"
    return f"{icon} **[{sev}] {a['alert_type']}** — {a['message']}\n`action:` {a.get('action', '-')}"


def _discord_payload(a: Dict[str, Any]) -> Dict[str, Any]:
    return {"content": _discord_line(a)}


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
def run_all_checks(picks: List[Dict[str, Any]],
                   config: Dict[str, Any],
                   generated_at: Optional[str] = None) -> List[Dict[str, Any]]:
    """Run all concentration + lag checks, return list of alerts."""
    alerts: List[Dict[str, Any]] = []

    # Concentration
    ca = ConcentrationAlert()
    alerts += ca.check_symbol_exposure(picks, config["max_symbol_exposure_pct"])
    alerts += ca.check_strategy_concentration(picks, config["concentration_hhi_warn"])
    alerts += ca.check_system_concentration(
        picks, config["top_n_systems"], config["max_system_share"])

    # Data lag
    da = DataLagAlert()
    if generated_at:
        alerts += da.check_payload_lag(generated_at, config["data_lag_warn_hours"])
    alerts += da.check_pick_lag(picks, config["max_pick_age_hours"])

    return alerts


# ---------------------------------------------------------------------------
# CSV / JSON pick loaders
# ---------------------------------------------------------------------------
def load_picks_json(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        return data.get("picks", [])
    return data


def load_picks_csv(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def load_picks(path: str) -> List[Dict[str, Any]]:
    if path.endswith(".csv"):
        return load_picks_csv(path)
    return load_picks_json(path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Alpha Engine concentration & data-lag alert checker")
    parser.add_argument("--config", default=None,
                        help="Path to alerts_config.json")
    parser.add_argument("--picks", default=None,
                        help="Path to picks file (JSON or CSV)")
    parser.add_argument("--generated-at", default=None,
                        help="ISO timestamp of payload generation")
    parser.add_argument("--webhook", default=None,
                        help="Slack/Discord webhook URL")
    parser.add_argument("--check-all", action="store_true",
                        help="Run all checks and print alerts")
    parser.add_argument("--symbol-exposure", type=float, default=None,
                        metavar="MAX_PCT",
                        help="Check single-run symbol exposure limit")
    args = parser.parse_args()

    config = load_config(args.config)

    # If --check-all, need picks
    if args.check_all or args.picks:
        picks_path = args.picks or "picks.json"
        picks = load_picks(picks_path)
    else:
        picks = []

    alerts: List[Dict[str, Any]] = []

    if args.check_all:
        alerts = run_all_checks(picks, config, args.generated_at)
    elif args.symbol_exposure is not None:
        alerts = ConcentrationAlert.check_symbol_exposure(picks, args.symbol_exposure)

    # Output
    print(json.dumps(alerts, indent=2))

    # Dispatch if webhook provided
    if args.webhook and alerts:
        sent = send_batch(alerts, args.webhook)
        print(f"\n# Sent {sent} alert(s) to webhook", file=sys.stderr)


if __name__ == "__main__":
    main()
