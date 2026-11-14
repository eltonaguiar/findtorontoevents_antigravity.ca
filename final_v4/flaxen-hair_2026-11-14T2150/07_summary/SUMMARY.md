# FINAL V4 — Final Review and Findings

**Worktree:** flaxen-hair_2026-11-14T2150 | **Date:** 2026-11-14T21:50Z | **Repo:** findtorontoevents_antigravity.ca

This is the final review stage. It synthesizes final_v3 (common themes, focus decision), local uncommitted files from the last 24 hours, and remote GitHub changes into a single, defensible picture of profitability across all asset classes.

---

## 1. The Bottom Line

| Question | Answer |
|----------|--------|
| Is any approach PROVED profitable? | **No.** 23 hypotheses tested across 4 protocol versions; 0/10 proof score. |
| Is any approach forward-validated? | **Yes — partially:** mega_mutation_macd_rsi on CRYPTO (PF 8.32, WR 84%, n=50 forward). |
| Which asset class should get the first real test? | **EQUITY** — only class clearing its own cost structure (3.23× cost, mean +0.323%, n=738). |
| Which asset class has a fixable defect hiding possible edge? | **CRYPTO** — late stop fills (1.54× planned risk, 98.8% of class loss from one system). |
| Which classes are blocked by arithmetic? | ETF (267% cost/PnL), COMMODITY (422%), FOREX (−16.2pp breakeven gap), BOND (n=35). |
| Are mutual funds a prediction edge? | **No** — they are the equity risk premium, not a signal; structurally untradeable as picks. |

---

## 2. Common Themes from final_v3 (reviewed and confirmed)

All five bug themes from final_v3 carry into v4 unchanged:

| # | Bug | Status | Impact |
|---|-----|--------|--------|
| B1 | Refuted strategy advertised as VALIDATED | FAIL | Highest consequence — misdirects deployment |
| B2 | Same class, 3 counts; ETF WR 2.22% vs 68.42% | FAIL | No canonical cohort definition |
| B3 | Crypto stop fills 1.54× planned risk, 98.8% loss from one system | FIXED today | Fix → breakeven (PF≈1.00), not profit |
| B4 | 40–56% of non-crypto "SL_HIT" never touched the stop | OPEN | Unexplained; do not rank by exit reason |
| B5 | `resolution_method` NULL on all 3,500 rows | FAIL | Exit taxonomy uses wrong field name |
| B6 | 100× PnL unit bug in MySQL sidefiles (not dashboard) | FAIL | Dashboard clean; sidefiles mixed units |
| B7 | FOREX 17.7% non-spot-FX rows; allowlist never enforced | FAIL | Class is a mixture |
| B8 | 170 ledgers, 4 pass at 95% vs 8.5 expected by chance | FAIL | No demonstrated edge in search space |
| B9 | 3 freshness failures (fetch_prices 404 since Apr; signal_outcomes 80d stale; crypto 172d stale) | FAIL | Dead prices fabricate metrics |
| B10 | 53 undecisive rows silently included in naive totals | FAIL | Win rate distortion |
| B11 | Statistical gates exist but unverified in main tree | OPEN | Cannot rely on them yet |
| B12 | `sizing_allowed: false` for all 9 classes; scanner emits anyway | FIXED today | Cost gate now enforced |
| B13 | 360 workflows, 0 concurrency, 0 timeout, schedule collisions | FAIL | Cancel-cascade risk |
| B14 | 6 peer reviews = 1 dataset read 6 times | Epistemics | Not independent confirmation |

---

## 3. Focus Decision from final_v3 (reviewed and confirmed)

**Slot 1 — EQUITY:** Only class with measured positive margin (mean +0.323% per trade, 3.23× cost, n=738). Pre-registered test vs SPY total return, n≥500, OOS Sharpe ≥ SPY Sharpe AND PF ≥ 1.15, stability first-half/second-half PF ≥ 1.05.

**Slot 2 — CRYPTO:** Conditional. Only class with a diagnosed, fixable defect (kimi_riseoftheclaw late fills = 94% of crypto fill leak). Fill fix → PF ≈ 1.00 (breakeven, not profit). Forward-test POSITION horizon only, n≥100, PF ≥ 1.3, WR ≥ 55%.

**Explicitly NOT pursued:** commodity COT tuning (failed 4/4), mutual funds as a class (equity risk premium, not signal), mining more strategies (170 ledgers already sampled), fixing FOREX 16pp gap with entries (structural), turning on more emitting systems.

---

## 4. Local Uncommitted Files — Last 24 Hours (Financial Prediction)

### Files found:

| File | Type | Key Finding |
|------|------|-------------|
| `MARKET_BEATING_REPORT.md` | Auto-generated report | 409 signals, 58.3% accuracy (target 60%), BTC-USD 50%, ETH-USD 64%, SOL-USD 47%, ADA-USD 66.7%, DOT-USD 60%. Status: OPTIMIZING/BELOW TARGET. |
| `dashboard/live_picks.json` | Live picks | 39 active picks across strategies; bond strategies at 0 winners/0.0 PnL; atr_percentile_gate_scanner 6 picks 3 winners +0.0057%; multiple inverse_ml strategies at 0.0. |
| `mercury2/data/metrics_report.json` | ML metrics | 469 closed trades, WR 40.09%, IC(confidence vs PnL): Pearson 0.0391, Spearman 0.1046 — **near-zero linear correlation**, hit_rate@top3/top5 = 0.0, top10 = 20.0%. Quality flags: low_linear_ic, weak_top5_hit_rate. |
| `research/profitability/*` | 23 hypotheses v1-v4 | **0/23 PROVED.** Best: H22 BTC funding carry Sharpe 14.24 but n=10 < 30; H10 RSI(2) Sharpe 1.83 but contaminated OOS, effective N≈38. All not proved. |
| `research/asset_class/equity/*` | Equity backtests | All strategies MIXED or NO_EDGE — tiny samples (3-6 trades), simplified signal parsing, insufficient for robust inference. |

### Local uncommitted git status:
- Modified: `___HELL_HEALTH_OPENCODE.MD`
- Untracked: 40+ files including skills, configs, reports, but only the above are financial-prediction-relevant

---

## 5. Remote GitHub — Origin/main Ahead by 5 Commits

| Commit | Subject | Time |
|--------|---------|------|
| ea7a4c6ed13 | Alpha Engine FAST: 2026-11-14 21:50 [AUTO] [skip ci] | 21:50 |
| 5679f88d0d3 | Sustained Gainer scan: 2026-11-14 21:48 [AUTO] [skip ci] | 21:48 |
| fc8f961811d | Auto-update prediction quality metrics 2026-11-14 21:48 UTC [skip ci] | 21:48 |
| e1db9f5881b | Dashboard pick trader: 2026-11-14 21:47 UTC [skip ci] | 21:47 |
| 489ec2ae9cd | chore: mega mutation tracker hourly update [skip ci] | — |

These are all automated updates — no substantive new profitability claims. The mega mutation tracker hourly update is consistent with the forward validation already documented.

---

## 6. Per-Class Profitability Assessment

| Class | Cost Coverage | Loss Mechanism | n | Verdict |
|-------|--------------|----------------|---|---------|
| **EQUITY** | ✅ 3.23× | ✅ No defect found | 738 | **Slot 1 — test vs SPY** |
| **CRYPTO** | ❌ 0.58× | ✅ Late fills (one system) | 1,966 | **Slot 2 — conditional** |
| ETF | ❌ 0.40× | ✅ Cost ≥ edge | 567 | No |
| FOREX | ❌ −1.94× | ✅ Contaminated + gap | 187 | No |
| BOND | ❌ −4.41× | ⚠️ Exit labels broken | 35 | No |
| COMMODITY | ❌ Thin | ✅ 422% cost ratio | 7 | No |
| MUTUAL FUND | n/a | n/a | 0 | No (equity risk premium) |

---

## 7. Proof Assessment

| Criterion | Score | Basis |
|-----------|-------|-------|
| Pre-registration | 9/10 | Protocol v1-v4 locked before results |
| Data provenance | 7/10 | Binance/Nasdaq/Treasury; manifests + SHA-256 |
| Candidate breadth | 8/10 | 23 candidates; 30 crypto, 50 ETFs, 30 perps |
| Statistical controls | 9/10 | DSR, PBO/CSCV, Bonferroni/BH, bootstrap, walk-forward |
| Independent replication | 8/10 | v1/v2 replicated + adversarial review |
| Verdict honesty | 10/10 | H10 downgraded; failures published |
| **Actual profitability proof** | **0/10** | **No candidate survives clean-OOS + effective-N + capital + execution gates** |
| **Overall** | **7.0/10** | Good science, negative result |

**170 ledgers sampled; 4 pass at 95% vs 8.5 expected by chance. Fewer pass than chance predicts.**

---

## 8. Execution Roadmap (90 days)

| Weeks | Work | Decision Point |
|-------|------|----------------|
| 1 | EQUITY 24-month benchmark test vs SPY; route kimi to resolver; kill crypto SWING | EQUITY alpha or beta |
| 2-3 | Exit-semantics fix (B4); per-class cost gate in CI; freshness gates (B9) | Can we trust the numbers? |
| 4-8 | CRYPTO POSITION forward test (frozen rules, n≥100); commodity momentum-vs-contrarian as new pre-registered trial | Does crypto have signal after fix? |
| 9-13 | Review forward data against gates; publish trial count | Scale or wind down |

**Success at day 90 is not "profitable."** It is one class with a pre-registered, benchmark-relative result and a known trial count — the first point at which "is this profitable?" becomes answerable.

---

## 9. Files in this Package

```
final_v4/flaxen-hair_2026-11-14T2150/
├── README.md                                      ← this file
├── 00_common_themes/                              final_v3 bug themes (B1-B14) + evidence
├── 01_focus_decision/                             final_v3 EQUITY/CRYPTO focus decision
├── 02_local_uncommitted/                          local files from last 24h
├── 03_remote_github/                              remote GitHub state
├── 04_per_class_profitability/                    per-class assessment matrix
├── 05_proof_assessment/                           0/10 proof score breakdown
├── 06_execution_roadmap/                          90-day plan with kill conditions
└── 07_summary/                                    this summary (SUMMARY.md)
```

---

## 10. Final Verdict

**Do not deploy capital to any strategy in this repo today.** The system is not money-ready. The only defensible path forward is:

1. **EQUITY:** Pre-registered 24-month benchmark test vs SPY. If it clears PF ≥ 1.15 and Sharpe ≥ SPY Sharpe with stability, it is the first candidate.
2. **CRYPTO:** Fix kimi_riseoftheclaw fills, kill crypto SWING, forward-test POSITION horizon n≥100. If forward PF ≥ 1.3 and WR ≥ 55%, reconsider.
3. **Everything else:** Blocked by arithmetic. Do not tune commodity COT, add mutual funds, mine more strategies, or fix FOREX entries — these are structural problems, not parameter problems.

The honest status: **unmeasurable is not the same as unprofitable, but it is not profitable either.**
