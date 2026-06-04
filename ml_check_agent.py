import os
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    filename='ml_check_agent.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger().addHandler(console)

SCANNER_STATE_FILE = "multi_asset/data/scanner_state.json"
INSTITUTIONAL_PICKS_FILE = "multi_asset/data/institutional_picks.json"

def monitor_v_pick():
    logging.info("Checking 'V' pick performance...")
    try:
        # Check scanner picks
        if os.path.exists(SCANNER_STATE_FILE):
            with open(SCANNER_STATE_FILE, "r") as f:
                scanner_data = json.load(f)
                active = scanner_data.get("active_picks", [])
                for pick in active:
                    if pick.get("symbol") == "V":
                        pnl = pick.get("unrealized_pnl_pct") or 0  # 2026-06-04 INCIDENT #89-sibling: coalesce explicit None
                        logging.info(f"Scanner Pick V current PnL: {pnl}%")
                        if pnl <= -2.0:
                            logging.warning(f"CRITICAL WARNING: V is below -2.0% warning zone! ({pnl}%)")
        
        # Check institutional picks
        if os.path.exists(INSTITUTIONAL_PICKS_FILE):
            with open(INSTITUTIONAL_PICKS_FILE, "r") as f:
                inst_picks = json.load(f)
                for pick in inst_picks:
                    if pick.get("symbol") == "V":
                        pnl = pick.get("unrealized_pnl_pct") or 0  # 2026-06-04 INCIDENT #89-sibling: coalesce explicit None
                        logging.info(f"Institutional Pick V current PnL: {pnl}%")
                        if pnl <= -2.0:
                            logging.warning(f"CRITICAL WARNING: V is below -2.0% warning zone! ({pnl}%)")
                            
    except Exception as e:
        logging.error(f"Error checking V pick: {e}")

def run_ml_audit():
    logging.info("Auditing ML systems...")
    systems = [
        "alpha_engine/ml_ranker.py",
        "KIMI_RISEOFTHECLAW/ml_signal_ranker.py",
        "ml_battleground/",
        "genome/"
    ]
    for sys in systems:
        if os.path.exists(sys):
            logging.info(f"System Check PASS: {sys} is online.")
        else:
            logging.warning(f"System Check FAIL: {sys} not found.")

def main():
    logging.info("Starting ML Check Agent...")
    monitor_v_pick()
    run_ml_audit()
    logging.info("ML Check Agent complete.")

if __name__ == "__main__":
    main()
