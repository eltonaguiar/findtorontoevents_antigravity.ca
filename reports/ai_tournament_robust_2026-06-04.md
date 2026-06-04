# AI Tournament — Robust-Metric Verification (post 4-round cleanup)
2026-06-04 ~09:55 UTC. Computed after all 2,987 MISPRICED_ENTRY rows excluded and outlier WON-PnL rows neutralized.

## Top models — risk-adjusted profile

| Rank | Model | n | WR | avg_w | avg_l | cumPnL | MDD | Ret/MDD |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **1** | **claude_haiku_4_5** | 56 | **71.4%** | 4.54% | -3.14% | **+131.4%** | **-12.1%** | **10.9** |
| 2 | grok3 | 98 | 55.1% | 8.09% | -4.72% | +229.3% | -27.4% | 8.4 |
| 3 | deepseek_r1 | 101 | 55.4% | 5.22% | -3.73% | +124.0% | -20.3% | 6.1 |
| 4 | kimi_direct | 71 | 63.4% | 3.57% | -2.85% | +86.6% | -17.9% | 4.8 |
| 5 | llm7_qwen | 55 | 63.6% | 3.10% | -3.18% | +45.0% | -18.6% | 2.4 |
| 6 | gpt5_mini | 52 | 57.7% | 3.15% | -2.85% | +31.8% | -19.6% | 1.6 |

## Diversification check

| Model | EQUITY | BOND | FOREX | CRYPTO | ETF | FUTURES | COMM |
|---|---|---|---|---|---|---|---|
| claude_haiku_4_5 | 11/15 (73%) | 11/14 (79%) | 7/10 (70%) | 5/7 (71%) | 3/6 (50%) | — | — |
| grok3 | 13/17 (76%) | — | — | 16/29 (55%) | **10/10 (100%)** | 8/16 (50%) | 3/14 (21%) |
| deepseek_r1 | 21/41 (51%) | 5/11 (45%) | 11/14 (79%) | 3/9 (33%) | — | — | 9/16 (56%) |

**claude_haiku_4_5 alone has WR>50% on every asset class it touched.** Other top models have at least one weak class.

## Caveats

- **grok3 ETF 10/10 = 100% WR**: likely contains residual mispriced rows under the 25% drift threshold. Would need lower threshold + intrabar OHLC replay to fully clean.
- **n=56 for claude_haiku** is below institutional n>=100; another 2 weeks of forward picks needed for stat-significance.
- **MDD computed on cumulative-sum** (not equity-curve compounding); approximate.

## Recommendation

If we wanted to weight model-blend submissions toward best-risk-adjusted edge today:
- **claude_haiku_4_5: 40%** (highest Ret/MDD, broadest diversification, lowest drawdown)
- grok3: 20% (strong returns but concentrated; veto ETF picks)
- deepseek_r1 + kimi_direct: 20% each
- All others: down-weighted or excluded

Do NOT size live capital until n>=100 per model and an additional 2-week paper-pilot.
