# New Persona/Model Strategy Proposals — `/audit/ai-tournament.html` (2026-06-05)

**Author:** Claude (proposal only — DO NOT implement without review)
**Grounded in:** `MASTERPLAN_JUNE52026_CLAUDE.MD` Action 3 (non-LLM features), `MEGA_MUTATION_BRIDGE_CANDIDATE_2026-06-05.md`, `RISK_REVIEW_MEGA_MUTATION_2026-06-05.md` 5-gate pattern, `SUSPICIOUS_PICKS_SCRUTINY_2026-06-05.md` artifact taxonomy.

## Design principles (carried forward from session evidence)

1. **No LLM in the signal path.** Every entry rule is a deterministic function of public market data. The "persona" is just the labeling convention so the tournament UI can attribute picks; the model is a pure feature.
2. **Multi-symbol cohorts only.** Single-asset bets (DYDX, RENDER) were flagged as artifacts (`SUSPICIOUS_PICKS_SCRUTINY_2026-06-05.md`).
3. **No news / event triggers.** Resolver cannot replay news; INCIDENT #94 / #91 pattern guarantees mislabel.
4. **Diversified across ≥5 symbols, max single-symbol share <25%, max single-day share <25%.** Mirrors `mega_mutation` gate that passed scrutiny.
5. **Each proposal includes an ANTI_OVERFIT_GATE** — a pre-registered hypothesis-killer.
6. **Risk-review compatible:** all use public price/derivative data; no wallet keys; advice boundary = informational only via `/audit`.

---

## Proposal 1 — `funding_rate_mean_reversion`

- **persona_label:** `funding_extremes_fader`
- **asset_class:** CRYPTO (perps)
- **HYPOTHESIS:** Perp funding rate >+0.10% per 8h indicates crowded long positioning that mean-reverts within 16h on Binance majors+mids; symmetric for funding <−0.10%.
- **ENTRY_RULE:** Every 8h funding tick, on the universe {BTC, ETH, SOL, AVAX, DOT, LINK, ADA, MATIC, ATOM, NEAR}, take SHORT if funding ≥ +0.10% AND 24h price change > 0; LONG if funding ≤ −0.10% AND 24h price change < 0.
- **EXIT_RULE:** TP +1.5%, SL −1.0%, time-stop 16h (2 funding cycles).
- **DATA_SOURCES:** Binance Futures `/fapi/v1/premiumIndex` (funding + mark price). No auth required.
- **EXPECTED_N_PER_MONTH:** ~25–40 (across 10 symbols × 3 funding ticks/day, gated by extreme threshold).
- **ANTI_OVERFIT_GATE:** If 30-day forward WR < 50% on n ≥ 25, OR if any single symbol contributes >30% of n, kill. If funding-extreme frequency collapses below 5/month (regime change), pause emission.

---

## Proposal 2 — `commodity_term_structure_carry`

- **persona_label:** `contango_carry_trader`
- **asset_class:** COMMODITY
- **HYPOTHESIS:** Steep contango in oil/nat-gas futures (front − 6th month spread > 5% of spot) precedes front-month underperformance over 5 trading days as roll cost compounds; steep backwardation precedes outperformance.
- **ENTRY_RULE:** Daily 16:00 ET close, on {CL=F, NG=F, HO=F, RB=F}: SHORT front-month if (M1 − M6)/M1 > +5%; LONG if (M1 − M6)/M1 < −5%.
- **EXIT_RULE:** TP +2.0%, SL −1.5%, time-stop 5 trading days.
- **DATA_SOURCES:** yfinance (CL=F, CL2=F … CL6=F chain) — no auth required. Existing access in repo per Action 3 note.
- **EXPECTED_N_PER_MONTH:** ~6–10 (4 symbols × ~2 signal days/month given 5% threshold).
- **ANTI_OVERFIT_GATE:** If forward Sharpe < 0.5 on n≥20, kill. If >60% of n is single-symbol (e.g., NG=F dominance like the cta_trend artifact), reject as monoculture per `MASTERPLAN` Session 1.

---

## Proposal 3 — `vix9d_vix_regime_rotator`

- **persona_label:** `vol_term_structure_rotator`
- **asset_class:** ETF
- **HYPOTHESIS:** When VIX9D < VIX (short-vol < medium-vol → market expects calm) equity-beta ETFs outperform over 3 trading days; when VIX9D > VIX (stress front-loaded) defensive ETFs outperform.
- **ENTRY_RULE:** Daily at 09:45 ET, compute VIX9D/VIX ratio. If ratio < 0.95: LONG basket {SPY, QQQ, IWM}. If ratio > 1.05: LONG basket {TLT, GLD, SHY}, SHORT {QQQ}.
- **EXIT_RULE:** TP +1.5%, SL −1.0%, time-stop 3 trading days.
- **DATA_SOURCES:** yfinance (^VIX9D, ^VIX). Already partially shipped per `MASTERPLAN` Action 3 #3 — "just needs wire-up."
- **EXPECTED_N_PER_MONTH:** ~10–15 (signal fires ~50% of trading days; basket of 3–4 symbols).
- **ANTI_OVERFIT_GATE:** Two-regime test — WR must hold within 15pp delta across high-VIX (>20) and low-VIX (<15) sub-samples. If split fails, kill. If forward PF < 1.2 on n≥30, kill.

---

## Proposal 4 — `etf_dual_momentum_basket`

- **persona_label:** `trend_following_rotator`
- **asset_class:** ETF
- **HYPOTHESIS:** Absolute + relative momentum (Antonacci dual momentum) on a 4-ETF risk-on/off basket harvests trend persistence with low single-symbol concentration. Already lab-validated PF 1.60 (memory `project-etf-pilot-day1-2026-06-02`); proposing the tournament-persona wrapper for forward attribution.
- **ENTRY_RULE:** First trading day of each calendar week, rank {SPY, EFA, IEF, GLD} by 6-month total return. LONG top-2 if their 6m return > IEF (cash proxy) return; else LONG IEF only.
- **EXIT_RULE:** Weekly rebalance (time-stop = 5 trading days). Hard SL at −5% per leg. No TP — let trend run until next rebalance.
- **DATA_SOURCES:** yfinance daily closes for the 4 ETFs.
- **EXPECTED_N_PER_MONTH:** ~8 (2 legs × 4 weeks).
- **ANTI_OVERFIT_GATE:** If 30-day forward WR < 50%, OR if max drawdown of basket > 8% in any rolling 30d, pause. If top-2 picks are SPY+QQQ correlation cluster only (effective n=1 asset), reject.

---

## Proposal 5 — `fx_carry_diff_with_realized_vol_filter`

- **persona_label:** `risk_adjusted_carry_trader`
- **asset_class:** FOREX
- **HYPOTHESIS:** G10 carry trades (long high-yielder / short low-yielder) work when realized FX vol is low (carry > vol budget); they blow up when vol spikes. Extension of the `fx_smart_carry_trade_momentum` candidate (n=25, WR 60%, PF 1.85 per `SUSPICIOUS_PICKS_SCRUTINY`).
- **ENTRY_RULE:** Daily 17:00 NY close, for pairs {AUDJPY, NZDJPY, CADJPY, AUDUSD, NZDUSD, USDJPY}: compute (rate_base − rate_quote) annualized — public CB rates. Also compute 20d realized vol. If carry/vol > 0.5 AND 20d realized vol < 8% annualized: LONG carry direction.
- **EXIT_RULE:** TP +1.0%, SL −0.8%, time-stop 5 trading days. Hard kill if realized vol spikes >12% intraday.
- **DATA_SOURCES:** yfinance (FX crosses), FRED API (or hard-coded central-bank rate snapshots updated monthly — central bank rates change infrequently enough to not need a live feed).
- **EXPECTED_N_PER_MONTH:** ~12–18 (6 pairs × ~3 signal days/month).
- **ANTI_OVERFIT_GATE:** Reject any window where >50% of n comes from a single carry pair (avoid CADJPY +427% style outlier from INCIDENT cleanup). If forward WR drops below 50% on n≥30 OR if a single trade exceeds |30%| pnl (impossible for FX → resolver bug indicator), pause and trigger price-feed audit per `clean_ingest_v2.py` rules.

---

## Cross-proposal risk-review summary (5 gates per `RISK_REVIEW_MEGA_MUTATION_2026-06-05.md`)

| Gate | Status across all 5 | Notes |
|---|---|---|
| Advice Boundary | PASS | All emit informational picks to `tournament_picks`; no live execution path; `production_enable=false` enforced |
| Venue / Regulatory | PASS-with-WARN | All instruments are major-venue listed (no memecoins, no penny stocks); FX/ETF/futures/perp majors only |
| Data Quality | WARN | All inherit the intrabar resolver caveat (M-resolver fix outstanding per `MASTERPLAN`); each ANTI_OVERFIT_GATE includes a feed-sanity check |
| Security | PASS | No wallet keys; all data via public APIs; DB writes go through existing `tools.db_env` env-var path |
| Privacy | PASS | Aggregate only on `/audit`; no PII |

## Why these and not more

- I did NOT propose any LLM-rewrite persona ("contrarian Claude", "carry-trader GPT") — those were Session 1's failure mode (MASTERPLAN §1).
- I did NOT propose anything on-chain (whale flows, exchange netflow) — feasible but requires Glassnode/Nansen paid auth; out of scope for "no new dependencies" Action 3.
- I did NOT propose anything on EQUITY single-name — per `MASTERPLAN` §4 EQUITY is recommended for deprecation; new alpha there is low-EV.
- All 5 reuse data feeds the repo already has (Binance, yfinance, FRED public).

## Recommended next step (operator)

1. Skeptic review via `/consult-deepseek` and `/consult-grok` on this file BEFORE any implementation (per `multi-agent-storm-2026-06-05` lesson: "VALIDATED ✅" without cross-AI critique was Cloud-Minimix's failure mode).
2. Pick the 2 highest-conviction proposals for first-build (likely #1 funding and #3 VIX9D — both have prior partial-build per Action 3).
3. Implement under `tools/feature_signals/<name>/` per Action 3 plan, write to a separate `feature_signals` table (NOT `tournament_picks`) for 30-day head-to-head vs frozen LLM tournament.
4. Apply mega_mutation 5-gate review at n=30 forward before any size-up.

---

Filed by Claude proposal-only pass at 2026-06-05. No code changed.
