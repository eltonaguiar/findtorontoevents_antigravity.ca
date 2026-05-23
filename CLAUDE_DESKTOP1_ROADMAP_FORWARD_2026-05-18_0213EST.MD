# How /audit Becomes World-Class — Honest Timeline & Accelerants

`claude-opus-4-7-desktop` — 2026-05-18 02:13 EST. Companion to
`reports/ROADMAP_TO_EDGE_2026-05-18.md` (swarm-reviewed: Grok + DeepSeek).

## The honest answer up front

**"World-class prediction system across ALL asset classes" is not a realistic
target on the current infrastructure.** Two independent AI reviewers put the
probability of hedge-fund-grade edge per asset class on shared hosting + free
APIs at **5–8%**. Renaissance-tier (PF>2, WR>55, all classes) requires
proprietary data feeds, co-located execution, and a full-time research desk —
structural advantages retail cannot buy.

What IS realistic, and worth pursuing: **a trustworthy, defensible edge in ONE
asset class** (probably CRYPTO), surfaced honestly on `/audit`, with real
capital gated behind it. That is the goal to aim at. "All asset classes,
world-class" is marketing language — drop it.

## Timeline

| horizon | what is achievable |
|---------|--------------------|
| **Weeks (3–6)** | Infra + honesty: dashboard tells the truth (canonical `pf_registry`, harness-verdict badges), regime field backfilled, regime-conditional harness shipped. NO edge yet — the machinery to *fairly find* one. |
| **Months (4–9)** | IF the 5–8% bet pays: one causal-hypothesis signal (CRYPTO on-chain net-flow) clears the regime-conditional harness + forward-test. First *defensible* "Money Ready" pick in one class. |
| **Years / never** | All six asset classes at world-class. Not happening on this infra. Honest. |

If the first causal-hypothesis test becomes the **9th kill**, the honest call
is **declare paper-only** — a research sandbox, no real capital. That is a
legitimate, non-failure outcome.

## Current state (canonical, not dashboard tiles)

8 straight walk-forward harness kills. `pf_registry.json` policy-clean:
EQUITY PF 0.60 · COMMODITY 1.11 · CRYPTO 0.88 · FOREX outlier-fake ·
FUTURES 0.11. **No class clears a PF 1.5 / WR 50% bar.** Every prior "best
candidate" label was an inflated un-deduped-ledger artifact.

## What speeds it up — and what does NOT

The operator asked: more symbols? more strategies? more research? more bug
fixes? more DB analysis? Ranked by real ROI:

### HIGH leverage — do these

1. **Bug fixes / data integrity (cheapest real lever).** The canonical ledger
   loses **83%** of rows (14,705 → 2,445) — 4,830 duplicate re-emissions +
   4,763 policy-excluded. Fix the duplicate-re-emission bug at the writer. A
   clean ledger is the prerequisite for *any* trustworthy stat. This is plain
   engineering, no luck required.
2. **DB-slice analysis (the magic-filter hunt).** Mine
   `pf_registry.json::by_asset_class_strategy_symbol` / `_date` for any slice
   with PF≥1.5, n≥30 — a regime/symbol/time-of-day filter that is *consistently*
   profitable, or conversely a corrupt-data cohort whose removal flips a class
   positive. Cheap, canonical, could surface a real conditional edge. (Logged
   in `DAILY_IDEAS.MD` for a `/money-maker-readyv2` run.)
3. **Regime-conditional harness.** The current harness only tests sign-stability
   and **structurally rejects regime-dependent edges** — most real edge.
   Without this fix every new signal is auto-killed regardless of merit.
4. **Targeted research — causal hypotheses, not signal mining.** Write the
   economic mechanism first, test only it. One good hypothesis per class beats
   100 mined signals.

### LOW or NEGATIVE leverage — do NOT

5. **More strategies — NEGATIVE.** 114 strategies already exist. More = more
   overfitting, more multiple-testing burden. The problem is too many
   single-signal hunts, not too few.
6. **More symbols — marginal/negative.** Adds noise and survivorship bias,
   inflates the multiple-testing correction. Coverage is not the bottleneck.
7. **More generated picks — negative.** 6,253 unresolved crypto picks already
   pollute the ledger.

### The one external accelerant worth money

The single thing retail structurally lacks is **proprietary / orthogonal
data**. A paid data feed (real options flow, an on-chain node, institutional
positioning) is worth more than months of free-API mining. If the operator
will spend anywhere, spend there — not on more compute for the same overfit.

## Future steps

### This session's remaining (owned by this agent)
- Regime-conditional harness — roadmap Phase 1. Dependency: backfill `regime`
  onto `closed_picks.json` (only ~3/6,000 rows have it) via the
  `regime_terminal` HMM. Then `evaluate_by_regime()` in
  `edge_stability_harness.py`.

### Next session
1. Run the logged `/money-maker-readyv2` deep audit — magic-filter hunt +
   missed-gainers gap + per-class coin-flip diagnosis.
2. issue #1221 — flip `/audit` tiles to canonical `pf_registry.json` (codebuff).
3. issue #1233 — FTP-TLS security P0.
4. Fix the duplicate-re-emission writer bug (83% data loss).

### Peers
- on-chain crypto research → STRAND B (sole owner per
  `OWNERSHIP_DECISION_2026-05-18.md`).

## Bottom line

We are **weeks** from an honest dashboard and a fair harness; **4–9 months**
from a *defensible* edge in one class IF the 5–8% bet pays; and we will likely
**never** be "world-class across all asset classes" on this infrastructure —
and saying so plainly is the most valuable output of this session. Speed comes
from fixing data integrity and buying real data, not from generating more.
