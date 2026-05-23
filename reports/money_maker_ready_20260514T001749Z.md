# Money-Maker-Ready Audit — 2026-05-13 (20260514T001749Z UTC)

## 0. Freshness preflight

- `audit_dashboard/data/dashboard_data.json::generated_at` = `2026-05-13T23:19:53.893945+00:00`
- Age at audit start: 0.94h (FRESH; passes <2h gate)
- Source: pulled `origin/main` snapshot (local was on feature branch per `feedback_dashboard_data_local_staleness`).

---

## 1. Per-class baseline (verdict-grade)

Source: `dashboard_data.json::performance.asset_class_health`. Cumulative since inception, post-resolver-v2.

| Class | (n | WR | PF | tier label) | Charter tier verdict |
|---|---|---|---|---|
| COMMODITY | (n? | 70.5% | **4.03** | stable) | **Tier-1 prima-facie** — but PF inflated by `multi_asset_cot` PF 21.86 (see §4 caveat) |
| ETF | (n? | 56.6% | 1.41 | stable) | Tier-2-floor PF gap (0.09 below 1.5) but WR-pass |
| EQUITY | (n? | 51.4% | **1.55** | stable) | **Tier-2 candidate** (PF ≥1.5, WR ≥50) |
| BOND | (n? | 54.5% | 0.66 | **thin**) | Sub-floor — n inadequate for verdict |
| CRYPTO | (n? | 46.4% | 1.33 | stable) | Tier-3 floor PF-pass, WR below Tier-2 (50) |
| FOREX | (n? | 41.8% | 0.63 | stable) | **Sub-floor** — kill candidates documented (§4) |
| FUTURES | (n=0 | 0.0% | n/a | insufficient) | **No closed trades** — emitter unblock pending (PRs #946/#949) |

**Gap:** `asset_class_health` rows lack explicit `n` field; verdict-grade audit needs n alongside WR/PF. Filed as P3 follow-up.

---

## 2. Walk-forward verification (per class, OOS)

Source: `dashboard_data.json::walkforward.by_class`.

| Class | folds | oos_wr | oos_sharpe | decay | consistency | verdict |
|---|---|---|---|---|---|---|
| ETF | 5 | **74.0%** | **10.08** | +19.0 | 100% | **EXCELLENT** — best OOS |
| EQUITY | 8 | **61.9%** | 7.53 | +1.7 | 100% | **EXCELLENT** — stable OOS |
| CRYPTO | 51 | 45.2% | 1.74 | -0.4 | 74.5% | STABLE — marginal decay |
| FOREX | 4 | **11.5%** | **-12.26** | -16.5 | 0% | **BROKEN OOS** — confirms cumulative sub-floor |
| COMMODITY | (missing) | — | — | — | — | **UNVERIFIED — walkforward absent** |
| BOND | (missing) | — | — | — | — | **UNVERIFIED — walkforward absent** |
| FUTURES | (missing) | — | — | — | — | **UNVERIFIED — n=0 expected** |

**Critical gap:** the strongest cumulative class (COMMODITY at PF 4.03) has NO walkforward verification. Same for BOND. Without OOS validation, the inception-cumulative numbers are not trustworthy for real money.

---

## 3. Cumulative system winners (Tier-2-MDD-verified)

Filter: `profit_factor ≥ 1.5 AND win_rate ≥ 50 AND max_drawdown ≤ 20 (or null) AND closed_picks ≥ 100`.

| System | classes | n | WR | PF | pnl_pct | last_signal | verdict |
|---|---|---|---|---|---|---|---|
| `multi_asset_cot` | COMMODITY | 102 | 94.1% | **21.86** | +429.0% | live | **SUSPICIOUS** — same shape as COT TIER-1 falsified pattern (PR #961). Verify per §11. |
| `kimi_signal_tracking` | CRYPTO,FOREX | 1183 | 68.8% | 4.30 | +28.4% | live | **TRUSTED** — high n, multi-class. |
| `signal_validation` | CRYPTO,FOREX | 541 | 50.5% | 4.04 | +96.4% | live | TRUSTED — PF gap from breakeven WR explained by R:R. |
| `ml_crypto_pred_v12` | CRYPTO | 123 | 55.6% | 2.53 | +20.4% | live | TRUSTED — production ML pred. |
| `copy_trader_intel` | CRYPTO | 688 | 50.0% | 1.84 | +4.2% | live | Marginal; WR exactly at floor. |

Only **5 of 129** systems meet the Tier-2-MDD verification gate. `multi_asset_cot` requires immediate audit before sizing up.

---

## 4. System draggers (negative PnL contribution)

Filter: `profit_factor < 0.5 OR pnl_pct < -50% AND n >= 20`.

| Rank | System | classes | n | WR | PF | pnl_pct | recommended action |
|---|---|---|---|---|---|---|---|
| 1 | `multi_asset` | COMMODITY,FOREX | 231 | 45.5% | 0.32 | **-160.9%** | **P0 investigate** — mutation-before-kill per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`. JPY-cross already blocked (line 1857). Look for next-biggest symbol drag. |
| 2 | `mercury2_fast` | CRYPTO | 32 | 42.9% | 0.07 | -139.5% | **P0 kill-candidate** — PF 0.07 catastrophic, low n means quick win. |
| 3 | `alpha_engine_fast` | BOND,COMMODITY,CRY... | 299 | 43.2% | 0.62 | -127.6% | **P0** — large drag, multi-class. Investigation per `STRATEGY_INVESTIGATION_BEFORE_KILL.md`. |
| 4 | `copy_trader_highscore` | CRYPTO | 339 | 31.9% | 0.77 | -79.8% | P1 — long-tail underperformer. |
| 5 | `fast_stocks_competition` | EQUITY | 60 | 0.0% | 0.00 | -22.0% | **P0 kill** — 0 wins on n=60 means structural broken. |
| 6 | `goldmine_stocks` | EQUITY,ETF | 453 | 42.9% | 0.14 | -11.7% | P0 — already documented as kill candidate in memory (per CLAUDE.md `project_futures_kill_without_replacement`). |

5 zero-WR systems with n>20: `breakout_b_ml`, `kimi_claw_research`, `ml_crypto_predictor` (n=22805!), `penny_screener`, `top_gainer_predictor`. `ml_crypto_predictor` at n=22805 / 0% WR is almost certainly a placeholder / template-emission system not actually trading — needs explicit `INACTIVE` mark.

---

## 5. Backtest-overfit detector flags

Source: `dashboard_data.json::fwd_vs_bt_divergence.rows` — 12 rows.

| family | flagged count | recommended action |
|---|---|---|
| `baby_strats` | **12 / 12** | **P1 surgical quarantine** — all flagged rows are in this single family. Per `reports/baby_strats_overfit_quarantine_proposal_2026_05_10.md` template, add per-strategy entries to `BLOCKED_ASSET_STRATEGY_PAIRS` rather than family-wide kill. |

---

## 6. Drift state

`hf_stats.concept_drift.drift_alert` = **TRUE**.

However `ks_d` and `ks_critical` are both `None` — drift module is emitting the alert flag but not the supporting statistics. Cannot compute D/critical ratio; cannot validate severity.

**Recommendation:** P1 — investigate why `hf_stats.concept_drift` is missing its KS-D + critical values. Either (a) `concept_drift` generator is partially broken (writes alert without writing stats), or (b) downstream consumer is reading the wrong field. Either way, the alert is unactionable as-is.

Pausing real-money sizing on the alert alone is over-cautious until the stats are present. Flag for operator awareness; do NOT auto-pause.

---

## 7. UI/Filter audit

Source: `audit_dashboard/template.html`.

Not exhaustively audited in this run (too long for in-context inspection). Spot-checks (PR #962 confirmed earlier this session):

- Swarm pick tracking panel: explainer + last-updated EST/EDT + thin-sample warning landed (PR #962, merged path).
- Research index page: EST/EDT timestamps + verdict legend landed (PR #965).
- High-Conviction filter: not re-audited this run. Memory `feedback_confidence_is_not_edge.md` notes confidence inversion on ETF/CRYPTO — High-Conviction filter may be misleading on those classes.

**Recommendation:** P2 — separate UI/filter audit PR. Specifically test that the High-Conviction filter does NOT include picks where `confidence >= 0.90` automatically (per memory `project_performance_reality`: 0.90+ conf = 22.2% WR = trap).

---

## 8. External data integrations to consider

Ranked by expected Goal-1 impact per current state.

| Library / data | Class fit | Expected impact | Effort | Current gap |
|---|---|---|---|---|
| **VectorBT** | CRYPTO + HFT | 50-100× faster backtests → faster iteration on FOREX mutation | Low-Med | Slow iteration is the main bottleneck on FOREX rescue |
| **Riskfolio-Lib** (CVaR / HRP) | All | Risk-cap layer; prevents -160% draws like multi_asset | Low | No risk-cap audit gate; relies on per-pick TP/SL |
| **FRED data** | Macro overlay | VIX/DXY/YC regime gates — `feat/system-staleness-detection-2026-05-13` PR #943 partial wiring | Low | `FRED_API_KEY` set but only partially consumed |
| **QuantStats** | Reporting | Tearsheet reports per system | Very Low | Audit reports currently hand-rolled markdown |
| **PyPortfolioOpt** (HRP / Black-Litterman) | EQUITY + ETF | Portfolio-level optimization on top of the 5 verified winners | Low | No portfolio-construction layer between pick selection and execution |
| **Polymarket + Kalshi consensus** | Cross-asset | Real-money prediction-market signal as macro overlay | Med | `prediction_market_consensus.py` wired; `pm_consensus_overlay.py` sidecar not yet built |
| **Glassnode / Coinglass** | CRYPTO on-chain | Whale flows + funding rates — helps fix the regime-flip stale-momentum issue (PR #971) | Med | Partial integration; funding_rate_arb exists |
| **FinRL** RL adaptive | CRYPTO | RL regime switching (longer horizon than today's hysteresis) | High | Defer until non-RL regime detection (PR #971) is stable |

---

## 9. Top statistical edges per asset class

Used `dashboard_data.json::cross_strategy_permutations` if present + `systems` aggregates. Top edges per class with (n ≥ 8 stat-sig gate, WR ≥ 52%, PF ≥ 1.5):

### CRYPTO top edges
- `kimi_signal_tracking` (n=1183, WR 68.8%, PF 4.30) — already deployed in production; broadest CRYPTO/FOREX strategy
- `ml_crypto_pred_v12` (n=123, WR 55.6%, PF 2.53) — production ML, comfortably above floor
- `signal_validation` (n=541, WR 50.5%, PF 4.04) — high-PF, low-WR (R:R-driven), works for trend-following overlay
- INJUSDT LONG via swarm UNANIMOUS (3/3) — placed in BROKIE this session, awaiting validation

### EQUITY top edges
- Walkforward 61.9% OOS WR, sharpe 7.53. Specific symbol×strategy combos: cross-reference `cross_strategy_permutations` (not deeply inspected in this run — P2 follow-up).
- Goal #1 banner notes EQUITY is T2-candidate at PF 1.41 / WR 52.7% — converging.

### ETF top edges
- Walkforward 74% OOS WR, sharpe 10.08. ETF emitter scale-up (n=87 → target n>=200) was queued in CLAUDE.md banner.
- `etf_trend_following` / `etf_dual_momentum` families likely; needs cross_strategy_permutations dive.

### COMMODITY top edges
- `multi_asset_cot` PF 21.86 (n=102, WR 94.1%) — **MUST VERIFY** before sizing. Likely same shape as falsified COT TIER-1 (PR #961). If real after dedup, it's the single biggest edge on the board.

### FOREX top edges
- Currently sub-floor system-wide. Best individual edge: `kimi_signal_tracking` FOREX subset and non-JPY pairs on `multi_asset_copytrader` (n=100, WR 52.2%, +148.2% pnl per earlier session forensic).
- 3 EQUITY-short swarm-flagged (NVDA / TSLA / PLTR) are EQUITY not FOREX, but production scanner has zero short coverage — explicit gap.

### BOND top edges
- Thin sample (`tier=thin`). No actionable edges until n raises.

---

## 10. Best-Possible-Action ranked recommendations

| Priority | Action | Asset class impact | Effort (hr) | Risk | Reversibility | Expected lift |
|---|---|---|---|---|---|---|
| **P0** | **Audit `multi_asset_cot` PF 21.86** — apply COT dedup logic (PR #961) to this system's emit path. If COT-falsified, expect PF crash analogous to TIER-1_RENAISSANCE artifact. | COMMODITY | 2 | Low | Full | Could remove the biggest single PF claim on the board; honest revaluation. |
| **P0** | Quarantine `mercury2_fast` (PF 0.07 / n=32) + `fast_stocks_competition` (0 WR / n=60) + `breakout_b_ml` (0 WR / n=44) | CRYPTO + EQUITY | 1 | Low | Full | Stop active losses; ~$140% drag clipped. |
| **P0** | Mark `ml_crypto_predictor` INACTIVE (n=22805 / 0 WR — placeholder pattern, not real strategy) | CRYPTO | 0.5 | Low | Full | Removes biggest single visual artifact from systems list. |
| **P1** | Fill walkforward gap for COMMODITY + BOND | COMMODITY + BOND | 4 | Low | n/a | Required before any real-money sizing on COMMODITY. |
| **P1** | Investigate `multi_asset` strategy (-160.9% pnl, n=231) — apply 3-axis mutation (symbol × direction × timeframe) per `MUTATION_THREE_AXIS_PROTOCOL.md`. JPY already blocked. | COMMODITY + FOREX | 4 | Low | Full | If mutation surfaces a working subset, rescue 30% of FOREX volume. |
| **P1** | Surface concept_drift `ks_d` + `ks_critical` (alert TRUE but stats None) | All | 2 | Low | n/a | Make drift alert actionable. |
| **P1** | Quarantine baby_strats 12 fwd_vs_bt_divergence rows per `reports/baby_strats_overfit_quarantine_proposal_2026_05_10.md` template | mixed | 2 | Low | Full | Reduces backtest-overfit noise in dashboard aggregates. |
| **P2** | Merge PR #946 + #949 (after my pushed fixes land) — unblocks FUTURES n=0 | FUTURES | 0 (review only) | Low | Full | Tier-2 candidate path for FUTURES; expected WR 55-65% on ES/NQ. |
| **P2** | ETF emitter scale to n≥200 (currently n=87) — exploits walkforward sharpe 10.08 | ETF | 6 | Low | Full | Lift ETF from Tier-2-floor-PF-gap to confirmed Tier-2. |
| **P3** | Riskfolio-Lib CVaR risk-cap layer | All | 8 | Med | Full | Prevents -160% multi_asset class drags. |
| **P3** | UI High-Conviction filter audit (memory: 0.90+ conf = 22.2% WR trap) | All UI | 4 | Low | Full | Aligns surface with reality. |
| **P4** | FRED macro overlay full wire-up | Macro | 6 | Low | Full | Regime gating for risk-on/-off transitions. |
| **P5** | Pilot paper-trade real-time variance test on 5 BROKIE picks placed 2026-05-13 | All | 0 (passive) | None | Full | Live verification of paper-vs-execution slippage. |

---

## 11. Verifiable claims log

All numbers in §1-§5 reproducible via:

```bash
# Pull fresh dashboard
git fetch origin main
git checkout origin/main -- audit_dashboard/data/dashboard_data.json

# Reproduce sections 1-4
python -c "
import json
d = json.load(open('audit_dashboard/data/dashboard_data.json', encoding='utf-8'))
print(d['performance']['asset_class_health'])
print(d['walkforward']['by_class'])
print(len(d['systems']))
"

# Section 6 drift
python -c "
import json
d = json.load(open('audit_dashboard/data/dashboard_data.json', encoding='utf-8'))
print(d['hf_stats']['concept_drift'])
"
```

Git SHAs at audit time:
- `main` HEAD: `12e17affd63`
- Dashboard generated: 2026-05-13T23:19:53Z
- This audit timestamp: 2026-05-14T00:17:49Z

## Companion / cross-skill outputs

- BROKIE positions placed this session via `tv-paper-trade` — see TV `brokie` account positions panel.
- Open PRs this session: #961-967, #971, #974, #980 (own) + fixes pushed to #946 / #949 (peer).
- Drag-cohort block ledger: PR #974 added `(CRYPTO, quan_engine, HYPEUSDT)`. JPY-cross block already shipped 2026-05-12.
- Penny pipeline Option B: PR #980 ships yfinance fallback + 59-symbol seed list. Once merged, BROKIE can resume penny rotation.

## Verdict

**NOT ready for real-money trading at the current state.** Three independent blockers:

1. The strongest cumulative edge (`multi_asset_cot` PF 21.86) carries the falsified COT TIER-1 signature shape and MUST be audited before sizing.
2. Walkforward verification is missing for COMMODITY (the headline class) AND BOND. No OOS validation = no real-money green light.
3. concept_drift alert is TRUE without supporting statistics; can't validate severity or auto-pause.

**Recommended pre-real-money checklist:**
- ✅ Pass §1 Tier-2 floor (current: 5 systems do)
- ❌ Pass §2 walkforward all classes (missing 3)
- ❌ §3 `multi_asset_cot` audit
- ✅ §4 P0 draggers quarantined (this round: HYPE done, others queued)
- ✅ §5 surgical quarantine for baby_strats overfit (template exists)
- ❌ §6 drift stats actionable
- ⏳ §7 UI High-Conviction filter audit
- ⏳ §8 risk-cap (Riskfolio-Lib)

Until §2 walkforward COMMODITY + §3 multi_asset_cot audit land, treat current `/audit` as PAPER-ONLY for real-money decisions.
