"""Local continuous runner for quick-guess agent.
Run with: py -3.14 parallel_agent/run_local.py

Runs predictions every 60 seconds, trains every 20 minutes.
More frequent than CI (every 10 min) for faster learning.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quick_guess_agent import QuickGuessAgent

SYMBOLS_PHASE_A = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT']
SYMBOLS_FULL = [
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
    'DOGEUSDT', 'ADAUSDT', 'AVAXUSDT', 'LINKUSDT', 'DOTUSDT',
    'TRXUSDT', 'NEARUSDT', 'FETUSDT', 'RENDERUSDT', 'SUIUSDT',
]
HORIZONS = [5, 15, 60, 240, 4320, 10080]

def main():
    print("Quick-Guess ML Agent — Local Runner")
    print(f"Symbols: {len(SYMBOLS_FULL)} | Horizons: {HORIZONS}")
    print("Predict every 60s, train every 20min\n")

    agent = QuickGuessAgent(symbols=SYMBOLS_FULL, horizons=HORIZONS)

    cycle = 0
    while True:
        try:
            cycle += 1

            # Train every 20 cycles (20 min at 60s interval)
            if cycle == 1 or cycle % 20 == 0:
                agent.train()

            # Resolve matured predictions
            if hasattr(agent, 'resolve_outcomes'):
                agent.resolve_outcomes()

            # Predict
            preds = agent.predict_all()

            # Compact summary
            ts = time.strftime('%H:%M:%S UTC', time.gmtime())
            up = sum(1 for p in preds if p.get('prob_up', 0.5) > 0.55)
            dn = sum(1 for p in preds if p.get('prob_up', 0.5) < 0.45)
            neutral = len(preds) - up - dn

            # Count resolved
            resolved = [h for h in agent.history if h.get('resolved')]
            correct = sum(1 for h in resolved if h.get('correct'))
            acc = correct / max(len(resolved), 1) * 100

            print(f"[{ts}] Cycle {cycle}: {len(preds)} preds ({up}UP {dn}DN {neutral}--) | "
                  f"Resolved: {len(resolved)} | Accuracy: {acc:.1f}%")

            # Save every 5 cycles
            if cycle % 5 == 0:
                agent._save_state()

            time.sleep(60)

        except KeyboardInterrupt:
            print("\nStopping... saving state.")
            agent._save_state()
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
