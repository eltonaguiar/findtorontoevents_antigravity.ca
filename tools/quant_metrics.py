#!/usr/bin/env python3
"""quant_metrics.py — Sharpe/Sortino/MaxDD/PF/DSR/PBO/ROC on forward ledger + overall ranking.

Reads:
  reports/forward_observations.jsonl  (430 rows, real returns)
  reports/overall_ranking.json        (top 20 picks)

Computes per-pick and aggregate metrics, net-of-cost (measured 12.87 bp RT at $25k).
Outputs reports/quant_metrics.json + one-page human summary.

Usage:
  python3 tools/quant_metrics.py
"""
import json
import math
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import statistics as st

REPO = Path(__file__).resolve().parent.parent
FWD = REPO / "reports/forward_observations.jsonl"
RANK = REPO / "reports/overall_ranking.json"
OUT = REPO / "reports/quant_metrics.json"
SUMMARY = REPO / "reports/quant_metrics_summary.txt"

TICKET = 25000.0
COST_RT_BP = 12.87          # measured round-trip cost
COST_RT = COST_RT_BP / 10000.0


def dt(s):
    from datetime import datetime as _dt
    try:
        return _dt.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def load_forward_rows():
    rows = []
    for line in FWD.open():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    return rows


def pnl_net(r):
    """Net pnl after round-trip cost on a $25k ticket."""
    gross = (r.get("exit_px", 0) - r.get("entry_px", 0)) / max(1e-9, r.get("entry_px", 1))
    side = 1 if r.get("side") == "LONG" else -1
    gross *= side
    net = gross - COST_RT
    return net


_QUOTE_SUFFIXES = ("USDT", "USDC", "BUSD", "USD", "-USD", "-USDT", "PERP")


def base_symbol(sym):
    """Normalise venue symbols to the bare ticker used by the ranking.

    SOLUSDT -> SOL, BTC-USD -> BTC, ETHUSDT -> ETH, XMR-USD -> XMR.
    """
    if not sym:
        return sym
    s = sym.upper().strip()
    for suf in _QUOTE_SUFFIXES:
        if s.endswith(suf) and len(s) > len(suf):
            return s[: -len(suf)]
    return s


def sharpe(returns):
    if not returns or len(returns) < 2:
        return None
    mu = st.mean(returns)
    sd = st.pstdev(returns) if len(returns) > 1 else 0.0
    return mu / sd if sd > 0 else None


def sortino(returns):
    if not returns or len(returns) < 2:
        return None
    mu = st.mean(returns)
    downside = [r for r in returns if r < 0]
    dd = st.pstdev(downside) if len(downside) > 1 else 0.0
    return mu / dd if dd > 0 else None


def max_dd(returns):
    if not returns:
        return None
    eq = 1.0
    peak = 1.0
    mdd = 0.0
    for r in returns:
        eq *= (1 + r)
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak
        if dd > mdd:
            mdd = dd
    return mdd


def profit_factor(returns):
    wins = sum(r for r in returns if r > 0)
    losses = -sum(r for r in returns if r < 0)
    return wins / losses if losses > 0 else None


def simple_pbo(returns, n_boot=200):
    if len(returns) < 10:
        return None
    import random
    random.seed(42)
    better = 0
    for _ in range(n_boot):
        samp = [random.choice(returns) for _ in range(len(returns))]
        if st.mean(samp) > 0:
            better += 1
    return 1.0 - (better / n_boot)


def roc_annual(returns, hold_days):
    if not returns or not hold_days:
        return None
    total = sum(returns)
    years = max(hold_days, 1) / 365.25
    return (1 + total) ** (1 / years) - 1 if years > 0 else None


def main():
    fwd = load_forward_rows()
    per_sym = defaultdict(list)
    hold_by_sym = defaultdict(list)
    for r in fwd:
        sym = r.get("symbol")
        if not sym:
            continue
        key = base_symbol(sym)
        per_sym[key].append(pnl_net(r))
        o, c = dt(r.get("opened_at")), dt(r.get("closed_at"))
        if o and c:
            hd = (c - o).total_seconds() / 86400.0
            if hd >= 0:
                hold_by_sym[key].append(hd)

    overall = json.loads(RANK.read_text()) if RANK.exists() else {"top20": []}
    top20 = overall.get("top20", [])

    metrics = []
    for p in top20:
        sym = p["symbol"]
        key = base_symbol(sym)
        rets = per_sym.get(key, [])
        hds = hold_by_sym.get(key, [])
        hold_days = (sum(hds) / len(hds)) if hds else None

        m = {
            "symbol": sym,
            "n_trades": len(rets),
            "sharpe": sharpe(rets),
            "sortino": sortino(rets),
            "max_dd": max_dd(rets),
            "profit_factor": profit_factor(rets),
            "dsr": p.get("dsr"),
            "pbo_simple": simple_pbo(rets) if len(rets) >= 10 else None,
            "roc_annual": roc_annual(rets, hold_days) if rets and hold_days else None,
            "net_of_cost_bp": COST_RT_BP,
            "ticket_usd": TICKET,
        }
        metrics.append(m)

    agg = {
        "n_picks": len(metrics),
        "n_trades_total": sum(m["n_trades"] for m in metrics),
        "sharpe_mean": st.mean([m["sharpe"] for m in metrics if m["sharpe"] is not None]) if any(m["sharpe"] is not None for m in metrics) else None,
        "sortino_mean": st.mean([m["sortino"] for m in metrics if m["sortino"] is not None]) if any(m["sortino"] is not None for m in metrics) else None,
        "max_dd_worst": max([m["max_dd"] for m in metrics if m["max_dd"] is not None]) if any(m["max_dd"] is not None for m in metrics) else None,
        "pf_mean": st.mean([m["profit_factor"] for m in metrics if m["profit_factor"] is not None]) if any(m["profit_factor"] is not None for m in metrics) else None,
    }

    out = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source_forward": str(FWD),
        "source_ranking": str(RANK),
        "ticket_usd": TICKET,
        "cost_rt_bp": COST_RT_BP,
        "per_pick": metrics,
        "aggregate": agg,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))

    # human one-pager
    lines = []
    lines.append("QUANT METRICS (forward ledger + overall ranking)")
    lines.append(f"forward rows: {len(fwd)}  symbols in ranking: {len(top20)}  ticket=${TICKET:,.0f}  cost={COST_RT_BP}bp RT")
    lines.append("")
    lines.append("AGGREGATE:")
    for k, v in agg.items():
        lines.append(f"  {k}: {v}")
    lines.append("")
    lines.append("TOP 3 (by gates + net_bp):")
    for i, m in enumerate(metrics[:3], 1):
        lines.append(f"  {i}. {m['symbol']} n={m['n_trades']} Sharpe={m['sharpe']} Sortino={m['sortino']} MaxDD={m['max_dd']} PF={m['profit_factor']} PBO={m['pbo_simple']}")

    SUMMARY.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
