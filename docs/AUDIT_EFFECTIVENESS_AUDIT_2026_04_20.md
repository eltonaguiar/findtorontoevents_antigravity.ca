# /audit Effectiveness Audit — 2026-04-20

**Source:** `audit_dashboard/data/dashboard_data.json` (generated 2026-04-20 16:07 UTC).
**Scope:** 48 active picks, 3,500 recent closed (range 2026-02-17 → 2026-04-20).
**Overall baseline (all closed):** n=3,500, WR=39.9%, avg_pnl=-0.28%, total=-982.5%, PF=0.76 — **net-negative**.

Notes on method:
- Closed-pick schema has no `hf_conviction_tier`, `conviction_tier`, `sym_track_wr`, or `verified_alpha` flag — retroactive feed tagging uses proxies: HC = `grade=='A' AND trust_tier in {PROVEN,RELIABLE}`; Verified Alpha = `source_system in verified_alpha.source_mix`; Smart Picks = strategy/source intersect with current `smart_picks_feed.picks`; Track% has no closed-side field.
- "Resolved" = status in {WON, LOST, CLOSED, EXPIRED}.

---

## 1. Per-feed scorecard

| Feed | n_active | n_closed (proxy) | WR % | avg_pnl % | total_pnl % | PF | Edge |
|---|---:|---:|---:|---:|---:|---:|:---:|
| All picks (baseline) | 48 | 3,500 | 39.9 | -0.28 | -982.5 | 0.76 | **D** |
| High Conviction (grade A + PROVEN/RELIABLE) | 3 | 62 | 51.6 | +0.48 | +29.6 | 1.61 | **B** |
| Verified Alpha (by source) | 17 | 1,757 | 37.8 | -0.17 | -298.8 | 0.66 | **D** |
| Smart Picks (current feed) | 1 (7 inc. tier feeds) | 1 retro-match | — | — | — | — | **N/A** |
| Track% (sym_track_wr ≥60, n≥10) | 2 | no closed field | — | — | — | — | **incomplete** |
| Open picks (floating) | 48 | — | — | avg +0.17 | sum +8.3 | — | — |
| Closed picks (all resolved) | — | 3,500 | 39.9 | -0.28 | -982.5 | 0.76 | D |
| Grade A (all tiers) | — | 211 | 45.5 | -0.33 | -69.2 | 0.71 | D |
| Trust=PROVEN | — | 790 | **26.7** | -0.45 | -357.9 | **0.52** | **F** |
| Trust=RELIABLE | — | 1,259 | 44.6 | +0.03 | +34.1 | 1.07 | C |
| Trust=WATCH | — | 820 | 40.6 | -0.97 | -792.9 | 0.60 | F |
| Trust=UNTRUSTED | — | 346 | 48.0 | +0.43 | +149.6 | 1.37 | B |
| Extreme-conviction bundle | 22 total (2A, 20B) | — | — | — | — | — | — |

**Key finding:** `PROVEN` trust tier is the single worst cohort and is dominated by one source (`claude_gainer_st`: 778/790 picks, WR 26.5%, -355%). `UNTRUSTED` outperforms `PROVEN` by ~20pp on avg_pnl — the trust label is inverted.

---

## 2. Asset-class recent-trend (last 10 vs prior-20 vs last-100)

| Class | n_total | last-10 WR / avg | prior-20 WR / avg | last-20 WR / avg | last-100 WR / avg | Trend |
|---|---:|---|---|---|---|---|
| CRYPTO | 1,738 | 90% / +0.60 | 90% / +0.85 | 85% / +0.59 | 96% / +1.51 | flat/cooling (still hot) |
| EQUITY | 338 | 50% / -0.48 | 45% / +0.63 | 45% / +0.12 | 60% / +1.42 | **down** |
| ETF | 69 | 90% / +2.53 | 60% / +0.68 | 75% / +1.40 | 51% / +0.03 | **up sharply** |
| FOREX | 836 | 30% / +0.25 | 45% / -0.02 | 30% / +0.10 | 46% / +0.02 | noisy/flat |
| COMMODITY | 502 | 70% / +0.40 | 80% / -0.15 | 80% / +0.05 | 59% / +0.01 | **up** |
| BOND | 17 | 50% / +0.44 | — | 47% / +0.17 | 47% / +0.17 | too few |

**Full-window PF by class:** EQUITY 1.44, BOND 1.60, COMMODITY 1.09, ETF 1.02, FOREX 0.93, **CRYPTO 0.63** (biggest drag).

---

## 3. Representative closed picks (sampled)

**CRYPTO wins:** ORDIUSDT +31.1% (copy_trader_intel, 04-19); LITUSDT +28.6%; ENJUSDT +25.4% (mercury2).
**CRYPTO losses:** DYDXUSDT -54.0%, -51.1%, -48.7% (copy_trader_intel copy_hl_lb — same strategy repeatedly blown up on 04-18/19).
**EQUITY wins:** MSTR +13.4%, COIN +8.4%, AMC +11.6% (kimi_riseoftheclaw scouts, 04-17).
**EQUITY losses:** XOM -3.8%, CVX -3.9%, XOM -6.6% (stocks_competition Bollinger MR / Classic Momentum, 04-17).
**ETF wins:** TQQQ +10.7% vix-mean-rev, XLK +4.7% rs-breakout, QQQ +3.3% intermarket-flow (all kimi_riseoftheclaw).
**ETF losses:** TQQQ -6.2%, XLE -5.8%, SLV -5.4%.
**FOREX:** USDCAD=X +40.45 (kimi_signal_tracking — likely bad unit scaling); best sustained: JPY=X +3.47, CHF=X +0.98 (04-20). Losses: AUDUSD=X -27.9 (same bad-scaling bucket), USDMXN=X -0.59, NZDUSD=X -1.88.
**COMMODITY wins:** CL=F +8.0 (ema_stack_momentum), GC=F +5.0, SI=F +1.32 (futures_momentum). Losses: CL=F -5.5, SI=F -4.2.
**BOND:** ZN=F +5.0 short (futures_momentum), HYG +0.75 pairs. Losses: TLT -1.3, -1.1, -0.97 (betting-against-beta).

---

## 4. Data-quality issues (concrete)

| # | Issue | Count | Example |
|---|---|---:|---|
| 1 | `trust_tier=PROVEN` while `strat_fwd_wr < 50%` (label inversion) | **790** | `claude_gainer_st_ETHUSDT_LONG_st_fear_greed_contrarian_20260420 015717` fwd_wr=31.7% yet PROVEN |
| 2 | `status='LOST'` but `pnl_pct > 0` | 8 | `aggregated_picks_TAOUSDT_SHORT_..._20260418` pnl=+2.11 |
| 3 | `status='WON'` but `pnl_pct ≤ 0` | 1 | pnl=0.0 with null id |
| 4 | Active pick with populated `exit_price` (should be OPEN only) | 1 | id `1620111b3ba7` exit_price=0.2457 |
| 5 | FOREX picks with decimal-formatted pnl (e.g. 0.0006) vs percent (e.g. +1.28) — two scales co-exist in same feed | ~hundreds in `multi_asset_copytrader` / `forex_copy_trader` | `USDCAD=X` pnl=-0.0003 vs same symbol +1.28 |
| 6 | Strategy `'unknown'` / empty string in kimi_riseoftheclaw FOREX picks | 7+ | all 04-20 FOREX kimi rows |
| 7 | `kimi_signal_tracking` pnl magnitudes suspicious: USDCAD=X +40.45 and AUDUSD=X -27.93 in FOREX (likely price-delta, not %) | 5+ | 2026-04-10 batch |
| 8 | `pm_kalshi_signals`, `ml_consensus`, `polymarket_signals` listed in Verified Alpha source_mix but have **zero** closed picks | 3 sources | verified_alpha realized WR is not representative of the VA cohort |
| 9 | `smart_picks_feed.total_scored=25` but only 1 closed-side match with any smart pick's strategy+source pair — feed is effectively un-auditable retroactively (no `_smart_pick` flag on closed picks) | — | — |
| 10 | `active` picks report `pnl_pct` on OPEN status (floating), which is fine, but easy to confuse — 45/48 have non-zero pnl | 45 | `copy_pm_comtruise::BTCUSDT::2026-04-20_1546` pnl=-0.36 |

---

## 5. Verdict per feed

- **High Conviction (grade-A PROVEN/RELIABLE proxy):** **Real edge.** WR 51.6%, PF 1.61, +29.6% total on 62 resolved trades. Small sample but consistent. **Production-ready as a curated feed.**
- **Verified Alpha:** **Not delivering.** Aggregate WR 37.8%, PF 0.66, -299% over 1,757 trades. Dominated by two sources: `multi_asset_copytrader` (PF 1.49, genuinely positive) and `claude_gainer_st` (PF 0.50, -355%). The label spans both good and broken systems. Three of its 8 listed sources have **zero** closed history — the displayed WR is not representative.
- **Smart Picks:** **Un-auditable retroactively** (no historical flag). Current feed is mostly 1 pick; can't confirm edge from this snapshot.
- **Track%:** Active-only field; no closed-side telemetry. Can't evaluate.
- **Open picks:** Currently slightly positive floating (+0.17% avg, +8.3% sum, 48 picks) — trivial sample.
- **Closed picks (baseline):** **Net-negative.** PF 0.76. EQUITY + BOND + COMMODITY classes are the positive contributors; CRYPTO (PF 0.63) and FOREX (PF 0.93) are the drag.

**Strongest value prop for a /audit visitor today:** EQUITY + ETF picks from `kimi_riseoftheclaw` scouts (intermarket-flow, rs-breakout, quality-momentum) — ETF last-10 WR 90% / avg +2.53%, EQUITY full-window PF 1.44. COMMODITY via `multi_asset_copytrader` futures_momentum is also trending up. **Deemphasize** `claude_gainer_st` and `copy_trader_intel` crypto signals — they account for the majority of the -982% total drag.

---

## 6. Top-3 recommendations

1. **Fix the trust-tier inversion.** `PROVEN` currently realizes WR 26.7% / PF 0.52 because `claude_gainer_st` dominates the cohort with `strat_fwd_wr` values in the 30s while labeled PROVEN. Re-derive `trust_tier` from realized rolling-N PF (not forward_wr). Either relabel or demote `claude_gainer_st` via `BLOCKED_SOURCE_SYSTEMS` following `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`.
2. **Stamp `is_smart_pick`, `is_verified_alpha`, `hc_tier`, and `track_pct_bucket` on picks at issue time and persist through close** so feeds can be audited retroactively. Today only High Conviction has a usable proxy; the three other feeds are un-auditable from `recent_closed`.
3. **Normalize FOREX pnl units.** `multi_asset_copytrader` / `forex_copy_trader` emit decimal-space pnl (0.0003) while `kimi_riseoftheclaw` / `kimi_signal_tracking` emit percent-space (and some price-delta). This silently destroys aggregate stats — FOREX PF 0.93 is not trustworthy. Add a unit-contract test at ingest and backfill.

---

*Generated 2026-04-20 from dashboard_data.json timestamped 16:07 UTC. Not committed.*
