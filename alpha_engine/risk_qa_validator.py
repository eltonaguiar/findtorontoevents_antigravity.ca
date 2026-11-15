#!/usr/bin/env python3
"""
QA Validator — Pick Quality Assurance
=====================================

Implements QA protocol from
2026-11-15_AM_profitability_plan/parallel_agent_worktree/08_qa_validation/qa_protocol.md

QA Check 1: PnL = 0% validation against real market data
QA Check 2: Blank field flags (CRITICAL/HIGH/MEDIUM/LOW)
QA Check 3: Mutual fund solid pick validation
QA Check 4: ETF solid pick criteria
QA Check 5: Reasonability checks (price, time, PnL, cross-source)

Gates (fail-closed):
  Gate 0: PnL=0% validation passes (no CRITICAL unresolved) → block all pick emission
  Gate 1: Blank fields: zero CRITICAL unresolved → block pick emission for affected symbols
  Gate 2-4: Mutual fund / ETF / reasonability → exclude failing assets

Usage:
  python3 risk_qa_validator.py validate --picks <json_file> --market-data <json_file> [--output <json>]
  python3 risk_qa_validator.py dashboard [--output <html>]
"""

import json
import os
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path

# Required fields with severity
REQUIRED_FIELDS = {
    "entry_price": "CRITICAL",
    "exit_price": "HIGH",
    "entry_time": "CRITICAL",
    "exit_time": "HIGH",
    "take_profit": "HIGH",
    "stop_loss": "HIGH",
    "status": "CRITICAL",
    "symbol": "CRITICAL",
    "asset_class": "HIGH",
    "strategy": "HIGH",
    "resolution_method": "CRITICAL",
    "pnl_pct": "CRITICAL",
    "direction": "HIGH",
}

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _is_open(pick) -> bool:
    return str(pick.get("status") or "OPEN").upper() in {"OPEN", "ACTIVE", "PENDING", "LIVE", ""}


def check_blank_fields(pick):
    """Blank-field flags. Exit fields are not required on an open card."""
    issues = []
    skip = set()
    if _is_open(pick):
        skip = {"exit_price", "exit_time", "resolution_method", "pnl_pct"}
    for field, severity in REQUIRED_FIELDS.items():
        if field in skip:
            continue
        val = pick.get(field)
        if val is None or val == "" or (isinstance(val, float) and val != val):
            issues.append({
                "check": "blank_field",
                "field": field,
                "severity": severity,
                "pick_id": pick.get("id") or pick.get("dedup_key") or "unknown",
                "detail": f"Missing {field}",
            })
    return issues


def validate_pnl_zero(pick, market_data):
    """Validate picks with pnl_pct=0% against real market data."""
    issues = []
    pnl = pick.get("pnl_pct")
    if pnl is None or pnl == 0:
        symbol = pick.get("symbol")
        entry = pick.get("entry_price")
        exit_px = pick.get("exit_price")
        status = pick.get("status")

        if symbol and symbol in market_data:
            md = market_data[symbol]
            close_px = md.get("close_price")
            current_px = md.get("current_price")

            # Closed pick with 0% PnL but price moved
            if status in ("CLOSED", "WON", "LOST", "TP_HIT", "SL_HIT"):
                if entry and close_px:
                    direction = str(pick.get("direction") or "LONG").upper()
                    if direction == "SHORT":
                        real_pnl = (entry - close_px) / entry * 100
                    else:
                        real_pnl = (close_px - entry) / entry * 100
                    if abs(real_pnl) > 0.5:  # >0.5% move = suspicious
                        issues.append({
                            "check": "pnl_zero_but_price_moved",
                            "severity": "CRITICAL",
                            "pick_id": pick.get("id") or "unknown",
                            "reported_pnl": 0,
                            "real_pnl_pct": round(real_pnl, 2),
                            "symbol": symbol,
                            "detail": f"Closed pick shows 0% PnL but real price moved {real_pnl:+.2f}%",
                        })

            # Open position >72h without exit
            if status in ("OPEN", "ACTIVE", "PENDING", "LIVE"):
                if entry and current_px:
                    created = pick.get("created_at") or pick.get("entry_time") or pick.get("timestamp")
                    if created:
                        try:
                            created_dt = datetime.fromisoformat(str(created).replace("Z", "+00:00"))
                            now = datetime.now(timezone.utc)
                            hours = (now - created_dt).total_seconds() / 3600
                            horizon = float(pick.get("max_hold_hours") or pick.get("horizon_hours") or 72)
                            if hours > horizon:
                                direction = str(pick.get("direction") or "LONG").upper()
                                if direction == "SHORT":
                                    unrealized = (entry - current_px) / entry * 100
                                else:
                                    unrealized = (current_px - entry) / entry * 100
                                issues.append({
                                    "check": "open_past_horizon",
                                    "severity": "HIGH",
                                    "pick_id": pick.get("id") or "unknown",
                                    "hours_open": round(hours, 1),
                                    "unrealized_pnl_pct": round(unrealized, 2),
                                    "symbol": symbol,
                                    "detail": f"Open {hours:.1f}h past horizon {horizon:.0f}h, unrealized {unrealized:+.2f}%",
                                })
                        except Exception:
                            pass

    return issues


def check_reasonability(pick, market_data):
    """Sanity-check picks for obvious data errors."""
    issues = []
    symbol = pick.get("symbol")
    price = pick.get("entry_price")
    entry_time = pick.get("entry_time")
    exit_time = pick.get("exit_time")
    pnl = pick.get("pnl_pct")

    # Price reasonability
    if price is not None:
        try:
            p = float(price)
            if p <= 0:
                issues.append({
                    "check": "price_non_positive",
                    "severity": "CRITICAL",
                    "pick_id": pick.get("id") or "unknown",
                    "detail": f"Entry price {p} is not positive",
                })
            elif p > 1000000:
                issues.append({
                    "check": "price_unreasonably_high",
                    "severity": "HIGH",
                    "pick_id": pick.get("id") or "unknown",
                    "detail": f"Entry price {p} exceeds 1M",
                })
        except (ValueError, TypeError):
            issues.append({
                "check": "price_invalid",
                "severity": "CRITICAL",
                "pick_id": pick.get("id") or "unknown",
                "detail": f"Entry price {price} is not a valid number",
            })

    # Time reasonability
    if entry_time and exit_time:
        try:
            et = datetime.fromisoformat(str(entry_time).replace("Z", "+00:00"))
            xt = datetime.fromisoformat(str(exit_time).replace("Z", "+00:00"))
            if xt < et:
                issues.append({
                    "check": "exit_before_entry",
                    "severity": "CRITICAL",
                    "pick_id": pick.get("id") or "unknown",
                    "detail": "Exit time is before entry time",
                })
        except Exception:
            pass

    # PnL reasonability
    if pnl is not None:
        try:
            p = float(pnl)
            if abs(p) > 500:
                issues.append({
                    "check": "pnl_extreme",
                    "severity": "CRITICAL",
                    "pick_id": pick.get("id") or "unknown",
                    "detail": f"|PnL| {p}% exceeds 500% — possibly corrupt",
                })
        except (ValueError, TypeError):
            pass

    # Cross-source consistency (if we have market data)
    if symbol and symbol in market_data and price is not None:
        md = market_data[symbol]
        close_px = md.get("close_price")
        market_date = str(md.get("asof") or md.get("date") or "")[:10]
        entry_date = str(pick.get("entry_date") or "")[:10]
        if market_date and entry_date and market_date != entry_date:
            close_px = None  # different session — not a same-bar disagreement
        if close_px and close_px > 0:
            try:
                p = float(price)
                diff = abs(p - close_px) / close_px * 100
                if diff > 2:
                    issues.append({
                        "check": "price_cross_source_disagreement",
                        "severity": "MEDIUM",
                        "pick_id": pick.get("id") or "unknown",
                        "detail": f"Entry price differs from market close by {diff:.1f}%",
                    })
            except (ValueError, TypeError):
                pass

    return issues


def validate_mutual_fund(fund):
    """Validate mutual fund against hard gates for passive core allocation."""
    gates = {
        "expense_ratio": fund.get("expense_ratio", 999) <= 0.0009,      # ≤ 0.09%
        "no_load": fund.get("load", 1) == 0,
        "no_12b1": fund.get("b_12b1", 1) == 0,
        "min_initial": fund.get("min_initial", 999999) <= 1000,
        "aum": fund.get("aum", 0) >= 1_000_000_000,                     # ≥ $1B
        "turnover": fund.get("turnover", 999) <= 0.20,                  # ≤ 20%
        "tracking_error": fund.get("tracking_error", 999) <= 0.0025,    # ≤ 0.25%
        "track_record_years": fund.get("track_record_years", 0) >= 10,
        "nav_freshness_hours": fund.get("nav_freshness_hours", 999) <= 24,
    }
    passed = all(gates.values())
    failed = [k for k, v in gates.items() if not v]
    return {"passed": passed, "failed_gates": failed, "gates": gates}


def validate_etf(etf):
    """Validate ETF against hard gates for passive core allocation."""
    gates = {
        "expense_ratio": etf.get("expense_ratio", 999) <= 0.0010,       # ≤ 0.10%
        "aum": etf.get("aum", 0) >= 500_000_000,                        # ≥ $500M
        "avg_daily_volume": etf.get("avg_daily_volume", 0) >= 10_000_000,  # ≥ $10M
        "bid_ask_spread": etf.get("bid_ask_spread", 999) <= 0.0005,     # ≤ 0.05%
        "tracking_error": etf.get("tracking_error", 999) <= 0.0020,     # ≤ 0.20%
        "track_record_years": etf.get("track_record_years", 0) >= 5,
        "no_leverage_inverse": etf.get("leverage", 1) == 1 and not etf.get("inverse", False),
    }
    passed = all(gates.values())
    failed = [k for k, v in gates.items() if not v]
    return {"passed": passed, "failed_gates": failed, "gates": gates}


def validate_pick(pick, market_data):
    """Run all QA checks on a single pick. Returns issue list + gate status."""
    issues = []

    # QA Check 2: Blank fields
    issues.extend(check_blank_fields(pick))

    # QA Check 1: PnL=0% validation
    issues.extend(validate_pnl_zero(pick, market_data))

    # QA Check 5: Reasonability
    issues.extend(check_reasonability(pick, market_data))

    # Determine gate status
    critical = [i for i in issues if i.get("severity") == "CRITICAL"]
    gate_0_pass = len(critical) == 0
    gate_1_pass = len(critical) == 0  # same for now

    return {
        "pick_id": pick.get("id") or pick.get("dedup_key") or "unknown",
        "symbol": pick.get("symbol"),
        "issues": issues,
        "critical_count": len(critical),
        "high_count": len([i for i in issues if i.get("severity") == "HIGH"]),
        "gate_0_pass": gate_0_pass,
        "gate_1_pass": gate_1_pass,
    }


def validate_all(picks, market_data, mutual_funds=None, etfs=None):
    """Validate all picks and return aggregate results."""
    pick_results = []
    for pick in picks:
        pick_results.append(validate_pick(pick, market_data))

    # Gate evaluations
    gate_0_fail = [r for r in pick_results if not r["gate_0_pass"]]
    gate_1_fail = [r for r in pick_results if not r["gate_1_pass"]]

    # Mutual fund validation
    mf_results = []
    if mutual_funds:
        for mf in mutual_funds:
            mf_results.append({
                "symbol": mf.get("symbol"),
                "validation": validate_mutual_fund(mf),
            })

    # ETF validation
    etf_results = []
    if etfs:
        for etf in etfs:
            etf_results.append({
                "symbol": etf.get("symbol"),
                "validation": validate_etf(etf),
            })

    # Overall QA status
    gate_2_pass = all(mf["validation"]["passed"] for mf in mf_results) if mf_results else True
    gate_3_pass = all(etf["validation"]["passed"] for etf in etf_results) if etf_results else True
    gate_4_pass = len(gate_0_fail) == 0  # reasonability CRITICAL unresolved blocks

    all_gates_pass = all([gate_0_pass := len(gate_0_fail) == 0,
                          gate_1_pass := len(gate_1_fail) == 0,
                          gate_2_pass, gate_3_pass, gate_4_pass])

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_picks": len(picks),
        "pick_results": pick_results,
        "gate_0_pnl_zero": {"pass": len(gate_0_fail) == 0, "failures": gate_0_fail},
        "gate_1_blank_fields": {"pass": len(gate_1_fail) == 0, "failures": gate_1_fail},
        "gate_2_mutual_funds": {"pass": gate_2_pass, "results": mf_results},
        "gate_3_etfs": {"pass": gate_3_pass, "results": etf_results},
        "gate_4_reasonability": {"pass": gate_4_pass, "failures": gate_0_fail},
        "all_gates_pass": all_gates_pass,
        "qa_status": "PASS" if all_gates_pass else "FAIL",
    }


def generate_dashboard_html(result):
    """Generate a simple HTML QA dashboard."""
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>QA Dashboard</title>
<style>
body {{ font-family: monospace; margin: 20px; }}
.pass {{ color: green; }}
.fail {{ color: red; }}
.warn {{ color: orange; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
th {{ background: #f4f4f4; }}
.critical {{ color: red; font-weight: bold; }}
.high {{ color: orange; }}
</style>
</head>
<body>
<h1>QA Validation Dashboard</h1>
<p>Generated: {result['generated_at']}</p>
<p>Total picks: {result['total_picks']}</p>
<p><strong>Overall QA Status: <span class="{'pass' if result['qa_status']=='PASS' else 'fail'}">{result['qa_status']}</span></strong></p>

<h2>Gate Results</h2>
<table>
<tr><th>Gate</th><th>Status</th><th>Failures</th></tr>
<tr><td>Gate 0 — PnL=0% validation</td><td class="{'pass' if result['gate_0_pnl_zero']['pass'] else 'fail'}">{'PASS' if result['gate_0_pnl_zero']['pass'] else 'FAIL'}</td><td>{len(result['gate_0_pnl_zero']['failures'])}</td></tr>
<tr><td>Gate 1 — Blank fields</td><td class="{'pass' if result['gate_1_blank_fields']['pass'] else 'fail'}">{'PASS' if result['gate_1_blank_fields']['pass'] else 'FAIL'}</td><td>{len(result['gate_1_blank_fields']['failures'])}</td></tr>
<tr><td>Gate 2 — Mutual funds</td><td class="{'pass' if result['gate_2_mutual_funds']['pass'] else 'fail'}">{'PASS' if result['gate_2_mutual_funds']['pass'] else 'FAIL'}</td><td>{len(result['gate_2_mutual_funds']['results'])} checked</td></tr>
<tr><td>Gate 3 — ETFs</td><td class="{'pass' if result['gate_3_etfs']['pass'] else 'fail'}">{'PASS' if result['gate_3_etfs']['pass'] else 'FAIL'}</td><td>{len(result['gate_3_etfs']['results'])} checked</td></tr>
<tr><td>Gate 4 — Reasonability</td><td class="{'pass' if result['gate_4_reasonability']['pass'] else 'fail'}">{'PASS' if result['gate_4_reasonability']['pass'] else 'FAIL'}</td><td>{len(result['gate_4_reasonability']['failures'])}</td></tr>
</table>

<h2>Pick Issues</h2>
<table>
<tr><th>Pick ID</th><th>Symbol</th><th>Critical</th><th>High</th><th>Issues</th></tr>
"""
    for r in result["pick_results"]:
        if r["issues"]:
            issue_desc = "; ".join(f"{i['check']}({i['severity']})" for i in r["issues"])
            html += f"<tr><td>{r['pick_id']}</td><td>{r['symbol']}</td><td class='critical'>{r['critical_count']}</td><td class='high'>{r['high_count']}</td><td>{issue_desc}</td></tr>"

    html += "</table></body></html>"
    return html


def main():
    parser = argparse.ArgumentParser(description="QA Validator")
    sub = parser.add_subparsers(dest="command")

    val_p = sub.add_parser("validate", help="Validate picks against QA gates")
    val_p.add_argument("--picks", required=True, help="Path to picks JSON file")
    val_p.add_argument("--market-data", required=True, help="Path to market data JSON file")
    val_p.add_argument("--mutual-funds", help="Path to mutual funds JSON file")
    val_p.add_argument("--etfs", help="Path to ETFs JSON file")
    val_p.add_argument("--output", help="Output JSON path")

    dash_p = sub.add_parser("dashboard", help="Generate QA dashboard HTML")
    dash_p.add_argument("--picks", required=True)
    dash_p.add_argument("--market-data", required=True)
    dash_p.add_argument("--output", default="qa_dashboard.html")

    args = parser.parse_args()

    if args.command == "validate":
        picks = load_json(args.picks)
        if isinstance(picks, dict):
            picks = picks.get("picks", picks.get("candidates", [picks]))
        elif not isinstance(picks, list):
            picks = [picks]

        market_data = load_json(args.market_data)
        mfs = load_json(args.mutual_funds) if args.mutual_funds else None
        etfs = load_json(args.etfs) if args.etfs else None

        result = validate_all(picks, market_data, mfs, etfs)

        if args.output:
            save_json(args.output, result)
            print(f"QA results saved to {args.output}")
        else:
            print(json.dumps(result, indent=2, default=str))

        print(f"\nOverall QA Status: {result['qa_status']}")
        print(f"All gates pass: {result['all_gates_pass']}")

    elif args.command == "dashboard":
        picks = load_json(args.picks)
        if isinstance(picks, dict):
            picks = picks.get("picks", picks.get("candidates", [picks]))
        elif not isinstance(picks, list):
            picks = [picks]

        market_data = load_json(args.market_data)
        result = validate_all(picks, market_data)

        html = generate_dashboard_html(result)
        with open(args.output, "w") as f:
            f.write(html)
        print(f"Dashboard saved to {args.output}")
        print(f"QA Status: {result['qa_status']}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
