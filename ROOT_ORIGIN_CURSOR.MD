# ROOT origin map — top strategies, closed vs unrealized, audit feed health

**Generated:** 2026-03-28 (Cursor analysis of repo + `audit_trail/data/dashboard_payload.json`)  
**Enhanced:** 2026-03-28 — **Mercury 2** review: risk/opportunity matrix, owner roadmap, health scripts (manifest + payload), schema corrections, **§K** metric toolkit, and **§L** four-pillar **playbook** (scorecard, architecture, governance, innovation, 3-week sprint).

## What “ROOT origin” means here

In this codebase, a strategy’s **ROOT** is the set of upstream **`source_system`** labels attached to picks, plus **synthetic tags** the audit generator adds when it merges auxiliary feeds.

- **Primary ROOT:** `pick["source_system"]` from each JSON pick file (see `JSON_PICK_SOURCES` in `audit_trail/dashboard_generator.py`). Examples: `alpha_engine`, `ml_crypto_pred`, `copy_trader_intel`, `super_signals`.
- **Leaderboard `systems` field:** built in `collect_strategy_leaderboard()` by unioning `source_system` on **closed** picks, then adding tags such as `baby_strats_forward`, `kimi_competition`, `coinglass`, `backtest_arena` when data comes from baby-strats JSON, KIMI competition JSON, SQLite, or backtest rankings—not only from raw pick files.
- **Unrealized PnL:** summed in `collect_system_stats()` per **`source_system`** (payload `systems[].unrealized_pnl_pct`). Per-strategy unrealized is **not** a first-class leaderboard column; below we aggregate it from `picks.active` for interpretation.

**Caveat:** Leaderboard default sort is **forward win rate**, not cumulative PnL. Rankings below are recomputed by **closed forward `fwd_total_pnl`** (from resolved picks).

---

## A. Top strategies by **closed** forward PnL (`fwd_total_pnl`)

Minimum **10** closed trades, sorted by `fwd_total_pnl` (snapshot: local `dashboard_payload.json`).

| Strategy | fwd_total_pnl % | fwd WR | trades | ROOT (`leaderboard.systems`) |
|----------|-----------------|--------|--------|--------------------------------|
| `ml_crypto_predictor` | 2611.43 | 58.2% | 1328 | `ml_crypto_predictor` |
| `st_fear_greed_contrarian` | 513.61 | 52.0% | 1172 | `aggregated_picks`, `claude_gainer_st` |
| `copy_hl_lb_None` | 399.0 | 60.0% | 10 | `alpha_engine`, `copy_trader_intel` |
| `st_rsi_momentum_confluence` | 127.86 | 60.1% | 291 | `aggregated_picks`, `claude_gainer_st` |
| `strong consensus (alpha_engine, ml_crypto_pred)` | 86.27 | 34.2% | 79 | `super_signals` |
| `claude_gainer_4h` | 80.21 | 56.2% | 32 | `claude_gainer` |
| `quan_engine_swing` | 77.43 | 38.5% | 78 | `alpha_engine` |
| `Trend Following` | 68.74 | 54.1% | 37 | `stocks_competition` |
| `enhanced_ml_A_xgboost` | 61.94 | 67.4% | 43 | `ml_crypto_pred` |
| `keltner_compression_expansion_eth_v1` | 58.05 | 58.0% | 81 | `baby_strats_forward`, `battleground`, `codex_gpt5` |
| `ensemble` | 55.81 | 47.4% | 78 | `mercury2` |
| `ml_crypto_pred` | 51.05 | 31.4% | 35 | `ml_crypto_pred` |
| `keltner_compression_expansion_xrp_v1` | 48.46 | 60.9% | 68 | `baby_strats_forward`, `battleground`, `codex_gpt5` |
| `Classic Momentum` | 45.79 | 50.0% | 14 | `stocks_competition` |
| `crypto_keltner_compression_expansion_v1` | 42.51 | 67.3% | 104 | `baby_strats_forward`, `battleground`, `codex_gpt5` |

**Interpretation:** The largest closed PnL stack is **ML crypto predictor** streams (`ml_crypto_predictor` / `ml_crypto_pred`). **Short-term Claude gainer** strategies show up both under `claude_gainer_st` and via **aggregated** pick labels. **Keltner** family strategies trace to **baby strats + battleground** (and `codex_gpt5` metadata). **Super-signals** consensus rows are rooted in `super_signals`.

---

## B. Top **systems** by closed `total_pnl_pct` and current **unrealized**

From payload `systems[]` (same snapshot).

**Closed PnL leaders:** `ml_crypto_predictor`, `claude_gainer_st`, `baby_strats_forward` (synthetic aggregation from baby-strat forward metrics), `copy_trader_intel`, `predictions`, `ml_crypto_pred`, `revival_all`, `battleground`, `mercury2`, `signal_validation`, `chatgpt_combined`, `super_signals`, …

**Unrealized leaders (open-book stress):**

| System | unrealized_pnl_pct (sum on opens) | active_picks |
|--------|-----------------------------------|--------------|
| `contrarian_consensus` | +47.83 | 31 |
| `incubator_gainer` | +7.68 | 4 |
| `alpha_engine` | +4.34 | 26 |
| `kimi_riseoftheclaw` | +3.79 | 14 |
| `inverse_mutations` | +2.89 | 6 |
| `short_engine` | +2.84 | 5 |
| `top_gainer_predictor` | +2.41 | 6 |
| `claude_gainer_st` | +1.39 | 1 |

**Largest negative unrealized (selected):** `super_signals`, `aggregated_picks`, `ml_crypto_pred`, `kimi_live_signals`, `riseoftheclaw`, `goldmine_stocks`, `rocket_scanner`, etc. (full list is in payload `systems`.)

---

## C. Top **strategies** by **unrealized** (aggregated from `picks.active`)

Sum of `unrealized_pnl_pct` (capped ±500% per pick like the generator) grouped by `strategy`:

| Strategy | Σ unrealized % | Open count | ROOT (`source_system` on actives) |
|----------|----------------|------------|-----------------------------------|
| `winner_pattern_precursor_inverse` | 316.12 | 39 | `inverse_mutations` |
| `contrarian_liquidity_grab` | 181.78 | 52 | `contrarian_consensus` |
| `incubator_gainer_composite` | 7.66 | 9 | `incubator_gainer` |
| `super signal (super) via alpha_engine` | 6.45 | 2 | `super_signals` |
| `quality-minus-junk` / `rs-breakout-scout` | ~4.37 | 3 each | `kimi_riseoftheclaw` |
| `volume-anomaly-scout` | 2.96 | 2 | `kimi_riseoftheclaw`, `riseoftheclaw` |
| `orderbook-imbalance` | 2.37 | 3 | `kimi_live_signals`, `kimi_riseoftheclaw`, `riseoftheclaw` |
| Several `strong consensus …` / `super signal …` | small positive | 1–2 | `super_signals` |

**Most negative Σ unrealized (examples):** `maplestax_vwap_cbc_flip` (`alpha_engine`), `goldmine_*_consensus` (`goldmine_unified`), `top_gainer_predictor`, `flash-crash-reversal`, `enhanced_ml_A_xgboost`.

---

## D. How dashboards feed **findtorontoevents.ca/audit**

### Canonical integration path

1. **Generator:** `python -m audit_trail.dashboard_generator` merges **~130** registered systems from `JSON_PICK_SOURCES` (and special loaders: stocks competitions, PM consensus, etc.), resolves picks, enriches prices, and writes:
   - `audit_trail/data/dashboard_payload.json` — full payload
   - `audit_dashboard/data/dashboard_data.json` — same JSON (external file for size / merges)
   - `audit_dashboard/index.html` — `template.html` with embedded `window.DASHBOARD_DATA`
2. **CI:** `.github/workflows/audit-dashboard.yml` runs hourly: merge scripts → `universal_pick_resolver` → `dashboard_generator` → commit → **FTP** to `findtorontoevents.ca/audit/` (`index.html`, `dashboard_enhancements.js`, `funds.html`, `audit/data/*.json` including **`dashboard_data.json` + `dashboard_payload.json`**, plus `stock_prices.json`).
3. **Browser:** `template.html` loads **`data/dashboard_data.json`** first, then may refresh from **GitHub raw** `dashboard_data.json` if newer than embedded data (`tryFetchFreshData`).

So **anything listed in `JSON_PICK_SOURCES` (or a special handler in `dashboard_generator.py`)** is intended to feed `/audit`. The live page is the **unified** view; standalone HTML dashboards are **not** automatically the source of truth unless their JSON outputs are on that ingest list.

### Standalone dashboards (same repo, **not** the same runtime as `/audit`)

These UIs read their own paths or APIs; they only affect `/audit` **if** their exported JSON is consumed by the generator on disk:

| Area | Typical entry | Feed relationship |
|------|---------------|-------------------|
| Unified audit | `/audit/` / `audit_dashboard/index.html` | **Sink** — main hub |
| Genome Darwin UI | `genome/dashboard/index.html` | Reads `genome/data/*.json` locally; **Darwin portfolio summary** (`darwin_portfolios.json`) is used by `alpha_engine/audit_sync.py` for MySQL but is **not** referenced in `JSON_PICK_SOURCES` |
| Alpha live HTML | `alpha_engine/live_dashboard.html` | Local / separate; overlaps `alpha_engine/data/*` which **are** ingested |
| Multi-asset | `multi_asset/dashboard.html` | Parallel UI; `multi_asset` **is** in `JSON_PICK_SOURCES` |
| KIMI | `KIMI_RISEOFTHECLAW/dashboard*.html` | Parallel UI; several `kimi_*` / `riseoftheclaw` sources **are** ingested |
| Trading / Asterdex | `trading/dashboard.html`, `asterdex_paper/dashboard.html` | `asterdex_paper` has one ingest path to `trading/data/dashboard_data.json` |
| Index page | `investments/all-dashboards.html` | Link hub only (deployed beside audit) |

### Gaps / “why isn’t X on audit?”

1. **`/audit_dashboard/` vs `/audit/`:** FTP deploy mirrors **both** on findtorontoevents (see `tools/deploy_to_ftp.py` `deploy_audit_dashboard`). The **hourly Action** deploys the **primary** tree under **`/audit/`**. Bookmarks to `/audit_dashboard/` can lag if only `/audit/` is updated—same files are intended to be mirrored, but manual partial deploys can desync.
2. **Manual `deploy_to_ftp.py` audit-only mode** uploads only `index.html`, `dashboard_enhancements.js`, `template.html` — **not** `audit/data/*.json`. Stale JSON on the server while HTML is new → “empty or old data” until the hourly job or full data upload runs.
3. **Darwin portfolio tracker:** `genome/data/darwin_portfolios.json` is **not** wired into `dashboard_generator.py` (no `darwin` in that module). Evolution families show in **genome dashboard** and DB sync, not in the unified payload unless picks also exist in another ingested file.
4. **Systems with `closed_path: None`:** Many genome / revival / challenge rows **never contribute closed history** to the audit merge unless `universal_resolved_picks` or another resolver backfills them—they still appear as **active** systems with low/zero closed stats.
5. **`funds.html`** tries multiple URLs for `dashboard_payload.json` (including raw GitHub); if on-site `audit/data` is missing or blocked, fallback paths determine what you see.

---

## E. Quick health checklist for “everything feeds audit”

- [ ] Pick JSON writers update paths under `JSON_PICK_SOURCES`.
- [ ] Hourly **Unified Audit Dashboard** workflow green (push + FTP).
- [ ] On server: `https://findtorontoevents.ca/audit/data/dashboard_data.json` and `dashboard_payload.json` timestamps match recent `generated_at`.
- [ ] After **manual** deploy, confirm data files uploaded—not only HTML.

---

## F. Mercury 2 — key takeaways (data-linked)

Cross-wired to sections **A–C**. These are **operational hypotheses** from review; validate against live payload and logs before trading decisions.

| Area | What the data suggests | Why it matters | Immediate actions |
|------|------------------------|----------------|---------------------|
| **Closed-PnL concentration** | `ml_crypto_predictor` dominates closed forward PnL in our snapshot (see §A; Mercury: “>70% of total closed profit” as a **portfolio-level** concern). | Single-model / single-pipeline dominance raises **regime-shift** risk. | Add a **model-diversity score** (e.g. % of closed PnL from top 3 `source_system` roots). Consider a **soft cap** on reported contribution (e.g. flag when one root exceeds a threshold) and rebalance research priority. |
| **Unrealized hotspots** | `winner_pattern_precursor_inverse` (Σ unrealized +316%, 39 opens, ROOT `inverse_mutations`) and `contrarian_liquidity_grab` (+182%, 52 opens, ROOT `contrarian_consensus`) — §C. | Large open % on **low-cap alts** → slippage, liquidity, gap risk; upside can reverse fast. | Per-asset **exposure limits** (e.g. ≤5% notional per symbol in risk docs). **Dynamic trailing stops** that tighten when volatility (e.g. ATR) > 2× rolling average. |
| **Feed health gaps** | Mercury flags **missing or sparse** feeds: `claws_of_doom`, `copy_trader_intel`, `breakout_*`, `rl_agent`, `quantum_fusion`; **DNA/Genome** only partially rolled up in reporting. | Skewed **coverage** and **metrics**; “connected systems” can look healthier than signal reality. | Audit **`hub/data/systems_manifest.json`** `data_endpoints` URLs (GitHub raw paths) for branch/commit drift. Add **staleness checks** on JSON `generated_at` / file mtime (see §H script). Optionally **RETIRED** status for dead scanners (see §G). |
| **Copy-trader pipeline** | `copy_hl_lb_None` shows high closed PnL with **few** trades in §A; Mercury: possible **ingestion gaps** or **schema drift** after refactors. | Small-N stats + broken feed → misleading confidence; leverage assumptions may be wrong. | **Unit tests** for `copy_trader_intel` exporters (schema + timestamps). **Structured logging** per signal (source ID, trader ID, ingest time). **Max leverage cap** policy for copy-derived sizing (e.g. 5×) enforced in downstream sizer. |
| **ML drift** | `ml_crypto_predictor` profit without visible drift monitors in-repo. | Silent **decay** when feature distributions or labels shift. | Weekly **feature distribution** snapshots; **shadow model** on last 30d; optional **KL**-based alert threshold (e.g. >0.2) to trigger retrain review — implement in `ml_crypto_predictor` training pipeline. |
| **Legacy system noise** | `breakout_a` / `breakout_b` / `breakout_c` (and similar) still registered in `JSON_PICK_SOURCES` with **empty or stale** data — inflates “total systems”. | Confuses **health** dashboards and on-call triage. | Mark **RETIRED** in manifest; **remove or gate** in `JSON_PICK_SOURCES` / generator enum; archive code per team policy. |
| **Observability** | Many moving parts (CI, FTP, raw GitHub, local JSON). | No **single pane** → slow incident response. | Lightweight **feed health** job (cron / GH Action) + Slack/Discord webhook on MISSING/STALE; long-term Grafana/Prometheus if ops standardizes. |
| **Documentation** | ROOT taxonomy split across `dashboard_generator.py`, manifest, Discord routing. | Onboarding duplicates work and mis-tags strategies. | **Strategy Origin Handbook** (one-pager: ROOT → path → latency → risk). Inline comments on **ingestion** for each `source_system`. |

---

## F2. Mercury 2 — risk & opportunity matrix (refined)

Combined **top closed-PnL strategies** (§A snapshot) and **top unrealized** (§C / §B). *Active picks* for closed-only rows are **0** in that snapshot (strategy row); unrealized rows use **open count** from §C.

| # | Strategy / system | Closed PnL % (fwd) | Win-rate | Active / opens | ROOT / source-system(s) | Primary risk | Quick-win mitigation |
|---|-------------------|-------------------|----------|----------------|-------------------------|--------------|----------------------|
| 1 | `ml_crypto_predictor` | 2611% | 58% | 0 | `ml_crypto_predictor` | Regime / single-pipeline dependence | Model-diversity cap (e.g. ≤40% of *attributed* closed PnL); weekly drift alerts (§H2 / §I2). |
| 2 | `st_fear_greed_contrarian` | 514% | 52% | 0 | `aggregated_picks`, `claude_gainer_st` | Stale sentiment in low-vol | Min **24h volume** filter (e.g. ≥5M USD notional). |
| 3 | `copy_hl_lb_None` | 399% | 60% | 0 | `alpha_engine`, `copy_trader_intel` | **Small-N** closed + fragile copy feed | Fix ingestion + tests; **5×** leverage cap policy; log every signal. |
| 4 | `st_rsi_momentum_confluence` | 128% | 60% | 0 | `aggregated_picks`, `claude_gainer_st` | Same stack as #2 | Add **volatility** gate (e.g. ATR% > threshold). |
| 5 | `winner_pattern_precursor_inverse` *(unrealized)* | — | — | 39 | `inverse_mutations` | Low-cap **liquidity / slippage** | Max **5%** capital per asset; ATR-based trailing stop. |
| 6 | `contrarian_liquidity_grab` *(unrealized)* | — | — | 52 | `contrarian_consensus` | Turnover + concentration | Same as #5. |
| 7 | `claude_gainer_4h` | 80% | 56% | 0 | `claude_gainer` | Short-horizon noise | Min **hold** before discretionary exit (e.g. 2h) if policy allows. |
| 8 | `keltner_compression_expansion_*` *(eth/xrp/v1)* | 48–58% | 58–61% | 0 | `baby_strats_forward`, `battleground`, `codex_gpt5` | **Synthetic multi-tags** → double-count confusion in narratives | Single **baby_strats** rollup ID in UI + docs. |
| 9 | `strong consensus (alpha_engine, ml_crypto_pred)` | 86% | 34% | 0 | `super_signals` | Low WR, dual dependency | Min WR / min trades before promotion; consensus quality gate. |
| 10 | `incubator_gainer_composite` *(unrealized)* | +7.7% Σ | — | 9 | `incubator_gainer` | Small sample | Require **≥20** closed trades before “official” reporting tier. |

### Bottom-line risk themes (Mercury 2)

- **Model concentration** — Most *attributed* closed forward PnL sits under the ML predictor pipeline; treat as single-point-of-failure until diversity metrics exist.
- **Liquidity & slippage** — Largest *strategy-level* unrealized sums are alt-heavy; paper % can diverge from executable PnL.
- **Feed health** — Several systems sparse or missing upstream JSON; manifests and `JSON_PICK_SOURCES` must stay aligned.
- **Synthetic / duplicate tagging** — `baby_strats_forward` + `battleground` + `codex_gpt5` on the same strategy family inflates narrative “system count” unless rolled up.
- **`systems[].active_picks` vs `picks.active`** — The generator does **not** expose `active_picks_detail`; counts can **differ** from a raw `source_system` count on `picks.active` (status / dedup / enrichment). Do **not** hard-fail health checks on that equality without defining the exact join rule in code.

---

## G. Mercury 2 — improvement matrix (expanded)

| Area | Why it matters | Concrete steps |
|------|----------------|----------------|
| **Data-pipeline reliability** | Missing or stale feeds (`claws_of_doom`, `copy_trader_intel`, `breakout_*`, etc.) cut coverage and skew §A–C. | 1) Audit **`hub/data/systems_manifest.json`** — each system’s `data_endpoints` (active/closed/metrics) for stale `main` URLs or wrong paths. 2) Health scripts: alert if pick JSON **older than 30 min** (HTTP `Last-Modified` or payload `generated_at` / `timestamp`). 3) **Retry + backoff** on all external API calls in scanners (shared helper). |
| **Strategy aggregation & reporting** | DNA-mutated strategies appear as separate IDs; Genome impact is opaque. | 1) **DNA / Genome** parent node in audit UI (rollup). 2) At ingestion: **`dna_group_id`** (or prefix rule) for `winner_pattern_*`, `contrarian_*`, GPX-style IDs. 3) Aggregated **P/L, WR, max DD** for the group in payload + template. |
| **Risk — high unrealized winners** | §C: `winner_pattern_precursor_inverse` concentrated in alts. | Exposure caps; trailing stops; optional **liquidity tier** filter (market cap / volume) before sizing. |
| **Copy-trader feed quality** | Few trades vs headline PnL → investigate leakage, double-count, or leverage. | Schema tests; per-signal logs; leverage cap (see table F). |
| **Model monitoring & drift** | `ml_crypto_predictor` drives most closed PnL. | Feature importance + distribution **weekly**; retrain workflow when drift threshold hit; shadow 30d model A/B. |
| **System hygiene & deprecation** | Empty `breakout_*` still count toward system totals. | RETIRED in manifest; remove from headline **total_systems** or filter `status === empty`; legacy archive. |
| **Unified alerting** | Actions scattered. | One dashboard: feed OK/STALE/MISSING, last success, error rate; webhooks on transition. |
| **Documentation & onboarding** | ROOT confusion. | Handbook + ingestion comments (see F). |

---

## H. Prioritized 30-day roadmap (Mercury 2 + Cursor merge)

Single suggested sequencing (adjust for capacity):

| Window | Focus |
|--------|--------|
| **Day 1–5** | Manifest URL audit (`hub/data/systems_manifest.json`); implement **JSON staleness** health-check; wire **Slack/Discord** on failure; add **retry/backoff** to hottest API callers. |
| **Day 6–10** | **`dna_group_id`** (or prefix rollup) at ingest; **Genome/DNA** parent metrics in `dashboard_generator` + `template.html`. |
| **Day 11–15** | **Exposure caps** + **dynamic trailing-stop** rules for top unrealized strategies (§C); document assumptions. |
| **Day 16–20** | **Unit tests** + repair **`copy_trader_intel`** pipeline; structured **signal logging** (source ID, gap detection >30 min). |
| **Day 21–25** | **Drift monitoring** hooks for `ml_crypto_predictor` (distributions, optional KL); weekly retrain **review** job (not necessarily auto-deploy). |
| **Day 26–30** | **Retire** legacy `breakout_*` (or gate in generator); launch **unified observability** MVP; publish **Strategy Origin Handbook**. |

**Note:** `/audit/health` does not exist today — either add a tiny static/JSON **health** artifact from CI or probe **`audit/data/dashboard_data.json`** `generated_at` from the health script.

---

## H2. 30-day implementation roadmap — owner & success metrics (Mercury 2 refined)

| Day | Goal | Owner / artifact | Success metric |
|-----|------|------------------|----------------|
| 1–3 | Audit manifest & URL health | Ops / `hub/data/systems_manifest.json` | All `data_endpoints` return **200**; script exits 0. |
| 4–7 | Automate health checks + alerts | DevOps / cron or GH Action | Alert within **~5 min** of endpoint failure or payload staleness. |
| 8–12 | DNA / Genome aggregation | Backend / `dashboard_generator.py` | One **DNA / Genome** rollup row with summed forward PnL + WR in payload/UI. |
| 13–16 | Copy-trader pipeline hardening | Data eng / `copy_trader_intel` | Schema tests pass; new closes visible in **`dashboard_payload.json`** within **2 min** of source refresh (target). |
| 17–20 | Exposure & stops | Quant / risk module (e.g. sizing + stop policy) | No single asset **>5%** notional (policy); document effect on top unrealized strategies after 48h paper run. |
| 21–24 | Model drift monitoring | ML / `ml_crypto_predictor` | Weekly distribution snapshot; alert if **KL > 0.2** (if adopted); shadow 30d model logged. |
| 25–27 | Retire legacy breakouts | Ops | `breakout_a/b/c` **RETIRED** in manifest; removed or gated in `JSON_PICK_SOURCES`; **total_systems** drops by 3 with no new MISSING noise. |
| 28–30 | Docs & observability | PM / Docs | **Strategy Origin Handbook** in `docs/`; minimal Grafana (or equivalent) green for feed + CI jobs. |

---

## I. Sample feed health script (adapted for this repo)

Manifest path in this workspace: **`hub/data/systems_manifest.json`**. Endpoints live under each system’s **`data_endpoints`** (e.g. `active`, `closed`), not a flat `feed_url`.

```python
#!/usr/bin/env python3
"""Ping manifest JSON endpoints; alert on HTTP failure. Extend with generated_at staleness."""
import json
import pathlib
import sys
from datetime import datetime, timezone

try:
    import urllib.request
except ImportError:
    raise SystemExit("stdlib only: use urllib")

# Assume this file lives in tools/ — repo root is parents[1]
_REPO = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = _REPO / "hub" / "data" / "systems_manifest.json"
TIMEOUT_SEC = 8
# SLACK_WEBHOOK = "https://hooks.slack.com/services/..."


def ping(url: str) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "feed-health/1.0"})
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as r:
            return 200 <= r.status < 300
    except Exception:
        return False


def main() -> None:
    if not MANIFEST.is_file():
        print(f"Missing manifest: {MANIFEST}", file=sys.stderr)
        sys.exit(2)
    doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    failures = []
    for sys_row in doc.get("systems") or []:
        sid = sys_row.get("id", "?")
        endpoints = sys_row.get("data_endpoints") or {}
        for label, url in endpoints.items():
            if not url or not isinstance(url, str):
                continue
            if not ping(url):
                failures.append(f"{sid}:{label}")

    if failures:
        ts = datetime.now(timezone.utc).isoformat()
        msg = f"[feed-health] FAIL {ts}\nMissing: {', '.join(failures)}"
        print(msg, file=sys.stderr)
        # if SLACK_WEBHOOK:
        #     import urllib.request
        #     urllib.request.urlopen(urllib.request.Request(
        #         SLACK_WEBHOOK,
        #         data=json.dumps({"text": msg}).encode(),
        #         headers={"Content-Type": "application/json"},
        #         method="POST",
        #     ), timeout=10)
        sys.exit(1)
    print("All manifest endpoints reachable")
    sys.exit(0)


if __name__ == "__main__":
    main()
```

Schedule via cron or a GitHub Action (e.g. every 5–15 minutes). Next iteration: parse each JSON for **`generated_at`** / **`timestamp`** and fail if older than **30 minutes**.

---

## I2. Payload-based audit health (`dashboard_payload.json`) — **schema-correct** for this repo

**Implemented files:** `audit_trail/collect_sources.py` (import-based source list), `audit_trail/dashboard_payload_health.py` (shared checks), `audit_trail/feed_health_check.py` (`--once` + optional Prometheus), `tools/audit_payload_health.py` (CI-friendly wrapper), `.github/workflows/feed-health.yml`, `docs/feed_health.md`, `docs/grafana_feed_health_panel.json`.

Mercury’s draft script assumed `systems[].system_id`, per-system `generated_at`, and `active_picks_detail`. **This repository does not:** rows use **`name`**, there is **no** per-system timestamp, and there is **no** `active_picks_detail`. `JSON_PICK_SOURCES` entries are **`(system_name, active_path, closed_path)` tuples** — not strings — so **regex parsing `dashboard_generator.py` is fragile**; use **import** (as in `collect_sources.py`).

**Recommended checks:**

1. **Payload age:** `payload["generated_at"]` (ISO) vs now — fail if older than `MAX_AGE_SECONDS` (e.g. 4h if generator hourly).
2. **Registry coverage:** every **first element** of `JSON_PICK_SOURCES` should appear in `systems[].name`, **except** names in **`_HIDDEN_SYSTEMS`** (intentionally omitted from the dashboard list — see `dashboard_generator.py`).
3. **Type sanity:** `unrealized_pnl_pct` and `active_picks` are numeric for each system row.
4. **Optional diagnostic:** compare `Counter(p["source_system"] for p in payload["picks"]["active"])` to `systems[].active_picks` — log **warnings** only until the generator documents the exact counting rule.

```python
#!/usr/bin/env python3
"""tools/audit_payload_health.py — run from repo root: python tools/audit_payload_health.py"""
from __future__ import annotations

import json
import pathlib
import sys
from datetime import datetime, timezone

# Repo root = parent of tools/
REPO = pathlib.Path(__file__).resolve().parents[1]
PAYLOAD_PATH = REPO / "audit_trail" / "data" / "dashboard_payload.json"
MAX_AGE_SECONDS = 4 * 3600


def main() -> int:
    sys.path.insert(0, str(REPO))
    from audit_trail.dashboard_generator import JSON_PICK_SOURCES, _HIDDEN_SYSTEMS

    if not PAYLOAD_PATH.is_file():
        print(f"Missing {PAYLOAD_PATH}", file=sys.stderr)
        return 2

    payload = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))
    age = -1.0
    gen_at = payload.get("generated_at")
    if gen_at:
        ts = datetime.fromisoformat(str(gen_at).replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - ts).total_seconds()
        if age > MAX_AGE_SECONDS:
            print(f"STALE payload generated_at={gen_at} age_s={int(age)}", file=sys.stderr)
            return 1

    names_in_payload = {s.get("name") for s in payload.get("systems") or []}
    registered = []
    for row in JSON_PICK_SOURCES:
        if isinstance(row, (list, tuple)) and row and isinstance(row[0], str):
            registered.append(row[0])
    missing = sorted(
        n for n in registered
        if n not in names_in_payload and n not in _HIDDEN_SYSTEMS
    )

    bad_types = []
    for s in payload.get("systems") or []:
        n = s.get("name", "?")
        try:
            float(s.get("unrealized_pnl_pct", 0.0))
            int(s.get("active_picks", 0))
        except (TypeError, ValueError):
            bad_types.append(n)

    if missing:
        print(f"MISSING system rows ({len(missing)}): {missing[:40]}{'...' if len(missing) > 40 else ''}", file=sys.stderr)
    if bad_types:
        print(f"BAD numeric fields: {bad_types}", file=sys.stderr)
    if missing or bad_types:
        return 1

    print(f"OK payload age_s={int(age)} systems={len(names_in_payload)} registered_sources={len(set(registered))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

### Example GitHub Action (schedule)

```yaml
# .github/workflows/audit-health.yml
name: Audit Feed Health
on:
  schedule:
    - cron: "*/15 * * * *"
  workflow_dispatch:

jobs:
  health:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: python tools/audit_payload_health.py
```

Add a second step to run **§I** manifest ping script if you copy it to `tools/manifest_endpoint_health.py`, or combine both in one job.

### Errata: Mercury draft `audit_health_check.py`

- Use **`systems[].name`**, not `system_id`.
- Do not require **`active_picks_detail`**; it is absent.
- Do not parse **`JSON_PICK_SOURCES`** with a broken regex — **import** the list or maintain a generated manifest.
- **Staleness:** use top-level **`payload["generated_at"]`**, not per-system fields.

---

## J. Follow-ups — sprint priority (Mercury question)

High-impact streams to sequence:

1. **Feed-health automation** — manifest pings + **§I2** payload age / registry coverage (fast, unblocks trust in §A–C).
2. **Exposure & stop-loss controls** — addresses #5–#6 in §F2 directly.
3. **Model-drift monitoring** — protects #1 over longer horizons.

Default recommendation: **(1) first**, then **(2)** in parallel with copy-trader fixes, then **(3)**.

Mercury also asked for deeper implementation checklists / resource estimates — still available on request per stream.

---

## K. Mercury 2 — quantitative metric toolkit (prop / hedge-fund style)

This section closes the two recurring gaps: **(a)** risk-adjusted performance beyond raw PnL%, and **(b)** **attribution** so ROOT / `source_system` rolls up into defensible capital decisions.

**Already in this repo (partial):** `dashboard_payload.json` carries portfolio-level **Sharpe**, **Sortino**, **Calmar**, **profit factor**, **expectancy**, **clean_metrics**, timeframe slices, and per-system stats under **`systems[]`**; the strategy **leaderboard** adds forward omega/tail ratios, sample-quality labels, and health scores. The toolkit below is the **next layer**: per **(strategy, symbol, direction)** time series, proof statistics, and governance.

### K1. Core performance-adjusted metrics (per strategy + per symbol)

| Metric | What it tells you | Quick formula / note | Why a quant desk cares |
|--------|-------------------|----------------------|-------------------------|
| **Annualised return (CAGR)** | Capital growth | \((1 + R_{\text{total}})^{365/d} - 1\) on equity curve (not sum of % trades unless chain-compounded carefully) | Benchmark vs. hurdle rate |
| **Sharpe** | Return vs. total vol | \((\mu - r_f) / \sigma\) on **daily** PnL or log returns | Classic risk-adjusted efficiency |
| **Sortino** | Return vs. downside vol | \((\mu - r_f) / \sigma_{\text{down}}\) | Penalises bad tails more than Sharpe |
| **Profit factor** | Money-maker simplicity | \(\sum \text{gains} / \sum |\text{losses}|\) | Fast go/no-go |
| **Hit-rate** | Win frequency | wins / total | Edge *type* (many small vs. few large) |
| **Average trade** | Typical payoff | \(\sum \text{PnL} / n\) | Sizing intuition |
| **Maximum drawdown (MDD)** | Worst peak→trough | On **cumulative** equity | Survival / allocator limits |
| **Calmar** | Return vs. drawdown | CAGR / \|MDD\| | Growth + pain |
| **Turnover / frequency** | Activity | trades / calendar days | Fee budget, capacity |
| **Capacity / impact** | Slippage vs. size | Simulate size ladder on spread + depth | Avoid killing edge |
| **Correlation / beta** | Factor exposure | Pearson vs. BTC/ETH/index returns | Diversification |
| **Information ratio** | Stable excess return | active return / tracking error vs. benchmark | Consistency of alpha |
| **p-value / CI** | “Is edge real?” | Bootstrap or t-test on **mean** trade return; multi-test correction if many strats | Anti–overfitting |

**Implementation tip:** Store metrics in a **time-series** keyed by `(strategy_id, symbol, direction, date)` (Parquet/SQLite/MySQL). Enables slices like “`ml_crypto_predictor` on BTCUSDT long in Q1” and clean aggregation upward. Today, closed picks in the payload/resolver are the natural **fact table** to feed this.

### K2. Attribution & “proof” layers

| Layer | What you capture | How it helps |
|-------|------------------|--------------|
| **Signal-source tagging** | `source_system` + optional **`synthetic_tag`** (e.g. `dna_mutation`, `sentiment`, `baby_strats_forward`) | Per-source PnL; spot one bad feed (ties to §F2 / ROOT map). |
| **Symbol–direction buckets** | PnL by `(symbol, LONG/SHORT)` | Shows *where* edge lives; position limits per bucket. |
| **Time-window segmentation** | In-sample / OOS / walk-forward / post-deploy | Separates backtest artefact from live edge. |
| **Confidence / proof score** | Fuse n, p-value, variance → 0–100 | Allocator-facing “how solid is this?” (see **K4**). |
| **Robustness** | Bootstrap PnL, Monte Carlo shocks, leave-one-feature-out | Fragility before real capital. |
| **Costs & slippage** | Fees, spread, impact model per venue | “Paper %” → executable PnL. |

### K3. Governance & operational best practices

| Practice | Reason | Quick implementation (this repo) |
|----------|--------|----------------------------------|
| **Experiment tracking** | Reproducible runs | Log a JSON manifest per `dashboard_generator` run under e.g. `audit_trail/runs/<iso>/` (params, git SHA, input file mtimes). |
| **Data versioning** | Feed changes ≠ silent metric jumps | DVC / git-lfs for heavy series; pin **raw** snapshot IDs in the run manifest. |
| **Metric regression suite** | Catch accidental PnL logic breaks | Golden snapshot tests (± tolerance) on `summary` + a few strategy rows after generator changes. |
| **Risk-budget allocation** | Caps per strategy / symbol / factor | Linear program or rule engine: max DD, max beta, max weight (extends §H2 / §F2). |
| **Live monitoring** | Decay alerts | Extend **§I2** + Prometheus/Grafana; alert e.g. rolling Sharpe < 0.5 or 30d MDD > threshold. |
| **Post-trade review** | Human loop on outliers | Weekly top/bottom 5 trades per strategy from resolved picks. |
| **Compliance logging** | Audit trail | Immutable append-only execution log if you ever need regulatory posture. |

### K4. Sample “proof-score” formula (adaptable)

Mercury proposed a **0–1** score; scale ×100 for display.

```
proof_score =
    0.40 * (1 - p_value)                    # bootstrap / test: p → 0 = more confident
    + 0.30 * (log10(trade_count) / log10(1e4))   # sample depth, cap at ~10k trades
    + 0.20 * (Sharpe / (Sharpe + 1))        # non-negative Sharpe assumed; clamp negatives separately
    + 0.10 * (1 - max_drawdown_frac)        # MDD as 0–1 fraction of equity
```

**Notes for integration:** clamp each term to \([0,1]\); handle **negative Sharpe** (e.g. map to 0 or use Sortino); apply **multiple-testing** correction when ranking hundreds of strategies. Wire the result into **`leaderboard[]`** or a new `proof_scores` block in `dashboard_payload.json` and surface in `audit_dashboard/template.html`.

### K5. End-to-end workflow (reference architecture)

```
Data ingest (OHLCV, on-chain, sentiment, picks JSON)
    → Signal gen (pick files with source_system, symbol, direction)
    → Backtest / resolver (per-trade PnL → audit_trail/data/*)
    → Metric engine (K1–K2 tables → aggregates)
    → dashboard_payload.json + /audit UI
    → Risk allocator (budgets, capacity)
    → Execution + slippage model + immutable logs
    → Live monitoring (health + performance decay alerts)
```

**TL;DR:** Measure **per (strategy, symbol, direction)** with risk-adjusted metrics; **tag** sources for attribution; add **statistical proof** (p-values, bootstrap) and a **proof-score**; wrap in **governance** (tracking, versioning, regression tests, risk budgets, monitoring).

### K6. Deeper-dive options (Mercury)

| Track | Focus |
|-------|--------|
| **A** | Implement **proof-score** + payload + dashboard cards. |
| **B** | **Risk-budget optimizer** (drawdown, capacity, beta constraints). |
| **C** | **CI pipeline** that validates new backtests / generator output and **alerts on metric regression**. |

These extend **§J**: after feed-health (1), proof metrics pair naturally with **exposure controls** (2) and **drift** (3); **C** is the safety rail whenever you change `dashboard_generator` or resolver logic.

---

## L. Mercury 2 — deep-dive playbook (four pillars)

Blends **quant rigor**, **ops discipline**, and optional **creative** layers. **§K** is the metric vocabulary; **§L** is how to **operationalize** it in sprints. **Repo reality:** picks live in many `*/data/*.json` files and in `audit_trail/data/universal_resolved_picks.json` — there is no single `audit_trail/picks/*.json` tree today; a **flat table** should be **exported** from the resolver + generator merge.

### L1. Metrics & attribution engine (“scorecard”)

| Pillar | Insight | Minimum-viable implementation | Why it matters |
|--------|---------|------------------------------|----------------|
| **A. Granular PnL** | Tag **strategy + symbol + direction** on every closed row. | Row shape: `{strategy, symbol, direction, entry_ts, exit_ts, pnl_pct, source_system, tags[]}`. Add a **`picks_flat.parquet`** (or SQLite) writer after merge in `dashboard_generator.py` or a small `audit_trail/export_picks_flat.py` job. | Answers “what works on **BTCUSDT long**?” vs. portfolio-averaged illusion. |
| **B. Proof-score** | Single **0–100** “edge solidity.” | Nightly job: read flat table → compute **§K4** → `strategy_metrics.parquet` keyed by `(strategy, symbol, direction)`. | Allocator-ready ranking; ties to **§K6 track A**. |
| **C. Capacity / impact** | Slippage vs. size. | Monte Carlo or grid: scale notional 5% steps; impact \(\propto \text{size}^{0.5}\); store **max size before net PnL < 0**. | Stops over-sizing illiquid alts (**§F2**). |
| **D. IR & beta** | Alpha vs. riding beta. | Daily returns vs. BTC/ETH/CCI composite; \(\beta\) from regression/correlation; **IR** = mean(excess)/std(excess). | Factor honesty. |
| **E. Turnover & costs** | Executable PnL. | Column **`gross_notional`**; `cost = notional * (fee + spread + impact_term)`. | Paper → bankable numbers. |

**Illustrative proof-score loop (pandas)** — replace bootstrap stub with a **proper** two-sided bootstrap or permutation test; Sharpe on **trade** PnL is noisy unless you align to **time buckets** first.

```python
# Illustrative only — validate statistics before production use
import numpy as np
import pandas as pd

picks = pd.read_parquet("audit_trail/data/picks_flat.parquet")
grp = picks.groupby(["strategy", "symbol", "direction"], observed=True)

def proof_score_block(df: pd.DataFrame) -> float:
    r = df["pnl_pct"].astype(float)
    n = len(r)
    if n < 5:
        return float("nan")
    # Bootstrap: fraction of resampled means <= 0 (one simple heuristic; prefer proper p-value)
    rng = np.random.default_rng(0)
    boot = rng.choice(r.values, size=(1000, n), replace=True)
    p_val = float((boot.mean(axis=1) <= 0).mean())
    size_factor = min(1.0, np.log10(n) / np.log10(10_000))
    sharpe = (r.mean() * 252) / (r.std() * np.sqrt(252) + 1e-9)
    equity = (1 + r / 100.0).cumprod()  # if pnl_pct is additive per trade, adjust compounding model
    peak = equity.cummax()
    mdd = float(((peak - equity) / peak.replace(0, np.nan)).max())
    score = 0.4 * (1 - p_val) + 0.3 * size_factor + 0.2 * max(0, sharpe / (sharpe + 1)) + 0.1 * (1 - min(1.0, mdd))
    return 100.0 * max(0.0, min(1.0, score))

out = grp.apply(lambda d: proof_score_block(d)).reset_index(name="proof_score")
out.to_parquet("audit_trail/data/strategy_metrics.parquet", index=False)
```

### L2. Architecture & data-flow blueprint

```
Market feeds (venues, on-chain, sentiment)
        →
Ingestion (today: JSON files + cron/GH Actions; optional: Kafka/PubSub)
        →
Raw pick store (per-system JSON under repo paths; resolved ledger)
        →
dashboard_generator + universal_pick_resolver
        →
Flat pick table (Parquet)  +  Metric engine  +  dashboard_payload.json
        →
/audit UI  +  optional Risk-budget engine  +  execution / logs
```

**Creative / optional twists**

| Twist | What it adds |
|-------|----------------|
| **Event-sourced picks** | Immutable stream (e.g. `crypto.picks` topic); replay from \(t_0\) for what-ifs without full regen. |
| **Feature store** | DuckDB / Delta / versioned Parquet for 400+ features — reproduce what the model saw. |
| **Unified ROOT registry** | `root_registry.json`: `source_system` → `{type: ML|DNA|sentiment|copy_trader, tier: A|B|C}` for UI colour + policy. |
| **Self-healing feed health** | Service pings feeds → Prometheus gauge `crypto_feed_up_to_date{system="..."}`; restart or page if latency > threshold; pair with **§I** manifest ping + **§I2** `tools/audit_payload_health.py**. |

### L3. Governance, risk & compliance (“hedge-fund discipline”)

| Practice | Crypto prop-shop shape | Minimal implementation |
|----------|------------------------|---------------------------|
| **Experiment tracking** | UUID per backtest + feature snapshot + git SHA | MLflow local SQLite; artifact path to `picks_flat.parquet` / payload hash. |
| **Data versioning** | Replay 2024-Q2 exactly | DVC or git-lfs on raw series; pin in run manifest. |
| **Regression suite** | CI fails if Sharpe drops > X% vs golden | GH Action: run generator + diff `summary` / golden `strategy_metrics` within tolerance (**§K6 track C**). |
| **Risk-budget LP** | Caps on DD, beta, capacity | PuLP / CVXPY: \(\sum exposure \le capital\), per-name caps, DD constraint (approximate). |
| **Live monitoring** | Sharpe, MDD, proof-score traces | Grafana + exporter scraping daily metrics table. |
| **Post-trade board** | Weekly winners/losers | Auto `audit_report.pdf` or Markdown from flat table → email/Discord. |
| **Regulatory log** | Immutable orders | Append-only store (S3 Object Lock / WORM pattern) if needed. |

### L4. Innovation & creative extensions

| Idea | Adds | Rough effort |
|------|------|--------------|
| **Meta-learning** | Which **ROOT** wins per regime (vol bull/bear) | Medium — needs regime series + labelled performance. |
| **Dynamic ROOT-switch** | Auto-fallback if proof-score **<** threshold **N** days | Medium — feature flags + mapping table. |
| **XAI (SHAP/LIME)** | “Top 3 drivers” per ML pick in UI | Medium — export JSON sidecar per pick. |
| **Cross-asset correlation heatmap** | Hidden concentration | Low — nightly Pearson matrix → Grafana. |
| **Synthetic stress paths** | Diffusion / generative paths for illiquids | High — offline validation first. |
| **Strategy Lab (sandbox UI)** | Drag ROOT tags, re-run metrics | Medium — small API + Tailwind UI. |

### L5. First-sprint checklist (3 weeks)

| Week | Focus | Deliverables |
|------|-------|----------------|
| **1** | Feed-health (**§J item 1**) | `tools/audit_payload_health.py` (done) + schedule **§I2** Action; optional Prometheus gauge + `docs/feed_health.md`; manifest ping script if desired. |
| **2** | Proof-score & attribution (**§K6 A**) | `picks_flat.parquet` export; nightly `strategy_metrics.parquet`; first **Tailwind** cards on `/audit` for proof_score + Sharpe + MDD per strategy. |
| **3** | Exposure & stops (**§J item 2**) | Capacity / impact stub; trailing-stop policy in execution path; unit tests for slippage edge cases. |

**Sprint outcome:** visible feed health; first **quantitative** proof layer; **safety** rails on high unrealized names (**§F2**).

### L6. TL;DR one-pager + next step

1. Instrument every pick with **strategy, symbol, direction, source_system, tags**.  
2. **Flat versioned pick table** + **proof-score** (confidence + size + risk-adjusted return + drawdown).  
3. Automate **feed health** (script + Prometheus + Slack/Discord).  
4. **Capacity & slippage** models before scaling size.  
5. **Risk-budget** optimizer (DD, beta, capacity).  
6. **Live monitoring** + weekly post-trade review.  
7. Iterate **meta-learning / XAI** to keep the ROOT map explainable.

**Next step (Mercury):** same fork as **§J** — **(1) feed-health**, **(2) exposure & stops**, **(3) drift** — *or* a **detailed implementation plan** for the **proof-score pipeline** (flat export → parquet → payload → UI). Say which track to spec first.

---

*Numbers in sections A–C are from the payload present in the workspace at analysis time; they will change as picks resolve and the generator reruns. Sections F–L incorporate Mercury 2 recommendations (operations, health checks, schema corrections, quantitative toolkit, and implementation playbook).*
