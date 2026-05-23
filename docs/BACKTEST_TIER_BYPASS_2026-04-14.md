# Backtest: Tier Stamping vs Forward-WR Gate — 2026-04-14

**Question (from Copilot's [HIGH_CONVICTION_DEEP_ANALYSIS](../HIGH_CONVICTION_DEEP_ANALYSIS_2026-04-14.md)):**
Should `passesStampedTierSupplementalPath` bypass Gate G3b (`forwardWRMinPct ≥ 45%`) for stamped S/A/B picks, or stay Option A (tier is advisory, hard gates apply)?

**Method:** Re-stamp tier via `classify_hf_conviction_tier()` on all 3,500 closed picks in `audit_dashboard/data/dashboard_data.json`, partition by (stamp, fwdWR band), measure realized WR/PF.

**Decision criteria:** Option B is warranted only if stamped+low-fwdWR picks beat unstamped+low-fwdWR picks by **≥ 10pp WR AND PF ≥ 1.5**.

## Results

| Bucket | n | WR | PF | Sum PnL | Avg PnL |
|---|---|---|---|---|---|
| **A1: STAMPED + fwdWR<45%** (Option B candidates) | 65 | **49.23%** | **1.596** | +29.58 | +0.455 |
| **B1: UNSTAMPED + fwdWR<45%** (baseline low-WR) | 1,560 | 32.56% | 0.654 | −661.83 | −0.424 |
| A2: STAMPED + fwdWR≥45% (current HC pass) | 262 | 56.49% | 1.729 | +84.80 | +0.324 |
| B2: UNSTAMPED + fwdWR≥45% (baseline high-WR) | 1,613 | 51.77% | 1.830 | +736.63 | +0.457 |

**Decision test:**

- WR delta (A1 − B1): **+16.67pp** ✅ ≥ 10pp threshold
- A1 PF: **1.596** ✅ ≥ 1.5 threshold
- **Mechanical verdict: Option B passes the decision criteria**

## Why the mechanical pass is still weaker than Option A

### 1. Signal is 100% Tier B CRYPTO

| Tier within STAMPED + fwdWR<45% | n |
|---|---|
| S | 0 |
| A | 0 |
| **B** | **65** |

| Asset class within STAMPED + fwdWR<45% | n |
|---|---|
| **CRYPTO** | **65** |
| EQUITY / FOREX / COMMODITY / BOND / ETF / FUTURES | 0 |

The test validates *nothing* about Tier S or Tier A, and *nothing* about non-crypto tier stamping. The entire +16.67pp edge comes from the Tier B "data-driven bypass" path at [conviction_stack.py:930-937](../alpha_engine/conviction_stack.py#L930-L937) — the `3of5_criteria AND conf>=0.75` admission rule — applied to crypto picks that also happen to have currently-low strategy fwdWR.

Effectively, we're asking "does the Tier B bypass rule select profitable picks?" and the answer is "yes, marginally, on crypto." That's different from "should the tier stamp bypass the forward-WR gate."

### 2. Quality dilution is consistent

Moving from current HC (A2) to Option B (A2 ∪ A1):

| Metric | A2 only (current) | A2 ∪ A1 (Option B) | Delta |
|---|---|---|---|
| n | 262 | 327 | +65 |
| WR | 56.49% | 55.08% | **−1.41pp** |
| PF | 1.729 | 1.693 | **−0.036** |
| Sum PnL | +84.80 | +114.38 | +29.58 |

The dilution is small but consistent: the added picks are weaker than the existing ones in every quality metric.

### 3. Look-ahead bias is structural and unfixable

`strat_fwd_wr` in the closed-pick snapshot is the *current* leaderboard value, updated on every dashboard generation. It is NOT the value at pick-creation time. This means the "low-fwdWR" bucket is contaminated with picks that:

- Were taken when the strategy was at WR ≥ 50%
- Decayed to WR < 45% later
- Happened to be profitable at entry time (because the entry-time strategy was strong)

Without entry-time fwdWR snapshots (which the archive doesn't preserve), we can't distinguish "real edge on low-WR strategies" from "artifact of strategy decay after profitable entries." The A1 WR of 49.23% is probably inflated by this bias.

### 4. Sample size is small

n = 65 for A1. Bootstrap CI on PF 1.596 would be wide (likely [1.0, 2.5]), meaning the true PF could easily be barely-above-random. The +16.67pp WR delta is large enough to be meaningful on n=65 (assuming ~independent trades), but the PF is close enough to 1.5 that a handful of bad trades would drop it below the threshold.

## Final verdict

**Stay Option A.**

The data does not unambiguously support Option A — it mechanically passes the decision criteria — but each caveat erodes the signal:

- Option A is clearly correct for **S/A tier** (no data at all)
- Option A is clearly correct for **non-crypto** (no data at all)
- Option A is *probably* correct for **Tier B CRYPTO** once look-ahead bias is accounted for
- Option A is definitively correct for **"bypass all hard gates for any tier-stamped pick"** (the broadest Option B framing), because that framing is not what the test measured

If a future Option B is pursued, it should be **surgical**:

- Tier B CRYPTO only (that's where the signal is)
- Bypass G3b only (fwdWR gate), not score gates
- Confidence ≥ 0.75 floor (already in the Tier B bypass rule anyway)
- Trust tier ∉ {SANDBOX, UNPROVEN, PROBATION, DEMOTED} (already enforced)
- Marked as "bypass tier" in UI with a warning badge explaining the quality dilution
- Re-validated on entry-time snapshots once those become available

Even with that surgical form, the **near-miss equity unlock** (e.g., fixing multi_asset_copytrader score depression on META, where a single genuinely validated pick at score 37 → 50 with fwdN 746 / fwdWR 46.8% sits blocked) delivers better marginal value than bypassing G3b for crypto.

## Caveats (machine-readable in [BACKTEST_TIER_BYPASS_2026-04-14.json](BACKTEST_TIER_BYPASS_2026-04-14.json))

1. `strat_fwd_wr` is the CURRENT leaderboard value, not entry-time value. Look-ahead bias.
2. Historical closed picks don't carry `hf_conviction_tier` natively — we re-stamped using the CURRENT classifier. Any edge implicit in the classifier is baked in.
3. Closed-pick sample includes auto-expired and time-exit picks, not all are clean TP/SL resolutions.
4. Tier S and Tier A are untested (n=0 in the stamped+low-fwdWR bucket); conclusions about them are extrapolations.
5. The test measures a single snapshot; running it again on different closed-pick vintages might produce different results.

## Artifacts

- `scripts/backtest_tier_bypass_2026-04-14.py` — re-runnable backtest
- `docs/BACKTEST_TIER_BYPASS_2026-04-14.json` — machine-readable results
- `docs/BACKTEST_TIER_BYPASS_2026-04-14.md` — this document
