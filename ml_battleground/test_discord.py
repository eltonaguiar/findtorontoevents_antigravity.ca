"""
One-time test script: sends sample Discord notifications for all 3 SUPERPOWERS systems.
Run via: python -m test_discord  (from ml_battleground/)
Delete after confirming notifications arrive.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from shared.discord_notify import (
    send_system_status,
    send_arena_comparison,
    send_pick_alert,
    send_pick_exit,
)


def main():
    print("=== SUPERPOWERS Discord Test Notifications ===\n")

    # --- System A: The Filter ---
    print("[1/6] System A status...")
    send_system_status(
        system_name="system_a_filter",
        system_label="The Filter",
        version="1.0.0",
        active_picks=[
            {"symbol": "BTCUSDT", "signal_type": "BUY", "entry_price": 96250.0,
             "unrealized_pnl_pct": 1.32, "strategy": "supertrend_follow", "ml_score": 0.78},
            {"symbol": "SOLUSDT", "signal_type": "BUY", "entry_price": 172.40,
             "unrealized_pnl_pct": -0.45, "strategy": "narrative_sniper", "ml_score": 0.65},
        ],
        closed_picks=[],
        stats={"trades": 0, "win_rate": 0, "sharpe": 0, "max_dd": 0, "total_pnl_pct": 0, "profit_factor": 0},
        proven=False,
        proven_reason="Need 50+ trades to begin validation",
        ml_filter_acceptance_rate=0.42,
    )

    # --- System A: sample pick alert ---
    print("[2/6] System A pick alert...")
    send_pick_alert(
        system_label="The Filter",
        pick={
            "symbol": "ETHUSDT", "signal_type": "BUY", "entry_price": 3420.50,
            "take_profit": 3580.0, "stop_loss": 3350.0, "risk_reward": 2.26,
            "strategy": "ema_stack", "confidence": 0.72, "ml_score": 0.81,
            "tp_sl_method": "S/R levels",
        },
    )

    # --- System B: The Regime ---
    print("[3/6] System B status...")
    send_system_status(
        system_name="system_b_regime",
        system_label="The Regime",
        version="1.0.0",
        active_picks=[
            {"symbol": "BNBUSDT", "signal_type": "BUY", "entry_price": 645.20,
             "unrealized_pnl_pct": 0.78, "strategy": "supertrend_follow", "ml_score": 0.70},
        ],
        closed_picks=[],
        stats={"trades": 0, "win_rate": 0, "sharpe": 0, "max_dd": 0, "total_pnl_pct": 0, "profit_factor": 0},
        proven=False,
        proven_reason="Need 50+ trades to begin validation",
        regime="trending_up",
        regime_confidence=0.82,
    )

    # --- System C: The Neural Net ---
    print("[4/6] System C status...")
    send_system_status(
        system_name="system_c_deeplearn",
        system_label="The Neural Net",
        version="1.0.0",
        active_picks=[],
        closed_picks=[],
        stats={"trades": 0, "win_rate": 0, "sharpe": 0, "max_dd": 0, "total_pnl_pct": 0, "profit_factor": 0},
        proven=False,
        proven_reason="Model not yet trained — awaiting sufficient data",
    )

    # --- Sample pick exit ---
    print("[5/6] Sample pick exit (The Filter)...")
    send_pick_exit(
        system_label="The Filter",
        pick={
            "symbol": "XRPUSDT", "exit_reason": "TP_HIT", "net_pnl_pct": 3.42,
            "entry_price": 2.3400, "exit_price": 2.4200, "strategy": "connors_rsi2",
        },
    )

    # --- Arena comparison ---
    print("[6/6] Arena head-to-head...")
    send_arena_comparison(
        systems=[
            {"name": "system_a_filter", "label": "The Filter", "trades": 0,
             "wr": 0, "sharpe": 0, "max_dd": 0, "total_pnl": 0, "proven": False},
            {"name": "system_b_regime", "label": "The Regime", "trades": 0,
             "wr": 0, "sharpe": 0, "max_dd": 0, "total_pnl": 0, "proven": False},
            {"name": "system_c_deeplearn", "label": "The Neural Net", "trades": 0,
             "wr": 0, "sharpe": 0, "max_dd": 0, "total_pnl": 0, "proven": False},
        ],
        consensus_pairs=[],
    )

    print("\n=== All 6 test notifications sent! Check Discord. ===")


if __name__ == "__main__":
    main()
