# Two different “ML consensus” systems

The repository contains **two unrelated** implementations. Use precise names in runbooks, CI comments, and code review to avoid wiring the wrong data source.

## 1. Audit ML consensus (dashboard JSON pipeline)

| | |
|---|---|
| **Path** | [`ml_consensus/consensus.py`](../ml_consensus/consensus.py) |
| **Data** | Reads `audit_dashboard/data/dashboard_data.json` — groups **active** picks by symbol + direction, uses **recent_closed** for symbol history. |
| **Output** | `ml_consensus/data/active_picks.json`, `ml_consensus/models/consensus_report.json` |
| **CI** | `audit-dashboard.yml` — `python ml_consensus/consensus.py` |
| **Dashboard** | Loaded as source_system `ml_consensus` in [`audit_trail/dashboard_generator.py`](../audit_trail/dashboard_generator.py) |

**Call it:** “audit ML consensus” or “dashboard ML consensus.”

## 2. Signal aggregator ML consensus (forward DB)

| | |
|---|---|
| **Path** | [`signal_aggregator/ml_consensus.py`](../signal_aggregator/ml_consensus.py) — class `MLConsensusEngine` |
| **Data** | SQLite `forward_tracking.db` — table `signals` with resolved statuses (`tp_hit`, `sl_hit`, `expired`), joined to `performance_stats`. |
| **Output** | `signal_aggregator/models/ml_consensus_latest.pkl` when training completes |
| **CI** | `master-automation-scheduler.yml`, `ml-model-autotraining.yml` |

**Call it:** “aggregator ML consensus” or “forward-tracking ML consensus.”

## Rule of thumb

- If the question is about **multi-system agreement on the audit dashboard feed**, use **audit ML consensus** (`ml_consensus/`).
- If the question is about **historical forward-test signal rows in SQLite**, use **aggregator ML consensus** (`signal_aggregator/`).
