# Cross-Check All Pick Surfaces — Entry-Condition Segmentation & Risk Assessment (2026-10-22)

## Executive summary

I cross-checked **every pick surface** (`findtorontoevents.ca/audit` dashboard data, the MySQL `trading_picks` DB truth, other agents' paper picks, the AI-tournament universe, Hyrotrader, and my prior candidate set) against the institutional Phase-1/2/3 verification gates.

**Bottom line: no additional MONEY-READY winner emerges.** The `money_ready_verdict.json` summary lists `money_ready: []` (only `COMMODITY` on "watch"). Every candidate that shows a positive net profit factor is either **below the n≥100 gate**, **below the net CI-LB > 1.15 promotion bar**, or **an artifact** (frozen-exit / over-emission / mispriced entry).

However, the **entry-condition segmentation** surfaced **three new CANDIDATE segments** not previously flagged (each net-of-cost and positive but underpowered). None is worth risking capital yet.

## 1. Surfaces inventoried

| Surface | Source | Verdict |
|---|---|---|
| /audit dashboard (forward candidates) | `forward_candidate_scoreboard.json` | Only `luxalgo_confluence/SHORT` real-edge sub-bar (CI-LB 1.0898, but n=47, n_eff=44.6 < 80) |
| DB truth (mysql.trading_picks) | `summary_picks.json` | 127,410 total / 17,990 resolved; winning_rate_pct values broken (>100%: BOND 133%, COMMODITY 240%, ETF 243%, FUTURES 381%, INDEX 1141%) → data-quality flag |
| Other agents' paper picks | `COMMUNITY/*` + `poolside_paper.json` | No PROVEN class; copper FAIL, mega_mutation FAIL, high_trust_momentum NOT-proven, tactical rotation only defensible instrument |
| AI tournament universe | `ai_tournament_leaderboard.json` | 7,099 picks; only `kimi_direct` T1 (WR 62.9%, PF 2.333) but n_resolved=62 < 100; all other 45 models BELOW. 4,285/7,099 entries mispriced (60% data contamination) |
| Hyrotrader | `hyro_pick_performance.json` | 30-day lookback only; top "A+" cell n=39 (33W/6L, PF 11) — too small, not a promotion signal |
| Prior candidates | `forward_candidate_scoreboard.json` + `verified_edge_status.json` | 0/6 money-ready; etf_verified_dual_momentum lab_wf PASS but forward_n=0 |

## 2. Entry-condition segmentation — the "advanced stuff"

Full list from [`entry_conditions_forward.json`](audit_dashboard/data/entry_conditions_forward.json) (cohort n=3,520, deduped, hard-only resolution). All figures are **net-of-cost**:

| Condition | Class | n | Net WR | Net PF | Last-30d Net PF | Gate status |
|---|---|---|---|---|---|---|
| `crypto_rsi5070_us` | CRYPTO | 393 | 41.2% | 0.954 | 0.874 | FAIL (net < 1.0, decaying) |
| `crypto_short_rsi5070_REGIMEWATCH` | CRYPTO | 473 | 41.0% | 0.951 | **1.234** | Full cohort FAIL; short-term regime-dependent only |
| `crypto_short_volhigh` | CRYPTO | 376 | 42.6% | 0.978 | **1.826** | Full cohort FAIL; last-30d strong |
| `luxalgo_short` | cross-class | 572 | 41.8% | 0.971 | **1.751** | Corroborates SHORT candidate; last-30d strong |
| `equity_lowvol` | EQUITY | 82 | **76.8%** | **3.756** | 999 (100% WR, n=18) | **Standout, but n < 100 gate** |
| `equity_highvol_NEGATIVE` | EQUITY | 83 | 65.1% | 1.321 | 1.338 | Confirm high-vol is a loss cluster to avoid |
| `forex_trend_aligned` | FOREX | 50 | 60.0% | 2.315 | 0.588 | Promising full-cohort, decaying last-30d |
| `forex_contrarian_NEGATIVE` | FOREX | 189 | 14.3% | 0.188 | 0.237 | Confirm contrarian is a loss cluster |
| baselines (per class) | CRYPTO 0.749 / FOREX 0.401 / BOND 0.0 / ETF 0.0 / MEMECOIN 0.546 / FUTURES 0.789 / COMMODITY 0.515 | — | — | all < 1.0 | — | Raw class baselines are all losers |

**Key finding:** the edge is **not** in any asset-class baseline — it lives in **directional + regime/vol filtered segments**:
- CRYPTO: **SHORT + high-vol** (and SHORT + RSI 50-70 in current regime) beats LONG + low-vol.
- EQUITY: **LOW-vol long** beats HIGH-vol; high-vol accounts for ~64% of losses (the NEGATIVE filter).
- FOREX: **trend-aligned** beats contrarian (contrarian is a systematic loser).

But **every one of these segments is below the n≥100 gate** or fails the full-cohort net-PF gate → none is promotion-ready.

## 3. Cross-check vs institutional gates

**Phase 1 (Sharpe/Sortino/Calmar/IR):** No single-strategy cell passes. Only the ETF tactical-rotation family is validated (bootstrap Sharpe positive across 2007–2026 incl. 2008/2020/2022; `TACTICAL_ROTATION_EDGE_2026-07-04.md`).

**Phase 2 (bootstrap/DSR/PF/expectancy):** Close to nothing passes the promotion bar `net CI-LB > 1.15 AND n_eff ≥ 80 AND n ≥ 150 AND OOS ≥ 1.0`:
- `luxalgo_confluence/SHORT`: CI-LB 1.0898 (n=47, n_eff 44.6) — below bar.
- `kimi_direct` tournament T1: WR 62.9%, PF 2.333, CI-LB PF 1.241 — but n_resolved=62 < 100.
- `equity_lowvol`: net PF 3.756 — n=82 < 100, no bootstrap yet.
- `crypto_short_volhigh` / `luxalgo_short` last-30d segments: net PF 1.826 / 1.751, but n<80 and recent-only.

**Phase 3 (capacity/Omega/CVaR):** Confirmed **entirely missing** in the codebase (no measured market impact/slippage, no Omega ratio, no portfolio CVaR). This remains the blocker for any "money-ready" claim.

## 4. Risk-worthiness

| Candidate segment | Net-of-cost PF | n | Concentration / tail concern | Worth the risk? |
|---|---|---|---|---|
| `equity_lowvol` | 3.756 | 82 | EQUITY shadow-pilot HHI strategy 0.496 / source 0.693 (highly concentrated) | **No** — underpowered + concentrated; bootstrap pending |
| `crypto_short_volhigh` (last-30d) | 1.826 | 77 | crypto ~50% vol proxy; tail not measured (no CVaR) | **No** — high tail risk unquantified |
| `luxalgo_short` (last-30d) | 1.751 | 126 | cross-asset; SHORT-only bias | **Watch** — closest to n gate, still sub-bar CI-LB |
| `kimi_direct` (tournament) | 2.333 | 62 | single-model, 60% mispriced-entry contamination in universe | **No** — n too small, data integrity flagged |

Concentration is the recurring damper: the strongest-looking segments sit in the most concentrated buckets (`equity_lowvol` HHI ≈ 0.5+), and tail risk is unmeasured because Phase 3 is missing. Net-of-cost expectation is already applied (all `net_pf` fields), so the numbers above are honest after costs — they simply do not clear the volume/confidence bar.

## 5. Recommendations

1. **Track (don't trade) the three new candidate segments** to their n≥100 gates, re-running R1/R2/R3 (split-half, concentration, binomial p<0.005) before any sizing: `equity_lowvol`, `crypto_short_volhigh`, `forex_trend_aligned`.
2. **Keep monitoring `luxalgo_confluence/SHORT`** — it is the only sub-bar real-edge cell; promoting it to n_eff≥80 with CI-LB>1.15 would be the first Phase-2 pass.
3. **Fix the Phase-3 gap** (measured slippage/market-impact, Omega, portfolio CVaR) before promoting anything.
4. **Clean the tournament feed** — 60% mispriced entries and broken `win_rate_pct` in `summary_picks.json` are still contaminating the "winner" search.
5. **Continue the ETF tactical rotation** as the only deployed, defensible instrument.

## Files consulted
- `audit_dashboard/data/entry_conditions_forward.json`
- `audit_dashboard/data/forward_candidate_scoreboard.json`
- `audit_dashboard/data/ai_tournament_leaderboard.json`, `ai_tournament_picks_latest.json`, `summary_tournament_data.json`
- `audit_dashboard/data/money_ready_verdict.json`
- `audit_dashboard/data/top_notch_money_ready.json`, `shadow_pilot_verdicts.json`
- `audit_dashboard/data/hyro_pick_performance.json`, `hyrotrader_enhanced_picks.json`
- `audit_dashboard/data/summary_picks.json`, `picks_now_track_record.json`, `poolside_paper.json`
- `reports/TACTICAL_ROTATION_EDGE_2026-07-04.md`, `COMMUNITY/*`

*Not financial advice. Research/educational only. Past performance does not guarantee future results.*
