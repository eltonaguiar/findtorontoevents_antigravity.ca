# inspect-wt (deepAI) — Final Deliverable (2026-11-14)

**Worktree:** `.inspect-wt` · **Branch:** `audit/live-audit-2026-11-14`
**Agent:** deepAI quantitative audit (Windows host) · **Date:** 2026-11-14
**Repo:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/

Consolidated archive of the full session: live-system audit → proposed fixes → profitability
research (V0–V6) → final-stage peer review of all 6 peer `final_2026_11_14/` packages.

## Folder map

```
final_2026_11_14/inspect-wt/
├── README.md                     ← this file (executive summary + cross-peer verdict)
├── AUDIT_FINAL.md                ← umbrella audit report (all 5 sections)
├── 01_actions_health/            ← GitHub Actions health: 365 workflows, 1,200 runs scanned
├── 02_active_picks/              ← live repricing of 703 open picks vs Binance/Yahoo/FX truth
├── 03_frozen_data/               ← staleness/zombie detection (hyro 157h, 404s, 78.6% EXPIRED)
├── 04_closed_picks/              ← closed-ledger recomputation (PF 0.80, Σ−424pp over 30d)
├── 05_verdict/                   ← FAIL verdict + multiple-testing analysis (646-strategy universe)
├── 06_profitable_approach/       ← V0→V6 research: walk-forward variant C + reproducible script
├── 07_proposed_fixes/            ← 8 fixspecs, 1 patch, 4 per-asset-class quick-win docs,
│                                   cross-peer merge analysis, Playwright live JS report
├── 08_peer_review/               ← review of all 6 peer packages + responses to their critiques
└── 09_evidence/                  ← JSON evidence (repricing, cells, surface truth) + session-1
                                    per-asset-class summaries
```

## 1. Audit verdict — FAIL (corroborated by all 6 peers)
Fleet PF 0.26–0.80, WR ~41–42%, **0/9 money-ready surfaces**; 4,164 active picks of which
**3,272 (78.6%) are EXPIRED zombies with pnl=0**; 81% of open picks show fake 0% P/L; real
mean open P/L **−1.80%** (claimed Σ−106pp vs repriced Σ−1,116pp ≈ **10× understated**);
hyro_pick_performance frozen 157h while its workflow "succeeds"; EURGBP=X entry 688.17 vs
market 0.835 (garbage ingest). Root cause: data integrity + multiple testing (646-strategy
universe, only 4 cells n≥100, **zero** pass n≥100+PF>1.3+z>1.96; 69/80 live anti-overfit
flags OVERFIT_LIKELY).

## 2. Profitability research (V0→V6) — the honest result
- **V1** cell search (8 source / 12 source×class / 26 strategy): none pass uncorrected z>1.96.
- **V2** split-sample: single-split p=0.006–0.038; alive-filter refinement FAILED (PF 0.80).
- **V3** cost: breakeven extra round-trip margins 0.23–3.31%/trade (healthy vs ~0.1–0.2%).
- **V4/V6 walk-forward (authoritative):** variant C = monthly reselect top-6 strategies by
  trailing PF (n≥20, PF>1.3), trade next month. **n=237 · WR 47.3% · PF 1.26 · +98.7pp ·
  maxDD −64pp · randomization 0/800 → p<0.0013** — improving 4 straight months
  (Jul 0.50 → Aug 1.74 → Sep 1.28 → Oct 1.49 → Nov 1.72); ETF+equity only, crypto naturally
  excluded. **Reproduced exactly by quant-audit (independent) and by finpredict-v2.**
- **NOT proved:** sub-T2 (PF 1.26<1.5, WR<50%), selection-based null, slippage UNVERIFIED on
  closed rows, payload-vintage sensitivity (v2 reports Oct-23 vintage PF 0.906 — unrepeatable),
  vwap-reversion-scout n=15 ≈47% of P/L. Pre-registered **forward pilot** (weekly scheduler
  task `5992b142`, next run 2026-11-21) is the arbitration: T2 gates n≥100/PF≥1.5/WR≥50%
  with kill criteria.

## 3. Cross-peer verdict (my review, details in 08)
All 6 packages agree on FAIL. No peer has proven a raw-alpha edge. Positive artifacts reduce to
three: **variant C** (reproduced twice, selection-based, sub-T2), **mega_mutation** (flaxen-hair
— but single-source `at_pick_outcomes`, PF 49–53 cells flagged `is_single_source_artifact=True`,
0 rows on `recent_closed`, strict n=16 → **pilot only, not "proven"**), and finpredict's *external*
TSMOM risk premium (Sharpe 2.13 ≈ its own B&H benchmark — risk premium, not system alpha).
Kilo's VWAP claim falsified twice independently. **`resolution_method=None` on all 3,500 closed
rows (quant-audit, confirmed by me) is the single blocker to certifying any PF.**

## 4. What I could not verify
- Linux host **192.168.2.52** peer work — SSH password required (key auth denied).
- 180/365 workflows' last-run status (GitHub API budget) and workflow logs (403 admin-only).
- Oct-23 payload vintage (artifact no longer served) — open issue (c) in 08 §3.

## Reproduce
```bash
python final_2026_11_14/inspect-wt/06_profitable_approach/walkforward_v6.py <dashboard_payload.json>
# → VARIANT C walk-forward: n=237 WR=47.3% PF=1.26 sum=+98.7pp ; randomization 0/800
```
