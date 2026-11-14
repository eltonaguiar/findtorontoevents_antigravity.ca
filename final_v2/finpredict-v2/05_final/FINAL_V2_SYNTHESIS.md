# FINAL V2 SYNTHESIS — Profitability Path & Peer Review (2026-11-14)

**Prepared by:** `finpredict-v2`
**Clock:** 2026-11-14T21:30Z
**Scope:** a second, final pass over the live system, our pre-registered research, and all peer
`final_v2/` packages. This is a prioritization and review, not a new profitability claim.

## 1. Verdict

**No asset class has a proved, statistically valid edge.** The live system is not profitable
(0/9 money-ready), 23 pre-registered candidates are NOT_PROVED, and every peer profitability claim
reviewed is falsified, unverified, or a selection effect. What this document adds is a **ranked,
realistic path per asset class** and the measurement fixes that must come first.

## 2. What changed in final_v2 (corrections to our own package)

| # | Correction | Consequence |
|---|---|---|
| C-A | `exit_reason` is populated (SL_HIT 1,468 / TP_HIT 873 / FORCE_CLOSED 615 / TIME_EXIT 517 / UNKNOWN 22 / EXPIRED 5); `resolution_method` was the wrong key | C1 is about **fill fidelity**, not missing exit taxonomy |
| C-B | The 100× PnL-unit bug is **not** in the 3,500-row dashboard ledger (3,500/3,500 within 0.05 pp); it is real in MySQL/sidefiles (17,632 percent vs 6,306 fraction rows) | C0 still applies, scoped to write paths |
| C-C | Crypto stops planned at **1.919%** risk, realized **2.990%**; overshoot **+828.0 pp** = **98.8%** of the −837.8 pp crypto loss; fill-at-stop → PF 0.768 ≈ 1.00 | New **C6 stop-fill fidelity**; breakeven, not profit |
| C-D | 170-ledger benchmark: **4 pass** at 95% vs **8.5 expected** by chance | Independent negative; sharper than "32.9 expected FP at N=658" |
| C-E | FOREX: **49/277** non-spot-FX (44 currency ETFs + 5 EURUSDT); 105 date-only; 44 EST-unparseable; allowlist appears once | FOREX block is unenforced and the population is contaminated |
| C-F | BOND n=35: **34.3% WR** under `status=WON`, **37.1%** under `pnl_pct>0` | Quote both; the class is still insufficient |
| C-G | Mutual-fund prototype exists untracked in the main checkout, nothing on `origin/main` | Production remains **NOT_BUILT / de-advertise** |
| C-H | `final_v2/{finpredict,finpredict-v3,flaxen-hair}` now exist on main | Reviewed in `04_peer_reviews/FP6_final_v2_peers.md` |

Full detail: `01_audit/CORRECTIONS_v2.md`.

## 3. Per-asset-class priority

| Class | Priority | Realistic edge | Best next experiment | Expected net Sharpe |
|---|---|---|---|---|
| **FUTURES** | **HIGH** | TSMOM + carry risk premia (real, modest, crowded) | 12m vol-targeted TSMOM on 16 continuous futures | 0.3–0.7 |
| **CRYPTO** | **HIGH feasibility / LOW return** | Funding/basis carry (real, low-vol, capital-limited) | Cross-venue funding+basis, ROC vs T-bill | 0.2–0.6 (ROC) |
| **BOND** | **HIGH** | UST curve carry + roll-down, DV01-neutral | Mechanical roll-down on ZT/ZF/ZN/ZB | 0.3–0.6 |
| **EQUITY** | **MEDIUM** | PEAD/SUE, value/quality (untested cross-section) | SUE event study, SEC XBRL, beta-neutral | 0.2–0.6 |
| **FOREX** | **MEDIUM** | G10 carry via CIP forwards/currency ETFs | Long high forward discount / short low, futures/ETF | 0.2–0.5 |
| **ETF** | **LOW** | Covered calls / vol-risk premium | SPY buy-write ~2% OTM 30-DTE, beta-matched | 0.0–0.4 |
| **COMMODITY** | **LOW** | Roll-yield/curve carry | 20 real curves after purging crypto proxies | 0.0–0.4 |
| **MUTUAL FUNDS** | **LOW / NOT_BUILT** | Fee arithmetic + allocation (beta) | Expense-ratio selection + low-cost sleeve; de-advertise | n/a |

Full detail: `05_final/PER_CLASS_PRIORITY_MATRIX.md` and `02_per_asset_class_profitability/*.md`.

### The five experiments worth running

1. **Crypto funding/basis carry (capital-adjusted, cross-venue).** Measure return on capital at
   1.2×/1.5×/2.0×; pass only if ROC > T-bill after fees. Current: 3.7–4.8% at 1.5× vs 4.5% cash.
2. **Futures TSMOM + carry.** 12-month trend, vol-targeted, 16 continuous contracts, benchmark-
   relative; true DSR/PBO/SPA; no ETF proxies.
3. **Bond curve carry/roll-down.** Mechanical, DV01-neutral, ZT/ZF/ZN/ZB; clean accrual is pure
   upside from n=1.
4. **Equity PEAD/SUE.** Event study from SEC XBRL filed dates (no analyst consensus), t+2, costs.
5. **ETF covered-call/VRP.** SPY buy-write, monthly, beta-matched benchmark; crash-convex, so gate
   on drawdown and tail, not just Sharpe.

## 4. Peer `final_v2` review (FP6)

**Coverage PASS / reproducibility FAIL.** All 25 files in `final_v2/{finpredict,finpredict-v3,
flaxen-hair}` were read; `quant-audit`'s self-contained package is the fourth reference.

| Peer | Position | Verdict |
|---|---|---|
| `finpredict` | audit + quick wins + master plan | PARTIAL — useful fixes, but cites our older package; no run artifacts |
| `finpredict-v3` | calls trend/carry/mean-reversion "real profitable" | **OVERSTATED** — its own folder refutes VWAP; no proof |
| `flaxen-hair` | re-asserts mega_mutation `production_enable=true` | **REJECT / DANGEROUS** — FP1 falsified; 170-ledger m006 PF 0.767; 4 passes vs 8.5 expected |
| `quant-audit` | stop-fill, 170-ledger, per-class R-multiple | **STRONGEST NEGATIVE** — adopt the diagnostics; no edge |

FP6 classification: **7 ADOPT, 12 MERGE, 11 REJECT, 4 ALREADY_COVERED.** Key adopts: stop-fill
replay, 170-ledger benchmark, 3× cost gate, `universal_price_enricher`, CRYPTO POSITION/SWING split.
Key rejects: short-term reversal, MUTUAL_FUND build, decimal-ratio PnL, TradingView winner windows,
"all other classes negative" (false on `recent_closed`: EQUITY 1.154, ETF 1.036).

Full detail: `04_peer_reviews/FP6_final_v2_peers.md` and `04_peer_reviews/FP5_ERRATUM.md`.

## 5. Measurement fixes before any new strategy (C0–C6)

1. **C0 — canonical PnL unit** at every write path; reject mixed units; migrate with an audit log.
2. **C1 — terminal exits + fill fidelity**; `exit_reason` exists; verify the fill price.
3. **C2 — admit-by-default-false gate**: independent n≥100, DSR≥0.95, PBO≤0.10, BH-FDR q<0.05,
   net PF≥1.25 at class costs; delete the FDR off-switch; add the **3× cost gate**.
4. **C3 — dedup/pseudo-replication**: canonical economic key; quarantine, never delete.
5. **C4 — quote surface**: `quote_at`, `quote_source`, `quote_status`, null PnL when unquoted.
6. **C5 — regime/strategy review only after C0–C4.**
7. **C6 — stop-fill fidelity**: replay exits against intrabar OHLCV, fill at stop, gap at close;
   gate median realized loss within 5% of planned. Current crypto overshoot is 98.8% of the loss.

## 6. What would count as proof

- Clean forward or unseen OOS; no post-hoc regime filters; no symbol cherry-picking.
- Correct annualization from bar frequency; intrabar stops; concurrent capital; ROC.
- True DSR at all trials, CSCV PBO, stationary-bootstrap Reality Check/SPA.
- n≥30 (preferably ≥100 independent events), 2× cost, one-period execution lag.
- Independent replication + adversarial review before "PROVED".

## 7. Honest conclusion

There is no proven profitable approach in this repo today. The live numbers are dominated by
measurement defects (stop fills, PnL units, zombies, multiple testing), not by a hidden signal.
The best realistic paths are **carry/trend/event-driven** sleeves with modest, capacity-limited
Sharpe — not another price-only parameter sweep. TradingView contests select winners from thousands
of entrants; that is survivorship, not a repeatable method. A contest-style edge would require
intraday L2/order-flow, options surfaces, or private data, plus the C0–C6 fixes above.

**Do not size real money on any class until C0–C6 are green and one pre-registered experiment
survives a clean forward OOS.**

## 8. Coverage

- Local and remote peer work: `final_2026_11_14/*` (6 packages) and `final_v2/*`
  (`finpredict`, `finpredict-v3`, `flaxen-hair`, plus `quant-audit`'s self-contained package).
- No peer `final_v2/finpredict-v2` alternative exists; this is our final_v2.
- Numbers trace to the audit, the pre-registered runs, or a named peer artifact.
- `UNVERIFIED` items are marked in the per-class files and reviews.
