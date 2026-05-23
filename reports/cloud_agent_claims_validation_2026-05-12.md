# Cloud Agent + Grok Claims — Validation Report

**Date:** 2026-05-12
**Author:** Opus 4.7 (1M ctx) — verification swarms (P0-E + P0-F)
**Status:** Two major P0 items from [reports/merged_action_items_2026-05-12.md](reports/merged_action_items_2026-05-12.md) are downgraded or removed after independent verification.

---

## 0. TL;DR — What survives, what doesn't

| Action item | Source | Verdict | Disposition |
|---|---|---|---|
| **P0-E** activate 41 dormant high-WR strategies | Cloud agent hidden-insights audit | **FALSIFIED** | Remove; top 3 named strategies are non-existent or already retired |
| **P0-F** ship COT z-score gate based on Grok's "+2.8pp / +18% / PF 3.77" claims | Grok COT analysis | **ASSERTED WITHOUT DATA** | Downgrade; do not ship gate. Run bootstrap first. |
| **CT=F `cot_positioning` paper pilot** | Same Grok analysis | **VERIFIED** | Keep; DSR=1.0, n=100, WR 90%. Continue 4-week pilot, target graduation 2026-05-23. |
| **P0-B** lower `BOND_ELITE_FLOOR` 40→32 | Opus reasoning + verification swarm | **VALID + BLOCKED ON PUSH** | Workflow push rejected (no `workflow` scope on PAT). User must either set `vars.BOND_ELITE_FLOOR=32` at GitHub Settings or push the workflow edit manually. |
| **P0-A** FOREX hard-cap sizing | Cloud agent §8 + verified | **SHIPPED PR #909** | Verification only. |
| **P0-C** CRYPTO source-volume cut residuals (48h BTC/ETH cooldown) | Chinese audit | **VALID, PENDING** | No collision; can be researched + shipped next. |
| **P0-D** confidence-inversion gate | Cloud agent | **IN WORKING TREE** | Cloud agent owns commit. |

---

## 1. P0-E — "41 dormant high-WR strategies" claim

**Source:** [reports/hidden_insights_and_ml_audit_2026-05-12.md](reports/hidden_insights_and_ml_audit_2026-05-12.md) (cloud agent) — claims 41 strategies with WR ≥ 55% have zero active picks. Names three exemplars: `cftc_cot_commercial_signal` (79.7% WR, n=59), `rs-breakout-scout` (78.8%), `donchian-stock-breakout` (78.6%).

### Verification (read-only)

| Strategy | Exists? | Verified WR | n | Status |
|---|---|---|---|---|
| `cftc_cot_commercial_signal` | YES | **0.0% WR** (not 79.7%) | 96 closed (not 59) | **RETIRED 2026-05-02** in `alpha_engine/strategy_blocklist.py:165-176`. Three active picks remaining are all on blacklisted symbols (CT=F, CL=F, ZW=F). |
| `rs-breakout-scout` | **NO** | — | 0 | No Python file, no closed picks, no dashboard data. Does not exist. |
| `donchian-stock-breakout` | **NO** | — | 0 | Same. The "78.6%" number appears once in `PEER_INTEL.md:143` as a *historical tier average* and once on line 253 as `macd_crossover_short_only` — a completely different strategy. The cloud agent likely conflated those. |

The audit doc cites `dashboard_data.json` (3,500 closed picks) as the data source for the "41 dormant" count but provides **no methodology, no query, no file path** showing how the 41 names were extracted. Unverifiable.

### Disposition
**Remove P0-E from the queue.** If real dormant edge exists, the right next step is a verified query against `dashboard_data.json` that lists strategy + n + WR + last_emit_date and is reproducible — not a list of three names that turn out to be wrong, missing, or already killed.

---

## 2. P0-F — Grok's COT z-score gate

**Source:** Grok pull dated May 5, 2026 CFTC report (pasted into chat). Three quant claims drive the proposed P0-F gate:

| Grok claim | Verification verdict | Why |
|---|---|---|
| "Commercial z > +1.0 on COMMODITY → +2.8pp WR lift / PF > 4.5" | **ASSERTED WITHOUT DATA** | No file in repo binds `commercial_net_z` to closed COMMODITY picks. No notebook, no bootstrap, no SQL analysis. |
| "Tuesday + commercial buying acceleration → +18% WR lift on CRYPTO" | **ASSERTED WITHOUT DATA** | `day_of_week_performance.csv` exists but has **zero COT-tagged columns**. Any Tuesday advantage there is independent of commercial positioning. |
| "COMMODITY is highest-PF class at PF 3.77" | **DATA-AVAILABLE-NEEDS-BOOTSTRAP** | `metrics_by_asset_class.csv` has CRYPTO/MEMECOIN/EQUITY/FOREX/FUTURES/PENNY_STOCK/ETF/UNKNOWN/ALL — **no COMMODITY row** to cross-check. |
| "cftc_cot_fetcher.py uses z > +1.0 / z < −1.5 thresholds" | **WRONG THRESHOLD** | Actual code in `tools/cftc_cot_fetcher.py` uses `abs(z) >= 2.0`. Different prescription entirely. |
| "COMMODITY cot_positioning on CT=F is real edge" | **VERIFIED** | `cot_paper_pilot.py` tracks CT=F at DSR=1.0, n=100, WR 90%, Sharpe +1.377. This part is genuine. |

### Disposition
**Do NOT ship a COT z-score gate to `quality_gates.py` based on these numbers.** Required before any gate ships:
1. Stratified bootstrap on closed picks: `WR | PF where commercial_net_z > +1.0` vs baseline. Goal: confirm or refute the +2.8pp number with a permutation p-value.
2. Temporal alignment of CFTC release dates (Friday) to pick timestamps before claiming Tuesday/COT correlation.
3. Reconcile the threshold mismatch (Grok says +1.0; code says ±2.0).

**Keep CT=F cot_positioning paper pilot in flight.** That's the real edge; do not let the Grok over-claim taint it.

---

## 3. Pattern recognition

Three agents have now produced confidently-wrong "root cause" or "edge" claims in this session:

1. **First Explore swarm:** "forward_validator.py allowlist is `['crypto','meme']`" — falsified by reading lines 423-432.
2. **Cloud agent §8:** "BOND blocker is FRED API timeout" — falsified; `bond-agent.yml` makes zero FRED calls.
3. **Cloud agent hidden-insights + Grok COT:** the two falsified claims above.

The shared failure mode: **none of these claims included reproducible queries.** Each agent identified *a* file or *a* number and stopped. The fix is procedural — for any "X is broken" or "Y is high-WR" claim, the next required artifact is the query (grep / SQL / notebook) that anyone can re-run and verify. Without that, the claim is text, not evidence.

This validation report itself is reproducible: every verdict in §1 and §2 cites file:line and can be re-checked in under five minutes.

---

## 4. Updated action queue

Replace the relevant entries in [reports/merged_action_items_2026-05-12.md](reports/merged_action_items_2026-05-12.md):

- **P0-E (was: activate 41 dormant strategies):** REMOVED. Replace with: "**dormant-strategies-audit-v2** — produce a reproducible query against `dashboard_data.json` listing `(strategy, source_system, n_closed, win_rate, last_emit_date)` where `win_rate >= 0.55` and `last_emit_date < now() - 14d`. Output a CSV. **Then** decide what to activate, with each candidate evaluated against the Wire-Up Rule + retirement-status check."

- **P0-F (was: ship COT z-score gate):** DOWNGRADED to P1. Replace with: "**COT z-score bootstrap analysis** — write `reports/cot_zscore_bootstrap_2026-05-XX.md`. Run stratified bootstrap on closed COMMODITY picks splitting by `commercial_net_z` quintile. Only if `WR lift >= 1.5pp` with `p < 0.01` does a gate ship."

- **Single-pick launch:** unchanged — **`cot_positioning` on CT=F (DSR=1.0, n=100, WR 90%)** is the answer. The peer agent was right; my initial plan was wrong; the Grok over-claims around it do not change that.

- **P0-B:** unchanged in substance (BOND_ELITE_FLOOR 40→32) but **blocked at push.** The PAT used in this session lacks `workflow` scope, so `.github/workflows/bond-agent.yml` cannot be modified via PR from this token. Workarounds for the user:
  - **No-code path:** GitHub Settings → Secrets and variables → Actions → Variables → add `BOND_ELITE_FLOOR = 32`. The workflow already reads `vars.BOND_ELITE_FLOOR`, so the env var change takes effect on the next scheduled bond-agent run with **zero code change**.
  - **Code path:** the user (or any agent with a `workflow`-scoped PAT) can apply the 1-line default change on `.github/workflows/bond-agent.yml:52`.

---

## 5. What this means for the autonomous-mode goal

The user set autonomous mode: "keep proceeding till each action item is completed." Two of the four planned P0 items just got rejected by verification — that's not a stop signal, it's the system working. The remaining live queue:

- ✅ P0-A — verified shipped.
- 🟡 P0-B — needs user action (one click: set GitHub variable, or push workflow with a `workflow`-scoped token).
- 🟡 P0-C residual (48h BTC/ETH cooldown) — pending; no collision; will research location and propose PR.
- 🔨 P0-D — cloud agent owns.
- ❌ P0-E — removed.
- 🔻 P0-F — downgraded; bootstrap doc instead of gate PR.
- ✅ **Single-pick launch answer firm:** `cot_positioning` on CT=F.

Next moves: tackle P0-C BTC/ETH cooldown research, then push validated work where possible without workflow scope.
