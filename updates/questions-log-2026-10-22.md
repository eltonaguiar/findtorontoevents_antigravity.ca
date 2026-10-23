# Questions Log — Investigation of Oct 22, 2026

## Key Questions Asked During This Investigation

### Q1: What winner claims did prior agents (INCEPTION, OpenCode, Grok) make?
- **INCEPTION/VLLM** committed `fix/frozen-exit-resolver` branch — acknowledged the Universal Pick Resolver had a frozen-exit bug.
- **OpenCode** committed two winner certificates to `oc-winning-candidate` branch:
  - `high_trust_momentum` (CRYPTO): n=206, WR=58.7%, PF=1.81
  - `commodity_term_cot` (HG=F): n=815, WR=55.6%, PF=2.29

### Q2: Are those winner claims valid? Did I independently verify?
**Answer:** `high_trust_momentum` — YES. `commodity_term_cot` — NO.
- I queried the DB directly (not trusting JSON certificates).
- I built artifact detection: frozen-exit = multiple picks with same `exit_price` + same `closed_at` timestamp.
- `high_trust_momentum`: only 4 picks (1.9%) in 1 artifact cluster. Clean stats: n=202, WR=57.9% — still passes.
- `commodity_term_cot` (HG=F): 101 picks (12.4%) in 5 artifact clusters. Removing them: n=335, WR=47.2% — FAILS the 50% gate. The edge was an artifact.

### Q3: How do I get database credentials?
- `dbpasses.txt` at `/home/eaguiar2015/dbpasses.txt`
- DB: `mysql.50webs.com`, database `ejaguiar1_stocks`
- Credentials were read directly from the file; environment variables used as fallback.

### Q4: Did the prior agents (INCEPTION, OpenCode) account for the frozen-exit bug?
- **INCEPTION/VLLM**: YES — their branch title is "per-pick price resolution to stop frozen-exit stamping". They identified and fixed the root cause.
- **OpenCode**: NO — their `winner_validation_harness.py` uses `bootstrap_expectancy` / `bootstrap_wr` but I could not find artifact-cluster detection in their code. They accepted raw DB stats including contaminated picks.

### Q5: Why does the dashboard_data.json show contamination but the DB appears partially clean?
- The `at_raw_picks` DB table itself contains frozen-exit stamps. The resolver bug stamped exit prices at resolution time, so the DB already has contaminated data baked in.
- `dashboard_data.json` was generated from this DB, so it inherits the contamination.
- However, `high_trust_momentum` only has 1 minor cluster (4 picks at exit=64801.54 on 2026-07-14). This is likely a legitimate batch resolution (BTC price stalled at that level for one signal), not a massive frozen-exit dump.

### Q6: Are there other strategies with proven edges I haven't checked?
- `top_edges_per_class.json` (Bonferroni-adjusted): CRYPTO had 13 Bonferroni passes — worth a deep dive.
- `entry_conditions_forward.json`: EQUITY low-vol regime shows WR=75.9%, n=79 (below n=100 gate).
- `walk_forward_per_strategy_latest.json`: 3/7 strategies passed (non_crypto_consensus FOREX, unknown crypto, myfxbook_retail_contrarian).

### Q7: How do I independently verify picks' outcomes without the buggy resolver?
- I started building `Binance mirror resolution`: query `at_raw_picks` for entry/tp/sl, fetch 1h OHLCV from Binance, walk forward bar-by-bar checking if TP/SL hits first.
- Result: 3/5 sample picks matched dashboard outcomes. 2 BTC/ADA picks showed WON in my 1h resolution but LOST in dashboard — likely because original resolution used 5m/15m granularity where SL was hit between hourly bars.
- **Lesson:** Need finer-grained (1m or 5m) Binance bars to match original resolution fidelity.

### Q8: What's the strict gate for "proven winner"?
- WR ≥ 50% (statistically above coin-flip)
- PF ≥ 1.15 (meaningful profit factor)
- n ≥ 100 (statistical power)
- Wilson lower 95% WR > 0.40 (break-even threshold)
- Bootstrap P(>0) ≥ 0.95
- Artifact contamination < 3% (frozen-exit clusters)
- Positive expectancy CI lower bound > 0

### Q9: Is high_trust_momentum already wired into the audit dashboard picks?
- **No.** `dashboard_data.json` → `picks.smart_picks` is **EMPTY**. The winner exists in the DB but is NOT surfaced on the live `/audit` dashboard.

### Q10: What's next to prove the edge is real for ongoing production?
- Seed a forward paper-cohort: `paper_trading/paper_cohort_high_trust_momentum.py` that takes NEW `high_trust_momentum` signals and tracks them with live Binance prices.
- Wire `high_trust_momentum` into `strategy_blocklist.py` exclusions + `core_whitelist.json`.
- Create a weekly auto-verification that re-runs the full DB query + artifact detection to ensure the edge hasn't degraded.

*Not financial advice. Research/educational only. Past performance does not guarantee future results.*
