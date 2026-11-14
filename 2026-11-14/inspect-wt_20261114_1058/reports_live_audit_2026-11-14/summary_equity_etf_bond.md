# EQUITY / ETF / BOND (+ mutual funds) — summary (live data, 2026-11-14 ~15:45Z)

Sources: `live_dashboard_payload.json` (.picks.active_raw EQUITY n=182, ETF n=38, BOND n=15; .picks.recent_closed EQUITY n=738, ETF n=567, BOND n=35), `live_money_ready.json`, `live_pf_registry.json`, `live_stock_prices.json`, `live_audit_surface_truth.json`.

**VERDICT: FAIL for bonds (effectively dead), MIXED-to-FAIL for equity/ETF (contradictory official stats; EQUITY is the only class with any positive recent window but n is tiny and surfaces disagree).**

## Evidence

1. **BOND is dead-but-displayed.** active_raw n=15, ALL 25–26h old (daily emission, not hourly). recent_closed n=35 with newest 98h (4.1 days) — confirms user's "bonds picks were 4 days ago". money_ready: n=1 resolved (WR 0, PF 0), intrabar n=26 (WR 7.7%, PF 0.39). Registry n=2. There is no functioning bond prediction system — there is a daily cron emitting picks that almost never resolve.
2. **ETF surfaces flatly contradict each other:** money_ready intrabar (n=45): **WR 2.2%, PF 0.0216** — nearly every ETF trade lost. Registry canonical (n=15): **WR 73.3%, PF 1.84**. My 14d recompute (n=37): WR 37.8%, PF 0.928. Same class, same day, three official numbers ranging from disaster to gold — sample windows and dedup filters are being chosen per surface, not reconciled.
3. **EQUITY:** money_ready intrabar (n=250): WR 59.2%, PF 0.9392, pf_ok=False, dsr_ok=True. Registry (n=493): WR 42.4%, PF 0.7068. My 14d recompute (n=42): WR 50%, PF 1.172, Σ +19.5%. The only class where any official surface (dsr_ok) passes a gate, yet its long-horizon registry PF is 0.71. June's money_ready had EQUITY pf_ok=True (PF 1.84) — by Nov that flipped False. The "best" class is not stable across months.
4. **Zombies in equity/ETF:** active_raw oldest rows ~5,416h (225 days) EXPIRED pnl=0 (`signal_validation`, `stocks_competition` etc.); `.picks.active` panel shows only fresh rows (2.8–3.6h), so the visible panel is curated while the raw feed rots.
5. **FWD WR / FWD N field check:** populated fields exist (forward_wr/forward_trades/strat_fwd_wr/strat_fwd_trades present in payload schema), but on many OPEN rows current_price=None means forward marks cannot update — the metric can be alive per row-set but frozen per pick. Exact per-class breakdown: `evidence_live_audit.json` (n_open_no_current_price).
6. **Stock price feed:** `live_stock_prices.json` generated 2026-11-14T14:13 (1.6h) — the underlying quotes are fresh; staleness is in pick resolution, not the price feed.
7. **Mutual funds:** searched live payloads/registries for mutual_fund, mf_, VTSAX/VBTLX/VFINX — **no live mutual-fund picks exist**. The class exists as DB strategy families and a planned-but-unbuilt ranker (`alpha_engine/mutual_fund_ranker.py` does not exist). Mutual-fund prediction is vaporware on the live page.

## What is real
- Hourly equity/ETF emission and a fresh price feed.
- EQUITY 14d window (+19.5% on n=42) — positive but statistically weak (n=42, one window).
