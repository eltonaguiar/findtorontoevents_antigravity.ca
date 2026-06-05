# Mercury 2 scrutiny framework → gap analysis vs our current engine

**Source:** Mercury 2 (Inception Labs) — audit-toolkit response on how professional quants validate picks.
**Our current engine:** `tools/per_class_scrutiny_engine.py` (6 axes, post-this-session) + `prediction-market-risk-review` skill (5 gates) + memory-stored corroboration patterns.

This is a **gap-by-gap mapping**: what Mercury proposes vs what we have, plus the 3 highest-leverage adds we should ship next.

---

## Coverage matrix

| Mercury axis | Our equivalent | Status | Gap to close |
|---|---|---|---|
| Corporate-action / split adjustments | `audit_trail/reverse_split_symbols.py` + `outcome_resolver` v2.1 | ✅ partial | Gemini's V3 yfinance auto-fetch crashed; clean version on resolver.py uncommitted (whose work?) |
| Ticker-resolution / symbol validation | `audit_trail/quality_gates.py` source bans | ✅ | Sufficient |
| Timestamp alignment | INCIDENT #91 dedup (composite-key) | ✅ partial | dedup only on `at_signal_outcomes`; `trading_picks` dedup script shipped this session (`tools/trading_picks_dedup_incident_91.py`) but not yet applied |
| Missing-data handling | `closed_at IS NOT NULL` filter | ✅ | Sufficient |
| Transaction-cost model | `pf_registry.by_asset_class_policy_clean_net` (net-of-slippage) | ✅ | Already net |
| Binomial / Wilson CI on WR | `tools/per_class_bootstrap_edge.py` (WR_lo95) | ✅ | Sufficient |
| **Bootstrap Sharpe (10k permutations)** | — | ❌ | **HIGH-LEVERAGE GAP** |
| Skew / kurtosis check | `pf_without_top_2_wins` (proxy for fat-tail) | ⚠️ | **MEDIUM-LEVERAGE GAP**: kurtosis > 5 catches strategies our fat-tail proxy doesn't |
| Walk-forward (rolling 2y/6m) | 50/50 half-split OOS | ⚠️ partial | Rolling window is stronger; ours catches lab-vs-forward but not regime drift mid-stream |
| Monte-Carlo shuffled-return Sharpe | `mlflow_bias_detector.py` (per memory, window-artifact detector) | ✅ partial | Mercury proposes 10k shuffles per strategy; ours flags windows but doesn't quantify Sharpe-rank vs null |
| Cross-validation across assets (5-fold) | Per-symbol concentration check | ⚠️ | **MEDIUM-LEVERAGE GAP**: we check single-symbol % but not "does the strategy work if you exclude each symbol in turn?" |
| FDR / Benjamini-Hochberg multiple-testing | — | ❌ | **LOW-LEVERAGE**: only matters if we're scanning N=hundreds of strategies; for the ~5 candidate sleeves under T2 review it's overkill |
| HHI position concentration | `max_single_day_share`, `max_symbol_share` | ⚠️ | Math is `Σ(w_i²)` — formalize this as a single number ≤ 1.0 |
| Factor regression (Fama-French, momentum) | — | ❌ | **HIGH-LEVERAGE GAP** for EQUITY: half our "edges" might just be SPY/QQQ momentum exposure (QQQ LONG 87.5% WR = bull-market correlation, already flagged) |
| Maximum drawdown (MDD) | `money_ready_verdict.json::classes.*.mdd` | ✅ | Already tracked |
| Sharpe / Sortino | `pf_registry` + manual | ✅ partial | Sortino not yet broken out |
| Turnover & frequency | — | ❌ | **LOW-LEVERAGE**: paper-only right now; matters at real-money sizing |
| Liquidity filter (ADV > 10× trade size) | — | ❌ | **HIGH-LEVERAGE** when promoting (our mega_mutation 8-altcoin basket has unknown ADV — already flagged in `RISK_REVIEW_MEGA_MUTATION_2026-06-05.md` mitigation #2) |
| Execution simulation (book depth) | — | ❌ | Defer to real-money phase |
| Stress-test (Covid 2020, crypto 2022) | — | ❌ | **MEDIUM-LEVERAGE**: lab backtests probably already include 2022 crypto winter; verify per strategy |
| Independent code review | `pr-reviewer` subagent + cross-AI peer | ✅ | Sufficient |
| Live-paper vs live-trading shadow | Forward pilot framework | ✅ partial | Live-real shadow not yet — operator gate |
| Risk-budgeting (vol-parity) | `kelly_per_pick` (per skill `money-maker-readyv2`) | ⚠️ | Per-pick, not per-sleeve |
| Model-risk register | memory/*.md + this report | ⚠️ partial | Per-incident register not consolidated |

---

## Top 3 highest-leverage additions to ship

### 1. Bootstrap Sharpe permutation test (P0)

**Mercury formulation:** shuffle daily returns N=10,000 times, recompute Sharpe each iteration, locate observed Sharpe in the null distribution. The p-value is `% of shuffled Sharpes >= observed`.

**Why it beats our current bootstrap WR_lo95:**
- WR_lo95 tests whether wins/total exceeds 50% in distribution — but a strategy can hit WR>50% from clustered small wins + one big loss (net negative Sharpe).
- Sharpe permutation tests whether the **shape of returns** is non-random, not just the directional success rate.
- Catches strategies that look great on WR but bleed on Sharpe (and vice versa — `myfxbook_retail_contrarian` PF=3.79 with WR=48% would fail).

**Implementation cost:** ~50 LOC in a new tool `tools/bootstrap_sharpe_significance.py`. Reuses the `closed_at IS NOT NULL` dedup'd PnL series we already pull.

### 2. Factor regression for EQUITY/ETF (P0)

**Mercury formulation:** regress strategy returns on Fama-French 3-factor + momentum (UMD) + low-volatility. If alpha disappears, it's not edge — it's beta to a known factor.

**Why it's urgent:**
- `QQQ LONG n=8 WR 87.5%` was flagged this session as a 2.5-month bull-market correlation, not edge. Factor regression would have surfaced this without manual inspection.
- `SPY LONG n=12 WR 66.7%` same risk.
- Half of our EQUITY "edges" likely have FF3 alpha = 0 once you account for the bull beta.

**Implementation cost:** ~80 LOC + pulling FF factor returns from yfinance or Ken French's website. Already have `statsmodels` per Session 1 stack notes.

### 3. Liquidity (ADV) gate before any sizing decision (P1)

**Mercury formulation:** average daily volume > 10× position size.

**Why it's urgent for our specific bridge candidate:**
- `mega_mutation` 8-altcoin basket: JUP, WIF, RENDER, STX, ENA are mid-cap to small-cap alts. WIF and ENA can have ADV < $50M on quiet days.
- At even $25k position size per leg, we'd be moving the market on the small ones.
- Already named as mitigation #2 in `RISK_REVIEW_MEGA_MUTATION_2026-06-05.md` — this would formalize the gate.

**Implementation cost:** ~40 LOC pulling 30d ADV via Binance API + simple JSON output `audit_dashboard/data/liquidity_gate_latest.json`.

---

## What we'd NOT add (despite Mercury suggesting)

- **FDR/Benjamini-Hochberg** — only meaningful when scanning 100+ strategies in parallel for promotion. We have 5-8 active candidates under formal review; family-wise correction is overkill.
- **Turnover constraints** — paper-only right now; defer to real-money phase.
- **Execution simulation with order-book depth** — same as above; defer.
- **Independent code review in different language** — Mercury suggests a "shadow implementation in another language." Our cross-AI peer-review (DeepSeek, Grok, MiniMax, multi-Claude) accomplishes the equivalent within Python.

---

## Honest self-assessment

What we already do well (Mercury would approve):
- ✅ Forward paper pilot with started_at honesty (`luxalgo` + `mega_mutation` fix)
- ✅ INCIDENT #91 composite-key dedup (catches the resolver-replay row inflation)
- ✅ Cross-AI peer review (3+ engines on key claims)
- ✅ Memory-of-failures pattern (`memory/MEMORY.md` indexes refutations)
- ✅ Skill-based gates (`prediction-market-risk-review` formalizes pre-promotion checks)

What we're STILL missing after this gap analysis closes:
- ❌ Intrabar OHLC replay (1m/5m bars) — `MASTERPLAN_JUNE52026_CLAUDE.MD` Session 2 names this as THE upstream T2 blocker
- ❌ Cross-PC gateway → real-money shadow (small real account alongside paper)
- ❌ Operational kill switch wired to `/audit/incidents.html` P0 auto-file

---

## Recommended next PRs (operator can pick the order)

1. **`tools/bootstrap_sharpe_significance.py`** + JSON output → wire into `per_class_scrutiny_engine.py` as axis #7
2. **`tools/factor_regression_alpha.py`** for EQUITY/ETF → blocks promotion if FF3+UMD alpha p-value > 0.05
3. **`tools/liquidity_adv_gate.py`** → formal mitigation #2 of mega_mutation risk review
4. **Intrabar replay** — Session 2 Action #3 of `MASTERPLAN_JUNE52026_CLAUDE.MD` (THE upstream blocker; biggest single-PR impact)

Filed by `/loop` blitz at 2026-06-05 ~07:00Z. Source: Mercury 2 (Inception Labs) shared via operator.
