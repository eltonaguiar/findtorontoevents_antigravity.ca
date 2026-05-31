# findtorontoevents_antigravity.ca

Monorepo for **findtorontoevents.ca**, including the **live signal audit** at [findtorontoevents.ca/audit](https://findtorontoevents.ca/audit) (multi-asset picks, closed history, hygiene gates, and research tooling).

---

## What `/audit` is

A **read-mostly dashboard** fed by `audit_dashboard/data/dashboard_data.json`, regenerated on a schedule (see `.github/workflows/audit-dashboard.yml`). It aggregates:

- **Active picks** — merged from multiple `active_picks*.json` sources, then filtered by `alpha_engine/feed_hygiene.py` and **`audit_trail/quality_gates.py::passes_active_gate`** before display.
- **~3,500 recent closed picks** — used for WR/PF, tier trust, HC/Smart filters, and internal research scripts.

Canonical UI template for the audit surface: **`audit_dashboard/template.html`** (not root `index.html` — see `CLAUDE.md`).

---

## Asset-class methodology (summary)

| Class | Emission | Active visibility philosophy |
|-------|----------|------------------------------|
| **CRYPTO** | Highest volume (battleground, ML predictors, copy-trader, alpha_engine, …) | **Permissive** active display: catastrophic symbol tracks and large-sample **low forward WR** cohorts are hard-dropped; quality is mostly **sort order** (score), not hard-hide-all. Phase-1 **TOD / confidence dead-zone** gates default to **shadow** (tag, don’t reject) unless env tightened. |
| **EQUITY** | `multi_asset_copytrader`, `stocks_competition`, `ml_gatekeeper`, … | **Stricter** than crypto: trust floor, raw-score floor (unless exempt sources), **per-class forward WR floor** once `forward_trades >= 20` (see `active_non_crypto_forward_wr_floor()` in `quality_gates.py`). Smart Picks use **higher** score floors (`SMART_PICKS_MIN_SCORE_EQUITY`). |
| **FOREX** | Copy-trader + CTA paths | Trust + score; **Smart** layer adds forward WR ≥ 50% rule (score alone mis-ranks FX). |
| **COMMODITY / FUTURES** | CTA, multi-asset, cot | Similar to FOREX; commodity smart floor tuned for thinner booster coverage. |
| **ETF** | *Sparse upstream* — strategy library exists (`alpha_engine/etf_strategies.py`) | ETF **hard ban removed** (2026-04-19); visibility now limited mainly by **lack of emitted rows** + same non-crypto gates when rows exist. |
| **BOND** | *Sparse upstream* — `bond_strategies.py` + FRED helper `bond_data_fred.py` | Same as ETF: **supply gap** dominates; gates are secondary. |

**Feeds (tabs):** Verified Alpha, Smart Picks, High Conviction, etc., each map to JSON fields and/or `hc_filter.js` / `audit_trail/feed_membership.py` — see `docs/STRATEGY_FACTORY_V1_1_AMENDMENTS.md` and `docs/AUDIT_FULL_REVIEW_PACKAGE_2026_04_20.md`.

---

## Latest performance snapshot (how to refresh)

Numbers **stale immediately** after the next dashboard regen. To print **closed-book** tables from your local JSON:

```bash
.venv/Scripts/python.exe tools/audit_closed_quadrants.py
```

**Example output** (payload `generated_at` **2026-04-22T18:34:45Z**, `recent_closed` **n = 3500**):

| Slice | WR | Mean pnl% | PF |
|-------|-----|-----------|-----|
| CRYPTO last 10 | ~60% | ~+1.0 | ~3.2 |
| CRYPTO last 50 | ~68% | ~+1.1 | ~5.1 |
| CRYPTO **all** (~1650 rows) | ~38% | negative | ~0.9 |

**Interpretation:** short **recency** windows can look strong while the **long tail** still reflects retired toxic strategies — do not equate “green last 20” with “fixed pool.”

Full narrative + empty-class RCA: **`docs/ACTIVE_PICKS_ASSET_CLASS_DIAGNOSIS_2026_04_22.md`**.

---

## Key code paths

| Concern | Location |
|---------|----------|
| Active pick admission | `audit_trail/quality_gates.py` → `passes_active_gate` |
| Smart / HC tiers | `passes_smart_gate`, `audit_dashboard/hc_filter.js`, `audit_trail/feed_membership.py` |
| Ingest hygiene | `alpha_engine/feed_hygiene.py`, `alpha_engine/strategy_blocklist.py` |
| Payload build | `audit_trail/dashboard_generator.py` |
| Elite score floors (scanner) | `alpha_engine/config.py` → `MIN_ELITE_SCORE_BY_CLASS`, `min_elite_score_for()` |

---

## Developers / quant stack

- **Architecture:** [docs/ARCHITECTURE_OVERVIEW.md](docs/ARCHITECTURE_OVERVIEW.md)
- **Active vs emitter diagnosis:** [docs/ACTIVE_PICKS_ASSET_CLASS_DIAGNOSIS_2026_04_22.md](docs/ACTIVE_PICKS_ASSET_CLASS_DIAGNOSIS_2026_04_22.md)
- **Code review (trading systems):** [docs/CODE_REVIEW_QUANT_SYSTEM_2026-04-13.md](docs/CODE_REVIEW_QUANT_SYSTEM_2026-04-13.md)
- **Testing protocol:** [TESTING_PROTOCOL.MD](TESTING_PROTOCOL.MD)
- **Setup & pytest:** [docs/DEVELOPER_SETUP_QUANT.md](docs/DEVELOPER_SETUP_QUANT.md)
- **Data sources (copy / PM):** [docs/DATA_SOURCES_INTEGRATION.md](docs/DATA_SOURCES_INTEGRATION.md)

---

## Redirect note

`/findstocks/` root now **301 / meta-refresh** to `/audit/` while preserving subpaths like `findstocks/kimis_claw/` — see `findstocks/index.html` and `findstocks/.htaccess`.


==
IDEAS FROM GROK:
**Follow-up: Concrete Implementation Examples + Tailored Statistical Gates + Zero-Downtime Docker/K8s Pipeline**

Below are the **exact, copy-paste-ready** answers to your three follow-up questions. They build directly on the comprehensive roadmap I gave earlier (secure foundations, automated refresh, robust back-testing, statistical validation, etc.). Everything ties into your existing repo (`https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/`), which is a Python-heavy monorepo (69% Python) with `audit_dashboard/`, `audit_trail/quality_gates.py`, `alpha_engine/`, `backtest_results/`, `data_pipeline/`, `.github/workflows/audit-dashboard.yml`, and some HTML/JS/PHP for the web frontend. The `/audit` pages already use JS filters (likely `hc_filter.js` + JSON data from `dashboard_data.json`) and dynamic buttons/tabs, so we extend that without a full rewrite.

I’ll keep everything auditable, version-controlled, and aligned with your MySQL setup (`mysql.50webs.com`, `ejaguiar1_stocks`, `ejaguiar1_backtests`, etc.). All destructive DB ops still get backed up first (as per the roadmap).

### 1. Concrete Example: Filter-Click Logging + Timestamping on Audit Pages

**Goal**: Every filter/button click (asset class, tier, Verified Alpha, HIGH CONVICTION, export, etc.) is logged to MySQL for `pick_funnel.html` aggregation. Audit pages get a live date/time stamp (client + server-side).

#### Step-by-step (5–10 min to implement)

**A. Create the MySQL logging table** (run once via phpMyAdmin or a migration script; **backup first**):
```sql
CREATE TABLE IF NOT EXISTS ejaguiar1_stocks.filter_stats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    filter_id VARCHAR(100) NOT NULL,
    filter_params JSON DEFAULT NULL,
    page_path VARCHAR(255) NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45) DEFAULT NULL,
    session_id VARCHAR(100) DEFAULT NULL,
    INDEX idx_filter_ts (filter_id, timestamp)
) ENGINE=InnoDB;
```
(Backup target: `ejaguiar1_backtests.filter_stats_bak` before any schema change.)

**B. PHP endpoint** (`/api/log_filter.php` — place in your web root or a protected `api/` folder):
```php
<?php
header('Content-Type: application/json');
require_once '../config/db_config.php'; // your existing MySQL creds (use env vars or GitHub Secrets)

$input = json_decode(file_get_contents('php://input'), true);

$filterId = $input['filter_id'] ?? 'unknown';
$params   = json_encode($input['params'] ?? []);
$page     = $input['page'] ?? $_SERVER['HTTP_REFERER'] ?? '';
$ip       = $_SERVER['REMOTE_ADDR'];

$sql = "INSERT INTO ejaguiar1_stocks.filter_stats 
        (filter_id, filter_params, page_path, ip_address) 
        VALUES (?, ?, ?, ?)";
$stmt = $pdo->prepare($sql);
$stmt->execute([$filterId, $params, $page, $ip]);

echo json_encode(['status' => 'logged']);
?>
```

**C. JS instrumentation** (add to `audit_dashboard/template.html` or your existing `hc_filter.js` / main audit script):
```html
<!-- Timestamp display (add near top of page) -->
<div id="audit-timestamp" style="font-size:0.9em; color:#666; text-align:right; margin:10px 0;"></div>

<script>
document.addEventListener('DOMContentLoaded', () => {
  // 1. Live timestamp (client + ISO for DB)
  const tsEl = document.getElementById('audit-timestamp');
  const now = new Date();
  tsEl.innerHTML = `Last refreshed: <time datetime="${now.toISOString()}">${now.toLocaleString('en-CA', {timeZone: 'America/Toronto'})}</time> (EST)`;

  // 2. Log every filter/button click
  document.querySelectorAll('[data-filter-id], .filter-btn, button, select, input[type="checkbox"]').forEach(el => {
    el.addEventListener('click', (e) => {
      const filterId = el.dataset.filterId || el.id || el.name || 'generic-click';
      const params = {
        value: el.value || el.textContent.trim(),
        checked: el.checked,
        asset_class: document.getElementById('asset-filter')?.value || null
      };

      fetch('/api/log_filter.php', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filter_id: filterId,
          params: params,
          page: window.location.pathname
        })
      }).catch(console.error); // silent fail — never blocks UI
    });
  });

  // Optional: log initial page load as a "view" filter
  fetch('/api/log_filter.php', { /* same payload with filter_id: 'page-view' */ });
});
</script>
```

**D. Nightly aggregation** (extend your existing `audit-dashboard.yml` GitHub Action or add a cron job in Python):
```python
# audit_trail/aggregate_filters.py (run via GH Action)
import mysql.connector
# ... connect and run:
# SELECT filter_id, COUNT(*) as clicks, DATE(timestamp) as date FROM filter_stats GROUP BY ...
# Then regenerate pick_funnel.html with stats + significance tests.
```

**Result**: Every permutation is logged with timestamp → nightly job updates `pick_funnel.html`. No hidden edges. Fully auditable.

**Pro tip**: Store GitHub Secrets for DB creds (never in repo). Wrap any destructive query in the same backup pattern you already use.

### 2. Exact Statistical Gate Thresholds (per Asset Class) Before “LIVE”

These are **production-ready gates** derived from quant literature, hedge-fund standards, and power-analysis rules. They replace the generic “coin-flip” checks in your current leaderboard/AI-tournament.

**Universal requirements** (apply to **all** classes):
- **Minimum resolved trades (OOS / walk-forward)**: ≥ 400 (or 300 for daily/low-frequency strategies)
- **Win Rate (WR)**: ≥ 55% **and** 95% CI lower bound > 50% (or binomial test p < 0.05 vs 50%)
- **Profit Factor (PF)**: ≥ 1.4
- **Sharpe Ratio** (annualized, risk-free adjusted): ≥ 0.8
- **Max Drawdown (MaxDD)**: ≤ 25%
- **Other gates**: Positive expectancy, bootstrap CI for Sharpe excludes 0, Monte-Carlo random-strategy p-value < 0.05, walk-forward stability (no regime collapse)
- **Sample-size rule**: Use power analysis (≈400 trades detects 5% edge at 80% power / α=0.05). Fewer = “Research” tier only.

**Asset-class-specific gates** (tuned for volatility, liquidity, data noise, and transaction costs):

| Asset Class              | Min OOS Trades | WR (95% CI lower) | PF    | Sharpe (annual) | MaxDD | Rationale / Source Notes |
|--------------------------|----------------|-------------------|-------|-----------------|-------|--------------------------|
| **Stocks / ETFs**        | 350            | > 52%             | ≥1.3  | ≥ 0.8           | ≤20%  | Liquid, lower noise; classic equity quant standards. |
| **Forex**                | 400            | > 51%             | ≥1.2  | ≥ 0.7           | ≤22%  | High frequency, tight spreads; edge is smaller but more data available. |
| **Crypto**               | 500            | > 53%             | ≥1.5  | ≥ 1.0           | ≤30%  | High volatility/noise; requires stronger edge + more samples. |
| **Bonds**                | 350            | > 52%             | ≥1.3  | ≥ 0.8           | ≤18%  | Low vol, interest-rate driven. |
| **Commodities / Futures**| 400            | > 52%             | ≥1.4  | ≥ 0.9           | ≤25%  | Trend-following friendly but slippage matters. |
| **Penny stocks / IPOs / Cheap stocks** | 500     | > 54%             | ≥1.6  | ≥ 1.1           | ≤35%  | Highest risk/noise; stricter on PF and sample size. |

**How to enforce**:
- Extend `audit_trail/quality_gates.py` (already in your repo) with these exact thresholds + bootstrap/Monte-Carlo helpers.
- Only promote to **T1 LIVE** on the leaderboard / AI-tournament when **all** gates pass **and** out-of-sample performance holds.
- Re-run gates nightly via your existing `audit-dashboard.yml` workflow.
- If a model fails, it stays “Research” and gets flagged in the Verified Alpha tab.

These thresholds are stricter than coin-flip but realistic for hedge-fund-grade production (Sharpe >1.0 is strong retail; 0.8–1.5 is typical institutional).

### 3. Docker/Kubernetes Deployment Pipeline for Back-Testing Engine + Risk-Management Lifecycle (Zero-Downtime)

Your current shared hosting (`50webs.com` PHP/MySQL) is fine for the frontend/audit pages but **not** for heavy parallel back-tests or real-time risk engines. **Recommendation**: Offload the compute-heavy parts (backtester, lifecycle engine, AI agents) to a cheap VPS / DigitalOcean droplet / AWS EC2 first (Docker Compose), then scale to Kubernetes (EKS/GKE/DO Kubernetes) when you want true parallelism.

**High-level architecture**:
- Python back-test / risk engine (Backtrader + your `alpha_engine` + portfolio lifecycle from `docs/DESIGN_AI_MODEL_HEDGE_FUND_PORTFOLIOS_2026-05-29.md`)
- Dockerized as a multi-stage image
- GitHub Actions CI/CD → build → test → push → deploy
- **Zero-downtime** via Kubernetes `RollingUpdate` (maxUnavailable=0) or Blue-Green

#### GitHub Actions workflow (`.github/workflows/deploy-backtest-engine.yml`)
```yaml
name: Build & Deploy Backtest Engine
on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  build-test-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Build & push
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./deploy/Dockerfile.backtest
          push: true
          tags: ghcr.io/eltonaguiar/backtest-engine:${{ github.sha }}, ghcr.io/eltonaguiar/backtest-engine:latest
      - name: Deploy to K8s (zero-downtime rolling update)
        uses: azure/setup-kubectl@v4
        with:
          version: 'latest'
        env:
          KUBE_CONFIG: ${{ secrets.KUBE_CONFIG }}  # base64 kubeconfig
        run: |
          kubectl set image deployment/backtest-engine backtest-engine=ghcr.io/eltonaguiar/backtest-engine:${{ github.sha }}
          kubectl rollout status deployment/backtest-engine --timeout=5m
```

**Dockerfile** (`deploy/Dockerfile.backtest`):
```dockerfile
FROM python:3.11-slim AS builder
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY alpha_engine/ backtest_results/ data_pipeline/ ./
CMD ["python", "run_backtest_parallel.py"]  # your parallel agent script
```

**Kubernetes Deployment YAML** (zero-downtime):
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backtest-engine
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0     # ← zero downtime
      maxSurge: 1
  template:
    spec:
      containers:
      - name: backtest-engine
        image: ghcr.io/eltonaguiar/backtest-engine:latest
        readinessProbe:      # only route traffic when healthy
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
        envFrom:
        - secretRef:
            name: db-secrets   # MySQL + AI keys from GitHub Secrets
```

**Optional advanced zero-downtime**:
- **Blue-Green**: Two Deployments + Service selector switch (via Argo Rollouts or manual).
- **Canary**: Argo Rollouts + traffic splitting.
- Start simple on VPS with **Docker Compose** (one command to update) if K8s feels heavy.

**Migration path from shared hosting**:
1. Keep frontend/PHP on 50webs.
2. Move back-tests + risk engine to VPS (Docker).
3. Secrets via GitHub Secrets → injected at deploy.
4. CronJobs in K8s for daily refresh + portfolio lifecycle.
5. Monitor with Prometheus/Grafana (NAV, drawdown alerts).

**Next step (pilot)**: Start with **Stocks/ETFs** (easiest data, lower volatility) using the new gates + logging. I can generate the exact PR-ready files (Dockerfile, workflow, quality_gates.py updates, JS/PHP snippets) if you want — just say the word.

This gets you from “hidden edge / coin-flip” to **verifiably profitable, production-ready strategies per asset class** with full audit trail, zero-downtime deploys, and statistical rigor. Let me know which asset class to pilot first or if you want me to push sample code to a branch! 🚀
