# CRYPTO Pipeline — Quick Wins (findtorontoevents.ca/audit)

Scope: CRYPTO surface of `/audit`. All numbers read live from `.inspect-wt/_audit_tmp/live_*.json` (snapshot 2026-11-14 10:51 UTC) and code anchors grep-verified in read-only worktree `.inspect-wt/` @ `f54efb3b4a`.

**Baseline live stats (verified this session):**
- `picks.active_raw` CRYPTO n=3,577 — statuses EXPIRED 3,100 / OPEN 402 / SL_HIT 50 / TP_HIT 25 (JSON: `.picks.active_raw[] | asset_class=="CRYPTO"`)
- Zombies (status EXPIRED + pnl 0): **2,995 of 3,577 = 83.7%** of the CRYPTO active_raw pool; oldest 6,420h (~267 days) (`evidence_live_audit.json → active_raw_zombies_expired_pnl0 = 3272` all-classes; CRYPTO subset computed from payload)
- `source=inverse_mutations`: **2,266 rows** (2,230 EXPIRED), strategy `inverse_luxalgo_confluence` = 2,261 of them; ids like `inverse_luxalgo_confluence::ARBUSDT::2026-11-13` persist back to 2026-05 (payload `.picks.active_raw[].id/.timestamp`)
- Zero-entry-price rows (entry_price ≤ 0 or missing): **85 EXPIRED + 62 OPEN** today; OPEN ones timestamped 2026-11-14 (same build day) — sources: mape_evolver, genetic_programmer, ensemble_evolver, prediction_market_consensus. Includes BTCUSDT/ETHUSDT/SOLUSDT/AVAXUSDT entry 0.0
- Gate-filtered `picks.active` CRYPTO = **3 rows** (OPEN) — the public "active" surface is clean; the pollution is concentrated in the Show-All / active_raw diagnostic pool and in aggregate counters
- Surface disagreement (established): pf_registry CRYPTO PF 0.2324 n=23,636 single_source_pct 0.979184 (`live_pf_registry.json → by_asset_class[] asset_class=CRYPTO`) vs money_ready intrabar PF 0.9196 n=3,705 (`live_money_ready.json → classes.CRYPTO.intrabar_truth`) vs 14d recompute PF 0.805 n=471 WR 38.2% (`evidence_live_audit.json → recent14d_closed_stats.CRYPTO`)
- Anti-overfit: 69/80 OVERFIT_LIKELY (`live_anti_overfit_audit.json → verdict_counts`)

Legend: **PASS** = exact anchor text grep-verified at f54efb3b4a (file:line cited) → patch or precise edit possible. **FAIL** = spec-only, no verified anchor.

---

## QW1 — Split EXPIRED+pnl-0 zombie rows out of `picks.active_raw` — **PASS**

- **(a) Anchor:** `audit_trail/dashboard_generator.py:17181` — exact text `payload["picks"]["active_raw"] = sorted(` (verified). Context: the full-pool assignment right after the gate filter (lines 17159–17185, comment block documents active_raw as "Show All Picks" full pool).
- **(b) Minimal change:** before sorting, partition `_active_raw_snapshot`:
  `zombies = [p for p in _active_raw_snapshot if p.get("status") == "EXPIRED" and not _float(p.get("pnl_pct", 0) or 0)]` → assign `payload["picks"]["active_raw"] = sorted(non-zombies)`, `payload["picks"]["active_raw_expired"] = zombies` (new diagnostic key), and `payload["summary"]["active_raw_zombie_count"] = len(zombies)`.
- **(c) Expected effect:** active_raw CRYPTO 3,577 → **582** (−2,995 zombie rows, −83.7%); total_active_raw_picks 4,148 → ~1,153. "Show All Picks" becomes a real candidate pool; per-class counts and UEPS sidecar (`_build_ueps_kpi_sidecar` at line 17975 consumes active_raw) stop being fed 84% dead weight.
- **(d) Risk/rollback:** Low — display/diagnostic layer only; closed-pick stats already exclude these rows (`expired_no_pnl` at line 9419). One-block revert. Rollback: restore the original `sorted(list(_active_raw_snapshot), …)` assignment.

## QW2 — Stop emitting entry_price=0 rows from the prediction-market consensus emitter — **PASS**

- **(a) Anchor:** `alpha_engine/prediction_market_consensus.py:588` — exact text `merged_pick["entry_price"] = merged_pick.get("entry_price") or 0` (verified, inside the merge loop lines 575–600 that appends into `active_picks.json`). Upstream cause also verified: `_extract_trade_levels` (lines 139–161) returns `(0.0, 0.0, 0.0)` when `_fetch_price` (line 157) fails, and line 489 already writes `"entry_price": entry_price or None` with `status = "SIGNAL"` (line 478) — but line 588 re-coerces None → 0 and merges it anyway.
- **(b) Minimal change:** in the merge loop, `if _float(merged_pick.get("entry_price")) <= 0: skipped += 1; continue` before appending. Patch written: `crypto_quick_wins.patch` (diff 1). Consensus picks with no price stay in `consensus_picks` output for the signals view; the dashboard already has a repricing path for signal-only PM rows (`_snapshot_prediction_market_entry`, `dashboard_generator.py:5361`, verified) so they can reprice next build instead of living as 0-entry zombies.
- **(c) Expected effect:** 0 new zero-entry PMC rows per build. Today's live contribution is small (3 rows) but recurring daily; also removes the `"status": "SIGNAL"` rows that other loaders treat as OPEN-with-0-PnL.
- **(d) Risk/rollback:** Low. Fewer unpriceable picks shown (they carry no tradeable entry anyway). Rollback: revert one hunk.

## QW3 — Loader-side guard: demote all unpriceable picks out of active pools (all sources) — **PASS**

- **(a) Anchor:** `audit_trail/dashboard_generator.py:14269` — exact text `active = _enrich_live_pnl(active)` (verified). `_enrich_live_pnl` already skips zero-entry rows for PnL math (lines 1709–1712: `if not entry or entry == 0: … continue`) but leaves them in the pool.
- **(b) Minimal change:** immediately after line 14269, partition: `[p for p in active if _float(p.get("entry_price", 0) or 0) > 0 or p.get("asset_class","").upper() != "CRYPTO"]` for CRYPTO (non-crypto entry conventions differ — e.g. PM rows) into active; move the demoted ones to `active_raw_expired`/unpriced bucket with `_unpriced=True` tag and a summary counter.
- **(c) Expected effect:** kills the recurring 62 OPEN zero-entry rows per build (mape_evolver 28, genetic_programmer 21, ensemble_evolver 10, neat_neural_evolver 8, PMC 3 — live counts this build); BTCUSDT/ETHUSDT 0.0-entry rows vanish from every active surface.
- **(d) Risk/rollback:** Low — one-line filter + counter; does not touch closed stats. Rollback: remove the partition. Note: production may have diverged from f54efb3b4a (~5 months old); re-grep anchors before merge.

## QW4 — Cap `inverse_mutations` re-emissions (id-level dedupe + merge-time TTL) — **PASS**

- **(a) Anchors (all verified):**
  - `alpha_engine/production_scanner.py:4317–4331` — merge of `inverse_picks.json` into the active pool dedupes on `(symbol, direction or signal_type)` only (`existing_keys = { (p.get("symbol"), p.get("direction") or p.get("signal_type")) for p in active }`). Since emitted ids are **dated** (`inverse_luxalgo_confluence::ARBUSDT::2026-11-13`), this key cannot prevent accumulation across days; rows persist for months (live timestamps back to 2026-05).
  - `alpha_engine/inverse_loser_mutations.py:283` — `def run_inverse_mutations():` ; line 384 `inverse_picks.append(inv_pick)` (3 mutations per active loser pick; live data shows the standard mutation dominating).
  - `audit_trail/dashboard_generator.py:3999` — source registry line `("inverse_mutations", "alpha_engine/data/inverse_picks.json", None),` and `:4290` `_FRESHNESS_REQUIRED_HOURS = {` (inverse_mutations is NOT in the freshness-gated set).
- **(b) Minimal change (2-line class of fix):**
  1. In the merge at production_scanner.py:4317–4331, dedupe on the full emitted `id` (or `strategy::symbol`) and skip emitted picks whose `timestamp` is older than 24h before merging.
  2. Add `"inverse_mutations": 24` to `_FRESHNESS_REQUIRED_HOURS` (dashboard_generator.py:4290 block) so a stale inverse_picks.json is skipped at load, mirroring the breakout_a_sr-style entries at 4307+.
- **(c) Expected effect:** inverse_mutations = 2,266 of 3,577 active_raw CRYPTO rows (65%); 2,262 of the 3,272 all-class zombies (`evidence_live_audit.json → active_raw_zombies_by_system.inverse_mutations`). Bounding emissions to a 24h TTL caps this at ~dozens of rows instead of ~2,266.
- **(d) Risk/rollback:** Low-Medium. Inverse picks are a real (if unproven) strategy family — 26 OPEN inverse rows today would age out normally; the TTL only removes stale re-emissions. Keep 3-mutation generation unchanged. Rollback: delete the TTL check and restore the (symbol, direction) key.

## QW5 — One-time zombie purge script for `alpha_engine/data/inverse_picks.json` — **PASS (script spec; trivially anchored)**

- **(a) Anchor:** `alpha_engine/inverse_loser_mutations.py:384–387` — the file is written by plain overwrite (`INVERSE_PICKS_PATH` dump, lines ~405–408, verified in function body); consumers: dashboard_generator.py:3999 and `alpha_engine/feed_health_monitor.py:26` (`"inverse_mutations": "alpha_engine/data/inverse_picks.json"`).
- **(b) Minimal change:** new `tools/purge_crypto_zombies.py` (one-time, GHA `workflow_dispatch`): load inverse_picks.json, keep rows with `timestamp ≥ now-24h`, archive the rest to `alpha_engine/data/inverse_picks.json.purged_<ts>.bak` (atomic rename), rewrite the file. Also prunes `active_picks.json` inverse rows older than ACTIVE_PICKS_MAX_AGE_SECS (default 86400 — env knob already exists at production_scanner.py:6515 comment block, verified).
- **(c) Expected effect:** next dashboard build drops ~2,230 inverse-mutation EXPIRED rows in one shot; combined with QW1, active_raw CRYPTO ≈ 500–600 rows, all live.
- **(d) Risk/rollback:** Low — .bak archive kept; idempotent. Never touches closed_picks.json or MySQL. Rollback: restore from .bak.

## QW6 — Template: show "awaiting price" instead of 0.00% for unpriced pick rows — **PASS**

- **(a) Anchors (verified):**
  - `audit_dashboard/template.html:13017` — smart-picks table cell: `((p.pnl_pct || 0) > 0 ? '+' : '') + (p.pnl_pct || 0).toFixed(2) + '%'` renders `0.00%` when pnl is null/unpriced (same coercion pattern at line 3249).
  - Live-repricing path already refuses entry=0 (`template.html:4166` `if (!entry || !livePrice) continue;`), so unpriced rows keep the server-side `pnl_pct=0` — which is exactly what renders as fake "0.00%".
- **(b) Minimal change:** at 13017 (and 3249): `p.pnl_pct == null || !(p.entry || p.entry_price)` → render `'<td …>awaiting price</td>'` else current expression. Patch written: `crypto_quick_wins.patch` (diff 2).
- **(c) Expected effect:** today 327 of 402 OPEN CRYPTO active_raw rows show pnl=0 (no current_price for 329 of them — `evidence_live_audit.json → active_raw_by_class.CRYPTO.n_open_no_current_price = 329`); these stop reading as "flat/breakeven trades", which currently understates loss exposure (the 2026-05 audit's "81% show fake 0% P/L" finding).
- **(d) Risk/rollback:** Cosmetic only; no data changes. Rollback: revert 2 template lines. Check `audit_dashboard/check_template_sync.py` still passes.

## QW7 — Add `active_raw_zombie_count` + `oldest_zombie_age_h` to `data_freshness` — **PASS**

- **(a) Anchor:** `audit_trail/dashboard_generator.py:3135` — `def _compute_data_freshness(active_picks_path: Path) -> dict:` (verified), payload write at `:16733` `"data_freshness": _compute_data_freshness(` (verified). Live payload confirms the shape: `.data_freshness = {last_dashboard_build, last_alpha_scan, stale_warning, age_hours}`.
- **(b) Minimal change:** inside `_compute_data_freshness` (or at the write site where active_raw is in scope), add: `freshness["active_raw_zombie_count"]`, `freshness["active_raw_zombie_share"]`, `freshness["oldest_active_raw_age_h"]` computed from the same rows as QW1. Wire the zombie count into `tools/db_freshness_check.py` check chain as a RED threshold when zombie_count > 500 or share > 30% (that file's per-check dict pattern is verified at `tools/db_freshness_check.py:168–202`).
- **(c) Expected effect:** the 2026-11-14 values would read zombie_count(CRYPTO)≈2,995, share 83.7%, oldest 6,420h — turning zombie accumulation into a CI-visible regression metric instead of something found in manual audits.
- **(d) Risk/rollback:** None (additive payload fields). Rollback: remove the 3 keys.

## QW8 — Add `inverse_mutations` to the CRYPTO per-source volume cap — **PASS**

- **(a) Anchor:** `alpha_engine/per_source_volume_cap.py:34` — `PER_SOURCE_VOLUME_CAP: dict[str, dict[str, float]] = {` (verified), with existing CRYPTO share entries (e.g. `"quan_engine": {"CRYPTO": 0.05}` line 35) and precedents for sub-floor PF sources (lines 39–43). Enforced on the scanner emit path at production_scanner.py:6460–6475 (`enforce_cap` call, verified).
- **(b) Minimal change:** add `"inverse_mutations": {"CRYPTO": 0.02},` to the dict. Justification: inverse strategy family has no demonstrated live edge (live inverse_mutations resolved rows: 2,230 EXPIRED / 7 SL_HIT / 3 TP_HIT — ~0% realized win rate on today's snapshot; backtest claims remain unvalidated forward).
- **(c) Expected effect:** bounds inverse share of emitted CRYPTO actives to 2% regardless of how many loser strategies qualify; complements QW4 (which fixes persistence, this caps volume).
- **(d) Risk/rollback:** Low — pure filter on over-represented source cohort, same mechanism as 2026-05-15/16 fixes. Rollback: remove the dict entry.

---

## Explicitly checked, NOT recommended as quick wins

- **Deleting `signal_validation` zombies (409 rows, source of the `MeanReversionBB`/`MomentumEMA` rows):** same pattern as QW1/QW4 but the emitter path wasn't locatable in this snapshot's code — the live `signal_validation` rows (314 active) predate/grew past the f54efb3b4a code. Covered automatically by QW1's status-based filter and QW3's unpriced guard; a dedicated emitter fix is **UNVERIFIED** at this commit.
- **pf_registry CRYPTO row itself (PF 0.2324 n=23,636):** the 97.9% single-source concentration (`top_source: file:mysql:at_pick_outcomes`) is a deeper aggregation problem — handled in `proposed_fix.md`, not a one-day edit.

## Sequencing (one engineer, ~1 day each)

1. QW1 + QW7 (same file, same day — filter + metric together)
2. QW2 + QW3 (unpriceable guard: emitter then loader)
3. QW4 + QW5 + QW8 (inverse-mutations triad)
4. QW6 (template, independent)

All patches/specs assume f54efb3b4a anchors; re-grep before merging (worktree is ~5 months behind origin/main).
