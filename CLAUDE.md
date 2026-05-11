# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

All Python commands must use the `UAX` conda environment:

```bash
conda run -n UAX <command>
```

## Common Commands

```bash
# Run all tests (DB-dependent tests auto-skip if Postgres is unreachable)
conda run -n UAX pytest tests/

# Run a single test
conda run -n UAX pytest tests/test_cltv.py::test_cltv_formula_consistency

# Lint with ruff (line-length=100, target py311)
conda run -n UAX ruff check .

# Launch the Streamlit dashboard
conda run -n UAX streamlit run dashboard/app.py

# Launch Jupyter to run notebooks
conda run -n UAX jupyter notebook
```

## Architecture

### Data Flow

```
public (raw) → staging (cleaned) → dwh (star schema)
                                          ↓
                                   notebooks 03–05
                                          ↓
                             data/processed/ + models/
                                          ↓
                                   dashboard/app.py
```

The ETL pipeline is orchestrated by six numbered notebooks that must run in order:

| Notebook | Purpose |
|---|---|
| `00_exploration.ipynb` | Explore raw data in `public` schema |
| `01_etl_staging.ipynb` | Clean and load `public → staging` |
| `02_etl_dwh.ipynb` | Transform `staging → dwh` (dims + facts) |
| `03_cltv_calculation.ipynb` | Compute CLTV per customer → `data/processed/cltv.parquet` |
| `04_customer_metrics.ipynb` | Recency, retention, AOV → `data/processed/customer_metrics.parquet` |
| `05_pca_clustering.ipynb` | PCA + KMeans → `models/customer_segments.parquet` + joblib artifacts |

### Database

PostgreSQL on Docker at `localhost:5433`, database `saleshealth`. Three schemas:
- `public` — raw source tables
- `staging` — cleaned/normalized data
- `dwh` — star schema (`dim_customer`, `dim_product`, `dim_store`, `dim_date`, `dim_return_reason`, `fact_sales`, `fact_returns`)

Connection is managed by `src/db/engine.py` as a singleton SQLAlchemy engine built from `config/settings.py`. Configuration is loaded from `.env` (copy `.env.example` and fill in `DB_USER` / `DB_PASSWORD`).

### Key Modules

- **`config/settings.py`** — Frozen `Settings` dataclass loaded from `.env`. Import the singleton: `from config.settings import settings`.
- **`src/db/engine.py`** — `get_engine()` (singleton), `run_sql()`, `run_sql_file()`, `read_sql()`.
- **`src/etl/load.py`** — `run_sql_directory(dir)` executes `.sql` files in alphabetical order.
- **`src/analytics/cltv.py`** — `compute_cltv(df)` applies `net_revenue × margin_rate × frequency × retention_rate`.
- **`src/analytics/clustering.py`** — `run_pca_kmeans(df, feature_cols, n_clusters, n_components)` returns a `ClusteringResult`; `save_artifacts(result, out_dir)` writes joblib + parquet files to `models/`.

### SQL Conventions

SQL files under `sql/03_transformations/` are prefixed with numbers (`10_`, `20_`, …) and executed in alphabetical order. DDL lives in `sql/02_dwh_schema/`.