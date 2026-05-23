# A6 — CT=F Correlation-Regime Cross-Check — 2026-05-12

**Trigger:** Peer's `post_concentration_action_plan_20260512T225914Z.md` A6 flagged GOLD↔EQUITY correlation crossed +0.20 → +0.77 (diversifier moving WITH equities). Question: does CT=F (the COMMODITY class's single-symbol concentration leader, 75.57% share) also have correlation breakdown vs SPY, which would invalidate the "COMMODITY = independent factor" premise behind sizing it up?

**Source:** `audit_dashboard/data/correlation_regime.json` @ 2026-05-12T23:04:15Z (123 observations).

## Verdict

**GREEN.** CT=F is still uncorrelated to equities. The GOLD↔EQUITY regime crossing is **gold-specific**, not a broad commodity-diversifier breakdown. CT=F sizing capacity model (peer's A4) does **not** need to pause on correlation grounds — the ADV-impact gate remains the binding constraint.

## Numbers

| Pair (against EQUITY=SPY, index 3) | Current 30d | Baseline 60d | Delta | Note |
|---|---|---|---|---|
| BOND ↔ EQUITY | +0.4858 | +0.2830 | +0.20 | Modest correlation increase — bonds risk-on lean |
| **COMMODITY_GOLD ↔ EQUITY** | **+0.7674** | +0.2024 | **+0.57** | **Confirmed crossing — gold no longer diversifier** |
| CRYPTO ↔ EQUITY | +0.2011 | +0.2384 | -0.04 | Stable |
| ETF_SMALLCAP ↔ EQUITY | +0.9090 | +0.8303 | +0.08 | Already coupled (same factor — index β) |
| FOREX_USD ↔ EQUITY | -0.7726 | -0.2086 | -0.56 | DXY strongly inverse (risk-on USD weakness) |
| **FUTURES_COT (CT=F) ↔ EQUITY** | **+0.0451** | +0.0754 | -0.03 | **Independent — no regime crossing** |

CT=F vs all classes (current 30d):

| CT=F vs ... | Corr |
|---|---|
| BOND | +0.0996 |
| GOLD | +0.0460 |
| CRYPTO | -0.1047 |
| EQUITY | +0.0451 |
| ETF_SMALLCAP | +0.2020 |
| FOREX_USD | -0.1649 |

Every pair within ±0.20 except IWM (+0.20). CT=F is the cleanest diversifier in the whole correlation matrix right now.

## Implications for peer's A4 (CT=F capacity model)

1. **Correlation gate: PASS.** No need to relax sleeve sizing based on a "commodity is the new equity" thesis. CT=F is the exception that makes COMMODITY genuinely independent — it just happens to be 75% of class PnL by accident of `multi_asset_cot` strategy concentration.

2. **The gating constraint remains capacity (ADV impact)**, not correlation. The 5% ADV threshold the swarm Q4 question proposed is the right metric. Cotton futures avg daily volume ~25k contracts at ~$35k notional/contract = $875M ADV. 5% cap = $43.75M max sleeve size, well above any retail allocation under discussion.

3. **GLD is no longer a diversification surrogate for COMMODITY.** If gold and equities are running +0.77, holding GLD alongside SPY/QQQ doesn't reduce factor exposure — it amplifies it. Anyone currently using GLD as the "defensive metal sleeve" should treat it as risk-on equity beta until correlation reverts under +0.35.

## Single-symbol-class re-framing

Peer's swarm question Q2 asked: should the dashboard *reframe* COMMODITY entirely as "CT=F sleeve" or keep class rollup with WARN badge? This A6 result argues **keep the class rollup with the WARN badge**:

- CT=F genuinely retains diversification benefit (uncorrelated to all 6 other classes in matrix)
- The WARN badge already exposes the single-symbol risk transparently
- Reframing as "CT=F sleeve" loses the framing that future commodity strategies (DBC, CORN, copper, etc.) could rotate INTO the class to broaden it. The class header should remain `COMMODITY` so the visual incentive is "we want more breadth here," not "we already have one good symbol, stop looking."

## Cross-link: V4 picks placed this round

`reports/v4_edge_picks_and_theswarm_cleanup_2026-05-12_2112EST.md` placed AMEX:CORN + AMEX:DBA on V4 to add commodity breadth via ETF surrogates. Both have negligible correlation to CT=F's COT-positioning signal, so they grow the COMMODITY-class breadth without contaminating the CT=F sleeve's edge. This is the correct direction per A6 finding.

## Open questions sent back to swarm

1. CT=F corr to IWM is +0.20 (highest in matrix for CT=F). IWM is small-cap equity — would adding `Russell-2000 size factor` exposure dilute the COMMODITY independence claim? Probably not at this level, but worth tracking if it crosses +0.35.

2. The 30d window may be too short to catch slower regime changes. Should A6 be repeated with a 90d window for confirmation? `correlation_regime_sidecar.py` would need a `--baseline-days 90` flag.

3. Should the dashboard add a `correlation_regime_alert_count` field to `dashboard_data.json` summary so the GOLD-EQUITY crossing is visible at top-of-page, not buried in `audit_dashboard/data/correlation_regime.json`? (Could be a small follow-up PR.)

## Status of post-concentration action plan items

| Action | This session | Status |
|---|---|---|
| A1 — multi_asset_cot PF verify | (peer code shipped, awaiting cron) | — |
| A2 — active_picks_sync --apply | (peer code shipped, workflow flip pending) | — |
| A3 — per-strategy concentration | (peer building this round) | — |
| A4 — CT=F capacity model | (open; correlation gate PASS per this A6) | Unblocked on corr side |
| **A5 — UI surface for WARN tier** | (open, my candidate next) | TBD |
| **A6 — Correlation-regime CT=F check** | **DONE this report** | ✅ |
| A7 — CRYPTO sub-T2 root-cause | (gated on A3) | — |
| A8 — Friction-adjusted DSR | (peer code shipped, awaits cron) | — |
