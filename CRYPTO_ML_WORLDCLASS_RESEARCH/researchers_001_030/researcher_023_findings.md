# Researcher 023: Dr. Emily Carter — Cloud AI/ML Services for Crypto ML Prediction
## Research Findings Report (Updated: February 2026)

**Researcher:** Dr. Emily Carter
**Title:** Cloud AI/ML Solutions Architect
**Background:** PhD Stanford CS, 12 years exp, former AWS Solutions Architect
**Research Question:** Which cloud services are best suited for crypto ML prediction at minimal cost?
**Status:** COMPLETE

---

## Executive Summary

After an exhaustive survey of the current (2024-2026) cloud ML landscape, the dominant finding is clear: for a solo developer or small team running a crypto ML pipeline on GitHub Actions' free tier, the marginal cost of significant compute upgrades is much lower than it was even 18 months ago. The GPU spot market has collapsed to under $0.25/hr for capable cards (RTX 4090 on Vast.ai), serverless inference is essentially free at low volumes, and free-tier databases can handle thousands of daily trade signals without a cent of spend.

The benchmark system (this project) is already well-positioned. The critical upgrade path is not "move to AWS" — it is "stay on GitHub Actions + add a $5-20/month burst compute layer on RunPod or Vast.ai for training runs only."

---

## Section 1: Free Tier ML Compute Platforms

### 1.1 GitHub Actions (Current Stack)

**Free Tier Specs (Public Repos — always free):**
- Ubuntu, Windows, macOS runners
- Standard runner: 2-core CPU, 7 GB RAM, 14 GB SSD
- Maximum job timeout: 6 hours per job (recommend setting `timeout-minutes: 360` explicitly)
- Maximum workflow run time: 35 days (irrelevant in practice)
- Concurrent jobs: 20 (free tier)
- Monthly minutes: 2,000 min/month for private repos on Free plan; **unlimited for public repos**

**GPU Availability (2024+):**
- GitHub GPU hosted runners are now GA (July 2024): T4 GPU runners available
- Cost: NOT included in free tier; T4 GPU runner = ~$0.07/min billed
- Self-hosted runners remain the recommended path for GPU workloads at zero cost

**2026 Pricing Change (effective March 1, 2026):**
- Hosted runner prices reduced by up to 39%
- New $0.002/minute cloud platform fee added for ALL runs (including self-hosted)
- Free minute quotas remain unchanged
- Impact on this project: public repo workflows stay free; private repo workflows eat into 2,000 min/month allowance

**Limitations for Crypto ML:**
- No GPU on free tier (CPU-only)
- 7 GB RAM is tight for training XGBoost/LightGBM on large datasets (manageable for our scale)
- 6-hour timeout is sufficient for all current workflows (our longest run is ~15 minutes)
- Disk space (14 GB) limits model artifact caching — use Hugging Face or GitHub Releases for large models
- No persistent state between runs (use SQLite committed to repo, or external DB)

**Performance Characteristics:**
- Excellent for: scheduled scanning, signal generation, lightweight inference, data pipeline orchestration
- Poor for: training deep learning models, large dataset processing, real-time sub-second inference

**Ease of Setup:** 10/10 — zero infrastructure management, YAML-based, already in use

---

### 1.2 Google Colab (Free Tier)

**Free Tier Specs (2025-2026):**
- GPU: NVIDIA T4 (16 GB VRAM) — availability varies by demand
- RAM: ~12-13 GB system RAM
- Disk: ~100 GB runtime disk (ephemeral)
- Session limit: up to 12 hours, but can be cut to 3-6 hours under heavy platform load
- Weekly GPU quota: ~15-30 GPU hours (not guaranteed; depends on usage history and demand)
- Compute Unit system introduced: heavier GPU usage depletes CUs faster, leading to throttling

**Cost:**
- Free tier: $0 (with restrictions above)
- Colab Pro: $9.99/month — more GPU hours, longer sessions, background execution
- Colab Pro+: $49.99/month — priority GPU access, V100/A100 access

**Performance Characteristics:**
- T4 GPU is solid for training small-to-medium models (Random Forest, XGBoost, shallow neural nets)
- Not reliable enough for production ML pipelines — sessions can drop mid-training
- No scheduled execution natively — requires external trigger (Colab API + GitHub Actions)

**Ease of Setup:** 9/10 — browser-based, no config needed

**Limitations for Crypto ML:**
- Session instability makes it unsuitable for unattended overnight training
- No persistent storage without Google Drive mount
- Cannot serve real-time inference (no public endpoint from free tier)
- IP-based rate limiting on free APIs is problematic when running from Colab's shared IP pool

**Best Use Case for This Project:** Ad-hoc exploratory training, hyperparameter sweeps when no RunPod budget available.

---

### 1.3 Kaggle Notebooks (Free Tier)

**Free Tier Specs (2025-2026):**
- GPU: NVIDIA Tesla P100 (16 GB) or T4 — available on demand
- TPU: Google TPU v3-8 — 30 hours/week
- GPU quota: 30 hours/week GPU time
- Session limit: 9 hours per session
- Background execution: YES — kernel continues running if browser is closed (critical differentiator vs Colab free)
- RAM: ~30 GB
- Disk: ~20 GB

**Cost:** $0 (Kaggle is free, owned by Google)

**Performance Characteristics:**
- More reliable than Colab free tier for training runs
- Background execution makes it the best free option for unattended model training
- P100 is slower than T4 for inference but fine for training
- 30 GPU hours/week = ~4.3 hours/day, which covers periodic retraining needs

**Ease of Setup:** 8/10 — requires Kaggle account, slightly less convenient than Colab for custom pip installs

**Limitations for Crypto ML:**
- Cannot make outbound API calls to Binance or CoinGecko (Kaggle blocks certain internet access during notebook execution — verify per session)
- No scheduled execution (must trigger manually or via Kaggle API)
- Dataset uploads required for data; cannot stream live market data during training
- 30 GPU hours/week hard cap

**Best Use Case for This Project:** Weekly model retraining jobs. Upload historical OHLCV dataset, run training, download model artifact. Best free GPU compute for batch training.

---

### 1.4 AWS Free Tier

**SageMaker Free Tier (First 2 months only):**
- Notebooks: 250 hours/month of ml.t3.medium
- Training: 50 hours/month of m4.xlarge or m5.xlarge (CPU, no GPU)
- Inference: 125 hours/month of m4.xlarge
- Note: This is a 2-MONTH trial, not permanent

**S3 Free Tier (Always Free):**
- 5 GB Standard storage
- 20,000 GET requests/month
- 2,000 PUT requests/month

**EC2 Free Tier (12 months):**
- 750 hours/month of t2.micro or t3.micro (1 vCPU, 1 GB RAM)
- Sufficient for running a lightweight inference API or monitoring daemon

**Lambda Free Tier (Always Free):**
- 1 million requests/month
- 400,000 GB-seconds of compute per month (e.g., ~3.2 million seconds at 128 MB)

**Performance Characteristics:**
- SageMaker free tier: CPU-only, not useful for deep learning
- Lambda + scikit-learn models: viable for inference if model is under 250 MB (Lambda package limit)
- S3: excellent for storing model artifacts and historical data

**Ease of Setup:** 5/10 — steep learning curve, IAM permissions, VPC config

**Limitations:**
- SageMaker free tier expires after 2 months — then costs escalate rapidly
- No GPU on free tier
- Lambda cold starts for ML models: 10-20 seconds for a 1 GB model (unacceptable for real-time signals)
- As of August 2025, AWS bills for Lambda INIT phase — can increase Lambda costs 10-50% for heavy startup models

---

## Section 2: Cheapest GPU Compute for Training

### 2.1 Vast.ai (Marketplace Model)

**Pricing (Feb 2026):**
- RTX 4090: $0.24-$0.60/hr (marketplace bid)
- H100 SXM: $1.49-$1.87/hr (marketplace)
- RTX 3090: $0.15-$0.35/hr

**Billing Model:** Real-time bidding marketplace — prices fluctuate with supply/demand. Per-hour or per-second billing depending on provider.

**Performance Characteristics:**
- Widest GPU selection of any provider
- Community-hosted machines — quality varies (uptime not guaranteed)
- SSH and Jupyter access
- Suitable for training jobs where interruption is tolerable

**Ease of Setup:** 7/10 — Docker-based, simple web UI, SSH key management required

**Limitations:**
- Community machines can go offline mid-training
- Latency to training machine varies (geographical distribution of hosts)
- Not suitable for inference (no guaranteed uptime)
- Privacy concern: running code on unknown hardware

**Best Use Case:** Burst training of our ML models (XGBoost/LightGBM retraining) at $0.30/hr or less. A 2-hour training run = $0.60.

---

### 2.2 RunPod

**Pricing (Feb 2026):**
- RTX 4090: $0.35/hr (Community Cloud)
- A100 40GB: $1.19/hr
- H100: $1.99/hr (Community Cloud)
- T4: $0.40/hr

**Serverless GPU Pricing:**
- Per-second billing (partial seconds rounded up to 1 second)
- Spot pricing: 60-91% discount vs standard rates
- On-demand flex workers scale to zero — pay only when processing
- 20-30% discount for always-on workers vs flex

**Performance Characteristics:**
- More reliable than Vast.ai (RunPod manages hardware quality)
- Serverless endpoints with auto-scaling to zero — ideal for inference endpoints
- Container-based deployment (Docker images)

**Ease of Setup:** 8/10 — clean UI, good documentation, template-based GPU pods

**Limitations:**
- Minimum spend required to activate account ($10 credit)
- Community Cloud less reliable than Secure Cloud (price premium applies)
- No persistent disk for serverless workers (mount network storage separately at cost)

**Best Use Case for This Project:**
1. Serverless inference endpoint for our crypto ML models — only charges when a signal is requested
2. Periodic training jobs (boot pod, train, save model to S3/HF, shut down)

---

### 2.3 Lambda Labs

**Pricing (Feb 2026):**
- H100 SXM: $2.99/hr (on-demand)
- A100 40GB: $1.29/hr
- A10 (24GB): $0.60/hr
- RTX 6000 Ada: $0.80/hr

**Performance Characteristics:**
- High-quality datacenter hardware (no community machines)
- Reliable uptime — better than Vast.ai or RunPod Community
- Simple API for programmatic instance management
- Jupyter + SSH access

**Ease of Setup:** 8/10 — cleaner than AWS, good Python SDK

**Limitations:**
- No serverless option — pay for full hours even for short jobs
- GPUs frequently out of stock (demand exceeds supply for H100/A100)
- More expensive than Vast.ai/RunPod for equivalent hardware

**Best Use Case:** Large training runs (multiple hours) where reliability matters more than cost.

---

### 2.4 Thunder Compute

**Pricing (Feb 2026):**
- A100 80GB: $0.78/hr (per-minute billing)
- RTX 4090: competitive pricing

**Key Differentiator:** Per-minute billing — critical for short training jobs where hourly billing wastes money.

**Best Use Case:** Short training runs (20-60 minutes) where per-minute billing saves 30-50% vs hourly providers.

---

## Section 3: Serverless Inference for Trading Models

### 3.1 AWS Lambda

**Free Tier:** 1M requests/month, 400K GB-seconds/month (always free)

**ML Inference Suitability:**
- Package size limit: 250 MB (direct) or 10 GB (container image via ECR)
- Memory: up to 10 GB RAM per function
- Timeout: up to 15 minutes per invocation
- Cold start for ML model: 100ms-20 seconds depending on model size
  - Simple sklearn model (10 MB): ~200-500ms cold start
  - XGBoost model (50 MB): ~1-3 seconds cold start
  - Large ensemble (500 MB): 10-20 seconds cold start

**2025-2026 Changes:**
- INIT phase now billed (August 2025): adds 10-50% cost for heavy startup logic
- SnapStart available for Java runtimes — reduces cold starts
- Python/Node.js remain fastest cold-start runtimes for ML

**Cost for Crypto Signal Inference:**
- At our scale (a few hundred requests/day): $0/month (well within free tier)
- Even at 10,000 signals/day at 1-second execution with 512 MB: ~$0.02/month

**Setup Complexity:** 6/10 — Lambda layers for large dependencies, ECR container for big models

**Recommended Pattern:**
```
GitHub Actions (scheduler)
  → API call to Lambda
  → Lambda loads model from S3
  → Returns signal JSON
  → GitHub Actions writes to active_picks.json
```

**Limitations:** Cold starts are the primary concern. Use Lambda Warmers (scheduled ping every 5 min) to keep warm — costs ~$0.50/month additional.

---

### 3.2 GCP Cloud Functions (Gen 2)

**Free Tier:** 2M invocations/month, 400K GB-seconds, 200K GHz-seconds (always free)

**ML Inference Suitability:**
- Memory: up to 16 GB (higher than Lambda's 10 GB)
- Timeout: up to 9 minutes (vs Lambda's 15 min — Lambda wins here)
- Cold start: generally faster than Lambda for Python/Node.js
- GPU support: NVIDIA L4 (24 GB VRAM) in preview via Cloud Run
- No provisioned concurrency equivalent (Lambda wins for consistent latency)

**Cost:** Similar free tier to Lambda. Beyond free tier, ~$0.0000004/request + compute time.

**Setup Complexity:** 6/10 — similar to Lambda; gcloud CLI required

**Best For:** If already on GCP ecosystem; higher memory limit is useful for large model loading.

**Limitations for Trading:**
- 9-minute max timeout (vs Lambda 15 min) — matters for batch signal generation
- GPU support (via Cloud Run) is still in preview; not production-ready for serverless

---

### 3.3 Cloudflare Workers AI

**Free Tier:**
- 10,000 "neurons" per day free (neurons = compute units for AI inference)
- Beyond free: $0.011 per 1,000 neurons
- Workers free tier: 100,000 requests/day, 10ms CPU time per request

**ML Inference Suitability:**
- Runs on Cloudflare's edge network (global, ultra-low latency ~10-50ms)
- Supports models from Cloudflare's catalog only — NO custom model uploads
- Available models include: text classification, embeddings, image classification, LLaMA variants
- Cannot deploy custom XGBoost/LightGBM crypto models

**Performance:** Sub-50ms inference for supported models (edge execution)

**Ease of Setup:** 9/10 — dead simple, zero DevOps

**Critical Limitation for This Project:** Cannot upload custom models. Cloudflare Workers AI is only useful for sentiment analysis (using their pre-built NLP models) as a supplementary signal, NOT for our core crypto ML models.

**Best Use Case:** Free sentiment scoring of crypto news headlines — call their text-classification model as a feature input to our main model.

---

### 3.4 RunPod Serverless (Recommended for Custom Models)

**Pricing:** Per-second billing, flex workers scale to zero
- RTX 4090 serverless: ~$0.00050/second (~$0.30/hr equivalent at full utilization)
- T4 serverless: ~$0.00016/second

**For Our Use Case (signal generation every 30 min):**
- Each inference call: ~2-5 seconds of GPU compute
- At 48 calls/day × 5 seconds × $0.00050/sec = **$0.12/day = ~$3.60/month**
- Scales to zero when not in use — no idle cost

**Best Use Case:** Deploy our trained XGBoost/LightGBM model as a RunPod serverless endpoint. GitHub Actions calls the endpoint, gets signal, writes to JSON. Total cost: ~$4/month.

---

## Section 4: GitHub Actions for ML — Detailed Limits

| Parameter | Limit | Impact on Crypto ML |
|-----------|-------|---------------------|
| Max job timeout | 6 hours | Fine — all our jobs are under 15 min |
| Max workflow runtime | 35 days | Irrelevant |
| RAM (standard runner) | 7 GB | Tight for large datasets; use chunking |
| Disk (standard runner) | 14 GB | Enough for current models |
| CPU cores | 2 | Fine for sklearn/XGBoost inference |
| GPU (free tier) | None | Must use external for training |
| Concurrent jobs (free) | 20 | More than enough |
| Private repo minutes | 2,000/month | ~33 hours; our 30-min workflows use ~1,440 min/month |
| Public repo minutes | Unlimited | Use public repos for all workflows |
| Artifact storage | 500 MB free | Sufficient for model files |
| Artifact retention | 90 days | Fine |
| Cache storage | 10 GB | Good for pip dependencies |
| Self-hosted runner fee (2026) | $0.002/min | Applies even to self-hosted from March 2026 |

**GPU Runners (Paid):**
- T4 GPU runner: available, ~$0.07/min ($4.20/hr)
- Not cost-effective vs RunPod/Vast.ai for training — use external for GPU work

**Key Insight:** For public repositories (which this project is), GitHub Actions minutes are effectively unlimited. All scheduled workflows should be in the public repo to maximize free compute.

---

## Section 5: Free Data Storage for ML Artifacts

### 5.1 GitHub Releases (Recommended for Model Artifacts)

- File size: up to 2 GB per release asset
- Total storage: no documented hard limit (practical limit ~10 GB)
- Cost: free for public repos
- Access: direct URL download — perfect for GitHub Actions to fetch models
- Versioning: built-in via release tags

**Best Use Case:** Store trained model `.pkl`, `.json`, or `.joblib` files as GitHub Release assets. Actions workflow downloads the latest release before inference.

---

### 5.2 Hugging Face Model Hub

**Free Tier (Public Repos):**
- Unlimited storage for public model repositories
- File size: recommended under 20 GB per file; enforces Git LFS for files over 10 MB
- Storage backend: switched from Git LFS to Xet (chunk-level deduplication) as of May 2025
- Bandwidth: generous (CDN-backed, designed for large model downloads)
- Private repos: 1 TB storage per seat on Team/Enterprise plans

**Cost:** Free for public model repos

**Performance:** Excellent — CDN-backed global download, faster than S3 for model weights due to Xet deduplication

**Ease of Setup:** 8/10 — `huggingface_hub` Python library, `HfApi.upload_file()`

**Limitations:**
- Public models are visible to all — do not upload proprietary trading logic embedded in model weights
- Requires HF account + access token for upload
- Not suitable for storing raw market data (use S3 or GitHub LFS for that)

**Best Use Case:** Store trained ensemble models. Push after each retraining run from Kaggle/RunPod. GitHub Actions pulls model file for inference.

---

### 5.3 GitHub LFS

- Free tier: 1 GB storage, 1 GB bandwidth/month
- Additional packs: $5/month for 50 GB storage + 50 GB bandwidth

**Verdict:** Too limited for ML artifacts. Use GitHub Releases or Hugging Face Hub instead.

---

### 5.4 AWS S3

- Free tier (always): 5 GB, 20K GETs, 2K PUTs
- Beyond free: $0.023/GB/month (Standard storage)
- For our model sizes (~50-500 MB), S3 free tier handles everything indefinitely

**Best Use Case:** Store historical OHLCV datasets, backtesting results, and model artifacts if already using AWS.

---

## Section 6: Cost Comparison — ML Pipeline Execution

| Platform | Free Compute | Cost After Free | Suitability | Our Use |
|----------|-------------|-----------------|-------------|---------|
| GitHub Actions (public repo) | Unlimited CPU | $0 (public) | Scheduling, inference, pipelines | PRIMARY |
| Kaggle Notebooks | 30 GPU hrs/week | $0 | Weekly model retraining | RECOMMENDED |
| Google Colab Free | ~15-30 GPU hrs/week | $9.99/mo (Pro) | Ad-hoc training | BACKUP |
| AWS Free Tier | 2 months trial | Expensive after trial | Not recommended | AVOID |
| RunPod Serverless | $0 (pay per use) | ~$0.30/hr per GPU | Inference endpoint | UPGRADE PATH |
| Vast.ai | $0 (pay per use) | $0.24-0.60/hr RTX4090 | Burst training | UPGRADE PATH |
| Lambda Labs | $0 (pay per use) | $0.60/hr A10 | Reliable training | PREMIUM OPTION |

**Monthly Cost Estimate for Our Current Stack (All Free):** $0

**Monthly Cost Estimate for Recommended Upgrade Stack:**
- GitHub Actions (scheduling + pipelines): $0 (public repo)
- Kaggle (weekly retraining, T4/P100): $0
- RunPod Serverless (inference endpoint for 48 signals/day): ~$3.60/month
- Hugging Face (model storage): $0
- Supabase (signal database): $0
- UptimeRobot (monitoring): $0
- **Total: ~$3.60-5/month**

---

## Section 7: Free Monitoring and Alerting

### 7.1 UptimeRobot

**Free Tier:**
- 50 monitors free
- 5-minute check interval (paid plans allow 1-minute)
- Monitors: HTTP(s), keyword, ping, port
- Alerts: email, SMS, Slack, Telegram, webhook
- Status page: 1 free public status page

**Setup:** 9/10 — set up in 2 minutes, no code required

**Best Use Case for This Project:**
- Monitor GitHub Pages alpha dashboard URL (every 5 min)
- Monitor JSON data feed freshness (keyword check for timestamp)
- Alert via Telegram if signal pipeline fails

**Limitation:** 5-minute interval on free tier — not suitable for sub-minute monitoring of live trading execution (but fine for our 30-min scheduled pipelines).

---

### 7.2 Grafana Cloud

**Free Tier (Forever Free Plan):**
- Metrics: 10,000 series, 14-day retention
- Logs: 50 GB/month
- Traces: 50 GB/month
- Profiles: 50 GB/month
- Dashboards: unlimited
- Alerts: unlimited alerting rules
- 50,000 frontend observability sessions

**Cost:** $0 for the forever-free plan

**Integration Pattern:**
```
GitHub Actions → Pushes metrics via Prometheus remote_write → Grafana Cloud
                     ↓
              Dashboard shows: signal count, win rate, last update time
                     ↓
              Grafana Alert → PagerDuty/Slack/Email if metrics drop
```

**Ease of Setup:** 6/10 — requires Prometheus setup or Grafana Agent; more complex than UptimeRobot

**Best Use Case:** Rich dashboarding for model performance over time (win rate trends, signal frequency, data freshness). Combine with UptimeRobot for simple uptime checks.

---

### 7.3 GitHub Actions Native Alerting

- Job failure notifications: built-in, email alerts on workflow failure
- Cost: $0
- Setup: automatic — GitHub emails on failure

**Best For:** Primary failure alerting. GitHub already emails when our scheduled workflows fail. No additional setup needed.

---

## Section 8: Database Options for Trade/Signal Storage

### 8.1 SQLite (Current Approach — Recommended)

**Cost:** $0 (file-based, no server)

**Current Usage in This Project:** `kimi_trading.db`, `signal_tracker.db`, `model_health.db` — all SQLite

**Performance:**
- Handles millions of rows easily at our scale (thousands of signals/day)
- Read performance: excellent for time-series queries
- Write performance: adequate for sequential signal writes
- Not suitable for concurrent multi-process writes (use WAL mode: `PRAGMA journal_mode=WAL`)

**Persistence Strategy:**
- Option A: Commit DB file to git (currently doing this — works for small DBs under 100 MB)
- Option B: Store DB in GitHub Releases (for larger historical datasets)
- Option C: Use DuckDB for analytics queries on parquet files

**Recommendation:** Stay with SQLite + WAL mode. For large historical datasets, switch to DuckDB + parquet files stored on Hugging Face.

---

### 8.2 Supabase (Postgres as a Service)

**Free Tier:**
- 500 MB database storage
- 1 GB file storage
- 50,000 MAU (monthly active users)
- Unlimited API requests
- Real-time subscriptions included
- Auto-pauses after 7 days of inactivity (free tier) — CRITICAL LIMITATION

**Cost:** Free tier; Pro plan $25/month

**Performance:** Full PostgreSQL — row-level security, real-time subscriptions, REST API auto-generated

**Ease of Setup:** 8/10 — dashboard-based, Python client library `supabase-py`

**Best Use Case for This Project:**
- Store active signals with real-time dashboard updates
- Enable live dashboard that auto-refreshes when new signals are written
- The 7-day auto-pause is solved by our GitHub Actions pinging the DB daily

**Limitation:** 500 MB storage is tight for large historical datasets. Use Supabase for active signals only; archive historical data to DuckDB/parquet on HF.

---

### 8.3 Turso (SQLite at the Edge)

**Free Tier:**
- 5 GB storage
- 100 databases
- 500 million row reads/month
- 25 million row writes/month

**Cost:** $0 (free tier); $29/month (Scaler)

**Why It Matters:** Turso is libSQL (SQLite fork) distributed globally. You get SQLite's simplicity with cloud hosting and edge replication. No auto-pause like Supabase.

**Best Use Case:** Drop-in replacement for our SQLite files with zero migration cost and cloud access from any GitHub Actions runner.

---

### 8.4 PlanetScale (MySQL-compatible)

**Status (2025):** PlanetScale removed its free tier. Minimum $34/month.

**Verdict:** Not suitable for our budget. Skip entirely.

---

### 8.5 Neon (Serverless Postgres)

**Free Tier:**
- 512 MB storage
- Unlimited databases
- Serverless autoscaling (scales to zero)
- No auto-pause like Supabase

**Cost:** Free tier; $19/month (Launch plan)

**Best Use Case:** Lightweight alternative to Supabase for signal storage without auto-pause concern.

---

## Section 9: Free API Services for Crypto ML

### 9.1 CoinGecko API

**Free Tier (Demo API):**
- Rate limit: 5-15 calls/minute (throttled, exact limit unpublished but community-reported as ~10-30 calls/minute)
- Data: prices, market cap, volume, historical OHLCV (daily only on free), coin list, trending
- Authentication: API key required (free demo key available)
- No guaranteed SLA

**Paid Plans:**
- Analyst: ~$129/month — 500K calls/month, 500 calls/minute
- Pro: ~$499/month — 2M calls/month

**Performance:** Reliable data, good historical depth (years of daily OHLCV), good coin coverage (10,000+ coins)

**Limitations for ML:**
- Free tier lacks minute/hourly OHLCV — must use Binance API for granular data
- Rate limits make bulk historical collection slow on free tier
- No futures/perp data (use Binance API for funding rates)

**Best Free Alternative:** For price data, use Binance public REST API (no key required for public endpoints, generous rate limits).

---

### 9.2 Alternative.me Fear & Greed Index

**API:** `https://api.alternative.me/fng/` — fully free, no authentication required

**Data:**
- Current F&G index value (0-100)
- Historical values (any date range via `limit` parameter)
- Updates daily

**Rate Limits:** No documented limits — appears to be unauthenticated and generous

**Usage in This Project:** Already integrated in `vix_spike_reversal.py` and `onchain_strategies.py`. Keep using — it's a valuable free signal.

**Example:**
```
GET https://api.alternative.me/fng/?limit=30&format=json
```

---

### 9.3 blockchain.info / Blockchain.com API

**API:** `https://blockchain.info/q/` — free, no authentication for public endpoints

**Data:**
- Hash rate
- Difficulty
- Miner revenue
- Transaction count (used as NVT proxy in our `nvt_overvaluation` strategy)
- BTC price (secondary source)

**Rate Limits:** Moderate — community-reported as ~100 calls/minute on public endpoints

**Usage in This Project:** Already used in `onchain_strategies.py` for hash ribbon and NVT calculations. Continue using.

---

### 9.4 FRED (Federal Reserve Economic Data)

**API:** `https://api.stlouisfed.org/fred/series/observations` — free with API key

**Data:**
- Federal Reserve balance sheet (WALCL) — used in Hayes Liquidity Index
- Reverse Repo (WLRRAL), TGA (WTREGEN)
- VIX (VIXCLS)
- Dollar Index (DTWEXBGS)

**Rate Limits:** 120 calls/minute, 1,000 calls/day on free tier

**Usage in This Project:** Used in `onchain_strategies.py` for `hayes_liquidity_index`. Essential free macro signal.

---

### 9.5 Binance Public REST API

**Cost:** Free, no authentication for public endpoints

**Data:**
- Spot OHLCV (1m, 3m, 5m, 15m, 30m, 1h, 4h, 1d — all timeframes)
- Order book depth (up to 5000 levels)
- Funding rates (perpetual contracts)
- Open interest
- Liquidation data

**Rate Limits:** 1,200 requests/minute (weight-based), very generous

**Best For:** Primary market data source for all crypto ML features. Replace CoinGecko for OHLCV — it's faster, more granular, and rate limits are better.

---

### 9.6 CryptoCompare / CoinDesk API

**CryptoCompare Free:**
- 100,000 calls/month
- Hourly and daily OHLCV, social data, blockchain data
- Good for multi-exchange aggregated data

**CoinDesk (news API):**
- Free access to news headlines and articles
- Useful for sentiment feature engineering

---

## Section 10: Budget ML Stack for Solo Developers ($0-50/Month)

### Tier 0: Pure Free Stack ($0/month)

| Component | Service | Notes |
|-----------|---------|-------|
| Compute (scheduling) | GitHub Actions (public repo) | Unlimited minutes |
| Compute (training) | Kaggle Notebooks | 30 GPU hrs/week |
| Data | Binance API + Alternative.me + FRED | All free |
| Storage (models) | Hugging Face Hub (public) | Unlimited |
| Storage (signals) | SQLite committed to git | Works up to ~100 MB |
| Inference | GitHub Actions CPU (sklearn/XGBoost) | 2-core, 7 GB RAM |
| Monitoring | UptimeRobot (50 monitors) | 5-min checks |
| Alerting | GitHub Actions email on failure | Built-in |
| Database | Turso free tier | 5 GB, SQLite-compatible |

**Total: $0/month**

**Limitations:** Training only via manual Kaggle runs, no real-time inference endpoint, no GPU for inference.

---

### Tier 1: Minimal Upgrade ($5-15/month)

Add to Tier 0:
- **RunPod Serverless inference endpoint** (~$4-5/month for 48 signals/day at GPU speed)
- OR **Vast.ai burst training** ($5-10/month for 2-4 training runs/month at 2hr each on RTX 4090)
- **Supabase** for real-time signal dashboard ($0 — free tier, ping daily to avoid auto-pause)

**Total: ~$5-15/month**

**What This Buys:** GPU-speed inference for complex models, persistent cloud DB, richer dashboard.

---

### Tier 2: Serious Solo Trader ($25-50/month)

- **Kaggle**: $0 (free — covers weekly retraining)
- **RunPod Serverless** (inference + occasional training): ~$10-15/month
- **Vast.ai** (monthly deep retraining): ~$5-10/month
- **Grafana Cloud** (rich monitoring): $0 (free tier)
- **Supabase Pro** (if more storage needed): $25/month (OR stay on free + Turso)
- **CoinGecko Demo API**: $0 (supplement with Binance)

**Total: $15-50/month (depending on Supabase choice)**

**What This Buys:** Full GPU training pipeline, serverless inference, monitoring dashboards, reliable DB.

---

## Top 5 Recommendations for Our System

### Current State Assessment
The project runs 100+ strategies on GitHub Actions free tier, with SQLite for persistence, public JSON files for signal delivery, and Binance/Alternative.me/FRED for data. This is already an excellent $0/month architecture. The primary bottlenecks are:

1. No GPU for training — model complexity is constrained to CPU-friendly algorithms
2. SQLite in git is approaching scalability limits as historical data grows
3. No real-time inference endpoint — all inference happens at scheduled 30-min intervals
4. No structured monitoring beyond GitHub Actions email alerts

---

### Recommendation 1: Kaggle Notebooks for Weekly Retraining (Free — Implement Now)

**What:** Move all model retraining (XGBoost, LightGBM, Random Forest) from GitHub Actions CPU runners to Kaggle Notebooks GPU environment.

**Why:** Kaggle provides 30 GPU hours/week free, background execution continues if browser is closed, P100/T4 GPU is 10-20x faster than our current 2-core CPU runner for training. This allows moving from shallow models to gradient boosting ensembles with 500+ features without cost.

**Implementation:**
1. Create Kaggle dataset with historical OHLCV + features CSV
2. Create training notebook using `kaggle-notebook-api` to trigger remotely
3. Upload trained model to Hugging Face Hub post-training
4. GitHub Actions inference step fetches model from HF Hub before generating signals

**Cost:** $0
**Impact:** 10-20x faster training, enables deeper models, enables hyperparameter search

---

### Recommendation 2: Turso for Signal Database (Free — Implement Now)

**What:** Migrate from SQLite files committed to git to Turso (libSQL cloud-hosted SQLite).

**Why:** Turso gives us cloud-accessible SQLite (no schema migration, same queries) with 5 GB free storage, no auto-pause (unlike Supabase free tier), and global edge reads. Our dashboard can query live signal data directly without committing DB files to the repo.

**Implementation:**
1. `pip install libsql-client` — same API as SQLite
2. Create Turso database at `turso.tech` (free)
3. Update all SQLite connection strings to use libSQL URL
4. Store Turso auth token in GitHub Secrets

**Cost:** $0
**Impact:** Clean separation of data from code, enables web dashboard to read live signals, removes git DB commits

---

### Recommendation 3: RunPod Serverless Inference Endpoint (~$4-5/month — Implement When Models Outgrow CPU)

**What:** Deploy our best-performing trained models as RunPod Serverless GPU endpoints.

**Why:** Our current inference runs on 2-core GitHub Actions CPU. For complex ensemble models or when we add neural network components, inference latency on CPU becomes prohibitive. RunPod Serverless scales to zero — we only pay per inference call (~$0.30/hr GPU equivalent, ~$0.00050/second).

**Implementation:**
1. Package model + inference script in Docker image
2. Push to Docker Hub or RunPod's registry
3. Create Serverless endpoint in RunPod dashboard
4. GitHub Actions calls `POST https://api.runpod.ai/v2/{endpoint_id}/run` with market features
5. Poll for result and write to `active_picks.json`

**Cost:** ~$3.60-5/month at current signal frequency
**Impact:** 5-10x faster inference, enables neural models, enables real-time signal generation

---

### Recommendation 4: UptimeRobot + GitHub Actions Failure Alerts (Free — Implement Now)

**What:** Set up UptimeRobot monitoring for the GitHub Pages alpha dashboard and JSON data feeds, plus verify GitHub Actions email alerts are enabled.

**Why:** Currently no external monitoring — if a workflow silently fails or produces stale data, there is no immediate alert. UptimeRobot can check the JSON feed timestamp hourly and alert via Telegram if the data is older than 2 hours.

**Implementation:**
1. Create UptimeRobot account (free)
2. Add keyword monitor: `https://raw.githubusercontent.com/.../active_picks.json` — check for today's date string
3. Set alert: Telegram webhook if keyword not found
4. Add status page for the alpha engine dashboard

**Cost:** $0
**Impact:** Immediate detection of pipeline failures, removes manual checking

---

### Recommendation 5: Vast.ai for Monthly Deep Retraining ($5-15/month — Implement When Scale Warrants)

**What:** Use Vast.ai marketplace to rent an RTX 4090 for 2-4 hours/month for comprehensive model retraining across all 100+ strategies with full hyperparameter optimization.

**Why:** Kaggle's 30 GPU hours/week is sufficient for routine weekly retraining, but deep hyperparameter search across all strategies with cross-validation requires more sustained compute. An RTX 4090 at $0.35/hr for 4 hours = $1.40 for a full monthly deep retrain. Scale to $10-15/month for aggressive monthly research cycles.

**Implementation:**
1. Create `vast_train.sh` script that: rents cheapest available RTX 4090, copies training data via SSH, runs training, downloads models to Hugging Face Hub, terminates instance
2. Trigger from GitHub Actions on the 1st of each month
3. Store Vast.ai API key in GitHub Secrets

**Cost:** $1.40-15/month depending on run frequency
**Impact:** Enables comprehensive hyperparameter optimization, prevents model staleness, supports 500+ feature sets

---

## Priority Implementation Order

```
Week 1 (Cost: $0):
  1. Set up UptimeRobot monitoring (2 hours)
  2. Create Kaggle training notebook template (4 hours)
  3. Enable Turso for signal storage (3 hours)

Week 2-3 (Cost: $0):
  4. Migrate model artifacts to Hugging Face Hub (2 hours)
  5. Wire Kaggle training output → HF Hub → GitHub Actions inference (4 hours)

Month 2 (Cost: ~$5/month if warranted):
  6. Deploy RunPod Serverless inference endpoint (6 hours)
  7. Set up Vast.ai automated monthly deep retrain (4 hours)

Month 3+ (Cost: ~$15-50/month if scale warrants):
  8. Add Grafana Cloud dashboarding for model health metrics
  9. Evaluate Supabase for real-time signal feed to web dashboard
```

---

## References and Sources

- [GitHub Actions Usage Limits Documentation](https://docs.github.com/en/actions/administering-github-actions/usage-limits-billing-and-administration)
- [GitHub Actions Pricing Changes 2026 — DevOps Geek](https://devops-geek.net/devops-lab/github-actions-pricing-changes-2026-what-devops-geeks-need-to-know/)
- [GPU Hosted Runners GA — GitHub Changelog](https://github.blog/changelog/2024-07-08-github-actions-gpu-hosted-runners-are-now-generally-available/)
- [H100 Rental Prices Compared — IntuitionLabs](https://intuitionlabs.ai/articles/h100-rental-prices-cloud-comparison)
- [Top Cloud GPU Providers 2026 — RunPod](https://www.runpod.io/articles/guides/top-cloud-gpu-providers)
- [Cheapest Cloud GPU Providers — Northflank](https://northflank.com/blog/cheapest-cloud-gpu-providers)
- [RunPod Serverless Pricing](https://docs.runpod.io/serverless/pricing)
- [Vast.ai GPU Marketplace Pricing](https://vast.ai/)
- [Lambda Labs AI Pricing](https://lambda.ai/pricing)
- [Google Colab FAQ](https://research.google.com/colaboratory/faq.html)
- [Free GPU Services Comparison 2025 — GMI Cloud](https://www.gmicloud.ai/blog/best-free-gpu-trials-for-online-deep-learning-2025-guide)
- [AWS Lambda Cold Start Optimization 2025 — Zircon](https://zircon.tech/blog/aws-lambda-cold-start-optimization-in-2025-what-actually-works/)
- [Serverless ML Inference Cost Comparison 2025](https://prateekvishwakarma.tech/blog/serverless-ml-inference-costs/)
- [AWS Lambda vs GCP Cloud Functions Comparison — Modal](https://modal.com/blog/aws-lambda-vs-google-cloud-functions-article)
- [Cloudflare Workers AI Pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/)
- [Cloudflare Workers AI Limits](https://developers.cloudflare.com/workers-ai/platform/limits/)
- [Hugging Face Hub Storage Limits](https://huggingface.co/docs/hub/en/storage-limits)
- [Hugging Face Xet Storage Backend (May 2025)](https://huggingface.co/docs/hub/en/storage-backends)
- [AWS SageMaker Pricing](https://aws.amazon.com/sagemaker/pricing/)
- [Supabase Review 2026 — Hackceleration](https://hackceleration.com/supabase-review/)
- [Turso Free Tier — LogRocket](https://blog.logrocket.com/11-planetscale-alternatives-free-tiers/)
- [PlanetScale Alternatives — DB Pro](https://www.dbpro.app/blog/planetscale-alternatives)
- [CoinGecko API Pricing](https://www.coingecko.com/en/api/pricing)
- [Alternative.me Fear & Greed API](https://alternative.me/crypto/api/)
- [UptimeRobot Free Monitoring](https://uptimerobot.com/)
- [Grafana Cloud Free Forever Plan](https://grafana.com/grafana/dashboards/9955-uptime-robot/)
- [Budget GPU Providers for Indie Developers — ThunderCompute](https://www.thundercompute.com/blog/budget-gpu-providers-indie-developers)
- [Top Serverless GPU Clouds 2026 — RunPod](https://www.runpod.io/articles/guides/top-serverless-gpu-clouds)

---

*Researcher ID: 023 | Dr. Emily Carter | Status: COMPLETE | Date: February 24, 2026*
*Next Review: May 2026 (pricing landscape changes rapidly)*
