import subprocess
import sys
from pathlib import Path

def main():
    """
    Standalone script to automate the generation of edge stability reports.
    This script wraps the existing `tools.edge.edge_stability` module.
    """
    print("🚀 Starting edge stability update...")
    
    try:
        # We use 'python3 -m tools.edge.edge_stability --all' to run the existing logic.
        # This ensures that all imports (like alpha_engine) work correctly.
        cmd = [sys.executable, "-m", "tools.edge.edge_stability", "--all"]
        print(f"Running command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        if result.stdout:
            print("--- Output ---")
            print(result.stdout)
        
        print("✅ Edge stability update completed successfully.")
        
    except subprocess.CalledProcessError as e:
        print("❌ Error during edge stability update:", file=sys.stderr)
        print(f"Command: {' '.join(e.cmd)}", file=sys.stderr)
        print(f"Exit Code: {e.returncode}", file=sys.stderr)
        print(f"Stderr: {e.stderr}", file=sys.stderr)
        if e.stdout:
            print(f"Stdout: {e.stdout}", file=sys.stderr)
        sys.exit(e.returncode)
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
