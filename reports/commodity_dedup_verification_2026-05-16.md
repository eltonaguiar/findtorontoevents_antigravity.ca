# COMMODITY Post-Dedup Stats Verification — 2026-05-16

**Purpose:** Verify whether PR-#994 COT-dedup has been applied before any Tier-1 claim
is made on COMMODITY headline metrics.

## Findings

- **Current `asset_class_health.COMMODITY` (production verdict-grade):** n=347, WR=61.4%,
  PF=2.52 — this is the *headline* number. It includes `multi_asset_cot` picks which carry
  a documented over-emission artifact (see below).

- **`hf_stats.by_asset_class.COMMODITY` (recent-window subset, n=74):** PF=2.26, WR=54.1%,
  MDD=49.2%. The MDD of 49.2% exceeds Tier-1 MDD ceiling (10%) and even Tier-2 ceiling
  (20%). This window is NOT Tier-1 quality on risk-adjusted basis.

- **`multi_asset_cot` system (primary COMMODITY driver):** n=130 resolved picks, WR=79.2%,
  PF=4.65, MDD=79.97% — but **`toxic_concentration=true`** (94.3% of PnL from single symbol
  CT=F) and **listed in `REQUIRES_WALKAHEAD_AUDIT`** per `quality_gates.py` lines 1706-1711.
  The audit note states: "PF=21.86 from 102 trades on only 5 unique CFTC weekly releases.
  Over-emission artifact (20:1 ratio). After 1-pick-per-cycle dedup: WR=40%, PF=0.17,
  PnL=-2." The current n=130 figure in the dashboard represents post-pipeline growth but
  the dedup question remains open.

- **PR-#994 COT-dedup status: NOT CONFIRMED APPLIED.** `git log -- audit_trail/dashboard_generator.py`
  shows no commit referencing PR-#994. Grep for "PR.994", "PR #994", "cot_dedup" across
  `audit_trail/` and `audit_dashboard/` returns zero matches. The dedup logic has NOT landed.

- **T1 claim safety verdict: NOT SAFE.** COMMODITY at PF 2.52 / WR 61.4% / n=347
  *appears* to meet Tier-1 thresholds on win-rate and PF, but: (a) the dedup that would
  remove over-emitted COT picks has not been confirmed applied; (b) `multi_asset_cot` is
  flagged in `REQUIRES_WALKAHEAD_AUDIT` and shows 94.3% single-symbol concentration;
  (c) the recent-window MDD (49.2%) is 5× the Tier-1 MDD ceiling. Until PR-#994 lands and
  walk-forward audit of `multi_asset_cot` completes with OOS data, **do not promote COMMODITY
  to Tier-1**.

## Required Next Steps (before any T1 claim)

1. Implement and merge PR-#994: 1-pick-per-CFTC-cycle dedup in `multi_asset_cot` pipeline.
2. Re-run `dashboard_generator.py` and confirm post-dedup n, WR, PF.
3. Walk-forward audit of `multi_asset_cot` (train pre-2025, test 2025+) per
   `REQUIRES_WALKAHEAD_AUDIT` gate — OOS PF must exceed 1.5 for Tier-2, 2.0 for Tier-1.
4. Address CT=F single-symbol concentration (94.3%) before sizing up.
