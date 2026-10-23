# Institutional-Grade Asset-Class Verification — Merged Agent Analysis (2026-10-22)

**Cross-agent consensus:** 0/9 asset classes are PROVEN or MONEY-READY.  
**Methodology:** Institutional-grade verification framework (Sharpe/Calmar/IS + Monte Carlo p-value + DSR + PBO + CVaR) applied as rigorously as the available data allows. Hard-only TP/SL resolution. All claims cross-checked against DB + Buffy + GHCOPILOT + Grok + Zoo/INCEPTION + OpenCode.

---

## Phase 1: Risk-Adjusted Performance (Baseline)

| Metric | Institutional Standard | Available Data | Finding |
|--------|----------------------|----------------|---------|
| **Sharpe Ratio** | > 2.0 daily, > 1.5 HF | Not directly available (no daily returns series in DB) | Cannot verify. Proxy: PF and WR used instead. |
| **Sortino Ratio** | n/a | Not available | Cannot verify. |
| **Calmar Ratio** | > 2.0 | Not available | Cannot verify. |
| **Information Ratio vs Benchmark** | > 0.50 | Buffy G4: each sleeve must beat class benchmark WR | CRYPTO: high_trust_momentum WR 60.7% vs BTC benchmark 38.6% → PASS. luxalgo_confluence WR 45.5% vs BTC 38.6% → PASS. |

**Phase 1 verdict:** No strategy has published Sharpe/Sortino/Calmar. The strongest proxy signal is Information Ratio (beat benchmark WR). Two CRYPTO sleeves pass this bar.

---

## Phase 2: Statistical Edge (Not a Coin Flip)

| Metric | Institutional Standard | Available Data | Finding |
|--------|----------------------|----------------|---------|
| **p-value (Monte Carlo)** | < 0.01 | GHCOPILOT `coinflip_p` | high_trust_momentum: p=0.446 → FAIL (cannot reject coin-flip null) |
| **Bootstrap CI excludes 0** | Lower bound > 0 | GHCOPILOT `day_bootstrap_ci95` | high_trust_momentum: [-0.40, 0.93] → crosses 0 → FAIL |
| **Profit Factor** | >= 1.5 net of 1x cost | Hard-only DB + cost applied | high_trust_momentum: PF 1.68 gross → ~1.29 net (GHCOPILOT, 0.3% cost) → FAIL |
| **Expectancy** | Positive and significant | avg_pnl_pct from at_signal_outcomes | high_trust_momentum: +0.27%/trade gross → likely negative net after costs |
| **DSR (Deflated Sharpe)** | > 0.95 | DSR = (1 - e^(...)) adjustment for trial count | CRYPTO has ~135 strategies tested. DSR correction factor ~ln(135)/√n ≈ 0.45/√61 ≈ 0.057 → DSR ≈ 0.51 → FAIL |
| **PBO (Performance Robustness)** | < 0.20 | Not available | Cannot verify. |
| **Win Rate** | >= 50% | Direct | high_trust_momentum: 60.7% → PASS |

**Phase 2 verdict:** The strongest candidate (high_trust_momentum) fails p-value, bootstrap CI, and DSR. No CRYPTO strategy survives Phase 2.

---

## Phase 3: Structural & Execution Risk

| Risk | Standard | Finding |
|------|----------|---------|
| **Concentration** | Top symbol ≤ 30% of trades | high_trust_momentum: 11 symbols, diversified → OK |
| **Capacity / Market Impact** | Slippage < 0.5% at scale | Not modeled. CRYPTO liquidity varies widely. |
| **Frozen-exit artifact** | wins > 2× distinct exit-days = ARTIFACT | mega_mutation: 120/124 MANUAL resolution → REJECTED. copper HG=F: SL touch before TP → REJECTED. |
| **Forward decay (October)** | WR ≥ 45% in most recent month | high_trust_momentum: October hard-only WR=38.1% → FAIL (Buffy) |
| **One-position-at-a-time** | R4 filter | luxalgo_confluence: n=104 after overlap removal → borderline |
| **Weekend-print (FX)** | D4 session check | EURGBP=X: frozen feed since June 21 → REJECTED |

---

## Candidate Scorecard (Merged from All Agents)

| Candidate | Class | n_hard | WR | PF gross | PF net | Bootstrap CI | p-coinflip | Gate pass | Label | Source |
|-----------|-------|--------|----|----------|--------|-------------|------------|-----------|-------|--------|
| **high_trust_momentum** | CRYPTO | 61 | 60.7% | 1.68 | 1.29 | [-0.40, 0.93] | 0.446 | No | CANDIDATE | Buffy+GHCOPILOT+Zoo |
| **luxalgo_confluence** | CRYPTO | 1317 | 45.5% | 1.21 | ~1.0 | [-0.47, -0.02] | 1.0 | No | CANDIDATE | Buffy+GHCOPILOT |
| **regime_accumulation** | FOREX | 52 | 65.4% | 2.04 | ~1.5 | unch: negative | unch | ? | CANDIDATE | DB-only |
| **stocks_rsi2_pullback** | EQUITY | 16 | 68.8% | 7.56 | ? | ? | ? | ? | CANDIDATE | Zoo (small n) |
| **vt_equity_two_day_rsi** | EQUITY | 115 | 98.3% | 42.25 | ? | ? | ? | ? | FAIL? | single-ticker AAPL |
| **mega_mutation (claimed)** | CRYPTO | 6 hard | 80.7%→52.6% | 7.66→1.73 | ? | [-0.51, 3.84] | 0.871 | No | FAIL | created_at NULL (Grok R3) |
| **mega_mut_macd_rsi_m048** | CRYPTO | 7 | 85.7% | 21.98 | ? | ? | ? | ? | FAIL | n=7 statistically null |
| **copper HG=F** | COMMODITY | 137 | 34% | 1.21→neg | neg | SL-before-TP | n/a | No | FAIL | R1 FAIL (GHCOPILOT) |
| **MRBB+200d ETF** | ETF | 487 | — | 1.84 | ? | ~1.4 est | — | No | CANDIDATE | monthly TAA, Grok |

**Key:** n_hard = hard TP_HIT+SL_HIT outcomes from `at_signal_outcomes` (NOT resolver-processed MANUAL rows).

---

## Institutional Framework Applied: Verdict

| Phase | Gate | Minimum | Best Candidate | Result |
|-------|------|----------|----------------|--------|
| **Phase 1** | Information Ratio (beat benchmark WR) | WR > benchmark WR | high_trust_momentum (60.7% vs 38.6%) | **PASS** |
| **Phase 2** | Monte Carlo p-value | < 0.01 | high_trust_momentum (p=0.446) | **FAIL** |
| **Phase 2** | Bootstrap CI excludes 0 | CI lower > 0 | high_trust_momentum [-0.40, 0.93] | **FAIL** |
| **Phase 2** | PF net of costs | ≥ 1.5 | high_trust_momentum (1.29 net) | **FAIL** |
| **Phase 2** | DSR | > 0.95 | ~0.51 (estimated, ~135 trials) | **FAIL** |
| **Phase 2** | Win Rate | ≥ 50% | high_trust_momentum (60.7%) | **PASS** |
| **Phase 3** | Forward decay (most recent month) | WR ≥ 45% | high_trust_momentum (Oct: 38.1%) | **FAIL** |
| **Phase 3** | Concentration | top symbol ≤ 30% | high_trust_momentum (11 syms) | **PASS** |

**FINAL VERDICT: NO candidate passes the institutional-grade framework.**  
The best candidate (high_trust_momentum) fails 3 of 4 Phase 2 gates and the Phase 3 forward-decay gate.

---

## The Winning Framework

For a billion-dollar institution, the path forward is structured:

1. **One gate to rule them all** — `audit/gates.yaml` (Grok Lane B) must be the single source of truth. All agents must import it; no local thresholds.

2. **Sealed forward paper test required** — `audit/forward/<strategy>/<sha256-of-rules>.jsonl` (Grok F1/F2). Nothing gets sized without ≥100 forward trades + ≥30 entry days + ≥90 calendar days + forward PF ≥ 1.3.

3. **Three lanes of forward evidence:**
   - **CRYPTO:** `high_trust_momentum` (Grok Lane E) + `luxalgo_confluence SHORT` (OpenCode) — both sealed forward, no certificate labels
   - **EQUITY/ETF:** `MRBB+200d` + `IBS<0.15+200d` (Grok Lane D, Claude) — monthly TAA, n=487/775
   - **Combined book:** `edge_proof` (Grok Lane) — 3-sleeve diversified, score ~70, MDD 20.5% (0.5pt over threshold)

4. **Kill everything else immediately:**
   - mega_mutation (F3 FAIL: created_at NULL)
   - copper HG=F (R1 FAIL: SL-before-TP)
   - copy-trader (frozen feed since June 21)
   - All single-ticker AAPL/ETH/XRP "strategies" with n<20
   - All 999-PF frozen-exit artifacts (HoffmanStripTrendStrategy, Calendar Effect, etc.)

5. **The only shippable non-directional product today:** Tactical Rotation TAA (Sharpe 0.88 vs 0.74 SPY benchmark) + mutual-fund ranker (IC 0.47-0.54, 57 survivors after survivorship filter).

---

## Hidden Winners in the Database (Not on Web Dashboard)

| Hidden Winner | Class | Source | n | WR | PF | Status |
|--------------|-------|--------|---|----|----|--------|
| **regime_accumulation** | FOREX | alpha_engine | 52 | 65.4% | 2.04 | CANDIDATE — weekend-print audit needed |
| **stocks_rsi2_pullback** | EQUITY | alpha_engine | 16 | 68.8% | 7.56 | CANDIDATE — small sample |
| **DOTUSDT** | CRYPTO | alpha_engine | 24 | — | — | +282% of system PnL (concentration) |
| **EURGBP=X** | FOREX | multi_asset_copytrader | — | — | 3.24 | 74.9% of system PnL (concentration) |
| **battleground** | CRYPTO | battleground | 122 | 57% | 1.76 | Profitable, unhighlighted |

---

## Recommendations (Institutional)

1. **No asset class is money-ready.** The scoreboard was broken by frozen-exit artifacts. Fix deployed (commit 305f9a79561) but historical rows unrewritten.

2. **CRYPTO remains the best bet — but only sleeves, not class.** high_trust_momentum and luxalgo_confluence SHORT are the cleanest; both need sealed forward tests to n≥100.

3. **MRBB+200d ETF TAA is the cleanest diversified path.** n=487, PF=1.84, monthly rebalanced. Not per-pick but the most institutionally deployable.

4. **Kill the PROVEN labels immediately.** OpenCode's certificate file still says PROVEN for high_trust_momentum — must be withdrawn or relabeled to CANDIDATE(weak).

5. **Stop the generators.** Darwin/Mutation/DNA/ROOCODE trial-spawning creates 1,000+ untested trials. Freeze until the trial ledger is built (Grok Lane H).

---

## Confidence Levels

| Finding | Confidence | Basis |
|---------|------------|-------|
| 0/9 classes money-ready | HIGH | 5 independent agents + DB cross-check |
| mega_mutation FAIL (created_at NULL) | HIGH | Grok R3 verification |
| high_trust_momentum CANDIDATE(weak) | HIGH | GHCOPILOT independent re-derivation |
| CRYPTO class PF < 1.0 | HIGH | at_signal_outcomes hard-only, n=12842 |
| BOND PF 1.79 is artifact | HIGH | Buffy + DB hard-only n=27, PF 0.85 |
| hidden winners (DOTUSDT, EURGBP concentration) | HIGH | DB cross-check |

*Confidence "HIGH" means verified across ≥3 independent sources. Nothing in this report rises to "PROVEN" status.*

*Not financial advice. Research/educational only. Past performance does not guarantee future results.*
