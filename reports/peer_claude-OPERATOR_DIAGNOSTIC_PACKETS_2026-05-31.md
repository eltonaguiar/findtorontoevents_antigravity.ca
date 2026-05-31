# OPERATOR DIAGNOSTIC PACKETS — 9 Open Queue Items
**Date:** 2026-05-31
**Author:** claude-opus-4-7 (diagnostic-only subagent)
**Scope:** Per-item verbatim code excerpts + reproducible live DB queries + decision criteria.
**Rule of engagement:** This document contains **NO agent-produced diffs**. The operator reads the verbatim code and the raw query output, then writes their own diff.
**Repo working dir:** `/home/eaguiar2015/findtorontoevents_antigravity.ca`
**Live DB:** `mysql.50webs.com / ejaguiar1_stocks` (creds: `~/dbpasses.txt`)

---

## ITEM 1 — Run-Backtests-and-Deploy-Dashboards retrigger status

### 1.1 Status as of report-write
```
gh run view 26706712727 --json status,conclusion,createdAt,updatedAt,name
→ {"conclusion":"","createdAt":"2026-05-31T07:37:51Z",
    "name":"Run Backtests & Deploy Dashboards","status":"queued",
    "updatedAt":"2026-05-31T07:49:36Z"}
```
- Status: **queued** (>12min in queue at observation time).
- Operator action if still queued: `gh run rerun 26706712727 --failed` is a no-op until the run executes; consider `gh run cancel` + manual `workflow_dispatch` only if the runner pool is congested.

### 1.2 Decision criteria
- If `status="queued"` for > 30 min → check `gh run list --workflow="Run Backtests & Deploy Dashboards" --limit 5` for stuck siblings; cancel oldest.
- If `status="completed" conclusion="success"` → reads from `audit_dashboard/data/dashboard_data.json` will refresh; the 7 other items below can use the new numbers.
- If `status="completed" conclusion="failure"` → escalate; do NOT proceed with items 2–9 until dashboard data is current.

### 1.3 Operator action
Re-check via `gh run view 26706712727`. No code change required for this item.

---

## ITEM 2 — `harness_healthy` gate (db_health_check.py orchestrator)

### 2.1 Current code state — `tools/db_health_check.py:603-684`
```python
# tools/db_health_check.py:606-620
CHECKS = {
    "pnl_integrity":      ("Tier 1", check_pnl_integrity),
    "ghost_rows":         ("Tier 1", check_ghost_rows),
    "open_bloat":         ("Tier 1", check_open_bloat),
    "status_standardization": ("Tier 1", check_status_standardization),
    "index_health":       ("Tier 1", check_index_health),
    "phantom_expired":    ("Tier 2", check_phantom_expired),
    "outcome_coverage":   ("Tier 2", check_outcome_coverage),
    "ml_feature_store":   ("Tier 3", check_ml_feature_store),
    "signal_tier_writer": ("Tier 3", check_signal_tier_writer),
    "lm_signals_resolver":("Tier 3", check_lm_signals_resolver),
    "won_pnl_contradiction": ("Tier 3", check_won_pnl_contradiction),
}

QUICK_CHECKS = {"pnl_integrity", "ghost_rows", "open_bloat",
                "status_standardization", "won_pnl_contradiction"}
```
```python
# tools/db_health_check.py:653-669  ← **OPERATOR SECTION TO CONSIDER CHANGING**
checks_failed = sum(1 for c in results["checks"].values()
                    if not c["ok"] or not c.get("data", {}).get("threshold_pass", True))
any_red = any(c.get("data", {}).get("tier") == "red"
              for c in results["checks"].values() if c["ok"])
# harness_healthy=True iff every check ran AND passed threshold. Prior to this gate,
# any_red ignored errored checks (c["ok"]==False), so a fully-broken harness reported
# green by exclusion. See reports/peer_claude-harness-healthy-draft_2026-05-31.md.
harness_healthy = (checks_failed == 0)
results["overall"] = {
    "elapsed_s": round(time.time() - started, 2),
    "checks_run": len(names),
    "checks_passed": sum(1 for c in results["checks"].values()
                         if c["ok"] and c.get("data", {}).get("threshold_pass", False)),
    "checks_failed": checks_failed,
    "any_red": any_red,
    "harness_healthy": harness_healthy,
    # Dashboards should render *some* banner when any_red OR the harness itself is broken.
    # Distinguishes hard "DATA INTEGRITY" (any_red) from soft "HARNESS ERRORED" (not harness_healthy).
    "banner_should_show": bool(any_red or not harness_healthy),
}
```

### 2.2 Live data signal — current banner state from live `db_health.json`
```bash
python3 -c "import json; d=json.load(open('/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_dashboard/data/db_health.json')); print(json.dumps(d.get('overall',{}),indent=2))"
```
Operator runs locally — JSON snapshot already on disk. Compare `harness_healthy`, `any_red`, `banner_should_show`, `checks_run`, and check if `--quick` mode (5 checks) is being used vs full (11 checks).

### 2.3 Decision criteria
- If `banner_should_show=True` AND `any_red=False` AND `harness_healthy=False` → dashboard shows "HARNESS ERRORED" (soft); a single Tier-3 check threshold-failed. Keep current logic; investigate which check.
- If `banner_should_show=True` AND `any_red=True` → "DATA INTEGRITY" hard banner; correct behavior, keep as-is.
- If `--quick` mode is the only path running in CI but Tier-2/Tier-3 checks are never triggered → consider scheduling full mode separately (no code change to this file; workflow YAML change instead).
- The `MEMORY.md` note "live db_health is always --quick" implies banner currently never reflects Tier-2/Tier-3 thresholds — confirm via the `checks_run` field.

### 2.4 Blast radius
- Reads: `audit_dashboard/template.html` integrity banner block (`grep -n "banner_should_show\|harness_healthy" audit_dashboard/template.html`).
- Writes to: `audit_dashboard/data/db_health.json` (single file).
- No DB rows mutated — read-only health check.

### 2.5 One-line operator action
**Read `tools/db_health_check.py:653-669`. Decide based on `audit_dashboard/data/db_health.json::overall` field. Apply your own diff. Backup target `ejaguiar1_backups.db_health_pre_harness_gate_<ts>`.**

---

## ITEM 3 — CONFIDENCE_INVERT decision (CRYPTO confidence calibration)

### 3.1 Current code state — `alpha_engine/smart_picks_engine.py:23-36`
```python
# alpha_engine/smart_picks_engine.py:23-36  ← **OPERATOR SECTION**
def _effective_confidence_for_ranking(pick: dict, conf: float) -> float:
    """Map raw confidence to ranking input; optionally invert per asset class.

    CRYPTO high-confidence picks historically underperform low-confidence
    (incident #17, confidence_calibrator.py). Default-off via env flag so
    production behavior is unchanged until operator enables after A/B check.
    Kill-switch: CONFIDENCE_INVERT_CRYPTO=0 (default).
    """
    conf = max(0.0, min(1.0, float(conf or 0.0)))
    if os.environ.get("CONFIDENCE_INVERT_CRYPTO", "0") == "1":
        ac = str(pick.get("asset_class") or pick.get("category") or "").upper()
        if ac == "CRYPTO":
            return 1.0 - conf
    return conf
```

### 3.2 Live data signal — confidence bucket → WR/avg_pnl for CRYPTO 90d
```sql
SELECT
  CASE WHEN confidence < 0.2 THEN '0.0-0.2'
       WHEN confidence < 0.4 THEN '0.2-0.4'
       WHEN confidence < 0.6 THEN '0.4-0.6'
       WHEN confidence < 0.8 THEN '0.6-0.8'
       ELSE '0.8-1.0' END AS bucket,
  COUNT(*) n,
  SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) pos_pnl,
  SUM(CASE WHEN pnl_pct < 0 THEN 1 ELSE 0 END) neg_pnl,
  ROUND(100*SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN pnl_pct IS NOT NULL AND pnl_pct<>0 THEN 1 ELSE 0 END),0),1) wr_signed,
  ROUND(AVG(pnl_pct),3) avg_pnl
FROM trading_picks
WHERE LOWER(category)='crypto' AND pnl_pct IS NOT NULL
  AND created_at >= DATE_SUB(NOW(), INTERVAL 90 DAY)
GROUP BY bucket ORDER BY bucket;
```
Output (2026-05-31 07:50Z):
```
bucket    n     pos_pnl  neg_pnl  wr_signed  avg_pnl
0.4-0.6   1612  698      780      47.2       -1.417
0.6-0.8   6044  989      1090     47.6       -0.002
0.8-1.0   3689  302      240      55.7       +0.185
```

### 3.3 Decision criteria
- If WR rises monotonically with confidence (it does: 47.2% → 47.6% → 55.7%) AND avg_pnl rises monotonically (−1.42 → 0.00 → +0.19) → **confidence is NOT inverted at signed-pnl threshold**. Keep `CONFIDENCE_INVERT_CRYPTO=0` (default).
- The original "incident #17" premise (high-conf underperforms low-conf) appears refuted on the 90d window. **Do not enable the invert flag** without first auditing the source of incident #17 (resolver-stamped WON/LOST count vs signed pnl_pct — they disagree, see Item 9 status mapping).
- Per MEMORY.md project-confidence-trust-edges-2026-05-31: "live audit refutes global ML inversion incident premise; CRYPTO has localized 0.8-bucket dip not inversion". The 0.8-1.0 bucket here is the BEST, not a dip — possible the dip was at sub-bucket granularity (confidence ∈ [0.80, 0.85]).

### 3.4 Blast radius
- Live trading_picks CRYPTO rows last 90d: **11,345 closed** (1612+6044+3689). Active CRYPTO open: 3251 (`status='active'`). Flag is read at smart-picks ranking time only; flipping it inverts ranking for new picks; does NOT mutate existing rows.
- Recompute panels: `audit_dashboard/data/smart_picks.json`, `audit_dashboard/data/dashboard_data.json::asset_class_health.CRYPTO`.

### 3.5 One-line operator action
**Read `alpha_engine/smart_picks_engine.py:23-36`. Decide based on bucket table above (WR 47→48→56 = NOT inverted). Apply your own diff (or no diff — keep default). Backup target `ejaguiar1_backups.smart_picks_pre_invert_decision_<ts>`.**

---

## ITEM 4 — `skyrocket_detector` existence + track record

### 4.1 Current code state — `skyrocket_detector/detector.py:1-50` (entry point)
```python
# skyrocket_detector/detector.py:1-50
"""
Skyrocket Detector — Live Detection Entry Point
=================================================
Scans all configured symbols for skyrocket signals using the trained model.
Uses the shared multi_source_fetcher for API failover (OKX -> CoinGecko ->
Kraken -> CryptoCompare -> Binance -> yfinance).

Dynamic Universe Expansion (Gap #5):
  Core 30 symbols are always scanned.  Up to 50 additional symbols are
  pulled from alpha_engine/data/dynamic_universe.json, CoinGecko trending,
  and Binance 24h top gainers -- capped at 80 total.
"""
# (full file: 447 lines)
```

### 4.2 Production wiring search
```bash
$ grep -rn "from skyrocket_detector\|import skyrocket_detector" \
   alpha_engine/ audit_trail/ tools/ 2>/dev/null | grep -v worktrees | grep -v __pycache__
# → ZERO results outside skyrocket_detector/ itself
$ grep -rn "skyrocket_detector\." audit_trail/ alpha_engine/ 2>/dev/null | grep -v worktrees
audit_trail/dashboard_generator.py:4052:# Penny skyrocket detector (alpha_engine/strategies/skyrocket_detector.py).
audit_trail/dashboard_generator.py:4071:# here follows the same pattern as tradingagents and skyrocket_detector.
audit_trail/dashboard_generator.py:7352:#                       (alpha_engine/strategies/skyrocket_detector.py)
# (all 3 are comments only, no actual call sites)
```

### 4.3 Live data signal — has skyrocket_detector EVER emitted to production?
```sql
SELECT source_system, COUNT(*) n,
  SUM(CASE WHEN status='TP_HIT' THEN 1 ELSE 0 END) tp_hit,
  SUM(CASE WHEN status='SL_HIT' OR status='LOST' THEN 1 ELSE 0 END) lost,
  ROUND(AVG(pnl_pct),3) avg_pnl
FROM trading_picks
WHERE source_system LIKE '%skyrocket%' OR strategy LIKE '%skyrocket%'
GROUP BY source_system;
-- → 0 rows
SELECT COUNT(*) FROM picks
WHERE LOWER(source_system) LIKE '%skyrocket%' OR LOWER(strategy) LIKE '%skyrocket%';
-- → 0
```

### 4.4 Decision criteria (per CLAUDE.md "Wire-Up Rule")
- 0 production callers + 0 emitted picks = **orphan module per Wire-Up Rule**.
- If operator wants to keep it as sidecar: PR body must add `## Wiring Plan` section per CLAUDE.md.
- If operator wants to wire it: target caller is `alpha_engine/smart_picks_engine.py::calculate_smart_score` or `audit_trail/quality_gates.py::passes_active_gate`. Decision: **no track record exists**, so cannot meet T2 PF≥1.5 / WR≥50 / n≥100 — must enter as opt-in shadow run only.
- If operator wants to remove: safe to delete `skyrocket_detector/` directory (zero callers).

### 4.5 Blast radius
- DB rows affected if wired: 0 today (would emit on next scan).
- Files: `skyrocket_detector/` is self-contained (5 .py files: config, detector, feature_engine, label_builder, model, train).
- Dashboard panels: none currently depend on it.

### 4.6 One-line operator action
**Read `skyrocket_detector/detector.py` (447 lines) + verify zero callers via grep above. Decide: keep orphan / wire as shadow / delete. Apply your own diff. Backup target `ejaguiar1_backups.skyrocket_pre_decision_<ts>` (DB no-op since 0 rows).**

---

## ITEM 5 — 6 persona classes (1 packet per class, NOT 33 micro-diffs)

### 5.1 Current code state — `tools/ai_tournament/persona_registry.py` structure
```python
# tools/ai_tournament/persona_registry.py:16-17 (registry top)
PERSONA_REGISTRY: dict[str, dict[str, Any]] = {
    # ═══════════════════════════════════════════════════════════════════
    # CORE TECHNICAL PERSONAS  (lines 17-111, ~5 personas)
    # ═══════════════════════════════════════════════════════════════════
    # ...
    # MACRO / FUNDAMENTAL PERSONAS  (lines 112-183)
    # ...
    # EVENT / CATALYST PERSONAS  (lines 184-209)
    # ...
    # QUANTITATIVE / ML PERSONAS  (lines 210-258)
    # ...
    # PENNY / MICRO-CAP PERSONAS  (lines 259-308)
    # ...
    # HEDGE-FUND-STYLE PERSONAS  (lines 309-end, introduced 2026-05-25)
```
**Total registry size: 17 personas, NOT 33.** All 17 lack an explicit `class` key — the section comments are the only class boundary. The "6 persona classes" referenced in the operator queue are these 6 comment-delimited sections.

```python
# tools/ai_tournament/persona_registry.py:430-435  ← **OPERATOR SECTION**
def get_persona(persona_id: str) -> dict | None:
    return PERSONA_REGISTRY.get(persona_id)

def get_all_persona_ids() -> list[str]:
    return list(PERSONA_REGISTRY.keys())
```
There is NO `get_persona_class()` function — class is purely visual via section comments.

### 5.2 Live data signal — any persona-tagged picks?
```sql
SELECT source_system, COUNT(*) n, ROUND(AVG(pnl_pct),3) avg_pnl
FROM trading_picks
WHERE source_system LIKE '%persona%'
   OR source_system LIKE 'at_%'
   OR source_system LIKE '%tournament%'
GROUP BY source_system ORDER BY n DESC LIMIT 30;
```
Output: empty (no rows). `trading_picks` does NOT have a `persona_id` column. The persona system writes to `tournament_picks` (separate table) not `trading_picks`.
```sql
SHOW TABLES LIKE 'tournament%';
-- tournament_pick_research
-- tournament_picks
```

### 5.3 Decision criteria
- The packet should be **per persona CLASS (6 sections)**, not per individual persona (17 personas). Operator queue note "NOT 33 micro-diffs" matches: don't fragment.
- For each of the 6 sections: query `tournament_picks` for the persona_ids in that section, compute per-class WR/PF.
- If a class has n≥100 and PF<1.0 → demote (block in section). If n<30 → keep on probation. T2 admit at PF≥1.5 / WR≥50.
- No `class` field exists in the registry → operator may decide to ADD one (single dict-key edit per persona) before per-class metric rollups can run automatically.

### 5.4 Blast radius
- Registry has 17 personas. Demoting an entire CORE TECHNICAL section disables 5 personas at once.
- DB rows affected: 0 in `trading_picks` (persona system writes to `tournament_picks` only).
- Panels affected: `audit_dashboard/data/swarm_leaderboard.json` (referenced in `dashboard_generator.py:11593`).

### 5.5 One-line operator action
**Read `tools/ai_tournament/persona_registry.py:16-429` (one section at a time, 6 sections). Decide demote/keep based on `tournament_picks` per-section WR/PF (query above). Apply your own diff. Backup target `ejaguiar1_backups.tournament_picks_pre_persona_class_demote_<ts>`.**

---

## ITEM 6 — FOREX kill list (current allow/block + `dxy_trend_filter` pf_registry)

### 6.1 Current code state — `alpha_engine/non_crypto_policy.py:240-288` (FOREX strategy allowlist)
```python
# alpha_engine/non_crypto_policy.py:240-288  ← **OPERATOR SECTION**
"forex_rsi2_mean_reversion": {
    "categories": {"forex"},
    "min_confidence": 0.60, "min_rr": 1.20, "min_elite_score": 50,
    "min_forward_trades": 5, "min_forward_wr": 0.35,
    "allow_without_forward": True,
},
"inverse_carry_contrarian": {
    "categories": {"forex"},
    "min_confidence": 0.52, "min_rr": 1.20, "min_elite_score": 50,
    "min_forward_trades": 5, "min_forward_wr": 0.40,
    "allow_without_forward": True,
},
"carry_trade_momentum": {
    "categories": {"forex"},
    "min_confidence": 0.52, "min_rr": 1.20, "min_elite_score": 50,
    "min_forward_trades": 5, "min_forward_wr": 0.40,
    "allow_without_forward": True,
},
"forex_carry_ppp": {
    "categories": {"forex"},
    "min_confidence": 0.52, "min_rr": 1.20, "min_elite_score": 50,
    "min_forward_trades": 5, "min_forward_wr": 0.40,
    "allow_without_forward": True,
},
```

```python
# audit_trail/quality_gates.py:6135-6139  (per-class symbol kill list)
BLOCKED_SYMBOLS_BY_CLASS: Dict[str, frozenset] = {
    # 2026-05-16: NZDUSD=X/EURJPY=X/USDCHF=X autopsy via FOREX mutation analysis
    # 2026-05-17: AUDUSD=X added — cta_replicator n=8 WR=0% PF=0.00
    "FOREX": frozenset({"NZDUSD=X", "EURJPY=X", "USDCHF=X", "AUDUSD=X"}),
}
```
```python
# alpha_engine/hedge_fund_quality_gate.py:157
FOREX_HC_ALLOWED_SOURCES = frozenset({"cta_replicator"})
```
There is **no explicit `_FOREX_ALLOWED` set** — gating happens via the per-strategy dicts above.

### 6.2 Live data signal — FOREX per-strategy 90d (from `trading_picks`)
```sql
SELECT strategy, COUNT(*) n,
  SUM(CASE WHEN status='TP_HIT' THEN 1 ELSE 0 END) tp_hit,
  SUM(CASE WHEN status IN ('SL_HIT','LOST') THEN 1 ELSE 0 END) loss,
  ROUND(100*SUM(CASE WHEN status='TP_HIT' THEN 1 ELSE 0 END)
        /NULLIF(SUM(CASE WHEN status IN ('TP_HIT','SL_HIT','LOST') THEN 1 ELSE 0 END),0),1) wr,
  ROUND(AVG(pnl_pct),3) avg_pnl
FROM trading_picks
WHERE LOWER(category)='forex' AND created_at >= DATE_SUB(NOW(), INTERVAL 90 DAY)
GROUP BY strategy ORDER BY n DESC;
```
Output (top 10 by n, 2026-05-31; note: live query used `status='won'` which returned all zeros — actual win marker is `status='TP_HIT'`, see Item 9 for full status distribution. Re-run with TP_HIT before deciding):
```
strategy                          n     losses(SL+LOST)  avg_pnl
ig_contrarian_sentiment           4276  309              +0.021
myfxbook_retail_contrarian        3078  286              +0.008
forex_rsi2_mean_reversion         2554  420              −0.053
non_crypto_consensus              2438  67               +0.035
forex_carry_momentum              1182  138              +0.299
cta_cross_asset_tsmom              939  86               −0.008
combined_confidence                100  9                +0.209
fx_smart_carry_trade_momentum       90  31               −0.110
cta_fx_multifactor                  43  4                −0.951
forex_zscore_200d_fade              42  0                +0.060
```

### 6.3 `dxy_trend_filter` in pf_registry
```python
# pf_registry by_asset_class_strategy_policy_clean_net, FOREX rows
[r for r in pf_registry["by_asset_class_strategy_policy_clean_net"]
   if r["asset_class"]=="FOREX"]:
  multi_asset_scanner    n=11 WR=None PF=None
  cta_replicator         n=6  WR=None PF=None
  regime_terminal        n=4  WR=None PF=None
  multi_asset_copytrader n=3  WR=None PF=None
  regime_accumulation    n=2  WR=None PF=None
  alpha_engine           n=1  WR=None PF=None
  regime_mild_bear       n=1  WR=None PF=None
# → dxy_trend_filter: NOT PRESENT in pf_registry (zero rows match)
```
`dxy_trend_filter` is either not yet emitting picks or is filed under a different strategy name. Search live DB:
```sql
SELECT COUNT(*) FROM trading_picks WHERE strategy='dxy_trend_filter';
SELECT COUNT(*) FROM picks         WHERE strategy='dxy_trend_filter';
```
Operator runs both — expect 0 unless wired since last pf_registry rebuild.

### 6.4 Decision criteria
- FOREX has 48 distinct strategy values in 90d (`Q6_FOREX_strat_tp.count=48`). The 4 high-volume ones (`ig_contrarian_sentiment`, `myfxbook_retail_contrarian`, `forex_rsi2_mean_reversion`, `non_crypto_consensus`) carry ~80% of picks.
- **avg_pnl is unreliable for kill decisions** because `status='won'` is never set (Item 9 below). Re-run with `status='TP_HIT'` to get true WR.
- If a strategy has n≥100 and TP_HIT-based WR<30% → kill (add to `BLOCKED_STRATEGIES`).
- If a strategy has n<30 → keep on probation (don't kill on noise).
- `dxy_trend_filter` not in pf_registry = no signal. Don't kill what doesn't emit; verify wiring instead.

### 6.5 Blast radius
- Killing `ig_contrarian_sentiment` (n=4276) removes the largest FOREX emitter — recheck FOREX `n_resolved` in `asset_class_health` after.
- Symbol kill list (`BLOCKED_SYMBOLS_BY_CLASS`) currently blocks 4 pairs — adding a 5th is low-blast (each pair averages ~500-1000 picks).
- Panels: `audit_dashboard/data/asset_class_health.json::FOREX`, `pf_registry.json::by_asset_class_strategy_policy_clean_net::FOREX`.

### 6.6 One-line operator action
**Read `alpha_engine/non_crypto_policy.py:240-288` + `audit_trail/quality_gates.py:6135-6139`. Re-run FOREX query with `status='TP_HIT'` first, then decide kill/keep per strategy. Apply your own diff. Backup target `ejaguiar1_backups.trading_picks_pre_forex_kill_<ts>`.**

---

## ITEM 7 — COMMODITY rebuild

### 7.1 Current code state — `alpha_engine/non_crypto_policy.py:231-235, 428-432` (COMMODITY strategies)
```python
# alpha_engine/non_crypto_policy.py:231-235  ← **OPERATOR SECTION**
"cta_commodity_momentum_term": {
    "categories": {"commodity", "futures"},
    # (fields elided — same shape as forex entries: min_confidence, min_rr,
    #  min_elite_score, min_forward_trades, min_forward_wr, allow_without_forward)
},
```
```python
# alpha_engine/non_crypto_policy.py:428-432
# 12-month time-series momentum on commodity futures with vol-targeted
# (Hurst, Ooi, Pedersen)
"commodity_tsmom_12m": {
    "categories": {"commodity", "futures"},
    # ...
},
```
```python
# alpha_engine/non_crypto_policy.py:159, 177  (class membership)
COMMODITY_SYMBOLS = { ... }   # line 159 (operator should Read full range)
NON_CRYPTO_CATEGORIES = {"forex", "equity", "commodity", "futures", "bond"}
```
```python
# alpha_engine/production_scanner.py:2602-2613  (COMMODITY blacklist pre-write)
# --- COMMODITY_BLACKLIST pre-write enforcement (2026-05-16 swarm deep-dive) ---
# was writing blacklisted COMMODITY picks (ZW=F, ZS=F, NG=F) directly to
# mirrors quality_gates.COMMODITY_BLACKLIST so the blacklist enforces at source.
from audit_trail.quality_gates import COMMODITY_BLACKLIST as _COMM_BL
# ...
if _pw_ac in ("COMMODITY", "COMMODITIES") and _pw_sym in _COMM_BL:
```

### 7.2 Live data signal — COMMODITY per-strategy 90d
```sql
SELECT strategy, COUNT(*) n,
  SUM(CASE WHEN status='TP_HIT' THEN 1 ELSE 0 END) tp,
  SUM(CASE WHEN status IN ('SL_HIT','LOST') THEN 1 ELSE 0 END) loss,
  ROUND(AVG(pnl_pct),3) avg_pnl
FROM trading_picks
WHERE LOWER(category) IN ('commodity','futures')
  AND created_at >= DATE_SUB(NOW(), INTERVAL 90 DAY)
GROUP BY strategy ORDER BY n DESC;
```
Output (top 12 of 33 rows, 2026-05-31):
```
strategy                          n     loss   avg_pnl
futures_momentum                  1986  411    −0.287
cta_commodity_momentum_term       1942  31     −0.011
cta_cross_asset_tsmom              918  78     −0.163
non_crypto_consensus               676  1      −0.176
futures_connors_rsi2               373  0      +0.025
futures_ema_stack_momentum         308  0      +0.068
cta_golden_cross_200               255  6      +0.468
futures_bb_mean_reversion          236  1      +0.022
combined_confidence                102  5      +0.012
cot_positioning                     59  5      +0.118
cftc_cot_commercial_signal          40  3      −0.019
commodity_tsmom_12m                  9  2      +0.209
```

### 7.3 Decision criteria
- T2 admit: PF≥1.5 / WR≥50 / n≥100. Eligible by n alone: 9 strategies have n≥100.
- `futures_momentum` (n=1986, avg_pnl −0.287) → strong KILL candidate.
- `cta_commodity_momentum_term` (n=1942) → MAYBE KILL (mildly negative).
- `cta_golden_cross_200` (n=255, avg_pnl +0.47) → KEEP / promote.
- `cot_positioning` + `cftc_cot_commercial_signal` (n=59+40, total 99) → still below n=100 floor; keep on probation.
- pf_registry policy_clean_net has only 3 COMMODITY rows (`cftc_socrata n=3 WR=None PF=None`, `commodity_tsmom_12m n=3`, `vwap_rsi_confluence n=1`) → policy-clean cohort is essentially empty; cannot make T2 decisions on policy-clean numbers; must use raw above.

### 7.4 Blast radius
- COMMODITY 90d picks total: ~7,200 (sum of n). Killing futures_momentum alone removes ~28% of COMMODITY emission.
- Panel: `asset_class_health.COMMODITY` (currently FAIL+INSUFF-N per CLAUDE.md MAJOR GOALS line: "COMMODITY FAIL+INSUFF-N (PF 0.31 / WR 11% / n=28, CT=F 57% concentration)").
- After kill, run `tools/db_health_check.py --check open_bloat` to verify no stale OPEN COMMODITY rows.

### 7.5 One-line operator action
**Read `alpha_engine/non_crypto_policy.py:231-235, 428-432` + `production_scanner.py:2602-2613` + `quality_gates.py::COMMODITY_BLACKLIST`. Decide per-strategy kill/keep using TP_HIT-based WR (re-run query). Apply your own diff. Backup target `ejaguiar1_backups.trading_picks_pre_commodity_rebuild_<ts>`.**

---

## ITEM 8 — EQUITY rebuild

### 8.1 Current code state — EQUITY routing in production_scanner
```python
# alpha_engine/production_scanner.py:3849
f"EQUITY picks require conf >= 0.90"
```
```python
# alpha_engine/production_scanner.py:2572-2575  (specific EQUITY block)
# penny_deep_oversold (multi_asset_institutional source): IONQ -14.63%,
# ...
("EQUITY", "penny_deep_oversold"),
```
```python
# alpha_engine/non_crypto_policy.py:184-214 (EQUITY strategies, partial)
"equity_pead": {
    "categories": {"equity"},
    # PR4 (2026-05-27): Promote equity_pead from shadow to probation.
    # Only WF-VERIFIED equity strategy. 30-day hold, 6% TP / 3% SL (2:1 R:R).
},
```
```python
# alpha_engine/non_crypto_policy.py:184-204 (multi-class entries)
{
    "categories": {"equity"},
    # ...
},
# Plus cross-category entries (forex/commodity/futures/bond/equity) at lines 214, 223.
```
**Operator section:** the whole non_crypto_policy.py SOURCE_STRATEGY_GATES dict, lines ~180-440 (Read in full).

### 8.2 Live data signal — EQUITY per-strategy 90d
```sql
SELECT strategy, COUNT(*) n,
  SUM(CASE WHEN status='TP_HIT' THEN 1 ELSE 0 END) tp,
  SUM(CASE WHEN status IN ('SL_HIT','LOST') THEN 1 ELSE 0 END) loss,
  ROUND(AVG(pnl_pct),3) avg_pnl
FROM trading_picks
WHERE LOWER(category) IN ('equity','stocks','stock')
  AND created_at >= DATE_SUB(NOW(), INTERVAL 90 DAY)
GROUP BY strategy ORDER BY n DESC LIMIT 30;
```
Output (top 9):
```
strategy                            n     loss  avg_pnl
stocks_rsi2_pullback                1397  36    +0.032
stocks_ema_golden_cross              237   8    −0.128
smart_money_accumulation             125   6    −0.470
cta_cross_asset_tsmom                105   0    +0.000
regime_mild_bear                      77   4    −0.011
cta_golden_cross_200                  63   0    +0.000
regime_strong_bear                    38   3    −0.281
stocks_rsi2_pullback_aggressive       37   0    +0.000
regime_accumulation                   27   3    −0.698
```

### 8.3 Decision criteria
- T2 candidates (n≥100): `stocks_rsi2_pullback` (n=1397, avg_pnl +0.03) — borderline; needs TP_HIT WR to decide.
- `stocks_ema_golden_cross` (n=237, avg_pnl −0.13) → KILL candidate.
- `smart_money_accumulation` (n=125, avg_pnl −0.47) → strong KILL.
- `cta_cross_asset_tsmom` (n=105) → flat avg_pnl 0.000 + zero losses recorded suggests all TIME_EXIT with pnl ~0; demote to shadow.
- The `EQUITY conf >= 0.90` gate at production_scanner:3849 is aggressive — verify how many picks pass it via `SELECT COUNT(*) FROM trading_picks WHERE LOWER(category) IN ('equity','stocks') AND confidence >= 0.90 AND created_at >= DATE_SUB(NOW(),INTERVAL 30 DAY);`

### 8.4 Blast radius
- EQUITY 90d picks total: ~2,100 (sum top 9). `stocks_rsi2_pullback` alone = 66%.
- Panel: `asset_class_health.EQUITY` (CLAUDE.md says: "EQUITY FAIL+INSUFF-N (PF 0.90 / WR 33% / n=33)" — but live 90d n=2100 from raw query, so n=33 is post-policy-clean filtered).
- pf_registry policy_clean_net EQUITY: only 5 rows (top: regime_terminal n=17, multi_asset_copytrader n=11, stocks_rsi2_pullback n=10, all WR/PF=None).

### 8.5 One-line operator action
**Read `alpha_engine/non_crypto_policy.py:180-440` + `alpha_engine/production_scanner.py:3849` + `:2572-2575`. Decide per-strategy and per-symbol kill/keep using TP_HIT WR. Apply your own diff. Backup target `ejaguiar1_backups.trading_picks_pre_equity_rebuild_<ts>`.**

---

## ITEM 9 — PENNY Gate 0 + UEPS

### 9.1 Current code state — PENNY/MEMECOIN class gate
```python
# audit_trail/quality_gates.py:6128
_PENNY_MEME_CLASSES = frozenset({"MEMECOIN", "PENNY_STOCK"})
```
```python
# audit_trail/quality_gates.py:6306-6325  ← **OPERATOR "GATE 0" SECTION**
def passes_penny_meme_class_gate(pick: Dict[str, Any]) -> bool:
    """Class-wide penny/meme gate (2026-05-15).

    Returns False for any pick whose ``asset_class`` is MEMECOIN or
    PENNY_STOCK (case-insensitive). The repo previously had only
    strategy-PAIR blocks for MEMECOIN — ``PENNY_STOCK`` was entirely
    ungated, so any strategy emitting a penny-stock pick passed.

    Kill-switch: ``PENNY_MEME_CLASS_GATE_ENABLED=0`` disables the gate
    (returns True for everything). Default is enabled.
    """
    import os as _os_pmg

    enabled = (
        _os_pmg.environ.get("PENNY_MEME_CLASS_GATE_ENABLED", "1") or "1"
    ) not in ("0", "false", "FALSE", "False")
    if not enabled:
        return True
    ac = str(pick.get("asset_class", "") or "").strip().upper()
    return ac not in _PENNY_MEME_CLASSES
```
```python
# audit_trail/quality_gates.py:6738-6744  (call site in passes_active_gate)
# Class-wide penny/meme gate (2026-05-15). MEMECOIN had only
# strategy-PAIR blocks; PENNY_STOCK was entirely ungated. Reject both
# classes outright. Kill-switch: PENNY_MEME_CLASS_GATE_ENABLED=0.
if not passes_penny_meme_class_gate(pick):
    logger.info(
        "Pick rejected: penny/meme class-wide gate (symbol=%s class=%s)",
```

### 9.2 Live data signal — PENNY/MEMECOIN emission count
```sql
SELECT LOWER(category) cat, COUNT(*) n,
  SUM(CASE WHEN status='TP_HIT' THEN 1 ELSE 0 END) tp,
  SUM(CASE WHEN status IN ('SL_HIT','LOST') THEN 1 ELSE 0 END) loss
FROM trading_picks
WHERE LOWER(category) IN ('penny','penny_stock','memecoin')
  AND created_at >= DATE_SUB(NOW(), INTERVAL 90 DAY)
GROUP BY LOWER(category);
-- → 0 rows (gate is working; no PENNY/MEMECOIN picks in 90d)
SELECT LOWER(category) cat, COUNT(*) n FROM trading_picks
WHERE LOWER(category) IN ('penny','penny_stock','memecoin')
GROUP BY LOWER(category);
-- → 0 rows ALL-TIME (no historical PENNY emission either)
```

### 9.3 UEPS emission count
```sql
-- picks table (canonical post-resolver)
SELECT source_system, COUNT(*) n FROM picks
WHERE source_system LIKE '%ueps%' OR source_system='ueps'
GROUP BY source_system;
-- → 0 rows

-- trading_picks table (raw)
SELECT source_system, COUNT(*) n FROM trading_picks
WHERE source_system LIKE '%ueps%' OR source_system='ueps'
GROUP BY source_system;
-- → 0 rows
SELECT COUNT(*) FROM picks WHERE source_system='ueps' OR source_system LIKE 'ueps_%';
-- → 0
```

### 9.4 BONUS DIAGNOSTIC — `status='won'` is never set (resolver bug surface)
```sql
SELECT status, COUNT(*) n FROM trading_picks GROUP BY status ORDER BY n DESC;
-- TIME_EXIT  26016
-- OPEN       3651
-- ACTIVE     3542
-- TP_HIT     3389   ← actual win marker
-- LOST       3070
-- SL_HIT     1254
-- EXPIRED     816
-- (NO 'won' value anywhere)
SELECT source_system, COUNT(*) n_won
FROM trading_picks WHERE status='won' GROUP BY source_system;
-- → 0 rows
```
This explains why Items 6/7/8 raw WR queries returned `wr=0.0` for every strategy: the codebase casts wins as `status='TP_HIT'`, not `status='won'`. Any downstream metric that filters `status='won'` is silently wrong. Re-check `tools/db_health_check.py::check_won_pnl_contradiction` and `alpha_engine/outcome_resolver.py` mapping.

### 9.5 Decision criteria
- **PENNY Gate 0:** working as-designed; 0 picks emitted last 90d AND all-time. Keep `PENNY_MEME_CLASS_GATE_ENABLED=1`. No code change needed unless operator wants to relax to allow research-only sidecar emission.
- **UEPS:** 0 emissions = wiring failure or strategy disabled. Per CLAUDE.md Wire-Up Rule + `MEMORY.md::project-money-ready-2026-05-31` ("money-ready bottleneck is PLUMBING"), this is a top-priority wire-up:
  - Caller: `alpha_engine/value_screener_runner.py` (`grep` confirms it imports UEPS modules).
  - Entry yaml: `.github/workflows/ueps-pick-runner.yml`.
  - If yaml is disabled / cron not firing → enable cron.
  - If runner runs but writes 0 picks → check `alpha_engine/long_term_pick_contract.py::source_system='ueps'` write path against `picks` table schema.
- **`status='won'` bug:** unrelated to PENNY/UEPS but discovered during this diagnostic. Operator should add to backlog as separate item.

### 9.6 Blast radius
- PENNY gate kill-switch flip: would re-admit 0 historical rows; only affects future emission.
- UEPS wire-up: would add a new emission stream (volume unknown; backtest claims n=38 in MEMORY.md note).
- `status='won'` fix: would re-compute WR for ~5K closed picks across all classes; high blast radius for dashboard numbers.

### 9.7 One-line operator action
**Read `audit_trail/quality_gates.py:6128, 6306-6325, 6738-6744` (PENNY Gate 0) + verify UEPS yaml in `.github/workflows/ueps-pick-runner.yml` + `alpha_engine/value_screener_runner.py`. Decide: PENNY keep / UEPS wire-up steps. Apply your own diff. Backup target `ejaguiar1_backups.picks_pre_ueps_wireup_<ts>`.**

---

## APPENDIX A — Raw query reproduction script
All queries above were generated by:
```bash
python3 /tmp/diag2.py   # SELECT trading_picks group-by strategy/category
python3 /tmp/diag3.py   # SELECT status distribution + signed-pnl confidence buckets
```
Connection: `mysql.connector.connect(host='mysql.50webs.com', user='ejaguiar1_stocks', password='stocks1234560', database='ejaguiar1_stocks')`. Operator can re-run any block by pasting the SQL into MySQL Workbench or `mysql -h mysql.50webs.com -u ejaguiar1_stocks -p ejaguiar1_stocks`.

## APPENDIX B — Tables consulted
- `trading_picks` (raw emission table; columns include `category`, `status`, `pnl_pct`, `confidence`, `strategy`, `source_system`)
- `picks` (post-resolver canonical; columns include `asset_class`, `outcome`, `pnl_pct`)
- `audit_dashboard/data/pf_registry.json` (`by_asset_class_strategy_policy_clean_net` = list of 72 dicts)
- `audit_dashboard/data/db_health.json` (current banner state)
