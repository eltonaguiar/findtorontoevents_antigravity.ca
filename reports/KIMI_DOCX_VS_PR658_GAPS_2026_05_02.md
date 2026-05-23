# Kimi Agent Swarm DOCX vs PR #658 Master MD — Gap Analysis

**Date:** 2026-05-02
**Author:** Claude Opus 4.7 (gap-analysis subagent)
**Scope:** Compare `e:/findtorontoevents_antigravity.ca/.tmp_research/kimi_docx_extracted.txt` (492 paragraphs / 521 lines) + `kimi_docx_tables.txt` (44 tables, lines 0–504) against `kimi_pr658_master.md` (1,573 lines) on PR #658 / branch `origin/hedge-fund-enhancement-2026-05-02`.

---

## TL;DR

The PR #658 master MD is a **substantively faithful, near-line-for-line reproduction** of the DOCX gold standard. All 10 chapter sections, all 44 tables, every quantitative claim I sampled (PF/WR/Sharpe/dollar-cost figures), the regression identifiers (-0.17 elite_score correlation, 0.5785 ml_score AUC, 9.1 × 10⁻³⁷ binomial p-value, +969.50% killed alpha, etc.), the 9-fix forex remediation list, the 37-issue QA matrix, the Mermaid pipeline diagram, the math (Wilson CIs, Kelly fractions, break-even WR), the academic reference catalog (20 entries), and the master 35-recommendation evidence summary are all preserved.

There is **one material defect** in the PR: the footnote *definitions* were re-numbered down to [^1^]–[^11^] (only the academic citations were kept), but **inline citation markers [^12^] through [^54^] were left in the body text without corresponding definitions** — they are orphan references. The same orphan pattern is present in the DOCX extract (the .docx footnote pane was not captured by the extractor), so this is at worst a parity issue rather than a regression introduced by the author.

**Verdict: MERGE (with one cosmetic follow-up to clean up orphan footnote markers).** No load-bearing data, recommendation, table, or risk warning was dropped or weakened. There is nothing in the DOCX that a human reader would derive a different hedge-fund decision from.

---

## Gap Inventory Table

| Section | What's in DOCX | Status in PR #658 | Severity | Evidence snippet |
|---|---|---|---|---|
| Executive Summary | Sharpe 5.395, S-Tier 85.7% WR / PF 30.17, weighted PF 3.99 / Sharpe 2.83, 77.79% PnL drag, +173% annual alpha bleed, -0.17 elite_score correlation | **Present, verbatim** | LOW | PR L11–13 mirrors DOCX L11 |
| Table 1 — Portfolio Current State | 10 asset class rows incl. WR/PF/Sharpe/n/Status/Triage | **Present, verbatim (10 rows)** | LOW | PR L25–36 = DOCX Table 0 |
| Table 2 — Top 10 Priority Actions | 10 ranked actions with effort + dollar lift | **Present, verbatim** | LOW | PR L48–59 = DOCX Table 1 |
| Table 3 — Conservative vs Optimistic Impact | 8 rows incl. Sharpe 2.83→4.20, MDD ~25→~12 | **Present, verbatim** | LOW | PR L77–86 = DOCX Table 2 |
| Capital Commitment Framework | 4 phases ($0 → $1M → $5M → $25M+) with entry gates and halt triggers | **Present in two locations (Exec Summary + §8.4) verbatim** | LOW | PR L92–97 + L1253–58 = DOCX Tables 3 & 37 |
| §1.1 S-Tier scaling pathways | 4 numbered pathways (lower conf to 0.80, crypto recalibration, regime gating, on-chain metrics) | **Present, verbatim** | LOW | PR L115 = DOCX L39 |
| §1.5 Banned Symbol Review | 6-row conditional unban table (DOGE/OP/LINK/LTC/ADA/TON) with per-strategy PF | **Present, verbatim** | LOW | PR L168–175 = DOCX Table 5 |
| §1.6 Crypto Gate Optimization | 5-row table incl. confidence dead-band keep-blocking + Forward WR floor 55%→60% | **Present, verbatim** | LOW | PR L191–197 = DOCX Table 6 |
| §2.1 Equity factor Sharpe history | SGH 2024 + Jegadeesh-Titman 1993 + Carhart 1997 + Fama-French 2015 + Blitz–van Vliet 2007 citations | **Present, verbatim** | LOW | PR §2.1 narrative parallels DOCX L92–93 |
| §2.3 AAPL Decision Matrix (Table 9 in DOCX) | 4-row strategy filter table (markov_zone_transition score 55, regular_divergence score 65, Classic Mom score 999) | **Present, verbatim** | LOW | DOCX Table 9 reproduced in PR §2.3 |
| §3.1.1 Bug Cascade Timeline | 6-stage timeline Apr 28 → May 3 with picks-blocked column | **Present, verbatim** | LOW | PR L402–409 = DOCX Table 11 |
| §3.1.2 Statistical proof, p = 9.1 × 10⁻³⁷ | Binomial CDF formula + per-window probability table | **Present, verbatim, inc. LaTeX math** | LOW | PR L417, L421–426 |
| §3.3.1 G10 Carry Spread Matrix | 6-pair table USDCHF / AUDCHF / NOKCHF / USDJPY / GBPCHF / AUDJPY with break-even 21.1% | **Present, verbatim** | LOW | PR L494–501 = DOCX Table 15 |
| §3.3.3 Forex Transaction Cost Model | 3-row spread/slippage/grade table (G10 Majors / Minors / Cross Pairs) | **Present, verbatim** | LOW | PR L519–523 = DOCX Table 16 |
| §3.4 Post-Fix Filter Configuration | 6-row pre-fix vs post-fix parameter table with rationale | **Present, verbatim** | LOW | PR L539–546 = DOCX Table 17 |
| §4.2 Bond Blocked Picks + Yield Curve | 5-row table incl. TLT/IEF/LQD ml_scores + post-fix projection + steepener strategy | **Present, verbatim** | LOW | PR L574–580 = DOCX Table 18 |
| §4.3 Futures Accumulation Plan | 6-row parameter relaxation table (forwardWRMinPctFutures 50→40, scoreFloor 35→25, etc.) | **Present, verbatim** | LOW | PR L604–611 = DOCX Table 19 |
| §5.1 Killed Alpha — Per-Gate breakdown | 5-row table incl. FOREX_GATE row + dollar net column | **Present, verbatim** | LOW | PR L645–651 = DOCX Table 20 |
| §5.2 Per-Gate F1 / Precision / Recall | 4-row (QUALITY / RR / WINNER / Overall) verdict table | **Present, verbatim** | LOW | PR L665–670 = DOCX Table 21 |
| §5.3 Top 10 KILLED_ALPHA picks | 10-row table led by RNDR-USD +337.72% | **Present, verbatim** | LOW | PR L688–699 = DOCX Table 22 |
| §5.4 Near-Miss Pattern Detection | 6-row table incl. Early-UTC-hour degradation row | **Present, verbatim** | LOW | PR L719–726 = DOCX Table 23 |
| §5.5 ROC-AUC Predictor Comparison | 8-row predictor ranking ml_score 0.5785 → elite_score 0.5458 | **Present, verbatim** | LOW | PR L740–749 = DOCX Table 24 |
| §5.5 Threshold Sweep Table | 5-threshold table (0.50 / 0.70 / 0.82 / 0.90 / 0.94) | **Present, verbatim** | LOW | PR L757–763 = DOCX Table 25 |
| §6.1 37-Issue Severity Matrix | All 37 numbered issues with severity / root cause / fix location | **Present, verbatim, all 36 rows in markdown table** (note DOCX table line ID#37 missing in both — likely an extraction quirk; both list 36 rows) | LOW | PR L790–827 = DOCX Table 26 |
| §6.2 Pipeline Mermaid Diagram | Full Mermaid `flowchart TD` block with 11 nodes + style directives | **Present, verbatim** | LOW | PR L847–866 = DOCX L278–295 |
| §6.3 TRK% vs FWD WR% Comparison | 7-row dimension comparison incl. 26pp LONG vs BUY direction-asymmetry row | **Present, verbatim** | LOW | PR L885–893 = DOCX Table 27 |
| §6.4 Schema Enforcement (12 fields) | Required-field validation table | **Present, verbatim** | LOW | PR L943–956 = DOCX Table 28 |
| §6.4 Field-name normalization aliases | 6-row alias table (take_profit/stop_loss/direction/asset_class/track_wr/track_trades) | **Present, verbatim** | LOW | PR L969–976 = DOCX Table 29 |
| §6.4 Track-record schema | 7-field track_calculator schema | **Present, verbatim incl. JSON example** | LOW | PR L920–933 + L988-onward = DOCX Table 30 |
| §7.1–7.6 Strategy expansion | 6 strategy proposals + Crypto Perp / CEF / Forex Carry / Meme / Penny / Commodity Triple-Screen | **All 6 sections present with academic citations** (He & Manela 2024, Burnside 2011, CUNY 2021, Da et al 2014, Fuertes et al 2015, etc.) | LOW | PR §7 = DOCX §7 |
| §7 Strategy Expected Performance Matrix | 7-row strategy table with academic anchors | **Present, verbatim** | LOW | DOCX Table 31 reproduced in PR §7.1 region |
| §7 Decision Framework | 8-row accept/reject matrix incl. Mutual Funds REJECT row | **Present, verbatim** | LOW | DOCX Table 32 reproduced |
| §7 Implementation Timeline | 8-week deliverable table | **Present, verbatim** | LOW | PR L1138–48 = DOCX Table 33 |
| §8.1 Correlation matrix viable assets | Intra-crypto 0.70–0.80, equity-ETF 0.85, bond -0.30 narrative | **Present, verbatim** | LOW | PR L1178 = DOCX L407 |
| §8.2 Golden Portfolio Allocation | 7-row CIO blend table ($10M reference, Sharpe 4.195 weighted) | **Present, verbatim** | LOW | PR L1188–96 = DOCX Table 34 |
| §8.2 Institutional Benchmarks Table | 5-row Renaissance / Two Sigma / Citadel / AQR / Golden comparison | **Present, verbatim** | LOW | PR L1202–08 = DOCX Table 35 |
| §8.3 Asset Class Triage | 12-row ELIMINATE/SCALE/MONITOR/DEVELOP matrix | **Present, verbatim** | LOW | PR L1224–37 = DOCX Table 36 |
| §8.4 Quarter-Kelly + correlation matrix | 6×6 cross-asset correlation matrix + Kelly discussion (44.9% / 61.5% / 85.2% full → 25% quarter caps) | **Present, verbatim** | LOW | PR L1270–77 = DOCX Table 38 |
| §8.4 Stress test (2008 crisis 55% MDD, COVID 31% MDD) | Quantified stress scenarios | **Present, verbatim** | LOW | PR L1216 = DOCX L417 |
| §9.1–9.4 Implementation Roadmap | 12-week phase plan with explicit Done criteria for each Day-N block | **Present, verbatim** | LOW | PR §9 = DOCX §9 |
| §9.5 Risk Mgmt 12-Week Roadmap (Table 9.1) | 17-row owner-assigned deliverables table | **Present, verbatim** | LOW | PR L1405–23 = DOCX Table 39 |
| §9.5 Risk Mgmt Checkpoint Matrix (Table 9.2) | 12-row kill-switch / drawdown / rebalance / schema / PSR checkpoint table | **Present, verbatim** | LOW | PR L1429–42 = DOCX Table 40 |
| §10.1 Master Evidence Summary | All 35 numbered recommendations with Cons/Opt lift, risk, grade, hours | **Present, verbatim incl. 258-hour total** | LOW | PR L1468–1505 = DOCX Table 41 |
| §10.2 Academic Reference Catalog | 20-entry table 1993–2025 incl. He & Manela / Burnside / Da et al / Fuertes et al / SGH 2024 / Jegadeesh-Titman / Carhart / Fama-French / Blitz-van Vliet / Moskowitz-Grinblatt / MDPI 2026 / CUNY 2021 / Ghoddusi / Gorton-Hayashi-Rouwenhorst / Liu et al / IJRASET / CoinGecko | **Present, verbatim, all 20 rows** | LOW | PR L1523–44 = DOCX Table 42 |
| §10.3 Code Changes Summary | 9-row file modification plan (4 modified, 5 added; ~1,163 lines total) | **Present, verbatim** | LOW | PR L1556–67 = DOCX Table 43 |
| **Footnote *definitions*** | DOCX extract has zero `[^N^]:` definition lines (the .docx footnote pane was not pulled by the extractor) | PR has **11 numbered defs covering academic citations only** (lines 1154–1164). Inline citations [^12^]–[^54^] used in body text **have no corresponding definition** in PR | **HIGH** (cosmetic but visible to reviewers) | `grep -c '^\[\^[0-9]*\^*\]:' kimi_pr658_master.md` → 11; inline refs go to [^54^] |
| Mathematical typesetting | DOCX extract dropped LaTeX (e.g., the binomial CDF formula, Kelly variables, $z_{\alpha/2}$) | PR retained full LaTeX + Mermaid + markdown tables — **richer than the extracted DOCX text** | LOW (PR is *better*) | PR L417, L448, L482 carry math the extracted .txt could not represent |

---

## Strongest 3 "Omissions" — full context

### 1. Orphan footnote markers [^12^]–[^54^] in PR body without definitions  *(HIGH severity, cosmetic)*

- **What is in the source:** The DOCX clearly intends inline footnote markers `[^12^]` through `[^54^]` to be live references. (The Word footnote pane was not captured in the extracted .txt I have, but the inline markers themselves were extracted.) The DOCX contains 43 distinct numbered inline references.
- **What the PR did:** The PR retained every single inline marker exactly as in the DOCX (verified by grep — both files share the same set of `[^12^]`–`[^54^]` markers), but the PR's bibliography section at lines 1154–1164 only re-defined eleven footnotes ([^1^]–[^11^]), all of them academic citations. Markers 12–54 therefore render as broken links / dangling references in the rendered MD on GitHub.
- **Why it matters for hedge-fund quality decisions:** It does not affect the *content* — every numerical claim those footnotes anchor is also stated inline in the prose. But for a reviewer who clicks a footnote to verify the source ("where does the +173% annual alpha bleed claim come from?" → `[^12^]`) the link is dead. This will erode reviewer trust on a PR whose entire pitch is "evidence-graded recommendations." A trivial post-merge cleanup (either re-number markers or add stub definitions) would resolve it.
- **Note:** Whether this is a *regression* introduced by the PR or an artifact of the original Word footnote pane being stripped during conversion is unclear. Either way, the PR currently presents broken footnote links.

### 2. Loss of original Word/DOCX figures rendered as PNG references  *(LOW–MED severity, structurally faithful)*

- **What is in the source:** The DOCX has 9 inline figures ("Figure 1: Crypto Tier Performance Degradation", "Figure 5.1", "Figure 5.2", "Figure 6.1", "Figure 6.2", "Figure 8.1", "Figure 9.1", "Figure 10.1", "Figure 10.2", plus chart-attached panels in chapters 2/3/4).
- **What the PR did:** The PR replaces every figure with markdown image references (e.g., `![Executive Summary Dashboard](executive_summary_dashboard.png)`). The image files themselves should live alongside the markdown in `audit-enhancement/research/` (per the user's brief these are 18 charts on the branch). Verifying their presence is outside the scope of this gap analysis but would be a cheap follow-up.
- **Why it matters:** If any of the 18 PNGs is missing on the branch, those `![...](xxx.png)` references render broken on GitHub. This is a delivery-channel concern, not a content gap.

### 3. No structural omissions to flag  *(NULL — this is the headline)*

- I sampled every chapter (1.1 → 10.3), every table (Tables 0 → 43 in the DOCX tables file → mapped to PR §§1–10), every regression statistic the DOCX cites (the −0.17 elite_score / +0.0006 t-test / 0.5785 AUC / 9.1 × 10⁻³⁷ binomial / +969.50% killed alpha / 27.6 percentage-point break-even cushion / 4.55%–4.75% USDCHF carry / 5-tier kill-switch ladder / quarter-Kelly 25%/40%/10%), every dollar figure ($1,901/mo verified subset → $3,800–$7,600 annualized), every academic citation, every code-file impact estimate (1,010 added + 153 modified ≈ 1,163 lines across 9 files), every risk warning (look-ahead bias on ml_score >= 0.82 threshold, 25% probability of ml_score degradation, 50% probability of futures non-existent edge, 40% pump-and-dump rate in meme coins, 6-month minimum C-Tier suspension burden of proof, etc.). All present. **Nothing of decision-grade substance was dropped.**

---

## Footnote Audit

- **DOCX inline footnote markers:** 43 distinct markers `[^12^]` through `[^54^]` (11 numbers absent because the original DOCX footnote chain started at 12 — likely because [^1^]–[^11^] were Word-managed footnote IDs that the .txt extractor failed to capture).
- **PR inline footnote markers:** 54 distinct markers `[^1^]` through `[^54^]`.
- **PR footnote *definitions*:** 11, lines 1154–1164. All 11 are academic citations (He & Manela / Li et al / Burnside et al / CUNY / CoinGecko / IJRASET / Da Liu Schaumburg / Liu Zhang Zhao / Fuertes et al / Ghoddusi+Gorton+Szymanowska / "Author calculation").
- **Orphan ratio:** 43 / 54 markers (≈ 80%) point to undefined footnotes.
- **Net assessment:** The PR did *not* drop any source attribution from prose — sources are typically named inline (e.g., "He & Manela (2024), forthcoming in the *Journal of Finance*…", "MDPI (2026) overnight/daytime ETF study…", "SGH (2024) analysis of Fama-French data from July 1963 through April 2024…"). The Academic References table at §10.2 lists all 20 papers with their venue and the claim they support. The orphan footnote markers are a presentation-layer defect, not a citation-loss event.

---

## Conclusion

**Recommendation: MERGE.** PR #658 is a faithful mirror of the DOCX. There is no decision-grade substantive content (claim, table row, recommendation, risk caveat, sample-size limitation, methodology reference, regression coefficient, dollar figure, or academic citation) that exists in the DOCX but was dropped or weakened in the PR.

The single defect worth a follow-up commit (not a blocker) is the **broken footnote-definition chain** — the PR retains inline markers `[^12^]`–`[^54^]` from the DOCX but only defines `[^1^]`–`[^11^]`. This is cosmetic on render and contributes zero loss to the analytical content (every claim is also stated inline in prose), but should be cleaned up because the PR's whole rhetorical posture is "evidence-graded with explicit citations." Two acceptable paths:

1. Re-number all inline markers to match the 11 actual definitions (preserves academic anchors only, drops the appearance of internal cross-refs).
2. Add stub footnote definitions for `[^12^]`–`[^54^]` pointing to the relevant chapter/table (e.g., `[^12^]: Chapter 8 CIO review, weighted portfolio metrics.`).

Option 2 is more transparent and reviewer-friendly; ~30 minutes of work.

The PR is *not* a watered-down subset and is *not* a different document. It is genuinely the same audit, faithfully transcribed into markdown with LaTeX math, Mermaid diagrams, and markdown tables — actually a *richer* presentation than what the DOCX extractor was able to dump to .txt.
