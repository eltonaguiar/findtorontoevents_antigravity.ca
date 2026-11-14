# OVERALL / Platform Quick Wins
Source: `../../scratch-hippodraco.MD` §3, §5.4, §6–§8. Ordered by impact/effort. Effort: S <4h · M 4–16h · L 2–5d. All file:line verified in this worktree during the audit.

## QW-ALL-1 · Freshness badge — kill the stale-green lie (S, 3h)
- **Problem:** Resolver/outcome/intrabar lanes stalled ~7.5h (last 08:21–08:50Z, dashboard built 14:30Z) while payload claimed `stale_warning:false`. `_compute_data_freshness()` (`audit_trail/dashboard_generator.py:3187-3227`) only checks active-picks mtime; the real guardian (`tools/db_freshness_check.py:445`) writes `db_freshness.json` that no frontend reads.
- **Fix:** Merge guardian lane minutes/status into `data_freshness.lanes{}` in the generator; `stale_warning = any(lane≠GREEN) or age>2h`; render a green/amber/red pill by the generated-at stamp in `audit_dashboard/template.html`. Missing guardian file → `FRESHNESS UNKNOWN`, never silent green.
- **Verify:** Fixture guardian JSON at 450 min → payload `stale_warning:true`; badge renders; `tests/test_audit_dashboard_payload.py` still passes.

## QW-ALL-2 · PnL unit contract + guarded backfill (M, 12h) — highest correctness impact
- **Problem:** `at_signal_outcomes.pnl_pct` mixes percent (17,632) and fraction (6,306); `trading_picks` same (3,543). Generator "heals" with `if abs(pnl)<0.10: pnl*=100` (`dashboard_generator.py:8065-8072`) — converts a genuine +0.08% into +8%. Corroborated independently by flaxen-hair in JSON files (`vix_reversal::SI=F` −0.04244 vs −3.6402).
- **Fix:** (1) Contract: `pnl_pct` = percent only, written only via resolver `_compute_pnl()` (`audit_trail/universal_pick_resolver.py:286-306`); add `pnl_source` (`intrabar|daily|close_approx|legacy_unknown`) at the outcomes upsert (`:1039-1046`). (2) Delete the ×100 guess; ambiguous → `pnl_pct=NULL, pnl_unit_ambiguous:true`. (3) Backfill **dry-run first**, snapshot tables, then per-class guarded UPDATE recomputing from entry/exit only where the fraction-guard matches (`ABS(pnl*100 − recomputed) < 0.15`); non-matching rows stay for manual review. **Never** adopt a bare `|v|≤1 → ×100` normaliser (peer variant) — FOREX/BOND genuine small percents would corrupt.
- **Verify:** Dry-run mismatch count → ~0; QQQ/AAPL audit samples match recomputation; `grep` shows no unit guess in generator.

## QW-ALL-3 · One clamp at write + flag fallback prices (M, 8h)
- **Problem:** ≥5 different clamps (ingest `pnl_ingest_sanity.py:12-14` crypto [−99,+500]; resolver ±100 `universal_pick_resolver.py:1107,1472`; frontend >100 vs >500). COMMODITY `MAX|pnl|=999,999.9999` reached stats. Hardcoded XAG $33.50 / XAU $3050 (`dashboard_generator.py:1453-1464`) fabricate PnL silently.
- **Fix:** `clamp_pnl_pct_for_pick()` (`pnl_ingest_sanity.py:36-45`) becomes the only clamp; resolver **rejects** (quarantine counter) out-of-bound PnL at write; one shared JS cap mirroring it; hardcoded-price picks stamped `price_source:"hardcoded_fallback"` and excluded from headline PnL (count disclosed).
- **Verify:** Fixture 999999% pick quarantined, not displayed; exactly one clamp per language by grep.

## QW-ALL-4 · Zombie OPEN drain (M, 10h)
- **Problem:** 90,567 OPEN + 21 ACTIVE in `trading_picks`; 86,064 >7d; ~5–7 resolved/day vs 14–19k new/month. `MAX_HOLD_HOURS_BY_CLASS` exists (`universal_pick_resolver.py:32,39`) but doesn't drain; dashboard auto-expire (`dashboard_generator.py:9540-9612`) only relabels payload rows.
- **Fix:** One-off batched drain script in `tools/`: expire OPEN older than class max-hold ×4 (first pass), `status=EXPIRED, exit_reason=ZOMBIE_DRAIN_2026_11, pnl_pct=NULL` (**NULL, not 0** — peer snippet writing `pnl_pct=0` would fabricate 90k flat trades), 1,000-row batches, dry-run count printed first. Then daily policy + alert when new OPEN/day > resolved/day for 2 days.
- **Verify:** Before/after `GROUP BY status` counts equal dry-run; closed-ledger WR/PF unchanged (stats-neutral proof).

## QW-ALL-5 · One active count; quarantine `active_raw` (M, 8h)
- **Problem:** `picks.active=20` vs `performance` active sum 158 vs `active_raw=4,148` (3,377 EXPIRED, median 2,055h, 86% price=0; snapshot at `dashboard_generator.py:9529-9538`).
- **Fix:** All surfaces derive per-class active by grouping the canonical final list (`final_active_picks`, ~`:16809-16953`); `active_raw` dropped or renamed `active_raw_open_only` with `_diagnostic:true` and only OPEN/ACTIVE/PENDING/LIVE statuses (`_OPEN_ACTIVE_STATUSES :868-873`); build-time assert `sum(by_class.active)==len(picks.active)` else stamp `integrity_warning`.
- **Verify:** Contract test QW-ALL-8(b/c); no EXPIRED in any active array.

## QW-ALL-6 · Artifact max-age stamps (S–M, 6h)
- **Problem:** Walkforward frozen 2026-04-15 (212d, passed through `dashboard_generator.py:15900-15913`); Claude Gainer ML `status:active` on 2026-05-25 model (`:16730-16786`); regime WRs published at 0.1% coverage (21/16,126).
- **Fix:** Per-artifact `age_hours` + budget (walkforward 48h, ml_health 7d, regime 24h) → `stale:true` stamp; frontend `STALE (212d)` chip; suppress regime WRs when coverage <5% ("insufficient regime data, n=21"); models over budget downgrade `active→stale`.
- **Verify:** Fixture dated 2026-04-15 → `stale:true, age_hours≈5088`; regime block shows suppression text.

## QW-ALL-7 · Frontend stops recomputing PnL (M, 8h)
- **Problem:** `template.html` recomputes PnL in ≥4 places (`:4325-4329,4459-4467,4727-4731,4821-4826`) with inconsistent caps; generator leaves pick untouched on price-fetch failure (`dashboard_generator.py:1752-1755`) so 13/20 picks show fake 0.0% (current==entry).
- **Fix:** Server emits `unrealized_pnl_pct + price_source + price_age_s` (null on fetch failure, never entry-clone); template deletes recompute blocks, reads server fields via `_unrealizedPnlPct()` (`:5446,6497`); null renders `—`.
- **Verify:** Grep template for `(livePrice - entry)` = 0; same pick identical PnL in two panels.

## QW-ALL-8 · CI contract tests + guardian MAX-by-id (M, 10h)
- **Problem:** Payload tests are shape-only (`tests/test_audit_dashboard_payload.py:50,69,93`) — every P0 shipped green. Guardian backtests lane RED is a timeout on `MAX(),COUNT(*)` over 34.6M rows (`tools/db_freshness_check.py:427`), training everyone to ignore RED.
- **Fix:** New `tests/test_payload_contracts.py` (fixtures, no DB): (a) recomputed-vs-stored PnL ≤0.15pp, (b) active-count equality, (c) no EXPIRED in active, (d) artifact age/stale stamps, (e) per-class |pnl| bounds. Add a fast pytest job (audit workflow currently has none). Guardian: `ORDER BY id DESC LIMIT 1` probe + information_schema count estimate.
- **Verify:** Tests fail on today's fixture for (a)(b)(c), pass post-fix; guardian backtests lane completes without timeout.

## QW-ALL-9 · Status vocabulary + honest summary naming (M, 12h)
- **Problem:** Dashboard WON/LOST/FLAT/CLOSED vs DB TP_HIT/SL_HIT/LOST/EXPIRED/TIME_EXIT vs resolver CLOSED; `alpha_engine/audit_sync.py:595` accepts only WON/LOST/EXPIRED — TP_HIT/SL_HIT silently dropped. `summary.total_pnl_pct` is actually rolling-100 compound (`dashboard_generator.py:16874-16886`) beside −923.53 raw-sum and −99.0 EW-compound.
- **Fix:** Single `status_vocab` mapping module applied at ingest + sync (log every unmapped status); rename headline to `total_pnl_pct_rolling100_compound`, keep `total_pnl_pct` as deprecated alias one release with `_deprecations` note.
- **Verify:** Sync logs 0 silent skips; every DB status round-trips to exactly one dashboard status.

## QW-ALL-10 · `summary_picks.json` WR>100% (adopted from finpredict-v2/v1, IMPLEMENTED by peer)
- **Problem:** `tools/sync_summary_picks_json.py:63-65` counted wins/losses over all rows while `resolved` counted only terminal statuses → published WR INDEX 1141%, FUTURES 364% (7 classes impossible). Same family as our count-reconciliation failures but a distinct surface we missed.
- **Status:** finpredict implemented the fix on branch `fix/audit-p0-truth` (`updates/2026-11-14-p0-truth-fixes.md`): wins/losses as strict subset of resolved + `min(wins,resolved)` clamp. Adopt pattern; verify `summary_picks.json` shows no `win_rate_pct > 100` post-merge. Also from the same peer commit: FX `KeyError:'LONG'` direction-bucket crash (`alpha_engine/scanner.py`) and `None→0.0` entry coercion removal (`prediction_market_consensus.py`) — the latter directly supports QW-ALL-3/QW-ALL-7.

## QW-ALL-11 · Frontend dead-JS guard (adopted from peer branch)
- `audit_dashboard/dashboard_enhancements.js` carried a malformed nested ternary since 2026-10-04; every hourly deploy pushed unparseable JS to all 3 sites (part of "empty fields" was frontend, not backend). Peer branch `fix/audit-js-syntax-and-deploy-guard` (`ba1378cbfa9`) adds a pre-FTP `node --check` withholding only broken JS. Confirm it merges; add JS syntax check to QW-ALL-8 contract tests.

## Also (from peers, adopted)
- **Unique pick IDs:** date-only IDs duplicate (`vix_reversal::SI=F::2026-03-11` ×4) — add time+seq/uuid suffix at emission (`multi_asset/scanner.py _pick_id`); CI validator. (flaxen-hair)
- **`ml_score == confidence` copy:** decouple globally; where a model is absent emit `ml_score:null`, not the confidence value. (flaxen-hair/childlike-airport)
- **Credential hygiene (generic):** rotate any credential ever shared in chat/files; inject per-service via env, not shared plaintext. (all peers agree; no values reproduced anywhere)
