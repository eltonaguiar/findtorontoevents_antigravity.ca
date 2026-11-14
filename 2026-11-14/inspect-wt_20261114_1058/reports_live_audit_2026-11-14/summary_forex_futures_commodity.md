# FOREX / FUTURES / COMMODITY — summary (live data, 2026-11-14 ~15:45Z)

Sources: `live_dashboard_payload.json` (.picks.active_raw FOREX n=277, FUTURES n=13, COMMODITY n=44; .picks.recent_closed FOREX n=187), `live_money_ready.json`, `live_pf_registry.json`, `live_stock_prices.json`, `live_audit_surface_truth.json`.

**VERDICT: FAIL — FOREX signals exist but the class is NOT_READY on its own verdict; FUTURES is near-dead but displayed; COMMODITY is thin; USDCAD=X/NZDUSD=X flat rows are mostly zombie artifacts, not real flat trades.**

## Evidence

1. **The one FUTURES active pick (`.picks.active`):** age 2.8h. In active_raw FUTURES n=13 with median age 2,343.9h (98 days) — the single "fresh" pick sits on a pile of month-old zombie rows. Whether its price fields update: `n_open_no_current_price` counts are in `evidence_live_audit.json` (active_raw_by_class.FUTURES).
2. **User's flat FX observation:** USDCAD=X / NZDUSD=X rows in active_raw include EXPIRED pnl=0.0 current_price=None zombies (same inverse_mutations/signal_validation pattern as crypto). Flat 0% displays are overwhelmingly **stale artifacts, not genuine flat marks**.
3. **Official FOREX surfaces disagree:** money_ready intrabar (n=612): WR 32.2%, PF 0.6596, pf_ok=False, dsr_ok=False. Registry canonical (n=456): WR 36.6%, PF 1.2136. My recomputed last-14d closed (n=43): WR 51.2%, PF 1.483, Σ +5.2%. Registry vs money_ready differ by ~2x in opposite directions from the 14d window — no surface is stable.
4. **Kill-switch status:** FOREX was hard-BLOCKED per PR #6 (PF 0.29/WR 46%). Live evidence shows FOREX picks are STILL being emitted (277 raw active rows; newest 1.5h). The block is a display/verdict posture, not an emission stop — **the class is picking money even while its verdict says NOT_READY.**
5. **FUTURES stats:** money_ready (n=52): WR 42.3%, PF 1.0936, pf_ok=False. Registry (n=36): PF 0.9176. surface_truth: INSUFFICIENT_DATA. Effectively dead-but-displayed.
6. **COMMODITY:** active_raw n=44 (median 3.3h, oldest 4,056h). recent_closed n=7, newest 25.3h. money_ready (n=229): WR 40.2%, PF 1.0256, pf_ok=False. Registry (n=69): PF 1.073 but **single-source 91.3%** — one source drives the whole class. My 14d (n=7): PF 0.604. surface_truth verdict: WATCH with policy_clean_pf 0.17 (n=14).
7. **Spot-flicker artifact scale (registry counts, all classes):** 34,540 raw → 3,872 dropped as spot-flicker (|pnl|<0.02bps), 129 duplicate re-emissions, 1,777 policy-excluded, 5,821 not-closed. 11% of everything "closed" was a zero-delta artifact.

## What is real
- Fresh FOREX/COMMODITY/FUTURES emissions arrive hourly (newest 1.5–2.8h).
- Realized 14d FOREX (+5.2% on n=43) is the only positive recent window, but n=43 and the class's own long-horizon PF (0.66 money_ready) say do not trust it.
