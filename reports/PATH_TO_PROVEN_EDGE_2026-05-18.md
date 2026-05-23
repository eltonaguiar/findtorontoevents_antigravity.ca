# Path to Proven Statistical Edge — 2026-05-18

**Read with `reports/EDGE_VERDICT_2026-05-18.md`.** That doc is the stop-sign;
this doc is the forward plan. Honest framing: **there is no proven edge today.**
This is the gated route to one — or to a defensible "no edge exists" conclusion.

## Where we are (measured, not guessed)

- Existing pick ledger: ~29% WR, PF ~0.74 net. All 7 pipeline scores fail
  `tools/edge_stability_harness.py` walk-forward. `elite_score` eff 0.06.
- **Fork 1 (feature-backfill, PR #1206)** — enriched the ledger with qlib
  factors + recomputed regime (98.2% coverage). All 4 candidates REJECTED.
  `qlib_pv_corr30` reproduced the `method_a_score` sign-flip. **The in-house
  ledger sweep is now honestly exhausted.**
- **Fork 2 (new signals, PR #1206)** — 3 converged cloud-harvest candidates.
  0/3 cleared the harness. H-007 COMMODITY roll-yield genuinely FAILED
  (sign-unstable). H-006 CRYPTO funding-rate and H-008 BOND 2s10s were
  initially **UNTESTED** — free data too thin per harness window.
  **UPDATE 2026-05-18 (later): all three are now cleanly tested + REJECTED**
  on deep samples — see "Update" section at the bottom of this doc.

## The standing rule (unchanged)

No score ranks or gates picks, and no pick is sized with real money, until it
clears `edge_stability_harness.py`: **eff ≥ 0.30, same sign, ≥3 of 5
walk-forward windows.** DSR / SPA / White's pass is necessary, nowhere near
sufficient — all three passed `cot_positioning`, a leakage artifact.

## The path — prioritized, gated

### P1 — Make H-008 (BOND 2s10s) testable. NOT a data problem.
FRED DGS2/DGS10 has 40+ years of daily data. Fork 2 only failed to render a
verdict because the 2s10s slope moves slowly, so discrete signal events cluster
and the harness scored <3 windows. Fix is backtest *design*, not data:
treat it as a **continuous-position** strategy (daily mark-to-market of a
slope-momentum book) instead of discrete picks, or use overlapping windows /
multiple bond instruments (ZN/ZB/ZF) for cross-sectional breadth.
→ Re-runnable now; lowest cost; clean verdict achievable this week.

### P2 — Make H-006 (CRYPTO funding-rate) testable. Data-archive problem.
Free Binance funding history caps ~333 days; the harness needs ≥80 events per
14-day window. Two routes, run both:
- **(a) Start a daily funding-rate collector now** (`tools/`-side cron) so the
  archive deepens passively — every week of delay is a week of lost sample.
- **(b) Pull a longer free archive** — Coinglass / CoinMetrics community tier
  carry multi-year funding history. Validate licence terms first.
→ Then re-run H-006 through the harness once ≥2 years of funding data exist.

### P3 — COMMODITY: H-007 is dead. Try ONE term-structure variant or stop.
Roll-yield z-score is sign-unstable — killed. A single defensible retry:
inventory-surprise (EIA/USDA) interacted with roll yield (the DeepSeek/xAI
variant). Pre-register as H-009 first. If it also fails the harness, COMMODITY
edge hunt is closed.

### P4 — EQUITY / ETF: pre-register before touching data.
PEAD (post-earnings-announcement drift, SUE-based) and 12-1 cross-sectional
momentum are the academically-grounded candidates (MASTER_ACTION_PLAN §29).
Each needs: ex-microcap universe, 100bps slippage, CPCV by quarter. Pre-register
as H-010/H-011. These are multi-day builds — queue after P1/P2.

### P5 — FOREX: stays disabled. No retry. (Unanimous across all rounds.)

## What "ready for real money" means here

The user's ask — be *ready* for real money without deploying it yet — maps to:
1. A signal that **clears `edge_stability_harness`** (the gate above). Today: none.
2. Then ≥4 weeks **paper-traded** (TradingView paper, $200–$1000 sandbox) with
   non-negative CLV and post-cost expectancy > 0.
3. Then, and only then, a real-money sizing decision — a user call.

Until step 1 passes for at least one class, "proven edge picks per asset class"
do not exist to hand over. The deliverable right now is the *gated pipeline*,
not picks. P1 (H-008 redesign) is the fastest shot at the first harness pass.

## Update 2026-05-18 (later) — P1 & P2 resolved, both REJECTED

The P1/P2 plan above is now executed. Result per `reports/hypothesis_registry.json`
(`fork2_new_signals`):

- **P1 — H-008 BOND 2s10s.** Redesigned exactly as planned: a continuous-position
  daily mark-to-market book. `tools/new_signal_research.py` gained
  `research_bond_continuous()` — 4 Treasury futures (ZN/ZB/ZF/TU) × a {1,2,3}-day
  holding-horizon ladder → ~120 resolved records per 14-day window, clearing the
  harness `MIN_WINDOW_N=80` density floor (design verified by 3 new network-free
  leakage tests). The deep retest scored a real verdict on **n=57,117** records:
  **REJECTED — tested, sign-unstable (regime noise).** No longer UNTESTED — a
  clean fail. The slope-momentum signal has no durable, sign-stable edge.
- **P2 — H-006 CRYPTO funding-rate.** The "free data too thin" diagnosis was a
  pagination bug, not a true archive limit: `/fapi/v1/fundingRate` caps 1000 rows
  *per request*, not in total. The P2 deep retest paginated the full ~6-year
  history (10 perps, **n=4,838** events): **REJECTED — sign-unstable.** A daily
  `tools/funding_rate_collector.py` + workflow was still added (P2a) so the
  archive deepens passively for any *future* funding-derived hypothesis — but
  H-006 itself is closed.
- **P3 — H-007 COMMODITY roll-yield.** Already dead (n=2,964, sign-unstable).

**Net:** Fork 2's three converged cloud-harvest candidates are now **0/3 — all
cleanly REJECTED**, not untested. Consistent with the EDGE_VERDICT base rate:
rigorous leakage-controlled testing keeps returning "no admissible edge". The
harness is doing its job — rejecting non-edges, exactly what a real-money gate
must do.

**Forward path is unchanged but now narrower.** The remaining shots are the
academically-grounded, not-yet-tested candidates: H-009 (COMMODITY
inventory-surprise × roll yield), H-010/H-011 (EQUITY/ETF PEAD + 12-1
cross-sectional momentum). Each must be pre-registered before any backtest and
must clear `edge_stability_harness` to be admissible. Until one does, Fork 3
(paper-only default) stays in force.

## Note on the MiMo (Xiaomi) review — do not action

The MiMo response of 2026-05-18 explicitly **could not fetch /audit** and
reasoned only from stale prompt-supplied numbers (the 2026-05-03
`asset_class_health` snapshot). Its top finding — the "R:R [1.5,2.0] PF 5.81"
band — is the `risk_reward` candidate **already killed in EDGE_VERDICT**
(leakage-control → n=17, −3%/pick; walk-forward flips sign every window).
This is the multi-AI convergence trap: an agent re-deriving a "finding" from
stale input is not independent verification. No action.
