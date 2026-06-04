# Wider Mispriced-Entry Audit — 2026-06-04 (Round 2)

After noticing `grok3 EQUITY` still had AMD picks at entry $158 vs actual market $484 (67% drift), discovered the original audit had `LIMIT 1000` cutting off 60% of the candidate set.

## Scope expansion

| Pass | Audited | Mispriced found |
|---|---:|---:|
| Round 1 (top-15 models, LIMIT 1000) | 969 | 553 |
| Round 2 (ALL models, NO LIMIT) | 3,453 | **1,525 additional** |
| **Cumulative** | — | **2,439 MISPRICED** |

## Honest leaderboard (n>=50)

| Rank | Model | n | WR | PF |
|---|---|---:|---:|---:|
| 1 | **claude_haiku_4_5** | 62 | 71.0% | 3.66 |
| 2 | kimi_direct | 78 | 64.1% | 2.21 |
| 3 | llm7_qwen | 59 | 62.7% | 1.63 |
| 4 | gpt5_mini | 58 | 60.3% | 1.87 |
| 5 | kimi_k2_6 | 76 | 57.9% | 1.56 |
| 6 | command_a | 87 | 56.3% | 1.35 |
| 7 | minimax_m2_5 | 80 | 56.3% | 1.12 |
| 8 | deepseek_r1 | 115 | 55.7% | 1.72 |
| 9 | cursor_agent | 103 | 55.3% | 1.99 |
| 10 | claude_opus_4_7 | 92 | 53.3% | 1.46 |

## Key signals

- **`claude_haiku_4_5`**: Maintains 71% WR even after the wider cleanup. Genuinely strong edge candidate.
- **`grok3` dropped out of top 12** — multiple inflated EQUITY picks (e.g., AMD entry $158 vs market $484) were caught in round 2.
- **PF compression**: top PF dropped from 3.90 → 3.66; most models now have PF 1-2 range — more realistic.

## Outstanding gaps

- 25% drift threshold may still miss subtle inflations (e.g. AMD pick with entry $445 — within yfinance daily range $443-460 around May 21). Lower threshold = more catch but more false positives.
- CRYPTO/FOREX excluded from this audit (different price-fetch path; CRYPTO uses Binance via api_failover, FOREX uses currency-pair APIs)
- Some entries are actually correct but yfinance auto-adjusted prices differ from the AI's raw quoted price
