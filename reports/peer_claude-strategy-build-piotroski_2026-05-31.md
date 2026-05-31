# Strategy Build — Piotroski F-Score (peer_claude, 2026-05-31)

## Summary
Implemented Joseph Piotroski's F-Score (J. Acc. Res. 2000) as a self-contained
strategy module in `/tmp/strategy_builds_2026-05-31/piotroski/` per the
build-wave protocol (isolated /tmp build, NO writes to shared tree apart from
this report + the docs PR).

## Deliverables
| File | Lines | Purpose |
|---|---|---|
| `strategy.py` | 245 | F-Score scoring, low-P/B universe filter, Wilson LB + bootstrap PF helpers |
| `paper_pilot_harness.py` | ~115 | sidecar JSON paper-pilot (screen / mark_to_market / stats); does NOT write trading_picks |
| `tests.py` | ~95 | 10 unit tests — all passing |
| `README.md` | — | citation, concrete rules, cursor stat gate, modern-variant backlog |
| `ai_consult_grok.txt` | — | verbatim Grok-4 fast-reasoning response |

Test result: `Ran 10 tests in 0.002s — OK`.

## Rules (verbatim from Piotroski 2000)
- Universe: bottom 20% by P/B
- F-Score = sum of 9 binary signals (profitability 4, leverage/liquidity 3, efficiency 2)
- BUY iff in low-P/B universe AND F-Score >= 8
- Hold 1 calendar year (252 trading days, time-based exit)

## Cursor statistical framework (applied)
- **n >= 500 floor** before any live promotion (avoids the n=2-8 ETF-class trap currently in `/audit`)
- **Wilson 95% LB** on WR (point estimates lie about small-sample WR)
- **Bootstrap PF 95% CI** (2,000 iters)
- **Bonferroni alpha = 0.05 / 7 = 0.00714** — 7 strategies in this build wave; raw 0.05 yields ~1 false positive by chance
- **Walk-forward 1y/1y** for the eventual live promotion gate

Encoded as module constants `LIVE_PROMOTION_N_FLOOR=500`, `BONFERRONI_ALPHA=0.05/7`.

## AI consult — Grok-4 fast-reasoning (xai api)
Asked for modern post-2010 F-Score variants. Key takeaways:

1. **F + Mohanram G + Beneish M overlay** — Dou et al. 2021 + Mohrman 2023:
   3.8-5.2% annual alpha (post-2010 US/EM) vs. 1.1% plain F. **Action: add as
   variant after baseline pilot crosses n=200.**
2. **Sector-adjusted F** (z-score each signal within GICS) — AQR 2023:
   +2.9-4.1% excess return vs. unadjusted F in tech/financials. **Action:
   second variant after baseline.**
3. **F x 12-1 momentum** — Asness 2022 / Bartram-Grinblatt 2021: Sharpe
   0.71-0.84 vs. 0.31-0.44 plain F (2010-2023). **Action: third variant
   — but watch momentum-crash drawdown amplification.**

Pitfalls noted: M-Score false positives in biotech (R&D capitalization),
sector-adjusted F is noisy in small sectors, F x momentum has 250%+
turnover so costs matter.

## Wire-up plan (per repo Wire-Up Rule)
This build is an **opt-in sidecar**. It does NOT touch the production
pick path (`calculate_smart_score`, `passes_active_gate`, etc.). Wiring
plan:
- **Target caller:** `alpha_engine/equity_fundamental_scanner.py` (does not
  yet exist — to be added in a follow-up PR)
- **Expected wire-up date:** after paper pilot accumulates n >= 100 closed
  picks (~Q1 2027 given 252-day hold)
- **Production gate:** must clear the cursor framework (Wilson LB > 0.50, PF LB > 1.0, n >= 500)

Until then, the EQUITY class on `/audit` continues to use existing strategies;
this module is fed a fundamentals dump out-of-band and tracks results in a
private sidecar JSON.

## Non-actions (deliberately)
- No DB schema changes
- No writes to `ejaguiar1_stocks`
- No updates to `updates/index.html` (premature — no proven edge yet)
- No new GitHub Actions workflow (premature)
- No edits to `audit_dashboard/template.html`

## Reproduce
```bash
cd /tmp/strategy_builds_2026-05-31/piotroski
python3 tests.py             # 10 tests pass
python3 strategy.py          # demo screen
```

## Open follow-ups
1. Add `equity_fundamental_scanner.py` that pulls fundamentals from EDGAR XBRL or yfinance and feeds `screen()`
2. Implement variant #2 (sector-adjusted F) — highest expected alpha at lowest implementation complexity
3. Add walk-forward harness (currently only the stats gate is implemented; walk-forward needs historical fundamentals corpus)
4. Cross-check Beneish M-Score availability in `ejaguiar1_stocks` for the F+M overlay variant
