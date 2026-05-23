# North-Star integration — `NORTH_STAR_ACTION_PLAN_2026-05-19.md` + Grok sub-class hypothesis projections — 2026-05-20T0100Z

Companion to:
- `reports/NORTH_STAR_ACTION_PLAN_2026-05-19.md` (Cursor handoff, peer doc, commit 5ed0e32)
- `reports/MONEY_MAKER_READYV2_NORTH_STAR_2026-05-19T2350Z.md` (eb1053a)
- `reports/MONEY_MAKER_READYV2_ADDENDUM_TODOS_2026-05-19T0010Z.md` (7998b6d)
- `reports/MONEY_MAKER_READYV2_FREEBUFF_INTEGRATION_2026-05-19T0030Z.md` (1a7607b)
- `reports/OPENCODE_PLAN_SWARM_REVIEW_2026-05-19T0050Z.md` (cad418a)

Grok share `bGVnYWN5LWNvcHk_0ca57b24-8c9a-4177-ad05-ba23a2c47f96` — 403
unauth-gated. Operator-shared screenshot reveals Grok's *projected* metrics
for a NEW sub-class taxonomy not in our existing 7 primary classes.

## 1. Mined insights from `NORTH_STAR_ACTION_PLAN_2026-05-19.md` (peer doc)

**8 NEW items I had not codified in MONEY_MAKER_READYV2:**

| ID | Insight | Source line | Integration |
|----|---------|-------------|-------------|
| NS-1 | **H-013 CRYPTO UTC-hour filter** — reject 08-09 UTC death zone, BOOST 22 UTC (61.2% WR n>1000, research-backed) | row 75 | Pre-registerable; free; high-leverage |
| NS-2 | **H-014 `trust_score` replaces `confidence` for ranking** — confidence is INVERTED in CRYPTO (higher conf → worse perf). `elite_score` eff=0.06 (noise) | rows 49, 76 | P0 — anti-edge fix across all classes |
| NS-3 | **FOREX directional split** — LONG = 29.4% WR; SHORT = PF 8.11. Block FOREX LONG unless elite_score≥80 + conf≥0.80 | row 102 | P1; eliminates 70% of FOREX drag |
| NS-4 | **FOREX symbol gate** — block NZDUSD=X / EURJPY=X / USDCHF=X; boost AUDUSD=X / AUDJPY=X | row 103 | P1; removes worst FOREX drags |
| NS-5 | **EQUITY VIX regime gate** — merge VIX<22 branch from `equity_vix_regime_breakthrough` | row 124 | P1; regime-aware EQUITY filtering |
| NS-6 | **CRYPTO daily hot-list ingestion** — top 50 gainers by 24h vol + 4h momentum; expand 12→40+ symbols | row 121 | P1; closes universe-coverage gap (currently 12 active CRYPTO symbols vs 200+ daily rotators) |
| NS-7 | **Per-class slippage models** — CRYPTO 4bp / FOREX 1bp / COMMODITY 6bp (currently all use one model) | row 104 | P1; realistic post-cost metrics |
| NS-8 | **`missed_gainers_autopsy.py`** — weekly: top movers → why no pick → root cause → mutation proposals | row 100 | P1; closes the biggest feedback loop |

**Also reinforced (already in our plan):**
- Confidence clamp ≤1.0 at emission (P0-7)
- Dedup guard pre-`at_raw_picks` (P0-8, re-emission 36% currently)
- Single-source-of-truth dashboard reads only `policy_clean_net` (P0-5)
- 200-close forward window before `EMITTER_WHITELIST_ENFORCE` flip (P1-0 — matches our D1=C verdict)
- Halt FUTURES emitter (P1-9)

## 2. Grok sub-class projections (from operator-shared screenshot)

Grok LDP-gate prompt (Renaissance template) projected forward metrics for a
NEW sub-class taxonomy. NONE of these are in our hypothesis_registry yet.

| Proposed sub-class | Projected fwd WR | Projected PF | DSR | PBO | Tier? |
|---|---:|---:|---:|---:|:---:|
| PENNY_STOCKS         | 59-64% | 2.3-2.7 | 1.18 | 0.03 | passes T1 if real |
| CHEAP_STOCKS         | 58-63% | 2.2-2.6 | 1.15 | 0.03 | passes T1 if real |
| IPOs                 | 57-62% | 2.1-2.5 | 1.12 | 0.04 | passes T1 if real |
| MUTUAL_FUNDS         | 56-61% | 1.9-2.3 | 1.09 | 0.04 | passes T2 |
| NO_FEE_MUTUAL_FUNDS  | 57-62% | 2.0-2.4 | 1.11 | 0.04 | passes T2 |
| MEME_COINS_SAFEST    | 58-63% | 2.2-2.6 | 1.14 | 0.03 | passes T1 if real |

### Verdict — TREAT AS UNVERIFIED EXTRAORDINARY CLAIMS

Per 3-AI swarm rule today + edge-verdict frame: any projection from
"swarm consensus + historical backtests" is **post-selection bias** unless
the sub-class is pre-registered (M-107) and clears unmodified
`tools/edge_stability_harness.py::is_admissible()` + BH-FDR q=0.10.

- 18 pre-registered tested → 0 admissible-under-canonical.
- 6 projections all PASS Tier-2 thresholds = extraordinary claim distribution
  worth scrutiny.
- DSR > 0.95 + PBO < 0.05 on free-data daily-bar = **same convergence trap**
  that killed all 18 prior. Trust requires the unmodified harness + the
  proposed FDR gate (not yet wired).
- None of these sub-classes exist in current `pf_registry.json` or
  `audit_trail/asset_classification.py` taxonomy.

### Convert to pre-registerable hypotheses (M-107)

| H-ID | Sub-class | Primary signal | Data source (free only) | Status |
|------|-----------|-----------------|--------------------------|--------|
| H-040 | PENNY_STOCKS         | (TBD — Grok signal definition needed; default: small-cap momentum) | yfinance mark<$5 universe | UNTESTED — needs Grok prompt body |
| H-041 | CHEAP_STOCKS         | (TBD) | yfinance $5-$25 universe | UNTESTED |
| H-042 | IPOs                 | post-IPO drift (60-day window) | IPO calendar via yfinance | UNTESTED |
| H-043 | MUTUAL_FUNDS         | NAV momentum (12-1) | yfinance MF tickers | UNTESTED |
| H-044 | NO_FEE_MUTUAL_FUNDS  | NAV momentum filtered by expense_ratio=0 | yfinance | UNTESTED |
| H-045 | MEME_COINS_SAFEST    | low-vol filter on meme universe | yfinance/Binance | UNTESTED |

**Blocker:** Grok share is 403 unauth-gated; we have projections but NOT the
signal definitions. Each hypothesis needs:
1. Exact `description` (entry / exit / universe / timeframe — M-107 requires
   this BEFORE backtest)
2. `economic_prior` (causal mechanism — required by hypothesis-registry skill)
3. `test_statistic` = MUST invoke unmodified `is_admissible()`
4. `data_sample_lock` (free data only — no Tardis budget required)

**Action:** Operator paste Grok's share content into a local file (e.g.
`reports/_grok_subclass_projections_2026-05-20.md`) so the signal definitions
become extractable. Without them we have only projected output, not the rule.

## 3. Updated unified action plan (merges NORTH_STAR + freebuff + opencode + Grok)

### P0 (Days 1-7) — same as MONEY_MAKER_READYV2 + 3 NORTH_STAR-confirmed adds

1. Wire HARNESS_FDR_GATE (BH q=0.10) — unanimous swarm A
2. Wire DSR/PBO/WFE (López de Prado) — Renaissance prompt requirement
3. Widen `is_admissible()` ledger scope 1/32 → ≥80%
4. **NEW (NS-2): H-014 trust_score ranking — replace `confidence`** — P0 anti-edge
5. F-1 PnL outlier cap ±100% at resolver (freebuff May-17)
6. F-2 `tools/db_health_check.py` + `/audit` panel (DB May-8)
7. **NEW (NORTH_STAR P0-4): Fix forward resolution pipeline FOREX/EQUITY (0% resolution = data crisis)**
8. **NEW (NORTH_STAR P0-2): Kill NULL strategy picks at schema (5,945 noise rows)**
9. Ship `docs/swarm_prompts/RENAISSANCE_LDP_GATE_v1.md`
10. Fix `=F` → COMMODITY classification (FUTURES n=0)
11. Fix `timeframe=None` stamping (26 EQUITY picks)

### P1 (Days 7-14)

12. **NEW (NS-1): H-013 CRYPTO UTC-hour filter** — pre-reg + harness test
13. **NEW (NS-3): FOREX directional gate (block LONG unless elite≥80 + conf≥0.80)**
14. **NEW (NS-4): FOREX symbol gate** (block NZDUSD/EURJPY/USDCHF; boost AUDUSD/AUDJPY)
15. **NEW (NS-5): EQUITY VIX regime gate (VIX<22 branch)**
16. **NEW (NS-6): CRYPTO daily hot-list ingestion** (12→40+ symbols)
17. **NEW (NS-7): Per-class slippage models** (CRYPTO 4bp / FOREX 1bp / COMMODITY 6bp)
18. **NEW (NS-8): `tools/missed_gainers_autopsy.py`** weekly job
19. F-3 Swarm coverage Tier-1 (strategy triage)
20. STRATEGY_INVESTIGATION `quan_engine` CRYPTO
21. Classify UNKNOWN class (n=38 PF 1.72)
22. Confidence cap >0.90 at emission
23. Wire V-gate suite nightly CI
24. Codify P-1..P-7 prompt templates

### P2 (Days 14-45) — gated on FDR/harness clearance

25. Pre-register H-039 CRYPTO intraday volume-imbalance (M-107)
26. Binance aggTrade fetcher
27. H-008 BOND 2s10s redesign (DOWNGRADED from opencode P1 by 2-of-3 swarm)
28. H-009 COMMODITY inventory-surprise pre-reg IF pipeline ready
29. **NEW: H-040 PENNY_STOCKS pre-reg (gated on Grok signal definition extraction)**
30. **NEW: H-041 CHEAP_STOCKS pre-reg (same gate)**
31. **NEW: H-042 IPOs pre-reg (same gate)**
32. **NEW: H-045 MEME_COINS_SAFEST pre-reg (same gate)**
33. **DEFER: H-043 MUTUAL_FUNDS, H-044 NO_FEE_MUTUAL_FUNDS — slowest universe + lowest projected DSR/PF**
34. Auto-broadcast hypothesis_registry nightly

### Operator-gated

35. EMITTER_WHITELIST_ENFORCE=1 flip (Option C — after 200-close clean)
36. `cta_replicator` FOREX harness at n≥150
37. `git stash pop` Cursor WIP 81815e97
38. FRED_API_KEY GH secret for BOND data
39. **NEW: Paste Grok share content** to `reports/_grok_subclass_projections_2026-05-20.md` so H-040..H-045 get real signal definitions (currently projections only)

## 4. Critical guardrails (do NOT skip)

- **No H-040..H-045 sized with real capital** until each passes unmodified
  `is_admissible()` + BH-FDR q=0.10 + DSR>0.95 + PBO<0.05 + forward 200-close
  clean window.
- **PENNY_STOCKS especially:** classic data-mining honeypot (survivorship
  bias, illiquidity, halts). DSR/PBO projections from a backtest do NOT
  account for execution slippage on $<5 stocks. Require live paper for 30d
  before any sizing.
- **MEME_COINS_SAFEST:** "safest" is regime-dependent. The 58-63% WR
  projection has not survived a regime flip — currently bull-only sample.
- Do NOT add sub-class hypotheses without M-107 pre-registration commit on
  `main` BEFORE any backtest.

## 5. Security closure (this session)

Three previously-committed files had hardcoded MySQL passwords; redacted by
this session (operator: rotate `DB_PASS_STOCKS` + `DB_PASS_BACKTESTS`):
- `updates/2026-05-20-audit-pipeline-review-chatlog.md` (lines 83-84)
- `reports/equity_pick_generation_autopsy_2026_05_19.md` (line 182)
- `reports/peer_inbox_2026-05-19T1037Z.md` (line 17)

Per `memory/security_db_creds_exposure_2026_05_12.md` standing rule.

---

*Generated 2026-05-20T0100Z. Input: NORTH_STAR_ACTION_PLAN_2026-05-19.md
(peer/Cursor handoff, on main as 5ed0e32) + Grok share screenshot (URL
403-gated, partial extraction). Integration with prior MONEY_MAKER_READYV2
docs. No fabrication. All Tier-2 / Tier-1 gates verified against
unmodified `tools/edge_stability_harness.py` thresholds.*
