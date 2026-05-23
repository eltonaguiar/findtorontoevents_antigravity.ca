# CHATWITHIT STATUS — Current State (Overwritten, Not Appended)
**Last Updated:** 2026-03-17 ~02:30 UTC by Claude (v138)
**Purpose:** Single source of truth. Overwrite entirely each update. For history, see CHATWITHIT.md.

---

## File Architecture

| File | Owner | Content |
|------|-------|---------|
| `docs/CHATWITHIT.md` | All | Active coordination log (Mar 14+) |
| `docs/CHATWITHIT_ARCHIVE_PRE_MAR12.md` | Antigravity | Historical archive (pre-Mar 12) |
| `docs/CHATWITHIT_STATUS.md` | Claude | Current state snapshot (this file) |
| `docs/CHATWITHIT_INDEX.md` | Claude | Quick-start guide for new AIs |

---

## Operational Rules (All AIs Must Follow)

1. **System freeze in effect.** No new strategies until count <= 20.
2. **TP/SL standard:** 1-1.5% TP, 1.5-2% SL (or ATR-scaled: 0.8x ATR TP, 0.5x ATR SL).
3. **Max 1 Keltner position per direction.** BTC/SOL/BNB are highly correlated.
4. **UTC 05:00-13:00 time filter** for new Keltner entries (>80% WR in this window).
5. **Quarter Kelly sizing** — $500 max per trade on $1K account.
6. **Dead strategies:** Keltner ETH, Keltner XRP, Drawdown Recovery RSI — STOP using these.
7. **Consensus filter (proposed):** ML ranker proposes, top-3 AIs must confirm. No confirmation = no trade.

---

## Tournament Standings — Round 4 (Live)

> **Tournament purpose:** Compare AI trading strategies head-to-head on same market conditions. Started: 2026-03-10.

| Rank | AI | W-L | Avg P/L | Best Pick | Worst Pick |
|------|----|-----|---------|-----------|------------|
| 1 | Scanner | 3-0 | +0.41% | XRP Long +0.50% | ETH Long +0.29% |
| 2 | Claude | 2-0 | +0.26% | XRP Long +0.50% | DOT Short +0.00% |
| 2 | Predictable | 2-0 | +0.26% | XRP Long +0.50% | TRX Long +0.00% |
| 4 | KIMI | 1-1 | +0.12% | BTC Long +0.44% | SOL Short -0.09% |
| 5 | Mercury | 1-0 | +0.10% | ETH Long +0.29% | DOT Short +0.00% |
| 6 | Grok | 1-1 | +0.03% | BTC Long +0.44% | INJ Short -0.36% |
| 7 | AG | 0-2 | -0.57% | TRX Long +0.00% | NEAR Short -1.28% |

**Overall R4:** 10W-4L across all AIs. Longs winning, shorts losing.

✓ Verified 2026-03-17 02:30 UTC

## Proven & Killed Systems (Walk-Forward Validated)

> **PROVEN definition:** Requires ≥20 OOS trades AND WR ≥55%. Strategies with <20 OOS trades are PROVISIONAL regardless of WR.

| Strategy | In-Sample WR | OOS WR | OOS Trades | p-value | Verdict |
|----------|-------------|--------|------------|---------|---------|
| **Keltner BTC** | 69.2% | **75.0%** | 36 | 0.002 | PROVEN — edge improved OOS |
| **Keltner SOL** | 75.0% | **62.1%** | 29 | 0.132 | ROBUST — monitor degradation |
| **RSI Confluence ETH** | 58.3% | **64.3%** | 14 | — | SANDBOX — small sample |
| **RSI Confluence XRP** | 57.9% | **83.3%** | 6 | — | SANDBOX — very small sample |
| Connors RSI-2 SPY | — | 75.7% | 200+ | 6e-6 | PROVEN (equity) |
| Connors RSI-2 QQQ | — | 75.3% | 200+ | 8e-6 | PROVEN (equity) |
| ~~Keltner ETH~~ | 87.5% | **37.5%** | 24 | 0.924 | KILLED — -50% WR collapse |
| ~~Keltner XRP~~ | 86.7% | **21.4%** | 14 | 0.994 | KILLED — -65% WR collapse |
| ~~Drawdown Recovery RSI~~ | 100.0% | **16.7%** | 18 | — | KILLED — -83% WR collapse |

### New Symbol Backtest Results (Keltner, same params, 500 x 1h candles)

| Symbol | Trades | WR | PF | Verdict |
|--------|--------|-----|-----|---------|
| **BNB** | 57 | **63.2%** | **2.39** | PROMISING — sandbox candidate |
| **DOGE** | 46 | **60.9%** | **2.00** | PROMISING — sandbox candidate |
| LINK | 34 | 52.9% | 2.25 | MONITOR |
| AVAX | 41 | 48.8% | 2.07 | WEAK |
| ADA | 44 | 40.9% | 0.82 | WEAK |
| NEAR | 19 | 21.1% | 0.12 | DEAD |
| DOT | 34 | 26.5% | 0.51 | DEAD |
| LTC | 27 | 14.8% | 0.22 | DEAD |

**Pattern:** Keltner works on high-liquidity, high-volatility majors. Fails on low-float/thin alts.

✓ Verified 2026-03-17 02:30 UTC

### Genome Evolution Results (9,000 backtests, 150 generations)

Best genome **G51883**: 98.6% WR, PF 14.73, 142 trades, +65.72% PnL. Key finding: **tp=0.5x ATR (tiny), sl=2.1x ATR (wide), channel=1.0x (tight)** — micro-scalping approach.

| Validation Track | Result | Status |
|-----------------|--------|--------|
| Walk-Forward (1h, 60/40 split) | 86% train → 99% test | ROBUST |
| 4h Timeframe | Weak transfer | 1h-SPECIFIC |
| 12-Symbol Expansion | 11/12 pass | BROAD |

**New sandbox strategies:** `keltner_evolved_v1` (exact G51883 params) + `keltner_evolved_moderate` (less extreme TP/SL). Both wired into scanner, need ≥30 forward trades to evaluate.

## ~~Final 15 Strategy Proposal~~ — SUPERSEDED (2026-03-17)

> **SUPERSEDED:** The "Final 15" concept is outdated. We now have 100+ strategies managed by the auto-tuner (elimination engine + genome evolution). The auto-tuner handles promotion, probation, and culling autonomously. This section is retained for historical context only.

| Tier | # | Strategy | WR | Capital |
|------|---|----------|----|---------|
| **Proven** | 1 | Keltner BTC | 75% OOS | 70% total |
| | 2 | Keltner SOL | 62% OOS | |
| | 3 | Connors RSI-2 SPY | 75.7% | |
| | 4 | Connors RSI-2 QQQ | 75.3% | |
| **Strong** | 5 | crypto_rsi_whaleconfirmed_v1 | 67.9% | 20% total |
| | 6 | funding_momentum | 53.8% (329 trades) | |
| **Sandbox** | 7 | Keltner BNB | 63.2% backtest | 10% max |
| | 8 | Keltner DOGE | 60.9% backtest | |
| | 9 | RSI Confluence ETH | 64.3% OOS | |
| | 10 | RSI Confluence XRP | 83.3% OOS (6 trades) | |
| | 11 | Keltner LINK | 52.9%, PF 2.25 | |
| **Experimental** | 12 | perp_funding_arb | market-neutral | paper only |
| | 13 | pairs_BTC_SOL | decorrelation | |
| | 14 | ML Consensus Filter | AI veto gate | |
| | 15 | baby_strats_forward | 47.9%, 920 trades | |

~~**Votes received:** Grok YES, AG YES (implied), Claude YES. Need 1 more for lock.~~ — **RESOLVED 2026-03-17: Superseded by auto-tuner. No further votes needed.**

## System Count

| Category | Count | Action Needed |
|----------|-------|---------------|
| Target strategies | ~~15~~ Auto-managed | Auto-tuner handles promotion/culling |
| Currently running | 100+ | Managed by elimination engine + genome evolution |

## Active Infrastructure

| Component | Frequency | Status |
|-----------|-----------|--------|
| Alpha Engine scanner | Every 30 min | Running |
| KIMI live_scanner | Every 15 min | Running |
| Signal tracker | Every 15 min | Running |
| Cross-aggregator | Every 5 min | Running |
| Battleground | Every 15 min | Running |

✓ Verified 2026-03-17 02:30 UTC

## Authority Matrix (Added v137)

| Role | Can Propose | Can Approve | Can Veto | Final Decision |
|------|------------|-------------|----------|----------------|
| **User** | YES | YES | YES | **ALWAYS final** |
| Any single AI | YES | Recommend only | Soft veto (flag risk) | No |
| 2+ AIs agree | YES | **Strong rec** | Strong flag | Still user decides |
| Scanner/Auto | Signal only | No | No | No |

**Tie-break:** Disagreement -> escalate to user with both arguments. No AI unilaterally kills a strategy.
**Emergency:** -5% session drawdown -> any AI can pause. User confirms kill/resume within 24h.

---

## Kill Criteria (Added v137)

| Condition | WR | PF | Trades | Verdict | Action |
|-----------|----|----|--------|---------|--------|
| Clear fail | < 40% | < 1.0 | >= 30 | **KILL** | Archive, remove from scanner |
| Inverse candidate | < 40% | > 1.5 | >= 30 | **INVESTIGATE** | Paper test inverse signal |
| Degrading | Was > 55%, now < 45% | Declining | >= 50 | **PROBATION** | Half sizing, 2-week monitor |
| Insufficient data | Any | Any | < 30 | **SANDBOX** | No real capital |
| OOS collapse | IS > 60%, OOS < 40% | OOS < 1.0 | >= 20 OOS | **KILL** | Walk-forward failure = dead |
| Marginal | 45-55% | 1.0-1.3 | >= 50 | **REVIEW** | Check regime dependency |

---

## Capital Allocation by Tier (Added v137)

| Tier | Allocation | Split Rule | Example ($1K) |
|------|-----------|------------|---------------|
| **Proven** (OOS validated, p < 0.05) | **70%** | Equal among N_proven | $175 each (4 strategies) |
| **Strong** (>50 trades, PF > 1.5) | **20%** | Equal among N_strong | $100 each (2 strategies) |
| **Sandbox** (backtest or < 30 OOS) | **10%** | Equal, minimum viable | $20 each (5 strategies) |
| **Experimental** (paper only) | **0%** | $0 real | Paper only |

Quarter Kelly ($500 max) still applies per-position. Both constraints must be satisfied.

✓ Verified 2026-03-17 02:30 UTC

---

## Open Action Items (Max 10)

| # | Item | Owner | Priority | Dates |
|---|------|-------|----------|-------|
| 1 | ~~Lock Final 15 vote + execute cull~~ | All | ~~P0~~ | **COMPLETED 2026-03-17** — Superseded by auto-tuner |
| 2 | Standardize position sizing (Quarter Kelly, $500 max) | All | P0 | Created: 2026-03-15 \| Due: 2026-03-18 |
| 3 | Fix 93 missing battleground picks in dashboard | Claude | P0 | Created: 2026-03-15 \| Due: 2026-03-18 |
| 4 | Backtest optimal SL width on closed_picks.json | Grok (volunteered) | P1 | Created: 2026-03-15 \| Due: 2026-03-20 |
| 5 | Wire COINALYZE_API_KEY + FRED_API_KEY as GitHub secrets | User | P1 | Created: 2026-03-15 \| Due: 2026-03-19 |
| 6 | Add UTC 05:00-13:00 time filter for Keltner entries | Claude | P1 | Created: 2026-03-15 \| Due: 2026-03-20 |
| 7 | Walk-forward validate Keltner BNB + DOGE | Claude | P1 | Created: 2026-03-15 \| Due: 2026-03-21 |
| 8 | Switch to limit orders at KC band boundaries | Research | P2 | Created: 2026-03-15 \| Due: 2026-03-24 |
| 9 | Test perp_funding_arb (market-neutral) | AG/Grok | P2 | Created: 2026-03-15 \| Due: 2026-03-24 |
| 10 | Implement ML Consensus Filter (Gemini proposal) | All | P2 | Created: 2026-03-15 \| Due: 2026-03-24 |

## Current Market Regime

- **HMM:** BEAR (98.7% confidence, rising)
- **Fear & Greed:** 15 (Extreme Fear)
- **DefiLlama TVL:** STRONG_BULLISH (+0.542 composite, still climbing)
- **BTC Funding Rate:** -0.012% (shorts paying longs)
- **Google Trends "Bitcoin":** +18% 72h delta (accumulation signal)
- **Correlation warning:** BTC/ETH/SOL have 100% direction agreement. 3 shorts = 1 short expressed 3x.
- **Interpretation:** Choppy accumulation. Long-only on proven systems, tight TPs. No shorts unless Keltner fires on majors.

## Unanswered Questions

| # | From | To | Question | Status |
|---|------|----|----------|--------|
| 1 | Claude v131 | KIMI | What's different about your R4 approach? | UNANSWERED |
| 2 | Claude v131 | Grok | INJ liquidity — helping or hurting? | ANSWERED v135 — hurting, thin float amplifies volatility |
| 3 | Claude v131 | Mercury | Phase 2 tight-TP regime-dependent? | UNANSWERED |
| 4 | Claude v131 | AG | Switch to market-neutral? | ANSWERED v134 — not yet, ride proven edges first |
| 5 | Kilo v132 | Claude | Who has authority to kill systems? | ANSWERED v133 — user decides, any AI proposes |
| 6 | Kilo v132 | All | Remove AI pick layer? | RESOLVED — Gemini proposed "Consensus Filter" compromise |
| 7 | AG Review | All | Enforce system freeze until count <= 20? | AGREED — unanimous |

## Key Files

| File | Purpose |
|------|---------|
| `docs/CHATWITHIT.md` | Coordination log (Mar 14-15, ~1500 lines) |
| `docs/CHATWITHIT_ARCHIVE_PRE_MAR12.md` | Archived entries (v84-v101+) |
| `docs/CHATWITHIT_STATUS.md` | THIS FILE — current state only |
| `docs/CHATWITHIT_INDEX.md` | Quick-start guide for new AIs |
| `chatwithit.md` (root) | Kilo-Code's entries (1100+ lines) |
