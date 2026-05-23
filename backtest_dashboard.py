"""
Walk-Forward Backtest Dashboard
=================================
Streamlit dashboard showing:
  - Equity curve per system
  - Win rate, Sharpe, Sortino, Calmar, max drawdown
  - Per-strategy performance table
  - System comparison heatmap
  - Rolling Sharpe (30-trade window)

Run: streamlit run dashboard/backtest_dashboard.py
"""
import os
import sys
import json
import numpy as np
import pandas as pd
import streamlit as st
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# --- Configuration ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SYSTEM_DIRS = {
    "Ensemble": PROJECT_ROOT / "ml_battleground" / "ensemble_data",
    "System A (Filter)": PROJECT_ROOT / "ml_battleground" / "system_a_filter" / "data",
    "System B (Regime)": PROJECT_ROOT / "ml_battleground" / "system_b_regime" / "data",
    "System C (Neural)": PROJECT_ROOT / "ml_battleground" / "system_c_deeplearn" / "data",
    "System D (Carry)": PROJECT_ROOT / "ml_battleground" / "system_d_carry" / "data",
    "System E (Momentum)": PROJECT_ROOT / "ml_battleground" / "system_e_momentum" / "data",
    "Alpha Engine": PROJECT_ROOT / "alpha_engine" / "data",
    "KIMI": PROJECT_ROOT / "KIMI_RISEOFTHECLAW" / "data",
    "Master Picks": PROJECT_ROOT / "signal_aggregator" / "data",
}


def load_closed_picks(data_dir: Path) -> list:
    """Load closed picks from a system's data directory."""
    for fname in ["closed_picks.json", "master_picks_tracker.json"]:
        path = data_dir / fname
        if path.exists():
            try:
                with open(path) as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return [p for p in data if p.get("status") == "closed" or p.get("pnl_percent") is not None]
                if isinstance(data, dict):
                    picks = data.get("closed_picks", []) + data.get("active_picks", [])
                    return [p for p in picks if p.get("status") == "closed" or p.get("pnl_percent") is not None]
            except Exception:
                continue
    return []


def compute_metrics(picks: list) -> dict:
    """Compute performance metrics from closed picks."""
    if not picks:
        return {"n_trades": 0, "win_rate": 0, "sharpe": 0, "max_dd": 0, "pf": 0}

    pnls = []
    for p in picks:
        pnl = p.get("pnl_percent") or p.get("net_pnl_pct") or p.get("pnl")
        if pnl is not None:
            pnls.append(float(pnl) / 100 if abs(float(pnl)) > 1 else float(pnl))

    if not pnls:
        return {"n_trades": 0, "win_rate": 0, "sharpe": 0, "max_dd": 0, "pf": 0}

    pnls = np.array(pnls)
    wins = pnls[pnls > 0]
    losses = pnls[pnls <= 0]

    # Equity curve
    equity = np.cumprod(1 + pnls)
    peak = np.maximum.accumulate(equity)
    drawdowns = (equity - peak) / peak
    max_dd = abs(drawdowns.min()) if len(drawdowns) > 0 else 0

    # Sharpe (annualized, assuming ~365 trades/year)
    sharpe = (pnls.mean() / pnls.std() * np.sqrt(365)) if pnls.std() > 0 else 0

    # Profit factor
    gross_profit = wins.sum() if len(wins) > 0 else 0
    gross_loss = abs(losses.sum()) if len(losses) > 0 else 0.001
    pf = gross_profit / gross_loss

    # Sortino
    downside = pnls[pnls < 0]
    sortino = (pnls.mean() / downside.std() * np.sqrt(365)) if len(downside) > 0 and downside.std() > 0 else 0

    return {
        "n_trades": len(pnls),
        "win_rate": float(len(wins) / len(pnls)),
        "sharpe": float(sharpe),
        "sortino": float(sortino),
        "max_dd": float(max_dd),
        "pf": float(pf),
        "avg_win": float(wins.mean()) if len(wins) > 0 else 0,
        "avg_loss": float(losses.mean()) if len(losses) > 0 else 0,
        "expectancy": float(pnls.mean()),
        "equity_curve": equity.tolist(),
        "pnls": pnls.tolist(),
    }


def main():
    st.set_page_config(page_title="Antigravity Backtest Dashboard", layout="wide")
    st.title("Walk-Forward Backtest Dashboard")
    st.markdown("Performance metrics across all trading systems")

    # Load data for all systems
    all_metrics = {}
    for name, data_dir in SYSTEM_DIRS.items():
        picks = load_closed_picks(data_dir)
        if picks:
            all_metrics[name] = compute_metrics(picks)

    if not all_metrics:
        st.warning("No closed picks data found. Run some scans first!")
        return

    # --- Summary Table ---
    st.header("System Performance Comparison")

    summary_data = []
    for name, metrics in all_metrics.items():
        if metrics["n_trades"] > 0:
            summary_data.append({
                "System": name,
                "Trades": metrics["n_trades"],
                "Win Rate": f"{metrics['win_rate']:.1%}",
                "Sharpe": f"{metrics['sharpe']:.2f}",
                "Sortino": f"{metrics['sortino']:.2f}",
                "Max DD": f"{metrics['max_dd']:.1%}",
                "Profit Factor": f"{metrics['pf']:.2f}",
                "Avg Win": f"{metrics['avg_win']:.2%}",
                "Avg Loss": f"{metrics['avg_loss']:.2%}",
                "Expectancy": f"{metrics['expectancy']:.3%}",
            })

    if summary_data:
        df_summary = pd.DataFrame(summary_data)
        st.dataframe(df_summary, use_container_width=True, hide_index=True)

    # --- Equity Curves ---
    st.header("Equity Curves")

    equity_data = {}
    for name, metrics in all_metrics.items():
        if metrics.get("equity_curve") and len(metrics["equity_curve"]) > 1:
            equity_data[name] = metrics["equity_curve"]

    if equity_data:
        max_len = max(len(v) for v in equity_data.values())
        eq_df = pd.DataFrame({
            name: curve + [curve[-1]] * (max_len - len(curve))
            for name, curve in equity_data.items()
        })
        st.line_chart(eq_df)

    # --- Rolling Sharpe ---
    st.header("Rolling Sharpe Ratio (30-trade window)")

    for name, metrics in all_metrics.items():
        pnls = metrics.get("pnls", [])
        if len(pnls) >= 30:
            rolling_sharpe = []
            for i in range(30, len(pnls)):
                window = np.array(pnls[i-30:i])
                if window.std() > 0:
                    rolling_sharpe.append(window.mean() / window.std() * np.sqrt(365))
                else:
                    rolling_sharpe.append(0)
            if rolling_sharpe:
                st.subheader(name)
                st.line_chart(pd.DataFrame({"Sharpe": rolling_sharpe}))

    # --- Per-Strategy Breakdown ---
    st.header("Per-Strategy Breakdown")

    selected_system = st.selectbox("Select System", list(all_metrics.keys()))
    if selected_system:
        data_dir = SYSTEM_DIRS.get(selected_system)
        if data_dir:
            picks = load_closed_picks(data_dir)
            if picks:
                strategies = {}
                for p in picks:
                    strat = p.get("strategy") or p.get("substrategy") or p.get("system") or "unknown"
                    if strat not in strategies:
                        strategies[strat] = []
                    strategies[strat].append(p)

                strat_metrics = []
                for strat_name, strat_picks in strategies.items():
                    m = compute_metrics(strat_picks)
                    if m["n_trades"] > 0:
                        strat_metrics.append({
                            "Strategy": strat_name,
                            "Trades": m["n_trades"],
                            "Win Rate": f"{m['win_rate']:.1%}",
                            "Sharpe": f"{m['sharpe']:.2f}",
                            "PF": f"{m['pf']:.2f}",
                            "Expectancy": f"{m['expectancy']:.3%}",
                        })

                if strat_metrics:
                    st.dataframe(pd.DataFrame(strat_metrics), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.caption(f"Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")


if __name__ == "__main__":
    main()
