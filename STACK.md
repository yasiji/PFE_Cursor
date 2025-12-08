# Project Stack Overview

Detailed breakdown of the technologies and libraries used across this repository.

## Backend (Python / FastAPI)
- **Runtime**: Python 3.10+
- **Framework**: FastAPI (with pydantic v2 models) served by uvicorn.
- **Rate limiting**: slowapi (Starlette middleware pattern).
- **Auth**: JWT via `python-jose[cryptography]`, password hashing via `passlib[bcrypt]`, OAuth2 password flow.
- **Config**: `pydantic-settings` + YAML (`config/config.yaml` with `dev.yaml`/`prod.yaml` overrides), `.env` for secrets, shared loader in `shared/config.py`.
- **Database**: SQLAlchemy 2.x ORM, SQLite by default (`data/replenishment*.db`), alembic listed as dependency (migrations scripts in `scripts/migrations/`).
- **Logging**: structlog, configurable JSON/text formats.
- **HTTP clients**: httpx (sync) for external services.

## Domain Services
- **Forecasting**:
  - Models: LightGBM (`services/forecasting/models/lightgbm_model.py`), baselines (last value, moving average, seasonal naive).
  - Feature engineering: pandas-based lag/rolling/calendar, weather/promo flags (`services/forecasting/features`).
  - Training script: `scripts/train_lightgbm_model.py`; artifacts under `data/models/` or `data/processed/lightgbm_results/`.
  - Evaluation: custom metrics (MAE, RMSE, MAPE, WAPE, bias).
- **Replenishment**:
  - Order-up-to policy with safety stock (`services/replenishment/policy.py`).
  - Markdown policy for near-expiry discounts (`services/replenishment/markdown.py`).
  - Inventory age tracking/expiry buckets (`services/replenishment/expiry.py`).
- **Ingestion**:
  - Data loading from HuggingFace FreshRetailNet-50K or local parquet (`services/ingestion/datasets.py`).
  - Synthetic/raw data stored under `data/raw*`, processed artifacts under `data/processed/`.
- **API Gateway**:
  - REST routes for auth, store inventory/sales/forecasts, orders, prices, notifications, analytics (`services/api_gateway`).
  - Weather factors via Open-Meteo (`weather_service.py`), holidays/demand factors routes present.
  - Notification generation logic (`notification_service.py`).
  - Order handling and recommendations sharing models in `services/api_gateway/models.py`.

## Frontend (Store Manager App)
- **Stack**: React 18 + TypeScript + Vite.
- **UI**: MUI 5 (material), notistack for toasts, recharts for charts.
- **State/async**: Zustand (auth/notifications), React Query for data fetching/caching.
- **Routing**: react-router-dom v6.
- **HTTP**: axios with auth interceptor pointing to FastAPI (`src/services/api.ts`).
- **Build/tooling**: Vite, TypeScript, ESLint (`@typescript-eslint`), npm scripts (`dev`, `build`, `preview`, `lint`).
- **Structure**: `apps/store-manager-frontend/src/` with pages (Dashboard/Forecast/Refill/Inventory/Orders/Products/Analytics/Settings), layout, notification components, and service wrappers.

## Analytics Dashboards
- **Streamlit apps**: `apps/streamlit/app.py` and pages for store view, SKU detail, simulation, ML dashboard, etc.
- **Plotting**: plotly, matplotlib.

## Data & Models
- **Datasets**: FreshRetailNet-50K (HuggingFace); synthetic samples under `data/raw_dev/`.
- **Models**: LightGBM pickles under `data/models/` and `data/processed/lightgbm_results/`.
- **Processed artifacts**: baseline comparisons, simulation results, MVP subset selections under `data/processed/`.

## Scripts & Ops
- **Bootstrap**: `start.bat`, `start_venv.bat`, `start_ngrok.bat`, `start_notifications.bat` (Windows-oriented).
- **DB**: `scripts/init_database.py` to create tables; migrations under `scripts/migrations/`; seeders (`scripts/seed_test_data.py`, `scripts/seed_prices.py`, `scripts/ensure_test_user.py`).
- **Simulation/EDA**: `scripts/run_simulation.py`, `scripts/run_eda.py`, `scripts/show_real_data.py`.
- **Testing utilities**: `scripts/test_api.py` for quick API checks.

## Testing & Quality
- **Frameworks**: pytest, pytest-asyncio, pytest-mock, pytest-cov.
- **Coverage**: unit tests for utilities, forecasting baselines, replenishment policy; integration tests for API endpoints and pipeline (`tests/`).
- **Lint/format**: ruff, black, isort configured via `requirements.txt` and `pytest.ini`.

## Infrastructure & Environment
- **Default DB**: SQLite in `data/`; can be switched via `DATABASE_URL`.
- **Auth**: JWT secret required (`AUTH_JWT_SECRET_KEY`); default dev secret present—must override in prod.
- **CORS**: Controlled via `config`/env; dev allows localhost and ngrok.
- **Env management**: `.env` referenced; config layering uses environment variables with `ENVIRONMENT` (`dev`/`prod`).

## External Integrations
- **Weather**: Open-Meteo (no API key) for forecasts and demand factors.
- **Holidays**: Nager.Date endpoints referenced in analytics routes.
- **Datasets**: HuggingFace `datasets` library for FreshRetailNet-50K with local caching.

## Notable Paths
- Backend services: `services/api_gateway/`, `services/forecasting/`, `services/replenishment/`, `services/ingestion/`, `shared/`.
- Frontend app: `apps/store-manager-frontend/`.
- Analytics: `apps/streamlit/`.
- Config: `config/*.yaml`.
- Data artifacts: `data/` (raw, processed, models).
- Scripts: `scripts/` (init/seed/train/migrations/ops).
