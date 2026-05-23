# Redis fleet message schema (`alpha_engine_bus`)

**Version:** 1 (2026-04-06)  
**Publisher:** `tools/redis_bus_hub.py publish` (recommended) or any `redis-cli PUBLISH` / `redis.publish` with valid JSON.

## Required fields

| Field | Type | Rule |
|--------|------|------|
| `from` | string | Agent id: `^[a-zA-Z0-9._-]{2,64}$` |
| `topic` | string | 1–120 chars; use `legacy_body_broadcast` only for human `body`-only posts |
| `summary` **or** `body` | string | At least one; `summary` is preferred for fleet digests |

## Recommended fields

| Field | Type | Purpose |
|--------|------|---------|
| `timestamp_utc` | string | ISO-8601 `Z`; auto-filled by hub if omitted |
| `schema_version` | int | Default `1` |
| `doc_path_repo_relative` | string | Primary markdown/json artifact under repo |
| `related_artifacts` | string[] | Extra paths for peers |

## Durable mirror

Pub/sub does not retain messages. The hub **LPUSH**es each payload to **`bus:alpha_engine_bus:log`** (trim ~200) so `peek-fleet` / `redis_peek_bus.py` can review recent traffic without subscribing live.

## Validation

Python: `tools/redis_bus_envelope.py` — `normalize_envelope`, `validate_envelope`.

## Example

```json
{
  "schema_version": 1,
  "from": "cursor-example",
  "topic": "feature_shipped",
  "timestamp_utc": "2026-04-06T12:00:00Z",
  "summary": "One-line description for humans and changelog.",
  "doc_path_repo_relative": "docs/FEATURE.md",
  "related_artifacts": ["tools/foo.py"]
}
```

## Topic extension: `kimi_swarm_tier_enrichment`

Published by `tools/redis_bus_kimi_tier_announce.py` (agent id `cursor-kimi-tier-bridge`). Same required envelope fields; may include `kimi_tier_histogram` and `kimi_crypto_picks_total` (see `docs/REDIS_BUS_KIMI_TIER.md`).

## Topic extension: `audit_picks_score_improvement_review`

Published by `tools/bus_post_audit_picks_edge.py` (agent id `cursor-audit-score-review`). May include optional `plan_status` / `plan_cursor` keys pointing at the Cursor plan filename and implementation checklist; primary human doc is `docs/AUDIT_SCORE_IMPROVEMENT_PLAN_REVIEW_2026-04-07.md`.

## Topic extension: `AUDIT_HF_GAP_AND_ENHANCEMENTS`

Published by `tools/bus_post_audit_hf_gap_enhancements.py` (agent id `cursor-composer`). Summarizes **live `/audit` tabs vs hedge-fund-grade pick quality**: Smart funnel / anti-overfit, score–PnL alignment, deploy truth-layer, non-crypto lanes, TCA; P0–P2 backlog with repo paths. Human doc: `docs/AUDIT_HF_GAP_AND_ENHANCEMENTS_2026-04-08.md`.

## Topic extension: `EXTERNAL_QUANT_FEEDBACK_COLLECTED`

Published by `tools/bus_post_external_quant_feedback_collected.py` (agent id `cursor-composer`). **Master index** of external quant reviews plus full **Xiaomi Mimo** `dashboard_data.json` audit (goldmine/sports cross-feed, active score–PnL inversion, suspicious consensus rows, `ml_bg` / `mega_mutation`, regime coverage on actives, decay alerts, closed deciles, TRX/rapid_fire). Human doc: `docs/EXTERNAL_QUANT_FEEDBACK_COLLECTED_2026-04-07.md`. Optional envelope key: `reviewer_label`.

## Topic extension: `HF_AUDIT_STRICT_GATES_PROGRESS`

Published by `tools/bus_post_hf_audit_strict_progress.py` (agent id `cursor-composer`). Optional `/audit` Smart tightening (`config/hf_audit_smart_strict.json`, default **off**), macro linear weights + `attach_macro_overlay`, `get_atr_stop_multiplier`, dashboard `hf_weekly_audit` embed. Envelope includes `coordination.similar_prior_bus` and `coordination.reconcile_with_golden_reconciliation` (elite ≥80 strict vs golden-plan sweet-spot note). Canonical roadmap: `docs/HF_MERGED_EXECUTION_PLAN_2026-04-02.md`.

## Topic extension: `GOOGLE_ANTIGRAVITY_HF_FEEDBACK`

Published by `tools/bus_post_google_antigravity_hf_feedback.py` (agent id `cursor-composer`). Captures Google Antigravity–style HF guidance (factor model, VA multi-TF, VaR sizing, regime, MC, TCA, WF) mapped to repo IDs **B6–B7**, **C4–C5**, **§10** of the merged plan. Human doc: `docs/GOOGLE_ANTIGRAVITY_HF_FEEDBACK_2026-04-02.md`.

## Topic extension: `HF_MERGED_EXECUTION_PLAN`

Published by `tools/bus_post_hf_merged_execution_plan.py` (agent id `cursor-composer`). **Canonical merged roadmap:** external live/code audit (stops, toxic systems, confidence, research vs live) + `AUDIT_HF_MULTICLASS_FLEET_REVIEW` + `HEDGE_FUND_ENHANCEMENT_PLAN` + Google Antigravity feedback (see §10). Human doc: `docs/HF_MERGED_EXECUTION_PLAN_2026-04-02.md`. Envelope may include `coordination.peer_append_topic` (`HF_MERGED_PLAN_PEER_APPEND`) for other agents to broadcast claims without editing git.

## Topic extension: `HF_MERGED_PLAN_PEER_APPEND`

Optional lightweight peer messages: `{ "from", "summary", "claims": ["A1","B2"], "doc_patch_hint" }` — does not replace git; use for fleet visibility when multiple agents (e.g. Claude Code) split P0 work.

## Topic extension: `AUDIT_HF_MULTICLASS_FLEET_REVIEW`

Published by `tools/bus_post_audit_hf_multiclass_review.py` (agent id `cursor-composer`). Cross-asset counts from user CSV exports + repo gates + Smart/VA pipeline summary; optional `dashboard_snapshot_stats` from `tools/data/audit_active_book_analysis.json`. Human doc: `docs/AUDIT_HF_MULTICLASS_FLEET_REVIEW_2026-04-07.md`.

## Topic extension: `AUDIT_CRYPTO_PREDICTION_TP_SL_QUALITY`

Published by `tools/bus_post_audit_crypto_prediction_tp_sl.py` (agent id `cursor-composer`). Points peers at `docs/AUDIT_CRYPTO_PREDICTION_TP_SL_QUALITY_2026-04-02.md` (TP/SL unification, PM geometry, closed-book calibration).

## Topic extension: `AUDIT_HIGH_CERTAINTY_ROLLOUT`

Published by `tools/bus_post_audit_high_certainty_rollout.py` (agent id `cursor-composer`).
Current repo convention for audit posts still uses legacy envelope keys such as `bus_topic` and `ts` rather than schema-first `topic` and `timestamp_utc`.
Primary human doc is `docs/AUDIT_HIGH_CERTAINTY_ROLLOUT_2026-04-06.md`.

## Topic extension: `UPDATES_GUIDE_SCORING_SCOPE`

Published by `tools/bus_post_updates_guide_scoring_scope.py` (agent id `cursor-composer`). Points humans to **https://findtorontoevents.ca/updates/** (filter **Type** = Fix/Improvement, **App** = Trading or Crypto) and **https://findtorontoevents.ca/audit/**; states that **post-penalty `AFFINITY_BOOSTS`** in `audit_trail/quality_gates.py` targets **crypto `*USDT`** pairs while **most other score components** apply across asset classes. Human doc: `updates/2026-04-08-audit-updates-index-scoring-scope.md`; index card in `updates/index.html`.

## Topic extension: `SMART_GATE_FUNNEL_STATS`

Published by `tools/bus_post_smart_gate_funnel.py` (agent id `cursor-composer`). Carries `smart_gate_funnel` (`active_count`, `passed`, `first_failure_counts`) from `summarize_smart_gate_funnel` on `picks.active`; durable mirror includes `bus:alpha_engine_bus:log`. Snapshot file: `tools/data/smart_gate_funnel_snapshot.json`.

## Topic extension: `crypto_wf_calibration`

Published by `tools/redis_bus_crypto_calibration_announce.py` (agent id `cursor-crypto-wf-calibration`). Same required envelope fields; may include:

- `calibration_engine` — e.g. `pav_isotonic_v1` (numpy isotonic; no sklearn).
- `calibration_dataset_stats` — e.g. `closed_picks_rows`, `rows_with_confidence_pnl` from `alpha_engine/data/closed_picks.json`.

See `docs/REDIS_BUS_CRYPTO_WF.md`.

## Topic extension: `HC_FILTER_EXPORT_VALIDATION_FINDINGS`

Published by `tools/bus_post_hc_filter_export_validation_findings.py` (agent id `cursor-composer`). Summarizes **empirical antigravity CSV export** analysis (closed-book WR by trust tier / asset class / grade; active vs `dashboard_hc_rules` HC pass rate). Human checklist: `docs/HC_FILTER_POST_PLAN_E2E.md` §5.1. Tool: `tools/analyze_antigravity_picks_export.py`.
