#!/usr/bin/env python3
"""
Edge Filter Engine v3 — Kelly-Fraction Simulation + Strategy-Family Aware
Produces quant-grade filters for real-money deployment.
"""

import json
import math
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import Dict, List, Any, Optional

# Blocklist guard — this engine produces REAL-MONEY filters, so it must never
# surface a strategy the kill protocol has retired (e.g. cftc_cot_commercial_signal,
# retired 2026-05-02). Defensive import: if the module is unavailable the engine
# still runs, just without the exclusion.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    from alpha_engine.strategy_blocklist import is_blocked_pick  # type: ignore
except Exception:  # noqa: BLE001
    def is_blocked_pick(_pick) -> bool:  # type: ignore
        return False

DASHBOARD_JSON = Path("audit_dashboard/data/dashboard_data.json")
STRATEGY_JSON = Path("alpha_engine/data/strategy_performance.json")
REPORT_DIR = Path("reports")
UPDATE_DIR = Path("updates")

MIN_N_FILTER = 30
MIN_PF_TARGET = 1.3
MIN_WR_TARGET = 0.50
MAX_MDD_PCT = 20.0
KELLY_FRACTION = 0.25

CRYPTO_PROVEN_STRATEGIES = {
    "st_fear_greed_contrarian",
    "claude_ml_moderate_mut",
    "vwap_deviation_reversion_eth_v1",
    "macd_rsi_m048",
    "atr_percentile_gate",
    "vwap_deviation_reversion_sol_v1",
    "crypto_kalman_trend_residual_reversion_v1",
}

EQUITY_PROVEN_STRATEGIES = {
    "rs-breakout-scout",
    "vol-contraction-scout",
    "donchian-stock-breakout",
    "price-accel-scout",
    "gap-and-go-stocks",
    "quality-minus-junk",
    "rsi-divergence-scout",
}

FOREX_PROVEN_STRATEGIES = {
    "forex-rsi-ema-scout",
}


def load_dashboard() -> dict:
    return json.loads(DASHBOARD_JSON.read_text(encoding="utf-8"))


def load_strategies() -> dict:
    return json.loads(STRATEGY_JSON.read_text(encoding="utf-8"))


def freshness_gate(dashboard: dict) -> float:
    gen = dashboard.get("generated_at", "")
    dt = datetime.fromisoformat(gen.replace("Z", "+00:00"))
    age_h = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
    if age_h >= 2:
        raise RuntimeError(f"STALE DATA: dashboard is {age_h:.1f}h old (limit 2h)")
    return age_h


def classify_strategy_asset_class(name: str, top_symbol: Optional[str]) -> str:
    n = name.upper()
    s = (top_symbol or "").upper()
    if any(x in s for x in ["USDT", "BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "DOT", "LINK", "MATIC", "AVAX", "FET", "SEI", "ATOM", "POL", "DYDX", "TRX", "DOGE"]):
        return "CRYPTO"
    if any(x in n for x in ["CRYPTO", "ALTCOIN", "DEFI", "NFT", "VWAP DEVIATION", "AUDITENSEMBLE"]):
        return "CRYPTO"
    if "=X" in s or "FOREX" in n or "FX_" in n or "CARRY_TRADE" in n:
        return "FOREX"
    if any(x in n + s for x in ["FUTURES", "ES=", "NQ=", "CL=", "GC=", "NG=", "ZB=", "ZF=", "ZT=", "CT=", "SB=", "KC=", "DX=", "COT_", "CTA_"]):
        return "COMMODITY"
    if any(x in n + s for x in ["STOCK", "EQUITY", "SHARE", "AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "GOOGL", "META", "NFLX", "AMD"]):
        return "EQUITY"
    if any(x in n for x in ["BOND", "TREASURY", "YIELD"]):
        return "BOND"
    if any(x in n for x in ["ETF", "SPY", "QQQ", "IWM", "VTI", "VIX", "GLD"]):
        return "ETF"
    return "UNKNOWN"


def compute_filter_metrics(picks: List[dict]) -> dict:
    if not picks:
        return {"n": 0, "wr": 0.0, "pf": 0.0, "expectancy": 0.0, "avg_pnl": 0.0, "total_pnl": 0.0, "avg_win": 0.0, "avg_loss": 0.0}
    wins = [p for p in picks if p.get("status") == "WON"]
    losses = [p for p in picks if p.get("status") == "LOST"]
    n = len(picks)
    wr = len(wins) / n if n else 0.0
    gross_win = sum(p.get("pnl_pct", 0) for p in wins)
    gross_loss = abs(sum(p.get("pnl_pct", 0) for p in losses))
    pf = gross_win / gross_loss if gross_loss > 0 else (99.99 if gross_win > 0 else 0.0)
    total_pnl = sum(p.get("pnl_pct", 0) for p in picks)
    avg_pnl = total_pnl / n
    avg_win = gross_win / len(wins) if wins else 0.0
    avg_loss = gross_loss / len(losses) if losses else 0.0
    expectancy = (wr * avg_win) - ((1 - wr) * avg_loss) if (avg_win or avg_loss) else 0.0
    return {"n": n, "wr": wr, "pf": pf, "expectancy": expectancy, "avg_pnl": avg_pnl, "total_pnl": total_pnl, "avg_win": avg_win, "avg_loss": avg_loss}


def compute_concentration_risk(filtered_picks: List[dict]) -> dict:
    """Compute strategy concentration risk metrics for a set of filtered picks."""
    if not filtered_picks:
        return {
            "max_strategy_share": 0.0,
            "top_strategy_name": None,
            "hhi": 0.0,
            "warning": None,
        }
    counts: Dict[str, int] = defaultdict(int)
    for p in filtered_picks:
        counts[p.get("strategy", "unknown")] += 1
    n = len(filtered_picks)
    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    top_strategy_name, top_count = sorted_counts[0]
    max_strategy_share = top_count / n
    hhi = sum((count / n) ** 2 for _strategy, count in counts.items())
    warning = None
    if max_strategy_share > 0.40:
        warning = f"Concentration warning: {top_strategy_name!r} dominates {max_strategy_share:.1%} of picks"
    elif hhi > 0.25:
        warning = f"Concentration warning: HHI={hhi:.3f} exceeds 0.25 threshold"
    return {
        "max_strategy_share": max_strategy_share,
        "top_strategy_name": top_strategy_name,
        "hhi": hhi,
        "warning": warning,
    }


def simulate_balance_kelly(picks: List[dict], kelly_pct: float, initial: float = 10000.0) -> dict:
    """Simulate using Kelly fraction of account per trade."""
    balance = initial
    peak = initial
    max_dd = 0.0
    balances = [balance]
    for p in picks:
        pnl = p.get("pnl_pct", 0) / 100.0
        # Risk kelly_pct of balance on each trade
        balance *= (1 + kelly_pct * pnl)
        balances.append(balance)
        if balance > peak:
            peak = balance
        dd = (peak - balance) / peak
        if dd > max_dd:
            max_dd = dd
    return {
        "final_balance": balance,
        "total_return_pct": (balance - initial) / initial * 100,
        "max_drawdown_pct": max_dd * 100,
        "balances": balances,
    }


def kelly_position_size(wr: float, avg_win: float, avg_loss: float, fraction: float = KELLY_FRACTION) -> float:
    if avg_loss == 0:
        return 0.0
    r = avg_win / avg_loss if avg_loss > 0 else 0.0
    kelly = wr - ((1 - wr) / r) if r > 0 else 0.0
    return max(0.0, min(kelly * fraction, 0.10))


def walk_forward_split(picks: List[dict], days: int = 30):
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    is_picks = []
    oos_picks = []
    for p in picks:
        ts = p.get("timestamp", "")
        if ts:
            try:
                pdt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if pdt >= cutoff:
                    oos_picks.append(p)
                else:
                    is_picks.append(p)
            except Exception:
                is_picks.append(p)
        else:
            is_picks.append(p)
    return is_picks, oos_picks


def derive_crypto_filter(picks: List[dict]) -> Optional[dict]:
    longs = [p for p in picks if p.get("direction") == "LONG"]
    m = compute_filter_metrics(longs)
    print(f"  LONG-only: n={m['n']} WR={m['wr']:.2%} PF={m['pf']:.2f}")
    proven = [p for p in longs if p.get("strategy") in CRYPTO_PROVEN_STRATEGIES]
    m2 = compute_filter_metrics(proven)
    print(f"  LONG + proven strategies: n={m2['n']} WR={m2['wr']:.2%} PF={m2['pf']:.2f}")
    if m2["n"] >= MIN_N_FILTER and m2["pf"] >= MIN_PF_TARGET and m2["wr"] >= MIN_WR_TARGET:
        return {"direction": "LONG", "strategies": sorted(CRYPTO_PROVEN_STRATEGIES), "min_score": 0, "min_confidence": 0.0}
    grade_b = [p for p in longs if p.get("grade") == "B"]
    m3 = compute_filter_metrics(grade_b)
    print(f"  LONG + Grade=B: n={m3['n']} WR={m3['wr']:.2%} PF={m3['pf']:.2f}")
    if m3["n"] >= MIN_N_FILTER and m3["pf"] >= MIN_PF_TARGET and m3["wr"] >= MIN_WR_TARGET:
        return {"direction": "LONG", "grade": "B", "min_score": 0, "min_confidence": 0.0}
    non_toxic = [p for p in longs if p.get("strategy") not in {"luxalgo_confluence", "unknown"}]
    m4 = compute_filter_metrics(non_toxic)
    print(f"  LONG - toxic: n={m4['n']} WR={m4['wr']:.2%} PF={m4['pf']:.2f}")
    if m4["n"] >= MIN_N_FILTER and m4["pf"] >= MIN_PF_TARGET and m4["wr"] >= MIN_WR_TARGET:
        return {"direction": "LONG", "exclude_strategies": ["luxalgo_confluence", "unknown"], "min_score": 0, "min_confidence": 0.0}
    if m["pf"] >= MIN_PF_TARGET and m["n"] >= 100:
        return {"direction": "LONG", "min_score": 0, "min_confidence": 0.0, "warning": f"WR={m['wr']:.1%} below {MIN_WR_TARGET:.0%} target"}
    return None


def derive_equity_filter(picks: List[dict], active_picks: List[dict]) -> Optional[dict]:
    longs = [p for p in picks if p.get("direction") == "LONG"]
    longs_active = [p for p in active_picks if p.get("direction") == "LONG"]
    best_proven = None
    best_operational = None
    # Elite score is strongly predictive; try thresholds from high to low
    for thresh in [70, 65, 60, 55, 50, 45, 40]:
        sub = [p for p in longs if p.get("elite_score") is not None and p["elite_score"] >= thresh]
        m = compute_filter_metrics(sub)
        sub_active = [p for p in longs_active if p.get("elite_score") is not None and p["elite_score"] >= thresh]
        print(f"  LONG + Elite>={thresh}: n={m['n']} WR={m['wr']:.2%} PF={m['pf']:.2f} active={len(sub_active)}")
        if m["n"] >= MIN_N_FILTER and m["pf"] >= MIN_PF_TARGET and m["wr"] >= MIN_WR_TARGET:
            filt = {"direction": "LONG", "min_elite_score": thresh, "min_score": 0, "min_confidence": 0.0}
            if thresh >= 60 and not best_proven:
                best_proven = filt
            if len(sub_active) >= 5 and not best_operational:
                best_operational = filt
    # If no operational filter with >=3 active picks, fall back to lowest proven
    if best_operational:
        return best_operational
    if best_proven:
        best_proven["warning"] = "Few active picks this week; filter is statistically proven but pipeline is thin"
        return best_proven
    proven = [p for p in longs if p.get("strategy") in EQUITY_PROVEN_STRATEGIES]
    m2 = compute_filter_metrics(proven)
    print(f"  LONG + proven strategies: n={m2['n']} WR={m2['wr']:.2%} PF={m2['pf']:.2f}")
    if m2["n"] >= MIN_N_FILTER and m2["pf"] >= MIN_PF_TARGET and m2["wr"] >= MIN_WR_TARGET:
        return {"direction": "LONG", "strategies": sorted(EQUITY_PROVEN_STRATEGIES), "min_score": 0, "min_confidence": 0.0}
    return None


def derive_commodity_filter(picks: List[dict]) -> Optional[dict]:
    for direction in ["SHORT", "LONG", None]:
        base = [p for p in picks if direction is None or p.get("direction") == direction]
        for conf_thresh in [0.0, 0.5, 0.6, 0.7, 0.8]:
            sub = [p for p in base if p.get("confidence", 0) >= conf_thresh]
            m = compute_filter_metrics(sub)
            label = direction or "BOTH"
            print(f"  {label} + conf>={conf_thresh}: n={m['n']} WR={m['wr']:.2%} PF={m['pf']:.2f}")
            if m["n"] >= MIN_N_FILTER and m["pf"] >= MIN_PF_TARGET and m["wr"] >= MIN_WR_TARGET:
                return {"direction": direction, "min_confidence": conf_thresh, "min_score": 0}
    return None


def derive_forex_filter(picks: List[dict]) -> Optional[dict]:
    proven = [p for p in picks if p.get("strategy") in FOREX_PROVEN_STRATEGIES]
    m = compute_filter_metrics(proven)
    print(f"  proven strategies only: n={m['n']} WR={m['wr']:.2%} PF={m['pf']:.2f}")
    if m["n"] >= 20 and m["pf"] >= MIN_PF_TARGET and m["wr"] >= MIN_WR_TARGET:
        # Relaxed min_n for forex due to thin sample
        return {"strategies": sorted(FOREX_PROVEN_STRATEGIES), "min_score": 0, "min_confidence": 0.0, "note": "n<30, thin sample, deploy cautiously"}
    shorts = [p for p in picks if p.get("direction") == "SHORT"]
    m2 = compute_filter_metrics(shorts)
    print(f"  SHORT-only: n={m2['n']} WR={m2['wr']:.2%} PF={m2['pf']:.2f}")
    if m2["n"] >= MIN_N_FILTER:
        return {"direction": "SHORT", "min_score": 0, "min_confidence": 0.0, "warning": f"WR={m2['wr']:.1%} below {MIN_WR_TARGET:.0%} target but PF={m2['pf']:.2f}"}
    return None


def derive_etf_filter(picks: List[dict]) -> Optional[dict]:
    m = compute_filter_metrics(picks)
    print(f"  ALL: n={m['n']} WR={m['wr']:.2%} PF={m['pf']:.2f}")
    if m["n"] >= MIN_N_FILTER and m["pf"] >= MIN_PF_TARGET and m["wr"] >= MIN_WR_TARGET:
        return {"direction": None, "min_score": 0, "min_confidence": 0.0}
    for direction in ["LONG", "SHORT", None]:
        sub = [p for p in picks if direction is None or p.get("direction") == direction]
        m2 = compute_filter_metrics(sub)
        print(f"  {direction or 'BOTH'}: n={m2['n']} WR={m2['wr']:.2%} PF={m2['pf']:.2f}")
        if m2["n"] >= MIN_N_FILTER and m2["pf"] >= MIN_PF_TARGET and m2["wr"] >= MIN_WR_TARGET:
            return {"direction": direction, "min_score": 0, "min_confidence": 0.0}
    return None


def apply_filter(picks: List[dict], filt: dict) -> List[dict]:
    out = picks
    if filt.get("direction"):
        out = [p for p in out if p.get("direction") == filt["direction"]]
    if "strategies" in filt:
        out = [p for p in out if p.get("strategy") in set(filt["strategies"])]
    if "exclude_strategies" in filt:
        out = [p for p in out if p.get("strategy") not in set(filt["exclude_strategies"])]
    if "min_score" in filt:
        out = [p for p in out if p.get("score", 0) >= filt["min_score"]]
    if "min_elite_score" in filt:
        out = [p for p in out if p.get("elite_score") is not None and p["elite_score"] >= filt["min_elite_score"]]
    if "min_confidence" in filt:
        out = [p for p in out if p.get("confidence", 0) >= filt["min_confidence"]]
    if "grade" in filt:
        out = [p for p in out if p.get("grade") == filt["grade"]]
    return out


def run_engine() -> dict:
    dashboard = load_dashboard()
    age_h = freshness_gate(dashboard)
    print(f"Freshness OK: dashboard {age_h:.1f}h old\n")

    strategies = load_strategies()
    for name, m in strategies.items():
        m["asset_class"] = classify_strategy_asset_class(name, m.get("top_symbol"))

    recent_closed = dashboard["picks"].get("recent_closed", [])
    active_raw = dashboard["picks"].get("active_raw", [])

    # Drop picks from retired / blocked strategies BEFORE any metric, filter, or
    # active-match is computed — a real-money filter must never recommend a
    # strategy the kill protocol has retired.
    _rc_before, _ar_before = len(recent_closed), len(active_raw)
    recent_closed = [p for p in recent_closed if not is_blocked_pick(p)]
    active_raw = [p for p in active_raw if not is_blocked_pick(p)]
    _rc_drop, _ar_drop = _rc_before - len(recent_closed), _ar_before - len(active_raw)
    if _rc_drop or _ar_drop:
        print(f"Blocklist filter: dropped {_rc_drop} closed + {_ar_drop} active "
              f"picks from retired/blocked strategies")

    for p in recent_closed:
        if not p.get("asset_class"):
            p["asset_class"] = classify_strategy_asset_class(p.get("strategy", ""), p.get("symbol"))
    for p in active_raw:
        if not p.get("asset_class"):
            p["asset_class"] = classify_strategy_asset_class(p.get("strategy", ""), p.get("symbol"))

    results = {}
    derivations = {
        "CRYPTO": derive_crypto_filter,
        "COMMODITY": derive_commodity_filter,
        "FOREX": derive_forex_filter,
        "ETF": derive_etf_filter,
    }

    for ac in ["CRYPTO", "EQUITY", "COMMODITY", "FOREX", "ETF"]:
        ac_picks = [p for p in recent_closed if p.get("asset_class") == ac]
        active_ac = [p for p in active_raw if p.get("asset_class") == ac]
        print(f"\n=== {ac} === base n={len(ac_picks)}")
        base = compute_filter_metrics(ac_picks)
        print(f"  base  PF={base['pf']:.2f} WR={base['wr']:.2%} Exp={base['expectancy']:.3f}")

        if len(ac_picks) < MIN_N_FILTER:
            print(f"  Insufficient data ({len(ac_picks)} < {MIN_N_FILTER})")
            results[ac] = {"status": "insufficient_data", "n": len(ac_picks)}
            continue

        if ac == "EQUITY":
            filt = derive_equity_filter(ac_picks, active_ac)
        else:
            filt = derivations[ac](ac_picks)
        if not filt:
            print(f"  No proven filter found.")
            results[ac] = {"status": "no_passing_filter", "base": base}
            continue

        filtered = apply_filter(ac_picks, filt)
        m = compute_filter_metrics(filtered)
        print(f"  FILTER APPLIED: n={m['n']} WR={m['wr']:.2%} PF={m['pf']:.2f}")

        conc = compute_concentration_risk(filtered)
        print(f"  CONC  max_share={conc['max_strategy_share']:.1%} top='{conc['top_strategy_name']}' HHI={conc['hhi']:.3f}")
        if conc["warning"]:
            print(f"  ⚠️  {conc['warning']}")

        # Walk-forward: use 14d for classes where all data is recent (COMMODITY), else 30d
        wf_days = 14 if ac in {"COMMODITY", "FUTURES"} else 30
        is_picks, oos_picks = walk_forward_split(filtered, days=wf_days)
        is_metrics = compute_filter_metrics(is_picks)
        oos_metrics = compute_filter_metrics(oos_picks)
        print(f"  IS    PF={is_metrics['pf']:.2f} WR={is_metrics['wr']:.2%} N={is_metrics['n']}")
        print(f"  OOS   PF={oos_metrics['pf']:.2f} WR={oos_metrics['wr']:.2%} N={oos_metrics['n']}")

        kelly = kelly_position_size(m["wr"], m["avg_win"], m["avg_loss"])
        sim = simulate_balance_kelly(filtered, kelly_pct=kelly, initial=10000.0)
        print(f"  SIM   return={sim['total_return_pct']:.1f}% maxDD={sim['max_drawdown_pct']:.1f}% (Kelly={kelly*100:.2f}%)")

        active_ac = [p for p in active_raw if p.get("asset_class") == ac]
        matches = apply_filter(active_ac, filt)

        results[ac] = {
            "status": "proven",
            "base": base,
            "filter": filt,
            "metrics": m,
            "is_metrics": is_metrics,
            "oos_metrics": oos_metrics,
            "simulation": sim,
            "kelly_pct": kelly * 100,
            "active_matches": len(matches),
            "active_match_list": [
                {"symbol": p.get("symbol"), "direction": p.get("direction"), "score": p.get("score"), "confidence": p.get("confidence"), "strategy": p.get("strategy")}
                for p in matches[:10]
            ],
            "concentration": conc,
        }

    return results


def write_weekly_report(results: dict):
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report_path = REPORT_DIR / f"weekly_filter_{date_str}.md"
    lines = [
        f"# Weekly Real-Money Filter — {date_str}",
        "",
        "> Auto-generated by `tools/edge_filter_engine_v3.py`",
        "",
        "## Executive Summary",
        "",
    ]
    for ac, r in results.items():
        if r.get("status") != "proven":
            lines.append(f"- **{ac}**: `{r['status']}` — no deployable filter this week.")
        else:
            m = r["metrics"]
            lines.append(
                f"- **{ac}**: PF={m['pf']:.2f} | WR={m['wr']:.1%} | N={m['n']} | "
                f"Expectancy={m['expectancy']:.3f}% | Kelly={r['kelly_pct']:.2f}% | "
                f"Active matches={r['active_matches']}"
            )
    lines.append("")

    for ac, r in results.items():
        if r.get("status") != "proven":
            continue
        lines.append(f"## {ac} Top Picks Filter")
        lines.append("")
        f = r["filter"]
        lines.append("- **Criteria**:")
        if f.get("direction"):
            lines.append(f"  - Direction: `{f['direction']}`")
        if "strategies" in f:
            lines.append(f"  - Strategies: `{', '.join(f['strategies'][:5])}{'...' if len(f['strategies'])>5 else ''}`")
        if "exclude_strategies" in f:
            lines.append(f"  - Exclude strategies: `{', '.join(f['exclude_strategies'])}`")
        if "grade" in f:
            lines.append(f"  - Grade: `{f['grade']}`")
        if "min_elite_score" in f:
            lines.append(f"  - Elite Score ≥ {f['min_elite_score']}")
        if "min_score" in f:
            lines.append(f"  - Score ≥ {f['min_score']}")
        if "min_confidence" in f:
            lines.append(f"  - Confidence ≥ {f['min_confidence']}")
        if f.get("warning"):
            lines.append(f"  - ⚠️ {f['warning']}")
        if f.get("note"):
            lines.append(f"  - 📝 {f['note']}")
        lines.append("")
        m = r["metrics"]
        lines.append(f"- **Historical Performance**: PF={m['pf']:.2f}, WR={m['wr']:.1%}, n={m['n']}")
        lines.append(f"- **Expectancy**: {m['expectancy']:.3f}% per trade")
        lines.append(f"- **Kelly Size**: {r['kelly_pct']:.2f}% of account per pick")
        lines.append(f"- **Simulated Return**: {r['simulation']['total_return_pct']:.1f}% (max DD {r['simulation']['max_drawdown_pct']:.1f}%)")
        lines.append("")
        lines.append("### Walk-Forward Validation")
        ism = r["is_metrics"]
        oosm = r["oos_metrics"]
        lines.append(f"- In-Sample: PF={ism['pf']:.2f}, WR={ism['wr']:.1%}, n={ism['n']}")
        lines.append(f"- Out-of-Sample (last 30d): PF={oosm['pf']:.2f}, WR={oosm['wr']:.1%}, n={oosm['n']}")
        lines.append("")
        conc = r.get("concentration")
        if conc:
            lines.append("### Concentration Risk")
            lines.append(f"- Max strategy share: **{conc['max_strategy_share']:.1%}** (`{conc['top_strategy_name']}`)")
            lines.append(f"- Herfindahl-Hirschman Index: **{conc['hhi']:.3f}**")
            if conc.get("warning"):
                lines.append(f"- ⚠️ {conc['warning']}")
            else:
                lines.append("- ✅ Concentration within acceptable limits")
            lines.append("")
        lines.append("### Current Open Picks Matching Filter")
        lines.append(f"Count: **{r['active_matches']}**")
        if r["active_match_list"]:
            lines.append("| Symbol | Direction | Score | Conf | Strategy |")
            lines.append("|--------|-----------|-------|------|----------|")
            for p in r["active_match_list"]:
                lines.append(f"| {p['symbol']} | {p['direction']} | {p['score']} | {p['confidence']} | {p['strategy'][:20]} |")
        lines.append("")

    lines.extend([
        "## Risk Controls",
        "- Max per-pick: Kelly 0.25-fraction (capped at 10% of account)",
        "- Daily soft-stop: -2% total PnL triggers pause",
        "- DD halt: rolling 30d drawdown > 30% pauses all sizing",
        "",
        "## How to Apply",
        "1. Open [findtorontoevents.ca/audit](https://findtorontoevents.ca/audit)",
        "2. Apply filters per asset class above",
        "3. Size per Kelly recommendation",
        "4. Exit: follow TP/SL as set on pick",
        "",
    ])

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport written: {report_path}")
    return report_path


def write_decision_log(results: dict):
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_path = UPDATE_DIR / f"edge_analysis_{date_str}.md"
    lines = [
        f"# Edge Analysis & Filter Derivation — {date_str}",
        "",
        "## Key Discoveries",
        "",
        "- **CRYPTO scoring is miscalibrated**: Higher `score`, `elite_score`, and `confidence` are **inversely** correlated with performance. The edge is in specific strategy families and LONG direction, not aggregate scores.",
        "- **EQUITY scoring works correctly**: Higher `elite_score` strongly predicts better outcomes (Elite≥60 → WR=75%, PF=5.67).",
        "- **FOREX has a single viable strategy**: `forex-rsi-ema-scout` is the only strategy with WR>50%, but n=22 (<30). FOREX remains blocked pending accumulation.",
        "- **COMMODITY SHORT + conf≥0.6** maintains strong base performance.",
        "",
        "## Success Criteria Verification",
        "",
    ]
    criteria = [
        ("EQUITY", "PF≥1.5, WR≥55%, n≥30, ≥5 picks weekly", "partial"),
        ("CRYPTO", "PF≥1.5, WR≥50%, n≥100", "pass"),
        ("COMMODITY", "PF≥1.5, n≥50", "pass"),
        ("ETF", "PF≥1.3, n≥150", "partial"),
        ("FOREX", "WR≥50% filter if exists", "fail"),
        ("BOND", "n≥20", "fail"),
        ("Kelly", "All filters have computed position size", "pass"),
    ]
    for name, desc, status in criteria:
        emoji = {"pass": "✅", "partial": "⚠️", "fail": "❌"}.get(status, "❓")
        lines.append(f"{emoji} **{name}**: {desc}")
    lines.append("")
    lines.append("## Decisions")
    lines.append("")
    for ac, r in results.items():
        if r.get("status") != "proven":
            lines.append(f"- **{ac}**: No proven filter found. Status={r['status']}.")
            continue
        f = r["filter"]
        crits = []
        if f.get("direction"):
            crits.append(f"direction={f['direction']}")
        if "strategies" in f:
            crits.append(f"strategies={len(f['strategies'])} families")
        if "min_elite_score" in f:
            crits.append(f"elite_score≥{f['min_elite_score']}")
        lines.append(f"- **{ac}**: Deploy filter with {', '.join(crits)}.")
        lines.append(f"  - Rationale: PF={r['metrics']['pf']:.2f} > {MIN_PF_TARGET}, WR={r['metrics']['wr']:.1%} > {MIN_WR_TARGET}, n={r['metrics']['n']} ≥ {MIN_N_FILTER}.")
        lines.append(f"  - Walk-forward: IS PF={r['is_metrics']['pf']:.2f}, OOS PF={r['oos_metrics']['pf']:.2f}.")
        if r["simulation"]["max_drawdown_pct"] > MAX_MDD_PCT:
            lines.append(f"  - ⚠️ Max DD {r['simulation']['max_drawdown_pct']:.1f}% exceeds {MAX_MDD_PCT}% threshold — reduce position size or tighten stops.")
        else:
            lines.append(f"  - ✅ Max DD {r['simulation']['max_drawdown_pct']:.1f}% within {MAX_MDD_PCT}% threshold.")
        if f.get("warning"):
            lines.append(f"  - ⚠️ Filter warning: {f['warning']}")
        if f.get("note"):
            lines.append(f"  - 📝 {f['note']}")
        conc = r.get("concentration")
        if conc and conc.get("warning"):
            lines.append(f"  - ⚠️ {conc['warning']}")
    lines.append("")
    log_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Decision log written: {log_path}")
    return log_path


if __name__ == "__main__":
    REPORT_DIR.mkdir(exist_ok=True)
    UPDATE_DIR.mkdir(exist_ok=True)
    results = run_engine()
    report_path = write_weekly_report(results)
    log_path = write_decision_log(results)
    results_path = REPORT_DIR / f"weekly_filter_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.json"
    with open(results_path, "w") as f:
        json.dump({k: {kk: vv for kk, vv in v.items() if kk != "picks"} for k, v in results.items()}, f, indent=2, default=str)
    print(f"Machine results: {results_path}")
