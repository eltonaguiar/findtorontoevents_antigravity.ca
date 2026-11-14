# Notes — Verdict: multiple-testing & survivorship, addressed directly

**Verdict: NOT profitable and NOT statistically sound. The performance is overwhelmingly an
artifact of running a very large strategy universe.**

## A. Multiple testing — quantified
| Quantity | Value | Source |
|---|---|---|
| Core strategy families | 361 | `alpha_engine/config.py` STRATEGY_FAMILIES |
| Baby strategy files | 285 | `baby_strategies/` |
| Total candidate universe | **646** | sum |
| Distinct strategies in live 3,500-row window | 114 | `.picks.recent_closed` |
| Distinct source systems | 15 | same |
| Expected PF>1.3 "winners" by chance at p=5% | **32** (of 646) / 18 (of 361) / 6 (of 114) | binomial expectation |
| Strategies flagged OVERFIT_LIKELY | **69 / 80 (86%)** | `live_anti_overfit_audit.json` 14:22Z |
| PBO observations | 21 (statistically meaningless) | same |
| White Reality Check | **never ran** (missing `arch` pkg) | same |

## B. Break-even test on adequate samples (n≥100)
Only **4** strategies have n≥100 in the live window:

| Strategy | n | WR | PF | z vs coin-flip |
|---|---|---|---|---|
| rs-breakout-scout | 133 | 53.4% | 1.65 | **0.78** |
| luxalgo_confluence | 1,284 | 43.0% | 1.13 | **−5.02** |
| momentum-factor | 105 | 48.6% | 1.06 | −0.29 |
| intermarket-flow-scout | 104 | 47.1% | 1.06 | −0.59 |

**Strategies passing n≥100 + PF>1.3 + z>1.96: ZERO.**
The one with the best PF (rs-breakout-scout) has z=0.78 — indistinguishable from luck.
The largest sample (luxalgo_confluence) is *significantly worse* than a coin flip.

## C. Survivorship — direct
- Positive cells exist only at n=15–19 (EQUITY/ETF 7d) and vanish by 30d (PF 3.63 → 0.84; 3.21 → 0.72).
- Duplicate re-emissions inflate counts without adding information: 2,262 `inverse_mutations`
  re-emissions; 129 dedup-key collisions; 3,872 spot-flicker zero-delta rows dropped from 28,719.
- 75 duplicate re-emissions dropped in the June registry; 99 `FORCE_CLOSED_TOXIC` exits.
- `prediction_market_agents` shows PF 44.24 at n=135 yet FAILS 3 of 5 scrutiny axes (concentration,
  batch-artifact, binomial) — a textbook survivorship/selection artifact.
- The one survivor of *both* peer review and my independent check: **`mega_mutation`** (PF 3.16–3.20,
  WR 64–72%). Even this is n≈18–295, so it is a *pilot candidate*, not a proven edge.

## D. The system's own verdicts (cannot be dismissed as auditor bias)
- `audit_surface_truth.json`: "**0/9 asset classes money-ready** on policy-clean closed picks.
  Do not size on Smart Picks / tournament / leaderboard inflated WR."
- `money_ready_verdict.json`: `pf_ok = False` for **every** class.
- `PAPER_PILOT_RESOLVER_FAIL_2026-06-05.md`: intrabar replay reclassified **28%–100%** of "TP hits"
  as actual SL hits → the historic WR/PF numbers were inflated by `NOMINAL_TP_LEGACY`.

## E. Why the page can look profitable anyway
1. Curated top layer: `.picks.active` (10–20 rows, fresh) is displayed; `.picks.active_raw`
   (4,164 rows, 79% zombies) is not.
2. 81% of visible open picks carry 0% P/L, which reads as "flat" rather than "losing"
   (true mean −1.80%; real aggregate −1,116pp vs claimed −106pp).
3. Display-tier styling implies edge independently of statistics (peer: `display_tier='ELITE'`
   cascade at `template.html:8786` renders "golden" rows for n=1 cohorts).
4. 646 strategies guarantee some cells look excellent by chance; the dashboard surfaces those.

## F. What would change the verdict
- Achieve n≥100 on intrabar-truth resolution for a class and show PF>1.3 with z>1.96.
- Only `mega_mutation` is on that path today; it needs a forward ledger with n≥100 to certify.
