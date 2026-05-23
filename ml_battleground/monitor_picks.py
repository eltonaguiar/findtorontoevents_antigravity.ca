"""
ML Battleground Pick Monitor
=============================
Validates active picks across all 5 systems + ensemble between scan cycles.
Catches TP/SL hits, expiries, and trailing stops that would otherwise wait
until the next scanner run.

Run: python -m ml_battleground.monitor_picks
"""
import os
import sys
import json

# Ensure imports work from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.validator import validate_picks, save_picks, load_active, load_closed
from shared.calibration import build_calibration_map, save_calibration_map

SYSTEMS = [
    ("system_a", "System A (The Filter)", "system_a_filter/data"),
    ("system_b", "System B (The Regime)", "system_b_regime/data"),
    ("system_c", "System C (The Neural Net)", "system_c_deeplearn/data"),
    ("system_d", "System D (The Carry Trade)", "system_d_carry/data"),
    ("system_e", "System E (The Momentum)", "system_e_momentum/data"),
    ("ensemble", "The Ensemble", "ensemble_data"),
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def monitor():
    """Load active picks from all systems, validate against live prices, save back."""
    print("=" * 60)
    print("[Monitor] ML Battleground Pick Monitor")
    print("=" * 60)

    total_active = 0
    total_closed = 0

    for system_name, label, data_rel in SYSTEMS:
        data_dir = os.path.join(BASE_DIR, data_rel)

        if not os.path.isdir(data_dir):
            print(f"\n  {label}: data dir not found, skipping")
            continue

        active = load_active(data_dir)
        if not active:
            print(f"\n  {label}: 0 active picks")
            continue

        print(f"\n  {label}: {len(active)} active picks -> validating...")

        still_active, newly_closed = validate_picks(active, system_name, data_dir)

        if newly_closed:
            # Load existing closed picks and append
            closed_path = os.path.join(data_dir, "closed_picks.json")
            existing_closed = []
            if os.path.exists(closed_path):
                with open(closed_path) as f:
                    existing_closed = json.load(f)
            existing_closed.extend(newly_closed)

            # Save updated active picks
            with open(os.path.join(data_dir, "active_picks.json"), "w") as f:
                json.dump(still_active, f, indent=2, default=str)

            # Save updated closed picks
            with open(closed_path, "w") as f:
                json.dump(existing_closed, f, indent=2, default=str)

            for p in newly_closed:
                pnl = p.get("net_pnl_pct", 0)
                reason = p.get("exit_reason", "?")
                print(f"    CLOSED: {p['symbol']} -> {reason} ({pnl:+.2f}%)")
        else:
            # Still save back active picks (hwm, trailing_active, current_price updated)
            with open(os.path.join(data_dir, "active_picks.json"), "w") as f:
                json.dump(still_active, f, indent=2, default=str)

        print(f"    {label}: {len(still_active)} active, {len(newly_closed)} closed this cycle")
        total_active += len(still_active)
        total_closed += len(newly_closed)

    # --- Rebuild calibration map from all closed trades ---
    all_closed = []
    for system_name in ["system_a_filter", "system_b_regime", "system_c_deeplearn",
                         "system_d_carry", "system_e_momentum"]:
        data_dir = os.path.join(BASE_DIR, system_name, "data")
        try:
            closed = load_closed(data_dir)
            all_closed.extend(closed)
        except Exception:
            pass

    if len(all_closed) >= 30:
        cal_map = build_calibration_map(all_closed)
        save_calibration_map(cal_map)
        print(f"\n  Calibration map rebuilt: {cal_map.get('method', '?')} "
              f"({cal_map.get('n_samples', 0)} samples)")

    print(f"\n{'=' * 60}")
    print(f"[Monitor] Total: {total_active} active, {total_closed} closed this cycle")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    monitor()
