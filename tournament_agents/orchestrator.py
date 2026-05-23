import subprocess
import sys
import os
import logging
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - TOURNAMENT_ORCHESTRATOR - %(message)s')

def run_agent(agent_script):
    try:
        script_path = os.path.join(os.path.dirname(__file__), agent_script)
        logging.info(f"Launching {agent_script}...")
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
        logging.info(f"{agent_script} completed. Output:\n{result.stdout}")
        if result.stderr:
            logging.error(f"{agent_script} Error:\n{result.stderr}")
    except Exception as e:
        logging.error(f"Failed to run {agent_script}: {e}")

def compile_tournament_status():
    """Reads the JSON outputs of all agents and compiles a cross-asset prediction ranking."""
    logging.info("Compiling overall Tournament Leaderboard...")
    base_dir = os.path.dirname(__file__)
    macro_file = os.path.join(base_dir, 'data', 'macro', 'macro_portfolios.json')
    spec_file = os.path.join(base_dir, 'data', 'speculative', 'speculative_portfolios.json')
    
    all_portfolios = []
    
    if os.path.exists(macro_file):
        with open(macro_file, 'r') as f:
            all_portfolios.extend(json.load(f))
            
    if os.path.exists(spec_file):
        with open(spec_file, 'r') as f:
            all_portfolios.extend(json.load(f))

    # Calculate simulated sharpe approximation: Realized PnL / MAX(1.0, DD)
    for p in all_portfolios:
        dd = p['performance'].get('drawdown', 0.0)
        pnl = p['performance'].get('realized_pnl_pct', 0.0)
        p['simulated_sharpe'] = pnl / max(1.0, dd) if pnl > 0 else (pnl / max(1.0, dd)) # simple approximation
        
    # Sort by the approximated sharpe or PnL
    sorted_ports = sorted(all_portfolios, key=lambda x: x.get('simulated_sharpe', 0.0), reverse=True)
    
    report_path = os.path.join(base_dir, 'TOURNAMENT_LEADERBOARD.md')
    with open(report_path, 'w') as f:
        f.write("# Cross-Asset Prediction Tournament Leaderboard\n")
        f.write(f"*Last Updated: {datetime.now().isoformat()}*\n\n")
        f.write("| Rank | Portfolio ID | Asset Class | Total PnL % | UnPnl % | Win Rate | Sim Sharpe |\n")
        f.write("|------|--------------|-------------|-------------|---------|----------|------------|\n")
        
        for idx, p in enumerate(sorted_ports[:50]): # Top 50 print
            pnl = p['performance'].get('realized_pnl_pct', 0.0)
            unpnl = p['performance'].get('unrealized_pnl_pct', 0.0)
            wr = p['performance'].get('win_rate', 0.0)
            sharpe = p.get('simulated_sharpe', 0.0)
            f.write(f"| {idx+1} | {p['portfolio_id']} | {p['asset_type']} | {pnl:.2f}% | {unpnl:.2f}% | {wr:.1f}% | {sharpe:.2f} |\n")
            
    logging.info(f"Tournament Leaderboard compiled to {report_path}")

if __name__ == "__main__":
    agents = [
        'agent1_macro.py',
        'agent2_legacy.py',
        'agent3_speculative.py',
        'agent4_crypto_audit.py'
    ]
    
    logging.info("Starting Masterplan Sub-Agent Orchestrator...")
    for agent in agents:
        run_agent(agent)
    logging.info("All Sub-Agents have completed their prediction cycles.")
    compile_tournament_status()
