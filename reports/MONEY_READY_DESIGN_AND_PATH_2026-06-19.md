# Money-Ready: Design Map + The Honest Path to Profitable Reliable Picks (2026-06-19)

Synthesis of a 4-agent fleet (webpage+DB design, incidents audit, PR triage, hostile skill critique)
+ a swarm review of the master-loop plan, by claude-opus-4-8 acting as a quant/HF manager. Every
number direct-SQL re-verified; read-only on `ejaguiar1_stocks`.

## 0. The blunt verdict (what an HF manager would tell the LPs)
**There is no net-of-cost directional edge in any asset class today.** After wiring real costs into the
promotion gate (PR #615), the two classes that *looked* over 1.0 on gross collapse:
- FOREX gross PF 1.102 → **net 1.035** (avg 0.031% → 0.011%/trade — a coin-flip after 2bp)
- COMMODITY gross 1.048 → **net 1.005** (avg 0.068% → 0.008% — break-even)
- CRYPTO 0.727 → 0.645 ; EQUITY 0.46 → 0.449
The "bottleneck is plumbing not strategy" thesis is **half true**: the plumbing *was* broken (and is
largely fixed today), but fixing it **confirms** there's no easy directional edge — it doesn't reveal one.
The swarm graded the plan **B / "unlikely to produce profitable picks ASAP"** for exactly this reason.

## 1. The foundation — FIXED today (necessary, not sufficient)
- **The honest measurement layer was silently DEAD for ~6 days** (at_signal_outcomes frozen 06-12→06-19).
  Root cause: `outcome-resolver.yml` crashed every run on a yfinance-only equity fetch, then (once unblocked)
  on an `UnboundLocalError` in the mirror step. **Fixed + verified** (PR #608, #614): the resolver now runs
  green end-to-end and the ledger is accruing again (closed_at 03:06). Incident #140 filed + RESOLVED.
- **NET-OF-COST wired into the promotion gate** (PR #615): the forward lane reported gross PF only; it now
  reports net_pf/net_avg_pnl/net_wr per asset class. Promotion (CI-LB net PF > 1.15) must read net.
- **Hardening shipped**: monkey-test null benchmark (#609), intrabar freshness alarm (#610),
  single-regime-warning verdict field (#611).

## 2. The path to a real winner — STOP chasing directional; harvest a structural premium
Every current sleeve lives or dies on a ~32% directional hit-rate in **one regime** (~170 days crypto /
~87 days equity). The velocity principle (replay-n ≫ live-n) resolves estimator variance, **not regime
variance** — so a "money-ready" claim from replay alone is unsound (walk-forward already reads UNSTABLE).
**The one genuinely-new shot with a net-of-cost case: perp funding-rate carry (delta-neutral).**
- Positive-expectancy *by construction* when 8h funding > borrow cost; PnL is largely **orthogonal** to the
  directional WR that's sinking every sleeve. It's a carry premium, not a prediction.
- NOT on the do-not-relitigate list; blocked only on DATA (no funding table exists; Binance/Bybit funding
  history is a free public API — listed as an unredeemed unlock in plan §6).
- **Action:** pre-register under M-107, ingest ~90d funding for the top ~30 liquid perps, replay the
  funding-extreme carry book net of *actual funding paid* + 16bp execution. First repo candidate that
  doesn't hinge on a 32% directional hit-rate.

## 3. Webpage + DB design map (the surfaces to TRUST a pick when one clears)
Build these so that *when* a candidate clears, it's trustworthy + auditable; and so the honest emptiness is
itself the trustworthy signal today.

| Page | Purpose | Must show | Source | Biggest flaw today |
|---|---|---|---|---|
| **A. "NOW" live picks** (`picks-now.html`) | retail front door | lifecycle badge, forward-status, **net-of-cost** EV, the condition's net-PF + CI-LB, regime/conc warning | `picks_now*.json`, `picks_now_tracker` | leads with an inflated "133/100" composite score; honest forward (−14.4% cum / 31.9% WR / net PF 0.82) is buried; **zero lifecycle vocabulary** |
| **B. Per-class money-ready / lifecycle board** (`template.html`) | the arbiter | net PF + **95% CI-LB**, **n_eff** (not raw n), 5-state lifecycle, IS/OOS + conc, forward-vs-replay decay | `money_ready_verdict.json` (`net_pf`/`status` are **None**), `pf_registry.json` | "probation" is a trust-tier label, not the Addendum-E state; no CI-LB on headline classes; dual-window conflation with no arbiter |
| **C. Single-pick provenance** (NEW) | due-diligence | source/strategy/dedup lineage, honest first-touch resolution, **reachability/expected-move**, cohort context, gate trail | `at_raw_picks` (was_stale/was_banned/dedup_hash) ⋈ `at_signal_outcomes` | **does not exist**; data is there, unsurfaced |
| **D. Model Portfolios / Risk-Managed Books** (`funds.html`) | LP reporting | **TWR**, MWR/XIRR, Brinson attribution, daily P&L reconciliation, calendar-aware Sharpe/MDD | `portfolio_daily_equity` (**EMPTY, n=0**) | uses **additive sum-of-percentages** (the banned bug, line 636); all return figures UNVALIDATED |
| **E. Edge-validation roadmap** (`edge_validation_roadmap.html`) | the gauntlet | live forward-n per candidate vs dated gates, CI-LB ratchet, DSR, stress-matrix pass count | `entry_conditions_forward.json` | **static HTML, no live fetch** — prescriptive, not live |

### DB gaps to power the above (7)
1. **Lifecycle-state table** — `strategy_lifecycle(strategy, asset_class, state ENUM(...), net_pf_ci_lb, n_eff, ...)`; nothing carries the 5-state machine today.
2. **Net-of-cost columns** on `at_signal_outcomes` (`net_pnl_pct`, `cost_bps`) — today gross-only (I wired net into the forward-lane *computation*; persisting it is the next step).
3. **Reachability / expected-move** (`reachable`, `bar_range_pct`, `dist_to_tp_in_sigma`) — kills fixed-TP labeling artifacts at the source; powers Page C.
4. **n_eff / clustering** (`trade_date_cluster`, `cluster_size`) — the promotion bar is n_eff≥80 but nothing stores it.
5. **`portfolio_daily_equity` is EMPTY** — right schema, never written; wire the daily writer for real TWR.
6. **CLV / forward-vs-replay decay** for trading (only sports has CLV today).
7. **`ai_strategy_forward_tests` is a zero stub** — populate or deprecate (avoid a 3rd competing source).

## 4. Incidents (`/audit/incidents.html`)
Page rendering is faithful (badges match DB); the rot is in **lifecycle management**. **Meta-ratchet
BREACHED:** 23 open P0s, **all >7 days old** (max 25d) vs the plan's "zero P0 >7d" success metric. P0 #111
("70-95% TIME_EXPIRED") is provably stale (current mix 0.2% EXPIRED). `incident_id` is non-unique across the
view (id=1 appears 9×); `asset_class` case-mess (STOCKS/EQUITY, ETFS/ETF). Filed #140 for the ledger freeze.

## 5. Recommended next actions (priority order)
1. **Pre-register + run the perp funding-carry experiment** (M-107) — the one structurally-different shot. (data ingest first)
2. **Persist net_pf + lifecycle `status` into `money_ready_verdict.json` + `at_signal_outcomes`** — unblocks Pages A/B/E with no recompute.
3. **Re-skin Page A/B**: lead with net-PF + CI-LB + lifecycle badge; demote the composite "right-now score".
4. **Fix `funds.html`** additive-math bug + wire the empty `portfolio_daily_equity` → real TWR/attribution.
5. **Triage the 23 stale P0s** (close #111 et al.); fix incident_id composite key + asset_class normalization.
6. Continue PR hygiene (merge #585 Bonferroni trimmed, #577 luxalgo kill; close remaining doc dumps).

**Bottom line:** the audit/measurement engine is now honest and alive (today's fixes). It has correctly proven
the *absence* of easy directional edge. The next real move is a structurally different return source (funding
carry), surfaced through a lifecycle/net/CI-LB-first design — not more directional entry-timing replays.
