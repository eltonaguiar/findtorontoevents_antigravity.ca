# Will This Actually Improve Performance? — Plain-English (2026-05-12)

User-facing summary of expected impact from this session's rescue work.
Translates the per-class technical fixes into "what should you actually
see" terms.

## The core problem right now

Our current system picks bad trades most of the time:
- Too many losing picks (especially CRYPTO and FOREX)
- Many "draggers" (bad strategies) are still active
- The AI is overconfident but often wrong
- Data has errors (zero-PnL trades, stale models)

## How the Week 1 fixes + v3b help

| Asset class | Current problem | How the fixes help | Expected improvement |
|---|---|---|---|
| **COMMODITY** | Good signals but too few | Better data + paper-pilot + cleaner signals | **Biggest & fastest win.** Should become reliably profitable |
| **EQUITY** | Okay but inconsistent | ml_gatekeeper enforcement + cleaner signals | Noticeable lift in WR and consistency |
| **ETF** | Small sample, decent | More volume + structured signals | Steady improvement toward profitable |
| **CRYPTO** | Very bad (biggest drag) | Dragger quarantine + confidence gate + better signals | **Major reduction in losses** (biggest $ impact) |
| **FOREX** | Consistently losing | SHORT-only gate + regime filter + bad signals blocked | Stops heavy bleeding (may turn neutral) |
| **BOND** | Too few trades | FRED fix + new strategies | Slow ramp-up; becomes usable |
| **FUTURES** | Almost dead | Dedicated scanner rebuild | From dead → potentially good |

## What each fix actually does (plain English)

### Data pipeline fix
Stops garbage data (zero-PnL trades) from poisoning decisions. Cleaner
numbers = the AI makes better choices.

→ Shipped: zero-PnL artifact filter (commit `dd8e8282537`) +
WON-vs-PnL sign-coherence guard (commit `22b677c1167`).

### Dragger quarantine
Kills the worst strategies that lose money consistently (kimi_signal_tracking,
crypto_soc, meta_strategy CRYPTO blanket, 5 ghost-row symbol-triples).
Immediately removes the biggest sources of losses.

→ Shipped across commits `597819d79c7`, `5c7a8c43a27`, `c778f8f1696`.

### ML staleness hard-fail
Old, broken models get disabled automatically. Only fresh, working
models are used.

→ Shipped: mtime watchdog flip (commit `db5bcfa0f04`).

### v3b signal translator
Instead of vague text, the AI now outputs structured instructions
(ticker, direction, confidence, features, time window). Our system can
**understand and execute them properly** instead of guessing. This is the
biggest long-term upgrade.

→ Shipped: schema + Pydantic validator + 15 passing tests (commits
`ba4a40ac36a`, `aad6cd94c64`). Production wire-up queued for next session.

## Realistic timeline + expectations

- **Week 1-2:** Losses should decrease noticeably (especially CRYPTO). Some classes become break-even.
- **Week 3-4:** COMMODITY and EQUITY should start showing consistent small profits.
- **Month 2+:** If we keep iterating, multiple classes can become reliably profitable.

## Important truth

This rescue plan **will improve performance**, but **it's not magic**.
It removes the worst problems first (bad data + toxic strategies), then
improves signal quality. The biggest gains will come from COMMODITY and
EQUITY first, then CRYPTO once cleaned up.

## What to watch in the next 7 days

1. **DB Health panel** on /audit — Ghost Rows should drop from 655k → ~440k after next cron commits fresh data.
2. **Paper Pilot tab** — `cot_positioning + CT=F` should continue accumulating closed picks at ~90% WR.
3. **Top-N rank backtest card** — EQUITY top-10 daily P&L should turn positive on the rolling-7d window.
4. **ML staleness** — `enhanced_ml_crypto_v3` 20K joblib files should retrain on next workflow_dispatch (mtime gate triggers auto-delete + retrain).
5. **BOND emission** — bond_emitter_spike should produce >0 picks per daily run now that FRED is skipped + yfinance fallback fires.

## NFA

Research surface only. The 10-step Lopez de Prado AFML readiness gate
(see `audit_dashboard/real_money.html`) remains the canonical real-money
bar regardless of any single fix landing.

## Refs

- `reports/rescue_plan_per_asset_class_2026-05-12.md` — per-class playbook
- `reports/expanded_rescue_roadmap_2026-05-12.md` — week-by-week tasks
- `reports/week1_draft_prs_2026-05-12.md` — 4 PR-style summaries
- `reports/v3b_signal_translator_spec_2026-05-12.md` — full spec
- `reports/grok_audit_red_team_synthesis_2026-05-12.md` — verified numbers
- `audit_dashboard/real_money.html` — readiness hub
- `audit_dashboard/paper_pilot.html` — SHADOW tracker
