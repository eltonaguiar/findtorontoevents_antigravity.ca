> **NOTE (2026-05-18):** credentials in the original Kimi deliverable were
> plaintext and have been **redacted**. All swarm modules read DB credentials
> from environment variables — set `DB_HOST`, `DB_USER`, `DB_PASS_STOCKS` /
> `DB_PASS_BACKTESTS` / `DB_PASS_BACKUPS`, `DB_NAME` (Windows env vars or a
> local `.env`, never committed). Never paste live passwords into repo files.

# SPEC.md — Swarm Enhancement Suite for Financial Edge Detection

## 1. Overview

This specification defines 5 Pull Requests that enhance the existing swarm infrastructure (`tools/swarm/`, `tools/swarm_v2/`, `.ruflo/`) with industry-standard features for statistical edge calculation, risk gating, repo analysis, meta-improvement, and DB integration.

## 2. Existing Architecture (Baseline)

- **tools/swarm/**: JSON-based pick tracking (`swarm_picks.json`), yfinance/CoinGecko resolution, weekly leaderboards, pattern miner (tier x class x regime)
- **tools/swarm_v2/**: Hierarchical/ensemble/research swarms, ChromaDB memory, skill export, 6 engines
- **.ruflo/**: Continuous orchestrator, multi-agent types (coder/reviewer/security/tester/architect)
- **MySQL DBs**: `ejaguiar1_stocks` (env: DB_PASS_STOCKS), `ejaguiar1_backtests` (env: DB_PASS_BACKTESTS), `ejaguiar1_backups` (env: DB_PASS_BACKUPS)
- **Valid asset classes**: CRYPTO, EQUITY, ETF, FOREX, BOND, COMMODITY, FUTURES, SPORTS

## 3. PR Specifications

### PR-1: `feature/swarm-mysql-edge-engine` (tools/swarm/)

**New Files:**
- `tools/swarm/mysql_pick_adapter.py` — Secure MySQL connector using env vars
- `tools/swarm/statistical_edge_engine.py` — EV, Sharpe, Kelly, concentration calculator  
- `tools/swarm/swarm_edge_auditor.py` — Hierarchical swarm (strategist → tacticians → reviewer)
- Update `tools/swarm/config_loader.py` — Add DB_* env var loading

**Interfaces:**
```python
# mysql_pick_adapter.py
class MySQLPickAdapter:
    def __init__(self, db_config: dict | None = None)
    def fetch_picks(self, status: str | None = None, asset_class: str | None = None) -> list[dict]
    def fetch_all_active(self) -> list[dict]
    def fetch_all_closed(self) -> list[dict]
    def sync_to_json_store(self, json_path: str) -> int

# statistical_edge_engine.py
@dataclass
class EdgeMetrics:
    asset_class: str
    total_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    expected_value: float
    profit_factor: float
    sharpe_ratio: float
    kelly_fraction: float
    max_drawdown_pct: float
    status_assessment: str  # STRONG_EDGE | WEAK_EDGE | NO_EDGE

class StatisticalEdgeEngine:
    def __init__(self, picks: list[dict])
    def compute_all_metrics(self) -> dict[str, EdgeMetrics]
    def compute_concentration_index(self) -> dict  # Herfindahl + Gini
    def alert_on_degradation(self, threshold_ev: float = 0.005) -> list[dict]

# swarm_edge_auditor.py
class SwarmEdgeAuditor:
    def __init__(self, db_config: dict | None = None)
    async def run_full_audit(self) -> str  # Returns markdown report
```

### PR-2: `feature/swarm-risk-gating` (tools/swarm/)

**New Files:**
- `tools/swarm/dynamic_asset_gating.py` — Kill switch + position sizing per asset class
- `tools/swarm/regime_switching_filter.py` — ATR/volatility-based signal filtering
- `tools/swarm/concentration_analyzer.py` — Herfindahl/Gini for pick distribution

**Interfaces:**
```python
# dynamic_asset_gating.py
class DynamicAssetGatingController:
    def __init__(self, target_asset_class: str)
    def evaluate_signal_clearance(self, current_ev: float, signal: dict) -> dict
    def emergency_kill_all(self, reason: str) -> None

# regime_switching_filter.py
class RegimeSwitchingVolatilityFilter:
    def __init__(self, historical_window: int = 20)
    def filter_predictions(self, predictions: list, historical_atr: list, current_atr: float) -> list
    def detect_regime(self, vix: float | None, atr_ratio: float) -> str  # TRENDING | MEAN_REVERTING | CHOPPY

# concentration_analyzer.py
class ConcentrationAnalyzer:
    def __init__(self, picks: list[dict])
    def herfindahl_index(self) -> float
    def gini_coefficient(self) -> float
    def diversification_score(self) -> float
    def recommend_rebalancing(self) -> list[dict]
```

### PR-3: `feature/swarm-v2-repo-analyzer` (tools/swarm_v2/)

**New Files:**
- `tools/swarm_v2/repo_analysis_swarm.py` — Codebase crawler + dependency mapper
- `tools/swarm_v2/prediction_quality_correlator.py` — Code metrics ↔ prediction quality
- `tools/swarm_v2/model_drift_detector.py` — Backtest vs live drift detection

### PR-4: `feature/swarm-meta-improvement` (tools/swarm_v2/)

**New Files:**
- `tools/swarm_v2/meta_swarm_orchestrator.py` — Self-review + A/B testing
- `tools/swarm_v2/skill_evolution_tracker.py` — Skill effectiveness over time
- `tools/swarm_v2/bayesian_edge_updater.py` — Bayesian edge updating

### PR-5: `feature/ruflo-db-sync` (.ruflo/)

**New Files:**
- `.ruflo/db_sync_agent.py` — MySQL ↔ JSON store bidirectional sync
- `.ruflo/edge_alert_agent.py` — Edge degradation alerts
- `.ruflo/enhancement_proposal_agent.py` — Auto-generates enhancement PRs when edge is weak

## 4. Design Principles

1. **Env vars for secrets** — No hardcoded credentials. Use `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
2. **Backwards compatible** — All new modules are additive; existing swarm scripts unchanged
3. **Async where possible** — swarm_edge_auditor uses async/await
4. **Type hints throughout** — Python 3.10+ style
5. **Logging via structlog-style** — `logging.getLogger("swarm.<module>")`
6. **Idempotent** — Multiple runs produce same results (no duplicate DB writes)

## 5. Deployment

Generated files are placed in `/mnt/agents/output/prs/PR-{N}/` with directory structure mirroring the repo. A `push_prs.sh` script is provided for manual branch creation and push.
