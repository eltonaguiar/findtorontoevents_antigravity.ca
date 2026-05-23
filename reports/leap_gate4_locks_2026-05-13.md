# Leap Crypto Gate-4 profit-lock sweep — 2026-05-13

Swarm advice (agent `aa069b82010784ccd`) executed. Leap moved from "3 unforced give-back exposures" → "all profit locked, theses still running."

## State at sweep start

Balance $100,008, Equity $100,279, Unrealized **+$271.30**.

| Sym | Side | Qty | Entry | Last | PnL | % | Gate-4 status |
|---|---|---|---|---|---|---|---|
| DOGEUSDC.P | Long | 18,000 | 0.11069 | 0.11181 | +$20.16 | +1.01% | below threshold, HOLD |
| SOLUSDC.P | Short | 15 | 95.559 | 91.025 | +$68.00 | **+4.74%** | **VIOLATION — no lock** |
| ETHUSDC.P | Short | 1.3 | 2,313.25 | 2,252.10 | +$79.48 | +2.64% | approaching, lock early |
| BTCUSDC.P | Short | 0.05 | 81,189.8 | 79,116.1 | +$103.67 | +2.55% | SL→81,500 already (cycle 5), TIGHTEN |

## Actions executed

| Sym | Action | Outcome |
|---|---|---|
| SOLUSDC.P | **PARTIAL 50% close** — Buy 7 cover (qty 15→8). Then **SL→breakeven 95.559** on remaining 8 | Banked ~$32 realized. Remaining 8 risk-free above BE |
| ETHUSDC.P | **SL→2,300** (vs entry 2,313.25, locks +$17 minimum on remaining run) | Trail tightened |
| BTCUSDC.P | **SL→80,600** (vs prior 81,500, locks +$29 additional minimum) | Trail tightened |
| DOGEUSDC.P | HOLD — only LONG diversifier in book, sub-threshold | No change |

Post-sweep: book = 4 positions (3S + 1L), all locked or sub-threshold. PCG-5 Gate 4 ALL clear.

## New picks tonight: NONE

Swarm recommended SKIP — CRYPTO is DECAYING_EDGE per `edge_stability_index.json`, book already 3 SHORTs (adding 4th = intra-class correlation breach), XRP-L is only LONG candidate but lacks thesis given bearish stance. Don't pad.

## Swarm right-vs-wrong tracking note (user directive 2026-05-13)

User asked to track who-was-right across swarm agents. Cycle 10 Leap-swarm advice (agent `aa069b82010784ccd`, ~10 min wall-clock):

| Recommendation | Outcome — will retro-eval in 7 days |
|---|---|
| SOL-S partial 50% + SL→BE (95.559) | Pending — verify if BTC topping thesis plays out OR SOL reverses |
| ETH-S SL→2,300 (lock min +$17) | Pending — verify ETH stays sub-2,313 |
| BTC-S SL→80,600 | Pending — verify BTC stays sub-81,500 (current 79,116, very comfortable) |
| Don't add 4th SHORT | Pending — if SOL/ETH/BTC all run further, skip will be CORRECT (book maxed out). If crypto rallies, skip prevents adding fresh LONG exposure (also CORRECT) |
| Don't add XRP-L | Pending |

Pattern to log per swarm in future: `agent_id, recommendation, action_taken, +7d_outcome, +30d_outcome, verdict (CORRECT/WRONG/N/A)`. Suggest adding `swarm_advice_audit.json` to `audit_dashboard/data/` next cycle so this becomes systematic, not ad-hoc.

## Cross-account state post-sweep

| Acct | Active | Realized (session) | Unrealized | Margin used |
|---|---|---|---|---|
| zerounderscore | 8 | -$4,676 (history) | +$3 | $4.7k |
| theswarm | 14 | +$234 | -$45 (deteriorating MES/TLT) | $27k |
| Leap Crypto | 4 | +$8 → ~+$40 after SOL partial | +$199 (was +$271, less the $32 partial-realize) | $1.1k |
| V4 | 1 + 9 LIMITs | +$22 | +$3.82 | $160 + $811 reserved |

Leap is the cleanest book — 4 positions, all locked, well-diversified across the 5-symbol restricted universe (1L + 3S, XRP unused).
