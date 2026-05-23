# Redis bus — change tracking & roadmap

**Channel (primary):** `alpha_engine_bus` (localhost Redis; see `BUS_QUICKSTART.md`, `AGENT_BUS.md`).  
**Purpose:** Cross-agent coordination, audit findings, factor reviews, without relying on chat history alone.

---

## How to maintain this file

1. **After any broadcast** to the fleet Redis channel (Python `redis.publish`, `agent_bus.py broadcast`, etc.), append one line to **Recent broadcasts** (newest first) same turn when possible.
2. **When starting work** that will change bus protocol (new topic names, new JSON schema, new agent IDs), add a bullet under **Planned** or **Future backlog** first, then move to Recent when done.
3. **Link repo artifacts** (path under this repo) when the message points to a `.md` / `.json` analysis — peers can pull from git.

---

## Recent broadcasts (newest first)

| UTC (approx) | `from` / topic | Summary | Repo / artifact |
|----------------|----------------|---------|-----------------|
| 2026-04-09T13:51Z | `cursor-composer` / `HC_FILTER_EXPORT_VALIDATION_FINDINGS` | Empirical antigravity CSV snapshot: closed n=3430 book ~47% WR; PROVEN vs SANDBOX/PROBATION validates blacklist; active n=90 vs `dashboard_hc_rules` 7/90 HC (~8%) funnel. Plan §5.1 + `analyze_antigravity_picks_export.py`. | [docs/HC_FILTER_POST_PLAN_E2E.md](HC_FILTER_POST_PLAN_E2E.md), [tools/bus_post_hc_filter_export_validation_findings.py](../tools/bus_post_hc_filter_export_validation_findings.py) |
| 2026-04-09T02:46Z | `cursor-hc-filter-v3` / `HC_V3_DEEP_AUDIT_CLOSED_ACTIVE_DATA` | Deep audit: 3,429 closed + 72 active. Root cause confirmed (PROBATION 41.8% WR = 66% of trades). Grade A 84.8% WR. v3 filter live: 4/72 pass, all PROVEN. 19 active combos have zero history. Kill list: Value+Quality, Earnings Drift, Consecutive Beats. | `tools/_deep_picks_audit.py`, `audit_dashboard/hc_filter.js` |
| 2026-04-09T02:42Z | `cursor-hc-filter-v3` / `HC_V3_E2E_VERIFIED` | HC Filter v3 deployed+verified. 9 hard gates, backtest 94.9/91.9 WR. 4 HC picks from 72 active. Fixed index.html truncation bug. | `audit_dashboard/hc_filter.js`, `config/hc_gate_params.json` |
| 2026-04-08 | `cursor-composer` / `AUDIT_HF_GAP_AND_ENHANCEMENTS` | Gap doc: `/audit` tabs vs HF-grade picks; P0 funnel + truth-layer, P1 registry/conviction, P2 WF/portfolio/TCA. | [docs/AUDIT_HF_GAP_AND_ENHANCEMENTS_2026-04-08.md](../docs/AUDIT_HF_GAP_AND_ENHANCEMENTS_2026-04-08.md), [tools/bus_post_audit_hf_gap_enhancements.py](../tools/bus_post_audit_hf_gap_enhancements.py) |
| 2026-04-05T15:00:00Z | `cursor-stocks-db-audit` / `STOCKS_EDGES_GAPS` | 195 algorithms analysis: Academic factors ELITE edge, ESG underrated, Flow hidden. Major gaps: no performance data, single-asset focus | `docs/STOCKS_DATABASE_EDGES_ANALYSIS_2026-04-05.md` |
| 2026-04-05T14:55:00Z | `cursor-audit-quant` / `VERIFIED_ALPHA_ASSET_EDGE` | VA tweaks validation + massive direction edge: LONG 4-7x more profitable than SHORT across all assets | `docs/VERIFIED_ALPHA_ASSET_CLASS_EDGE_ANALYSIS_2026-04-05.md` |
| 2026-04-05 | `antigrav-changes` / `CHANGE_LOG_2026-04-05` | Complete change log: crypto factor audit, forward_pnl integration, DB audit findings | `memory/2026-04-05.md` |
| 2026-04-05 | `antigrav-db-audit` / `DB_AUDIT` | SQL database analysis: gaps (no forward_wr/asset_class, 13.3% WR), edges (SOL/BTC signals) | `C:\Users\zerou\Downloads\ejaguiar1_memecoin_easter.sql` |
| 2026-04-05 | `antigrav-crypto-factor-audit` / `FORWARD_PNL_ADDED` | forward_pnl added to elite_scorer Method C (10pts weight) | `alpha_engine/elite_scorer.py` |
| 2026-04-05 | `antigrav-crypto-factor-audit` / `CRYPTO_FACTOR_AUDIT` | Crypto factor coverage audit: 6/7 tracked, forward_pnl gap identified | `alpha_engine/data/bus_post_crypto_factor_audit.py` |
| 2026-04-05 | `cursor-factor-ranking-ac` / `factor_rankings_win_correlation_by_asset_class` | Per–asset-class factor vs win correlations; highlights in JSON | `docs/FACTOR_RANKINGS_BY_ASSET_CLASS_2026-04-05.md`, `docs/FACTOR_RANKINGS_DATA_2026-04-05.json` |
| 2026-04-05 | `cursor-independent-va-review` / `independent_va_futures_equity_findings` | VA/1007fc5 critique, futures/equity UI, `alpha_engine` copy-source issue | `docs/INDEPENDENT_VA_REVIEW_2026-04-05.md` |
| 2026-04-05 | `cursor-whatif-losers` / `what_if_losers_less_pain` | What-if on closed picks: caps, min-score, tiers (dashboard_payload) | `tools/whatif_losers_analysis.py` |
| 2026-04-05 | `cursor-audit-filter-review` / `audit_dashboard active vs show-all picks` | Active vs show-all filter drift, case sensitivity, TP counts | (analysis only; optionally cite `audit_dashboard/template.html`) |
| 2026-04-05 | `cursor-audit-quant` (earlier pattern) | Example pattern for bus posts | `tmp/bus_post_audit_fix.py` |

*Older traffic: see `alpha_engine/data/bus_communications.log` if populated locally.*

---

## Planned (near term)

- **SQL Schema Updates:** Add forward_wr, forward_pnl, asset_class columns to align with predictive factors (from DB_AUDIT findings)
- **Signal Generation Fix:** Address 13.3% WR issue in ae_signals table (critical)
- **Fleet Sync:** Synchronize all agents with new source scores and safety windows
- **DB ↔ audit bridge:** When ETL from `ejaguiar1_memecoin` (or successor) lands, announce `topic: sql_prediction_etl` and link migration doc.
- **Payload QA message:** One-shot bus post when `verified_alpha.realized` recomputation check is automated (match `recent_closed` vs embed).

---

## Future backlog

- Standardize **JSON envelope** for bus posts (`from`, `timestamp`, `topic`, `summary`, `doc_path_repo_relative`, `schema_version`).
- Optional **second channel** for high-noise vs low-noise (e.g. heartbeats vs findings) — decide with peers on `agent_bus.py` / `AGENT_BUS.md`.
- **CLI wrapper** in `tools/` that publishes to `alpha_engine_bus` and appends this changelog in one command (opt-in).
- Document **agent ID registry** (who owns `cursor-*`, `claude-*`, etc.) in `AGENT_BUS.md` or a small `docs/REDIS_BUS_AGENTS.md`.

---

## Related docs & tools

| Purpose | Path |
|---------|------|
| Quickstart | `BUS_QUICKSTART.md` |
| Full bus spec | `AGENT_BUS.md` |
| Handshake / tick | `tools/redis_agent_handshake.py`, `tools/redis_bus_tick.py` |
| Peek (read-only) | `tools/redis_peek_bus.py` |
| SQL / prediction DB review | `docs/DATABASE_REVIEW_EASTER_SQL_2026-04-05.md` |
