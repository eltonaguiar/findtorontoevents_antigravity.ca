# Incidents P0 Batch Implementation — 2026-05-31

**Branch:** `fix/incidents-p0-batch-2026-05-31`  
**Live page:** [findtorontoevents.ca/audit/incidents.html](https://findtorontoevents.ca/audit/incidents.html)  
**DB:** `ejaguiar1_stocks` on `mysql.50webs.com` (`INCIDENT_*` / `ENHANCEMENT_*` tables)

---

## Review summary (49 incidents + 75 enhancements)

Nightly feed (`audit_dashboard/data/incidents_enhancements_feed.json`, refreshed 2026-05-30) mirrors MySQL. At session start:

| Bucket | Count | Notes |
|--------|------:|-------|
| OPEN P0 (live DB) | 10 | Down from page headline after partial prior fixes |
| OPEN P1 | ~20 | Workflow/CI, UI, strategy wiring |
| IN_PROGRESS | 3+ | job-health loop, Node 24 bump, failure-guardian |
| RESOLVED (page) | 2 | top_n_rank_backtest, forward_validator false alarm |

**Highest-impact unhandled P0 themes still open after this PR:**

1. HC JS/Python parity drift  
2. Profitable-but-filtered observability lane  
3. smart_picks_engine confidence inversion (partial fix exists; incident still OPEN)  
4. signal_outcomes / active_picks_sync upstream writer  
5. Ghost rows (56k duplicate cohorts) — needs separate dedup PR  
6. COT over-emission / COMMODITY class aggregation  
7. trust_score NULL on 99.99% of closed picks  

This PR intentionally scopes to **quick, verifiable data + gate fixes** that do not require destructive dedup or multi-day pipeline rewires.

---

## What was implemented

### 1. Data integrity repair (`tools/repair_data_integrity.py`)

Guarded repair tool (dry-run default) for `trading_picks`:

- Clamps `FOREX` rows with `pnl_pct < -100` to `-100`
- Relabels terminal status from PnL sign (`WON`/`LOST` contradictions)
- Attempts `chk_pnl_sign_coherence` CHECK constraint (already present on live DB)

**Live apply (2026-05-31):**

| Task | Result |
|------|--------|
| FOREX PnL clamp | 1 row fixed |
| Status/PnL contradiction | 1 row fixed |
| CHECK constraint | Already exists (`Duplicate check constraint name`) |
| Post-verify contradictions | 0 remaining |

**Incidents closed:** OVERALL #7 (FOREX pnl), OVERALL #8 (WON vs PnL)

### 2. FOREX strategy consolidation (`alpha_engine/config.py`, `alpha_engine/non_crypto_policy.py`)

Per INC FOREX P0 #3 and enhancement “add forex_carry to allowlist”:

- **Blacklisted** proven losers: `forex_rsi2_mean_reversion`, `inverse_carry_contrarian`, `carry_trade_momentum`, `forex_carry_momentum`, `forex_carry_ppp`, `myfxbook_retail_contrarian`, `forex_carry_bb_hybrid`
- **Admission gate:** only `cta_cross_asset_tsmom` (SHORT only) and `forex_carry` (probation) may emit FOREX picks
- **Policy:** replaced loser entries with single `forex_carry` probation block

**Incident:** FOREX #3 → `IN_PROGRESS` (gate landed; forward record TBD)

### 3. UNKNOWN category backfill (`tools/backfill_unknown_category.py`)

Uses existing `detect_asset_class()` to map symbols → DB `category` enum.

**Live apply (limit 2000 batch, 2026-05-31):**

- Scanned 1,361 UNKNOWN/NULL rows in batch  
- Updated 1,332 rows  
- 29 symbols still unclassifiable (left UNKNOWN)

**Incident:** OVERALL #26 (UNKNOWN asset_class) → `IN_PROGRESS`

### 4. Already on main (no code change this PR)

- **Smart Picks `signal_time`:** `dashboard_generator.py` already sets `"signal_time": entry_ts or ts` (INC P1 #23 satisfied on main)
- **SUPREME EDGE caveat:** POST-HOC banner in `template.html` ~line 1342 (INC OVERALL #16 → marked RESOLVED in DB)

---

## Approach

1. **Read live incidents page + MySQL feed** — triage by severity × effort × blast radius  
2. **Verify on live DB** before coding (`DB_PASS_STOCKS` from local creds file)  
3. **Prefer guarded tools** (`--apply` opt-in) over ad-hoc SQL  
4. **Update `INCIDENT_*` rows** via `tools/audit_pick_funnel/cli_track.py` so nightly `incidents.html` reflects truth  
5. **Defer** ghost-row dedup, signal_outcomes pipeline, HC parity corpus, profitable-filtered lane to follow-up PRs (documented in audit summary)

---

## Verification commands

```bash
export DB_PASS_STOCKS=...
python3 tools/repair_data_integrity.py          # expect 0 affected post-fix
python3 tools/backfill_unknown_category.py        # remaining UNKNOWN count
python3 -c "import py_compile; py_compile.compile('alpha_engine/non_crypto_policy.py', doraise=True)"
python3 - <<'PY'
from alpha_engine.non_crypto_policy import evaluate_non_crypto_candidate
for s,d,exp in [
  ("forex_rsi2_mean_reversion","LONG",False),
  ("cta_cross_asset_tsmom","SHORT",True),
  ("cta_cross_asset_tsmom","LONG",False),
  ("forex_carry","LONG",True),
]:
  r=evaluate_non_crypto_candidate({"category":"forex","strategy":s,"symbol":"USDJPY=X","direction":d,"confidence":0.7,"rr_ratio":1.5,"elite_score":60})
  print(s,d,r["allowed"],r.get("reason",""))
PY
```

---

## Follow-up PRs (not in this batch)

| Priority | Item | Suggested branch |
|----------|------|------------------|
| P0 | Ghost rows dedup + writer investigation | `fix/ghost-rows-dedup` |
| P0 | `active_picks_sync.py` + outcome resolver CI fix | `fix/signal-outcomes-pipeline` |
| P0 | trust_score backfill / HC gate field migration | `fix/trust-score-backfill` |
| P0 | HC JS/Python parity test corpus | `fix/hc-parity-contract` |
| P1 | Profitable-but-filtered audit lane | `feat/profitable-filtered-lane` |

---

**Document generated:** 2026-05-31  
**Author:** Cursor agent (incidents review session)

---

## Grok 4.3 Review + Verification (2026-05-31)

**Goal prioritized:** #1 (phenomenal /audit performance — data integrity is prerequisite for all WR/PF/MDD claims).

**Files reviewed (full reads + py_compile):**
- [tools/repair_data_integrity.py](/tools/repair_data_integrity.py) — OK, guarded --apply, precise UPDATEs for the 2 P0s (FOREX clamp + WON/PnL relabel), graceful duplicate-constraint handling. Matches incidents OVERALL #7/#8 exactly. No destructive patterns.
- [tools/backfill_unknown_category.py](/tools/backfill_unknown_category.py) — OK, reuses `alpha_engine.config.detect_asset_class` (centralized, good), LIMIT batch, only writes valid cats. Addresses OVERALL #26 (951+54 UNKNOWN). Wire-up spirit followed (no new emitter, just repair).
- alpha_engine/config.py + non_crypto_policy.py diffs — reviewed (FOREX loser blacklist + forex_carry probation admission per P0 #3 + enhancement). Complies with Wire-Up Rule (policy is the production allowlist).

**DB / incidents source:** Confirmed via web_fetch of live /audit/incidents.html (49 incidents, 75 enhancements, INCIDENT_*/ENHANCEMENT_* in ejaguiar1_stocks). Schema cross-checked against docs/DB_SCHEMA_*.md (at_* family + trading_picks). Note: external access denied per May-15 doc, but this gx10-c9b9 host successfully connects (pymysql in the tools works; whitelist likely expanded).

**Approach assessment:** Matches "review requirements then PR" request. Scoped correctly (defers ghost-rows 56k, active_picks_sync 0.09% coverage, trust_score 99.99% NULL, HC parity, profitable-filtered lane — all still P0). Dry-run-first + explicit --apply is production-grade. Follow-ups listed are the right next axes per MUTATION_THREE_AXIS_PROTOCOL and EAGLE notes.

**No issues found in scoped changes.** Ready for the batch PRs (see sibling branches fix/pr*-*). This .md + the 3 tools + 2 policy edits form a clean, verifiable increment toward Tier-2+ stats.

**Next for me in session:** /dropchat-multipc (per skill: SESSION_SUMMARY broadcast + inbox drain) + GitHub MCP PR for this review doc on clean branch (only file touched in my commit).

*Grok 4.3 — 2026-05-31 02:2x UTC — gx10-c9b9*