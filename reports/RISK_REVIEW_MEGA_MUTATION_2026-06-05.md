# Risk Review — `mega_mutation` Bridge Candidate (2026-06-05)

**Skill applied:** [`prediction-market-risk-review`](../.claude/skills/prediction-market-risk-review/SKILL.md) (newly integrated from `affaan-m/ecc`).
**Subject:** `mega_mutation` CRYPTO multi-symbol sleeve, post-INCIDENT-#91 dedup (n=109, WR 61.5%, PF 2.79, OOS-stable). Forward pilot wired at `verified_strategies/paper_pilot/mega_mutation_forward_pilot.py`, `production_enable=false`.
**Reviewer:** Claude (this session) — for the multi-AI fleet record.

---

## 1. Scope reviewed

- Strategy: `mega_mutation` (8 crypto altcoins: JUP, WIF, AVAX, DOT, RENDER, STX, ENA, ADA)
- Data sources: `ejaguiar1_stocks.trading_picks` (live forward closes), dedup via composite key per `tools/trading_picks_dedup_incident_91.py`
- Execution surface: forward-paper-only via `tools/run_verified_pilots_daily.py`; `PROMOTED_STRATEGIES` frozenset still empty; no live wallet/exchange auth in the pilot path
- Reporting surface: `audit_dashboard/data/`, FTP-deployed to `findtorontoevents.ca/audit`

## 2. Per-gate findings

| Gate | Verdict | Evidence |
|---|---|---|
| **Advice Boundary** | **PASS** | All output is informational/analytical (audit dashboard, reports). No buy/sell/hold/size recommendation surfaces to anyone yet. `production_enable=false` hard-coded in the pilot. |
| **Venue / Regulatory** | **WARN** | Alt-heavy basket — JUP/WIF/RENDER/STX/ENA are not all listable on US-regulated venues; AVAX/DOT/ADA are. Memecoin-adjacent assets (WIF, ENA) carry venue + jurisdiction ambiguity. |
| **Data Quality** | **WARN** | Three live data-quality flags: (a) resolver uses 1h klines, not intrabar — TP_HIT/SL_HIT order is undefined on whipsaw bars (see memory `sl-optimization-needs-pricepath`); (b) the lab baseline of n=109 is post-dedup from 296 raw rows (2.72× inflation factor was real INCIDENT #91 pattern, confirmed via 4× identical JUP rows on 2026-05-26); (c) one of the cohort assets (RENDERUSDT) has separate-strategy ban under Kimi's strategy_kill_switch.py for 1h/4h variants — overlap risk. |
| **Security** | **PASS** | No wallet keys in this code path. DB creds resolve through `tools.db_env.get_stocks_creds()` (env-var first, no hardcoded passwords after `fab668aee5`). Pilot script is read-only against `trading_picks`. |
| **Privacy** | **PASS** | All data is in user's own MySQL. No third-party PII. Public-facing `/audit` surfaces aggregate stats only, no row-level personally-identifying info. |

## 3. Blocked actions

Until forward n≥100 AND mitigations 1, 2, 4 below are addressed:

- ❌ No `PROMOTED_STRATEGIES` insertion of `mega_mutation`
- ❌ No live sizing on any signal from this strategy
- ❌ No flip of `production_enable` to true
- ❌ No public claim of "verified Tier-2" on `/audit/incidents.html` or `updates/index.html` — only "WATCH" allowed

## 4. Required mitigations (priority-ordered)

1. **Intrabar resolver verification (P0)** — replay the 109 deduped closes with 1m OHLC and re-tag TP_HIT vs SL_HIT vs TIME_EXIT. If the WR/PF post-replay drops by > 10% in PF, treat the lab numbers as upper-bound only. Owner action: extend `audit_trail/universal_pick_resolver.py` for `mega_mutation` cohort.
2. **Venue accessibility map (P1)** — emit a CSV: `symbol, available_on_binance_us, available_on_kraken, available_on_coinbase, avg_daily_volume_30d_usd`. Block any symbol with ADV < $5M from the sizing rotation.
3. **Concentration cap inside the sleeve (P1)** — even though no single symbol exceeds 15.9% of the n=109 cohort, the trade-level Kelly per pick should cap any single-symbol open exposure at 25% of sleeve allocation. JUP at 15.9% is the natural max.
4. **Circuit breaker (P1)** — rolling-7d drawdown > 15% on the live forward pilot must pause emission. Forward pilot script does not yet implement this; add to `mega_mutation_forward_pilot.py`.
5. **Pre-trade slippage simulation (P2)** — when the time comes to size, simulate each pick against book depth before submit. Not blocking until live-sizing decision.

## 5. Safe next step

1. Keep the daily forward pilot running with `production_enable=false`. **No change to operator's current path.**
2. Build the intrabar resolver patch (#1 above) and re-run the dedup + scrutiny on the post-replay numbers — that gives a true lab→forward translation factor, which is the single highest-information signal we can produce before n=100.
3. Re-apply this risk review at n=30 forward (~3-4 weeks given current cadence). If WR drops below 50% or PF below 1.5 on the live-forward slice, kill the sleeve before n=100.

---

## Cross-AI corroboration matrix (running tally for this candidate)

| Reviewer | Verdict | Headline |
|---|---|---|
| This Claude (initial) | T2 candidate | reports/MEGA_MUTATION_BRIDGE_CANDIDATE_2026-06-05.md |
| Parallel Claude (live-forward dig) | Survives strict filter | n≥100, WR≥50%, PF≥1.5, dates≥30, avg≥+0.3%, no fat-tail — all pass |
| Other Claude (negative_knowledge_registry) | Unblocked from BLOCKED_STRATEGY_SYSTEMS | commit 9c5bc6ec4e — old kill was stale n=7/WR=14.3% entry |
| **This risk-review** | **WATCH (2× WARN, 3× PASS)** | Mitigations 1-4 required before promotion; pilot stays paper |
| MiniMax M3 (peer-review) | Not yet returned (Ollama Cloud auth issue) | `/consult-minimax` skill shipped — operator may need `ollama signin` |
| DeepSeek (independent on other candidates) | Corroborated 5/11 VRP refutation axes 2026-06-04 | Confirms cross-AI skeptic pattern works |

---

Filed by `/loop` blitz at 2026-06-05 ~06:55Z. Skill source: `affaan-m/ecc` → `.claude/skills/prediction-market-risk-review/`.
