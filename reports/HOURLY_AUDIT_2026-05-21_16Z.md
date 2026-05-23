# Hourly Audit — 2026-05-21 16Z

**Dashboard snapshot:** `2026-05-21T12:18:29Z` (same cron as 13Z/14Z/15Z; next refresh expected ~17Z–18Z)
**Analysis computed at:** `2026-05-21T16:14Z`
**Data basis:** `audit_dashboard/data/dashboard_data.json` — `picks.recent_closed` (n=3500)

---

## Per-asset summary (16Z windows)

| Class | 24h PF | 24h n | 7d PF | 7d n | 7d WR | 30d PF | vs 15Z |
|-------|--------|-------|-------|------|-------|--------|--------|
| CRYPTO | 2.436 | 77 | 1.361 | 888 | 47.7% | 1.318 | 24h −0.603; 7d −0.045 (softening) |
| EQUITY | 1.319 | 7 | 0.833 | 44 | 36.4% | 1.416 | 7d +0.058 **improving** ✅ |
| FOREX | 1.460 | 8 | 1.166 | 16 | 37.5% | 2.576 | **16th consecutive hr ≥1.0 post-#687** ✅ |
| COMMODITY | 4.016 | 2 | 0.243 | 38 | 10.5% | 1.005 | +0.007 noise; legacy drain ongoing |
| ETF | — | — | 1.081 | 9 | 11.1% | 2.121 | stable |
| BOND | — | — | 0.000 | 4 | 0.0% | — | n=4; too small to act |

**15Z baselines for reference:** CRYPTO 24h 3.039 / 7d 1.406; EQUITY 7d 0.775; FOREX 7d 1.083; COMMODITY 7d 0.236

---

## Key findings

### FINDING-52 CONFIRMED — `multi_asset_copytrader × COMMODITY` regime failure

7d: n=37, WR **8.1%**, PF **0.243**, sumPnL **−108.07%**

Full 7d symbol breakdown:

| Symbol | n | WR | sumPnL% | Note |
|--------|---|-----|---------|------|
| SI=F | 9 | **0.0%** | −39.82% | Silver futures — worst offender |
| PL=F | 6 | **0.0%** | −18.00% | Platinum futures (FINDING-52 orig) |
| CT=F | 13 | 23.1% | −17.54% | Cotton — all-time 54.8% WR; 7d regime failure |
| ZW=F | 3 | **0.0%** | −13.37% | Wheat |
| KC=F | 2 | **0.0%** | −10.46% | Coffee |
| ZS=F | 4 | **0.0%** | −8.89% | Soybeans |

Every commodity symbol is losing. CT=F was cited in 15Z as "main volume driver — system not broken" based on all-time WR; 7d window now shows it too is in regime failure (23.1% WR). SI=F (n=9) approaches but does not reach n≥20 solo kill gate.

**Assessment:** Pattern consistent with commodity futures regime breakdown (not random). Aggregate n=37 meets n≥20 gate, WR 8.1% <35% sustained. A BLOCKED_ASSET_STRATEGY_PAIR `("COMMODITY", "multi_asset_copytrader")` requires 2 more AI votes (currently 1/3). Do NOT kill unilaterally. Post full table to issue #686 as FINDING-52 follow-up.

**Roll-off timeline:** The pre-block `cftc_cot_commercial_signal` + `futures_momentum` trades from 15Z are separate from `multi_asset_copytrader`. COMMODITY 30d PF holds at 1.005 — historical baseline intact. If `multi_asset_copytrader × COMMODITY` 7d is regime-specific (post-May-14 only), the 30d should recover as pre-May-14 trades roll into the 7d window (~2026-05-23).

---

### NEW FINDING-53 — `battleground × CRYPTO` approaching kill gate

7d: n=**18**, WR **16.7%**, sumPnL −13.43%

| Symbol | n | WR | sumPnL% |
|--------|---|-----|---------|
| ETHUSDT | 9 | 33.3% | −4.68% |
| BTCUSDT | 4 | 0.0% | −2.72% |
| XRPUSDT | 3 | 0.0% | −4.03% |
| SOLUSDT | 2 | 0.0% | −2.00% |

**2 trades short of n=20 kill gate.** WR 16.7% is well below the 35% sustained floor. Monitor; trigger mutation analysis when n hits 20. Do not add to BLOCKED_ASSET_STRATEGY_PAIRS yet per CLAUDE.md §kill protocol.

---

### FOREX — 16th consecutive hour ≥1.0 post-#687

7d PF **1.166** (up from 1.083 at 15Z), n=16, WR 37.5%, 30d PF 2.576.

Continued confirmation that the JPY-cross BUY rule fix in PR #687 has stabilised FOREX. 7d n is low (n=16) so this streak has limited statistical power, but 16 consecutive hourly readings ≥1.0 is a consistent signal. **Do not disturb.**

---

### CRYPTO 24h softening — `alpha_engine` drag

24h PF 3.039 → **2.436** (−0.603). `claude_gainer_st` (7d n=269, WR 63.9%) remains the anchor. Drag sources (7d):
- `alpha_engine`: n=57, WR 35.1%, sumPnL **−78.54%**
- `battleground`: n=18, WR 16.7%, sumPnL −13.43%
- `luxalgo_filters`: n=131, WR 37.4%, sumPnL −28.04%
  - Worst symbols: JUPUSDT (n=13, WR 23%), ARBUSDT (n=11, WR 27%), STXUSDT (n=12, WR 33%)

`alpha_engine` WR at 35.1% is on the borderline (35% threshold) but this is the core engine — no kill action. `luxalgo_filters` WR 37.4% is above the 35% floor. Both need sustained data to confirm degradation.

---

### EQUITY 7d recovering post-#692

7d PF 0.775 → **0.833** (+0.058). Consistent with `goldmine_6x_consensus` kill in PR #692 removing the main drag. Strategy breakdown (7d):
- `multi_asset_copytrader`: n=27, WR 37.0%, sumPnL +4.04% ← positive
- `kimi_riseoftheclaw`: n=11, WR 18.2%, sumPnL −23.61% ← n<20, monitor
- `alpha_engine`: n=6, WR 66.7%, sumPnL +4.26% ← good

`stocks_rsi2_pullback` not present in 7d EQUITY — has rolled off the 7d window, consistent with prior sessions noting improving attribution. EQUITY on a recovery trajectory; issue #693 monitor criteria being met.

---

### Mutation analysis — directional bias signals

From `tools/mutation_analysis.py` (section 1, STRATEGIES THAT FLIP WR BY DIRECTION):

| Strategy | SHORT WR | n | LONG WR | n | Spread | Action |
|----------|----------|---|---------|---|--------|--------|
| `ig_contrarian_sentiment` | **61.4%** | 57 | 16.8% | 197 | 45pp | SHORT-only mutation candidate |
| `combined_confidence` | 55.6% | 9 | 10.0% | 10 | 46pp | n too small |
| `myfxbook_retail_contrarian` | 50.0% | 14 | 13.8% | 123 | 36pp | SHORT-only candidate |

`ig_contrarian_sentiment` SHORT (n=57, 61.4% WR) vs LONG (n=197, 16.8% WR) is the strongest directional bias finding this session. Recommend posting to issue #686 for cross-AI review of a SHORT-only mutation. `myfxbook_retail_contrarian` SHORT WR solid but n=14 is borderline.

---

## PR triage

| PR | Title | CI | Reviews | Mergeable | Action |
|----|-------|----|---------|-----------|--------|
| #1293 | 15Z audit | 3/3 ✅ | Greptile COMMENTED only | CLEAN | **MERGED** ✅ |
| #1292 | B10 UEPS KPI sidecar | test(3.11) ❌ | — | BLOCKED | HOLD |
| #1287 | B10 UEPS KPI panel | test(3.11) ❌ | — | BLOCKED | HOLD |
| #1279 | docs: AGENTS.md cloud agent | — | — | DRAFT | HOLD |

- **HOLD set** (#660 #658 #681 #661 — Plan v2.1 family): absent from open PR list ✅
- **Rebase-list PRs** (#669 #676 #608 #665 #644 #597 #615 #655): all merged/closed per 15Z ✅
- **Plan v2.1 guardrails** (auto REQUEST_CHANGES on PF 5.81 / ml_score 0.90 / WINNER_FILTER citations): clean ✅
- **Issue #685** (resolver-rescope DONE): no new PRs claiming resolver work ✅

---

## New strategy kill findings — mutation_analysis.py

No new strategies meeting all three kill criteria (n≥20 + WR<35% sustained + 3+ AI consensus) emerged this hour.

**Watch list for next hour:**
- `battleground × CRYPTO`: n=18 → trigger mutation analysis at n=20
- `multi_asset_copytrader × COMMODITY`: FINDING-52 symbol table posted to issue #686 for AI #2+#3 votes
- `ig_contrarian_sentiment` SHORT-only mutation: posted to #686 for review

---

## Checklist vs task constraints

- [x] Pull latest dashboard_data.json from origin/main — synced to `400af822` / `2026-05-21T12:18:29Z`
- [x] Compute per-asset PF/WR for 24h, 7d, 30d windows
- [x] Document deltas vs documented baseline
- [x] PR triage — open PRs reviewed; #1293 merged (criteria met)
- [x] HOLD set absent
- [x] Rebase-list PRs confirmed all merged/closed
- [x] Author rebase PRs (#669 #676 #608 #665 #644 #597 #615 #655) — confirmed closed per prior sessions
- [x] mutation_analysis.py run — watch-list updated, no new kills
- [x] Plan v2.1 refuted stats guardrail — clean
- [x] Issue #685 resolver-rescope DONE respected

Refs: issues #685 #686 #693 | previous: `reports/HOURLY_AUDIT_2026-05-21_15Z.md`
