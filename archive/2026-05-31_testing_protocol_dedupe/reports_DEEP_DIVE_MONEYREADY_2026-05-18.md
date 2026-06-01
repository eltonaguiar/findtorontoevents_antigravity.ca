# Money-Ready Deep-Dive — Best & 2nd-Best Asset Class — 2026-05-18

**Method:** fleet of 3 parallel subagents (CRYPTO harness deep-dive, COMMODITY
deep-dive, winner-strategy research) on the canonical deduped ledger
(`audit_dashboard/data/pf_registry.json`), gated by
`tools/edge_stability_harness.py::is_admissible()`.

## Verdict: still 0 admissible. No asset class is money-ready. But the path is now concrete.

CRYPTO is the only class with the sample size to *ever* pass the harness.
COMMODITY's gaudy PF is a leakage mirage. The honest move is to **build one
new causal-hypothesis strategy** (C-2, below), not to keep mining the dead ledger.

---

## Canonical per-class state (policy-clean, net-of-slippage)

| class | n | PF | WR | harness-testable? | verdict |
|-------|---|----|----|----|---------|
| CRYPTO | 1949 | 1.25 | 44.8% | YES (only class with n) | sub-floor, no admissible sub-cohort |
| COMMODITY | 47 | 2.30 | 61.7% | NO (n=47) | **leakage mirage — deprioritize** |
| UNKNOWN | 38 | 1.72 | — | NO | junk bucket |
| EQUITY | 31 | 0.72 | 35.5% | NO | failed |
| FOREX | 288 | 0.18 | 12.8% | NO/failed | failed |
| FUTURES | 12 | 0.96 | — | NO | failed |

## Vetting peer notes (kilo / Hermes / opencode) — REJECTED as evidence

The Hermes "Real-Money Readiness Audit" (kilo forwarded it) queried
`ejaguiar1_stocks.at_raw_picks` — the **raw un-deduped** MySQL table. Its
headline findings are artifacts:

- "CRYPTO 40.3% WR / −12.92% avg PnL" — raw ledger; canonical clean-net is
  44.8% WR / PF 1.25. The raw view inflates trade count with ~4,830 duplicate
  re-emissions.
- **"RR≥1.5 + conf≥0.65 → 48.9% WR profitable filter"** — POISONED. The CRYPTO
  subagent found the `confidence` field is corrupted: **146 CRYPTO rows hold
  values 15–78** (domain is 0–1, percent-as-integer leak). Any confidence-based
  filter manufactures a fake positive. This is the same false-edge class as the
  retracted dashboard "winners".
- "High-conf ≥0.8 cohort +0.5% avg PnL" — same corrupted field; not edge.

**Do not gate production on the Hermes filter.** Its one *correct* finding:
non-crypto forward resolution is broken (FOREX/EQUITY ~0% resolved) — already a
known P0.

## CRYPTO deep-dive (subagent: harness on canonical ledger)

- **No CRYPTO sub-cohort is genuinely admissible.** Three slices superficially
  flag ADMISSIBLE — all three are data-quality artifacts (near-constant
  `forward_wr` field, degenerate eff=+0.00 window, corrupted-confidence garbage
  in the WON bucket).
- `ensemble` cohort (n=410) — large enough for windows, but zero per-window
  separation. Volume without edge.
- **Best lead: `st_fear_greed_contrarian`** (n=91 deduped, PF ~2.8–3.15, WR
  74.7%). NOT a placeholder artifact — avg-win/avg-loss ratio 1.07, sane
  win/loss split. BUT all 91 picks span one 18-day window (2026-04-30→05-18) =
  exactly the one-regime fluke the harness exists to catch. **Cannot be
  backfilled — must accrue ~400 deduped picks over ≥10 weeks of live emission**,
  then re-harness monthly.
- **P0 BUG (harness scope):** `tools/edge_stability_harness.py:35` reads only
  `alpha_engine/data/closed_picks.json` — 1 of the 32 ledger files pf_registry
  ingests. It cannot even *see* the `ensemble` / `st_fear_greed` cohorts. The
  CLOSED path must be widened to the pf_registry source list or every harness
  verdict is on a non-canonical subset.
- **P0 BUG (data):** 146 CRYPTO rows with `confidence` ∈ [15,78]. Clamp/reject
  >1.0 at ingestion and trace the upstream percent-as-integer emitter.

## COMMODITY deep-dive (subagent) — leakage mirage, deprioritize

- All 47 COMMODITY picks are `multi_asset_copytrader`. **38 of 47 are CT=F
  (cotton).** Strip CT=F → 10 picks, 0 wins, PF 0.00.
- `multi_asset_copytrader`'s COMMODITY arm is produced by
  `copy_trader_intel/multi_asset_copytrader_scraper.py::scrape_cot_positioning()`
  — the **exact COT-proxy signal that gate M-095 killed for look-ahead
  leakage**. Dominant reason string: "CFTC COT proxy (API unavailable): Weekly
  RSI extreme". It is the killed `cot_positioning` strategy under a different
  label — a gate-bypass via aliasing.
- CT=F is on probation in `COMMODITY_BLACKLIST`; the rest of the commodity
  universe is blacklisted on its own losing record. **No clean n-expansion
  path exists.** COMMODITY's PF 2.30 should be footnoted as contaminated and
  must not feed asset-class verdicts.

## Winner-strategy research (subagent) — what to actually build

All 9 prior harness kills share one defect: **market-wide daily-bar timing
signals applied to a correlated basket** → beta dominates, eff flips sign
window-to-window. The fix: intraday, per-symbol, **cross-sectional**,
event-anchored signals.

| rank | strategy | exp. PF net | data cost | effort | capacity |
|------|----------|-------------|-----------|--------|----------|
| **1** | **C-2 Exchange net-flow cross-sectional spread** | 1.3–1.6 | ~$30–200/mo CryptoQuant | low (daily bars) | $250k–1M |
| 2 | E-1 PEAD intraday-anchored (EQUITY) | 1.1–1.3 | ~$30/mo Polygon | medium | $1M+ |
| 3 | C-1 Order-book imbalance reversion | 1.3–1.6 | ~$300–500 one-time Tardis | high (tick infra) | $10k–50k |
| 4 | C-3 Funding-settlement liquidation cascade | 1.1–1.3 | free | medium | $50k–150k |

**#1 build: C-2.** Long the 2 majors with largest exchange *outflow*
(accumulation), short the 2 with largest *inflow* (distribution); market-neutral
daily-rebalanced spread. It structurally repairs the beta-domination defect
behind all 9 kills (the spread cancels crypto beta so the harness measures the
signal). Cheapest credible paid feed; daily bars = no tick infra. Not a banned
family (not funding-directional, not COT, not F&G/RSI). If C-2 also kills →
10th kill → honest paper-only declaration per ROADMAP Phase 2 exit gate.

## Money-ready verification bar (per strategy, all must hold)

1. `is_admissible()` = True — eff≥0.30, same sign, ≥3/5 walk-forward windows
   (feed C-2 the *spread* records so beta is removed first).
2. Cost gate — net edge ≥60% of gross after 30bp crypto / 10bp equity round-trip.
3. Capacity-aware — PF restated at $10k/$100k/$1M; declare the size PF<1.3.
4. Pre-registered in `reports/hypothesis_registry.json` before any backtest;
   then ≥30 forward crypto picks / ≥10 forward earnings events, fwd PF≥1.3 net.
5. No single symbol >25% of records (the CT=F kill mode).

## Per-asset-class TODOs

**CRYPTO**
- [ ] P0: clamp/reject `confidence` >1.0 at ingestion; trace percent-as-integer emitter (146 rows).
- [ ] P0: widen `edge_stability_harness.py:35` CLOSED path to pf_registry's 32-file source list.
- [ ] Keep `st_fear_greed_contrarian` emitting; re-harness monthly; target n≈400 over ≥10 weeks.
- [ ] Build C-2 net-flow cross-sectional spread; pre-register hypothesis; backtest on canonical dedup.

**COMMODITY**
- [ ] Add `multi_asset_copytrader` COMMODITY arm (or `scrape_cot_positioning`) to the COT leakage gate so PF 2.30 stops feeding `pf_registry` / `asset_class_health`. (Requires `STRATEGY_INVESTIGATION_BEFORE_KILL.md` — this report is that investigation gate.)
- [ ] Footnote COMMODITY PF 2.30 as contaminated in any verdict surface.
- [ ] Deprioritize behind CRYPTO until a clean point-in-time COT or price-momentum signal exists.

**EQUITY**
- [ ] Pre-register E-1 PEAD intraday-anchored (SUE + first-15-min reversal, 3-day drift).
- [ ] Fix non-crypto forward resolution (UNCLAIMED P0 — the one valid Hermes finding).

**FOREX / FUTURES / BOND**
- [ ] No action — retail-hopeless per swarm consensus; do not spend effort.

## How this advances PnL / PF / Sharpe

No strategy here is yet proven — these are causal hypotheses, the bar ROADMAP §3
set. Realistic per-class odds of clearing the harness: 5–8%. C-2 is the highest
expected-value bet because it fixes the structural defect (beta domination) at
the lowest cost. The honest framing remains: **paper-only until a strategy
clears the harness on canonical data with ≥30 forward picks.**

*Subagent runs: CRYPTO afae64c8, COMMODITY af932dc8, research a25dbe72.
Cross-checks: EDGE_HARVEST / ROADMAP_TO_EDGE / COHORT_HARNESS_VERDICT /
BURIED_WINNER_HUNT (all 2026-05-18).*
