import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
PERF_PATH = ROOT / "alpha_engine" / "data" / "strategy_performance.json"
OUT_JSON = ROOT / "audit_dashboard" / "data" / "strategy_expansion_backtests.json"
OUT_MD = ROOT / "docs" / f"STRATEGY_EXPANSION_REVIEW_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.MD"

UNIVERSE = {
    "CRYPTO": ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "ADA-USD"],
    "EQUITY": ["AAPL", "MSFT", "NVDA", "META", "TSLA"],
    "ETF": ["SPY", "QQQ", "IWM", "GLD", "TLT"],
    "FOREX": ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X"],
    "FUTURES": ["ES=F", "NQ=F", "GC=F", "CL=F"],
}


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def build_proxy_signals(df: pd.DataFrame, style: str) -> pd.DataFrame:
    c = df["Close"]
    h = df["High"]
    l = df["Low"]
    v = df["Volume"] if "Volume" in df.columns else pd.Series([0] * len(df), index=df.index)

    out = df.copy()
    out["ema20"] = c.ewm(span=20, adjust=False).mean()
    out["ema50"] = c.ewm(span=50, adjust=False).mean()
    out["ema200"] = c.ewm(span=200, adjust=False).mean()
    out["rsi14"] = rsi(c, 14)
    out["mom10"] = c.diff(10)
    tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
    out["atr14"] = tr.rolling(14).mean()
    out["volratio"] = v / v.rolling(20).mean().replace(0, np.nan)

    out["signal"] = 0

    if style == "lightgbm":
        # Momentum+trend proxy for single-symbol ML models.
        out.loc[(out["ema20"] > out["ema50"]) & (out["rsi14"].between(45, 68)) & (out["mom10"] > 0), "signal"] = 1
        out.loc[(out["ema20"] < out["ema50"]) & (out["rsi14"].between(32, 55)) & (out["mom10"] < 0), "signal"] = -1
    else:
        # Ensemble-stack proxy: mix trend and squeeze breakout behavior.
        squeeze = (out["atr14"] < out["atr14"].rolling(30).mean())
        out.loc[(out["ema20"] > out["ema200"]) & (out["rsi14"] > 50) & squeeze & (out["volratio"] >= 0.9), "signal"] = 1
        out.loc[(out["ema20"] < out["ema200"]) & (out["rsi14"] < 50) & squeeze & (out["volratio"] >= 0.9), "signal"] = -1

    return out


def simulate(df: pd.DataFrame):
    pos = 0
    entry = 0.0
    stop = 0.0
    trades = []

    for i in range(1, len(df)):
        p = float(df["Close"].iloc[i])
        sig = int(df["signal"].iloc[i])
        atr = float(df["atr14"].iloc[i]) if not np.isnan(df["atr14"].iloc[i]) else 0.0

        if pos != 0:
            pnl = (p / entry - 1) * 100 * pos
            if pos == 1:
                stop = max(stop, p - 2.2 * atr)
                if p <= stop or df["rsi14"].iloc[i] > 70:
                    trades.append(float(pnl))
                    pos = 0
            else:
                stop = min(stop, p + 2.2 * atr)
                if p >= stop or df["rsi14"].iloc[i] < 30:
                    trades.append(float(pnl))
                    pos = 0

        if pos == 0 and sig != 0 and atr > 0:
            pos = sig
            entry = p
            stop = p

    if not trades:
        return {"trades": 0, "wr": 0.0, "pf": 0.0, "avg": 0.0, "total": 0.0}

    wins = [x for x in trades if x > 0]
    losses = [x for x in trades if x <= 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses)) if losses else 1e-9
    return {
        "trades": len(trades),
        "wr": (len(wins) / len(trades)) * 100,
        "pf": gross_win / gross_loss,
        "avg": float(np.mean(trades)),
        "total": float(sum(trades)),
    }


def get_underexposed_candidates(data: dict):
    cands = []
    for name, v in data.items():
        if not isinstance(v, dict):
            continue
        t = int(v.get("closed_picks", 0) or 0)
        wr = float(v.get("win_rate", 0) or 0)
        pf = float(v.get("profit_factor", 0) or 0)
        by = v.get("by_symbol") or {}
        sym_n = len(by) if isinstance(by, dict) else 0
        if 8 <= t <= 160 and wr >= 0.55 and pf >= 1.2 and sym_n <= 3:
            cands.append(
                {
                    "strategy": name,
                    "closed_picks": t,
                    "win_rate": wr * 100,
                    "profit_factor": pf,
                    "symbol_exposure": sym_n,
                }
            )
    cands.sort(key=lambda x: (x["win_rate"], x["profit_factor"]), reverse=True)
    return cands


def main():
    perf = json.loads(PERF_PATH.read_text(encoding="utf-8"))
    cands = get_underexposed_candidates(perf)

    # Focus expansion on strongest families found in data.
    families = [
        {"name": "ml_enhanced_lightgbm_transfer", "style": "lightgbm"},
        {"name": "ml_enhanced_ensemble_transfer", "style": "ensemble"},
    ]

    start = (datetime.now() - timedelta(days=900)).strftime("%Y-%m-%d")
    expansion_results = []
    total_jobs = sum(len(v) for v in UNIVERSE.values()) * len(families)
    job_i = 0

    for fam in families:
        print(f"[family] {fam['name']}")
        for asset_class, symbols in UNIVERSE.items():
            for sym in symbols:
                job_i += 1
                print(f"  [{job_i}/{total_jobs}] {asset_class} {sym}")
                df = yf.download(sym, start=start, interval="1d", progress=False)
                if df.empty:
                    print("    -> no data")
                    continue
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                if len(df) < 240:
                    print(f"    -> too short ({len(df)})")
                    continue
                sig = build_proxy_signals(df, fam["style"])
                m = simulate(sig)
                print(f"    -> trades={m['trades']} wr={m['wr']:.1f}% pf={m['pf']:.2f}")
                expansion_results.append(
                    {
                        "family": fam["name"],
                        "asset_class": asset_class,
                        "symbol": sym,
                        **{k: round(v, 4) if isinstance(v, float) else v for k, v in m.items()},
                    }
                )

    recommended = [
        r for r in expansion_results
        if r["trades"] >= 12 and r["wr"] >= 55 and r["pf"] >= 1.2 and r["avg"] > 0
    ]
    recommended.sort(key=lambda x: (x["wr"], x["pf"], x["trades"]), reverse=True)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "underexposed_candidates": cands,
        "expansion_backtests": expansion_results,
        "recommended_expansions": recommended,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(output, indent=2), encoding="utf-8")

    lines = []
    lines.append("# Strategy Exposure Review + Expansion Backtests")
    lines.append("")
    lines.append(f"Generated: {output['generated_at']}")
    lines.append("")
    lines.append("## Strong But Underexposed Strategies")
    lines.append("")
    for c in cands[:20]:
        lines.append(
            f"- {c['strategy']}: WR {c['win_rate']:.1f}% | PF {c['profit_factor']:.2f} | "
            f"closed {c['closed_picks']} | symbols {c['symbol_exposure']}"
        )

    lines.append("")
    lines.append("## Expansion Backtest Recommendations")
    lines.append("")
    for r in recommended[:40]:
        lines.append(
            f"- {r['family']} -> {r['asset_class']} {r['symbol']}: "
            f"WR {r['wr']:.1f}% | PF {r['pf']:.2f} | trades {r['trades']} | avg {r['avg']:.3f}%"
        )

    lines.append("")
    lines.append("## Files")
    lines.append(f"- {OUT_JSON}")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")
    print(f"candidates={len(cands)} recommended={len(recommended)}")


if __name__ == "__main__":
    main()
