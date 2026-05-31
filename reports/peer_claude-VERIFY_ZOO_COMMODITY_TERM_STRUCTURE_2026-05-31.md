# VERIFY ZOO COMMODITY_TERM_STRUCTURE CANDIDATE — 2026-05-31

**Reviewer:** claude-opus (peer)
**Subject:** Zoo's master report claim — "ONE statistically valid edge found: commodity_term_structure (n=247, PF=1.06, p=0.0098)"
**Verdict:** **NOT_AN_EDGE / RESEARCH-SIDECAR_NOT_LIVE** (12th independent candidate verification today; 12th rejection)

---

## TL;DR

Zoo's master report (`updates/2026-05-31-MASTER_AUDIT_TRUTH_LAYER_REPORT.md`) elevates `commodity_term_structure` to "one viable edge" status. Independent verification falsifies the elevation on five independent grounds:

1. **Does not exist in production `trading_picks`** — 0 rows in live DB (`ejaguiar1_stocks.trading_picks WHERE strategy LIKE '%commodity_term_structure%'` returns n=0).
2. **It is an opt-in research sidecar**, registered as H-034 (`reports/hypothesis_registry.json:2032`): *"OPT-IN RESEARCH SIDECAR ONLY. HARNESS-GATED. No caller in any pick-generation / scoring path."* Confirms wire-up rule violation if treated as production edge.
3. **Even taking zoo's own backtest figures at face value (n=247, WR=31.6%, PF=1.064)**, Wilson 95% LB on WR is **0.2612** — far below the 0.50 admissibility threshold.
4. **PF=1.064** is one rounding error from break-even; fails the PF > 1.5 hedge-fund tier-2 threshold.
5. **avg_pnl = −1.06** per zoo's own strategy_audit_summary table (`audit_dashboard/strategy_audit_summary.html:121`). PF>1 with negative avg-pnl indicates fat-tailed positive outliers — a classic survivorship/Monte-Carlo-noise pattern, not a robust edge. zoo's own dashboard already chips it `shadow`.

The p=0.0098 figure could not be reproduced from any JSON in zoo's worktree (`grep -rn "0.0098" --include="*.json"` returns no MC-result hits).

---

## Independent SQL Output

```
strategy_variants found in live DB:
  funding_term_structure
  proven_futures_term_structure_proxy

commodity_term_structure: (0, None, None, None)          # n=0
last_90d_n: (0,)
top_symbols: ()                                          # nothing

proven_futures_term_structure_proxy: (0, None, None, None)   # n=0 closed
funding_term_structure:               (1, 0, -1.870, 0.00)   # n=1, loss
```

The only live siblings have a combined closed-trade n of 1 (a single losing SEI-USD trade on `funding_term_structure`).

---

## Wilson Lower Bound

Using zoo's own claimed n=247, wins=78 (31.6% WR):

```
Wilson 95% CI: [0.2612, 0.3764]
LB > 0.50?     False  (LB is below 0.27)
```

The Wilson LB at the claimed numbers is **below the no-skill 50% line by a 24-pp margin** — this strategy is **negative-WR with statistical confidence**, the opposite of an edge. Whatever the MC p-value, it can at best say "this strategy is consistently bad at directional prediction." A positive PF with negative WR is fragile, depending on a few outsized winners — the textbook setup for the same "regime-fragile" pattern that killed COMMODITY today (CT=F 57% concentration, PF 0.31, WR 11% on n=28).

---

## Cross-Reference to Today's COMMODITY Findings

- **PR #182 retire list** falsified `cot_positioning` and other CT=F-dominated strategies on 2026-05-13.
- **COMMODITY 90d live performance**: PF 0.31, WR 11%, n=28, CT=F 57% concentration (per CLAUDE.md MAJOR GOAL banner data).
- Zoo's own report Agent 1 finding: "62 COMMODITY picks excluded by resolver `RESOLVE_FAILED_MAX_RETRIES`, inflating dashboard WR from 60.2% to 85.5%" — yet uses unresolved/research backtest figures to declare an edge in the same class. This is internally inconsistent.

---

## Convergence Note (Genuine)

The valuable signal from zoo's swarm is not the candidate — it's the **convergence on zero edges**:

- Zoo's Agent 5 (Truth Filter): **0/138** active picks pass `n≥100, 30d WR≥50%, Sharpe≥0.3`.
- Zoo's Agent 3 (Rolling-100 audit): **+313.43% is artifact**; actual rolling-100 is **−0.15%**.
- Zoo's Agent 2 (ML calibration): high-confidence bands inverted (COMMODITY 0.75–0.80 conf → 8.3% WR; CRYPTO conf>0.90 → 0% WR).

This is the **11th independent NO_EDGE source today** alongside this session's 10 prior NO_EDGE confirmations. The aggregate signal is robust; the single-candidate elevation is not.

---

## Verdict

**VERIFIED FAILURE on all 4 admissibility checks + ALREADY_RESEARCH_SIDECAR_NOT_LIVE.** Recommend zoo's report be amended to: "Zero live edges; one research-backtest candidate (n=247, WR 31.6%, PF 1.06) that fails Wilson LB and PF thresholds and was already shadow-tier per the strategy audit summary."

| Check | Threshold | Observed | Pass? |
|---|---|---|---|
| n adequate | ≥30 (live) | 0 (1 across siblings) | NO |
| WR Wilson LB | > 0.50 | 0.2612 | NO |
| PF | > 1.5 | 1.064 | NO |
| Concentration | top symbol < 50% | n/a (no live trades) | INSUFF |
| Wire-up | live caller | research sidecar (M-107) | NO |

Reproducer:
```bash
python3 -c "
import pymysql
c = pymysql.connect(host='mysql.50webs.com',user='ejaguiar1_stocks',
                    password='stocks1234560',database='ejaguiar1_stocks')
cur = c.cursor()
cur.execute(\"SELECT COUNT(*) FROM trading_picks WHERE strategy LIKE '%commodity_term_structure%' AND closed_at IS NOT NULL\")
print(cur.fetchone())  # (0,)
"
```

— claude-opus, 2026-05-31
