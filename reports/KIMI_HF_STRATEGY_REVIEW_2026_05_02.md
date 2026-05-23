# Review — Kimi Code "HEDGE-FUND-GRADE STRATEGY IMPROVEMENT REPORT v99.0"

**Date:** 2026-05-02
**Reviewer:** Copilot (Claude Sonnet 4.5) on `copilot/hedge-fund-strategy-improvement` @ `c5d266b`
**Source under review:** Kimi Code report dated 2026-05-01 ("Hedge-Fund-Grade Strategy Improvement Specialist")
**Goal alignment:** Goal #1 — phenomenal performance across all asset classes on `findtorontoevents.ca/audit`.

This review validates each Kimi recommendation against the **current code in this repo**, the shipped 30-day edge analysis (`reports/EDGE_ANALYSIS_2026_04_30.md`), the 3,500-pick edge findings (`reports/HEDGE_FUND_EDGE_FINDINGS_2026_04_22.md`), the near-miss deep dive (`reports/NEAR_MISS_DEEP_DIVE_2026_04_29.md`), and the latest hedge-fund performance reviews (`reports/hedge_fund_performance_review_*_2026_04_27.md`). I have **not** independently re-derived Kimi's "500 shadow-blocked picks" cohort numbers — those are taken at face value where directionally consistent with shipped data and called out where they conflict.

---

## TL;DR — verdict per Kimi action

| # | Kimi action | Verdict | Why |
|---|---|---|---|
| 1 | Eliminate C-Tier crypto | ✅ **Already shipped** — the audit-dashboard HC gate (`audit_dashboard/hc_filter.js:200-237`, `passesPerAssetTierContract`) only allows S/A/B. C is rejected by construction. Kimi's "1-line change" already exists. | Validates the rule is in production. Open question is whether it leaks anywhere upstream. |
| 2 | Volatility targeting / vol-scaled position sizing | ✅ **Valid + high-ROI**. Already on roadmap per `reports/deep_dive_crypto_mdd_reduction_2026_04_28.md` (referenced in AGENTS.md). Not yet wired into `audit_trail/universal_pick_resolver.py` or any sizing call. **Recommend ship**. | MDD 140% on crypto is the single biggest blocker to T2 (per hedge-fund performance review tier table). |
| 3 | Per-asset-class confidence bands | ⚠️ **Partially shipped + partially conflicting**. Crypto dead band `[0.60, 0.70)` is already in `hedge_fund_quality_gate.py:43`. Equity `[0.60, 0.65)` already in `:61-63`. Forex `[0.95, 1.0001)` already in `:97-99`. Commodity `< 0.70` already in `:70`. Kimi's *new* claims (block crypto >0.90, allow 0.85-0.90 as "sweet spot 82% WR PF 11.8") **conflict with Cerebras 2nd-opinion findings** in our existing report which flagged `[0.85, 0.90)` as "too small to act on yet (n=5 at 25% WR — flagged but deferred until OOS purged K-Fold)". **Do not act without re-deriving on current 3500-pick ledger.** |
| 4 | Forex emergency: trusted-tier only | ⚠️ **Partially valid; partially blocked on a known bug**. The forex disaster is real (last-100 WR 5%) — but per AGENTS.md and `reports/action_B_resolver_2026_04_27.md` the **forex/commodity result is contaminated by a resolver bug** (`alpha_engine/outcome_resolver.py:97`, `PNL_WIN_THRESHOLD=0.00001`). 63-67% of forex closes are noise. **Fix the resolver first** before tuning forex gates. Trusted-tier-only is a reasonable interim, but cite the resolver dependency. |
| 5 | Deprecate `elite_score`, use `ml_score >= 0.60` | ❌ **Outdated premise**. The "memory note" Kimi quotes (`elite_score r=-0.001`) was **explicitly invalidated** by `EDGE_ANALYSIS_2026_04_30.md §TL;DR-7`: current data shows `elite_score` Spearman ρ=+0.082 (p=1e-6), `trust_score` ρ=+0.196 (p=1.7e-31). The stronger signal is **`trust_score`**, not `ml_score`. ML-pump-probability gating is already implemented in `hedge_fund_quality_gate.py:113-114, 298-312` with bounded `[0.35, 0.50)` sweet spot derived from 486 RESOLVED Claude ML picks. **Do not deprecate elite_score; do consider a `trust_score` minimum.** |

**Net:** 2 of Kimi's 5 top actions are already shipped. 1 is high-ROI and recommended (vol targeting). 1 is correct-direction but blocked on a known data-quality bug (forex). 1 is based on outdated stats and should be rejected (elite_score deprecation).

---

## Section-by-section validation

### Section 1 — "Real money patterns"

#### 1.1 S-Tier Crypto (n=16, WR 87.5%, PF 30.62)
- **Statistical caveat is correct.** Kimi explicitly flags Wilson lower bound at 62%. ✅
- **DOGEUSDT contradiction is REAL.** Kimi notes DOGEUSDT shows in S-Tier active symbols but is in `CRYPTO_BANNED_SYMBOLS` (`hedge_fund_quality_gate.py:33-36`). This is a genuine inconsistency worth investigating — either the banned-symbol list is stale, or the S-tier label is being assigned without enforcing the ban (sequencing bug).
- **Recommendation:** Audit the active S-tier symbol list against `CRYPTO_BANNED_SYMBOLS`. If DOGEUSDT really is producing live picks, either (a) re-evaluate the ban (the original PF<0.50 rationale may be stale per `crypto_rsi4h_killzone_review_2026_04_28.md`) or (b) tighten enforcement order so the ban runs before S-tier stamping.

#### 1.2 Equities L100 (WR 59%, PF 2.90, +176%)
- **Validated against `EDGE_ANALYSIS_2026_04_30.md`:** that report measured 30-day EQUITY PF **1.85**, not 2.90. The L100 vs 30d window difference can explain this — L100 likely spans further back. Both are consistent with "EQUITY is a Tier-2 franchise" framing.
- **The 2026-04-30 floor lowering (55→45) is shipped.** `audit_dashboard/hc_filter.js:38` confirms. ✅
- **Kimi's "lower further to 40" suggestion:** plausible but **must be A/B'd first**. The 55→45 move was justified by lifting HC pass-set 16→57 with PF 4.05. There is no reported delta for 45→40 yet. Do not lower without an explicit re-run of the same edge analysis.

#### 1.3 ETFs "resurrection"
- Plausible but **n=20 at L20 is too small** to declare "T1". Kimi's own appendix admits this (Wilson [58%, 84%]). Treat as a data-collection cohort.

#### 1.4 Forex catastrophe
- **Confirmed.** `EDGE_ANALYSIS_2026_04_30.md` shows FOREX 30d PF 1.53 BUT 602 picks; Kimi's L100 (5% WR, -41%) refers to the most-recent slice. Both are likely true: FOREX has a few large winners hiding many small losers, masked by the resolver-noise bug.
- **Trusted filter rescue (49% WR, PF 3.59, n=273)** — repo does have trust-tier infrastructure (`config/hf_quality_gates.json:13-23`, `min_trust_tier: WATCH`). Kimi's recommendation to apply trust-tier filtering to forex specifically is reasonable.
- **Critical caveat:** AGENTS.md explicitly says "Block FOREX/COMMODITY verdicts until alpha_engine/outcome_resolver.py resolver-noise is fixed." Any forex tuning is **premature** until that lands.

#### 1.5 Commodities
- **`COMMODITY_CONFIDENCE_MIN = 0.70` is already shipped** at `hedge_fund_quality_gate.py:70`. ✅
- **`cftc_cot_commercial_*` "top strategy"** — the top 30d commodity strategies in `EDGE_ANALYSIS_2026_04_30.md` aren't broken out, but COT-based signals are credible. Recommend instrumenting before promoting.

### Section 2 — Per-asset filter recommendations

| Kimi rec | Current state | Verdict |
|---|---|---|
| Crypto score floor 55 / S-tier 70 | `scoreFloorCrypto: 55` (shipped) | ✅ matches; S-tier 70 is a stamping criterion not a floor — minor terminology gap |
| Crypto FWD WR 70 → 60 | `forwardWRMinPctCrypto: 70` (shipped 2026-04-23) | ⚠️ Defer until vol-targeting + resolver fix; lowering FWD WR alone reintroduces the C-tier-style losers |
| Crypto confidence: block <0.75, allow 0.75-0.90, block >0.90 | Current: dead band `[0.60, 0.70)` only | ❌ Rejects too much. Existing dead band has empirical support (n=882, WR 29.9%, PF 0.69). Kimi's <0.75 cliff has no equivalent citation in our reports. |
| Crypto R:R floor 1.5 → 1.0 | `min_risk_reward: 0.8` in `config/hf_quality_gates.json` | ⚠️ Already 0.8, not 1.5. Kimi may be referencing a downstream RR_GATE that lives elsewhere or is from a stale gate config. Need to identify the actual RR_GATE Kimi audited (possibly in dashboard JS) before acting. |
| Eliminate C-tier crypto from trading | `passesPerAssetTierContract` already enforces S/A/B only | ✅ Shipped |
| Equity score 45 / FWD WR 50 | Score floor 45 ✅, FWD WR 70 currently | ⚠️ FWD WR 70→50 plausible but A/B before shipping |
| Equity AAPL re-evaluation | `EQUITY_BANNED_SYMBOLS = {"AAPL"}` based on n=15 | ✅ Valid concern — re-derive on current ledger |
| Forex trusted-tier only | Not currently AC-conditional | ⚠️ Implementable but blocked on resolver fix |
| Commodity conf >= 0.70 | Already shipped | ✅ |
| Bonds: gather n>50 | n=20 currently | ✅ Correct posture |

### Section 3 — Near-miss opportunities

#### 3.1 RR_GATE 1.5 → 1.0
- **Cannot validate without locating Kimi's exact RR_GATE.** `config/hf_quality_gates.json:6` has `min_risk_reward: 0.8` (already lower than 1.5). If Kimi audited a different gate (perhaps in a dashboard preset or in the `kelly_cap_fraction` path), point at the file.
- The existing `note_rr_band` in the config file ("Closed-book: R:R ~1.0–1.5 band strongest; R:R > 2.0 often never hits TP") **directly contradicts Kimi's "R:R >= 2.0 optimal at 58% WR PF 3.06" claim**. This is a real disagreement that warrants re-derivation on the current ledger.

#### 3.2 QUALITY_GATE 44.1% accuracy / deprecate elite_score
- **Outdated.** See TL;DR row 5 above. `EDGE_ANALYSIS_2026_04_30.md` measured a current ρ=+0.082 for elite_score (statistically significant), and ρ=+0.196 for trust_score. The "44.1% accuracy on shadow-blocked" framing is **a different question** than "is the score predictive on the population that passes." Both can be true: a gate can be net-negative *on the blocked subset* while still being a useful filter on the *passed* subset (because it's the picks-that-passed that actually trade).
- **Recommendation:** Reject "deprecate elite_score". Add a parallel `min_trust_score` gate instead, since trust_score is empirically the stronger signal.

#### 3.3 WINNER_FILTER (confidence > 0.85)
- The repo's `confidenceLoBand: 0.85` / `confidenceHiBand: 0.95` (`hc_filter.js:45-46`) is more nuanced than Kimi describes — it isn't a flat ban above 0.85; it's a forward-trades-required gate (`confidenceLoBandFwdTradesMin: 30`). Kimi's "blocking 4 winners worth +26.79%" finding may be picking up the secondary gate, not a flat ban. **Re-confirm exactly which gate produced those 4 blocks** before reshaping confidence bands.

### Section 4 — Conditional unblocks

- **DOGEUSDT conditional unblock proposal:** sound *if* the S-tier observation in §1.1 is real. See §1.1 verdict.
- **Forex banned-pair conditional allow:** depends on resolver fix landing first.
- **AAPL re-evaluation:** valid; matches our own near-miss / stale-ban patterns.
- **Empty-strategy block:** **already shipped** at `hedge_fund_quality_gate.py:235-236`. ✅
- **`Breakout Momentum` forex-only ban:** already shipped at `:84-86`, with the exact rationale Kimi cites. ✅

### Section 5 — Data-layer additions

| Kimi tier | Item | Repo state | Recommendation |
|---|---|---|---|
| T1 | Regime detection at entry | Partial: regime fields exist but not always at entry-time | Wire-up project; medium effort |
| T1 | Volatility targeting | Not wired into sizing | **Ship — highest ROI per existing reports** |
| T1 | MFE/MAE tracking | Not in closed schema | Schema migration; medium effort |
| T2 | Funding rates (crypto perps) | Not used | Worthwhile data add |
| T2 | On-chain metrics | `stablecoin_flow_momentum` exists | Incremental adds |
| T2 | Earnings calendar guard | Not wired | Worthwhile — prevents gap risk |
| T3 | COT reports | Strategy-level only | Defer |
| T3 | Dynamic correlation matrix | Static `corrPairs` (`hc_filter.js:87-94`) | Defer |
| T3 | Point-in-time blocklist | HEAD-only currently | **Ship — required for valid backtests** (matches our look-ahead concerns) |

---

## Recommended action queue (re-prioritized)

Ranked by `(expected_pnl_lift × confidence_in_estimate) / effort`, taking into account what's already shipped and what's blocked on the resolver bug.

### P0 — Ship now (blocks Goal-#1 progress otherwise)

1. **Fix `outcome_resolver.py` resolver-noise bug** (AGENTS.md-flagged; `PNL_WIN_THRESHOLD=0.00001`). Without this, *every* forex/commodity recommendation in Kimi's report is statistically untrustworthy.
2. **Audit DOGEUSDT (and any other `CRYPTO_BANNED_SYMBOLS` member) appearing in S-tier active picks.** This is a sequencing/contract violation — fix before tuning anything else.

### P1 — High ROI, low risk

3. **Vol-targeting for crypto sizing.** Implement 20d realized-vol percentile scaling per the deep-dive plan. Target: drop crypto MDD from 140% to <30% to make the class T2-eligible on MDD.
4. **Add `min_trust_score` gate** in `config/hf_quality_gates.json` (env-overridable). `trust_score` ρ=+0.196 is the strongest predictor we've measured; not currently used as a gate.
5. **Point-in-time blocklist** — git-log the blocklist file so retrospective analyses use historical state, not HEAD. Critical for backtest validity even though near-zero immediate PnL impact.

### P2 — Valid but requires re-derivation first

6. Crypto FWD WR `70 → 60` — only after vol-targeting lands; otherwise reintroduces losers.
7. Equity FWD WR `70 → 50` — re-derive lift on current ledger (the 55→45 score-floor change already lifted EQUITY HC picks 16→57).
8. ETF score floor 35 → 40 with FWD WR → 55 — small-sample; re-derive.
9. Equity score floor 45 → 40 — small-delta; A/B with new HC pass-set count.

### P3 — Reject or restate

10. **Reject** "deprecate elite_score". Replace with "**add** trust_score gate; keep elite_score" — outdated correlation claim per `EDGE_ANALYSIS_2026_04_30.md §TL;DR-7`.
11. **Reject** the 0.75/0.85/0.90 crypto confidence reshaping until the n=5 sub-band issue (Cerebras flagged) is resolved with more data.
12. **Reject** "lower R:R floor to 1.0" until we identify the actual RR_GATE Kimi audited (current `min_risk_reward` is already 0.8). Existing config-note empirically argues *against* R:R>=2.0 being optimal.

### P4 — Already shipped (no action)

- C-Tier crypto blocked at HC gate (`passesPerAssetTierContract`).
- COMMODITY confidence ≥ 0.70 (`COMMODITY_CONFIDENCE_MIN`).
- FOREX overconfidence `[0.95, 1.0001)` reject band.
- EQUITY `[0.60, 0.65)` reject band.
- CRYPTO `[0.60, 0.70)` dead band.
- `Breakout Momentum` forex-only ban.
- Empty-strategy hard reject.
- ML pump-probability sweet-spot gate `[0.35, 0.50)` for ML-sourced picks.
- Equity score floor 55 → 45 (shipped 2026-04-30).

---

## Statistical-validity notes (Kimi Appendix A — endorsed)

Kimi's appendix is the strongest part of the report. The Wilson-CI ranges and Bonferroni call-out are correct. **Apply α = 0.01 per-test** if running multiple changes in one PR. The repo already has multiple `tools/walkforward_validator.py` and `tools/mutation_analysis.py` scaffolds — use them before any P2 item ships.

The survivorship-bias warning (Kimi A.3) is the same point our `STRATEGY_INVESTIGATION_BEFORE_KILL.md` and `MUTATION_THREE_AXIS_PROTOCOL.md` make about kill decisions — gate accuracy on the blocked subset is **not** the same metric as gate accuracy on the population.

---

## Open questions for the Kimi cohort to disclose

1. **Which exact RR_GATE was audited?** `config/hf_quality_gates.json` has `min_risk_reward: 0.8`, not 1.5. Source-of-truth needed.
2. **Which `elite_score` cutoff was used (30 in the report) and on which picks ledger?** The 30 floor doesn't match `min_elite_score: 80` in `hf_quality_gates.json`. Cohort definition matters.
3. **The "500 shadow-blocked picks" cohort** — date range, asset-class breakdown, and snapshot SHA needed to reproduce.
4. **The "Forex Trusted Filter (49% WR, PF 3.59, n=273)"** — which trust-tier subset, which date window? Need to confirm against `min_trust_tier: WATCH` in current config.
5. **DOGEUSDT in S-tier active symbols** — please share the active-pick row so we can verify the contract violation.

Once those land, P2/P3 items can graduate to P1.

---

## Process note

Per the repo's **Wire-Up Rule** (AGENTS.md), any new gate code added in response to this review must include at least one production caller (e.g. in `audit_trail/dashboard_generator.py` or `alpha_engine/smart_picks_engine.py`). Sidecar-only additions will be closed.

Per the **Document Every Fix** rule, any P0/P1 change shipped from this review will get its own `updates/2026-05-XX-*.md` describing what was broken, what changed, and how it was verified.
