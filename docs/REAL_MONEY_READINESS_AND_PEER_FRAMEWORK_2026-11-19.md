# Real-money readiness + a framework peers can use to check my work

**Date:** 2026-11-19T21:10Z · **Author:** kilo
**Question this answers:** *how close are we to something worth putting real money into, and
what would you actually buy with $2,000 — a mutual fund, an index ETF, a low-fee fund, penny
stocks, or $5 stocks?*

---

## 1. Bottom line, stated plainly

**Nothing this system emits is money-ready today.** 0 proven cells, 0 candidates, 0 forward
rows for the only pre-registered equity pod, and selection alpha of **−0.276%/trade**
(CI [−0.506, −0.043]) — the picks lose to holding the same instruments.

The only real-money answer I can justify is **not** a pick from the system. It is a **low-cost
broad index fund or index ETF**, chosen on cost and diversification, with **zero edge claim**
from this repo. Everything else on the list is either contingent, experimental, or structurally
loss-making at $2,000.

## 2. The options, honestly graded

| Option | Cost | Evidence for it | Real-money verdict |
|---|---|---|---|
| **Low-cost index mutual fund** (FXAIX, SWTSX, VTSAX, VFIAX) | **0.015–0.05%** ER | Fee arithmetic + index base rates; not an alpha claim | **Yes, as a savings vehicle** |
| **Low-cost index ETF** (VOO/VTI equivalents) | ~0.03% ER | Same | **Yes, equivalent** |
| **Low-fee *active* fund** (VWELX, 0.25%) | 0.25% | Manager skill is not persistent; median active net alpha negative | Maybe — 5–16× the index fee for an unproven premium |
| **TAA / 9-month rotation** (POD-FABER-TAA) | ~2–5 bp/trade monthly | Lag-corrected Sharpe 0.82 vs SPY 0.69, MDD −20.9% vs −52.9%, **CAGR 8.9% vs 10.8%** | **Contingent**: drawdown control, not excess return; forward n=0 |
| **Our breakout pod** (POD-EQUITY-BREAKOUT) | 8 bp class slippage | 8 confirmatory cells, all WEAK, all fail 2× cost, DSR ≤0.10 | **No** — 0 forward rows |
| **Crypto intraday** | ~0.15% round trip | Class KILL (n=6,740, net −0.309%) | **No** — ~9%/month friction at $2k |
| **Penny stocks / sub-$5** | spreads often 2–10%, dilution, slippage | No fundamentals coverage here; audit PENNY n=4; no survivorship-free data | **No** |
| **$5–$20 stocks** | wide spreads, thin data | Same gaps; our equity evidence is large-cap breakout scouts | **No** |

### The specific funds (from the repo's own metadata sample)

The file `alpha_engine/data/mutual_fund_metadata_sample.json` already encodes the right screen
(index flag, expense ratio, load, 12b-1, AUM, turnover, tracking error):

| Fund | Type | Expense ratio | Load / 12b-1 |
|---|---|---:|---|
| **FXAIX** | Fidelity 500 Index | **0.015%** | 0 / 0 |
| **SWTSX** | Schwab Total Stock Market Index | 0.03% | 0 / 0 |
| **VTSAX** | Vanguard Total Stock Market Index | 0.04% | 0 / 0 |
| **VFIAX** | Vanguard 500 Index Admiral | 0.05% | 0 / 0 |
| **VBTLX** | Vanguard Total Bond Market Index | 0.05% | 0 / 0 |
| **VTIAX** | Vanguard Total International Index | 0.11% | 0 / 0 |
| **VGSLX** | Vanguard Real Estate Index | 0.12% | 0 / 0 |
| VWELX | Wellington (active balanced) | 0.25% | 0 / 0 |

**"Is a mutual fund generally good?"** The *category* is fine; the *active* subset is the
problem. A mutual fund is just a wrapper — what matters is the mandate and the fee. The
low-cost index rows above are the good ones: they are also, by construction, the "low-fee mutual
fund" the question asks about. The active fund in the sample is cheap for active but still 5–16×
the index fee, and manager persistence is weak.

**Why not penny / $5 stocks?** Three structural reasons, not opinions: (1) spreads and
market-impact dominate any realistic edge at $2k; (2) we have no survivorship-free small-cap
data and no fundamentals coverage, so we cannot even measure them honestly; (3) the audit's
PENNY class has n=4 — below every statistical floor we use. "Cheap price per share" is not a
valuation signal.

## 3. What $2,000 realistically produces

- **Index route:** market return − 0.015–0.05% fee. At a 7–8% nominal market return that is
  roughly **$140–160/year**, with normal drawdowns. No skill required, no claim from us.
- **Rotation route (if it proves):** similar return, ~half the drawdown, plus monthly
  implementation risk. The lag-corrected evidence says CAGR *trails* SPY; the value is risk.
- **Our picks:** expected negative before any skill appears (selection alpha −0.28%/trade).
- **Day trading $2k:** 9%/month friction in crypto before edge; base rates say most persistent
  day traders lose. Paper only.

## 4. Framework for peers to check my work

Apply these five tests to every claim. A claim must pass all five to be "money-ready".

| # | Test | Pass criterion | How to check |
|---|---|---|---|
| 1 | **Reproducibility** | The number can be re-derived from a committed artifact | `git show <sha>:<file>`, re-run the module, compare |
| 2 | **Population** | The claim names its population and cost model, joinable via `provenance.id` | `audit3_ledger.json → provenance`; every bucket carries `provenance_id` |
| 3 | **Multiplicity** | DSR is published with `dsr_n_trials ≥ 658` for PROVEN; BH q ≤ 0.10 | any ledger row with `dsr` but no `dsr_n_trials` is a defect (A4) |
| 4 | **Cost** | Net CI lower bound > 0 at **2× measured slippage** | `net_ci_pct_2x` / `stress_2x_ok` on every cell |
| 5 | **Forward** | The claim comes from rows dated after pre-registration, with a benchmark leg and intrabar honesty | `forward_gate` block; `reports/forward_observations.jsonl` |

**Red flags I will accept as findings:** a bucket without `provenance_id`; a DSR without a trial
count; a forward claim built from back-scored rows; a sleeve whose universe differs from the
study it cites; a test that passes when the implementation regresses.

## 5. Files to review (with SHAs)

| Artifact | Path | SHA |
|---|---|---|
| Provenance triple (A1) | `alpha_engine/audit3_tribunal.py` | `1189ff4150d` |
| DSR trial counts (A4) | `alpha_engine/audit3_tribunal.py` | `260df7f980f` |
| Forward ingest + unmatched diagnostics | `alpha_engine/forward_observations_ingest.py` | `1a36da257e2` |
| Growth watchdog (B3) | `tools/forward_growth_watchdog.py`, `.github/workflows/forward-observations-ingest.yml` | `485b4e7c1b5` |
| Sleeve engine | `paper_trading/sleeves.py`, `sleeves.json` | `57c1c0d11d2`, `6448b582fe0` |
| Sleeve spec alignment (B4) | `paper_trading/sleeves.json` | `4ec5fd7089f` |
| Surface review | `docs/AUDIT_SURFACES_FULL_REVIEW_2026-11-19.md` | on main |
| Per-class evidence | `docs/WHAT_WORKS_PER_ASSET_CLASS_2026-11-19.md` | on main |
| $2k plan | `docs/ALLOCATION_2000_AND_LIVE_SIM_PLAN_2026-11-19.md` | on main |
| This-phase plan | `docs/NEXT_PHASE_PLAN_2026-11-19.md` | on main |

## 6. My intent, stated so it can be checked

1. Make the measurement layer auditable **before** adding strategies.
2. Get exactly one pod accruing honest forward rows (EQUITY breakout) and nothing else.
3. Kill anything that cannot beat a random-entry control and 2× costs.
4. Keep $2,000 in cheap beta until a pod clears the forward gate; treat the $200 sandbox as
   tuition, not investment.
5. Say "no" in writing when the data says no — including to my own earlier claims (payload-slice
   denominator, PDT, TAA 0.88 were all corrected after review).

## 7. Questions for reviewers

1. Is the "cheap index = the only justifiable $2k answer" conclusion too conservative, or is
   there a class we can *measure* today that deserves a small allocation?
2. Is 0.015–0.05% ER truly the dominant factor for a 1–3 year horizon, or does tracking
   difference/tax dominate?
3. For the rotation sleeve: should negative-momentum slots go to **cash** or to **IEF** (bonds),
   and does either materially change the lag-corrected result?
4. Is my PENNY/$5 rejection correct given we cannot measure it, or should we build the
   survivorship-free dataset first?
5. Which of the five tests above is weakest in our current implementation?

*Not investment advice. Fund tickers are the repo's own metadata sample, shown to illustrate a
cost screen; verify current fees and suitability independently.*
