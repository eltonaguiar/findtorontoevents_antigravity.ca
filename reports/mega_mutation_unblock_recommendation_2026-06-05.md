# mega_mutation Unblock Recommendation — 2026-06-05

## Current Status
`mega_mutation` and `genome_mega_mutation` are in `alpha_engine/strategy_blocklist.py` (lines 211, 216) since 2026-06-02.

## Block Rationale (June 2)
- 141 rows with sign-flipped pnl_pct (reported as T1 but true PF=0.67 after recompute)
- 142 sign-flips in kimi_signal_tracking (same root cause)
- Evidence: `reports/sign_coherence_2026-06-02.json` — 367 total flips

## Evidence Supporting Unblock (June 5)

### 1. Sign Coherence — CLEAN
- `reports/sign_coherence_2026-06-04.json`: 0 flips across 32,447 scanned rows
- `reports/sign_coherence_2026-06-05.json`: 0 flips across 32,628 rows
- Live DB verification (2026-06-05): `long_should_lose_pos=0, long_should_win_neg=0, short_should_lose_pos=0, short_should_win_neg=0` for all 296 mega_mutation rows

### 2. Scrutiny — 5/5 Axes
From `reports/per_class_scrutiny_20260605.json`:
- **Concentration**: PASS (max_share=16.4% DOTUSDT, well under 30% HHI gate)
- **Fat-tail**: PASS (top3_share=16.3%)
- **OOS Stability**: PASS (h1_pf=3.16, h2 has sufficient trades)
- **Batch Artifact**: PASS (max_date_share spread across 39+ unique dates)
- **Binomial**: PASS (p=0.036, n=295, WR=64.1%)

Stats: n=295, WR=64.1%, PF=3.16, avg_pnl=487bp

### 3. Intrabar OHLCV Replay — Edge Confirmed
From `reports/intrabar_replay_mega_mutation_20260605.json`:
- Conservative PF = **2.72** (keeps only sustained + no-data exits)
- 11.5% wick-only exits (16/139 evaluated trades)
- Verdict: **EDGE HOLDS under conservative fills**

### 4. Operational Status
- Genome tracker runs hourly (`mega-mutation-tracker.yml`)
- Currently 0 OPEN picks — no signals firing in current market regime (EMA/MACD entry conditions not met)
- Unblocking is operationally no-op until signals fire again

## Recommendation

**Remove `mega_mutation` and `genome_mega_mutation` from `strategy_blocklist.py`** subject to operator review.

Surgical change (2 lines to remove):
```python
# lines 211 and 216 in alpha_engine/strategy_blocklist.py
"mega_mutation",
"genome_mega_mutation",
```

### Pre-conditions
- [x] Sign coherence clean (June 4+, 0 flips)
- [x] 5/5 scrutiny axes pass
- [x] Intrabar replay confirms PF>2 under realistic fills
- [ ] Operator review and approval
- [ ] At least 1 new forward pick generates and closes correctly post-unblock

## Risk
Low. Unblocking only affects FUTURE picks from the genome tracker. Historical trades are unchanged. If new picks show sign issues, the daily sign-coherence check (`reports/sign_coherence_*.json`) will catch it within 24h. The auto_shutdown_monitor.py daily cron will flag if rolling Sharpe drops below 0.5.

## Note on kimi_signal_tracking
kimi_signal_tracking also had sign flips (142 on June 2 → 0 on June 4). However, it has severe batch artifact (80.4% of trades on 2026-04-10) which makes the WR/PF numbers unreliable. Recommend keeping kimi_signal_tracking blocked until >3 months of forward data without batch artifact.
