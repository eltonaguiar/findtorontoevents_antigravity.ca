# Crypto Prediction Enhancement Plan

## Goal
Significantly improve cryptocurrency and meme‑coin prediction performance by enriching our data sources, engineering new features, and retraining models.

## Step‑by‑Step Plan

1. **Acquire Existing Data**
   - Obtain `ejaguiar1_memecoin_mar312026.sql` and `ejaguiar1_stocks.sql` from the user.
   - Load them into a temporary SQLite database to inspect schema and sample rows.

2. **Data Exploration**
   - Identify tables, columns, primary keys, and data types.
   - Determine which fields are useful for price prediction (e.g., historical prices, volumes, timestamps).
   - Document any missing attributes (e.g., on‑chain metrics, sentiment).

3. **Gap Analysis & External Data Sources**
   - Based on the schema, list required additional data:
     - Real‑time and historical price/volume (CoinGecko, Nomics).
     - On‑chain activity (Messari, Blockchair).
     - Technical indicators (CryptoCompare).
     - Social sentiment (e.g., Reddit, Twitter APIs – optional).
   - Prioritize APIs that are free, have HTTPS, and support CORS: **CoinGecko**, **Nomics**, **Messari**, **CryptoCompare**, **Blockchair**.

4. **API Mapping**
   - Create a mapping table (`api_field_map.md`) that aligns API response fields to our internal schema (e.g., `price_usd` → `price`, `volume_24h` → `volume`).
   - Note authentication requirements (API keys) and rate limits.

5. **Data‑Ingestion Pipeline**
   - Implement `data_ingest_crypto.py`:
     - Pull data from each API on a scheduled basis.
     - Normalize timestamps to UTC.
     - Upsert rows into our SQLite/PostgreSQL tables.
   - Add error handling and logging.

6. **Feature Engineering**
   - Compute derived features for each asset:
     - Momentum (price change over 1h, 4h, 24h).
     - Volatility (std dev of returns).
     - Volume spikes (z‑score of volume).
     - Transaction fee trends (Blockchair).
     - Network hash‑rate (Messari).
     - Sentiment scores (if available).
   - Store features in a `features` table.

7. **Model Retraining**
   - Update the training script (`train_crypto_model.py`) to include new features.
   - Perform cross‑validation and track performance metrics (RMSE, MAE, Sharpe).
   - Compare against baseline model.

8. **Hyper‑parameter Optimization**
   - Use Optuna or grid search to tune model parameters.
   - Run back‑testing on meme‑coin subsets to ensure robustness.

9. **Documentation**
   - Write `pipeline_documentation.md` covering:
     - Data sources, schema, ingestion schedule.
     - Feature definitions.
     - Model architecture and training process.
   - Include a README for reproducing the pipeline.

10. **Deployment & Monitoring**
    - Containerize the pipeline (Docker) and schedule with cron.
    - Add health checks and alerts for data freshness and model drift.
    - Visualize predictions in the existing dashboard.

## Deliverables
- `crypto_prediction_enhancement_plan.md` (this document)
- `api_field_map.md`
- `data_ingest_crypto.py`
- Updated `train_crypto_model.py`
- `pipeline_documentation.md`
- Dockerfile and deployment scripts

## Next Immediate Action
Await the upload of the two SQL files so we can start step 1.
