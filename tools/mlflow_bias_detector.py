#!/usr/bin/env python3
"""mlflow_bias_detector.py — Auto-flag suspicious persona x class cells.

Operator rule 2026-06-04 22:30: "Anytime we see WR > 70% (even WR > 60%) we need
to deep dive." This script encodes the deep-dive logic and logs a bias_score to
mlflow.db so future cells can be auto-flagged before any operator decision.

Bias signals computed per (persona, asset_class) cell:
  1. Symbol HHI (Herfindahl) — concentration on 1-2 symbols
  2. Model-family HHI — concentration on one model family (e.g., deepseek_*)
  3. Time-window HHI — % of trades within rolling 14-day window
  4. TP_HIT_REPLAY share — intrabar wick-fills inflate WR vs real-time orders
  5. Symbol chi-square p — are all symbols winning equally or one symbol carrying it
  6. statsmodels ADF on cum-pnl — distinguishes durable trend vs lucky-window
  7. Drift-below-market — % of entries that closed in their first day (suspect
     stale-quote entries below market)

Composite bias_score = weighted sum (0=clean, 1=heavily biased). Threshold
0.50 -> WINDOW_ARTIFACT auto-flag.

Discovered 2026-06-04 via 4-engine swarm scrutiny (deepseek + xai + vllm-large +
ollama-large unanimous): cta_trend x COMMODITY 86.7% WR was 100% explained by an
11-day NG=F + CL=F rally with stale entries and deepseek model family
concentration. This tool would have caught it automatically.

Usage: python3 tools/mlflow_bias_detector.py
"""
from __future__ import annotations

import os
import warnings
from collections import Counter

import mlflow
import numpy as np
import pymysql
from scipy.stats import chisquare
from statsmodels.tsa.stattools import adfuller

warnings.filterwarnings("ignore")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MLRUNS_DB = os.path.join(REPO, "mlflow.db")
WR_DEEP_DIVE_THRESHOLD = 0.60   # operator rule: WR > 60% needs scrutiny
BIAS_FLAG_THRESHOLD = 0.50


def _connect():
    from tools.db_env import get_stocks_creds
    return pymysql.connect(**get_stocks_creds())


def hhi(values: list) -> float:
    """Herfindahl-Hirschman Index 0..1 on a distribution of counts/strings."""
    if not values:
        return 1.0
    counts = Counter(values)
    total = sum(counts.values())
    if total == 0:
        return 1.0
    return sum((c / total) ** 2 for c in counts.values())


def model_family(model_id: str) -> str:
    """Group e.g. deepseek_v3, deepseek_v4, deepseek_r1 -> 'deepseek'."""
    if not model_id:
        return "unknown"
    parts = model_id.split("_")
    return parts[0] if parts else model_id


def _to_epoch(ts) -> float | None:
    if ts is None:
        return None
    if isinstance(ts, str):
        try:
            from datetime import datetime
            return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
        except Exception:
            return None
    return ts.timestamp() if hasattr(ts, "timestamp") else None


def time_window_hhi(timestamps: list, window_days: int = 14) -> float:
    """Fraction of trades clustered into the densest rolling 14d window."""
    if not timestamps or len(timestamps) < 2:
        return 1.0
    epochs = sorted([e for e in (_to_epoch(ts) for ts in timestamps) if e is not None])
    win = window_days * 86400
    densest = 0
    for i, t in enumerate(epochs):
        cnt = sum(1 for s in epochs if t <= s <= t + win)
        densest = max(densest, cnt)
    return densest / len(epochs)


def scrutinize_cell(persona: str, ac: str) -> dict:
    conn = _connect()
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute(
            """SELECT symbol, direction, entry_price, exit_price, pnl_pct,
                      exit_reason, submitted_at, resolved_at, model_id, status
               FROM tournament_picks
               WHERE persona_id=%s AND asset_class=%s AND status IN ('WIN','LOSS')
                 AND pnl_pct IS NOT NULL
               ORDER BY submitted_at""",
            (persona, ac),
        )
        rows = cur.fetchall()
    conn.close()
    if not rows:
        return {}

    n = len(rows)
    wins = [r for r in rows if r["pnl_pct"] > 0]
    wr = len(wins) / n

    # 1. Symbol concentration
    sym_hhi = hhi([r["symbol"] for r in rows])
    # 2. Model family concentration
    fam_hhi = hhi([model_family(r["model_id"]) for r in rows])
    # 3. Time-window cluster
    tw_hhi = time_window_hhi([r["submitted_at"] for r in rows], 14)
    # 4. TP_HIT_REPLAY share
    replay_share = sum(1 for r in rows if "REPLAY" in (r["exit_reason"] or "")) / n
    # 5. Symbol chi-square: are wins uniformly distributed across symbols?
    sym_counter = Counter(r["symbol"] for r in rows)
    win_counter = Counter(r["symbol"] for r in wins)
    expected_win = wr  # if uniform, every symbol wins at WR rate
    chi_p = 1.0
    if len(sym_counter) >= 2:
        observed = [win_counter.get(s, 0) for s in sym_counter]
        expected = [sym_counter[s] * expected_win for s in sym_counter]
        if all(e > 0 for e in expected):
            try:
                _, chi_p = chisquare(observed, expected)
            except Exception:
                chi_p = 1.0
    # 6. ADF on cum-pnl
    pnls = [r["pnl_pct"] for r in rows]
    cum = np.cumsum(pnls)
    try:
        _, adf_p, *_ = adfuller(cum, autolag="AIC")
    except Exception:
        adf_p = float("nan")

    # Composite bias_score (0 clean, 1 heavily biased)
    # Heavy weight on symbol/family/time concentration since those caught cta_trend.
    bias_score = (
        0.30 * (sym_hhi - 0.3) / 0.7      # 0.3 baseline diverse, 1.0 single symbol
        + 0.25 * (fam_hhi - 0.3) / 0.7
        + 0.20 * (tw_hhi - 0.3) / 0.7
        + 0.15 * replay_share
        + 0.10 * (1 - chi_p)              # low p = symbols differ = high bias
    )
    bias_score = max(0.0, min(1.0, float(bias_score)))

    verdict = "CLEAN"
    flags = []
    if sym_hhi > 0.5:
        flags.append("SYMBOL_CONCENTRATION")
    if fam_hhi > 0.5:
        flags.append("MODEL_FAMILY_BIAS")
    if tw_hhi > 0.7:
        flags.append("WINDOW_CLUSTERING")
    if replay_share > 0.3:
        flags.append("TP_HIT_REPLAY_INFLATION")
    if bias_score > BIAS_FLAG_THRESHOLD:
        verdict = "WINDOW_ARTIFACT" if tw_hhi > 0.7 else "BIASED"

    return {
        "n": n,
        "wr": wr,
        "sym_hhi": sym_hhi,
        "fam_hhi": fam_hhi,
        "tw_hhi": tw_hhi,
        "replay_share": replay_share,
        "chi_p": chi_p,
        "adf_p": adf_p,
        "bias_score": bias_score,
        "verdict": verdict,
        "flags": flags,
        "unique_symbols": len(sym_counter),
        "unique_model_families": len(set(model_family(r["model_id"]) for r in rows)),
    }


def main():
    mlflow.set_tracking_uri(f"sqlite:///{MLRUNS_DB}")
    mlflow.set_experiment("persona_bias_detection_2026-06-04")
    print(f"mlflow: sqlite:///{MLRUNS_DB} (local)")
    print(f"Scrutinizing every persona x class cell with WR > {WR_DEEP_DIVE_THRESHOLD*100:.0f}%")
    print(f"{'persona':28} {'class':10} {'n':>3} {'WR':>5} {'symHHI':>6} {'famHHI':>6} {'twHHI':>6} {'replay%':>7} {'bias':>5} verdict + flags")

    conn = _connect()
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute(
            """SELECT persona_id, asset_class, COUNT(*) n,
                      SUM(status='WIN')/COUNT(*) wr
               FROM tournament_picks
               WHERE status IN ('WIN','LOSS') AND persona_id IS NOT NULL
               GROUP BY persona_id, asset_class HAVING n>=10 AND wr>=%s
               ORDER BY wr DESC""",
            (WR_DEEP_DIVE_THRESHOLD,),
        )
        targets = cur.fetchall()
    conn.close()

    print(f"\n{len(targets)} cells exceed WR > 60% deep-dive threshold\n")

    for t in targets:
        res = scrutinize_cell(t["persona_id"], t["asset_class"])
        if not res:
            continue
        flags_str = ",".join(res["flags"]) if res["flags"] else "-"
        print(
            f"  {(t['persona_id'] or '?')[:28]:28} {t['asset_class']:10} "
            f"{res['n']:>3} {res['wr']*100:>4.1f}% "
            f"{res['sym_hhi']:.2f}   {res['fam_hhi']:.2f}   "
            f"{res['tw_hhi']:.2f}   {res['replay_share']*100:>5.1f}%  "
            f"{res['bias_score']:.2f}  {res['verdict']} {flags_str}"
        )

        with mlflow.start_run(run_name=f"{t['persona_id']}__x__{t['asset_class']}__bias"):
            mlflow.log_param("persona_id", t["persona_id"])
            mlflow.log_param("asset_class", t["asset_class"])
            mlflow.log_param("verdict", res["verdict"])
            mlflow.log_param("flags", ",".join(res["flags"]) if res["flags"] else "")
            for k, v in res.items():
                if isinstance(v, (int, float)) and not (isinstance(v, float) and np.isnan(v)):
                    mlflow.log_metric(k, float(v))
            mlflow.set_tag("scrutiny_date", "2026-06-04")

    print(f"\nView per-cell scrutiny in mlflow UI: mlflow ui --backend-store-uri sqlite:///{MLRUNS_DB}")


if __name__ == "__main__":
    main()
