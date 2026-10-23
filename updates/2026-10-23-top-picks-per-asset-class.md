# Top Picks per Asset Class — Merged Report (2026-10-23)

**Agents consulted:** INCEPTION, OpenCode BEAM, Grok, GHCopilot, Poolside/KiloCode, Buffy
**Method:** Community & deployed-files scan (`COMMUNITY/`, `updates/`, `reports/`, `audit_dashboard/`), winner-hunt backtest, mutual-fund walk-forward.

---

## 0. The Honest Bottom Line (read this first)

**Zero asset classes have a proven, forward-tested, cost-inclusive winning pick today.**

- Winner-hunt backtest screened **599 strategies**: **0 ELITE, 0 SURVIVOR**, all 599 FAILED (8 passed all four gates but were excluded as single-source artifacts).
- Every agent (OpenCode, Grok, GHCopilot, Poolside, Buffy, INCEPTION) independently converged on the same verdict: **no directional class is MONEY-READY / PROVEN**.
- The only things that *did* beat baselines were **index buy-and-hold** selections and **fee minimization** — not per-pick "alpha."
- Everything below is a **CANDIDATE** (paper-only) at best. Treat it as research, not a trade signal.

> *Not financial advice. Research/educational only. Past performance does not guarantee future results.*

---

## 1. Top Picks per Asset Class (with justification + ELI5)

### 🪙 Crypto — NO real-money pick; CANDIDATE SHORTs only

| Lead | Status | Why | ELI5 |
|------|--------|-----|------|
| `prediction_market_consensus` SHORT | CANDIDATE | n=682, PF 2.11 | After a coin flip, this signal won 2.1× for every 1 it lost — but we can't yet prove the coin isn't loaded. |
| `rapid_momentum_filter_mut` SHORT | CANDIDATE | n=55, PF 2.59 | Good ratio but small sample; a few lucky flips can fake this. |
| `cvd_divergence` SHORT | CANDIDATE | n=42, PF 2.60 | Same caveat — tiny n. |
| `luxalgo_confluence` SHORT | CANDIDATE | n=206, PF 1.65, MDD 85.6% | Win ratio is fine but the ride is terrifying (85% peak-to-trough); not tradeable with real money. |
| `crypto_short_rsi3050` SHORT | CANDIDATE (strong) | PF 2.16, Sharpe 6.9, null 99.8th pct | The single most-tested SHORT candidate; strongest null rejection of the set. |
| `high_trust_momentum` | CANDIDATE (weak) | Oct decay, WR 38.1% | Huge win-rate claims collapsed once the frozen-exit bug was fixed — historically unreliable. |
| `alpha_engine` cell | CANDIDATE | WR 75.1%, PF 3.90 | Same decay risk as above; scoreboard is known-corrupt. |

**Verdict:** No real-money allocation. **BTC** is used only as the first verification benchmark.

### 📈 Equity (US) — index core only, no certified stock pick

| Lead | Status | Why | ELI5 |
|------|--------|-----|------|
| FXAIX / SWPPX / VFIAX (S&P 500) | Baseline core | Sharpe 1.03, 5yr 15.7% | Just buy the whole market — you own all 500 coin flips at once, so you average out the randomness. |
| FSPGX (large-cap growth tilt) | Watch | 5yr 18.2% | Higher return but it's a "beta" bet on growth, not proof of skill. |
| VTSAX / FSKAX (total market) | Core | 5yr 15.1% | Same logic — own everything. |
| `rs-breakout-scout` LONG | CANDIDATE (weak) | n=46, PF 1.78, CI [0.85, 3.60] | The confidence interval dips below 1.0, so we cannot rule out pure luck. |
| AAPL RSI Reversal | CANDIDATE | n=1 symbol | One symbol — far too thin to claim anything. |

**Verdict:** No certified individual-stock pick. Cheapest broad index = the core.

### 💰 ETF — hold the cheapest broad index (fee edge is the only proven edge)

| Lead | Status | Why | ELI5 |
|------|--------|-----|------|
| VOO / FXAIX / VFV.TO / XUS.TO | Fee edge | Expense ratio near 0.00–0.03% | Fees are the only cost you *control*; the cheapest broad fund wins because less leaks out. |
| BKLC (US) | Core | 0.00% expense, CAGR 18.42%, MDD 26.14% | Zero-fee S&P baseline. |
| XEQT / VBAL (Canada) | Core | XEQT 14.41% vs VBAL 8.68% CAGR | XEQT is the all-equity Canadian all-in-one; VBAL is the balanced version. |
| MRBB + 200d TAA | RESEARCH-VAL | tactical rotation, Sharpe 1.48 vs SPY 1.37 | Moving between broad buckets beats picking single names — but still not forward-proven. |

**Verdict:** Walk-forward confirms **always VOO / FXAIX** beats fund-picking. Stick to the cheapest core.

### 🏦 Mutual Funds — no active-fund winner; index still wins

| Lead | Status | Why | ELI5 |
|------|--------|-----|------|
| XEQT | Best CAD baseline | **14.25% net CAGR**, vol 15.40%, MDD −29.76%, Sharpe 0.94 | The all-in-one index fund won the walk-forward race by just sitting still. |
| TDB902 | Best 5Y performer | **17.08% net CAGR**, vol 15.61%, MDD −27.45%, Sharpe 1.09 | A low-cost index fund; beating active managers by owning the market cheaply. |
| FCNTX / VPMCX | Diligence only | 13.52% / 13.70% CAGR, MDD ~49–52% | Big returns but brutal drawdowns — not automatic buys. |
| TDB900 / TDB911 / VBAL | Baselines | 8.35% / 10.65% / 7.57% net CAGR | Reference points, not recommendations. |

**Verdict:** Picker mean net CAGR **11.89% underperforms** the index. No active fund edge survived walk-forward.

### 🧾 Bonds / Fixed Income — cash-equivalent SHY, free broad-bond BKAG

| Lead | Status | Why | ELI5 |
|------|--------|-----|------|
| SHY / VSBSX | Cash-equivalent | Sharpe 1.05, CAGR 1.97%, MDD 5.71% | Short-term bonds barely move — they're a parking spot, not a growth bet. |
| AGG / BND / VBTLX | Core | Sharpe 0.28 | The broad bond market; smooth but low return. |
| TLT / VUSTX | Long-term | Sharpe 0.25 | Long-duration bonds swing more; only for risk-tolerant holders. |
| BKAG | Free broad-bond baseline | 0.00% expense | The zero-fee bond core. |
| `bond_yield_curve_slope` LONG | CANDIDATE | n=18, PF 9.44 | PF looks amazing but **n=18 < 100** — the gate rejects it; sample too small. |

**Verdict:** No proven tactical bond pick. SHY (cash equiv) + BKAG (free core) are the honest options.

### 🛢 Commodities — gold baselines only, no proven tactical winner

| Lead | Status | Why | ELI5 |
|------|--------|-----|------|
| GLD / IAU | Gold baselines | GLD Sharpe 0.87, 12.8%; IAU CAGR 10.70%, MDD 45.14% | Gold is a hedge, not a skill play — you own the shiny metal and hope. |
| DBC | Diversified | Sharpe 0.65, 10.2% | A basket of commodities; blunter but broader. |
| `commodity_term_cot` | REJECTED | — | Contrarian positioning signals failed validation. |
| `commodity_rsi_divergence` | CANDIDATE (weak) | PF 3.24 | Eye-catching but not forward-tested. |

**Verdict:** RSI divergence and term-structure ideas are rejected or weak. Gold is the only defensible reference.

### 🌍 Forex — abstain (contaminated data)

| Lead | Status | Why | ELI5 |
|------|--------|-----|------|
| `myfxbook_retail_contrarian` | CANDIDATE | n=306, WR 49.7%, PF ~2.43 | Fading retail crowds looks strong, but retail-fill data is known to be contaminated. |
| `forex_zscore_200d_fade` SHORT | CANDIDATE | n=207, PF 1.44 | Modest edge; below the 1.5 PF gate. |
| `non_crypto_consensus` | CANDIDATE | n=102, PF 1.63 | Thin sample; borderline. |
| `regime_accumulation` | WATCH | — | Regime claims are under investigation, not trusted. |
| `forex_trend_aligned` | CANDIDATE (weak) | PF 2.32 | Same caveats — not forward-proven. |

**Verdict:** All forex leads are flagged as contaminated or thin. **Abstain** until data integrity passes Phase-0 gates.

### ⛽ Futures — BLOCKED / abstain

| Lead | Status | Why |
|------|--------|-----|
| Stock-index futures | BLOCKED | PF 0.29, WR 46.1% — clearly negative edge. |
| HG=F (copper) | Falsification target | Not a pick; a benchmark to prove the null. |

**Verdict:** No edge. Abstain.

### 🏷 Penny / Memecoin / Options — NO supported selection

None of these classes had a single honest, forward-tested candidate. No recommendation.

---

## 2. Merged Result Quick Table (all agents)

| Asset Class | INCEPTION | OpenCode BEAM | Grok | GHCopilot | Poolside/KiloCode | Buffy |
|-------------|-----------|---------------|------|-----------|-------------------|-------|
| **Crypto** | CANDIDATE SHORTs only; no real-money | `prediction_market_consensus` SHORT (PF 2.11) | `high_trust_momentum` weak; `alpha_engine` cell | None; BTC = benchmark | `crypto_short_rsi3050` SHORT (PF 2.16, strong) | SHORT RSI(14) 30–50 (PF 2.16, null 99.8th pct) |
| **Equity** | No stock pick; index core | None yet (mega-cap RSI2 lead) | FXAIX/SWPPX/VFIAX core; FSPGX growth tilt | FXAIX/BKLC baseline; `rs-breakout-scout` LONG weak | `rs-breakout-scout` (PF 2.00, weak) | TAA / `rs-breakout-scout` (n=58, weak) |
| **ETF** | Cheapest broad index (fee edge) | VOO/FXAIX/VFV.TO/XUS.TO | "Boring Billion" (FZROX 50 / FZILX 25 / FNDF 10 / SHY 10 / GLD 5) | BKLC (0% fee); XEQT/VBAL CA | MRBB+200d TAA (RESEARCH-VAL) | Monthly TAA (MRBB+200d, IBS+200d) |
| **Mutual Funds** | XEQT 14.25%, TDB902 17.08% net CAGR | Always VOO/FXAIX (walk-forward YES) | Fund ranker "product" | FCNTX/VPMCX diligence only | — | — |
| **Bond** | SHY cash-equiv; BKAG free core | `bond_yield_curve_slope` LONG (n=18, PF 9.44 — rejected) | SHY/VSBSX; AGG/BND core | SHY (MDD 5.71%); BKAG free | FAIL | — |
| **Commodity** | GLD/IAU baselines | Class FAIL/REHAB (overlap) | GLD/DBC core; `commodity_term_cot` REJECTED | GLD/IAU baselines | `commodity_rsi_divergence` (weak) | — |
| **Forex** | Abstain (contaminated) | `forex_zscore_200d_fade` SHORT (PF 1.44) | `myfxbook_retail_contrarian` (PF ~2.43) | Abstain | `forex_trend_aligned` (weak) | — |
| **Futures** | BLOCKED (PF 0.29) | BLOCKED | — | Abstain (HG=F falsification) | — | — |
| **Penny/Meme/Options** | No supported selection | — | — | No supported selection | — | — |

**Consensus row:** No class is MONEY-READY. CANDIDATE ≠ investable. Cast the widest net only where the null is strongest (crypto SHORT RSI), and default everything else to the cheapest broad index.

---

## 3. Community & Deployed Files Check (scanned for picks/recommendations)

Scanned `COMMUNITY/`, `updates/`, `reports/`, `audit_dashboard/` for `.MD` and `.html` files containing picks. Files found to contain picks/recommendations:

### `COMMUNITY/`
| File | Picks/claims |
|------|--------------|
| `OPENCODE_20261023_MASTER_SUMMARY_TOPPICKS.MD` | OpenCode BEAM top picks per class (crypto SHORTs, bond slope, forex fade) |
| `GROK_20261023_0406_HIGHSUMMARY.MD` | Grok top picks + "Boring Billion" portfolio |
| `GHCOPILOT_20261023_MASTER_SUMMARY_PICKS_AND_PLAN.MD` | GHCopilot per-class choices |
| `OPENCODE_20261023_FUND_WALKFORWARD.MD` | Fund walk-forward: index still wins |
| `GROK_20261022_1930_WINNERS.MD` | Grok winners: 0 MONEY-READY, 7 CANDIDATE, 17 FAIL |
| `GHCOPILOT_20261023_FUND_DURABILITY.MD` | Durable funds: BKLC/BKAG 0% fee, FSCSX, FDGRX |
| `CROSS_AGENT_MASTER_PLAN_2026-10-22.md` | Poolside/KiloCode master plan: no agent proved a class |

### `updates/`
| File | Picks/claims |
|------|--------------|
| `2026-10-23-winner-hunt-report.md` | 599 strategies → 0 ELITE / 0 SURVIVOR; XEQT 14.25%, TDB902 17.08% net CAGR |

### `reports/`
| File | Picks/claims |
|------|--------------|
| `2026-10-22-community-plans-winner-leads-synthesis.md` | Synthesis: no directional class PROVEN; CANDIDATE leads + dead ends |
| `2026-10-22-proven-winners-per-asset-class.json` | Proven-winners JSON: COMMODITY PF 1.565, EQUITY 100% WR n=8, CRYPTO PF 0.958 |

### `audit_dashboard/`
| File | Picks/claims |
|------|--------------|
| `opencode_beam.html` | 0/9 classes pass real-money thresholds; CANDIDATE deep-dives |
| `poolside_paper.html` | Per-class top picks (crypto_short_rsi3050 strong) |
| `freebuff_buffy_proven_picks.html` | "0 of 9 classes MONEY-READY"; SHORT RSI(14) 30–50 strong |
| `mutual-funds.html` | FOCPX only fund whose edge survives style adjustment |
| `picks-now.html` | Top picks now |
| `index.html` | Claude Top Picks tab; 5-AI Top Picks Battle; Picks Now |
| `antigravity_picks.html` | Antigravity Top Picks |
| `opencode_paper_trading.html` | Primary candidate luxalgo_confluence SHORT |
| `ghcopilot_paper.html` | Ranked diagnostic strategies (not 5 profitable recs) |
| `kimi_top_picks_OLD.html`, `curated_picks_20260524.html` | Legacy curated picks |
| `CLAUDE_TOP_PICKS_METHODOLOGY.md`, `antigravity_picks_methodology.md`, `score_analysis.md` | Methodology / score files |

**Measurement caveat:** `data/summary_picks.json` showed corrupted win-rate values (BOND 133.3%, COMMODITY 240.2%, FUTURES 381.0%, INDEX 1141.2%). This confirms the agent consensus that the historical scoreboard was inflated by the frozen-exit resolver bug. **Any "PROVEN" claim from the pre-fix scoreboard should be treated as untrusted** until re-run on clean data.

---

## 4. Recommended Next Steps

1. **Don't deploy any CANDIDATE** into real money.
2. **Core allocation:** cheapest broad index (BKLC/VOO in US, XEQT in Canada) + SHY/BKAG for the cash sleeve.
3. **Seal forward cohorts** for the top crypto SHORT candidate (RSI 30–50) — the only candidate with a strong null rejection.
4. **Finish the scorekeeper repair** (Phase A) and re-run all "PROVEN" claims on clean data.
5. **Kill / quarantine** the dead ends: copy-trader, `commodity_term_cot`, high_trust_momentum, regime_* family, all pre-fix PROVEN claims.

---

> *Not financial advice. Research/educational only. Past performance does not guarantee future results.*
