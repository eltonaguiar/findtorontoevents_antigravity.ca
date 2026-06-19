# KILO ACTION PLAN — 2026-06-12

**Author:** Kilo (mimo-v2.5-free)  
**Status:** READY FOR EXECUTION  
**PR:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/563  

---

## SITUATION

The trading prediction system at findtorontoevents.ca/audit has **no profitable picks per asset class** after months of development. The system produces 181K trades with 32.3% win rate (worse than coin flip). Multiple interconnected problems create an illusion of profitability while hiding real losses.

---

## PHASE 1: EMERGENCY STABILIZATION (This Week)

**Goal:** Stop the bleeding. Reduce losses by 50% within 7 days.

### 1.1 Kill the #1 Value Destroyer

| Action | Command | Impact | Effort |
|---|---|---|---|
| Disable kimi_riseoftheclaw | Set `KIMI_RISEOFTHECLAW_ENABLED = False` in config | Removes 76% of noise picks (28.4% WR) | 1 hour |
| Verify disable | Check `at_signal_outcomes` for new kimi picks = 0 | Confirm kill worked | 15 min |

**Evidence:** kimi_riseoftheclaw produces 138,878 picks at 28.4% WR. Disabling it immediately removes the single largest drag on system performance.

### 1.2 Fix the Scoring Inversion

| Action | Command | Impact | Effort |
|---|---|---|---|
| Investigate scoring logic | Query `trading_picks` WHERE confidence ≥ 0.90 | Confirm high conf = low WR | 2 hours |
| Invert the scoring | Reverse the confidence weighting | High conf = high WR | 4 hours |
| Test on paper | Run inverted scoring for 48 hours | Verify improvement | 2 days |

**Evidence:** Confidence ≥0.90 → 14.4% WR. Confidence 0.50-0.60 → 60.3% WR. The scoring system is anti-predictive.

### 1.3 Wire the Kill Gate

| Action | Command | Impact | Effort |
|---|---|---|---|
| Connect kill_gate.py to production | Add kill_gate checks in quality_gates.py pass points | Auto-kill bad strategies | 4 hours |
| Set kill criteria | WR < 35% over 50 trades = automatic kill | Prevents value destruction | 1 hour |
| Test kill gate | Run on paper for 48 hours | Verify it works | 2 days |

**Evidence:** `audit_trail/kill_gate.py` exists but isn't wired into production. Bad strategies continue to emit picks indefinitely.

### 1.4 Fix Double-Stamping

| Action | Command | Impact | Effort |
|---|---|---|---|
| Fix make_pick_id() | Include entry_price in `universal_pick_resolver.py` | Prevents duplicate counting | 2 hours |
| Re-resolve affected picks | Run re-resolution on duplicates | Clean up data | 4 hours |

**Evidence:** BNBUSDT+prediction_market_consensus has 687 duplicate picks. This inflates strategy volumes and win rates.

### 1.5 Cut Position Sizes

| Action | Command | Impact | Effort |
|---|---|---|---|
| Reduce max position size | Set `MAX_POSITION_PCT = 0.01` (1% per pick) | Cuts risk by 50% | 1 hour |
| Set max portfolio drawdown | Set `MAX_PORTFOLIO_DD = 0.10` (10%) | Hard stop on losses | 1 hour |

**Evidence:** Current system has no portfolio-level risk limits. One bad strategy can destroy the entire portfolio.

---

## PHASE 2: STATISTICAL VALIDATION (Week 2-3)

**Goal:** Identify the 5 core ideas that actually work. Prove they're not overfit.

### 2.1 Kill Losing Strategies

| Action | Command | Impact | Effort |
|---|---|---|---|
| Query all strategies | `SELECT strategy, COUNT(*), AVG(pnl_pct) FROM trading_picks GROUP BY strategy` | Identify losers | 1 hour |
| Kill WR < 35% | Set status='KILLED' for strategies with WR < 35% over 50+ trades | Remove value destroyers | 2 hours |
| Kill negative PnL | Set status='KILLED' for strategies with total PnL < 0 over 50+ trades | Remove net losers | 2 hours |

**Strategies to KILL immediately:**
- copy_hl_lb_None (38.6% WR, -961.43% total PnL)
- futures_momentum (43.4% WR, -876.83% total PnL)
- cta_cross_asset_tsmom (51.2% WR, -345.62% total PnL)
- smart_money_accumulation (38.5% WR, -220.45% total PnL)
- ml_enhanced_DYDXUSDT (42.6% WR, -254.27% total PnL)

### 2.2 Run Significance Tests

| Action | Command | Impact | Effort |
|---|---|---|---|
| Calculate p-values | Use binomial test for each strategy | Statistical proof of edge | 4 hours |
| Calculate Sharpe ratios | Daily returns → annualized Sharpe | Risk-adjusted performance | 4 hours |
| Calculate max drawdown | Peak-to-trough analysis | Worst-case scenario | 2 hours |
| Identify survivors | Strategies with p < 0.05 AND Sharpe > 1.0 | Proven edge | 2 hours |

### 2.3 Backtest with Out-of-Sample Split

| Action | Command | Impact | Effort |
|---|---|---|---|
| Split data 70/30 | Train on first 70%, test on last 30% | Prevent overfitting | 2 hours |
| Run walk-forward | Rolling 30-day windows | Realistic performance | 1 day |
| Compare IS vs OOS | If OOS < 70% of IS, strategy is overfit | Kill overfit strategies | 4 hours |

### 2.4 Document the Edge

| Action | Command | Impact | Effort |
|---|---|---|---|
| Write one-sentence edge | "We buy X when Y because Z" | Clear thesis | 2 hours |
| Identify data source | What exogenous data drives the edge? | Not just price indicators | 2 hours |
| Identify regime | When does the edge work? When does it fail? | Regime awareness | 4 hours |

---

## PHASE 3: DEPLOY WINNERS (Week 3-4)

**Goal:** Scale up proven strategies. Achieve 50%+ WR across focus classes.

### 3.1 Deploy FOREX-1 (Carry + Volatility Gate)

| Action | Command | Impact | Effort |
|---|---|---|---|
| Enable FOREX-1 | Set `FOREX_CARRY_VOL_ENABLED = True` | Deploy proven strategy | 1 hour |
| Set pair filter | Only trade: EURJPY, USDJPY, CADJPY, EURGBP, AUDUSD, GBPJPY, USDCAD, AUDCAD | Top 8 pairs only | 1 hour |
| Set position sizing | 1% risk per trade, max 5% portfolio | Conservative sizing | 1 hour |
| Monitor for 30 days | Track WR, PF, Sharpe | Validate live performance | Ongoing |

**Expected:** WR ~53%, PF ~1.5 based on backtest of 1,385 trades.

### 3.2 Expand EQUITY-1 (Quality Factor)

| Action | Command | Impact | Effort |
|---|---|---|---|
| Expand fundamental universe | Add S&P 500 fundamentals via FMP API | Validate across 500 stocks | 1 day |
| Enable EQUITY-1 | Set `EQUITY_QUALITY_ENABLED = True` | Deploy proven strategy | 1 hour |
| Set filters | ROE > 20%, GM > 40%, PM > 15%, price < 90% of 52w high | Quality + value | 1 hour |
| Monitor for 30 days | Track WR, PF, Sharpe | Validate live performance | Ongoing |

**Expected:** WR ~54%, PF ~3.5 based on backtest of 110 trades (small sample).

### 3.3 Re-engineer EQUITY-2 (PEAD)

| Action | Command | Impact | Effort |
|---|---|---|---|
| Fix risk/reward | Use fixed +3% TP with surprise%-based SL | Fix asymmetry inversion | 4 hours |
| Re-backtest | Run on historical data | Verify improvement | 2 hours |
| Deploy on paper | Paper trade for 30 days | Validate live performance | 30 days |

**Expected:** WR ~60%, PF ~1.5 after fixing the asymmetry.

### 3.4 Paper Trade COMMODITY-9 (CTA Momentum)

| Action | Command | Impact | Effort |
|---|---|---|---|
| Enable paper trading | Set `COMMODITY_CTA_PAPER = True` | Validate without risk | 1 hour |
| Set position sizing | 1% risk per trade, max 5% portfolio | Conservative sizing | 1 hour |
| Monitor for 90 days | Track WR, PF, Sharpe | Validate live performance | Ongoing |

**Expected:** WR ~63%, PF ~5.2 based on backtest (small sample, needs validation).

---

## PHASE 4: BUILD INFRASTRUCTURE (Month 2-3)

**Goal:** Build the tools needed for long-term success.

### 4.1 Build Replay Harness In-Repo

| Action | Command | Impact | Effort |
|---|---|---|---|
| Create replay_harness.py | Entry-anchored, SL-wins-ties, net of costs | Velocity principle becomes real | 1 week |
| Add cost model | 16bp RT crypto, 4bp equity, 2bp FX | Realistic backtesting | 2 hours |
| Add time-split validation | Train on first 70%, test on last 30% | Prevent overfitting | 4 hours |
| Add statistical gates | p < 0.05, Sharpe > 1.0, MDD < 20% | Prove the edge | 4 hours |

### 4.2 Run Walk-Forward Suite

| Action | Command | Impact | Effort |
|---|---|---|---|
| Update walk-forward config | Current is 2 months stale (incident #132) | Fresh validation | 2 hours |
| Run on all surviving strategies | Validate 20-30 strategies | Statistical proof | 1 day |
| Generate report | Walk-forward PF, Sharpe, MDD per strategy | Evidence for promotion | 4 hours |

### 4.3 Consolidate Strategy Count

| Action | Command | Impact | Effort |
|---|---|---|---|
| Audit 324 baby_strategies | Identify genuinely different ideas | Reduce overfitting | 1 day |
| Consolidate to 20-30 | Keep only strategies with different edges | Focus on quality | 1 day |
| Document each edge | One-sentence thesis per strategy | Clarity | 4 hours |

### 4.4 Consolidate Tier Systems

| Action | Command | Impact | Effort |
|---|---|---|---|
| Audit 5 tier systems | Identify which is authoritative | Remove confusion | 4 hours |
| Pick 1 system | Use dashboard_generator.py thresholds | Single source of truth | 1 hour |
| Update all references | Point to authoritative system | Consistency | 2 hours |

---

## PHASE 5: PROVE THE EDGE (Month 4-12)

**Goal:** Achieve 3 asset classes profitable on 12-month rolling basis.

### 5.1 Target Metrics

| Metric | Current | 90-Day Target | 1-Year Target |
|---|---|---|---|
| Overall WR | 32.3% | 50%+ | 55%+ |
| Sharpe Ratio | ~0 | >1.0 | >1.5 |
| Max Drawdown | Unknown | <20% | <15% |
| Profitable Classes | 0/6 | 2/6 | 3/6 |
| Strategy Count | 324 | 30 | 20 |

### 5.2 Weekly Scorecard

| Day | Action | Owner |
|---|---|---|
| Monday | Refresh honest ledger + coverage metrics + H1 structural audit | Dev |
| Tuesday | Score H1-H5 per focus class; pick top hypothesis PER CLASS | Dev |
| Wednesday | Run replay-variant batches on focus classes (FDR-controlled) | Dev |
| Thursday | Plumbing fixes; data additions (shadow lane) | Dev |
| Friday | Weekly scorecard .MD committed; CI guards updated | Dev |

### 5.3 Monthly Review

| Item | Action |
|---|---|
| Performance review | Compare actual vs predicted for each strategy |
| Kill underperformers | Strategies with 3 consecutive null cycles rotate OUT |
| Promote winners | Strategies passing all gates move to production |
| Update playbook | Document what worked, what didn't, what changed |

---

## PHASE 6: LEVERAGE AI SWARM (Ongoing)

**Goal:** Use the AI swarm for peer review and strategy discovery.

### 6.1 Peer Review Swarm

| Action | Command | Impact | Effort |
|---|---|---|---|
| Deploy /PeerReviewSwarmOptions | Use multi-AI review for strategy validation | Reduce bias | Ongoing |
| Run /consult-grok | Get second opinion on findings | Independent verification | Ongoing |
| Run /consult-codex | Get code review on implementations | Catch bugs | Ongoing |

### 6.2 AI Model Selection

| Model | Use Case | Why |
|---|---|---|
| grok3 | Primary pick generation | Only trustworthy AI (67.3% WR, 0% synthetic) |
| deepseek_v4 | Secondary validation | PF=3.72 on tournament |
| cursor_agent | Code generation | Best at implementation |

### 6.3 Avoid Contamination

| Issue | Prevention |
|---|---|
| Synthetic picks | Filter out SYNTHETIC_SEED_ENRICHED picks |
| Mispriced entries | Set max entry drift = 10% from market |
| Single-snapshot bias | Use intrabar OHLC replay (already live 2026-06-04) |

---

## SUCCESS CRITERIA

### 30-Day Success
- [ ] kimi_riseoftheclaw disabled
- [ ] Scoring inversion fixed
- [ ] Kill gate wired into production
- [ ] Position sizes cut by 50%
- [ ] FOREX-1 deployed with pair filter
- [ ] EQUITY-1 expanded universe

### 90-Day Success
- [ ] Overall WR > 50%
- [ ] Sharpe > 1.0
- [ ] 2 classes at PF 95%-CI-lower-bound > 1.15
- [ ] Replay harness built in-repo
- [ ] Walk-forward suite re-run
- [ ] Strategy count consolidated to 30

### 1-Year Success
- [ ] 3 asset classes profitable on 12-month rolling basis
- [ ] Sharpe > 1.5 across focus classes
- [ ] Strategy count consolidated to 20
- [ ] Tier system consolidated to 1
- [ ] Portfolio risk metrics updated nightly

---

## RISK REGISTER

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Scoring inversion fix doesn't work | Medium | High | Test on paper first, have rollback plan |
| FOREX-1 underperforms live | Medium | Medium | Paper trade first, conservative sizing |
| Walk-forward shows all strategies overfit | Low | High | Have backup strategies ready |
| Data quality issues persist | Medium | Medium | Run data quality audit weekly |
| New strategies have hidden bugs | Medium | High | Paper trade for 30 days before live |

---

## APPENDIX: FILES TO READ

| File | Purpose |
|---|---|
| `PLAN_INSIGHTS_KILO_June122026_1236pm.MD` | Full audit findings |
| `KILO_DEEP_DIVE_FINDINGS_2026-06-12.MD` | Root causes and action items |
| `docs/QUANT_FUND_TURNAROUND_PLAYBOOK.md` | Hedge fund turnaround playbook |
| `docs/superpowers/specs/2026-06-12-40-new-strategies-design.md` | 40 new strategy designs |
| `kilo_JUNE112026.MD` | Plan review with evidence |

---

**Plan created:** 2026-06-12 18:48 UTC  
**Next review:** 2026-06-19 (1 week)  
**Author:** Kilo (mimo-v2.5-free)
