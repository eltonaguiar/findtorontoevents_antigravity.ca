# COT Paper Pilot — Testing + Backtesting Plan for Statistical Edge Proof

**Strategy:** `cot_positioning` on `CT=F` (ICE Cotton Futures)
**Generated:** 2026-05-12
**Author:** Claude Code SUPREME EDGE session
**Status:** DRAFT — awaiting agent-swarm cross-review

## Hypothesis under test

> The `cot_positioning + CT=F` edge that scored DSR=1.0000 (Lopez de Prado AFML eq 14.5) on n=100 closed picks (WR 90%, Sharpe +1.377) is a **real, statistically-validated, persistent edge** that will produce net positive P&L in forward live trading at futures-contract sizing.

**Null hypothesis (H0):** The 90% WR is sample-window luck; OOS performance reverts to coin-flip (45-55% WR) or worse.

**Alternative hypothesis (H1):** The 90% WR holds within ±10pp on a strict OOS window AND the per-trade net P&L falls within $3-15/contract band predicted from contract-scaling math.

## Why this matters

User accepted single-class deviation per Codex governance 2026-05-12. cot_positioning + CT=F is the #1 candidate for first real-money LIVE_EXECUTION. Before risking capital, we must independently verify:

1. The DB-reported edge is NOT a data artifact (Agent E's synthetic-data concern was partially debunked but warrants test gates).
2. The edge persists OOS (Lopez de Prado AFML methodology).
3. Per-trade economics match the futures-contract math ($3.40-$13.40 net per trade).
4. Risk-of-ruin under realistic capital ($5-15k starter) is acceptable.

## 7-step validation pipeline (mandatory before any LIVE_EXECUTION sizing)

### Step 1 — Reproducibility audit (pass/fail gate, 1h)

**Goal:** Confirm the n=100 / WR 90% claim reproduces under independent queries.

**Actions:**
- Re-run `tools/anti_overfit_audit_sidecar.py --min-n 20` and verify cot_positioning DSR still ≥0.95
- Independent SQL query (different session) against `trading_picks`:
  ```sql
  SELECT status, COUNT(*) FROM trading_picks
   WHERE strategy='cot_positioning' AND symbol='CT=F'
     AND status IN ('WON','LOST','WIN','LOSS','TP_HIT','SL_HIT')
   GROUP BY status
  ```
- Expected: 90 WON + 10 LOST = 100 total (matches Agent A DB probe 2026-05-11)

**Pass criterion:** WR within ±5pp of 90%.

### Step 2 — Data-integrity audit (pass/fail gate, 1h)

**Goal:** Verify the 100 closed picks are NOT synthetic.

**Actions:**
- Query `trading_picks` for cot_positioning + CT=F: check `exit_price=0` count, `pnl_pct=0` count, weekend `created_at` count, whole-dollar entry/exit prices.
- Cross-reference `created_at` against CFTC COT publication calendar — every CFTC release falls on a Friday 3:30pm ET. Picks created within 1 trading day of a CFTC release pass.
- Spot-check 10 random closed picks: do the entry/exit prices match historical CT=F closes (within 1%)?

**Pass criterion:** 0 zero-PnL rows, 0 missing exits (already confirmed by Agent A); ≥80% of created_at timestamps fall within 0-3 trading days post-CFTC release.

### Step 3 — Walk-forward OOS test (statistical gate, 2h)

**Goal:** Validate edge persistence under combinatorial purged cross-validation (CPCV).

**Actions:**
- Split 100 closed picks into 10 folds (chronologically).
- For each fold-as-OOS-holdout configuration: compute WR + PF on held-out 10 picks.
- Compute WR variance across all 10 OOS folds.

**Pass criterion:**
- Mean OOS WR ≥ 75% (allows 15pp regression from training-set 90%).
- WR variance across folds ≤ 15pp.
- Worst fold ≥ 60% WR.
- At least 8 of 10 folds beat 50% WR.

### Step 4 — Deflated Sharpe Ratio re-verification (statistical gate, 30 min)

**Goal:** Confirm DSR≥0.95 holds under more conservative `n_trials` assumption.

**Actions:**
- Re-run `deflated_sharpe(sharpe=1.377, n_trials=131, returns_array=...)` per Lopez de Prado AFML eq 14.5 (131 = total systems in dashboard payload — more conservative than 42 default).
- Re-run with n_trials=500 (penalty for multiple comparisons across mutation-axis variants).

**Pass criterion:** DSR ≥ 0.85 even at n_trials=500.

### Step 5 — Sample-window robustness (statistical gate, 30 min)

**Goal:** Confirm edge holds on recent windows, not just the full 100-pick sample.

**Actions:**
- Compute WR + PF on:
  - Full 100 picks
  - Last 60 picks (~60% sample)
  - Last 30 picks (~30% sample)
- Confirm WR drift ≤ 10pp across windows.

**Pass criterion:** Last-30 WR ≥ 80% (allows 10pp drift from full-sample 90%).

### Step 6 — Forward paper-pilot (live gate, 4 weeks)

**Goal:** Observe edge persistence on NEW closed picks emitted post-test.

**Actions:**
- Run `alpha_engine/strategies/cot_paper_pilot.py` weekly post-CFTC release.
- Accumulate ≥4 NEW closed CT=F picks (typically 1 per week).
- Track rolling P&L in `audit_dashboard/data/cot_paper_pilot_status.json`.

**Pass criterion:**
- After 4 weeks: ≥3 of 4 new picks closed
- Net P&L per contract within tolerance band ±50% of expected mid ($8.40) = [$4.20, $12.60]
- WR ≥ 75% on new picks

### Step 7 — Risk-of-ruin Monte Carlo (statistical gate, 1h)

**Goal:** Confirm capital tier survives realistic worst-case sequences.

**Actions:**
- Bootstrap 10,000 simulated 50-trade sequences from the 100-pick PnL distribution.
- For each, compute drawdown trajectory + final P&L at $5k / $10k / $25k starter.
- Compute probability of margin call at each tier.

**Pass criterion:**
- $10k starter: probability of margin call < 5% over 50-trade sequence
- $25k starter: probability of margin call < 1%

## Disqualifying conditions (any one = NO REAL MONEY)

- Step 1 fails reproducibility
- Step 2 finds >10% synthetic-data signature
- Step 3 walk-forward mean OOS WR < 75%
- Step 4 DSR drops below 0.85 at conservative n_trials
- Step 5 last-30 WR drops below 80%
- Step 6 forward paper-pilot WR < 75% on ≥4 new picks
- Step 7 margin-call probability > 5% at $10k tier

## Auxiliary verification (recommended but not gating)

### Independent academic cross-check
- Replicate Miffre 2010 (SSRN 1127213) commodity carry+momo double-sort on CT=F alone. Expected α 21% annualized class-wide should map to a multiple of cot_positioning at CT=F sub-edge.
- Cross-check against current `tools/research/commodity_carry_momo.py` output (live result: NG=F SHORT signal). Does cot_positioning agree?

### External COT consensus check
- Pull CFTC current-week COT data from public API (NDelventhal/cot_reports repo).
- Compare current commercial-net positioning to the threshold the strategy uses.
- Sanity-check: is the strategy's "long" signal currently aligned with commercials' net-long state?

### Brokerage validation
- Confirm at least 3 retail brokers offer CT=F: Interactive Brokers ✓ ($1,200 margin), TD Ameritrade ✓ (~$1,500), AMP Futures ✓ (~$1,000)
- Verify commission per round-trip is at most $5/contract (Interactive Brokers Tiered: $0.85/contract + exchange fees ~$2.50)

## Statistical thresholds summary

| Gate | Metric | Pass threshold |
|---|---|---|
| Reproducibility | WR | within ±5pp of 90% |
| Data integrity | zero-PnL rows | <10% |
| Walk-forward | mean OOS WR | ≥75% |
| Walk-forward | WR variance | ≤15pp |
| Walk-forward | worst fold | ≥60% |
| DSR (conservative) | DSR | ≥0.85 at n_trials=500 |
| Recent window | last-30 WR | ≥80% |
| Forward paper-pilot | new-pick WR | ≥75% on ≥4 new picks |
| Forward paper-pilot | per-trade $ | [$4.20, $12.60] net |
| Risk-of-ruin | margin-call prob | <5% at $10k tier |

## Estimated total testing time

| Step | Time | Type |
|---|---|---|
| 1. Reproducibility | 1h | code + SQL |
| 2. Data integrity | 1h | SQL spot-checks |
| 3. Walk-forward CPCV | 2h | code + analysis |
| 4. DSR conservative | 30m | re-run validator |
| 5. Sample-window | 30m | SQL + plot |
| 6. Forward paper-pilot | **4 weeks** | passive observation |
| 7. Risk-of-ruin MC | 1h | code + plot |
| **Total active work** | **~6h** | + 4-week passive wait |

## Codex state-machine transitions

```
REHAB  ──[Steps 1-5 pass]──>  OOS_READY  ──[Step 6 4wk pass]──>  SHADOW  ──[Step 7 + user approval]──>  LIVE_ELIGIBLE
                                                                                                                │
                                                                                                                ▼
                                                                                                  $5-15k capital, 1 contract live
```

## Open questions for swarm review

1. Is the WR ≥75% mean OOS threshold appropriate, or should we demand ≥85%? (Conservative answer = 85%; aggressive = 70%)
2. Is 4 weeks paper-pilot enough? (Antonacci GEM uses 90 days post-discovery; Lopez de Prado AFML suggests 6 months for novel signals)
3. Should we replicate the strategy code from scratch as an independent implementation, OR is using the existing trading_picks rows sufficient?
4. Does the microscopic per-trade PnL ($3.40 net) survive real-world slippage on a $35k notional?
5. Should we paper-pilot KC=F (coffee, Agent A confirmed n=95 WR 93.7%) in parallel as a diversification check?
6. Is anti_overfit_audit_sidecar's DSR using returns_array correctly for monthly-frequency COT signals? (DSR variance assumes IID returns)
7. What's the right time-stamp for the closing decision — Friday CFTC release T+0, T+1, T+5?

## Verifiable claims log

All numbers above derive from:
- `tools/anti_overfit_audit_sidecar.py` (commit `3e388035b8c`) producing `audit_dashboard/data/anti_overfit_audit.json` with DSR=1.0 on cot_positioning
- `alpha_engine/strategies/cot_paper_pilot.py` (commit pending this turn) producing first-run: n_trades=100, WR=90%, cum_pnl=$344.49, avg=$3.44
- Agent A DB probe 2026-05-11 (transcript in session)
- Antigravity audit walkthrough.md / money_maker_ready_2026-05-11.md.resolved at `C:\Users\zerou\.gemini\antigravity\brain\506d900a-9cc5-461c-9f3a-e39405ae5a00\`

## Recommended next actions

1. Ship this plan to GitHub main + FTP for review
2. Dispatch agent-swarm cross-review (target: `/swarm-second-opinion` or `tools/swarm` with 3-engine consensus on Steps 3, 6, 7 specifically)
3. Build the audit_dashboard/paper_pilot.html viewer page
4. Wire nav pill from `/audit/` to `/audit/paper_pilot.html`
5. Add the cot_paper_pilot.py script to hourly cron in audit-dashboard.yml
6. After swarm-review, execute Steps 1-5 (active work) before next-Friday CFTC release
7. Step 6 paper-pilot starts naturally on next-Friday signal emission
