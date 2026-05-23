# CT=F Correlation Regime Cross-Check — 2026-05-12T23:19:00Z

**Spec:** Action A6 from `reports/post_concentration_action_plan_20260512T225914Z.md`,
elevated to new P0 by deepseek in 4-engine swarm review.

**Question deepseek raised:** "If CT=F correlates with SPY/QQQ >0.5 in
current regime, the entire COMMODITY edge is a beta bet, not alpha."

## Answer: CT=F is NOT a beta bet to equities

Live data from `audit_dashboard/data/correlation_regime.json` (just generated):

### CT=F (FUTURES_COT) — 30d rolling correlation with every other class

| Pair | current | baseline | Δ | flagged | just_crossed |
|---|---|---|---|---|---|
| **CT=F ↔ EQUITY (SPY)** | **+0.045** | +0.075 | -0.030 | NO | NO |
| CT=F ↔ ETF_SMALLCAP (IWM) | +0.202 | -0.076 | +0.278 | NO | NO |
| CT=F ↔ FOREX_USD (UUP) | -0.165 | -0.142 | -0.023 | NO | NO |
| CT=F ↔ CRYPTO (BTC) | -0.105 | -0.112 | +0.007 | NO | NO |
| CT=F ↔ BOND (TLT) | +0.100 | +0.003 | +0.097 | NO | NO |
| CT=F ↔ COMMODITY_GOLD (GLD) | +0.046 | +0.138 | -0.092 | NO | NO |

**Highest CT=F correlation:** +0.20 with IWM (small-cap). Still well below
the 0.5 alert threshold. **CT=F-vs-SPY = +0.045 ≈ statistically zero.**

CT=F is genuinely independent of equity beta. The cotton edge, if
`multi_asset_cot` PF=19.93 verifies, is NOT a hidden equity beta exposure.

## Where the original alarm came from

The regime sidecar flagged 5 cross-class pairs:

1. **EQUITY ↔ FOREX_USD** (SPY ↔ UUP): -0.21 → -0.77 — risk-on/dollar inverse strengthened
2. **COMMODITY_GOLD ↔ EQUITY** (GLD ↔ SPY): +0.20 → +0.77 — gold moving WITH equities (NOT diversifying)
3. **ETF_SMALLCAP ↔ FOREX_USD** (IWM ↔ UUP): -0.20 → -0.77 — same as #1, small-cap
4. **COMMODITY_GOLD ↔ ETF_SMALLCAP** (GLD ↔ IWM): +0.30 → +0.69 — gold tracking small-cap risk-on
5. **BOND ↔ ETF_SMALLCAP** (TLT ↔ IWM): +0.21 → +0.59 — bonds tracking equities (deflation regime broken)

**The class "COMMODITY" as defined by gold (GLD) is broken — gold is no longer a diversifier.**

**The class "COMMODITY" as defined by cotton (CT=F) is fine — cotton remains independent.**

This is exactly the supreme-plan + concentration-disclosure finding,
just confirmed from another angle: COMMODITY is NOT a homogeneous class.
At least two distinct factor structures inside it:

| Sub-class | Driver | Current regime status |
|---|---|---|
| **Soft commodity / agricultural** (CT=F) | Weather, USDA reports, commercial-hedger flow, COT positioning | Independent — diversifier role intact |
| **Precious metal / macro hedge** (GLD) | Risk-off, real rates, USD | **Broken — tracking equities at +0.77** |

## Implications for sizing

1. **CT=F remains a valid diversifier candidate.** Earlier "pause COMMODITY sizing"
   recommendation (deepseek) was correct AT THE CLASS LEVEL but does NOT
   apply to CT=F specifically.

2. **Gold-vehicle COMMODITY allocation IS broken.** If the COMMODITY sleeve
   has any exposure to gold/GLD/GC=F, that portion is currently a
   levered equity beta bet, not a diversifier.

3. **Per-class sizing should split COMMODITY into sub-buckets**:
   - `commodity_ag` (CT=F, KC=F, ZW=F, etc.) — keep at planned allocation
   - `commodity_metal` (GLD, GC=F, SI=F) — pause until correlation reverts

4. **No new P0.** The original A6 concern dissolves once gold and cotton
   are separated. The concentration disclosure (P0-#2) was the right
   intervention; this audit confirms its value.

## Recommendation

- Promote `correlation_regime_sidecar.py` to a daily-with-alerts model
  (already wired into `ab_analysis.yml`)
- Add sub-class split in `dashboard_generator.py` next iteration: when
  computing `asset_class_concentration` for COMMODITY, also emit
  `subclass_breakdown` keyed on {ag, metal, energy} so the dashboard
  can show "COMMODITY_AG diversifier intact / COMMODITY_METAL broken"
- Hold `multi_asset_cot` Tier-1 candidacy on DB-verification (A1)
  — the diversification thesis is now strengthened, not weakened

## NFA

Research surface only. Does not modify sizing logic. The classification
mismatch (cotton vs gold rolled into one "COMMODITY" class) is a
dashboard taxonomy choice; trade execution doesn't currently consume it.
