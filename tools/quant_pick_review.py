import csv
import json
import math
import sys
from collections import defaultdict


BLOCKED_TIERS = {"SANDBOX", "UNPROVEN", "PROBATION", "DEMOTED"}


def parse_float(value, default=0.0):
    try:
        s = str(value).strip().replace(",", "")
        if s.endswith("%"):
            s = s[:-1]
        if s == "" or s.lower() == "none":
            return default
        return float(s)
    except Exception:
        return default


def parse_ratio_or_percent(value):
    v = parse_float(value, 0.0)
    if v > 1.5:
        return v / 100.0
    return v


def normalize_asset_class(row):
    ac = str(
        row.get("Asset Class")
        or row.get("asset_class")
        or row.get("asset_class_type")
        or "CRYPTO"
    ).strip().upper()
    if ac in {"STOCKS", "PENNY_STOCK", "EQUITIES"}:
        return "EQUITY"
    if ac == "COMMODITIES":
        return "COMMODITY"
    if ac == "":
        return "CRYPTO"
    return ac


def normalize_tier(row):
    return str(row.get("Trust Tier") or row.get("trust_tier") or "").strip().upper()


def pf_from_pnls(pnls):
    wins = sum(p for p in pnls if p > 0)
    losses = sum(p for p in pnls if p < 0)
    if losses == 0:
        return math.inf if wins > 0 else 0.0
    return abs(wins / losses)


def basic_perf(rows):
    pnls = [parse_float(r.get("PnL%"), 0.0) for r in rows]
    wins = sum(1 for p in pnls if p > 0.01)
    losses = sum(1 for p in pnls if p < -0.01)
    flats = len(rows) - wins - losses
    wl = wins + losses
    wr = (wins / wl * 100.0) if wl else 0.0
    return {
        "n": len(rows),
        "wins": wins,
        "losses": losses,
        "flats": flats,
        "wr": wr,
        "avg_pnl": (sum(pnls) / len(pnls)) if rows else 0.0,
        "total_pnl": sum(pnls),
        "pf": pf_from_pnls(pnls),
    }


def passes_enhanced_profile(row):
    score = parse_float(row.get("Score"), 0.0)
    trust = parse_float(row.get("Trust Score (0-10)") or row.get("trust_score"), 0.0)
    tier = normalize_tier(row)
    fwd_wr = parse_ratio_or_percent(row.get("Forward WR") or row.get("forward_wr"))
    fwd_n = int(parse_float(row.get("Forward Trades") or row.get("forward_trades"), 0.0))
    conf = parse_ratio_or_percent(row.get("Confidence") or row.get("confidence"))
    asset = normalize_asset_class(row)

    if score < 40:
        return False
    if score < 50 and trust < 8:
        return False
    if tier in BLOCKED_TIERS:
        return False
    if fwd_n < 5:
        return False
    if fwd_wr < 0.45:
        return False
    trust_floor = 6 if asset == "CRYPTO" else 5
    if trust < trust_floor:
        return False
    if conf > 0.95 and fwd_n < 30:
        return False
    if conf > 0.90 and fwd_n < 20:
        return False
    return True


def load_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def print_asset_class_breakdown(title, rows):
    by_ac = defaultdict(list)
    for r in rows:
        by_ac[normalize_asset_class(r)].append(r)
    print(f"\n{title}")
    print("-" * len(title))
    for ac in sorted(by_ac, key=lambda k: -len(by_ac[k])):
        perf = basic_perf(by_ac[ac])
        pf = "inf" if perf["pf"] == math.inf else f'{perf["pf"]:.2f}'
        print(
            f"{ac:12} n={perf['n']:4} WR={perf['wr']:5.1f}% "
            f"avgPnL={perf['avg_pnl']:+.2f}% totalPnL={perf['total_pnl']:+.1f}% PF={pf}"
        )


def top_bottom_asset_classes(rows):
    by_ac = defaultdict(list)
    for r in rows:
        by_ac[normalize_asset_class(r)].append(r)
    items = []
    for ac, group in by_ac.items():
        perf = basic_perf(group)
        if perf["n"] >= 20:
            items.append((ac, perf))
    items.sort(key=lambda x: x[1]["wr"], reverse=True)
    return items[:3], items[-3:]


def summarize_tiers(rows):
    tiers = defaultdict(list)
    for r in rows:
        tiers[normalize_tier(r)].append(r)
    out = []
    for t, group in tiers.items():
        perf = basic_perf(group)
        out.append((t or "(empty)", perf))
    out.sort(key=lambda x: -x[1]["n"])
    return out


def main():
    if len(sys.argv) != 4:
        print("Usage: python tools/quant_pick_review.py <all_csv> <closed_csv> <active_csv>")
        sys.exit(2)

    all_rows = load_csv(sys.argv[1])
    closed_rows = load_csv(sys.argv[2])
    active_rows = load_csv(sys.argv[3])

    print("=== QUANT REVIEW: PICKS BY ASSET CLASS ===")
    print(f"All rows: {len(all_rows)} | Closed: {len(closed_rows)} | Active: {len(active_rows)}")

    closed_perf = basic_perf(closed_rows)
    print(
        f"\nClosed overall: n={closed_perf['n']} WR={closed_perf['wr']:.1f}% "
        f"avgPnL={closed_perf['avg_pnl']:+.2f}% totalPnL={closed_perf['total_pnl']:+.1f}%"
    )

    print_asset_class_breakdown("Closed performance by asset class", closed_rows)
    print_asset_class_breakdown("Active snapshot by asset class (live PnL%)", active_rows)

    # Enhanced profile comparison on closed trades (counterfactual quality uplift)
    passed_closed = [r for r in closed_rows if passes_enhanced_profile(r)]
    failed_closed = [r for r in closed_rows if not passes_enhanced_profile(r)]
    pass_perf = basic_perf(passed_closed)
    fail_perf = basic_perf(failed_closed)
    print("\nEnhanced-profile counterfactual on CLOSED trades")
    print("-------------------------------------------")
    print(
        f"Pass set: n={pass_perf['n']} ({(pass_perf['n']/len(closed_rows)*100 if closed_rows else 0):.1f}%) "
        f"WR={pass_perf['wr']:.1f}% avgPnL={pass_perf['avg_pnl']:+.2f}% totalPnL={pass_perf['total_pnl']:+.1f}%"
    )
    print(
        f"Fail set: n={fail_perf['n']} ({(fail_perf['n']/len(closed_rows)*100 if closed_rows else 0):.1f}%) "
        f"WR={fail_perf['wr']:.1f}% avgPnL={fail_perf['avg_pnl']:+.2f}% totalPnL={fail_perf['total_pnl']:+.1f}%"
    )

    # Current active quality
    passed_active = [r for r in active_rows if passes_enhanced_profile(r)]
    failed_active = [r for r in active_rows if not passes_enhanced_profile(r)]
    print("\nActive picks vs enhanced profile")
    print("--------------------------------")
    print(f"Pass active: {len(passed_active)} / {len(active_rows)}")
    print(f"Fail active: {len(failed_active)} / {len(active_rows)}")
    if passed_active:
        print("Pass-active symbols:")
        for r in passed_active:
            print(
                f"  {str(r.get('Symbol') or '?'):12} {str(r.get('Direction') or '?'):5} "
                f"ac={normalize_asset_class(r):8} "
                f"sc={parse_float(r.get('Score'), 0.0):.0f} "
                f"trust={parse_float(r.get('Trust Score (0-10)') or r.get('trust_score'), 0.0):.1f} "
                f"tier={normalize_tier(r):10} "
                f"fwdWR={parse_float(r.get('Forward WR') or r.get('forward_wr'), 0.0):.1f}% "
                f"fwdN={int(parse_float(r.get('Forward Trades') or r.get('forward_trades'), 0.0))} "
                f"livePnL={parse_float(r.get('PnL%'), 0.0):+.2f}%"
            )

    print_asset_class_breakdown("Enhanced-profile PASS set by asset class (closed)", passed_closed)

    # Tier diagnostics
    print("\nClosed performance by trust tier")
    print("-------------------------------")
    for t, perf in summarize_tiers(closed_rows):
        pf = "inf" if perf["pf"] == math.inf else f'{perf["pf"]:.2f}'
        print(
            f"{t:12} n={perf['n']:4} WR={perf['wr']:5.1f}% "
            f"avgPnL={perf['avg_pnl']:+.2f}% totalPnL={perf['total_pnl']:+.1f}% PF={pf}"
        )

    top3, bot3 = top_bottom_asset_classes(closed_rows)
    summary = {
        "closed_overall_wr": round(closed_perf["wr"], 2),
        "closed_overall_total_pnl": round(closed_perf["total_pnl"], 2),
        "enhanced_pass_n_closed": pass_perf["n"],
        "enhanced_pass_wr_closed": round(pass_perf["wr"], 2),
        "enhanced_fail_wr_closed": round(fail_perf["wr"], 2),
        "enhanced_pass_avg_pnl_closed": round(pass_perf["avg_pnl"], 4),
        "enhanced_fail_avg_pnl_closed": round(fail_perf["avg_pnl"], 4),
        "active_pass_count": len(passed_active),
        "active_total": len(active_rows),
        "top_asset_classes_by_wr_min20": [
            {"asset_class": ac, "wr": round(p["wr"], 2), "n": p["n"], "total_pnl": round(p["total_pnl"], 2)}
            for ac, p in top3
        ],
        "bottom_asset_classes_by_wr_min20": [
            {"asset_class": ac, "wr": round(p["wr"], 2), "n": p["n"], "total_pnl": round(p["total_pnl"], 2)}
            for ac, p in bot3
        ],
    }
    print("\nJSON_SUMMARY")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
