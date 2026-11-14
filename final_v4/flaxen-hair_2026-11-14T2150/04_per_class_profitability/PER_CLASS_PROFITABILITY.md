# Per-Class Profitability Assessment

**Source:** final_v3 focus decision + local uncommitted files + remote GitHub review
**Worktree:** flaxen-hair_2026-11-14T2150

## Assessment Matrix

| Class | Cost Coverage (3× gate) | Loss Mechanism Known? | Decisive n | Cost/PnL Ratio | Mean PnL | Verdict |
|-------|------------------------|----------------------|------------|----------------|----------|---------|
| **EQUITY** | ✅ 3.23× | ✅ No defect; stops respected (0.91×) | 738 | — | +0.323% | **Slot 1** |
| **CRYPTO** | ❌ 0.58× | ✅ Late fills, 94% one system | 1,966 | — | negative | **Slot 2 conditional** |
| ETF | ❌ 0.40× | ✅ Cost ≥ edge (267% of PnL) | 567 | 267% | negative | No |
| FOREX | ❌ −1.94× | ✅ Contaminated + 16pp gap | 187 | negative | −16.2pp gap | No |
| BOND | ❌ −4.41× | ⚠️ Exit labels broken | 35 | −4.41× | negative | No |
| COMMODITY | ❌ Thin | ✅ 422% cost ratio | 7 | 422% | negative | No |
| MUTUAL FUND | n/a | n/a | 0 | n/a | n/a | Excluded |

## Per-Class Detail

### EQUITY — Slot 1

**Why:** Only class clearing its own cost structure. Mean +0.323% per trade against 0.30% requirement. Losses inside plan (0.91× stop fill ratio). Best-behaved exit bucket: TIME_EXIT n=220, WR 61.4%, PF 1.988.

**Risk:** t=1.52, p=0.12 (not statistically significant yet). Second-half PF fell 1.342 → 0.977. Rising-market beta until proven otherwise.

**Pre-registered test:**
- Sample: 24 months, n ≥ 500 closed equity trades
- Benchmark: SPY total return, same window (not zero)
- Gate: OOS Sharpe ≥ SPY Sharpe AND PF ≥ 1.15
- Stability: first-half PF ≥ 1.05 AND second-half PF ≥ 1.05
- Kill condition: fails any line → EQUITY is beta, stop emitting, hold index

### CRYPTO — Slot 2 (Conditional)

**Why not first:** Class loses −837.8pp; 98.8% is fill slippage. Measuring signal quality today is measuring the executor.

**Why worth the slot:** Only class with (a) large, diagnosed, fixable defect and (b) positive sub-bucket (POSITION horizon: n=33, WR 69.7%, PF 3.180, +74.4pp).

**Order of operations:**
1. Route `kimi_riseoftheclaw` through intrabar resolver (resolver_version = NULL; +727.3pp of +832.4pp leak)
2. Kill CRYPTO SWING emission (n=243, PF 0.457, −328.6pp = 39% of class loss)
3. Forward-test POSITION horizon only, frozen rules, n ≥ 100, PF ≥ 1.3, WR ≥ 55%
4. Re-measure before touching any signal — fix expected to reach PF ≈ 1.00 (breakeven, not profit)

### ETF — Blocked

WR spans 2.22% to 68.42% across three live files (85× spread). Cost/PnL = 267%. No path to profitability without fixing measurement first.

### FOREX — Blocked

−16.2pp breakeven gap. 17.7% of rows are not spot FX (44 currency ETFs + 5 EURUSDT crypto pair). Allowlist never enforced. Structural problem — no entry-timing fix closes it.

### BOND — Blocked

n=35 (insufficient for decision). −4.41× cost coverage. Exit labels broken.

### COMMODITY — Blocked

n=7. Cost/PnL = 422%. COT contrarian test failed 4/4 gates. No path.

### MUTUAL FUND — Excluded

Not in ledger (n=0). Not a prediction edge — it is the equity risk premium. Structurally untradeable as picks (daily NAV, next-NAV execution, no intraday TP/SL, frequent-trading limits).

**Procurement view (not research):** broad-market index fund → target-date index fund → money market, screening on expense ratio ≤ 0.20%, no load, no 12b-1, minimum ≤ $1,000, AUM ≥ $1B, turnover ≤ 20%, tracking error ≤ 0.25%.
