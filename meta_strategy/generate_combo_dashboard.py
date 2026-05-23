"""Generate combo_metrics.json for the Battleground dashboard.

Reads from meta_strategy.db and produces a JSON file consumed by
battleground/app.js to display the Meta-Strategy Combos panel.

Run: python -m meta_strategy.generate_combo_dashboard
"""
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).parent / "data" / "meta_strategy.db"
OUTPUT_PATH = Path(__file__).parent.parent / "battleground" / "data" / "combo_metrics.json"


def generate():
    if not DB_PATH.exists():
        print(f"DB not found: {DB_PATH}")
        # Write empty scaffold
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(json.dumps({
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "total_permutations": 0,
            "active_combos": 0,
            "winners": [],
            "elimination_log": [],
            "walkforward": [],
            "adversarial": [],
            "regime_state": "unknown",
        }, indent=2))
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # Top winning combos
    winners = []
    try:
        rows = conn.execute("""
            SELECT pr.combo_id, pr.win_rate, pr.sharpe, pr.sortino,
                   pr.max_drawdown_pct, pr.profit_factor, pr.p_value,
                   pr.total_trades, pr.portfolio_final, pr.portfolio_return_pct,
                   pr.kelly_pct, pr.eval_period, pr.failure_reason,
                   p.systems, p.logic_type, p.status, p.consecutive_failures,
                   p.resurrection_count
            FROM permutation_results pr
            JOIN permutations p ON p.combo_id = pr.combo_id
            WHERE pr.total_trades >= 1
            ORDER BY pr.is_winner DESC, pr.sharpe DESC, pr.total_trades DESC
            LIMIT 100
        """).fetchall()
        for r in rows:
            d = dict(r)
            try:
                d["systems"] = json.loads(d["systems"])
            except Exception:
                d["systems"] = []
            winners.append(d)
    except Exception:
        pass

    # Count stats
    total_perms = 0
    active_count = 0
    eliminated_count = 0
    try:
        total_perms = conn.execute("SELECT COUNT(*) FROM permutations").fetchone()[0]
        active_count = conn.execute(
            "SELECT COUNT(*) FROM permutations WHERE status IN ('ACTIVE','RESURRECTED','PROBATION')"
        ).fetchone()[0]
        eliminated_count = conn.execute(
            "SELECT COUNT(*) FROM permutations WHERE status = 'ELIMINATED'"
        ).fetchone()[0]
    except Exception:
        pass

    # Recent elimination log
    elim_log = []
    try:
        rows = conn.execute("""
            SELECT combo_id, action, reason, timestamp
            FROM elimination_log
            ORDER BY timestamp DESC LIMIT 20
        """).fetchall()
        elim_log = [dict(r) for r in rows]
    except Exception:
        pass

    # Walk-forward results
    wf_results = []
    try:
        rows = conn.execute("""
            SELECT combo_id, fold_number, train_sharpe, test_sharpe,
                   train_wr, test_wr, oos_degradation_pct, is_robust
            FROM walkforward_results
            ORDER BY timestamp DESC LIMIT 50
        """).fetchall()
        wf_results = [dict(r) for r in rows]
    except Exception:
        pass

    # Adversarial compatibility
    adv_results = []
    try:
        rows = conn.execute("""
            SELECT combo_id, system_a, system_b, correlation,
                   failure_overlap_pct, diversification_score
            FROM adversarial_compat
            ORDER BY diversification_score DESC LIMIT 30
        """).fetchall()
        adv_results = [dict(r) for r in rows]
    except Exception:
        pass

    conn.close()

    data = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total_permutations": total_perms,
        "active_combos": active_count,
        "eliminated_combos": eliminated_count,
        "winners": winners,
        "elimination_log": elim_log,
        "walkforward": wf_results,
        "adversarial": adv_results,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(data, indent=2, default=str))
    print(f"Wrote {len(winners)} combos to {OUTPUT_PATH}")


if __name__ == "__main__":
    generate()
