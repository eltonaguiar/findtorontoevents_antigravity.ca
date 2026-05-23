# Audit + Hyrotrader Unified Implementation Queue (2026-05-04)

Sources fused:
- Kimi sec01-10 deep re-review → `reports/kimi_deep_review_audit_only_2026_05_04.md`
- Kimi 5-item enhancement queue → `reports/audit_enhancement_implementation_queue_2026_05_04.md`
- 11-engine audit hyperfocus swarm → `swarm_runs/audit_hyperfocus_v1/` (8/11 engines produced output: claude, deepseek, cerebras, opencode, kilo, xai, gemini, ollama_cloud; inception + openrouter dropped 0 KB).

## Cross-engine consensus (≥3 engines flagged)

| # | Finding | Engines | Severity |
|---|---|---|---|
| C1 | **Hyrotrader: `trading_days_logged=0` + null pick entry/stop/target prices + 16-day stale `hyro_quan_bridge.json` (only BTCUSDT)** | claude, deepseek, opencode, kilo, xai (5) | P0 |
| C2 | **Shadow probation disabled** despite documented R:R [1.5,2.0] PF 5.81 edge | claude, opencode, kilo (3-4) | P0 |
| C3 | **Take_profit null on 60/60 active picks** — R:R undefined for ALL active picks | claude, opencode (2) | **P0 BLOCKER for `feat/rr-hard-gate-shadow`** |
| C4 | **Drawdown alerts for prop-firm bands (5% daily / 8% total)** missing | deepseek, opencode, xai (3) | P0 |
| C5 | **Strategy degradation banner / regime display** | deepseek, opencode, kilo (3) | P1 |
| C6 | **Concentration risk / outlier flagging (KC=F 147%, EQUITY 10× capped/raw)** | deepseek, kilo, xai (3) | P1 |
| C7 | **PF contradiction (`hf_stats` vs `asset_class_health` panels show different PF for same trades)** | claude, deepseek (2) | P1 |
| C8 | **`total_pnl_pct = -99.99` vs `sum_raw = +202.82`** — sign-inversion / floor-clamp bug | claude (1, but high-confidence 0.92) | **P0 critical** |

## Critical blocker discovered

**The Kimi C1 R:R recommendation conflicts with our local `quality_gates.py:2492-2511` 2026-04-01 "DATA CORRECTED" comment** which claims R:R is INVERTED (1.0-1.5 = 70.8% WR best). My already-shipped `feat/rr-hard-gate-shadow-2026-05-04` branch uses Kimi's numbers. **DO NOT MERGE that PR until the conflict is adjudicated** by `tools/mutation_analysis.py` re-run on closed picks.

Also: **C3 (60/60 null take_profit) is a hard blocker for the R:R gate**. `passes_rr_hard_gate(pick)` rejects picks without TP. Until take_profit is populated, the gate would zero-out picks even if the band were correct.

## Unified queue (final ordering)

### Tier A — ship-this-week (small, no contested logic)

1. **Score Explainability Tooltips** (Kimi queue #1, S) — `audit_dashboard/template.html` info icons + popovers for F-Score / Score / Composite / Tier. No backend changes. **Best first PR.**
2. **PF contradiction disclosure footnote** (C7, S) — single template.html edit; add "headline: full history; recent: closed-only" footnote next to per-class PF.
3. **Tiered n-guard** for FUTURES n=2 / BOND n=18 / ETF n=87 — `audit_dashboard/dashboard_generator.py` adds `display_status` ∈ {`insufficient_data`, `candidate`, `stable`} based on n thresholds. Suppress WR/PF display when n<10.
4. **`audit/rr-band-reaudit`** (Kimi C1 conflict): re-run `tools/mutation_analysis.py` on closed picks; ship `reports/rr_band_reaudit_2026_05_04.md` with verdict. **Gates the merge of `feat/rr-hard-gate-shadow`.**

### Tier B — hyrotrader data-credibility (medium, requires backend)

5. **Populate `trading_days_logged` from journal** — `audit_dashboard/dashboard_generator.py` derives from `hyrotrader_journal.json` timestamps.
6. **Atomic-write fix for `hyro_quan_bridge.json`** — fix the race that truncates to 1 symbol; restore 14+ symbols.
7. **Populate `take_profit` (and entry/stop) on Hyrotrader picks** — `alpha_engine/` pick-generation path; field-name reconciliation (`take_profit` vs `target_price`).
8. **Prop-firm drawdown bands** (5% daily / 8% total) — `audit_dashboard/hyrotrader/hyro_live_signals.js` + new gauge in `hyrotrader/index.html`.

### Tier C — UI polish + risk visibility (medium-large, after Tier A+B)

9. **Best-Picks Guidance Card + Filter Presets** (Kimi queue #2, M) — Conservative/Moderate/Aggressive preset chips.
10. **Trust Badges from OOS Sharpe** (Kimi queue #3, S) — A-F grade per asset class.
11. **C-Tier Guard Rail + Paper-Only Badge** (Kimi queue #4, M) — capital-protection win.
12. **Hyrotrader Parity** (Kimi queue #5, M) — import explainability + trust badges.

### Deferred (not in current scope)

- **`total_pnl_pct = -99.99` floor-clamp bug** (C8) — needs root-cause investigation in `audit_trail/dashboard_generator.py` compounding logic; defer to dedicated investigation PR.
- **`shadow_probation` re-enable** (C2) — depends on C1 R:R reaudit + C3 take_profit fix landing first.
- **ml_score gate raise to 0.90** (Kimi C2) — blocked on ml_score fill-rate; needs widget first.

## Sequencing diagram

```
Tier A:   #1 Tooltips ──┐
                        ├─→ #2 PF footnote ──→ #3 n-guard
          #4 RR reaudit ─┘                              │
                                                       ▼
Tier B:   #5 trading_days ──→ #6 atomic write ──→ #7 TP populate ──→ #8 DD bands
                                                                          │
                                                                          ▼
Tier C:   #10 Trust badges ──→ #11 C-tier guard ──→ #12 Hyrotrader parity ←──── #9 Presets
```

## Acceptance for each Tier-A item

- **#1 Tooltips**: Playwright asserts `[data-metric-tooltip="f-score"]` is focusable, reveals "Piotroski 9 criteria"; same for `score`, `composite`, `tier`. ≥4 distinct tooltips with `aria-describedby` linkage.
- **#2 PF footnote**: Each per-class PF cell has a `<sup>` footnote-ref with text "headline=all-history, recent=closed-only resolved trades".
- **#3 n-guard**: FUTURES n=2 displays "insufficient_data" with stats hidden; BOND n=18 displays "candidate"; EQUITY n=421 displays "stable".
- **#4 RR reaudit**: `reports/rr_band_reaudit_2026_05_04.md` exists with verdict + closed-pick PF per band.

## Implementation start: Tier A #1 (Score Explainability Tooltips)

Branch: `feat/audit-score-tooltips-2026-05-04` from `chore/super-swarm-synthesis-2026-05-04` (or main).
Files: `audit_dashboard/template.html` only (UI-side first; backend `metric_definitions` block deferred to v2).
Risk: low — pure frontend additive change, no logic changes.
