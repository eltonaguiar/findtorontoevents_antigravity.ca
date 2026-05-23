# Leap Crypto fresh-picks placement — 2026-05-13

Post-closeout re-entry per user directive: "get us fresh picks under 'the leap crypto' portfolio" for the ~48h window before contest close on May 15.

Swarm pre-approved (task `ae93616b0af196111`, see Leap Top-5 research `reports/leap_top5_traders_research_2026-05-13.md` Pattern A justification).

## Account state at entry

- Account: **The Leap Crypto** (paper)
- Pre-trade balance: **$100,278.60** (banked from closeout earlier today, see `reports/leap_closeout_2026-05-13.md`)
- Post-trade margin used: **$1,302.13** ($1,002.13 BTC + $300 XRP), 98.7% buffer.

## Positions placed

| # | Side | Symbol | Qty | Entry | TP | SL | Lev | Notional | Margin |
|---|---|---|---|---|---|---|---|---|---|
| 1 (anchor) | SHORT | COINBASE:BTCUSDC.P | 0.126 | 79,551.5 | 76,800.0 | 79,950.0 | 10x | $10,021.79 | $1,002.13 |
| 2 (satellite) | LONG | COINBASE:XRPUSDC.P | 2,098 | 1.4302 | 1.5800 | 1.4000 | 10x | $3,000.05 | $300.00 |

### R:R per position (post-fill live entries)

- BTC-S: risk $398.5 (entry→SL) / reward $2,751.5 (entry→TP) ≈ **R:R 6.9**. Better than swarm-modeled 2.94 because we entered at 79,551 vs swarm-target 79,150 (higher = better short).
- XRP-L: risk $0.0302 (entry→SL) / reward $0.1498 (entry→TP) ≈ **R:R 4.96**. Better than swarm-modeled 2.6 because XRP at 1.4302 vs target 1.45 (lower = better long).
- Combined max-loss if both stop: $451 (0.45% of account).
- Combined max-win if both TP: $2,914 (2.91% of account).

## Why this construction (per swarm + top-5 retro)

- **Anchor SHORT BTC**: prior Leap swarm BTC-S printed +$103.67 on the same thesis 2 days ago; trend intact (price still below 4H EMA-21 + 1D EMA-200 distance compressed); $80.2k = invalidation breach of structure.
- **Satellite LONG XRP**: alt-beta hedge against BTC dominance reversal. Same role DOGE played last round (+$20.16 small but positive). XRP at 1.43 sits near pivot support with mediocre near-term but high reward-to-risk ratio.
- Hard exits documented: time-stop 2026-05-15 12:00 UTC; profit-lock at +$3,008 unrealized (3%); BTC 4H close above $80,200 kills BOTH (regime break) regardless of XRP state.

## Swarm right-vs-wrong tracking (user directive 2026-05-13)

Per the standing "track who was right vs wrong" directive, this entry will be retro-evaluated within 48h:

| Pick | Swarm agent | Recommendation | Outcome eval | Verdict |
|---|---|---|---|---|
| BTC-S 10% anchor | `ae93616b0af196111` | Short @ 79,150 swarm-target (real 79,551) | resolves by 2026-05-15 12:00 UTC | PENDING |
| XRP-L 3% satellite | `ae93616b0af196111` | Long @ 1.45 swarm-target (real 1.4302) | resolves by 2026-05-15 12:00 UTC | PENDING |

Auto-write to `audit_dashboard/data/swarm_advice_audit.json` next cycle (schema in `reports/leap_closeout_2026-05-13.md` followup section).

## Notes / friction

- **Order ticket TP/SL didn't carry through on market submit** for either pick. Both required follow-up Protect Position dialog to attach brackets. Repeat of TV-paper bug observed previously — order-panel TP/SL on a market order is unreliable; manual protect-attach is mandatory after fill.
- Both Protect dialogs needed TP and SL toggle switches enabled (default off) before price values would persist. See `feedback_tv_protect_position_tp_toggle.md`.
- Leverage forced to 10x by paper-account default (swarm spec was 5x). Doubles notional vs spec — actual exposure $13k vs spec $6.5k. Acceptable given Leap closes in 48h: max combined loss still capped at $451 (0.45%).
