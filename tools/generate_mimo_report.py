import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

DASH = ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
ETF_REPORT = ROOT / "alpha_engine" / "new_strategies" / "etf_mean_reversion_report.json"
FUT_REPORT = ROOT / "alpha_engine" / "new_strategies" / "futures_trend_pullback_report.json"
CAND = ROOT / "audit_dashboard" / "data" / "copy_pm_high_certainty_candidates.json"
HYRO = ROOT / "audit_dashboard" / "data" / "hyrotrader_enhanced_picks.json"


def load_json(path: Path):
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _run(cmd):
    try:
        return subprocess.check_output(cmd, cwd=ROOT, shell=True, text=True).strip()
    except Exception:
        return ""


def format_table(rows, headers):
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        lines.append("| " + " | ".join(str(x) for x in r) + " |")
    return "\n".join(lines)


def main():
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%d_%H%M%S")

    dash = load_json(DASH)
    etf = load_json(ETF_REPORT)
    fut = load_json(FUT_REPORT)
    cand = load_json(CAND)
    hyro = load_json(HYRO)

    by_asset = (dash.get("performance", {}) or {}).get("by_asset_class", {}) or {}
    recent_closed = (dash.get("picks", {}) or {}).get("recent_closed", []) or []
    low = [p for p in recent_closed if (p.get("pnl_pct") is not None and p.get("pnl_pct") <= 0)]

    low_by_asset = {}
    for p in low:
        a = p.get("asset_class", "UNKNOWN")
        low_by_asset.setdefault(a, {"n": 0, "sum": 0.0})
        low_by_asset[a]["n"] += 1
        low_by_asset[a]["sum"] += float(p.get("pnl_pct") or 0)

    etf_rows = []
    for r in etf.get("results", []):
        etf_rows.append([
            r.get("symbol"),
            r.get("trades"),
            f"{r.get('win_rate', 0):.1f}%",
            f"{r.get('profit_factor', 0):.2f}",
            f"{r.get('monte_carlo', {}).get('prob_profitable', 0):.2f}",
            f"{r.get('walk_forward', {}).get('avg_oos_wr', 0):.1f}%",
        ])

    fut_rows = []
    for r in fut.get("results", []):
        fut_rows.append([
            r.get("symbol"),
            r.get("trades"),
            f"{r.get('win_rate', 0):.1f}%",
            f"{r.get('profit_factor', 0):.2f}",
            f"{r.get('monte_carlo', {}).get('prob_profitable', 0):.2f}",
            f"{r.get('walk_forward', {}).get('avg_oos_wr', 0):.1f}%",
        ])

    top_copy = cand.get("copy_candidates", [])[:10]
    top_pm = cand.get("prediction_market_candidates", [])[:10]

    hy_sum = hyro.get("enhancement_summary", {})

    recent_commits = _run("git log --oneline -n 8")
    changed = _run("git diff --name-only")

    mimo_path = DOCS / f"MIMO_{stamp}.MD"
    prsum_path = DOCS / f"PR_SUMMARY_{stamp}.MD"

    asset_rows = []
    for a, m in by_asset.items():
        low_n = low_by_asset.get(a, {}).get("n", 0)
        low_sum = low_by_asset.get(a, {}).get("sum", 0.0)
        asset_rows.append([
            a,
            m.get("closed", 0),
            f"{m.get('win_rate', 0):.1f}%",
            f"{m.get('profit_factor', 0):.2f}" if m.get("profit_factor") is not None else "n/a",
            f"{m.get('pnl', 0):.2f}%",
            low_n,
            f"{low_sum:.2f}%",
        ])

    mimo = []
    mimo.append(f"# MIMO Strategy + Edge Report ({stamp})")
    mimo.append("")
    mimo.append("## 1) Recent GitHub Commit Context")
    mimo.append("")
    mimo.append("```text")
    mimo.append(recent_commits)
    mimo.append("```")
    mimo.append("")
    mimo.append("## 2) Edge Snapshot by Asset Class")
    mimo.append("")
    mimo.append(format_table(asset_rows, ["Asset", "Closed", "WR", "PF", "Total PnL", "Low/Flat Closed", "Low/Flat PnL Sum"]))
    mimo.append("")
    mimo.append("## 3) New Strategies Implemented")
    mimo.append("")
    mimo.append("- etf_connors_rsi2_mr (new): ETF mean-reversion with protocol gates")
    mimo.append("- futures_trend_pullback (new): futures pullback model with protocol gates")
    mimo.append("- Protocol validators added: bootstrap CI, Monte Carlo profitability, anchored walk-forward")
    mimo.append("")
    mimo.append("### ETF Backtest + Protocol Validation")
    mimo.append("")
    mimo.append(format_table(etf_rows, ["Symbol", "Trades", "WR", "PF", "MC Prob+", "WF OOS WR"]))
    mimo.append("")
    mimo.append("### Futures Backtest + Protocol Validation")
    mimo.append("")
    mimo.append(format_table(fut_rows, ["Symbol", "Trades", "WR", "PF", "MC Prob+", "WF OOS WR"]))
    mimo.append("")
    mimo.append("## 4) High-Conviction Wiring Deep Check + Enhancements")
    mimo.append("")
    mimo.append("Implemented:")
    mimo.append("- Prediction-market consensus high-conviction now requires source diversity AND minimum forward quality (WR/trades) before auto-flagging")
    mimo.append("- Copy-trader bridge now enforces high-certainty history gate (min trades, WR, PF)")
    mimo.append("- HyroTrader enhanced scoring now adds short_term_entry profile with actionable/no-actionable signal")
    mimo.append("")
    mimo.append("HyroTrader summary:")
    mimo.append(f"- High conviction: {hy_sum.get('high_conviction', 0)}")
    mimo.append(f"- Moderate: {hy_sum.get('moderate', 0)}")
    mimo.append(f"- Low confidence: {hy_sum.get('low_confidence', 0)}")
    mimo.append(f"- Actionable short-term entries: {hy_sum.get('actionable_short_term', 0)}")
    mimo.append("")
    mimo.append("## 5) CopyTrader / Prediction Market High-Certainty Candidates")
    mimo.append("")
    mimo.append("Top copytrader candidates:")
    for c in top_copy:
        mimo.append(f"- {c.get('platform')} | {c.get('name')} | WR {c.get('win_rate')}% | trades {c.get('trades')} | quality {c.get('quality_score')}")
    mimo.append("")
    mimo.append("Top prediction-market candidates:")
    for p in top_pm:
        mimo.append(f"- {p.get('symbol')} {p.get('direction')} | conf {p.get('confidence')} | sources {p.get('source_count')} | quality {p.get('quality_score')}")
    mimo.append("")
    mimo.append("## 6) Practical Deployment Guidance")
    mimo.append("")
    mimo.append("- Deploy ETF strategy variants that pass protocol gates (WR>=50, PF>=1.2, MC>=0.6)")
    mimo.append("- Keep futures strategy in research-only mode until thresholds pass")
    mimo.append("- Use new high-certainty gates to reduce low-quality copy/PM signals entering active books")
    mimo.append("- For HyroTrader short-term entries, only take actionable=true picks")

    with open(mimo_path, "w", encoding="utf-8") as f:
        f.write("\n".join(mimo) + "\n")

    pr = []
    pr.append(f"# PR Summary ({stamp})")
    pr.append("")
    pr.append("## What Changed")
    pr.append("")
    for line in changed.splitlines():
        if line.strip():
            pr.append(f"- {line.strip()}")
    pr.append("")
    pr.append("## Why")
    pr.append("")
    pr.append("- Add strategy generation for low-coverage asset classes (ETF/FUTURES)")
    pr.append("- Enforce TESTING_PROTOCOL-style validation before live emission")
    pr.append("- Improve high-conviction quality control in prediction-market and copytrader pipelines")
    pr.append("- Add actionable short-term entry logic for HyroTrader panel")
    pr.append("")
    pr.append("## Expected Benefits")
    pr.append("")
    pr.append("- Better pick quality in low-sample segments")
    pr.append("- Lower false-conviction picks from weak consensus/history")
    pr.append("- Clearer real-time execution decisioning for HyroTrader")
    pr.append("- More auditable strategy validation (walk-forward + bootstrap + Monte Carlo)")
    pr.append("")
    pr.append("## Overall Summary")
    pr.append("")
    pr.append("This PR introduces new strategy research paths, adds protocol-aligned validation gates, strengthens conviction/candidate filtering, and ships documentation for edge hotspots and deployment recommendations.")

    with open(prsum_path, "w", encoding="utf-8") as f:
        f.write("\n".join(pr) + "\n")

    print(mimo_path)
    print(prsum_path)


if __name__ == "__main__":
    main()
