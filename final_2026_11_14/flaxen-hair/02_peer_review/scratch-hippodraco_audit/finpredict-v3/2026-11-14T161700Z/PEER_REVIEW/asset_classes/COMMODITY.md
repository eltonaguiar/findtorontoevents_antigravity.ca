# PEER REVIEW — COMMODITY

**Reviewer:** finpredict-v3 peer-review subagent, 2026-11-14T16:17Z

## 1. Peer docs read
- v4 `noncrypto_deep_dive.md` §5 COMMODITY (4 picks, all ancient; DSR falsified).
- v4 `dashboard_data_report.md` §2.1/2.2/2.4 §5 (COMMODITY WATCH; policy-clean n=14; 0 top-25).
- v4 `market_crossref_report.md` Commodities (NG=F/CL=F MISPRICED_ENTRY).
- v1 `2026-11-14-prediction-system-audit.md` §2 (27 OPEN, 18 frozen).
- v2 `E_statistical.md` §5 (n=14, z=-2.67).
- Mine `2026-11-14-prediction-data-hygiene.md` (zombie rows).

## 2. Peer verdict per class
- v4 (noncrypto): **"COMMODITY Verdict: DEAD"** — only **4 active picks**, all **156–157 days old** (ZM=F, ZS=F x2, LE=F; June 10–11 2026); no new emission since June; avg +3.57% skewed by two ZS winners; intrabar **n=229, WR 40.2%, PF 1.026 FAIL**; `cta_golden_cross_200` n=24 (WR 83.3%, PF 10.87) is a single small strategy. **CT=F DSR=1.0 claim falsified 2026-05-13** (6.33x over-emission artifact).
- v4 (dashboard): **WATCH** (money-ready PF 1.03, WR 40.17, MDD 19.8%, but expectancy negative, DSR=0, policy frozen); policy-clean net **n=14, PF 0.172**; 0 top-25 picks.
- v1: 27 OPEN, 18 (67%) frozen; newest signal 1.5h but raw feed has zombie EXPIRED rows.
- v2: **n=14, WR 14.29%, PF 0.1718, z=-2.67, p=0.0075** — just misses Bonferroni (α=0.0056); PF<1.
- v4 crossref: NG=F/CL=F flagged MISPRICED_ENTRY and resolved same-day; live prices now show both would have been **profitable (+19.6% / +10.0%)** → flag likely a false positive.

## 3. Peer-proposed quick wins (with source)
1. Close/ignore the 4 zombie June picks (ZM/ZS/LE); they are not live positions (v4 noncrypto rec #5).
2. If re-emission desired, start from scratch — do not inherit the dead cohort (v4 noncrypto rec #5).
3. Investigate MISPRICED_ENTRY false-positive flag (NG=F/CL=F) before trusting entry-quality gates (v4 crossref).
4. Keep policy frozen (WATCH, no sizing) until a real closed sample exists (v4 dashboard; v2).
5. Purge EXPIRED zombie rows inflating the raw active count (v1; mine).

## 4. Disagreements / contradictions
- **Status label**: v4 deep-dive calls it DEAD; v4 money-ready gate labels it WATCH (PF 1.03 but DSR=0, expectancy negative). Both agree: no money-ready, no recent emission.
- **Policy-clean vs intrabar**: v2 policy-clean **n=14, PF 0.17** (bad) vs v4 intrabar **n=229, PF 1.026** (near break-even). Different populations, same conclusion (no edge).
- **golden_cross_200 PF 10.87** is a single n=24 strategy — not a class edge.

## 5. Gaps
- ML-audit has **no commodity `proposed_fixes/` folder** — NOT FOUND; no ML fix proposal for commodity.
- No recent closed sample (last closes old); no re-emission plan from any peer beyond v4's "start from scratch".
- No live price refresh for the 4 zombies; no forward ledger.

## 6. Recommended best-of (master plan)
Treat COMMODITY as **deprecated/dead**: close the 4 zombie picks, keep the class policy-frozen, do not size. Any re-emission must start from a fresh scanner run with a forward ledger n>=100. Log the MISPRICED_ENTRY false positive as a known entry-gate over-trigger.
