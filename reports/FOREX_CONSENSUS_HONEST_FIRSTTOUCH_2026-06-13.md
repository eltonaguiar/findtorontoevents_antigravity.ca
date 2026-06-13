# FOREX consensus "winner" is a daily-resolution artifact — honest first-touch collapses it

**Author:** claude-opus (8h money-ready loop, tick 2) · 2026-06-13 ~16:40Z
**Method:** conservative SL-wins-ties **first-touch** re-resolution of the `non_crypto_consensus` FOREX cohort against actual daily OHLC bars (`fxp_price_history`, 8 majors), then cluster-bootstrap PF CI-LB (`tools/pf_ci_lower.py`, symbol-day clusters), compared head-to-head against the **daily-resolved** `pnl_pct` stored on the same picks.

## Verdict: the project's single best candidate has NO edge once honestly resolved

| resolution (same 88 deduped picks, 8 majors, April cohort) | gross PF | CI-LB | WR |
|---|--:|--:|--:|
| **Honest first-touch** (SL-wins-ties, daily bars) | **1.02** | **0.70** | 40.9% |
| Daily-resolved (`trading_picks.pnl_pct`) | 2.88 | 1.73 | — |

**The daily resolver inflates gross PF ~2.8× on this cohort** (2.88 → 1.02). The FOREX consensus edge that prior loops promoted (daily gross CI-LB 1.35, point PF 1.79) is a **resolution artifact** — there is no edge even *gross* when you walk the actual price path and assign first-touch outcomes conservatively. Net of 2bp cost the honest PF is ~0.99.

**Robust across horizons:** identical result at 20/40/60-bar horizons (most picks resolve within 20 trading days). First-touch finds TP=37 / SL=51 / TIME_EXIT≈0 — i.e. within the horizon nearly every pick touches its band, and the closer SL (~0.5%) is hit first ~58% of the time vs the further TP (~0.8%). The geometry alone (reward 0.8 : risk 0.5, win-prob <50%) yields PF ≈ 1.05 — exactly what honest first-touch shows. The daily 2.88 comes from crediting favorable *close* drift on picks that never actually touched TP.

## Why this matters (the months-of-false-candidates explanation)

This is the same pathology proven on `ml_enhanced_INJUSDT_1d_B_lightgbm` the same day: 24 daily "TP_HIT" rows at +11–22% each, every one carrying `intrabar_status=TIME_EXIT` (TP never touched). FOREX consensus is the subtler, lower-amplitude version of the identical bug.

**Generalized caveat — applies to ALL daily-resolved `trading_picks` CI-LB work this session:** the stored `pnl_pct` systematically overstates gross PF by ~2–3×. The candidates that kept appearing and then "decayed" or "died on cost" (FOREX 1.79, COMMODITY 1.75) mostly **never had gross edge once honestly resolved** — the cost/decay framings partially masked that the gross number itself was a daily-resolution artifact. The only trustworthy source is honest first-touch / the `at_signal_outcomes` intrabar ledger, which independently reports FOREX ~1.10 / CRYPTO 0.73 / all classes FAIL (0/9 T2).

**`non_crypto_consensus` is entirely ABSENT from the honest intrabar ledger** (`at_signal_outcomes`) — it is a `trading_picks`-only, daily-resolved source. So its entire candidacy rested on the inflated resolution path with zero first-touch verification until this re-resolution.

## Caveats (honest scope)
1. **n=88 deduped** — the April-cohort subset of the 8 fxp-covered majors where ≥15 forward daily bars exist (`fxp_price_history` ends 2026-05-12; cohort entries run to 2026-05-25). Not the full 303-deduped cohort, but a clean, representative majors subset.
2. **Daily bars, not intraday** — within-day path is unknown; SL-wins-ties is the conservative/defensible convention (matches the project's `outcome_resolver.py` daily first-touch discipline). Optimistic TP-wins-ties would raise PF modestly but not to 2.88 (that requires the close-crediting artifact).
3. JPY-cross pairs except USDJPY are uncovered by `fxp_price_history` (only 8 majors) — but majors are the deployable subset anyway.

## Implications / recommended actions
- **Kill the FOREX consensus candidacy.** Not "knife-edge at sub-1bp execution" (the prior framing) — it has **no gross edge** under honest first-touch. Do not pilot, do not size, do not forward-track as a lead.
- **Re-resolve every daily-resolved CI-LB survivor with first-touch before any pilot** — including `non_crypto_consensus/COMMODITY` (the DEFINITIVE_NETCOST "survivor") and `forex_rsi2_mean_reversion`. Expect the same ~2–3× deflation.
- **Trust only the honest intrabar ledger** (`at_signal_outcomes` / `build_intrabar_truth_by_class.py`) for verdict-grade per-class numbers. It already says 0/9 T2.
- The binding constraint is unchanged and now better explained: not strategy scarcity, not execution cost alone — **the daily resolver manufactures phantom edge**, and honest forward intrabar n is the only ground truth (calendar-gated).

## Reproduce
`fxp_price_history` daily OHLC → first-touch (LONG: low≤SL→SL_HIT else high≥TP→TP_HIT; SHORT mirror; same-bar tie→SL; else TIME_EXIT at last close) → dedup symbol-day → `tools/pf_ci_lower.py` net of per-pair cost (majors 2bp / JPY 6bp). DB via `tools/db_env.get_stocks_creds()` + `get_backtests_creds()`. Cohort: `trading_picks` `strategy='non_crypto_consensus'`, `category='forex'`, entry/TP/SL>0, 2026+.
