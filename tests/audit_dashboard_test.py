"""
Live HTTP smoke for findtorontoevents.ca/audit — run manually, not during pytest collection.

  python tests/audit_dashboard_test.py
"""

import sys

import requests

BASE = "https://findtorontoevents.ca/audit"
PAGES = {
    "Main Dashboard": f"{BASE}/",
    "Trading Blueprint": f"{BASE}/trading_blueprint.html",
    "Claude's Test": f"{BASE}/claudes_test.html",
    "Funds": f"{BASE}/funds.html",
    "Payload JSON": f"{BASE}/data/dashboard_payload.json",
}


def main() -> int:
    errors = []
    for name, url in PAGES.items():
        try:
            r = requests.get(url, timeout=30)
            status = r.status_code
            size = len(r.content)
            ok = status == 200 and size > 1000
            print(f"{'PASS' if ok else 'FAIL'} {name}: {status} ({size:,} bytes)")
            if not ok:
                errors.append(f"{name}: {status}")
        except Exception as e:
            print(f"FAIL {name}: {e}")
            errors.append(f"{name}: {e}")

    # Check payload data quality
    try:
        r = requests.get(f"{BASE}/data/dashboard_payload.json", timeout=30)
        if r.status_code == 200:
            data = r.json()
            systems = data.get("systems", {})
            active = data.get("active_picks", [])
            closed = data.get("recent_closed", [])
            print(
                f"\nPayload: {len(systems)} systems, {len(active)} active, {len(closed)} closed"
            )

            # Check for Trade Entry / Leverage Entry filter presence
            main_resp = requests.get(f"{BASE}/", timeout=30)
            html = main_resp.text
            has_trade_entry = (
                "Trade Entry" in html
                or "trade_entry" in html
                or "tradeEntry" in html
            )
            has_leverage_entry = (
                "Leverage Entry" in html
                or "leverage_entry" in html
                or "leverageEntry" in html
            )
            print(f"Trade Entry filter: {'FOUND' if has_trade_entry else 'MISSING'}")
            print(
                f"Leverage Entry filter: {'FOUND' if has_leverage_entry else 'MISSING'}"
            )

            # Check score distribution
            scores = [
                p.get("score", p.get("elite_score", 0)) or 0 for p in active
            ]
            if scores:
                print(
                    f"Active pick scores: min={min(scores)}, max={max(scores)}, avg={sum(scores)/len(scores):.1f}"
                )
                trade_worthy = sum(1 for s in scores if s >= 45)
                leverage_worthy = sum(1 for s in scores if s >= 60)
                print(f"Trade Worthy (45+): {trade_worthy}/{len(scores)}")
                print(f"Leverage Worthy (60+): {leverage_worthy}/{len(scores)}")

            # Check if new proven strategy picks appear
            strategies = set(p.get("strategy", "") for p in active)
            proven = [
                "rsi_capitulation",
                "beaten_majors",
                "relative_strength",
                "momentum_catcher",
                "winner_pattern",
            ]
            for s in proven:
                found = any(s in st for st in strategies)
                print(f"Strategy '{s}': {'ACTIVE' if found else 'not yet'}")
        else:
            print(f"\nPayload fetch failed: {r.status_code}")
    except Exception as e:
        print(f"\nPayload analysis error: {e}")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
