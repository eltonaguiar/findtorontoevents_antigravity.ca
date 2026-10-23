# Asset-Class Review — Which Class Is the Winner? (2026-10-22)

**Author:** Zod (Inception) — independent review of the audit surface + agent-dropped reports + live DB artifacts.
**Date:** 2026-10-22
**Scope:** findtorontoevents.ca/audit and its data payload, `audit_dashboard/data/dashboard_data.json`, `research/asset_class/*/run_2026-10-17*` (P5 agent syntheses), `money_ready_verdict.json`, `top_notch_money_ready.json`, `forward_candidate_scoreboard.json`, and orphan audit pages.

---

## TL;DR

**No asset class is a verified "winner" (MONEY‑READY) right now.** Every independent source agrees:
the standing promotion gate (Tier‑2: n≥100 clean, PF≥1.5, WR≥50%, MDD<20%, CI‑LB≥1.2) is **not passed by any class**.

Among the four traditional classes the user asked about, the ranking by real *closed-pick* evidence is:

| Class | Verdict | Best supporting evidence |
|---|---|---|
| **EQUITY (stocks)** | 🏆 **Best candidate** | Closed n=22, expectancy **+1.95%**/trade, PF **11.9**, WR 45.5%; UEPS long-term-value book (22 open positions); GOOGL 100% WR (n=17). Small sample → CANDIDATE, not proven. |
| **COMMODITY** | WATCH | PF ≈1.03–1.33; only n=4–16 closed. Carry/momentum diversifier wired but research-only. |
| **BONDS** | ❌ No verifiable edge | Research syntheses: all `NO_EDGE`/`MIXED` (n<20). TLT/IEF rotation backtest Tier‑3. |
| **ETF** | ❌ No edge | Closed n=10, PF 0.57 (net negative); sector-rotation backtest BELOW_T3. |
| CRYPTO (context) | Largest sample, positive but diluted | n=5164, WR 45.8%, PF 1.29, expectancy +0.41%. High-confidence *subset* edge is genuinely strong (see below). |
| FOREX | ❌ | Closed n=93, PF 0.42, WR 16.1%. |
| FUTURES | ❌ insufficient | n=1 closed; research all `NO_EDGE`. |

---

## 1. How the verdict was reached (multi-source convergence)

No single "winning class" claim survives all checks. The **strict promotion gate (A‑9)** is designed to stay empty until something genuinely clears it — and it is empty:

- `money_ready_verdict.json` (2026‑10‑22): **FOREX / CRYPTO = NOT_READY**, **COMMODITY = WATCH** (PF 1.03), everything else **INSUFFICIENT_DATA** (BOND n=0, ETF n=30, FUTURES n=48).
- `top_notch_money_ready.json`: **0/9 classes money-ready**.
- `dashboard_data.json` → `readiness.by_class`: all classes **BLOCKED** or **MONITORING**, `sizing_allowed=false` for all.
- `forward_candidate_scoreboard.json`: only **luxalgo_confluence/SHORT** is "real-edge (sub-bar)"; all others verdict `no-edge/mirage`.
- Agent P5 syntheses (2026‑10‑17) for bond / etf / futures / commodity / equity: every strategy flagged `NO_EDGE`/`MIXED` because backtest trade counts are far below the 100-trade floor (n=3–17). These agent reports **agree** with the strict gate, not contrary to it.

## 2. Which class is the *best candidate*? EQUITY.

Among the classes with non-trivial live closed data, **EQUITY is the only one with a healthy positive per-trade expectancy**:

- `performance.by_asset_class.EQUITY`: closed = 22, WR 45.5%, PF **11.91**, expectancy **+1.95%**, PnL +42.91%.
- **UEPS magic_formula book**: 22 open EQUITY positions (ADBE, QCOM, PYPL, HD, META, NFLX, GOOGL, MA, MDT, PEP, V, T, COST, LIN, TXN, IBM, PFE, JNJ, XOM, BMY, BA, TSLA), avg score 46.9, avg conf 0.58, unrealized +0.39%/pos.
- `top_notch_money_ready.json` EQUITY: PF 1.84 (n_clean=71), **GOOGL = 100% WR (n=17)**.
- Backtest corroboration (research): VIX-filtered 12‑1m equity momentum shows WR 75%, PF 5.37, Sharpe 2.19, MDD 7.3% (n=88 active months — strongest clean backtest in the repo).

**Caveats:** closed n=22 is small; avg_loss 0.33 is skewed by a couple of tight stops; the mean-reversion "PF 235" edge in `top_edges_per_class.json` is almost certainly the **frozen-exit artifact** class (same family as QUBT/IONQ/AAPL per `AUDIT_ACTIONS_GCOPILOT_OCT22.MD` C1/A‑3) — do not promote on it.

## 3. CRYPTO: biggest sample, positive, but diluted — with a real *subset* edge

- Headline (closed n=5164): WR 45.8%, PF 1.29, expectancy +0.41%.
- **Genuine high-confidence subset edge** (`top_edges_per_class.json`): `conf=0.75–0.80 & LONG & score_dec=S50 & source=alpha_engine` → **n=183, WR 76.4%, PF 4.71, holdout_pass, Bonferroni_pass**. This is the strongest *statistically vetted* live edge in the whole dataset — but it is a high-confidence slice, not the whole class.
- Active system worth tracking: **mega_mutation** (n=502, WR 60%, PF 2.49, +1021%, active, not stale).
- Dilution drivers: 3,563 resolved rows include many low-pf/placeholder strategies; several single-source "sleeves" show absurd PF (155×–111×) that are resolver artifacts, not real returns.

## 4. Hidden winners in the database / system (not surfaced on the web page)

These are masked inside aggregates and never called out on the audit surface — they are the closest thing to "hidden top performers":

1. **DOTUSDT** — drives **+282%** of `alpha_engine`'s total PnL (concentration warning in `system_clean_metrics`). Removing it flips alpha_engine from +22.1% to **−40.3%**. Single-symbol winner hidden inside a losing system.
2. **EURGBP=X** — 74.9% of `multi_asset_copytrader` PnL; that system is PF 3.24, Sharpe/trade 0.54, calmar 4.68 (n=20). Best clean per-system live performer.
3. **battleground** (crypto) — PF 1.76, +27.5%, n=122, calmar 3.76. Profitable, multi-trade, not highlighted.
4. **UEPS magic_formula** equity book — 22 open positions, all long-term value; the biggest *structured* equity deployment in the DB.
5. **cheap_stock_momentum** — backtest: WR 61.3%, PF 2.79, +995% (MDD 57% — high risk, research only).
6. **GOOGL / FETUSDT / TONUSDT / STRKUSDT** — top-notch symbols from `top_notch_money_ready.json` with WR 69–100% at respectable n (17–69).

## 5. Hidden pages on the audit site (present but not linked from index/template)

The audit surface (`index.html`/`template.html`) links ~37 pages; these files exist but are **orphans** (not linked from the main surface), so their content is effectively hidden:

`funds.html`, `mutual-funds.html`, `strategy_perf_by_class.html`, `summary.html`, `pf.html`, `model.html`, `research_sidecars.html`, `incidents.html`, `institutional_readiness_plan.html`, `edge_validation_roadmap.html`, `benchmark_proof.html`, `curated_picks_20260524.html`, `hedge_fund_simulation_20260524.html`, `simulation_full_report_20260524.html`, `localrun_eltonslaptop.html`, `kimi_top_picks_OLD.html`, `antigravity_picks.html`.

- **`strategy_perf_by_class.html`** and **`summary.html`** are the most likely to contain per-class performance details not surfaced on the dashboard.
- `funds.html` / `mutual-funds.html` are the mutual-fund/ETF-class pages — relevant to the ETF question.
- `updates/index.html` also points to `../../docs/zoocode-inception-combined-book-paper-trade.html` and `2026-10-19-combined-book-paper-trade-pilot.md` (multi-asset proxy ETF→MF book) — a hidden research thread.

## 6. Verification notes (data hygiene)

- **Artifacts present:** frozen-exit / sentinel rows (`999999.9999`, `0.0%` pnl placeholders) distort COMMODITY and single-source sleeves. The A‑3/A‑4/A‑5 actions in `AUDIT_ACTIONS_GCOPILOT_OCT22.MD` directly address these; until fixed, treat very-high PF cells as suspicious.
- **Concentration is the #1 hidden-risk driver** (DOTUSDT, EURGBP, ETHUSDT across systems).
- **`data_freshness`** and `db_health` should be checked before acting on any open-pick numbers; several leadership metrics are bucketed by 48h/14d/90d.

## 7. Recommendation (actionable)

1. **Debug the "winner" as EQUITY (stocks) — CANDIDATE, not MONEY‑READY.** Promote only after n≥100 clean closed; currently at n≈22.
2. **Wire the proven CRYPTO confidence-slice edge** (conf 0.75–0.80, LONG, score_dec S50) as an explicit sleeve rather than letting the diluted class headline hide it.
3. **Surface the hidden winners:** add a "concentration / top-symbol" callout for DOTUSDT, EURGBP=X, and battleground to the audit dashboard, and link the orphan pages (`strategy_perf_by_class.html`, `funds.html`, `mutual-funds.html`) from the main audit nav.
4. **Keep BONDS/ETF/FUTURES/FOREX un-promoted** (data insufficient or negative).
5. **Do not promote** on the mean-reversion PF=235 or any single-source 100× PF sleeve until the resolver artifact fix (A‑3) is verified.
6. Read the combined-book paper-trade thread (`updates/2026-10-19-combined-book-paper-trade-pilot.md`) — it is the only place with a *broad, multi-asset* reproducible book and may be the cleanest path to a diversified "winner".

*Not financial advice. Research/educational only. Past performance does not guarantee future results.*
