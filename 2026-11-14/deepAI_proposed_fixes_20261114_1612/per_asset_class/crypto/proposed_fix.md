# PROPOSED FIX (deeper) — CRYPTO single-source concentration breaker + zombie re-emission guard

Class: CRYPTO · Repo: `.inspect-wt` @ `f54efb3b4a` (read-only; ~5 months behind origin/main — anchors re-grep before merge)

## Problem (verified numbers, this snapshot)

1. **The CRYPTO class statistic is one feed wearing a class costume.** pf_registry CRYPTO: PF **0.2324**, n=**23,636**, `single_source_pct` **0.979184**, `top_source: file:mysql:at_pick_outcomes`, `is_single_source_artifact: true` (`live_pf_registry.json → by_asset_class[] asset_class=CRYPTO`). 97.9% of all resolved CRYPTO rows come from a single outcome table, and that table is polluted by the same zombie/auto-expired rows documented in `quick_wins.md` (2,995 CRYPTO zombies in active_raw alone).
2. **The gate that would catch this is built but switched off.** `alpha_engine/money_ready_verdict.py:1036 _single_source_gate()` implements exactly the needed check ("Reject class edge that rests entirely on single-source sleeves (#65)") and its enforcement flag is env-gated OFF: `_SINGLE_SOURCE_GATE_ENFORCE` at lines 194–197 reads `MONEY_READY_SINGLE_SOURCE_GATE` (default "0"). Live money_ready confirms: `"single_source_ok": true` with **31 of 33 profitable CRYPTO sleeves single-source** (`live_money_ready.json → classes.CRYPTO: n_profitable_multi_source=2, n_profitable_single_source=31, _single_source_gate_enforce=false`). I.e. even the 0.9196 "honest" PF rests ~94% on single-source sleeves.
3. **The registry also counts the zombie flow.** The registry is built by `tools/build_pf_registry.py`, whose input list is `dashboard_generator.JSON_PICK_SOURCES` closed files (verified: `_resolve_source_files()` at lines 143–167 imports `JSON_PICK_SOURCES`). Auto-expired pnl-0 rows flow into the same closed files the auto-expiry pass appends to (`dashboard_generator.py:9408–9420`), so the n=23,636 / PF 0.2324 numerator and denominator both include months of never-priced zombie rows that no real trade ever resolved. The 14d recompute (PF 0.805 n=471) and the intrabar truth (PF 0.9196 n=3,705) disagree with the registry precisely because the registry's window is years of polluted accumulation while the honest windows are recent and resolution-clean.

## Fix spec — two coupled components

### Component A — Turn on and harden the single-source breaker (small, deterministic)

1. **Enable the existing gate.** Set `MONEY_READY_SINGLE_SOURCE_GATE=1` in the money-ready workflow env (integration point: `.github/workflows/audit-dashboard.yml:543–545` — the hourly money_ready snapshot step `python tools/money_ready_snapshot.py`). Effect: `classes.CRYPTO` verdict routes to `NOT_READY` (money_ready_verdict.py:1149–1152 returns "NOT_READY" when the gate fails), instead of today's `"single_source_ok": true` with 31/33 single-source sleeves.
2. **Tighten `_single_source_gate` granularity (money_ready_verdict.py:1036–1082).** Today it checks whether ≥1 profitable strategy is multi-source. Add a second output: `profitable_single_share` = `n_profitable_single_source / n_profitable`. Class-level rule: if share ≥ 0.75 → `ok=False` even when 1–2 multi-source sleeves exist (CRYPTO today: 31/33 = 0.94 → fail). This prevents the 2 lucky multi-source sleeves from laundering a 31-sleeve single-source book.
3. **Registry stamping (tools/build_pf_registry.py:107–128 `_compute_source_concentration`).** Already computes `is_single_source_artifact` (CRYPTO flagged true in live registry). Additive change: emit per-class `single_source_pct` into `by_asset_class` rows consumed by `alpha_engine/emitter_whitelist.py` (which loads `audit_dashboard/data/pf_registry.json`, verified at emitter_whitelist.py:21) so emitters can refuse to promote CRYPTO sleeves whose rows are ≥X% single-source.

### Component B — Zombie re-emission guard (the pipeline-side root cause)

The single-source 97.9% is sustained by an append-only zombie flow: auto-expired pnl-0 rows are re-listed into the active_raw pool every build (QW1) and the largest producer, `inverse_mutations`, re-merges dated-ID picks on a lossy `(symbol, direction)` key (`alpha_engine/production_scanner.py:4317–4331`). Spec:

1. **Stable-ID dedupe at merge.** Replace the `(symbol, direction)` key at production_scanner.py:4317–4331 with the emitted pick `id` (format `inverse_luxalgo_confluence::ARBUSDT::2026-11-13`, verified in live payload). Ids are already date-stamped, so id-level dedupe + a `timestamp ≥ now-24h` pre-merge filter bounds re-emission to one row per symbol per day.
2. **TTL write-back.** When writing `active_picks.json` (production_scanner.py:5044–5057, the "ML PERSIST" overwrite — verified) and step 6n's age-prune (line ~6515, `ACTIVE_PICKS_MAX_AGE_SECS` default 86400 — verified), apply the same 24h TTL to `inverse_*` rows explicitly rather than relying on the global prune (which today coexists with rows dated 2026-05 in live active_picks derivatives — evidence the prune path doesn't run on every writer).
3. **Closed-side tag.** In `dashboard_generator.py` auto-expiry (lines 9408–9420, `p["status"] = "EXPIRED"` + `expired_no_pnl` — verified), also set `p["_zombie_purge_reason"] = "auto_expired_no_price"` so `tools/build_pf_registry.py` can exclude tagged rows from registry `n` (one filter in its per-source row loop; the registry's policy-exclusion machinery already exists — `policy_excluded_count` key verified in `live_pf_registry.json` top-level keys).

### Integration points (all verified in code)

| Point | File:line | Change |
|---|---|---|
| Env flag | `.github/workflows/audit-dashboard.yml:543–545` | `MONEY_READY_SINGLE_SOURCE_GATE=1` on the snapshot step |
| Verdict gate | `alpha_engine/money_ready_verdict.py:1149–1152` | already returns NOT_READY — no code change needed for step 1 |
| Gate hardening | `alpha_engine/money_ready_verdict.py:1036–1082` | add `profitable_single_share` + ≥0.75 rule |
| Registry stamping | `tools/build_pf_registry.py:107–128` | propagate `single_source_pct` per class row |
| Emitter consumption | `alpha_engine/emitter_whitelist.py:21,100` | read new field, refuse single-source-artifact sleeves |
| Re-emission dedupe | `alpha_engine/production_scanner.py:4317–4331` | id-key dedupe + 24h TTL pre-filter |
| TTL write-back | `alpha_engine/production_scanner.py:5044–5057`, `~6515` | explicit inverse-row TTL |
| Registry exclusion | `tools/build_pf_registry.py` row loop | drop `_zombie_purge_reason` rows from n |

## Expected effect on live stats

- `money_ready.classes.CRYPTO` → NOT_READY (correct: 31/33 profitable sleeves single-source, class PF<1 on the honest daily basis).
- pf_registry CRYPTO n drops from 23,636 as tagged zombie rows are excluded (auto_expired_excluded count in the dashboard summary is already 8,888 all-class — the registry-side n reduction will be material; exact number UNVERIFIED until the tag exists).
- The three CRYPTO surfaces (registry / money_ready / 14d) converge toward each other once the registry's numerator stops mixing never-priced zombies with resolved trades; the residual gap becomes a true accounting-basis difference (intrabar vs close), not a pollution gap.
- Emission volume: inverse_mutations active share bounded to 2% (QW8) and ≤1 row/symbol/day (Component B).

## Risk & rollout

- **Rollout order:** B first (purge + TTL, 1 day, reversible with .bak), then A-1 env flag (single workflow env change, instantly revertible), then A-2/A-3 (code, shadow-mode first: emit `profitable_single_share` for 1 week before acting on the 0.75 threshold).
- **Fail-open preserved:** `_single_source_gate` returns `ok=None` (never blocks) on insufficient data — keep that semantics in the hardened version.
- **Biggest risk:** the money_ready NOT_READY downgrade makes the /audit money banner red for CRYPTO. That is the honest state given PF 0.23–0.92 vs the daily basis PF 0.2628 (`classes.CRYPTO.intrabar_daily_divergence.daily_pf`), and is reversible by unsetting the env var.
- **Divergence caveat:** anchors verified at f54efb3b4a; production code may differ (the live emitter that produced 2,261 `inverse_luxalgo_confluence` rows is not byte-identical to this snapshot's `run_inverse_mutations`, which emits 3 mutations/pick — UNVERIFIED upstream). Re-grep all 8 integration points before implementing.
