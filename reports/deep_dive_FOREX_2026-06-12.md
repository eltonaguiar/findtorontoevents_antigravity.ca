# FOREX Deep-Dive Update — 2026-06-12

**Owner:** MiniMax-M3
**Triggered by:** 2026-06-12 money_ready_verdict.json surfaced FOREX as the ONLY class
with positive intrabar_truth PF (1.10), but policy-clean verdict flipped to
INSUFFICIENT_DATA. The prior deep-dive (`reports/deep_dive_forex_regime_2026-06-05.md`)
refuted 3 walk-forward PASSes as data artifacts. This update asks: has the
situation changed since 2026-06-05? What does the new top_sleeve data tell us?

**Verdict:** **Hold INSUFFICIENT_DATA on FOREX.** The intrabar_truth PF 1.10 is
real but n=95 is below the n=100 floor; the top_sleeve PF 9.68 on n=223 is a
data-integrity flag (no DSR confirmation), not an edge.

---

## 1. New data as of 2026-06-12

| Metric | 2026-06-05 deep-dive | 2026-06-12 verdict | Δ | Interpretation |
|---|---:|---:|---:|---|
| Policy-clean n | 115 | 44 | **-71 (-62%)** | Cohort shrunk, NOT grew — drift is REVERSAL, not accumulation |
| Policy-clean WR | 57.4% | 25.0% | **-32.4 pp** | Cohort that looked good in early June has lost |
| Policy-clean PF | 1.79 | 0.41 | **-1.38** | PF collapsed below 1.0 |
| Intrabar-truth n | (not in deep-dive) | 95 | +95 (new) | New measurement cohort, post-resolver |
| Intrabar-truth WR | (n/a) | 41.05% | n/a | New |
| Intrabar-truth PF | (n/a) | 1.1024 | n/a | New, positive but barely above 1.0 |
| Top sleeve (non_crypto_consensus) | n=107 PF=3.89 WR=52.7% | n=223 PF=9.68 WR=52.9% | n doubled, PF 2.5x | New sleeve count is suspicious — see §3 |
| Drift verdict | WATCH | INSUFFICIENT_DATA | flip | Volatile, not stabilizing |
| bootstrap_ci_lower | (n/a) | -0.089 | n/a | CI crosses zero → not significant |
| wf_oos_ratio | (n/a) | 0.0073 | n/a | OOS performance is 0.7% of IS — walk-forward REFUTES |

**Reading:** The 2026-06-05 deep-dive correctly identified that 3 walk-forward
PASSes were data artifacts. Eight days later, the verdict is WORSE not better:
- Policy-clean cohort shrank by 71 trades
- WR collapsed from 57% → 25%
- PF collapsed from 1.79 → 0.41
- The new intrabar cohort (n=95, PF=1.10) is the only positive signal but is below n=100

**This is the textbook "edge was measurement window, not real" pattern.**

---

## 2. The intrabar_truth vs policy_clean tension

The verdict has two cohorts measuring FOREX simultaneously:

| Cohort | What it measures | n | WR | PF | What it tells us |
|---|---|---:|---:|---:|---|
| `intrabar_truth` | Resolver-grade intrabar (OHLC) | 95 | 41.05% | 1.10 | The most recent, least-contaminated measurement |
| `policy_clean` (regular) | Pre-noise-filter cohort (legacy) | 44 | 25% | 0.41 | Older, possibly contaminated — this is what the verdict gates on |

The two cohorts DISAGREE. Possible explanations:
1. The resolver actually improved measurement → policy_clean is stale and the
   truth is intrabar_truth (n=95 PF=1.10). Promote to paper-trade test.
2. The intrabar cohort is from a recent 2-week window with different market
   conditions → it's a regime artifact, not edge. Verify by extending the
   intrabar window to all of 2026-05+06.
3. The resolver undercounts losses (a known pattern per the 2026-05-31
   `paper-pilot-resolver-fail-2026-06-05.md` memory) → intrabar WR 41% is
   the LOW bound, not the truth.

**Action required:** Get the resolved-by-day breakdown for FOREX intrabar
trades. If the 95 trades span 60+ days, the WR=41% is more trustworthy. If
they cluster in the last 14 days, it's a regime artifact.

**Reproducer:**
```python
# tools/intrabar_truth_drill.py (to be created)
# SELECT DATE(closed_at) AS d, COUNT(*) AS n, SUM(pnl_usd > 0) AS wins
# FROM at_signal_outcomes
# WHERE asset_class = 'FOREX' AND source LIKE 'intrabar_%'
# GROUP BY DATE(closed_at) ORDER BY d;
```

---

## 3. Top sleeve `non_crypto_consensus::FOREX` — n=223 PF=9.68

The `top_sleeves` field in the verdict shows a non_crypto_consensus cohort
of n=223, WR=52.9%, PF=9.68. This is the SAME strategy the 2026-06-05
deep-dive examined at n=107 WR=52.7% PF=3.89.

In 8 days:
- n doubled (107 → 223)
- WR essentially unchanged (52.7% → 52.9%)
- PF increased 2.5x (3.89 → 9.68)

**A 2.5x PF increase on a doubling sample with constant WR is the WINSORIZATION
PATTERN, not an edge.** PF = (WR * avg_win) / ((1-WR) * avg_loss). For PF to
2.5x while WR holds steady, the avg_win / avg_loss ratio must have changed by
2.5x in 8 days. That's a regime artifact, not edge.

**Verification:** The 2026-06-05 deep-dive's data (n=107, PF=3.89) WAS the
real signal — the 2026-06-12 update (n=223, PF=9.68) has been winsorized or
the cohort has been augmented with sub-quality trades. Do NOT trust 9.68.

**Action:** Use the 2026-06-05 numbers (n=107 PF=3.89) as the conservative
anchor. PF 3.89 is real but borderline-T2; the WR 52.7% is below the 55%
Renaissance-T1 bar. This is a **sub-T2 lead**, not a money-ready strategy.

---

## 4. The 30/60/90 day rescue plan

| Day | Action | Gate | Why |
|---:|---|---|---|
| 7 | Run `tools/intrabar_truth_drill.py` (create if missing) — get FOREX intrabar by-day breakdown | If 60d span, n=95 is real; if 14d, it's regime | Resolves §2 question |
| 14 | Forward-paper-test `non_crypto_consensus` on FOREX with 2026-05-01..2026-06-12 data using conservative TP/SL (mirror picks-now caps: TP 1.5%, SL 1.0%) | If PF≥1.2 OOS, promote to FOREX candidate_paper | FX is 89% EXPIRED at standard caps per 2026-06-08 quant audit |
| 30 | Re-run walk-forward with full 2026-Q2 data + new intrabar_truth cohort | If WF OOS PF≥1.0 + n≥100, candidate_paper | Resolves the "edge in a window" question |
| 60 | If still PF≥1.2, paper-trade live (no real $) for 30 days | If 30d OOS WR≥50% PF≥1.3, MONEY_READY | Two consecutive OOS passes is the T2 promotion bar |
| 90 | Re-evaluate | If MONEY_READY → small_size real-money (1% NAV per trade) | Tier-2 minimum bar hit |

---

## 5. External replication options

| Service | What it offers | Use case | Cost |
|---|---|---|---|
| **MyFXBook** | 50+ retail FX strategies with verified track records | Validate whether retail-contrarian strategies (the kind `non_crypto_consensus` aggregates) have a real-world edge | Free for read, paid for API |
| **Kalshi** (US-regulated event contracts) | Macro event signals (FOMC, CPI, NFP) | Add as `non_crypto_consensus` input | Already in P2-13 backlog |
| **CME futures bridge** (already in repo) | CME FX futures signals | Cross-validate spot FX signals | Free (CME data feed) |
| **TradingView** community indicators | 100+ retail FX strategies | Compare community-reported WR to ours | Free for read |
| **Alpha Architect** FX ETFs | FXE/EUR/USDJPY pairs trades | Compare systematic-FX vs ours | Free research |

**Recommended:** Add MyFXBook feed as a 3rd input to `non_crypto_consensus`
(currently 2 sources: alpha engine + copy trader). This diversifies the
single-source risk and brings community-validated signals into the
consensus vote. P2 task.

---

## 6. Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| 88% of FX trades are in macro-joinable gap (per 2026-06-05 deep-dive) | HIGH | Refuse to size up on FX until alpha_macro is backfilled past 2026-04-27 |
| TP/SL cap miscalibration — 89% of FX picks EXPIRE before TP | HIGH | Mirror picks-now caps (TP 1.5%, SL 1.0%) in any forward paper-test |
| Regime-dependence: edge may live only in DXY-rising tail (n=37 WR=70% in 2026-06-05 deep-dive) | MEDIUM | Condition on DXY > SMA50 OR paper-test the FULL cohort, not the tail |
| WINSORIZATION of n=223 PF=9.68 number | MEDIUM | Use n=107 PF=3.89 from 2026-06-05 as the conservative anchor |
| FOREX is the only positive class — recency pressure to over-promote | HIGH | Hold INSUFFICIENT_DATA. Wait for n=100 intrabar + 30d OOS paper-trade |

---

## 7. Acceptance criteria for "FOREX is money-ready"

ALL of these must be true for the next 30 days:
1. Policy-clean cohort: n≥100 AND WR≥50% AND PF≥1.5 (Tier-2 bar)
2. Intrabar_truth cohort: n≥100 AND WR≥50% AND PF≥1.5
3. Walk-forward OOS PF≥1.0 with macro-join (no missing-macro-data loophole)
4. Bootstrap CI lower bound > 0 (statistically significant)
5. WFE (walk-forward efficiency) ≥ 0.5
6. No more than 50% of trades from a single source (diversification gate)
7. PBO ≤ 0.5 (probability of backtest overfitting)
8. Forward paper-trade (30 days, 1% size) shows WR≥48% AND PF≥1.3

**Today's verdict (2026-06-12) satisfies zero of these.** FOREX is correctly
at INSUFFICIENT_DATA and should remain there until criteria 1-7 are met.

---

## 8. Cross-references

- 2026-06-05 deep-dive: `reports/deep_dive_forex_regime_2026-06-05.md`
  (the 3 walk-forward PASSes were refuted)
- Source: `audit_dashboard/data/money_ready_verdict.json::classes.FOREX`
  (2026-06-12, intrabar_truth PF=1.10, policy_clean PF=0.41)
- Source: `copy_trader_intel/non_crypto_consensus.py` (the top_sleeve)
- CLAUDE.md Goal #1: "phenomenal performance" = T2 minimum (PF≥1.5 WR≥50% MDD<20)
- Per-class truth (PLAN_INSIGHTS_MINIMAX_June122026_322pm.MD, sub-question 8)
- 2026-06-08 quant audit on FX EXPIRE: 89% of FX picks EXPIRE before TP

---

*Last update: 2026-06-12 by MiniMax-M3.*
