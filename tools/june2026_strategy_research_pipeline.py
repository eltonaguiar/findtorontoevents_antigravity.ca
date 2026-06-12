#!/usr/bin/env python3
"""June 2026 strategy research pipeline — autopsy, enhanced v2 forward pool, new-strategy BT+MC.

Steps:
  1. Intrabar autopsy per asset class (live DB)
  2. Rigorous harness on existing strategy PnL vectors
  3. Verified backtest runners (where scripts exist)
  4. New-strategy OHLC backtests + Monte Carlo bootstrap
  5. Register hypotheses (M-107 append)
  6. Write reports/june2026_strategy_research_<date>.json + .md

Usage:
  python3 tools/june2026_strategy_research_pipeline.py
  python3 tools/june2026_strategy_research_pipeline.py --skip-network
  python3 tools/june2026_strategy_research_pipeline.py --register-hypotheses
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

ASSET_CLASSES = [
    "CRYPTO", "EQUITY", "FOREX", "COMMODITY", "ETF", "BOND",
    "FUTURES", "CHEAP_STOCKS", "PENNY_STOCK", "MEME",
]

VERIFIED_BACKTESTS = {
    "ETF": REPO / "verified_strategies" / "etf_dual_momentum_backtest.py",
    "FOREX": REPO / "verified_strategies" / "fx_trend_backtest.py",
    "COMMODITY": REPO / "verified_strategies" / "commodity_tsmom_backtest.py",
    "EQUITY": REPO / "verified_strategies" / "equity_momentum_backtest.py",
    "BOND": REPO / "verified_strategies" / "bond_duration_timing_backtest.py",
    "CRYPTO": REPO / "verified_strategies" / "crypto_momentum_backtest.py",
}


def _connect():
    import pymysql
    from tools.db_env import get_stocks_creds
    creds = {k: v for k, v in get_stocks_creds().items()
             if k in ("host", "user", "password", "database", "port", "connect_timeout")}
    return pymysql.connect(**creds, cursorclass=pymysql.cursors.DictCursor)


def intrabar_autopsy() -> dict[str, Any]:
    conn = _connect()
    cur = conn.cursor()
    out: dict[str, Any] = {}
    for ac in ASSET_CLASSES:
        cur.execute("""
            SELECT strategy, COUNT(*) n,
              ROUND(100*SUM(intrabar_status='TP_HIT')/COUNT(*),2) wr,
              ROUND(SUM(intrabar_pnl_pct),2) sum_pnl,
              ROUND(SUM(CASE WHEN intrabar_pnl_pct>0 THEN intrabar_pnl_pct ELSE 0 END)/
                NULLIF(ABS(SUM(CASE WHEN intrabar_pnl_pct<0 THEN intrabar_pnl_pct ELSE 0 END)),0),3) pf
            FROM at_signal_outcomes
            WHERE asset_class=%s AND intrabar_resolved_at IS NOT NULL
              AND intrabar_status IN ('TP_HIT','SL_HIT')
            GROUP BY strategy ORDER BY n DESC
        """, (ac,))
        rows = cur.fetchall()
        for r in rows:
            for k in ("n", "wr", "sum_pnl", "pf"):
                if r.get(k) is not None:
                    r[k] = float(r[k])
        cur.execute("""
            SELECT COUNT(*) n,
              ROUND(100*SUM(intrabar_status='TP_HIT')/NULLIF(COUNT(*),0),2) wr
            FROM at_signal_outcomes
            WHERE asset_class=%s AND intrabar_resolved_at IS NOT NULL
              AND intrabar_status IN ('TP_HIT','SL_HIT')
        """, (ac,))
        baseline = cur.fetchone()
        out[ac] = {
            "baseline": {k: float(baseline[k]) if baseline.get(k) is not None else None
                         for k in ("n", "wr")},
            "strategies": rows,
            "worst_n10": sorted([r for r in rows if r["n"] >= 10],
                                key=lambda x: x.get("pf") or 0)[:5],
            "best_n10": sorted([r for r in rows if r["n"] >= 10],
                               key=lambda x: x.get("pf") or 0, reverse=True)[:5],
        }
    conn.close()
    return out


def monte_carlo_bootstrap(pnls: list[float], n_trials: int = 5000, seed: int = 42) -> dict:
    if len(pnls) < 10:
        return {"n": len(pnls), "insufficient": True}
    rng = random.Random(seed)
    wrs, pfs = [], []
    for _ in range(n_trials):
        sample = [pnls[rng.randrange(len(pnls))] for _ in range(len(pnls))]
        wins = sum(1 for x in sample if x > 0)
        wrs.append(100 * wins / len(sample))
        gp = sum(x for x in sample if x > 0)
        gl = abs(sum(x for x in sample if x < 0))
        pfs.append(gp / gl if gl > 0 else (999.0 if gp > 0 else 0.0))
    wrs.sort()
    pfs.sort()
    actual_wr = 100 * sum(1 for x in pnls if x > 0) / len(pnls)
    mc50 = [100 * sum(1 for _ in pnls if rng.choice([0, 1])) / len(pnls) for _ in range(n_trials)]
    pctile = sum(1 for x in mc50 if x <= actual_wr) / n_trials
    gp = sum(x for x in pnls if x > 0)
    gl = abs(sum(x for x in pnls if x < 0))
    return {
        "n": len(pnls),
        "wr_pct": round(actual_wr, 2),
        "pf": round(gp / gl, 3) if gl > 0 else None,
        "mc_coinflip_percentile": round(pctile, 4),
        "bootstrap_pf_ci_95": [round(pfs[int(0.025 * n_trials)], 3),
                              round(pfs[int(0.975 * n_trials)], 3)],
        "bootstrap_wr_ci_95": [round(wrs[int(0.025 * n_trials)], 2),
                               round(wrs[int(0.975 * n_trials)], 2)],
    }


def rigorous_harness_by_class(autopsy: dict) -> dict[str, Any]:
    from alpha_engine.rigorous_backtest_harness import run_backtest
    import numpy as np
    results = {}
    for ac, data in autopsy.items():
        class_results = {}
        for row in data.get("strategies", []):
            if row["n"] < 15:
                continue
            # Re-load pnls for strategy
            conn = _connect()
            cur = conn.cursor()
            cur.execute("""
                SELECT intrabar_pnl_pct FROM at_signal_outcomes
                WHERE asset_class=%s AND strategy=%s
                  AND intrabar_resolved_at IS NOT NULL
                  AND intrabar_status IN ('TP_HIT','SL_HIT')
                  AND intrabar_pnl_pct IS NOT NULL
            """, (ac, row["strategy"]))
            pnls = [float(r["intrabar_pnl_pct"]) for r in cur.fetchall()]
            conn.close()
            if len(pnls) < 15:
                continue
            bt = run_backtest(np.array(pnls), ac, row["strategy"])
            mc = monte_carlo_bootstrap(pnls)
            class_results[row["strategy"]] = {
                "intrabar_n": row["n"],
                "harness_verdict": bt.get("verdict"),
                "harness_pf": bt.get("pf"),
                "harness_wr": bt.get("wr"),
                "dsr": bt.get("dsr"),
                "pbo": bt.get("pbo"),
                "monte_carlo": mc,
            }
        results[ac] = class_results
    return results


def run_verified_backtests(skip_network: bool) -> dict[str, Any]:
    out = {}
    if skip_network:
        return {"skipped": True, "reason": "skip_network"}
    for ac, script in VERIFIED_BACKTESTS.items():
        if not script.exists():
            out[ac] = {"error": "script_missing", "path": str(script)}
            continue
        try:
            proc = subprocess.run(
                [sys.executable, str(script)],
                capture_output=True, text=True, timeout=180, cwd=str(REPO),
            )
            stdout = proc.stdout.strip()
            parsed = None
            if stdout:
                try:
                    parsed = json.loads(stdout)
                except json.JSONDecodeError:
                    # fx_trend prints json via print(json.dumps)
                    for line in reversed(stdout.splitlines()):
                        if line.startswith("{"):
                            try:
                                parsed = json.loads(line)
                                break
                            except json.JSONDecodeError:
                                pass
            out[ac] = {
                "exit_code": proc.returncode,
                "result": parsed,
                "stderr_tail": proc.stderr[-500:] if proc.stderr else "",
            }
        except subprocess.TimeoutExpired:
            out[ac] = {"error": "timeout"}
        except Exception as e:
            out[ac] = {"error": str(e)}
    return out


def _fetch_yf_closes(symbol: str, period_days: int = 800):
    try:
        import yfinance as yf
        import pandas as pd
        t = yf.Ticker(symbol)
        df = t.history(period=f"{min(period_days, 730)}d", auto_adjust=True)
        if df is None or df.empty:
            return None
        return df["Close"].dropna()
    except Exception:
        return None


def _simple_momentum_backtest(closes, lookback: int = 126, hold: int = 21,
                              cost_bps: float = 5.0) -> list[float]:
    """Monthly momentum: long if return > 0 else flat. Returns list of trade pnls %."""
    import pandas as pd
    if closes is None or len(closes) < lookback + hold + 10:
        return []
    rets = closes.pct_change()
    pnls = []
    idx = list(closes.index)
    for i in range(lookback, len(idx) - hold, hold):
        r = float(closes.iloc[i] / closes.iloc[i - lookback] - 1)
        if r <= 0:
            continue
        entry = float(closes.iloc[i])
        exit_p = float(closes.iloc[min(i + hold, len(closes) - 1)])
        pnl = 100 * (exit_p / entry - 1) - 2 * cost_bps / 100
        pnls.append(pnl)
    return pnls


def _rsi2_mr_backtest(closes, cost_bps: float = 2.0) -> list[float]:
    import pandas as pd
    if closes is None or len(closes) < 30:
        return []
    delta = closes.diff()
    gain = delta.clip(lower=0).rolling(2).mean()
    loss = (-delta.clip(upper=0)).rolling(2).mean()
    rs = gain / loss.replace(0, 1e-9)
    rsi = 100 - 100 / (1 + rs)
    pnls = []
    for i in range(5, len(closes) - 5):
        if float(rsi.iloc[i]) >= 10:
            continue
        entry = float(closes.iloc[i])
        exit_p = float(closes.iloc[i + 5])
        pnl = 100 * (exit_p / entry - 1) - 2 * cost_bps / 100
        pnls.append(pnl)
    return pnls


NEW_STRATEGY_BACKTEST_CONFIG = {
    "CRYPTO": {"symbol": "BTC-USD", "fn": "momentum", "lookback": 90, "hold": 14},
    "EQUITY": {"symbol": "SPY", "fn": "momentum", "lookback": 126, "hold": 21},
    "FOREX": {"symbol": "USDCHF=X", "fn": "rsi2_mr"},
    "COMMODITY": {"symbol": "GC=F", "fn": "rsi2_mr"},
    "ETF": {"symbol": "XLF", "fn": "momentum", "lookback": 126, "hold": 21},
    "BOND": {"symbol": "TLT", "fn": "momentum", "lookback": 126, "hold": 21},
    "FUTURES": {"symbol": "ES=F", "fn": "momentum", "lookback": 126, "hold": 21},
    "CHEAP_STOCKS": {"symbol": "IWM", "fn": "momentum", "lookback": 63, "hold": 21},
    "PENNY_STOCK": {"symbol": "IWM", "fn": "rsi2_mr"},
    "MEME": {"symbol": "DOGE-USD", "fn": "momentum", "lookback": 30, "hold": 7},
}


def backtest_new_strategies(skip_network: bool) -> dict[str, Any]:
    from alpha_engine.june2026_research_candidates import NEW_STRATEGY_BY_CLASS
    out = {}
    if skip_network:
        return {ac: {"skipped": True} for ac in NEW_STRATEGY_BY_CLASS}
    for ac, meta in NEW_STRATEGY_BY_CLASS.items():
        cfg = NEW_STRATEGY_BACKTEST_CONFIG.get(ac, {})
        sym = cfg.get("symbol", "SPY")
        closes = _fetch_yf_closes(sym)
        fn = cfg.get("fn", "momentum")
        if fn == "rsi2_mr":
            pnls = _rsi2_mr_backtest(closes)
        else:
            pnls = _simple_momentum_backtest(
                closes, cfg.get("lookback", 126), cfg.get("hold", 21),
            )
        mc = monte_carlo_bootstrap(pnls)
        gp = sum(x for x in pnls if x > 0)
        gl = abs(sum(x for x in pnls if x < 0))
        out[ac] = {
            "strategy_id": meta["id"],
            "proxy_symbol": sym,
            "proxy_method": fn,
            "n_trades": len(pnls),
            "wr_pct": round(100 * sum(1 for x in pnls if x > 0) / len(pnls), 2) if pnls else None,
            "pf": round(gp / gl, 3) if gl > 0 else None,
            "sum_pnl_pct": round(sum(pnls), 2),
            "monte_carlo": mc,
            "passes_t2_proxy": bool(pnls and mc.get("pf") and mc["pf"] >= 1.5
                                 and mc.get("wr_pct", 0) >= 50 and len(pnls) >= 30),
        }
    return out


def forward_observation_snapshot() -> dict[str, Any]:
    os.environ.setdefault("JUNE2026_FORWARD_OBSERVATION", "1")
    from alpha_engine.june2026_research_candidates import (
        generate_forward_observation_picks,
        list_all_candidates,
    )
    picks = generate_forward_observation_picks()
    by_class = defaultdict(list)
    for p in picks:
        by_class[p.get("asset_class", "?")].append({
            "symbol": p.get("symbol"),
            "direction": p.get("direction"),
            "strategy": p.get("strategy"),
        })
    return {
        "candidates_meta": list_all_candidates(),
        "n_picks_generated": len(picks),
        "by_class": dict(by_class),
    }


def register_hypotheses(dry_run: bool = True) -> list[dict]:
    from alpha_engine.june2026_research_candidates import (
        ENHANCED_V2_BY_CLASS, NEW_STRATEGY_BY_CLASS,
    )
    reg_path = REPO / "reports" / "hypothesis_registry.json"
    reg = json.loads(reg_path.read_text())
    existing_ids = {h.get("id") for h in reg.get("hypotheses", []) if isinstance(h, dict)}
    new_entries = []
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for ac, specs in ENHANCED_V2_BY_CLASS.items():
        for spec in specs:
            hid = f"H-20260612-{spec['id']}"
            if hid in existing_ids:
                continue
            new_entries.append({
                "id": hid,
                "asset_class": ac,
                "family": "june2026_enhanced_v2",
                "description": f"Enhanced v2 forward observation: {spec['enhancement']}",
                "test_statistic": "intrabar forward WR/PF at checkpoint n>=80",
                "acceptance_criteria": {
                    "min_wr": 0.50, "min_pf": 1.5, "min_n": 80,
                    "validation": "forward_observation post-2026-06-12 entries only",
                },
                "economic_prior": spec.get("parent_evidence", ""),
                "status": "FORWARD_OBSERVATION",
                "registered_at": ts,
            })
    for ac, meta in NEW_STRATEGY_BY_CLASS.items():
        hid = f"H-20260612-{meta['id']}"
        if hid in existing_ids:
            continue
        new_entries.append({
            "id": hid,
            "asset_class": ac,
            "family": meta["family"],
            "description": meta["description"],
            "test_statistic": "net PF + Monte Carlo coin-flip percentile",
            "acceptance_criteria": {
                "min_pf": 1.5, "min_wr": 0.50, "min_n": 30,
                "mc_percentile_vs_50pct": 0.95,
            },
            "economic_prior": meta["economic_prior"],
            "status": "PRE_REGISTERED",
            "registered_at": ts,
        })
    if not dry_run and new_entries:
        reg.setdefault("hypotheses", []).extend(new_entries)
        reg_path.write_text(json.dumps(reg, indent=2))
    return new_entries


def write_markdown_report(payload: dict, path: Path) -> None:
    lines = [
        f"# June 2026 Strategy Research Report",
        f"",
        f"**Generated:** {payload['generated_at']}",
        f"",
        f"## Summary",
        f"",
        f"- Forward observation picks generated: **{payload['forward']['n_picks_generated']}**",
        f"- Asset classes autopsied: **{len(payload['autopsy'])}**",
        f"- New hypotheses registered: **{len(payload.get('hypotheses_registered', []))}**",
        f"",
        f"## Per-class intrabar baseline",
        f"",
        f"| Class | n | WR% | Best strategy (n≥10) |",
        f"|-------|---|-----|------------------------|",
    ]
    for ac in ASSET_CLASSES:
        d = payload["autopsy"].get(ac, {})
        bl = d.get("baseline", {})
        best = (d.get("best_n10") or [{}])[0]
        lines.append(
            f"| {ac} | {bl.get('n', '—')} | {bl.get('wr', '—')} | "
            f"{best.get('strategy', '—')} (n={best.get('n', '—')}, PF={best.get('pf', '—')}) |"
        )
    lines.extend(["", "## New strategy backtest proxy results", ""])
    for ac, r in payload.get("new_strategy_bt", {}).items():
        lines.append(
            f"- **{ac}** `{r.get('strategy_id')}`: n={r.get('n_trades')} "
            f"WR={r.get('wr_pct')}% PF={r.get('pf')} "
            f"MC pctile={r.get('monte_carlo', {}).get('mc_coinflip_percentile', '—')}"
        )
    lines.extend([
        "",
        "## Forward observation wiring",
        "",
        "Set `JUNE2026_FORWARD_OBSERVATION=1` and run `python -m alpha_engine.priority_picks_emitter`.",
        "",
        "## Repro",
        "",
        "```bash",
        "python3 tools/june2026_strategy_research_pipeline.py --register-hypotheses",
        "```",
    ])
    path.write_text("\n".join(lines))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-network", action="store_true", help="Skip yfinance + verified BT")
    ap.add_argument("--register-hypotheses", action="store_true")
    ap.add_argument("--dry-run-hypotheses", action="store_true", default=True)
    args = ap.parse_args()

    print("[1/6] Intrabar autopsy...")
    autopsy = intrabar_autopsy()

    print("[2/6] Rigorous harness + Monte Carlo on intrabar strategies...")
    harness = rigorous_harness_by_class(autopsy)

    print("[3/6] Verified backtest scripts...")
    verified = run_verified_backtests(args.skip_network)

    print("[4/6] New strategy OHLC proxy backtests...")
    new_bt = backtest_new_strategies(args.skip_network)

    print("[5/6] Forward observation snapshot...")
    forward = forward_observation_snapshot()

    print("[6/6] Hypothesis registration...")
    hyps = register_hypotheses(dry_run=not args.register_hypotheses)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "autopsy": autopsy,
        "rigorous_harness": harness,
        "verified_backtests": verified,
        "new_strategy_bt": new_bt,
        "forward": forward,
        "hypotheses_registered": hyps,
    }
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    json_path = REPO / "reports" / f"june2026_strategy_research_{date}.json"
    md_path = REPO / "reports" / f"june2026_strategy_research_{date}.md"
    json_path.write_text(json.dumps(payload, indent=2, default=str))
    write_markdown_report(payload, md_path)
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
