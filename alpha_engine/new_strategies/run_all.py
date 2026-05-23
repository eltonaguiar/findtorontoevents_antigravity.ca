
import subprocess
import os

def run_strat(name):
    print(f"\n--- RUNNING {name} ---")
    try:
        # Use absolute paths to be safe
        script_path = os.path.join(os.getcwd(), "alpha_engine", "new_strategies", f"{name}.py")
        result = subprocess.run(["python", script_path], capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(f"ERR: {result.stderr}")
        return result.stdout
    except Exception as e:
        print(f"FAILED {name}: {e}")
        return str(e)

def main():
    logs = ""
    for s in [
        "crypto_squeeze",
        "forex_reversion",
        "stock_momentum",
        "etf_mean_reversion",
        "futures_trend_pullback",
    ]:
        logs += run_strat(s) + "\n"
    
    with open("alpha_engine/new_strategies/results.log", "w") as f:
        f.write(logs)
    print("\nBatch Research Completed. Results saved to alpha_engine/new_strategies/results.log")

if __name__ == "__main__":
    main()
