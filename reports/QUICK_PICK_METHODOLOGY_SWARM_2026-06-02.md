# Quick-Pick & Long-Term Methodology — 15-Round AI Swarm Refinement

**Date:** 2026-06-02 · **Orchestrator:** Claude Opus 4.8 · **Panel (rotating):** nvidia-deepseek-v4-pro, deepseek-chat-direct, paid-mode-large, hybrid-model-large, cloudflare-llama, ollama-cloud-local · **Rounds:** 15

> Methodology design via iterative multi-model refinement. Opinion/process design, not backtested edge. Per-round changelog at the end.

## FINAL METHODOLOGY (round-15 draft)

# Quick-Pick & Long-Term Methodology (DRAFT v10)

Covers QUICK-PICK (fast, consensus-only) and LONG-TERM (multi-year hold) selection for five asset groups.

## Quick-Pick Rules (per group)

**STOCKS**
* **Signals:** Bloomberg consensus EPS revisions (30d); 13F top-50 hedge fund ownership; Morningstar moat (narrow/wide); Institutional Investor All-America Executive Team rank ≥ 10.
* **Thresholds:** Market cap ≥ $100B; P/E ≤ 25; ROIC ≥ 15% (TTM); analyst count ≥ 5; top-50 hedge fund ownership ≥ 2% of float; insider ownership ≥ 5%.
* **Sizing:** Equal-weight top 10; max 5% per name; max 20% sector.
* **Rebalance:** Quarterly.
* **Avoid:** Negative EPS revisions (30d); insider selling >0.1% float (90d); SEC inquiry/restatement; dividend cut (3yr).

**ETFs**
* **Signals:** Morningstar category; AUM ≥ $5B; expense ratio ≤ 0.10%; bid-ask spread ≤ 0.05%; FactSet Index Performance Attribution (IPO ≥ 10%).
* **Thresholds:** Holdings: 500 (US), 200 (intl), 50 (fixed income); turnover ≤ 50%; tracking error ≤ 0.5% annual.
* **Sizing:** Single ETF up to 20%; max 10% sector.
* **Rebalance:** Quarterly.
* **Avoid:** Leveraged/inverse; AUM < $1B; overlap >50%.

**BONDS**
* **Signals:** U.S. Treasury yield curve; short-duration T-bills (≤1yr); IG corporate bonds (A-rated min); Bloomberg Barclays Aggregate Bond Index yield spread ≥ T-bill + 50bps.
* **Thresholds:** Duration ≤ 2yr (T-bills); yield spread ≥ T-bill + 50bps (A-rated); maturity ≤ 5yr (corporates); credit rating ≥ A-.
* **Sizing:** 50% T-bills, 50% short IG ladder; max 20% sector.
* **Rebalance:** Monthly.
* **Avoid:** Rating < A-; high-yield; duration >10yr; negative real yields; inverted curve >6 months.

**FUTURES**
* **Signals:** SG CTA Index (12m rolling); 12-month momentum per contract (Gold, Crude, S&P 500, 10yr Treasury); Bloomberg Commodity Index (BCOM) 12-month momentum > 0.
* **Thresholds:** Max 5% per contract; SG CTA Index > 0 (12m).
* **Sizing:** Managed-futures ETF (e.g., DBMF) as proxy; 10% total allocation.
* **Rebalance:** Quarterly.
* **Avoid:** Momentum flat/negative; SG CTA Index shows broad negative trend.

**COMMODITIES**
* **Signals:** Gold spot (XAUUSD); BCOM Index; Bloomberg Commodity Index (BCOM) 12-month momentum > 0.
* **Thresholds:** Max 5% gold ETF, max 5% broad-basket ETF.
* **Sizing:** Max 10% sector.
* **Rebalance:** Semi-annually.
* **Avoid:** Both momentum filters negative → 0% allocation.

## Long-Term Rules (per group)

**STOCKS**
* **Signals:** ROIC (≥20% 5yr avg); Debt/EBITDA ≤ 1.5x; Revenue Growth ≥ 8% CAGR (5yr); FCF Reinvestment Rate ≥ 50%; Institutional Investor All-America Executive Team rank ≥ 10.
* **Thresholds:** Market cap ≥ $10B; P/FCF ≤ 30; insider ownership ≥ 5%; ROE ≥ 15%; analyst count ≥ 10; dividend growth ≥ 5% (5yr).
* **Sizing:** 15-20 names; equal-weight; max 10% sector.
* **Rebalance:** Annually.
* **Avoid:** Dividend cut (3yr); SEC inquiry/restatement; negative FCF (3yr avg); institutional ownership <5%.

**ETFs**
* **Signals:** Dual-momentum (6m/12m relative strength); factor tilt (value/quality); FactSet Index Performance Attribution (IPO ≥ 10%).
* **Thresholds:** Expense ratio ≤ 0.20%; AUM ≥ $1B; factor z-score > 0.5; track record ≥ 3yr; turnover ≤ 50%.
* **Sizing:** 3-5 ETFs; 20% each; max 10% sector.
* **Rebalance:** Semi-annually.
* **Avoid:** Track record < 1yr.

**BONDS**
* **Signals:** U.S. Treasury yield curve (10yr-2yr spread); Bloomberg Barclays Aggregate Bond Index yield; IG corporate bond yield spread (A-rated min).
* **Thresholds:** Duration ≤ 5yr; credit rating ≥ A-; yield spread ≥ T-bill + 100bps; maturity ≤ 10yr.
* **Sizing:** 40% T-bills, 60% IG corporate ladder (5-10yr); max 20% sector.
* **Rebalance:** Semi-annually.
* **Avoid:** Rating < A-; high-yield; duration >10yr; negative real yields; inverted curve >12 months.

**FUTURES**
* **Signals:** SG CTA Index (12m rolling); 12-month momentum per contract (Gold, Crude, S&P 500, 10yr Treasury); Bloomberg Commodity Index (BCOM) 12-month momentum > 0.
* **Thresholds:** Max 5% per contract; SG CTA Index > 0 (12m).
* **Sizing:** Managed-futures ETF (e.g., DBMF) as proxy; 15% total allocation.
* **Rebalance:** Semi-annually.
* **Avoid:** Momentum flat/negative; SG CTA Index shows broad negative trend.

**COMMODITIES**
* **Signals:** Gold spot (XAUUSD); BCOM Index; Bloomberg Commodity Index (BCOM) 12-month momentum > 0; supply

---

## Round-by-round changelog

- R1 [nvidia-deepseek-v4-pro]: FAIL timed out
- R2 [deepseek-chat-direct]: Added concrete numeric thresholds, signal sources, and when-to-avoid rules for all five asset groups in both modes; introduced position sizing and rebalance cadence.
- R3 [paid-mode-large]: (no changelog parsed)
- R4 [hybrid-model-large]: Refined numeric thresholds for greater specificity across all asset classes and modes.
Introduced concrete signal sources for Futures and Commodities in Quick-Pick, and clarified Long-Term Futures sig
- R5 [cloudflare-llama]: - Improved signal sources and numeric thresholds for each asset group in both Quick-Pick and Long-Term modes.
- Added concrete rules for position sizing, rebalance cadence, and when-to-avoid rules for
- R6 [ollama-cloud-local]: (no changelog parsed)
- R7 [nvidia-deepseek-v4-pro]: FAIL HTTP Error 429: Too Many Requests
- R8 [deepseek-chat-direct]: (no changelog parsed)
- R9 [paid-mode-large]: (no changelog parsed)
- R10 [hybrid-model-large]: Completed the truncated FUTURES section and standardized the COMMODITIES long-term rules to ensure consistent risk-management across all asset classes.
- R11 [cloudflare-llama]: - Improved signal sources and numeric thresholds for all asset groups in both modes.
- Added concrete examples and clarified rules for position sizing, rebalance cadence, and when-to-avoid rules.
- R12 [ollama-cloud-local]: **CHANGelog:** Added concrete signal sources and numeric thresholds for each group; clarified position sizing and rebalance cadence rules.
- R13 [nvidia-deepseek-v4-pro]: FAIL HTTP Error 429: Too Many Requests
- R14 [deepseek-chat-direct]: Added concrete signal sources and numeric thresholds for Futures and Commodities in both modes; tightened Quick-Pick bond yield spread and duration bands; fixed missing Long-Term rules for Bonds, Futu
- R15 [paid-mode-large]: (no changelog parsed)
