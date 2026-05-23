# Non-production ML triage

Quick classification for modules that are **not** part of the primary audit + alpha + crypto CI path documented in [ML_PRODUCTION_INVENTORY.md](ML_PRODUCTION_INVENTORY.md). No algorithm changes are recommended here unless a module is promoted back to production with a protocol (e.g. `TESTING_PROTOCOL.MD` / strategy investigation docs).

| Area | Status | Notes |
|------|--------|--------|
| **`ml_battleground/`** | **Disabled in CI** | Workflows note catastrophic realized WR (e.g. March 2026 audit). Treat as archived research; do not tune models until a new forward-test mandate exists. |
| **`meta_strategy/` + `ml_meta_learner.py`** | **Not wired** | [`audit_trail/dashboard_generator.py`](../audit_trail/dashboard_generator.py) lists `meta_strategy` under `_GHOST_SYSTEMS` (missing data files). Meta-learner needs a live `permutation_results` / DB pipeline before value. |
| **`KIMI_*` copies** (e.g. `KIMI_RISEOFTHECLAW/ml_signal_ranker.py`) | **Legacy / competition** | Parallel implementations of ranker-style logic; not the canonical `alpha_engine/ml_ranker.py`. Keep for reference unless explicitly revived. |
| **`claude_gainer_ml/`** | **Standalone scanners** | RF/XGB ensemble for gainer workflows; integrate metrics only if outputs become dashboard sources with real outcomes. |
| **`risk_management/ml_risk_predictor.py`** | **Library-style** | Portfolio risk models; not listed as a dashboard pick source. Validate only if connected to live portfolio ingestion. |
| **`ml_crypto_predictor/researchers/`** | **Research** | Transformers, ablations, etc. Production path is `production_engine.py` + scheduled workflows. |

**Recommendation:** When adding new ML, extend the production inventory table first and wire one JSON/DB contract before expanding features.
