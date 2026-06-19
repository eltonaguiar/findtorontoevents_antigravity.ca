# Session Summary — Money-Ready Master Loop (2026-06-19)

**Agent:** claude-opus-4-8 (money-ready lead) · **Mode:** quant/HF manager
**Mission (user, verbatim):** *"get us PROFITABLE RELIABLE PICKS, ASAP!"* — review the money-maker-ready
"now" surfaces, map each webpage + the DB, peer-review, hunt flaws/optimizations, look at
`/audit/incidents.html`, run swarm PR-review + actions-audit, deploy subagents.

This file is the work summary; a scheduled **review of all new `.MD` files** follows ~15 min after it lands.

---

## 1. What shipped this session (all VERIFIED on main)

| # | PR | What | Why it matters |
|---|---|---|---|
| Foundation | **#608 + #614** | Un-froze the honest ledger (resolver crashed ~6 days on a yfinance-only equity fetch, then an `UnboundLocalError` in the mirror step) | The measurement layer was **silently dead** — any "winner" shown would have been off a frozen ledger. Verified flowing again (`at_signal_outcomes` accruing). Incident **#140** filed + resolved. |
| **#1 lever** | **#615** | Wired **NET-OF-COST** into the promotion gate (`stamp_entry_conditions.py`) — it was **gross-only** | The fix that **changes verdicts**. FOREX gross 1.102→**net 1.035**; COMMODITY 1.048→**1.005**; CRYPTO 0.727→0.645; EQUITY 0.46→0.449. **No class is net-promotable** (1.15 bar). |
| Hardening | #609 | monkey-test null benchmark (overfit-killer) | gate input |
| Hardening | #610 | intrabar-resolution freshness alarm | catches the next freeze |
| Hardening | #611 | single-regime-warning / day-concentration fields | anti-one-day-artifact |
| Registry | #612 | H-124 + H-125 logged **REFUTED** | negative knowledge banked |
| Docs | #613 | updates/ wave entry (FTP-deployed live) | user-facing |
| **Design map** | **#616** | `reports/MONEY_READY_DESIGN_AND_PATH_2026-06-19.md` | 5 pages + 7 DB gaps + flaws/optimizations + the honest path |

**PR triage (acted, not just reviewed):** merged **#589** (crypto_verified_wf default-OFF + fail-CLOSED — stops
backtest-only sleeves leaking to prod). **Closed with documented evidence:** the refuted FOREX-consensus chain
**#587 / #591 / #592** (the "PF 2.02 winner" is disproven by merged `FOREX_CONSENSUS_HONEST_FIRSTTOUCH_2026-06-13.md`
→ honest first-touch PF 1.02) + superseded P0 batches **#565 / #570**. Backlog 22 → 17.

---

## 2. The honest verdict (as the HF manager)

**There is no net-of-cost directional edge in any asset class today.** The two classes that *looked* >1.0 on
gross (FOREX, COMMODITY) are **net ~1.0** after costs — coin-flips. The "bottleneck is plumbing not strategy"
thesis is **half-true**: the plumbing *was* broken (now largely fixed); fixing it **confirms** there's no easy
directional edge rather than revealing one. A swarm review of the master-loop plan graded it **B / "unlikely to
produce profitable picks ASAP"** for the same reason.

### The one structurally-different shot: perp funding-rate carry (feasibility done this session)
Delta-neutral funding harvest is positive-expectancy *by construction* and **orthogonal** to the ~32% directional
WR sinking every sleeve. Feasibility (Binance `/fapi/v1/fundingRate`, keyless, ~66d, 14 liquid perps):
**realized funding APR is thin — best LINK 4.3%, DOGE 3.6%, NEAR 3.2%; 0/14 clear 5%; some negative (INJ −11%).**
→ A real but **modest market-neutral premium (~2–4% APR)**, not a home-run. For *"reliable"* picks it is the most
**reliable** (positive-by-construction, low-drawdown) option available; for *"big"* it is not the answer.

---

## 3. Webpage + DB design map (peer-reviewed) — full detail in #616

5 surfaces: **A** picks-now (leads with an inflated "133/100" composite; honest forward −14.4% buried; no lifecycle
vocab) · **B** per-class money-ready/lifecycle board (`money_ready_verdict.json` ships `net_pf`/`status` = **None**;
no CI-LB on headline classes) · **C** single-pick provenance (**does not exist** — data is there, unsurfaced) ·
**D** Model Portfolios (`funds.html` uses the **banned additive sum-of-percentages** math; `portfolio_daily_equity`
is **EMPTY** → all fund returns unvalidated) · **E** edge-validation roadmap (static HTML, should be live).

7 DB gaps: lifecycle-state table · net-of-cost columns · reachability/expected-move · n_eff/clustering ·
empty `portfolio_daily_equity` · CLV/decay · zero-stub `ai_strategy_forward_tests`.

---

## 4. Incidents (`/audit/incidents.html`)
Page renders faithfully; the rot is lifecycle management. **Meta-ratchet BREACHED: 23 open P0s, all >7 days old**
(the plan's metric is "zero"); several provably stale (P0 #111 "TIME_EXPIRED" — now 0.2%). Data bugs: `incident_id`
non-unique, `asset_class` case-mess.

---

## 5. Peer corroboration (in flight)
A parallel peer agent independently re-resolved the **picks-now** cohort and found it **NET-LOSING** (realized net PF
**0.82**, WR 29.5%, n=44, no subset clears the bar; over-emission 3.14×) — **corroborating** this session's
"no net-of-cost edge" conclusion. A read-only verification workflow (`verify-peer-picksnow`) is confirming the
peer's numbers + the state of their `picks_now_tracker` UNIQUE-constraint DDL migration (which was truncated
mid-run). Results fold into the 15-min `.MD` review.

---

## 6. Next actions (priority order)
1. **Pre-register + run the perp funding-carry experiment (H-126, M-107)** — the one structurally-different shot; ingest ~90d funding for top ~30 perps, replay net of actual funding + execution + basis.
2. **Persist `net_pf` + lifecycle `status` into `money_ready_verdict.json` + `at_signal_outcomes`** — unblocks design Pages A/B/E with no recompute.
3. **Re-skin picks-now / lifecycle board** to lead with net-PF + CI-LB + lifecycle badge.
4. **Fix `funds.html`** additive-math bug + wire the empty `portfolio_daily_equity` → real TWR.
5. **Triage the 23 stale P0s**; fix `incident_id` composite key + `asset_class` normalization.

**Bottom line:** the audit/measurement engine is now **honest and alive** (today's fixes) and has correctly proven
the *absence* of easy directional edge. The next real move is a **structurally different return source (funding
carry)**, surfaced through a **lifecycle/net/CI-LB-first design** — not more directional entry-timing replays.
