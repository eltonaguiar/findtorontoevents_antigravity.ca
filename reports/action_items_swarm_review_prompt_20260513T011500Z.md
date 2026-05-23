# Swarm review — 5 action items implementation + testing plan

Repo: `findtorontoevents.ca/audit` trading dashboard. 4 asset classes active
in production scope, 2 thin/stressed.

Each action item below has live data context + design intent + open
implementation question. For EACH item, return:

1. `verdict`: SHIP | DEFER | SCOPE_CHANGE
2. `implementation_plan`: 3-5 bullets of concrete steps; cite file paths
3. `testing_plan`: 2-3 bullets of unit + functional + regression tests
4. `risk`: LOW | MED | HIGH + one-line reason
5. `dependencies`: explicit blockers if any

---

## NS-A — Manually dispatch ab_analysis.yml to unlock multi_asset_cot DB verdict

**Context:** `tools/verify_system_pf.py` shipped (`96f72d2ec47`); wired into
`ab_analysis.yml`. Awaits next daily cron (05:30 UTC) OR manual trigger.

**Live data:** `multi_asset_cot` reports PF=21.33 / WR=88.2% / n=144 in
`dashboard_data.json`. 75.6% of COMMODITY class PnL flows through CT=F
(the symbol multi_asset_cot trades). If PF=21.33 is real, this single
strategy IS the entire COMMODITY edge.

**Open Q:** dispatch via `gh workflow run` (user-action) — should the
inspect-output step be automated next run, OR is the manual gate
intentional?

---

## NS-B — Procure GLASSNODE_API_KEY + CFTC_API_KEY secrets

**Context:** FRED_API_KEY set; both other keys missing. Glassnode
needed for Edge #11 (funding-skew/taker-imbalance, Sharpe>1.5 documented).
CFTC needed for Edge #1 (multi_asset_cot uses COT data) and Edge #9
(Hyperliquid HLP carry replication).

**Open Q:** which CFTC source — official socrata feed (free, slow) vs
quandl/nasdaq (paid, fast)? Glassnode tier — basic ($30/mo) vs
professional ($800/mo) for derivatives endpoints?

---

## NS-C — BTC seasonal-by-UTC-hour filter (free statistical edge)

**Context:** memory `project_clean_data_symbol_wr` proves 22 UTC = 61.2%
WR on n>1000 CRYPTO picks. 08-09 UTC = death zone (sub-30% WR).
Implementation: 1-line filter on every CRYPTO strategy's emission.

```python
hour = pick.created_at.hour
if pick.asset_class == "CRYPTO" and hour in (8, 9):
    return SKIP
```

Estimated impact: +14pp class-level WR. From 46.5% to ~60% on CRYPTO
sleeve which currently has n=7935.

**Open Q:** apply at intake (smart_picks_engine) or at execution
(passes_active_gate)? Both have precedent. Memory
`feedback_gate_at_execution_not_generation` warns intake-only
filters get bypassed by some exec paths.

---

## NS-D — PEAD on EQUITY top-100 cohort

**Context:** EQUITY is the only confirmed Tier-2 class (PF 1.55 / WR
53.2% / n=447). Post-Earnings Announcement Drift is the lowest-hanging
academic edge — long-documented, transaction-cost-survivable, public
data implementable.

DE Shaw R3 in supreme plan: "PEAD edge is real, not yet shipped."

Constraint: HFT-crowded since ~2022; per-name short-window edge has
decayed. Multi-day window (2-5 days post-earnings) still has alpha.

**Open Q:** earnings calendar source — IEX Cloud / Polygon.io / SEC
EDGAR scrape? Universe — S&P 500 only or Russell 2000 included?
Sizing — equal-weight long-only or long-top-decile / short-bottom-decile?

---

## NS-E — FOREX hard-disable until carry-factor (Edge #14) ships

**Context:** FOREX PF 0.29 / -1026% cumulative PnL / n=1355. Already-set
`FOREX_MIN_SCORE=70` raised admission gate. But emissions still happen.

Memory `[Mutate Before Kill]`: cannot kill silently; must run mutation
protocol first. The supreme plan + AQR R3 prescribe carry-factor
rehab (Edge #14: long high-yielder / short low-yielder G10 rebalanced
monthly, 30yr Sharpe 0.7-0.9 documented).

**Open Q:** disable via env flag `FOREX_HARD_DISABLE=1` OR via
`BLOCKED_ASSET_STRATEGY_PAIRS` blanket add for every FOREX strategy?
The first is cleaner; the second is verifiable via existing
quarantine_manifest infrastructure.

---

## Constraints applying to ALL 5 items

- `CLAUDE.md`: edit `audit_dashboard/template.html`, NOT `index.html` (auto-generated)
- `CLAUDE.md`: Wire-Up Rule — new modules need a production caller OR opt-in label
- `feedback_gate_at_execution_not_generation` — gates must fire at exec, not just intake
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md` + `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` — mandatory before any new BLOCKED_ASSET_STRATEGY_PAIRS add
- Real-money sizing requires 10-step López de Prado AFML readiness gate clear

## Output format

Return a structured JSON-like response per item:

```
## NS-A
verdict: ...
implementation_plan:
  - step 1 (file path)
  - step 2
  - step 3
testing_plan:
  - test 1
  - test 2
risk: ... (one-line reason)
dependencies: ...
```

Keep total response under 1200 words. Cite NS-id when cross-referencing.
