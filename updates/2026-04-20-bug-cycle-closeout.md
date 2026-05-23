# Bug cycle closeout — 2026-04-20

## Fixed

### 1. Asset-class mismatches on closed picks (HIGH)
- **File:** `audit_trail/mysql_client.py:689` (`mysql_fetch_closed_non_crypto`)
- **Symptom:** 7 closed rows on `/audit` tagged with wrong `asset_class` (e.g. `LINKUSDT` → `EQUITY`, `GC=F` → `EQUITY`, `BCH-USD` → `EQUITY`).
- **Root cause:** `_cat_map.get(cat_raw, "EQUITY")` silently defaulted unknown DB category values to `EQUITY`. The MySQL fetch path appended rows directly to `closed` at `dashboard_generator.py:7677`, bypassing `_normalize_pick` / `_derive_asset_class` symbol-override logic.
- **Fix:** Derive `asset_class` from `symbol` first via `resolve_asset_class` (already imported at mysql_client.py:37); fall back to `_cat_map` lookup only if symbol derivation returns empty.
- **Blast radius:** Only 7 / 3500 closed rows affected; no active picks. Upstream emitters (`regime_terminal`, `alpha_engine_fast`, `kimi_signal_tracking`) are not bugged — their JSON outputs are correctly tagged.

### 3. `st_fear_greed_contrarian` promoted to `_RETIRED_STRATEGIES`
- **File:** `alpha_engine/strategy_blocklist.py`
- **Reason:** 640 closed picks under this `st_` prefix variant, 10.5% WR, -381.62% cumulative PnL per Kimi fact-check. #1 historical-damage driver in the entire closed ledger. Parent `fear_greed_contrarian` is already retired; the `st_` variant shares the same underlying logic and was bypassing the hard-block via prefix alone. Paper-only tier was insufficient.

## Not actionable this cycle

### 2. ml_consensus stale-merge — **FALSE POSITIVE**
- Investigation (agent report in conversation log) confirmed the writer is healthy: `ml_consensus/consensus.py` runs every cycle via `.github/workflows/audit-dashboard.yml:311`. The live dashboard has 4 fresh ml_consensus picks with `entry_time: 2026-04-20T13:48:10Z`.
- The "119h stale" reading in `docs/AUDIT_DATA_PIPELINE_GAP_CHECKS_2026_04_20.md` came from local working-tree mtime — i.e. my local clone hadn't pulled the CI-committed file since 2026-04-15.
- **Follow-up:** update `tools/` staleness checks to compare `git log -1 --format=%ct -- path` instead of `os.stat(path).st_mtime`, so false positives don't recur.

### 4. Live Autonomous Scanner `NameError: 'commodity'`
- Logs for run `24490037788` have aged out (>4 days) and the error no longer reproduces against the current `alpha_engine/forward_validator.py`. Likely fixed incidentally in the 2-week churn.
- **Follow-up:** monitor next `alpha-engine-live` failure; re-open if it recurs.

### 5. Dead `forward_win_rate` readers — scope correction
- The original claim (3 files silently returning 0) was based on `forward_win_rate` being 0/3500 populated on `audit_dashboard/data/dashboard_data.json`.
- Verification this cycle: the 3 flagged files (`battleground_quality_filter.py:429`, `bundle_baby_system.py:537`, `discord_bundle_baby.py:152`) read from **different** payloads:
  - `battleground/data/baby_strats_dashboard.json`
  - bundle `stats` dict (internal)
  - bundle payload (internal)
- Whether each of those payloads populates `forward_win_rate` correctly is a per-payload question and was NOT verified in the original flag. No fix applied — re-audit each source before assuming silent-zero.

## Still pending

### 6. `is_blocked_pick` ingress migration
Only `alpha_engine/feed_hygiene.py:132` calls `is_blocked_pick()`. Any emitter/scanner/validator that bypasses `feed_hygiene.is_valid_active_pick` will miss the composite `(source_system, strategy)` block. Candidates to migrate: `forward_validator.py` ingestion, `stamp_pick_quality.py`, per-scanner writers. Medium-effort refactor; not bundled here.
