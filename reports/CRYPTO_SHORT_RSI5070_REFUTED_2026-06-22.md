# crypto_short_rsi5070 — REFUTED as a standalone edge (2026-06-22)

**TL;DR:** The miner (#641) surfaced `CRYPTO|SHORT|RSI50-70` (net PF 1.52, n=45; recent PF 2.44)
as a promising 2nd candidate. A consensus-3 swarm flagged REGIME as the top risk; the falsification
checks it suggested all came back RED. **It is a regime + concentration artifact, not an RSI edge.**
Relabeled `crypto_short_rsi5070_REGIMEWATCH` and kept as a monitor only. **Do not size.**

## Falsification evidence (honest intrabar, class=CRYPTO, n=45, Feb–Jun 2026)

### 1. Regime-dependent (the decisive one)
| month | BTC return | n | WR | netPF | pnl_sum |
|-------|-----------|---|----|-------|---------|
| 2026-02 | −14.7% DOWN | 1 | 0% | 0 | −2.3 |
| 2026-03 | **+2.2% UP** | 7 | **0%** | **0** | **−14.0** |
| 2026-05 | −3.6% DOWN | 8 | 87.5% | 16.5 | +23.2 |
| 2026-06 | −12.7% DOWN | 29 | 65.5% | 1.67 | +29.5 |

The condition **lost 0/7 in the one up-ish month (March)** and won only in BTC-down months. The
"edge" is directional regime exposure: *short crypto while crypto is falling*. (April was +11.7% UP
but produced no qualifying picks — the cleanest bull test is missing, which is itself a coverage gap.)

### 2. P&L concentration (kilo's >60% = kill)
Top-3 symbols = **82.2% of net P&L**: RENDERUSDT 38.7% (3 picks), ARBUSDT 22.0% (3), ETHUSDT 21.4% (3).
Remove three symbols and the edge largely vanishes. Not a broad, repeatable signal.

### 3. Session clustering
US n=17 WR 82.4% netPF 6.0 · ASIA n=22 WR 50% netPF 1.56 · **EU n=6 WR 16.7% netPF 0.12**. The
apparent edge is concentrated in US session and negative in EU — another fragility axis.

## Verdict
- **REFUTED as a standalone RSI edge.** netPF 1.52 / recent PF 2.44 were produced by (a) a 4-month
  BTC-down regime, (b) 3 lucky symbols, (c) US-session clustering — not by RSI(50-70)+SHORT generalizing.
- Kept as `crypto_short_rsi5070_REGIMEWATCH`: a monitor to see whether the SHORT side survives a
  future BTC-**up** window. If it stays positive through a bull month with concentration <35%, revisit.
- **rsi5070-LONG remains the sole real honest lead** (n=116/150, netPF ~1.28, robustness already held).

## Process note
This is the TICK-15 discipline working: swarm + pre-registered falsification caught a mirage that
looked stellar on headline numbers (recent PF 2.44) *before* any sizing. The miner (#641) is still
valuable — it surfaces candidates fast; the falsification gate is what separates edge from artifact.
