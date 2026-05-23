"""Autopoietic self-repairing monitor for the meta-strategy system.

Detects anomalies (Sharpe collapse, herding, freeze-ups, chattering,
drawdown spirals) and applies automated corrective actions to the
permutation database.

Standalone usage:
    python -m meta_strategy.autopoietic_monitor
"""
from __future__ import annotations

import json
import random
import sqlite3
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "meta_strategy.db"
SWARM_WEIGHTS_PATH = Path(__file__).parent / "data" / "swarm_weights.json"

ANOMALY_SHARPE_COLLAPSE = "SHARPE_COLLAPSE"
ANOMALY_HERDING = "HERDING_BEHAVIOR"
ANOMALY_FREEZE = "FREEZE_UP"
ANOMALY_CHATTERING = "CHATTERING"
ANOMALY_DRAWDOWN_SPIRAL = "DRAWDOWN_SPIRAL"
ANOMALY_REGIME_LOCK = "REGIME_LOCK"
ANOMALY_ML_DEGRADATION = "ML_DEGRADATION"
ANOMALY_CORRELATION_SPIKE = "CORRELATION_SPIKE"
ANOMALY_STALE_DATA = "STALE_DATA"

SHARPE_HIGH = 1.0
SHARPE_LOW = 0.3
HERDING_THRESHOLD = 0.8
FREEZE_PERIODS = 10
CHATTERING_LIMIT = 100
DRAWDOWN_LIMIT = 40.0
LOOKBACK_SIGNALS = 100
REGIME_DIVERSITY_MIN = 3       # need at least 3 distinct regime_gate values
SYSTEM_OVERLAP_MAX = 0.70      # max Jaccard overlap between combo system masks
STALE_CUTOFF_MINUTES = 90      # system producing 0 signals for this long = stale


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _ensure_health_table(conn)
    return conn


def _ensure_health_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS health_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            anomaly_type TEXT,
            action_taken TEXT,
            details TEXT,
            metrics_snapshot TEXT
        )
    """)
    conn.commit()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AutopoieticMonitor:
    def __init__(self, conn: sqlite3.Connection | None = None):
        self.conn = conn or _get_conn()
        self.anomalies: list[dict] = []
        self.actions_taken: list[dict] = []

    # ------------------------------------------------------------------
    # Data loaders (all wrapped in try/except for missing tables)
    # ------------------------------------------------------------------

    def _load_recent_signals(self, limit: int = LOOKBACK_SIGNALS) -> list[dict]:
        try:
            rows = self.conn.execute(
                "SELECT * FROM permutation_signals ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def _load_active_combos(self) -> list[dict]:
        try:
            rows = self.conn.execute(
                "SELECT * FROM permutations WHERE status IN ('ACTIVE', 'RESURRECTED') ORDER BY combo_id"
            ).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def _load_recent_results(self) -> list[dict]:
        try:
            rows = self.conn.execute(
                "SELECT * FROM permutation_results ORDER BY last_updated DESC LIMIT 200"
            ).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def _load_eliminated_combos(self, limit: int = 20) -> list[dict]:
        try:
            rows = self.conn.execute(
                "SELECT * FROM permutations WHERE status = 'ELIMINATED' ORDER BY RANDOM() LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def _count_recent_eval_periods(self, n_periods: int = FREEZE_PERIODS) -> dict:
        try:
            rows = self.conn.execute(
                "SELECT DISTINCT eval_period FROM permutation_results "
                "WHERE eval_period IS NOT NULL AND eval_period != '' "
                "ORDER BY eval_period DESC LIMIT ?",
                (n_periods,),
            ).fetchall()
            periods = [r["eval_period"] for r in rows]
            if not periods:
                return {"periods": [], "trade_count": 0}
            placeholders = ",".join("?" for _ in periods)
            row = self.conn.execute(
                f"SELECT COALESCE(SUM(total_trades), 0) as tc "
                f"FROM permutation_results WHERE eval_period IN ({placeholders})",
                periods,
            ).fetchone()
            return {"periods": periods, "trade_count": row["tc"] if row else 0}
        except Exception:
            return {"periods": [], "trade_count": 0}

    # ------------------------------------------------------------------
    # Anomaly detectors
    # ------------------------------------------------------------------

    def detect_anomalies(self) -> list[dict]:
        self.anomalies = []
        self._detect_sharpe_collapse()
        self._detect_herding()
        self._detect_freeze()
        self._detect_chattering()
        self._detect_drawdown_spiral()
        self._detect_regime_lock()
        self._detect_ml_degradation()
        self._detect_correlation_spike()
        self._detect_stale_data()
        return self.anomalies

    def _detect_sharpe_collapse(self) -> None:
        signals = self._load_recent_signals(LOOKBACK_SIGNALS)
        closed = [s for s in signals if s.get("pnl_pct") is not None]
        if len(closed) < 20:
            return
        closed.sort(key=lambda s: s["timestamp"])
        mid = len(closed) // 2
        first_half = [s["pnl_pct"] for s in closed[:mid]]
        second_half = [s["pnl_pct"] for s in closed[mid:]]
        sharpe_first = self._quick_sharpe(first_half)
        sharpe_second = self._quick_sharpe(second_half)
        if sharpe_first > SHARPE_HIGH and sharpe_second < SHARPE_LOW:
            self.anomalies.append({
                "type": ANOMALY_SHARPE_COLLAPSE,
                "sharpe_first_half": round(sharpe_first, 4),
                "sharpe_second_half": round(sharpe_second, 4),
                "signal_count": len(closed),
            })

    def _detect_herding(self) -> None:
        results = self._load_recent_results()
        active_ids = {c["combo_id"] for c in self._load_active_combos()}
        by_combo: dict[str, list[float]] = {}
        for r in results:
            cid = r["combo_id"]
            if cid in active_ids and r.get("win_rate") is not None:
                by_combo.setdefault(cid, []).append(r["win_rate"])
        avg_wr = {cid: statistics.mean(vals) for cid, vals in by_combo.items() if vals}
        ids = list(avg_wr.keys())
        if len(ids) < 3:
            return
        vals = [avg_wr[i] for i in ids]
        if statistics.stdev(vals) < 0.001:
            correlation = 1.0
        else:
            pairs_above = 0
            pair_count = 0
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    pair_count += 1
                    diff = abs(avg_wr[ids[i]] - avg_wr[ids[j]])
                    if diff < 0.05:
                        pairs_above += 1
            correlation = pairs_above / pair_count if pair_count else 0.0
        if correlation > HERDING_THRESHOLD:
            self.anomalies.append({
                "type": ANOMALY_HERDING,
                "correlation": round(correlation, 4),
                "combo_count": len(ids),
            })

    def _detect_freeze(self) -> None:
        info = self._count_recent_eval_periods(FREEZE_PERIODS)
        if len(info["periods"]) >= 2 and info["trade_count"] == 0:
            self.anomalies.append({
                "type": ANOMALY_FREEZE,
                "periods_checked": len(info["periods"]),
                "trade_count": 0,
            })

    def _detect_chattering(self) -> None:
        info = self._count_recent_eval_periods(FREEZE_PERIODS)
        if info["trade_count"] > CHATTERING_LIMIT:
            self.anomalies.append({
                "type": ANOMALY_CHATTERING,
                "periods_checked": len(info["periods"]),
                "trade_count": info["trade_count"],
            })

    def _detect_drawdown_spiral(self) -> None:
        active = self._load_active_combos()
        if not active:
            return
        active_ids = {c["combo_id"] for c in active}
        results = self._load_recent_results()
        max_dd = 0.0
        worst_combo = None
        for r in results:
            if r["combo_id"] in active_ids:
                dd = abs(r.get("max_drawdown_pct", 0) or 0)
                if dd > max_dd:
                    max_dd = dd
                    worst_combo = r["combo_id"]
        if max_dd > DRAWDOWN_LIMIT:
            self.anomalies.append({
                "type": ANOMALY_DRAWDOWN_SPIRAL,
                "max_drawdown_pct": round(max_dd, 2),
                "worst_combo": worst_combo,
            })

    def _detect_regime_lock(self) -> None:
        """All combos converged on same regime_gate — evolution lost diversity."""
        active = self._load_active_combos()
        if len(active) < 3:
            return
        try:
            conn = _get_conn()
            regime_gates = set()
            for c in active:
                row = conn.execute(
                    "SELECT parameters FROM permutations WHERE combo_id = ?",
                    (c["combo_id"],)
                ).fetchone()
                if row and row[0]:
                    params = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                    regime_gates.add(params.get("regime_gate", "all"))
                else:
                    regime_gates.add("all")
            conn.close()
        except Exception:
            return
        if len(regime_gates) < REGIME_DIVERSITY_MIN:
            self.anomalies.append({
                "type": ANOMALY_REGIME_LOCK,
                "distinct_regimes": len(regime_gates),
                "regimes": list(regime_gates),
                "combo_count": len(active),
            })

    def _detect_ml_degradation(self) -> None:
        """ML-backed systems running in heuristic fallback mode."""
        ml_systems = {"crypto_ml_edge", "claws_of_doom", "ml_crypto_pred",
                      "ml_bg_a", "ml_bg_b", "ml_bg_c", "ml_bg_d", "ml_bg_e",
                      "claude_gainer", "mercury2"}
        signals = self._load_recent_signals(50)
        ml_signals = [s for s in signals if s.get("system_id") in ml_systems]
        if not ml_signals:
            return
        heuristic_count = sum(1 for s in ml_signals
                              if s.get("mode", "heuristic") == "heuristic"
                              or s.get("ml_mode") == "heuristic")
        ratio = heuristic_count / len(ml_signals) if ml_signals else 0
        if ratio > 0.7:
            self.anomalies.append({
                "type": ANOMALY_ML_DEGRADATION,
                "heuristic_ratio": round(ratio, 3),
                "heuristic_count": heuristic_count,
                "total_ml_signals": len(ml_signals),
            })

    def _detect_correlation_spike(self) -> None:
        """Active combos share too many of the same systems — system-level herding."""
        active = self._load_active_combos()
        if len(active) < 3:
            return
        system_sets = []
        for c in active:
            systems = set(c["combo_id"].split("|")[0].split("+")) if "|" in c["combo_id"] else set()
            if systems:
                system_sets.append(systems)
        if len(system_sets) < 3:
            return
        overlap_scores = []
        for i in range(len(system_sets)):
            for j in range(i + 1, len(system_sets)):
                intersection = len(system_sets[i] & system_sets[j])
                union = len(system_sets[i] | system_sets[j])
                if union > 0:
                    overlap_scores.append(intersection / union)
        avg_overlap = statistics.mean(overlap_scores) if overlap_scores else 0
        if avg_overlap > SYSTEM_OVERLAP_MAX:
            self.anomalies.append({
                "type": ANOMALY_CORRELATION_SPIKE,
                "avg_jaccard_overlap": round(avg_overlap, 3),
                "combo_count": len(system_sets),
            })

    def _detect_stale_data(self) -> None:
        """Systems producing zero signals for too long — stale data risk."""
        try:
            conn = _get_conn()
            signal_db = Path(__file__).parent.parent / "signal_recorder" / "data" / "signal_log.db"
            if not signal_db.exists():
                return
            sconn = sqlite3.connect(str(signal_db))
            sconn.row_factory = sqlite3.Row
            cutoff = datetime.now(timezone.utc).isoformat()
            rows = sconn.execute(
                "SELECT system_id, MAX(timestamp) as last_ts FROM signal_log GROUP BY system_id"
            ).fetchall()
            sconn.close()
            conn.close()
        except Exception:
            return
        stale_systems = []
        now = datetime.now(timezone.utc)
        for r in rows:
            try:
                last = datetime.fromisoformat(r["last_ts"].replace("Z", "+00:00"))
                age_min = (now - last).total_seconds() / 60
                if age_min > STALE_CUTOFF_MINUTES:
                    stale_systems.append({"system": r["system_id"], "minutes_stale": round(age_min)})
            except Exception:
                continue
        if len(stale_systems) >= 3:
            self.anomalies.append({
                "type": ANOMALY_STALE_DATA,
                "stale_systems": stale_systems[:10],
                "stale_count": len(stale_systems),
            })

    # ------------------------------------------------------------------
    # Self-repair actions
    # ------------------------------------------------------------------

    def apply_repairs(self) -> list[dict]:
        self.actions_taken = []
        for anomaly in self.anomalies:
            atype = anomaly["type"]
            if atype == ANOMALY_SHARPE_COLLAPSE:
                self._repair_sharpe_collapse(anomaly)
            elif atype == ANOMALY_HERDING:
                self._repair_herding(anomaly)
            elif atype == ANOMALY_FREEZE:
                self._repair_freeze(anomaly)
            elif atype == ANOMALY_CHATTERING:
                self._repair_chattering(anomaly)
            elif atype == ANOMALY_DRAWDOWN_SPIRAL:
                self._repair_drawdown_spiral(anomaly)
        return self.actions_taken

    def _repair_sharpe_collapse(self, anomaly: dict) -> None:
        now = _now_iso()
        self.conn.execute(
            "UPDATE permutations SET status = 'PROBATION' WHERE status = 'ACTIVE'"
        )
        self.conn.execute(
            "INSERT INTO elimination_log (combo_id, action, reason, timestamp) "
            "VALUES ('__SYSTEM__', 'REGIME_RESET', ?, ?)",
            (json.dumps(anomaly), now),
        )
        self.conn.commit()
        action = {
            "anomaly": ANOMALY_SHARPE_COLLAPSE,
            "action": "Set all ACTIVE combos to PROBATION, logged REGIME_RESET",
            "timestamp": now,
        }
        self.actions_taken.append(action)
        self._log_health(ANOMALY_SHARPE_COLLAPSE, action["action"], anomaly)

    def _repair_herding(self, anomaly: dict) -> None:
        now = _now_iso()
        try:
            top = self.conn.execute(
                "SELECT pr.combo_id, pr.sharpe FROM permutation_results pr "
                "JOIN permutations p ON p.combo_id = pr.combo_id "
                "WHERE p.status = 'ACTIVE' ORDER BY pr.sharpe DESC LIMIT 1"
            ).fetchone()
            if top:
                self.conn.execute(
                    "UPDATE permutations SET status = 'PROBATION' WHERE combo_id = ?",
                    (top["combo_id"],),
                )
                self.conn.execute(
                    "INSERT INTO elimination_log (combo_id, action, reason, timestamp) "
                    "VALUES (?, 'PROBATION', 'Herding detected — top performer paused for diversity', ?)",
                    (top["combo_id"], now),
                )
        except Exception:
            top = None

        eliminated = self._load_eliminated_combos(3)
        resurrected_ids = []
        for combo in eliminated[:3]:
            cid = combo["combo_id"]
            self.conn.execute(
                "UPDATE permutations SET status = 'RESURRECTED', "
                "resurrection_count = resurrection_count + 1, "
                "consecutive_failures = 0 WHERE combo_id = ?",
                (cid,),
            )
            self.conn.execute(
                "INSERT INTO elimination_log (combo_id, action, reason, timestamp) "
                "VALUES (?, 'RESURRECTED', 'Diversity injection — herding detected', ?)",
                (cid, now),
            )
            resurrected_ids.append(cid)
        self.conn.commit()

        action = {
            "anomaly": ANOMALY_HERDING,
            "action": f"Paused top performer ({top['combo_id'] if top else 'none'}), "
                      f"resurrected {len(resurrected_ids)} combos: {resurrected_ids}",
            "timestamp": now,
        }
        self.actions_taken.append(action)
        self._log_health(ANOMALY_HERDING, action["action"], anomaly)

    def _repair_freeze(self, anomaly: dict) -> None:
        now = _now_iso()
        weights = {}
        if SWARM_WEIGHTS_PATH.exists():
            try:
                weights = json.loads(SWARM_WEIGHTS_PATH.read_text())
            except Exception:
                weights = {}

        current_threshold = weights.get("confidence_threshold", 0.6)
        new_threshold = max(0.1, current_threshold - 0.15)
        weights["confidence_threshold"] = round(new_threshold, 3)
        weights["last_adjusted"] = now
        weights["adjustment_reason"] = "FREEZE_UP detected — lowered threshold"

        SWARM_WEIGHTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        SWARM_WEIGHTS_PATH.write_text(json.dumps(weights, indent=2))

        action = {
            "anomaly": ANOMALY_FREEZE,
            "action": f"Lowered confidence_threshold from {current_threshold} to {new_threshold}",
            "timestamp": now,
        }
        self.actions_taken.append(action)
        self._log_health(ANOMALY_FREEZE, action["action"], anomaly)

    def _repair_chattering(self, anomaly: dict) -> None:
        now = _now_iso()
        weights = {}
        if SWARM_WEIGHTS_PATH.exists():
            try:
                weights = json.loads(SWARM_WEIGHTS_PATH.read_text())
            except Exception:
                weights = {}

        current_threshold = weights.get("confidence_threshold", 0.6)
        new_threshold = min(0.95, current_threshold + 0.15)
        weights["confidence_threshold"] = round(new_threshold, 3)
        weights["last_adjusted"] = now
        weights["adjustment_reason"] = "CHATTERING detected — raised threshold"
        SWARM_WEIGHTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        SWARM_WEIGHTS_PATH.write_text(json.dumps(weights, indent=2))

        try:
            aggressive = self.conn.execute(
                "SELECT pr.combo_id, pr.total_trades FROM permutation_results pr "
                "JOIN permutations p ON p.combo_id = pr.combo_id "
                "WHERE p.status = 'ACTIVE' "
                "ORDER BY pr.total_trades DESC LIMIT 3"
            ).fetchall()
            probation_ids = []
            for row in aggressive:
                self.conn.execute(
                    "UPDATE permutations SET status = 'PROBATION' WHERE combo_id = ?",
                    (row["combo_id"],),
                )
                self.conn.execute(
                    "INSERT INTO elimination_log (combo_id, action, reason, timestamp) "
                    "VALUES (?, 'PROBATION', 'Chattering — most aggressive combo throttled', ?)",
                    (row["combo_id"], now),
                )
                probation_ids.append(row["combo_id"])
            self.conn.commit()
        except Exception:
            probation_ids = []

        action = {
            "anomaly": ANOMALY_CHATTERING,
            "action": f"Raised confidence_threshold to {new_threshold}, "
                      f"set {len(probation_ids)} aggressive combos to PROBATION",
            "timestamp": now,
        }
        self.actions_taken.append(action)
        self._log_health(ANOMALY_CHATTERING, action["action"], anomaly)

    def _repair_drawdown_spiral(self, anomaly: dict) -> None:
        now = _now_iso()
        self.conn.execute(
            "UPDATE permutations SET status = 'PROBATION' WHERE status IN ('ACTIVE', 'RESURRECTED')"
        )
        self.conn.execute(
            "INSERT INTO elimination_log (combo_id, action, reason, metrics_at_action, timestamp) "
            "VALUES ('__SYSTEM__', 'PROBATION', 'DRAWDOWN_SPIRAL emergency — all combos paused', ?, ?)",
            (json.dumps(anomaly), now),
        )
        self.conn.commit()

        action = {
            "anomaly": ANOMALY_DRAWDOWN_SPIRAL,
            "action": f"EMERGENCY: All combos set to PROBATION (max DD {anomaly.get('max_drawdown_pct', '?')}%)",
            "timestamp": now,
        }
        self.actions_taken.append(action)
        self._log_health(ANOMALY_DRAWDOWN_SPIRAL, action["action"], anomaly)

    # ------------------------------------------------------------------
    # Health logging
    # ------------------------------------------------------------------

    def _log_health(self, anomaly_type: str, action_taken: str, metrics: dict) -> None:
        now = _now_iso()
        try:
            self.conn.execute(
                "INSERT INTO health_log (timestamp, anomaly_type, action_taken, details, metrics_snapshot) "
                "VALUES (?, ?, ?, ?, ?)",
                (now, anomaly_type, action_taken, json.dumps(metrics), json.dumps(self._snapshot())),
            )
            self.conn.commit()
        except Exception:
            pass

    def _snapshot(self) -> dict:
        snapshot = {"timestamp": _now_iso()}
        try:
            row = self.conn.execute(
                "SELECT COUNT(*) as n FROM permutations WHERE status = 'ACTIVE'"
            ).fetchone()
            snapshot["active_combos"] = row["n"] if row else 0
        except Exception:
            snapshot["active_combos"] = 0
        try:
            row = self.conn.execute(
                "SELECT COUNT(*) as n FROM permutation_signals WHERE status = 'OPEN'"
            ).fetchone()
            snapshot["open_signals"] = row["n"] if row else 0
        except Exception:
            snapshot["open_signals"] = 0
        return snapshot

    # ------------------------------------------------------------------
    # Sharpe helper
    # ------------------------------------------------------------------

    @staticmethod
    def _quick_sharpe(pnl_list: list[float]) -> float:
        if len(pnl_list) < 2:
            return 0.0
        avg = statistics.mean(pnl_list)
        std = statistics.stdev(pnl_list)
        if std == 0:
            return 0.0 if avg == 0 else (10.0 if avg > 0 else -10.0)
        return avg / std

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_health_check(self) -> dict:
        anomalies = self.detect_anomalies()
        actions = self.apply_repairs() if anomalies else []
        return {
            "timestamp": _now_iso(),
            "anomalies_detected": len(anomalies),
            "anomalies": anomalies,
            "actions_taken": actions,
            "status": "HEALTHY" if not anomalies else "REPAIRED",
        }

    def get_health_report(self) -> dict:
        snapshot = self._snapshot()
        try:
            rows = self.conn.execute(
                "SELECT * FROM health_log ORDER BY timestamp DESC LIMIT 20"
            ).fetchall()
            recent_logs = [dict(r) for r in rows]
        except Exception:
            recent_logs = []

        active = self._load_active_combos()
        results = self._load_recent_results()
        active_ids = {c["combo_id"] for c in active}

        sharpes = []
        drawdowns = []
        for r in results:
            if r["combo_id"] in active_ids:
                if r.get("sharpe") is not None:
                    sharpes.append(r["sharpe"])
                dd = abs(r.get("max_drawdown_pct", 0) or 0)
                drawdowns.append(dd)

        return {
            "timestamp": snapshot["timestamp"],
            "active_combos": snapshot["active_combos"],
            "open_signals": snapshot["open_signals"],
            "avg_sharpe": round(statistics.mean(sharpes), 4) if sharpes else None,
            "max_drawdown_pct": round(max(drawdowns), 2) if drawdowns else None,
            "recent_health_events": recent_logs,
            "last_anomalies": self.anomalies,
            "last_actions": self.actions_taken,
        }


def main() -> None:
    print("=" * 60)
    print("  AUTOPOIETIC MONITOR — Meta-Strategy Health Check")
    print("=" * 60)

    monitor = AutopoieticMonitor()
    result = monitor.run_health_check()

    if result["anomalies_detected"] == 0:
        print("\n  STATUS: HEALTHY — No anomalies detected\n")
    else:
        print(f"\n  STATUS: {result['status']} — {result['anomalies_detected']} anomalie(s) found\n")
        for a in result["anomalies"]:
            print(f"    [{a['type']}] {json.dumps({k: v for k, v in a.items() if k != 'type'})}")
        print()
        for act in result["actions_taken"]:
            print(f"    REPAIR: {act['action']}")
        print()

    report = monitor.get_health_report()
    print(f"  Active combos : {report['active_combos']}")
    print(f"  Open signals  : {report['open_signals']}")
    print(f"  Avg Sharpe    : {report['avg_sharpe'] or 'N/A'}")
    print(f"  Max Drawdown  : {report['max_drawdown_pct'] or 'N/A'}%")
    print(f"  Health events : {len(report['recent_health_events'])} in log")
    print("=" * 60)


if __name__ == "__main__":
    main()
