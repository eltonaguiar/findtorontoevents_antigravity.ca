## 4. UI/UX Audit: Finding the Best Picks

The audit dashboard presents fourteen navigation tabs, eight filter buttons, nine dropdown selectors, and overlapping quality labels — all competing to answer one question: which picks are worth trading? This chapter tests every filter combination, documents a naming collision that violates UX heuristics, cross-checks the ?Guide against live data, assesses supplementary tabs, and fixes a production HTML bug.

### 4.1 Filter Combination Testing

The filter bar offers seven binary toggles (including "🧠 SMART PICKS," "Verified Alpha," and "🔥 HIGH CONVICTION ⭐") plus five preset categories. Testing logical pairings and triplets against the live database produces a clear hierarchy. The single-filter baseline shows "Verified Alpha" and "🔥 HIGH CONVICTION ⭐" each isolating picks with projected WR of approximately 62–64%, a 14–19 percentage-point lift over the unfiltered feed [^33^].

**Table 1: Filter Combination Matrix — Projected WR and Pick Count**

| Filter Set | Projected WR | Pick Count | PF (est.) | Usability |
|:---|:---:|:---:|:---:|:---|
| All picks (baseline) | 45–50% | ~210 | 1.0 | Reference only |
| High-grade only | 52–55% | ~45 | 1.1 | Low lift, vague criteria |
| Trusted only | 55–58% | ~18 | 1.3 | Source-based, not quality-based |
| R:R 1.5+ only | 50–52% | ~67 | 1.4 | Underperforms baseline on non-crypto |
| 🧠 SMART PICKS (filter) | 58–60% | ~12 | 1.6 | Per-asset gates, composable |
| 🔥 HIGH CONVICTION ⭐ | 60–64% | ~8 | 1.8 | Best single quality gate |
| Verified Alpha only | 62–64% | ~13 | 1.9 | Best single trust gate |
| Verified Alpha + High Conviction | **65–68%** | **3–8** | **2.1** | **Best daily driver** [^33^] |
| Verified Alpha + R:R 1.5+ | 63–65% | 2–5 | 1.9 | Loses forward validation |
| High Conviction + Trusted | 60–63% | 3–6 | 1.8 | Redundant overlap |
| SMART PICKS + R:R 1.5+ | 58–60% | 1–3 | 1.7 | Too restrictive |
| **VA + HC + R:R 1.5+** | **66–70%** | **0–2** | **2.3** | **Best WR; often empty** [^33^] |
| High-grade + Trusted + R:R 1.5+ + Recent | 55–58% | 5–10 | 1.5 | Volume-quality tradeoff |

The triple-filter combination gates out 192 of 210 picks (91%), leaving an empty table on most sessions [^33^]. The UI treats this as a failure state rather than a protective one. For practical use, "Verified Alpha + High Conviction" is the optimal daily driver — 3–8 picks with projected WR above 65%. The triple-filter variant suits high-conviction sizing decisions where capital preservation outweighs frequency.

### 4.2 The "Smart Picks" Naming Crisis

The UI contains **three distinct elements** carrying the label "Smart Picks," each with a different behavioral contract. This violates Nielsen's heuristic #2 (system-real-world match) and heuristic #4 (consistency) [^159^].

**Table 2: Three UI Elements Named "Smart Picks" — Behavioral Divergence**

| Element | Visual Location | Behavioral Contract | Interaction Model |
|:---|:---|:---|:---|
| "🧠 SMART PICKS" button | Filter bar | Composable toggle; applies per-asset gates (min score, R:R ≥1.5, forward WR ≥50%, regime alignment) | Toggle on/off; stacks with other filters |
| "🧠 Smart Picks" tab | Top navigation (4th tab) | Standalone page showing pre-filtered results | Switches page context; may alter columns |
| "Smart Picks" reference | ?Guide modal, feed descriptions | Non-interactive conceptual tier label | Defines scoring methodology only |

The collision creates concrete errors. A trader clicking the filter button expects the same outcome as clicking the tab, yet the former is composable within the current view while the latter is a dedicated page that may reset filter context [^159^]. The fix: rename the tab to "Smart Picks Feed," rename the filter button to "Apply Smart Gates," and reserve "Smart Picks" for documentation only.

### 4.3 Guide Page Accuracy

The ?Guide modal presents authoritative documentation, but cross-referencing against the closed-pick database ($n = 4{,}618$) reveals misalignment on R:R recommendations and combo reproducibility.

**Table 3: ?Guide Claim vs. Actual Data — Discrepancy Audit**

| Guide Claim | Stated Metrics | Actual / Cross-Check | Severity |
|:---|:---|:---|:---:|
| Crypto Confidence 0.85–0.90 | 82% WR, PF 11.8 | Confirmed; overfit cliff (>0.90 → 47% WR) not explained | Low |
| R:R ≥2.0 band | 58.0% WR, PF 3.06 | Triple-verified; prior tooltip (29.5% WR) empirically wrong | Low |
| **R:R ≥1.5 filter (current)** | Recommended | **Underperforms baseline on every asset class** (crypto −0.4pp, equity −1.0pp, forex −9.2pp, commodity −32.3pp) [^33^] | **High** |
| **Maximum Conviction Combo** | 71.3% WR, PF 13.21, n=94 | **Not reproducible on current window (n=0); "insufficient sample"** [^33^] | **High** |
| **Stocks Trusted + score ≥50** | 69.2% WR, +25.8pp lift | **PF 0.77 on n=13 — fails PF > 1.5 edge threshold** | **Medium** |
| High-grade A/B | NOT an edge | 49.3% WR, PF 0.66, −0.08% avg (n=483) | None (honest) |

The Maximum Conviction Combo — "PROVEN strategy + confidence 0.8–0.9: 71.3% WR, PF 13.21" — produces zero matching picks on the current data window. The guide buries this in a footnote reading "insufficient sample," but a user scanning headline claims would conclude it is validated and actionable [^33^]. The R:R ≥1.5 filter is the second high-severity issue: live data shows it underperforming baseline across every asset class, a case of conditional statistics (R:R ≥2.0 among *closed picks*) diverging from prospective filter performance. Verdict: the Guide presents two non-reproducible or contradictory recommendations alongside accurate crypto confidence data.

### 4.4 Supplementary Tab Analysis

The dashboard ships with **fourteen tabs**. Two merit scrutiny.

**US Equity Picks** is entirely non-functional: "Building track record · n=0/100" with empty sub-tabs. The scoring formula (0.55 × ValueComposite + 0.45 × QualityComposite × SafetyGate) is displayed, but zero picks exist to score. This tab consumes prime navigation real estate for a feature with no actionable data since deployment.

**Closed Picks** is the audit trail — the only tab enabling forward-claim validation by comparing advertised FWD WR against realized WR. For a platform styled as an audit system, this is the evidence locker and should be prominently placed.

The remaining tabs fall into operational (Portfolios, Performance), internal diagnostics (Score Tracker, ML Health, Permutations), and external links (Links) categories. Most duplicate Overview data or expose pipeline states irrelevant to trading decisions.

**Table 4: Recommended Tab Reduction — 14 to 5**

| Current Tab | Recommendation | Rationale |
|:---|:---|:---|
| Overview | **Keep** | Consolidated landing with asset-class tiles |
| Active Picks | **Keep** | Core feed; add filter chips from Section 4.1 |
| Verified Alpha | **Merge into Active Picks** | Becomes filter toggle, not standalone tab |
| Smart Picks | **Merge into Active Picks** | Becomes "Apply Smart Gates" filter per 4.2 |
| US Equity Picks | **Hide until n≥100** | Zero actionable picks; show badge in Overview |
| Closed Picks | **Keep** | Audit validation; rename "Trade History" |
| Portfolios | **Merge into Overview** | Duplicates existing portfolio tiles |
| Dashboards | **Remove** | No unique data vs. Overview |
| Strat. Leaderboard | **Keep** | Per-strategy WR/PF rankings |
| Permutations | **Remove** | Internal combinatorial analysis |
| Performance | **Merge into Overview** | Duplicates asset-class tile data |
| Score Tracker | **Demote to Debug Mode** | Internal diagnostics only |
| ML Health | **Remove** | Empty tab at time of audit [^34^] |
| Links | **Move to footer** | External URLs in primary nav dilute focus [^159^] |

The reduction follows progressive disclosure: show decisions users need, hide infrastructure they don't [^35^]. Diagnostic depth stays accessible via an "Advanced" toggle.

### 4.5 HTML Bug Fix

The US Equity Picks tab displays leaked text: `` ` inside this block — HTML does not support nested comments and the inner `-->` would close the outer. -->``. This is a developer comment escaped into the rendered page.

**Table 5: HTML Comment Bug — Root Cause and Fix**

| Attribute | Detail |
|:---|:---|
| **File** | `audit_dashboard/template.html`, lines ~1813–1825 (UEPS section) |
| **Bug type** | Nested HTML comment with premature `-->` terminator [^34^] |
| **Root cause** | HTML parser treats `-->` inside backtick-quoted text as comment end [^157^] |
| **Visible impact** | Developer warning text renders on US Equity Picks tab |
| **Severity** | Medium — UX degradation; security risk if pattern repeats |

The comment warned: "do NOT nest comments inside this block." The irony is self-evident — the warning about nested comments triggers the exact bug it describes [^157^][^163^].

**Fix:** Replace the entire multi-line block:

```html
<!-- Before (lines 1813–1825): verbose multi-line comment containing nested `-->` -->
<!-- After: -->
<!-- UEPS mount point -->
```

This is the cleanest fix — the comment contains no runtime logic and describes server-side architecture irrelevant to end users [^34^][^170^].

**Verification:** (1) replace block with `<!-- UEPS mount point -->`; (2) reload and confirm no leaked text; (3) grep codebase for other comments containing `-->` sequences; (4) add an `htmlhint` linter or CI grep check [^34^]. Secondary cleanup: wrap 15+ `console.log` statements in a debug flag (they leak internal file paths) and remove the empty ML Health tab that presents users with a blank page [^34^]. These fixes address the most visible quality issues. They do not alter underlying statistical validity — that was the subject of Chapters 2 and 3 — but they prevent users from encountering HTML fragments, empty tabs, and contradictory filter recommendations that erode trust in engineering standards.
