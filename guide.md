# guide.md – Coding & Architecture Guide for Cursor

This document explains **how Cursor must implement and structure the Fresh Product Replenishment Manager project**.

The main goals:

- Use **Python** as the primary language.
- Use a **microservices-style architecture**, not a monolith.
- Ensure code is **clean, typed, tested, and configurable** via environment variables and config files.
- Keep everything reproducible with **virtual environments**.

Cursor must always respect this guide together with `project.md` and `task.md`.

---

## 1. Global Principles

1. **Single source of truth**  
   - `project.md` defines the **vision & architecture**.  
   - `task.md` defines the **task backlog**.  
   - `guide.md` defines **how** to code and structure things.
   - Cursor must **not** create new components that contradict these documents.

2. **Microservices, not a monolith**  
   - Each major responsibility (ingestion, forecasting, replenishment, APIs, dashboards) is a **separate service/module**.
   - Services communicate via **HTTP APIs or clearly defined Python interfaces**, not via random cross-imports.
   - See Section 3.3 for detailed service communication patterns.

3. **Python only for backend + data**  
   - Main stack: **Python 3.10+**  
   - If a frontend is needed (e.g. React), it should live in its **own directory** and only talk to backend via HTTP.

4. **Reproducibility & portability**  
   - Always assume the project must run on a new machine with only `git`, `python`, and `pip` available.
   - No hard-coded local paths (like `C:\Users\...` or `/home/...`).

---

## 2. Environment & Dependencies

### 2.1 Python & venv

- The project must use a **virtual environment**:
  - Recommended structure:
    - `python -m venv .venv`
    - Activation documented in `README.md`:
      - Windows: `.\.venv\Scripts\activate`
      - Linux/macOS: `source .venv/bin/activate`
- Cursor must assume all commands are run **inside the venv**.

### 2.2 Dependency Management

- Use either:
  - `requirements.txt` + `pip install -r requirements.txt`, or
  - `pyproject.toml` with `poetry` (only if explicitly added later).
- For now, default to **`requirements.txt`** with pinned versions where necessary.

Recommended base dependencies (Cursor can extend but must keep it reasonable):

- `pandas` or `polars`
- `numpy`
- `scikit-learn`
- `lightgbm`
- `pyarrow`
- `datasets` (HuggingFace)
- `pydantic`
- `pydantic-settings` or similar (for config from env)
- `fastapi`
- `uvicorn`
- `sqlalchemy` (if using relational DB)
- `alembic` (optional, for migrations)
- `python-dotenv` (for loading `.env`)
- `streamlit`
- `pytest`
- `black`, `isort`, `ruff` (or similar style tools)

Cursor must **not** install huge unnecessary libraries without a clear reason.

### 2.3 Configuration Management

- **Configuration hierarchy:**
  - Environment variables (highest priority, for secrets and environment-specific overrides).
  - `config/{env}.yaml` (dev/staging/prod specific configs).
  - `config/config.yaml` (base/default config).
- **Config loading pattern:**
  - Use `pydantic-settings` or similar to load configs.
  - Each service should have its own config model that inherits from base config.
  - Validate configs on startup (fail fast if invalid).
- **Example structure:**
  ```python
  # config/config.yaml
  data:
    dataset_path: "data/raw"
    cache_dir: "data/processed"
  
  models:
    forecasting:
      horizon_days: 7
      model_type: "lightgbm"
  
  # config/dev.yaml (overrides)
  data:
    dataset_path: "data/raw_dev"
  ```

---

## 3. Repository Structure & Microservices

### 3.1 High-Level Layout

Cursor should aim for a structure like:

```text
.
├── apps/
│   ├── streamlit/          # Streamlit analytics dashboard
│   │   └── app.py
│   └── webapp/             # Store/chain manager web app frontend (if different from Streamlit)
│       └── ...
├── services/
│   ├── ingestion/          # Data download & ingestion + preprocessing
│   ├── forecasting/        # Demand forecasting service
│   ├── replenishment/      # Replenishment + markdown policy service
│   ├── reporting/          # KPIs & reporting computations
│   └── api_gateway/        # REST API for frontends (FastAPI)
├── config/                 # YAML/JSON config + settings models
├── data/                   # Local data (gitignored) – e.g. cached HF dataset
├── notebooks/              # EDA & experiments (only exploratory; not production code)
├── tests/                  # pytest-based tests
├── docs/                   # Additional documentation (data dictionary, diagrams)
├── scripts/                # Utility scripts (training, inference, etc.)
├── .env.example            # Sample environment variables
├── requirements.txt
├── README.md
└── guide.md
```

### 3.2 Service Internal Structure

Each service in `services/` should be a Python package with:
- `__init__.py` exposing main public interfaces.
- Clear separation of concerns (data access, business logic, API layer if applicable).
- Service-specific config models.
- Service-specific tests in `tests/unit/{service_name}/`.

**Example service structure:**
```text
services/forecasting/
├── __init__.py              # Exports: ForecastService, ForecastModel
├── models/
│   ├── __init__.py
│   ├── lightgbm_model.py
│   └── baseline_model.py
├── features/
│   ├── __init__.py
│   └── feature_engineering.py
├── evaluators.py
└── config.py                # Service-specific config
```

### 3.3 Service Communication Patterns

**When to use HTTP APIs vs Python interfaces:**

1. **Use HTTP APIs (FastAPI) when:**
   - Services run as separate processes/containers.
   - Services need to scale independently.
   - Services may be deployed on different machines.
   - Example: `api_gateway` → `forecasting` service, `api_gateway` → `replenishment` service.

2. **Use Python interfaces (direct imports) when:**
   - Services are tightly coupled and always run together.
   - Performance is critical (no serialization overhead).
   - Services are in the same process.
   - Example: `forecasting` → `shared/config`, `replenishment` → `shared/database`.

**Service discovery:**
- For HTTP services: use environment variables or config files to specify service URLs.
- Example: `FORECASTING_SERVICE_URL=http://localhost:8001` in `.env`.
- For local development, services can run on different ports and be discovered via config.

**Error handling between services:**
- HTTP services: use standard HTTP status codes, return structured error responses.
- Implement retry logic with exponential backoff for transient failures.
- Use circuit breakers for services that may be unavailable.
- Log all inter-service communication failures.

**Example HTTP service client:**
```python
# shared/clients/forecasting_client.py
import httpx
from typing import Optional

class ForecastingClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def forecast(self, store_id: str, sku_id: str, horizon: int):
        response = await self.client.post(
            f"{self.base_url}/forecast",
            json={"store_id": store_id, "sku_id": sku_id, "horizon": horizon}
        )
        response.raise_for_status()
        return response.json()
```

---

## 4. Testing Strategy

### 4.1 Test Structure

- **Unit tests** (`tests/unit/`): Test individual functions, classes, and modules in isolation.
  - Mock external dependencies (databases, HTTP clients, file system).
  - Aim for >80% code coverage on business logic.
  - Fast execution (< 1 second per test file).

- **Integration tests** (`tests/integration/`): Test service interactions and data flows.
  - Test API endpoints with test database.
  - Test service-to-service communication (can use test doubles).
  - Test end-to-end workflows (e.g., data ingestion → forecasting → replenishment).

- **Test fixtures** (`tests/fixtures/`): Reusable test data and mocks.
  - Sample datasets for testing.
  - Mock service responses.
  - Database fixtures.

### 4.2 Testing Best Practices

- Use `pytest` as the test framework.
- Use `pytest.fixture` for shared test setup.
- Use `pytest.mark.parametrize` for testing multiple scenarios.
- Test both happy paths and error cases.
- Use descriptive test names: `test_forecast_returns_positive_values_for_valid_input`.

**Example test structure:**
```python
# tests/unit/forecasting/test_models.py
import pytest
from services.forecasting.models.lightgbm_model import LightGBMForecastModel

def test_lightgbm_model_initialization():
    model = LightGBMForecastModel()
    assert model is not None

@pytest.mark.parametrize("horizon", [1, 7, 14])
def test_forecast_horizon(horizon):
    model = LightGBMForecastModel()
    # Test implementation
```

### 4.3 Testing Microservices

- **Isolated service tests:** Each service should be testable without other services running.
- **Service mocking:** Use `responses` library or `httpx` mocking for HTTP service calls.
- **Database testing:** Use in-memory SQLite or test database containers for integration tests.
- **Test data management:** Use factories or fixtures to generate test data.

---

## 5. Logging & Observability

### 5.1 Logging Standards

- **Structured logging:** Use JSON format for production, human-readable for development.
- **Log levels:** Use appropriate levels:
  - `DEBUG`: Detailed information for diagnosing problems.
  - `INFO`: General informational messages (service start, request received).
  - `WARNING`: Warning messages (deprecated features, recoverable errors).
  - `ERROR`: Error messages (exceptions, failed operations).
  - `CRITICAL`: Critical errors (service cannot continue).

- **Log format:** Include:
  - Timestamp (ISO 8601).
  - Service name.
  - Log level.
  - Message.
  - Context (request ID, user ID, store ID, etc.).

**Example logging setup:**
```python
# shared/logging/setup.py
import logging
import json
from datetime import datetime

def setup_logging(service_name: str, log_level: str = "INFO"):
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, log_level))
    
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger
```

### 5.2 What to Log

- **Service lifecycle:** Start, stop, configuration loaded.
- **Request/response:** API endpoints (sanitize sensitive data).
- **Model operations:** Training start/end, inference calls, model loading.
- **Errors:** All exceptions with stack traces.
- **Performance:** Slow operations (> 1 second), database query times.
- **Business events:** Order recommendations generated, markdowns applied.

### 5.3 Monitoring & Alerting

- **Metrics to track:**
  - Request rate and latency (for API services).
  - Error rates.
  - Model prediction latency.
  - Database query performance.
  - Resource usage (CPU, memory).

- **Alerting thresholds:**
  - Error rate > 5% over 5 minutes.
  - Service unavailable.
  - Model prediction latency > 10 seconds.
  - Database connection failures.

- **Health checks:** Implement `/health` endpoints for all services.

---

## 6. Error Handling

### 6.1 Error Handling Strategy

- **Custom exceptions:** Define service-specific exceptions in `shared/exceptions.py`.
- **Error responses:** Return structured error responses with appropriate HTTP status codes.
- **Error logging:** Log all errors with context (request ID, user, parameters).
- **Graceful degradation:** Services should handle failures gracefully (fallback to cached data, default values).

**Example custom exceptions:**
```python
# shared/exceptions.py
class ForecastingError(Exception):
    """Base exception for forecasting service."""
    pass

class ModelNotFoundError(ForecastingError):
    """Raised when a model is not found."""
    pass

class InvalidInputError(ForecastingError):
    """Raised when input validation fails."""
    pass
```

### 6.2 Error Handling Patterns

- **Try-except blocks:** Catch specific exceptions, not bare `except:`.
- **Retry logic:** Implement retries for transient failures (network, database).
- **Circuit breakers:** Prevent cascading failures when a service is down.
- **Timeouts:** Set timeouts for all external calls (HTTP, database).

---

## 7. Performance & Scalability

### 7.1 Performance Requirements

- **API response time:** < 500ms for 95th percentile.
- **Forecast generation:** < 2 seconds for a single store-SKU-day.
- **Batch processing:** Process 1000 store-SKU combinations in < 5 minutes.
- **Database queries:** < 100ms for simple queries, < 1 second for complex aggregations.

### 7.2 Optimization Strategies

- **Caching:** Cache model predictions, feature computations, and database queries.
- **Async operations:** Use async/await for I/O-bound operations (HTTP, database).
- **Batch processing:** Process multiple items in batches to reduce overhead.
- **Database indexing:** Index frequently queried columns (store_id, sku_id, date).
- **Lazy loading:** Load data only when needed.

### 7.3 Scalability Considerations

- **Horizontal scaling:** Design services to scale horizontally (stateless services).
- **Database scaling:** Use read replicas for read-heavy workloads.
- **Caching layer:** Use Redis or similar for distributed caching.
- **Load balancing:** Use load balancers for HTTP services.

---

## 8. Security

### 8.1 Authentication & Authorization

- **API authentication:** Use JWT tokens or API keys for service-to-service communication.
- **User authentication:** Implement OAuth2 or similar for user-facing apps.
- **Role-based access control (RBAC):** Enforce permissions based on user roles (store_manager, regional_manager, admin).

### 8.2 Data Security

- **Secrets management:** Never commit secrets to git. Use environment variables or secret management services.
- **Data encryption:** Encrypt sensitive data at rest and in transit (HTTPS, database encryption).
- **Input validation:** Validate and sanitize all user inputs to prevent injection attacks.
- **SQL injection prevention:** Use parameterized queries (SQLAlchemy ORM).

### 8.3 Security Best Practices

- **Dependency scanning:** Regularly update dependencies and scan for vulnerabilities.
- **Rate limiting:** Implement rate limiting on API endpoints to prevent abuse.
- **CORS:** Configure CORS properly for web applications.
- **Security headers:** Set appropriate security headers (X-Content-Type-Options, X-Frame-Options).

---
