# PEER REVIEW — FOREX

**Reviewer:** finpredict-v3 peer-review subagent, 2026-11-14T16:17Z

## 1. Peer docs read
- v4 `forex_deep_dive.md` (PR#6 bypass; 2 frozen active; PF 0.48).
- v4 `dashboard_data_report.md` §2.2/2.3/2.4/4.3 §5 (FOREX NOT_READY; policy-clean n=438).
- v1 `2026-11-14-prediction-system-audit.md` §2/§6/§7 (118 OPEN, 93 frozen; 11 phantoms).
- v2 `E_statistical.md` §5 (n=438, z=-6.02) + §7.1 (summary WR 147% bug).
- ML-audit `proposed_fixes/forex/FIX_PROPOSED.md` (4 stale active; case dup; strategy_stats).
- Mine `2026-11-14-prediction-data-hygiene.md` (11 frozen phantoms; batch-identical closed_at).

## 2. Peer verdict per class
- v4 (deep dive): "FOREX is **functionally dead but artificially kept alive** by a cross-asset consensus engine that bypasses the stated PR#6 gate" — **0/2** active picks genuinely live; both have `current_price≈entry` showing -0.0% while live rates give +0.04–0.06%; aggregate **PF 0.48, WR 36.6%, total -27.78%**.
- v4 (dashboard): **NOT_READY** (intrabar n=612, WR 32.2%, PF 0.66, expectancy -0.105; policy frozen; recent closed DB raw 14d n=159, WR 6.9%, PF 0.087; policy-clean net **n=438, PF 0.834**).
- v1: FOREX is the most heavily frozen class — **118 OPEN, 93 (79%) frozen at 0%**; 11 frozen closed phantoms (EURUSD/USDCHF/… March 2026, exit==entry, pnl 0). Net PF 0.48.
- v2: **n=438, WR 35.62%, PF 0.8339, z=-6.02, p=1.7e-9** — significantly BELOW 50% (second-worst major class).
- ML: **4 active forex picks stale ~172d (2026-05-25)** with current_price=None, pnl=0.0, never resolved; 120 lowercase `forex` closed rows duplicated vs `FOREX`.

## 3. Peer-proposed quick wins (with source + dedup)
1. **Enforce PR#6/PR-D on cross-asset systems**: add asset-class gate so `non_crypto_consensus` respects the FOREX block (v4 deep dive rec #2) — UNIQUE, critical.
2. **Audit consensus inputs**: remove blocked `forex_rsi2_mean_reversion` from consensus; fix blocklist propagation (v4 deep dive rec #3).
3. Fix forex price fetching (`fetchForexPrices`/enricher); stop emitting FROZEN_CLOSED_PHANTOM rows + purge the 11 (v4 rec #1; mine §per-class).
4. Deduplicate over-emission (29 picks across 10 symbols; 4x USDCAD/AUDUSD) (v4 rec #5).
5. Kill or paper-trade only until a strategy shows PF>0.8 (v4 rec #4) — matches "policy frozen" gate.
6. Backfill asset_class case (FOREX/forex) + refresh/exit the 4 stale active picks via resolver (ML §3.1–3.4; mine).
7. Populate `strategy_stats` so gatekeeper doesn't score forex as unproven (ML §3.5).

## 4. Disagreements / contradictions
- **"All blocked" banner vs active emission**: v4 proves PR#6 is FALSE in practice (non_crypto_consensus bypasses both FX kill-switch and PR#6). No peer disagrees once code read.
- **Live counts**: v4 dashboard shows 2 active; ML DB shows 4 stale active — different layers, both frozen.
- **Magnitude**: v4 aggregate PF 0.48 / -27.78% vs v2 policy-clean PF 0.834 (n=438) — same net-losing sign, different severity (clean vs raw).

## 5. Gaps
- No peer provides a live quote source fix beyond "enricher"; placeholder prices persist.
- Closed-pick counts inconsistent: dashboard `picks.closed` returns 0 forex when filtered; aggregate says 82 closed.
- No forward ledger n>=100; `strategy_stats` empty blocks gatekeeper.

## 6. Recommended best-of (master plan)
Highest-priority class for a policy fix. Enforce PR#6 at emission, propagate blocklist into `non_crypto_consensus`, remove blocked inputs, fix price enricher, dedup, and keep the class **policy-frozen / paper-only** (v4 + v1 + v2 all agree it loses at high significance). Dat hygiene (backfill, resolve 4 stale) is P0 prerequisite.
