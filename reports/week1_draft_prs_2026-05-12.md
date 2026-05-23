# Week 1 Draft PRs — 2026-05-12

Per Grok 2026-05-12 expanded roadmap §2. Each PR listed with title, files
to touch, and success criteria. Items already shipped this session are
marked ✓.

## PR #910 — Data Pipeline Integrity Fix

**Title:** `fix(data): eliminate zero-PnL trades + resolver sync + checksum validation`

**Files:**
- `audit_trail/mysql_client.py` — add `pnl_integrity_check()` helper
- `alpha_engine/outcome_resolver.py` — enforce non-zero price movement check
- New: `tools/data_audit/etl_checksum.py` (batch checksum validator)
- `metrics_by_asset_class.csv` regeneration cron update

**Status (this session):**
- ✓ Zero-PnL artifact filter shipped in `dashboard_generator.py` (commit `dd8e8282537`).
- ✓ WON-vs-PnL sign-coherence guard in both atomic writers (`outcome_resolver.py:1670` + `mysql_client.py:628`, commit `22b677c1167`).
- Pending: backfill SQL execution (drafts at `reports/won_vs_pnl_backfill_sql_2026-05-12.md` + `reports/zero_pnl_backfill_sql_2026-05-12.md`); etl_checksum.py.

**Success criteria:** Zero-PnL <1%; full reconciliation between `at_raw_picks` and `lm_trades`.

---

## PR #911 — Dragger Quarantine + Blacklist Enforcement

**Title:** `feat(quarantine): blacklist kimi_signal_tracking + crypto_soc_* + stale models`

**Files:**
- `alpha_engine/config.py` — expand `BLACKLISTED_STRATEGIES`
- `audit_trail/quality_gates.py` — add `is_quarantined()` at execution gate
- `quarantined_emitters.json` — version-controlled list

**Status (this session):**
- ✓ kimi_signal_tracking already blacklisted (commit `4a2d337a5dc`, prior session).
- ✓ crypto_soc 3 named draggers already in `BLOCKED_ASSET_STRATEGY_PAIRS`.
- ✓ Ghost-row 5-cohort symbol-triple block shipped (commit `597819d79c7`).
- ✓ meta_strategy CRYPTO blanket block shipped (commit `5c7a8c43a27`).
- ✓ ml_gatekeeper CRYPTO confidence-inversion gate shipped (commit `c778f8f1696`).
- Pending: `is_quarantined()` runtime helper + `quarantined_emitters.json` consolidation.

**Success criteria:** No trades from quarantined emitters in next 48h production.

---

## PR #912 — ML Staleness Watchdog Hard-Fail Flip

**Title:** `ci: flip ML staleness watchdog to hard-fail (conditions met)`

**Files:**
- `.github/workflows/ml-staleness-watchdog.yml` — remove `--warn-only`
- `tools/assert_model_freshness.py` — remove ghost entry + add 4 new systems

**Status (this session):**
- ✓ mtime hard-fail flip for enhanced-ml-crypto (commit `db5bcfa0f04` / rebased from `2b9692d4f3e`).
- Pending: similar flip for ml_gatekeeper/ml_consensus workflows; consolidated `tools/assert_model_freshness.py`.

**Success criteria:** All models pass drift check for ≥24h before deployment.

---

## PR #913 — v3b Signal Translator + Paper-Pilot Flag

**Title:** `feat(orchestrator): v3b structured signal spec + paper-pilot mode`

**Files:**
- `tools/research/signal_spec.py` — Pydantic SignalSpec model + validator
- `tools/research/orchestrator.py` — add `--mode=paper` flag
- `updates/index.html` — Round 10 entry + per-class expected impact

**Status (this session):**
- ✓ Round 10 updates/index.html entry shipped (commit `26cd0f39d01`).
- ✓ `--mode=paper`-equivalent already in `alpha_engine/active_picks_sync.py` DRY-RUN scaffold (commit `bf85c4a343c`).
- v3b signal spec: design at `reports/v3b_signal_translator_spec_2026-05-12.md`. Pydantic implementation queued.

**Success criteria:** Validator rejects malformed specs upstream; paper-pilot routes work end-to-end.

---

## Grok's User-Provided Enhanced JSON Schema

User's 2026-05-12 v3b schema variant (compatible with the in-repo design):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "SignalSpec_v3b",
  "type": "object",
  "required": ["signal_id", "asset_class", "direction", "confidence", "valid_from", "features"],
  "properties": {
    "signal_id": { "type": "string", "pattern": "^[a-z0-9_]+$" },
    "asset_class": { "enum": ["CRYPTO","EQUITY","FOREX","COMMODITY","ETF","BOND","FUTURES"] },
    "direction": { "enum": ["LONG","SHORT","NEUTRAL","SKIP"] },
    "confidence": { "type": "number", "minimum": 0, "maximum": 1 },
    "valid_from": { "type": "string", "format": "date-time" },
    "valid_to":   { "type": "string", "format": "date-time" },
    "primary_ticker": { "type": "string" },
    "secondary_ticker": { "type": "string" },
    "regime_gate": {
      "type": "object",
      "properties": {
        "vix_max": { "type": "number" },
        "dxy_trend": { "enum": ["RISING","FALLING","FLAT"] },
        "session_utc": { "type": "array", "items": { "type": "string" } }
      }
    },
    "features": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "value"],
        "properties": {
          "name": { "type": "string" },
          "value": { "type": ["number","string","boolean"] },
          "source": { "type": "string" }
        }
      }
    },
    "rationale": { "type": "string", "maxLength": 800 }
  }
}
```

### Reconciliation

The in-repo spec at `reports/v3b_signal_translator_spec_2026-05-12.md` is
a superset of the user's variant:

| Field | In-repo spec | User variant | Resolution |
|---|---|---|---|
| Direction enum | `target` LONG/SHORT/NEUTRAL/PAIR_LONG/PAIR_SHORT | `direction` LONG/SHORT/NEUTRAL/SKIP | Adopt `direction`; add PAIR_LONG/PAIR_SHORT |
| Features | `{name, type, source, params}` | `{name, value, source}` | User's is leaner; in-repo's handler-aware schema may live on the `entry.handler.params` instead |
| Rationale | `thesis` (2000 char) | `rationale` (800 char) | Adopt `rationale` (matches Pydantic convention); 800 char is fine |
| Regime gate | `{filter, condition}` enum | `{vix_max, dxy_trend, session_utc}` | User's is more structured; adopt with extension for HMM_STATE/COT_SENTIMENT |
| Entry/exit | `{handler, params}` dispatch | n/a (rationale-only) | Keep dispatch logic; the user's variant is the data-only view; handlers are runtime concern |

**Net design:** Use the user's leaner schema for the *ingest* contract,
preserve the in-repo handler-registry for *dispatch*. Validator validates
the user's schema; the dispatcher reads `features` + `regime_gate` + the
existing strategy_handlers registry.

## Implementation priority

1. **Ship PR #913 (v3b)** first — unblocks NO_EDGE → GO transitions
   across asset classes. ~250 LOC core + 100 LOC tests.
2. PR #910 etl_checksum + #911 is_quarantined helper + #912 watchdog
   consolidation — incremental tightening of already-shipped guards.

## Refs

- This session's 25+ commits today on origin/main
- `reports/v3b_signal_translator_spec_2026-05-12.md` (in-repo spec)
- `reports/expanded_rescue_roadmap_2026-05-12.md`
- `reports/rescue_plan_per_asset_class_2026-05-12.md`
- `reports/grok_audit_red_team_synthesis_2026-05-12.md`
- Grok 2026-05-12 user submission (this document captures the variant)
