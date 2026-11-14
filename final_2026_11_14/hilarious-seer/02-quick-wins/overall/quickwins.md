# Overall + DB Quick Wins (merged v4/v3 peers)
- 0/9 classes money-ready (all FAIL: crypto 3 stale SHORTs PF 0.37-0.92, equity -5.22% PnL, forex frozen +0.04% vs 0%, commodity marginal, ETF/bond/FUTURES insufficient n/ghosts 22k+). Root: frozen prices (false 0% PnL), divergent DBs (empty audit_trail, 254d resolver, 26d dashboard), inverted ML conf, no fwd overlap, 0/26 horizon pass.
- P0 merges: gatekeeper leakage mask (confirmed fixed), universal_pick_resolver + price_sync for live Binance/Yahoo, dedup ghosts/TIME_EXIT, harmonize SQLite/MySQL/JSON, Bonferroni/MC null/intrabar/n>=200 gates in validators.
- DB/freshness: extend guardian + cross_db_consistency; revive alpha-engine-live.yml heartbeat.
Proposed: surgical P0 to resolver/gatekeeper/dashboard_generator/active_picks_sync (no capital till 90d paper PF>1.5 post-costs). Our quickwins now unified.
