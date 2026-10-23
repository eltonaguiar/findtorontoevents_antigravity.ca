# OPENCODE — BEAM · Asset-Class Scorecard Page (2026-10-22)

## What this covers
A public-facing audit page that distills the institutional/asset-class findings into
something a non-DB user can cross-check, per the operator request: *"see each asset and
their performance over time, to easily cross-check it without going deep into the database,
then see whatever methods you used to 'prove' it's beyond a coin-flip, in beginner terms with
an ELI5 tooltip/expandable."* The page was later enhanced (2026-10-22) to be much more
beginner-friendly: a defined call scale, per-pick "why" (technical + fundamental), a
per-method who-pass/fail + ELI5 expandable, and a per-class decision/meta-research map.

## What was added / changed

### New page (original build)
- `audit_dashboard/opencode_beam.html` — standalone, self-contained (inline CSS, no deps).
  - **Bottom line strip:** 0/9 asset classes money-ready · watch=[COMMODITY] · 0 PROVEN · 4 weak candidates.
  - **Asset-class scorecard** (hard-only n, WR, PF, verdict, status, honest note) for
    CRYPTO / EQUITY / FOREX / COMMODITY / ETF / BOND / FUTURES / MEMECOIN.
  - **Strongest validated edge:** tactical asset-class rotation family (TAA) — SPY-vs-rotation/v2-blend/PAA1/VAA table, plus mutual-fund ranker T1/T2 tiers.
  - **Rejected claims table** (mega_mutation, high_trust relabel, HG=F overlap, BOND replay artifact, EURGBP copy-trader).
  - Data provenance + NFA footer.

### Enhancement pass (call scale, "why", ELI5 who-pass/fail, decision map)
All added inside the same `opencode_beam.html` file:
- **Defined call scale table** (REJECTED / WATCH / CANDIDATE / PROVEN) — each pill with a
  plain-English definition and a "Can you trade it?" column. CANDIDATE is explicitly defined:
  *passed several not-luck backtest checks but no forward cohort yet; promotion bar = n≥100 hard
  outcomes, ≥30 distinct entry days, ≥90 days, PF≥1.5 net of 2× costs*. PROVEN = also survived
  the forward cohort + statistical matrix; explicitly "no asset class is here today".
- **Per-candidate deep-dive cards** (6 cards): each shows Direction pill (LONG/SHORT), Certainty
  pill, Call pill, a meta grid (n/PF/CI-LB/ex-top3/entry), a **"Why — technical"** box and a
  **"Why — fundamental"** box, plus gate PASS/FAIL/PENDING lines. Covers CRYPTO SHORT RSI30-50,
  high_trust_momentum, luxalgo_confluence SHORT, regime_accumulation, stocks_rsi2_pullback,
  MRBB+200d ETF rotation.
- **Proof-method grid** — 12 cards, each with: the bar (`statline`), a **"Who passes"** box
  (`whopass`, with green pass / yellow tbd / red fail spans per candidate), and an **ELI5
  `<details>`** expandable explaining the technique, why we bother, and the pass bar.
- **Decision-map table** — per class: Overall call · Direction · Certainty · Next action
  (research) · **"The ONE meta-question to ask"**. This answers the pick-vs-fine-tune-vs-
  meta-research question directly (NFA).
- **Recommended engineering priority callout** — 1) paper-track RSI30-50 SHORT + TAA rotation,
  2) meta-research the EQUITY/FOREX data layer, 3) fine-tune the momentum regime gate,
  4) re-run the full proof matrix before upgrading past CANDIDATE.
- **Predicted-price honesty note** — pipeline emits probabilistic directional edges, not fixed
  price forecasts, so targets/stops are expressed as direction + strategy rule logic rather than a
  made-up number.

### Wiring (unchanged from original build)
- `audit_dashboard/index.html`:
  - New **OPENCODE — BEAM** card added to the **Links (tab-links)** grid (line ~2810).
  - New prominent bottom banner link just before `</body>` (line ~19004) → `/audit/opencode_beam.html`.
- `tools/deploy_audit_files.py` — added UPLOADS entry (`opencode_beam.html` → `/findtorontoevents.ca/audit/opencode_beam.html`, tag `healthchecks`), right after `benchmark_proof.html`.
- `.github/workflows/audit-dashboard.yml` — added `"opencode_beam.html"` to all **three** per-site deploy page lists (findtorontoevents.ca, tdotevent.ca, torontoevent.net), next to `opencode_paper_trading.html`.

## Verification (fresh, post-enhancement)
- `python3` regex balance pass on the rewritten 509-line page: all key tag nets 0
  (div 238/238, span 114/114, table 6/6, tr/td, tbody/thead, details/summary 12/12).
- Feature markers confirmed present: `CANDIDATE`×15, `PROVEN`×8, `WATCH`×8, `REJECTED`×15,
  `whopass`×13, `ELI5`×13, `pill`×66, `meta-question` in the decision-map header.
- `search_files` confirms: call-scale glossary table, candidate cards with Direction + Certainty
  pills, 12 proof-method cards each with `whopass` + `.eli5` `<details>`, and the decision-map
  table with the "The ONE meta-question" column.
- File closes cleanly through `</html>` (line 508); `</body>`/`</html>` present.

## Note
- The page bakes current data inline (like `benchmark_proof.html`). It is a static snapshot as
  of 2026-10-22; data refreshes require editing the inline numbers (or future refactor to
  `fetch('/audit/data/…')`).
- Deployment to the live site happens via the next `audit-dashboard.yml` run (hourly cron) or a
  manual `python tools/deploy_audit_files.py --only healthchecks`.

*Not financial advice. Research/educational only. Past performance does not guarantee future results.*
