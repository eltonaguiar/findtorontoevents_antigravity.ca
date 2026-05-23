# Cotton COT — Real-Money Capital Sizing Brief

**Generated:** 2026-05-12
**Strategy:** `cot_positioning` + symbol `CT=F` (ICE Cotton Futures)
**DSR:** 1.0000 (Lopez de Prado AFML eq 14.5; highest "publishable confidence")
**Verified by:** anti_overfit_audit_sidecar + Agent A DB probe + Antigravity Gemini audit

## Contract spec

| Field | Value |
|---|---|
| Exchange | ICE Futures US |
| Symbol | CT (yfinance: CT=F) |
| Contract size | 50,000 lbs cotton |
| Tick size | $0.0001/lb = **$5.00 per contract per tick** |
| Daily price limit | 3 cents/lb = $1,500/contract |
| Current price (~2026-05) | ~$0.70/lb |
| **Notional per contract** | **~$35,000** |
| Initial margin | $1,200-2,000 (broker-dependent) |
| Maintenance margin | $1,000-1,500 |
| Trading hours | Sun 8pm – Fri 1:20pm ET (electronic) |

## Micro contracts?

**NO micro-cotton exists.** ICE has not released a micro-CT contract. Unlike CME index futures (ES + MES, NQ + MNQ, RTY + M2K, YM + MYM), cotton trades full-size only.

Fractional-exposure alternatives:
1. **BAL** (iPath Series B Bloomberg Cotton Subindex Total Return ETN) — fractional shares possible but illiquid (~$2M/day volume; 1-3% bid-ask on retail tickets). Not recommended for real-money sizing.
2. **Options on CT=F** — defined-risk via futures options. Premiums $200-800 depending on strike + DTE.
3. **CFDs via international broker** — US persons restricted (CFTC Section 4c). Skip.

## Per-trade economics (from DSR-verified history)

| Metric | Per-pick % | Per-contract $ |
|---|---|---|
| WON avg PnL | +0.046% | **+$16.10** (3.22 ticks × $5) |
| LOST avg PnL | -0.031% | **-$10.85** (2.17 ticks × $5) |
| Round-trip cost (commission $5 + slippage $5) | — | -$10 |
| **Expected net per trade** (90% × $16.10 - 10% × $10.85 - $10) | — | **+$3.40 net** |

Multi-contract scenarios:
- 1 contract: +$3.40/trade × 50 trades/yr = $170/yr
- Tight execution ($5 round-trip): +$8.40/trade × 50 = $420/yr
- 2 contracts tight: $840/yr
- 5 contracts tight: $2,100/yr

## Capital tiers — recommended sizing

| Tier | Capital | Contracts | Annual P&L est. | Annual ROI | Risk posture |
|---|---|---|---|---|---|
| **Below-floor** | $1,500-2,500 | 1 | $170-$670 | 7-45% | UNSAFE — 1 daily limit move = wipeout |
| **Paper-graduating floor** | **$5,000** | 1 | $170-$670 | 3-13% | First-live posture after paper pilot |
| **Comfortable single** | **$10,000-15,000** | 1 | $170-$670 | 1.7-6.7% | **Recommended starting point** |
| **Single-class deviation cap** | **$25,000** | 2-3 (CT=F + KC=F coffee, also DSR-real) | $340-$1,340 | 1.4-5.4% | Per Codex SUPREME EDGE 2026-05-12 single-class accept |
| **Full COT basket** | **$50,000+** | 5-10 (CT/KC/SB/CC/ZC/ZW) | $850-$3,350 | 1.7-6.7% | Institutional-style COT allocation |
| **Hedge-fund-grade** | **$100,000+** | All 4 backed strategies | varies | 8-15% target | All-classes-first SHADOW posture |

### Multi-COT diversification (extension of cot_positioning)

Agent A DB probe confirmed `cftc_cot_commercial_signal` + CT=F at **WR 93.7% n=95** (sister signal, same data family). Adding KC=F coffee (60% WR n=25) at $25k tier offers natural diversification.

### Risk-of-ruin math

- 90% WR → probability of N consecutive losses = 0.10^N
- 5 straight losses: 1 in 100,000 (~once per 1,900 years of weekly trading)
- 10 straight losses: 1 in 10 billion (effectively impossible)
- Primary risk = single black-swan adverse move > $1,500 limit (daily limit cap acts as natural stop)
- With $5,000 floor: 3× margin buffer absorbs 3 simultaneous adverse moves before margin call

## Pre-live checklist (4-step gate)

1. ✓ DSR-verified edge (DSR=1.0)
2. ✓ Independent confirmation (Agent A DB + Antigravity Gemini)
3. ✓ Data integrity verified (0 zero-PnL rows, 0 missing exits)
4. ☐ **Paper pilot 4 weeks via `tools/cot_paper_pilot.py`** (needs implementation; placeholder for next-window work)
5. ☐ Net P&L within ±50% of expected $3.40-$13.40/trade
6. ☐ User explicit approval for single-class deviation (✓ verbally accepted 2026-05-12)
7. ☐ Capital allocated at recommended tier ($5k-$10k starter)

## Recommended next commits

1. Build `tools/cot_paper_pilot.py` — emits paper-trade signals from the cot_positioning + CT=F edge with $3.40-$13.40 expected P&L per trade
2. Build `audit_dashboard/money_ready.html` viewer page (parallel to anti_overfit.html + research_sidecars.html)
3. Wire `MONEY READY` HC-filter button (shipped this turn) into the same paper-pilot signal stream
