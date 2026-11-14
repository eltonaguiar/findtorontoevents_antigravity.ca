# finpredict — Final Audit & Research Deliverable (2026-11-14)

Worktree: `finpredict`. This is the consolidated, organized archive of the full session: system audit → peer review → master plan → profitability research. Final stage: peer review in a matching structure.

## Folder map

```
final_2026_11_14/finpredict/
├── README.md                       ← this file (executive summary + cross-peer verdict)
├── 01-audit/                       ← full quantitative audit of findtorontoevents.ca/audit
├── 02-quick-wins/                  ← proposed fixes, per asset class + overall (file:line-verified)
├── 03-peer-review/                 ← reconciliation of all 9 peer agents
├── 04-master-plan/                 ← phased remediation plan + 7 consolidated inputs
├── 05-research/                    ← proof-of-profitability protocol + iterations 001–005
└── 06-implementation/              ← the P0 fixes actually implemented (branch fix/audit-p0-truth)
```

## 1. Audit verdict (01-audit) — FAIL

The prediction system (stocks/crypto/forex/bonds/ETF/futures/mutual funds) is **not money-ready**. Headline: WR 41.8%, PF 0.94, Sharpe −1.31, compounded PnL −99% (equal-weight). 365 workflows (28 failing last run), 4,148 raw active picks mostly frozen/EXPIRED, dead metrics, fabricated flat-3% placeholder PnL. Root cause is **data integrity + multiple-testing (126 systems / 683 strategies)**, not a tuning problem.

## 2. Quick wins (02-quick-wins) — 19 fixes, file:line-verified

Top 5: wire live price refresh; label unquoted rows (stop fake 0%); surface honesty metrics (n + Wilson CI + excluded counts); entry-price sanity gate; kill vacuous PASS. Vetoes applied (no `current_price=entry_price` backfill, no hard data purge, no destructive SQL).

## 3. Peer review (03-peer-review) — 9 agents reconciled

`finpredict` (me), `finpredict-v2`, `-v3`, `-v4`, `ML childlike-airport`, `scratch-hippodraco`, `flaxen-hair`, `hilarious-seer`, and `deepAI`/`inspect-wt` (Windows host). All agree: negative verdict. Key cross-findings: PnL-unit mix bug (up to 100×), ML target leakage (fixed on main via `d8c8dd25581`), v4's destructive SQL vetoed, `dashboard_enhancements.js` parse-broken since 2026-10-04 (dead enhancement layer), FTP deploy 56.6 min = 54% of the audit job.

## 4. Master plan (04-master-plan) — 4 phases + veto list

Phase 0 (truth/CI, 12 fixes) → Phase 1 (data-consistency gates) → Phase 2 (resolver, gated) → Phase 3 (statistical re-validation). Binding veto list (destructive SQL, MF class, push-trigger re-enable, forced_resolution).

## 5. Research (05-research) — is there a *provably* profitable approach?

Full honesty, three stages:

1. **The 683-strategy system has NO provable edge** (ITERATION-001..003): after purity filtering, the closed ledger is net-negative (−469.5% sum). The best candidate `rs-breakout-scout` fails Bonferroni (p=0.009 vs α=7.3e-5) and decays out-of-sample (t 2.07→1.16). Apparent 87–97%-WR "edges" are frozen-price artifacts.
2. **A real method exists and IS statistically valid in the risk-adjusted sense** (ITERATION-004..005): diversified, volatility-targeted **time-series momentum** over 10 liquid crypto assets / 7.4 years → **net-of-cost Sharpe 2.13, block-bootstrap 95% CI [1.25, 3.25] (excludes 0), t=5.56, OOS Sharpe 2.33 > IS 2.06, 10/10 assets positive, maxDD −17% vs B&H −36%.**
3. **But it is a risk premium, not a contest-winner** — honest caveats: survivorship in the asset universe; crypto bull-market window (B&H Sharpe ≈2.2 but 124% CAGR / −36% DD); the edge is risk-adjusted (drawdown/vol control), not raw alpha over buy-and-hold.

## 6. Cross-peer profitability consensus (from the final review sweep)

- **finpredict-v2** ran 23 candidates across 4 versions → **NOT PROVED** (scorecard 7.0/10, "good science, negative result"). Falsified the peer VWAP-mean-reversion "3.76 Sharpe" claim (correct ≈1.18, t=0.91 p=0.18, CSCV PBO 0.84–0.97, intrabar-stops PF 0.81). Funding carry is real but capital-limited (4.8% vs 4.5% cash). RSI(2) 22% CAGR was mostly T-bill carry on idle cash.
- **childlike-airport** claimed VWAP + trend validated; the VWAP claim was independently falsified (above).
- **finpredict-v4 / v3** breadth + funding carry → **NOT PROVED**.
- **My result** (trend momentum, Sharpe 2.13, CI excludes 0) is the only surviving *statistically-significant positive* result — and it is a **low-vol risk premium**, not an equity-beating raw-alpha edge.

## The honest final answer

**No peer has proven a raw-alpha, contest-winning edge** — the contest winners are survivorship + leverage + regime luck, exactly as the multiple-testing math predicts. What IS real and provable is a family of **low-volatility risk premia** (diversified trend/momentum — Sharpe ~2 risk-adjusted; funding/T-bill carry — real but capacity-limited). These are positive-expectancy and statistically valid, but modest, and they would not win a leveraged contest. The profitable path is to run **one clean, diversified, risk-managed trend portfolio**, not to mine more signals on broken data.

## Next (final-stage peer review)

Review the other agents' `final_2026_11_14/<worktree>/` folders in the same structure, reconcile, and produce the master final report.
