# EQUITY Edge Hunt — 2026-06-05

**Sources:** `money_ready_verdict.json`, `pf_registry.json`, live DB `at_pick_outcomes`, `ueps_picks.json`, `data/earnings/*/latest.json`, `production_scanner.py`, rigorous backtest + H-010 reports.

## Verdict: **NO_EDGE_YET**

Class-level EQUITY is not real-money ready. No sleeve clears Tier-2 (PF>1.5 / WR>50% / n≥30 / MDD<20%) under policy-clean accounting.

| Metric | Value | Source |
|--------|-------|--------|
| n_resolved | 45 | money_ready_verdict |
| WR | 24.4% | money_ready_verdict |
| PF | 0.26 | money_ready_verdict |
| MDD | 75.9% | money_ready_verdict |
| Verdict | INSUFFICIENT_DATA | money_ready_verdict |
| top_source | regime_terminal (37.8%) | money_ready_verdict |

---

## Sleeve autopsy

**regime_terminal** — KILL. pf_registry: n=17, WR=17.6%, PF=0.19, single-source artifact. Dominates class losses; LCID/OPEN/AMD heavy.

**stocks_rsi2_pullback** — DISPUTED. pf_registry forward n=5, 100% WR (no losses → INSUFF_N). Live `at_pick_outcomes`: n=81, WR=46.9%, PF=1.22. Rigorous backtest n=64 PF=21.5 but PBO=0.645 (overfit). **Banned** in `banned_strategies.json`. Do not size up.

**smart_money_accumulation** — FAIL live. pf_registry n=9 PF=1.45 (artifact); `at_pick_outcomes` n=6, WR=0%.

**yahoo_analyst_consensus** — KILLED. Blocked in `production_scanner.py` Gate 0; 0% WR cited in `auto_tuner.py` / `non_crypto_quality_gate.py`. Not in production path.

**equity_pead / equity_post_earnings_drift** — NOT in `production_scanner.py`. Wired via `academic_strategies_emitter` → `priority_picks_emitter` only. `EQUITY_PEAD_ENABLED=0` default. H-010 harness **REJECTED** (eff sign-split). Forward PEAD picks: n=1 (`Earnings Drift`).

**UEPS / value_screener** — Wired weekly (`value_screener_runner.py`, GHA). `ueps_picks.json`: 22 LONG, 0 SHORT, universe 51. Today's run scored n=1 → 0 picks (universe fetch gap). 3y+ thesis horizon — not a swing edge yet.

---

## Earnings cache (PEAD usability)

`data/earnings/{AAPL,MSFT,GOOGL,XYZ}/latest.json` — real yfinance pulls (2026-06-05). Usable for surprise triggers:

| Ticker | Last report | surprise_pct |
|--------|-------------|--------------|
| GOOGL | 2026-04-29 | +94.3% |
| MSFT | 2026-04-29 | +5.2% |
| AAPL | 2026-04-30 | +3.5% |
| XYZ | 2026-05-07 | +25.6% |

Next dates Jul 2026 — no imminent catalyst this week; drift window on recent beats still actionable for paper.

---

## AI tournament

AI tournament EQUITY picks (MSFT, AMZN, JPM…) — all OPEN, zero resolved.

---

## Top 3 candidates (fast-week validation path)

### 1. MeanReversionBB (best live sleeve)
- `at_pick_outcomes`: **n=175, WR=54.9%, PF=1.82**
- Emitted via `multi_asset/scanner.py` (Bollinger mean-reversion)
- **Action:** isolate paper pilot; cap 0.25× size; exclude regime_terminal co-emissions

### 2. equity_pead + earnings cache (fast catalyst lane)
- Probation gates in `non_crypto_policy.py`; production off
- **Action:** `EQUITY_PEAD_ENABLED=1` paper-only on GOOGL/MSFT/AAPL post-beat; feed `data/earnings/*/latest.json`; 5–10d hold (not 30d harness window); cross-filter with UEPS (GOOGL in top-8 longs)

### 3. UEPS fundamentals (quality filter, not timing)
- 22 real fundamental LONGs (ADBE rank-1, GOOGL, META…)
- **Action:** use as conviction overlay on #1/#2; fix value_screener universe (today n=1) before standalone sizing

---

## Fast-week playbook (no months of waiting)

1. **Day 1:** Block `regime_terminal` EQUITY emissions; start MeanReversionBB-only paper book.
2. **Day 2–3:** Enable PEAD shadow on 4 cached tickers; log drift vs SPY 5d/10d.
3. **Day 5:** Resolve paper trades; require n≥10 closed with PF>1.2 before any live capital.
4. **Do not:** unban `stocks_rsi2_pullback`, re-enable `yahoo_analyst_consensus`, or size on pf_registry n=5 no-loss sleeves.

**Reproduce:** `python3 tools/strategy_tier_tracker.py`; DB query on `at_pick_outcomes WHERE asset_class='EQUITY'`.
