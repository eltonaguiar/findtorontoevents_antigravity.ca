# Review — audit3 ("Quant Kill Tribunal"), /audit, and FINANCE_DB_SCHEMA_SPEC
**Date:** 2026-11-19 · **Method:** fetched live pages + `audit3_ledger.json`, `audit3_evidence.json`, branch `docs/finance-db-schema` spec, main `/audit` page. All numbers below are measured, not recalled.

---

## 1. What audit3 is — and the one thing it has to do next

audit3 is the best artifact in the repo: a pre-declared, innocent-until-proven-guilty ledger with Wilson CIs, one-sided binomial vs 50%, 2,000-resample bootstrap net-expectancy CIs after per-class slippage, BH-FDR, split-half stability, concentration caps, and a kill rule that requires **net-CI entirely < 0 AND BH harm q ≤ 0.10**. The discipline is right. Two problems remain:

1. **It can never promote anything.** Forward-classified rows are the only feed it scores (correct), but every gate is tuned to *deny*, and the dashboard shows 0 PROVEN / 0 CANDIDATE. Kill switches that can't also certify "this survived" turn the system into a one-way ratchet to zero. That's statistically safe and strategically sterile.
2. **It's not wired to block emission.** A tribunal that reports kills while `non_crypto_policy.passes_non_crypto_policy()` returns True (the PR #6 allowlist historically had **0 call sites**) is theatre. The tribunal output must be the *denylist the scanner reads*, not a web page.

Everything below is ordered by leverage.

---

## 2. Bugs and mis-specifications in audit3's own gates (fix first — they're cheap)

### 2.1 G1 (edge direction: one-sided binomial, WR > 50%) is mis-specified
50% is the break-even win rate **only for payoffs with avg-win = avg-loss**. Your own EQUITY class is the counter-example in reverse (WR 59–60%, PF 0.94 — net-negative), and a genuine trend cell (WR 35%, RR 2.5) can never clear G1 regardless of expectancy — which is the only honest definition of edge for trend/premia. **Make the gate: bootstrap net-expectancy CI > 0 (G2) as the primary edge test; demote WR to a descriptor.** Otherwise audit3 structurally cannot ever PROVE a premia strategy, which is the only family with real evidence behind it.

### 2.2 Selection bias on the "CI above zero" segments is unpriced
65 segments screened → 3 with net CI > 0 (`grade A/score≥60 CRYPTO` n=33 net +1.47% CI[+0.48, +2.45]; `elite_grade B CRYPTO` n=72 net +1.41% CI[+0.62, +2.19]; same cohort — the A ⊂ B overlap must be deduped or you double-count the trial). After screening 65 cells, a nominal 95% CI is not 95% — coverage is optimistic. They're correctly labeled WEAK, but the page should print a **selection-adjusted CI** (or Bonferroni-adjusted critical value for the 65-segment screen) so nobody re-commits the INCIDENT #18 error by eye. Also confirm these rows were scored with the **SL-wins-ties intrabar resolver** before nominating them — fixed-TP label artifacts are the house style of this repo's failure mode.

### 2.3 BH applied across one pooled family mixes confirmatory and discovery
45 tested cells, all BH'd together at q ≤ 0.1. That's valid for *ranking* but wrong as the promotion gate: your confirmatory set (the 3–5 pre-registered pods) deserves its own, smaller BH family (or a fixed α), separate from the 40+ discovery cells. **Split the ledger into `confirmatory` and `discovery` namespaces; promotion gates apply only within confirmatory.**

### 2.4 Trial accounting is inconsistent
Summary says 45 tested cells; provenance says 59 DSR-scored; hypothesis registry carries 99 entries with 28 raw status spellings. One canonical N must feed DSR, Bonferroni, and BH everywhere. Wire the same `cumulative_trials` counter into audit3, `money_ready_verdict.py`, and the emitter — three counters that disagree means the correction is fictional.

### 2.5 luxalgo_confluence SHORT fails two different gates — verify the right one
n=476, WR 54.4% (Wilson [49.9, 58.8]), PF 1.56, net +0.67%/trade, **bootstrap net CI [+0.35, +0.96] excludes zero**, split-half stable and *improving* (first +0.34, second +0.99), top symbol 10%, DSR 0.977 ≥ 0.95, binomial p=0.030 — but **q = 0.338 (BH across 45 cells) and top_source_share = 0.977 vs your own 0.9 max_source_share cap**. So it fails multiplicity and the source-concentration cap — not a lack of edge. Two work items:
- **Confirm whether closed rows used SL-wins-ties first-touch.** If not, re-score before nomination (this exact cell shape — high confidence, TP-first labeling — is the INCIDENT #18 artifact).
- **Check it isn't just short beta.** Regress pod PnL on BTC: if corr ≈ −0.8, this is "systematic crypto-short in a drawdown regime", i.e. beta with direction, not luxalgo's edge, and not portable to a high-vol regime. Either way it must be re-expressed as vol-targeted short-exposure sizing, not TP/SL picks. And to ever PROMOTE, it needs a **second, independent source** (or a different venue's fills) — at 97.7% single-source it can never pass your own concentration gate.

### 2.6 Hard-coded slippage constants are optimistic
CRYPTO 0.15% / EQUITY 0.10% / FOREX 0.05% flat constants. Your own Q25 (2× costs) is unenforced here, and small-cap EQUITY slippage is often worse than 0.10% with spread+market impact. **Add a 2×-slippage stress column and a "net CI at 2×" gate; validate constants against `now_history` realized fills vs quote at entry.**

### 2.7 Split-half is a weak stability test
Two windows only. Add rolling 4–8 weekly cohort means (or monthly) with a monotonicity/consistency check, and a turnover-adjusted capacity note per cell.

### 2.8 Provenance leaks a /tmp path
Ledger `source: /tmp/audit3/dashboard_data.json`. Embed **commit SHA + input file SHA-256 + generator version** — you already hash evidence records; the ledger itself should carry the same.

### 2.9 Ledger window is recent-biased
n=3,500 scored rows vs 21,988 policy-clean CRYPTO alone in the full registry. Declare the window explicitly and publish the full-history companion — a tribunal that only sees a recent crypto drawdown can KILL structural longs spuriously (it seems to have: every major crypto LONG symbol — BTC, ETH, SOL, BNB, BCH — is a kill).

### 2.10 Doctrine vs wiring — the most important fix
- Tribunal output must degrade emission privileges: KILL cells → auto-denylist in the scanner; KILL symbols → drop dominance; re-review only on forward evidence, not on backtest re-runs.
- Add an explicit **promotion path**: PROVEN_T2 → small-size production cap (e.g. ≤1% NAV/trade) with mandatory forward-clock review at 30/60/90 days; else the audit machine never graduates anything and the pipeline stays at zero forever.

---

## 3. The actionable short-list — what actually moves toward a winning strategy

### 3.1 The three positive clusters (everything else is noise — starve it)
| Cluster | Evidence (measured today) | Verdict → Action |
|---|---|---|
| **A. Crypto high-ensemble-score LONGs** (`grade A` / `score≥60`, same cohort; and `elite_grade B`) | n=33–72, WR ~65–67%, net +1.4–1.5%/trade, net CI **entirely above 0** in both windows | Pre-register **one** pod: "CRYPTO long when ensemble grade ∈ {A,B} / score ≥ 60, symmetric vol-scaled exit (2×ATR trail or time stop), no fixed TP". Dedup A⊂B. Forward-shadow 90d. **No sizing.** |
| **B. luxalgo_confluence SHORT** (crypto) | n=476, CI>0, stable & improving half, DSR 0.977, p=0.030, single-source 97.7% | Pre-register SHORT-only pod with BTC-regression and funding-rate covariates; require a second source or re-express as vol-targeted short sleeve; kill if forward CI-LB ≤ 0 at day 60. |
| **C. Equity/ETF breakout family** (`donchian-stock-breakout` EQUITY 45, `rs-breakout-scout` EQ 52 + ETF 80, `vol-contraction-scout` EQ 62, `adx-trend-scout` ETF 43) | Pooled ≈ **364 trades, net +0.46%/trade**; individual CIs straddle 0; all four same-direction, same expression | One family-level pre-registered test vs a **random-entry timing null** (you have `daily_prices` 66k rows + `benchmark_closed_ledger.py`). 30-day decision: promote to forward pod or retire the family. |

**Explicitly do nothing** with: all 11 KILL strategies, KILL symbols, copytrader family (n=81, net −1.34%, KILL), every crypto LONG (class-aggregate CRYPTO KILL, n=1851, net −0.51%), COMMODITY class (n=55, WR 14.5%, net −3.17%, KILL), `MEANReversionBB SHORT`, `futures_momentum SHORT` (0% WR), and the `mega_mutation` family (n=19, WR 73.7%, PF 3.65 — register it as a hypothesis if you can reproduce the mutations; INSUFFICIENT_N today means *observe*, not *trade*).

### 3.2 Concentrate emission
Three pods max, all in two classes: CRYPTO SHORT + EQUITY/ETF LONG. Pause emission elsewhere (the tribunal already proves those streams are negative *net of your own slippage constants*). This single move raises your effective breadth per trial by ~50×.

### 3.3 Re-express every pod as premia-style sizing, not TP/SL
Exit on time/vol (e.g., 10–20 day or 2–3 ATR trailing, symmetric), size by inverse realized vol to a fixed portfolio vol target; no fixed take-profit. Your fixed-TP design is the proximate cause of the "WR 59% but PF<1" pathology and INCIDENT #18. This matters more than which cluster wins.

### 3.4 Benchmark legs or it didn't happen
Every pod card: excess vs matched-exposure benchmark (BTC-hold for crypto SHORT, SPY for equity/ETF LONG), IR, down-capture. If pod B's alpha vanishes vs short-BTC, you had beta, not a strategy. Your own BENCHMARK_GATES.md already specifies this — audit3 should inherit those columns.

### 3.5 Copytrader / PM final disposition
Copytrader: net −1.34% on n=81 — this is measured harm; retire the family and stop "reverse-engineering" wallets. PMs: no PREDICTION class exists; rows still tagged CRYPTO (32 rows) and poisoning CRYPTO cells — fix tagging, and only ever run PMs as **maker** at ≥ 85¢ with Brier tracking, or purely as a probability oracle.

---

## 4. `/audit` main page — targeted fixes

1. **Tournament/leaderboard/PF>2 "Renaissance T1" framing** — delete. "T1 (PF>2/WR>55/MDD<10, Renaissance)" invites exactly the overclaiming your incidents document. Replace the tier ladder with a single axis: forward-clock evidence (days, CIs).
2. **Kill-switch summary card** reports WR lift +6.10pp but **PF lift −0.0224** — i.e., removing 42 "losers" didn't improve profit factor. Publish lift on forward PnL only, or drop the lift line; current version lets a reader think the kill switch has a measured win when it doesn't.
3. **crypto_rsi5070_us** says "re-run at n≥150 gate (~2026-06-25)" — stale; it has n=431. Refresh text; state the real bar honestly: CI-LB > 1.15 (unlikely to ever promote — that's the point of the bar).
4. **Money-ready bridge "PF ≥ 1.5" bar** is arbitrary; replace with benchmark-relative gate (excess > 0, IR ≥ 0.5, matched exposure) per your own BENCHMARK_GATES.md §6.
5. **Theory tracker H-020…H-025 all KILL** (incl. H-024 G10 carry at n=950) — note these tested carry as TP/SL picks, i.e. the wrong expression. Don't conclude "G10 carry is dead" from a failed TP/SL harness; if you revisit carry, test it as a vol-targeted long/short basket with trend overlay — a different hypothesis, needing its own pre-registration. Be explicit in the page about *why* they died to avoid throwing away a real premium on a bad test.
6. The page still shows two PF/WR sets per class ("weigh the recent panel") — pick one source of truth per decision: forward clock for promotion, full-history for strategy validation; label them.
7. The **honest kill switch evaluated only 56/181** — raise evaluated coverage > 90% or freeze the un-evaluated cohort out of emission by default.

---

## 5. FINANCE_DB_SCHEMA_SPEC.md — review (branch docs/finance-db-schema)

Ground truth established from the doc + tree: 409 tables in `stocks` (110 empty), ~32.7M `bt_backtest_trades` (+27M duplicate mirror in `stocks`), ~76M `at_local_picks`, `bt_backtest_runs` stale since 2026-03-06, memecoin/sportsbet pipelines dormant since ~May 2026, `portfolio_snapshots` frozen March, `consensus_tracked` frozen April, 414-table backups DB never restore-tested, cross-DB joins impossible (per-DB users), spec currently leaks **host `mysql.50webs.com`, the `ejaguiar1_<db>` naming map, and the credential-resolution path (`tools/db_env.py` + `~/dbpasses.txt`)** — while the note explicitly proposes pasting it into a web AI.

**Verdict: the inventory is genuinely useful; it is not yet safe to share, and it documents what exists, not the contract the pipeline must satisfy.**

Actionable:
1. **Redact before any paste/merge**: strip §1 host+user mapping and §10 credential-path mentions into a private appendix; the public spec carries table semantics only. Also scan & scrub `discord_*` columns in `consensus_tracked` (tokens/webhooks?) and any cookie/session fields.
2. **Declare systems of record**: three overlapping ledgers (`trading_picks`, `at_pick_outcomes`, `at_signal_outcomes`) — designate one canonical (suggest `at_signal_outcomes`, it carries intrabar fields) and define the other two as views/derived; enforce in code, stop filtering for validity ad hoc (`_is_valid_resolved_pick` sprinkled everywhere).
3. **Add a data contract per critical table** (you had `P1_STRUCTURAL/DATA_CONTRACT.md`): bar-close semantics, timezone normalization, resolver version + idempotent re-resolve, dedup_hash enforcement, NOT NULL on `pnl_pct` for resolved rows. The spec should *link* to it and assert it in CI.
4. **Silence the graveyard**: decision-log (owner, date, "why retired") for the 110+20+9 empty tables and the dormant clusters (memecoin, sportsbet, portfolio_snapshots, consensus_tracked, bt_backtest_runs). Empty tables inflate AI-agent search space — the 331k commits partly trace to agents poking at dead surface area.
5. **Kill the duplication**: one canonical `bt_backtest_trades`; drop/mirror-less the stocks copy after a row-count parity check. **Pre-aggregate** to (strategy, symbol, class, month) — the tribunal's evidence re-scoring and the "66,764 trades, only 11 retestable" gap in audit3_evidence are both downstream of this single fix.
6. **CI freshness assertions**: per-table staleness budgets with workflow failure (e.g., `portfolio_snapshots` > 7d → red). Docs decay; assertions don't.
7. **Backups you never restore are not backups**: run and record a quarterly restore test against `ejaguiar1_backups`; add row-count/checksum parity job; document RPO/RTO.
8. **Add the forward-ledger spec** — the missing table that makes "winning" measurable:
   `forward_observations(id, hypothesis_id FK → hypothesis_registry, opened_at, closed_at, symbol, class, side, entry_px, exit_px, qty, fees, funding, slippage_bps, resolver_version, intrabar_first_touch, benchmark_leg_ret, regime_ok, created_at)` with promotion rule "PROVEN_T2 requires n≥100 forward rows with net CI-LB>0 (or IR≥0.5)". Without this, audit3 can never mint a PROVEN verdict from live data — the branch above is the perfect place to add it.
9. **Merge plan**: PR → redact → add §11 "Forward evidence contract" + CI assertions → merge. Keep the doc auto-regenerated monthly (`schema pull + freshness`) with redaction in the generation step, not by hand.
10. Minor: `RECOVERY_PROTOCOL.MD does not exist` (your own known-gap note) — grep for stale references repo-wide; AI agents hallucinate procedures from dead links.

---

## 6. The 90-day sequence this implies

| Week | Action | Gate |
|---|---|---|
| 1 | Fix audit3 gates (G1→G2, split confirmatory/discovery, slippage 2×, provenance SHA); wire tribunal → emitter denylist | KILL strategies cannot emit |
| 1–2 | Redact + extend spec; canonical ledger declaration; pre-aggregate bt_backtest_trades; silence empty tables | spec merges |
| 2 | Pre-register pods A (crypto ensemble-grade LONG with corrected resolver/exits) and B (luxalgo SHORT, covariates) and C (breakout family vs timing null) | signed pre-regs before any new data |
| 3–12 | Forward paper all three; weekly audit3 cards (matched-exposure benchmark, IR, down-capture, net CI at 2× slippage); kill any pod with forward CI-LB ≤ 0 at day 30/60 | promotion only via forward CI>0 |
| 4+ | Capital side: 70–85% low-cost beta core (index ETFs, TFSA/RRSP sheltering) + ≤25% satellites; pods ≤5% sleeve, vol-targeted, −15%/−25% drawdown circuit-breakers | paper sleeve tracked monthly vs benchmarks |

**Realistic prize**: if a pod survives, it's a Sharpe ~0.5–1.0, low-correlation sleeve at small capacity — that, plus beta discipline and cost elimination, is the whole game. Audit3's job is to make sure you never mistake noise for it again, and that when something real arrives, you'll know it.

*Not personalized investment advice.*
