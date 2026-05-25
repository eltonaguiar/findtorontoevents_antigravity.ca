# Opencode Ring-2.6-1T Session Deep-Scan — Net-New Items

**Source:** `session-ses_1a2d.md` (22,048 lines, Ring-2.6-1T via opencode, 2026-05-12 → 2026-05-25)
**Reviewer:** Claude Opus 4.7 (1M)
**Date:** 2026-05-25
**Swarm verdict source:** `/tmp/swarm_session_review_20260525T034736/` (deepseek + cerebras + gemini, JSON-strict)
**Goal:** Surface action items NOT already in the 33 INCIDENTS / 19 ENHANCEMENTS captured by `tools/audit_pick_funnel/seed_incidents_enhancements.py`.

---

## Swarm consensus snapshot (12 candidate items, 3 engines)

| # | Candidate | deepseek | cerebras | gemini | Decision |
|---|---|---|---|---|---|
| 1 | IPO/lockup-expiry strategy missing entirely | REAL | NOISE | NOISE | ADD (genuine gap, see #N1) |
| 2 | Cherry-picked "Supreme Edge" stats on UI without caveat | REAL | REAL | REAL | ADD (#N2) |
| 3 | smart_picks_engine 35% weight on anti-predictive confidence-derived score | REAL | REAL | REAL | ADD (#N3) |
| 4 | ETF Faber-tactical / dual-momentum promotion candidates | NOISE | NOISE | NOISE | REJECT |
| 5 | FOREX SL=0.5% at median ATR | DUP | DUP | DUP | REJECT (already captured) |
| 6 | Yield-curve-momentum bond strategy | DUP | DUP | DUP | REJECT |
| 7 | Commodity term-structure roll-yield | DUP | DUP | DUP | REJECT |
| 8 | 206 baby_strategies orphan count | DUP | DUP | DUP | REJECT |
| 9 | summary_picks.json uniform last-pick timestamps (simulated?) | REAL | REAL | REAL | ADD (#N4) |
| 10 | ML crypto DSR≥0.9995 on n=25-34 surfaced w/o caveat | REAL | REAL | REAL | ADD (#N5) |
| 11 | Walk-forward validator tool (purge/embargo/CPCV) | NOISE | NOISE | NOISE | ADD as ENHANCEMENT (#N6 — tooling gap is real) |
| 12 | PEAD equity shadow-mode | DUP | DUP | DUP | REJECT |

**Triangulation rule:** 3/3 REAL = strong add; 2/3 REAL = add; 3/3 NOISE = reject unless I can argue otherwise. Item #1 added despite 2/3 NOISE because the project explicitly enumerates IPO as an asset class with zero coverage (Section 6 of Ring's summary, line 21622-23) — this is the same charter shape that drove the existing "skyrocket_detector not wired" / "penny_deep_oversold blocked" entries. Item #11 added as ENHANCEMENT (not INCIDENT) because tooling gaps belong in that table.

---

## ADD — 6 net-new items (ranked by user-protection value)

### N1 — INCIDENT — `OVERALL` — "Cherry-picked Supreme Edge stats surfaced on /audit without post-hoc-mining caveat"

```python
("OVERALL", "Cherry-picked 'Supreme Edge' segment stats surfaced on /audit without post-hoc-mining caveat",
 "top_edges_per_class.json is a post-hoc segment search across confidence x R:R x strategy-family buckets. The 82% WR / PF 13+ headline numbers it yields are NOT forward-actionable signals, yet they are presented on the main /audit page alongside live forward stats. Three independent reviewers (deepseek, cerebras, gemini) flagged this as a real production issue: it misleads users about real edge. Severity is elevated because the same dashboard banners say 'real money sizing' downstream.",
 "P0", "OPEN", "audit_dashboard/template.html (Supreme Edge banner) / audit_dashboard/data/top_edges_per_class.json",
 "Either (a) add a 'POST-HOC SEGMENT SEARCH - NOT A FORWARD SIGNAL' badge to every cell pulled from top_edges_per_class, or (b) require any displayed cell to also pass DSR>=0.95 with n>=100 in the SAME displayed segment. Cells failing the second test get hidden.",
 "reports/2026-05-25_opencode_session_deep_scan.md", "https://findtorontoevents.ca/audit/", None, "ring-2.6-1t+swarm3"),
```

### N2 — INCIDENT — `OVERALL` — "smart_picks_engine.py weights confidence-derived score at 35%, structurally inverting the ranker"

```python
("OVERALL", "smart_picks_engine.py weights confidence-derived elite/quality at 35%, structurally inverting the ranker",
 "The existing 'ML calibration system-wide inverted' incident covers the underlying calibration bug. This is the downstream consequence: the 5-factor Smart Picks composite places 35% weight on 'elite/quality' which is derived FROM confidence. Because confidence is anti-predictive (conf>=0.9 -> WR 14.4%), the ranker is structurally flipped at 35% influence, not just a misread on a sidecar. Fixing _normalize_confidence alone will NOT recover this until the weight is re-pointed at trust_score (which code comments already nominate).",
 "P0", "OPEN", "alpha_engine/smart_picks_engine.py (5-factor composite weights)",
 "Re-point the 35% 'elite/quality' weight at trust_score for crypto (and validate per-class). Backtest the swap on 90d closed picks; if median Smart Picks WR lifts >=3pp, ship. Linked to the trust_score-backfill enhancement (must land first or weight has nothing to read).",
 "reports/2026-05-25_opencode_session_deep_scan.md", None, None, "ring-2.6-1t+swarm3"),
```

### N3 — INCIDENT — `CRYPTO` — "ML crypto DSR>=0.9995 strategies surfaced on /audit at n=25-34 without insufficient-sample warning"

```python
("CRYPTO", "ML crypto DSR>=0.9995 strategies surfaced on /audit at n=25-34 without insufficient-sample warning",
 "Four crypto ML strategies (INJ 1d, DYDX 15m, FET 1d, RENDER 1h) display DSR>=0.9995 on the anti_overfit.html page. Sample sizes are 25-34 trades. DSR is misleadingly high in micro-samples due to low variance over short windows; the Bailey-Lopez de Prado >=0.95 'publishable confidence' bar implicitly assumes adequate n. The UI does not gate on n, so these strategies appear co-equal to cot_positioning (n=104).",
 "P1", "OPEN", "audit_dashboard/anti_overfit.html / tools/anti_overfit_audit_sidecar.py",
 "Add an 'INSUFFICIENT N' badge for rows where n<60 regardless of DSR. Document the small-sample DSR caveat in the page header. Optionally re-rank: a strategy must clear DSR>=0.95 AND n>=60 to be eligible for the 'EDGE_LIKELY_REAL' verdict.",
 "reports/2026-05-25_opencode_session_deep_scan.md", "https://findtorontoevents.ca/audit/anti_overfit.html", None, "ring-2.6-1t+swarm3"),
```

### N4 — INCIDENT — `OVERALL` — "summary_picks.json shows identical last_pick timestamps across all asset classes"

```python
("OVERALL", "summary_picks.json shows identical last_pick timestamps across all asset classes (auto-generated/simulated suspicion)",
 "Ring observed every asset class in summary_picks.json showing last pick timestamp of 2026-05-24T11:00:00Z — exactly identical across CRYPTO/EQUITY/FOREX/COMMODITY/BOND/ETF/FUTURES. Real per-class scanners would produce divergent timestamps. The shape looks like a simulated/auto-filled fixture, not live per-class telemetry. This is independent from the smart_picks.json staleness incident.",
 "P1", "OPEN", "audit_dashboard/data/summary_picks.json / dashboard_generator builder for summary_picks",
 "Audit the builder. Either (a) populate last_pick_at per class from a per-class MAX(created_at) on trading_picks, or (b) remove the field if it isn't actually being computed. Add a unit test asserting timestamps vary by >=1 minute across classes on real data.",
 "reports/2026-05-25_opencode_session_deep_scan.md", None, None, "ring-2.6-1t+swarm3"),
```

### N5 — INCIDENT — `STOCKS` — "IPO asset class has zero strategy coverage in alpha_engine/strategies/"

```python
("STOCKS", "IPO asset class has zero strategy coverage in alpha_engine/strategies/",
 "Ring's per-class inventory found zero IPO-specific strategies (post-IPO lockup-expiry, insider-selling reversal, revenue-trajectory). The existing PEAD framework could be adapted with minor changes. This is a charter gap analogous to the documented penny-stock gap. Swarm split 1-REAL / 2-NOISE; flagged as INCIDENT not ENHANCEMENT because /audit advertises IPOs as a tracked asset class (tab exists in the UI) but no scanner ever fires.",
 "P2", "OPEN", "alpha_engine/strategies/ (no ipo_*.py file) / production_scanner.py (no _run_ipo_scanner)",
 "Build alpha_engine/strategies/ipo_lockup_expiry.py forking pead_equity.py. Trigger universe: IPOs 150-200 days post-listing (lockup-expiry window). Signal: insider-selling acceleration + revenue-growth deceleration -> SHORT bias. Wire into production_scanner under a STOCKS asset_class branch.",
 "reports/2026-05-25_opencode_session_deep_scan.md", None, None, "ring-2.6-1t"),
```

### N6 — ENHANCEMENT — `OVERALL` — "Ship tools/wf_validator.py (purged walk-forward with embargo + CPCV)"

```python
("OVERALL", "Ship tools/wf_validator.py (purged walk-forward with embargo + CPCV)",
 "Ring's quant-workflow review (session lines 21985-22041) specified a concrete WF framework: 500d train / 126d test / purge=30d / embargo=5d / >=8 folds / FDR-corrected p-values / block-bootstrap stress. The repo has anti_overfit_audit_sidecar.py (DSR) but no systematic WF runner. Without WF, the COT 7-step plan and PEAD promotion paths require ad-hoc validation. Shipping this tool unblocks the entire 10-step readiness gate (CLAUDE.md #3-#4).",
 "TOOLING", "HIGH", "L", "BACKLOG", "ring-2.6-1t", None,
 "tools/wf_validator.py runs end-to-end on cot_positioning + pead_equity within 90s, produces per-fold Sharpe/MDD/WR + bootstrap CI, and is invoked from audit-dashboard.yml hourly cron.",
 "reports/2026-05-25_opencode_session_deep_scan.md", None, None),
```

---

## REJECTED candidates (with one-line rationale)

| Item | Why rejected |
|---|---|
| FOREX SL=0.5% at median ATR | Already captured: "FOREX: SL at 0.5% sits at median FX ATR" incident. |
| Yield-curve-momentum bond strategy | Already captured: "yield-curve-momentum (TLT/IEF) + wire bond_scanner.py" enhancement. |
| Commodity term-structure roll-yield | Already captured: "commodity term-structure roll-yield" enhancement. |
| 206 baby_strategies orphan-count | Adds only file-count evidence to existing "batch-DSR baby_strategies" enhancement; not a new row. |
| PEAD equity shadow mode | Already captured. |
| ETF Faber-tactical / dual_momentum promotion notes | Probation-monitoring detail, not actionable until n>=50; covered by existing "5 ETF strategies on probation" incident. |
| US Equity screener zero picks | Already captured. |
| Top-N Rank Backtest broken | RESOLVED (commits 702eac27 + c5fcbdc1). |
| Confidence inversion (calibration root cause) | Already captured; N2 above is the downstream-weight consequence, distinct. |
| Forex_carry.py not in allowlist | Already captured enhancement. |
| COT over-emission | Already captured. |
| signal_outcomes 82-day stale | Already captured. |
| ghost rows / WON-vs-PnL | Already captured. |
| Confidence-extremes blocked gate | Mechanical reading of hc_filter.js, already implicit in HC incident. |
| Trust-tier blacklist (SANDBOX/UNPROVEN/PROBATION/DEMOTED) | Documented behavior, not an issue. |
| Hand-derived risk-budget pitfalls (10-item table) | Educational content from Ring's analysis; doesn't map to a single executable action. |
| Concrete momentum+macro pseudo-code | Reference architecture, not an incident. |
| Faber TAA academic citation | Marketing fodder, not a tracked item. |

---

## Notes for inspector

- Items N1, N2, N3 are the highest-trust additions (full 3/3 swarm REAL consensus + independently corroborated in seed-script peer reviews).
- N4 (uniform timestamps) is concrete enough to write a one-line SQL probe to confirm before adding: `SELECT category, MAX(created_at) FROM trading_picks GROUP BY category;` — if the spread is >1 minute, this is a builder bug, not real data drift.
- N5 (IPO gap) is the lowest-confidence add. Reasonable to defer until a real user request lands; flagged P2 for that reason.
- N6 (WF validator) is the only ENHANCEMENT add; everything else is INCIDENT.
- All 6 items cite `reports/2026-05-25_opencode_session_deep_scan.md` so the audit trail from seed-script row -> evidence -> session source is one click.

End — 6 ADD / 18+ REJECT / report under 250 lines as requested.
