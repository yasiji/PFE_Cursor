# Fresh Product Replenishment Manager – project.md

## 1. Vision

Build an end-to-end decision support system that:

1. Predicts daily order quantities for fresh products at store level.
2. Minimizes waste and stockouts while protecting profitability.
3. Exposes the results through:
   - A **Streamlit analytics dashboard** (data/ops side).
   - A **store / chain manager web app** (operational side).

Initial development will use the **FreshRetailNet-50K** dataset from HuggingFace as the main sandbox. The system must be designed so that it can later plug into a real retailer’s data (multiple stores, multiple regions).

---

## 2. Problem Statement

Fresh products (fruits, vegetables, bakery, chilled items, etc.) are highly perishable. Under-ordering causes stockouts and lost sales; over-ordering causes waste and margin erosion. 

We want a model-driven replenishment engine that, for each store–product–day:

- Suggests how much to **order today**.
- Optionally suggests **markdown (discount) actions** for near-expiry stock.
- Ensures shelves stay filled while keeping waste and markdowns under control.

This must be done using not only historical sales, but also:

- Stock levels & expiry structure of current inventory.
- Calendar effects (weekday/weekend, holidays, events).
- Weather (hot/cold, rain, etc.).
- Promotions / discounts.
- Store and product characteristics.

---

## 3. Business Objectives

**Primary objectives (MVP):**

1. **Service level:** Reduce stockouts vs. a simple heuristic baseline (e.g., current manual policy) at the same or lower waste level.
2. **Waste reduction:** Reduce write-offs and near-expiry destruction as a % of sales.
3. **Margin:** Maintain or improve gross margin after markdowns.
4. **Operational usability:** Provide clear, explainable daily order suggestions that managers can trust and override when needed.

**Secondary objectives:**

- Provide a **multi-store, multi-category view** for regional managers.
- Allow simple **scenario simulation** (e.g., “what if next week is +3°C hotter?” or “add a 20% promo on this SKU?”).

---

## 4. Scope

### 4.1 In scope (v1 / MVP)

- Use **FreshRetailNet-50K** as the main development dataset.
- Focus on **daily** replenishment decisions (1–7 day horizon).
- Start with a small subset of:
  - Stores (e.g., 5–10).
  - Fresh categories (e.g., fruits & vegetables).
- Build:
  1. A **replenishment engine** (Python, ML + business rules).
  2. A **Streamlit dashboard** for data/ops.
  3. A **store manager web app** (MVP features: inventory, forecasts, recommended orders, basic KPIs).

### 4.2 Out of scope (for now)

- Real-time intraday ordering (hour-level).
- Full-blown pricing optimization (complex multi-step markdown strategies).
- Integration with actual ERP / WMS / POS systems.
- Multi-tenant SaaS productization (billing, multi-tenant auth, etc.).

These can be future phases.

---

## 5. Users & Use Cases

### 5.1 Personas

1. **Store Manager**
   - Needs: Daily list of products to order, quantities, and any recommended discounts for near-expiry stock.
   - Interaction: Web app (desktop/tablet) every morning.

2. **Chain / Regional Manager**
   - Needs: Aggregated KPIs across stores (waste, service level, sales uplift), spotting “problem” stores or SKUs.
   - Interaction: Web app & Streamlit dashboard.

3. **Data Scientist / Ops Analyst**
   - Needs: Model performance monitoring, error diagnostics, scenario testing, feature importance.
   - Interaction: Streamlit dashboard + notebooks.

### 5.2 Core Use Cases

- **UC1 – Daily Replenishment Plan**
  - Input: store, date (e.g., tomorrow), current stock & expiry profile.
  - Output: order quantity per SKU and suggested markdowns for near-expiry units.

- **UC2 – Store Performance Overview**
  - View past N days for a store: sales, waste, stockouts, service level, margin.

- **UC3 – SKU Deep Dive**
  - For a given store–SKU: trends, forecasts, recommendation history, and actual vs recommended.

- **UC4 – Scenario Simulation**
  - “What if” changes (weather hotter/colder, holiday flags, promo flags) and their impact on recommended orders and expected waste/sales.

---

## 6. Functional Requirements

### 6.1 Replenishment Engine

- Predict **future demand** per store–SKU–day (short horizon).
- Incorporate:
  - Current on-hand stock.
  - In-transit orders.
  - Shelf life / expiry structure.
  - Business rules (min order quantity, case pack sizes, service level target).
- Produce:
  - Recommended **order quantity**.
  - Recommended **markdown actions** for near-expiry stock (discount % and effective date).
- Provide an API/function that can be called for:
  - One store–day (interactive).
  - Batch runs (all stores for next day).

### 6.2 Streamlit Dashboard (data/ops)

- Pages:
  1. **Global Overview**
     - Total sales, waste %, stockout rate, forecast error vs baseline.
  2. **Store View**
     - KPIs per store, ranking, outliers.
  3. **SKU Detail**
     - Time series plots (sales, stock, forecasts).
     - Feature importance / explainability for predictions.
  4. **Simulation / Sandbox**
     - Adjust external conditions (holiday flag, weather bucket, promo flag, discount) and see projected impact.

### 6.3 Store / Chain Manager Web App ✅ **IMPLEMENTED**

- **Authentication** (JWT-based with role-based access: store manager, regional, admin). ✅
- **Store dashboard:** ✅
  - Today's recommended orders (per SKU).
  - Current inventory snapshot (qty by expiry bucket).
  - Near-expiry items and suggested discounts.
  - Store selection (manual or assigned).
  - CSV export functionality.
- **Chain dashboard:** ✅
  - KPIs aggregated across stores and categories.
  - Ability to drill down into a store or SKU.
  - Store rankings and performance metrics.
- **History page:** ✅
  - View past recommendations and overrides.
  - Date range filtering.
- **Settings page:** ✅
  - User information display.
  - API configuration.
- Ability to **export** recommended orders (CSV) to integrate with existing processes. ✅

---

## 7. Data & Features

### 7.1 Core Data Entities

- **Store** (id, city, region, size, etc.).
- **Product / SKU** (id, category, subcategory, unit size, shelf life rules).
- **Sales transactions** (store, SKU, timestamp, quantity sold, price, promo flags).
- **Stock & stockout status** (store, SKU, timestamp, on-hand/balance, stockout indicator).
- **Orders / deliveries** (store, SKU, order date, delivery date, ordered qty).
- **Calendar** (date, weekday, weekend, holiday, special events).
- **Weather** (temperature bucket, precipitation bucket, etc., by store region).
- **Markdown history** (discount %, start date, end date).

For MVP, we adapt these to the structure provided by FreshRetailNet-50K and fill any missing pieces via assumptions or synthetic features.

### 7.2 Feature Families

- **Demand history:** past sales at multiple lags (1, 7, 14, 28 days), moving averages, seasonality.
- **Stock & stockout:** previous stockouts, days since last stockout.
- **Calendar:** weekday, weekend, holiday, month, season.
- **Weather:** temperature buckets, rain/no-rain, extreme heat/cold flags.
- **Price & promo:** regular price, promo flags, discount level.
- **Product & store characteristics:** category, store type, store size proxies.
- **Shelf life:** remaining days before expiry for current inventory, rules per category.

### 7.3 Data Quality & Validation

**Data quality checks:**
- **Completeness:** Check for missing values in critical fields (store_id, sku_id, timestamp, sales).
- **Consistency:** Validate that sales quantities are non-negative, timestamps are in valid ranges.
- **Accuracy:** Detect outliers (e.g., sales > 3 standard deviations from mean).
- **Timeliness:** Ensure data freshness (e.g., sales data should be available within 24 hours).

**Data validation rules:**
- Store IDs must exist in store master data.
- SKU IDs must exist in product master data.
- Timestamps must be in chronological order.
- Stock levels must be non-negative.
- Sales quantities must be non-negative.

**Data quality monitoring:**
- Track data quality metrics over time (missing value rates, outlier rates).
- Alert when data quality degrades below thresholds.
- Document data quality issues and resolutions.

**Handling missing data:**
- For missing weather data: use regional averages or last known value.
- For missing promotions: assume no promotion (flag as false).
- For missing stock levels: use last known value or interpolate.

---

## 8. Modeling Strategy

### 8.1 Latent Demand Recovery (optional but recommended)

- Use stockout information to distinguish between:
  - True zero demand.
  - Censored demand due to stockout.
- Recover a “latent demand” series that is closer to what customers actually wanted, not just what was sold.
- Train forecasting models on recovered demand to reduce systematic underestimation.

### 8.2 Demand Forecasting

- Predict daily demand per store–SKU for the next **H days** (e.g., 1–7).
- Start with:
  - Simple baselines (moving average, last week).
  - At least one ML model (e.g., tree-based or time-series model).
- Evaluate on:
  - **Magnitude accuracy:** MAE/MAPE/WAPE.
  - **Bias:** tendency to systematically under- or over-forecast, which impacts stockouts vs waste.

### 8.3 Replenishment Logic

Define order quantity per store–SKU–day, e.g.:

- Let:
  - `D_hat` = forecasted demand for the target coverage window (e.g., next N days).
  - `I_on_hand` = current on-hand inventory.
  - `I_inbound` = confirmed deliveries arriving before or during window.
  - `U_exp` = units that will expire before or during the window (without markdown).
  - `sigma_D` = forecast uncertainty (standard deviation of forecast error).
  - `z` = safety factor based on target service level (e.g., z=1.65 for 95% service level).
- Basic **order-up-to policy**:

> `order_qty = max(0, target_coverage * D_hat + z * sigma_D - (I_on_hand - U_exp) - I_inbound)`

**Uncertainty handling:**
- Use forecast prediction intervals (e.g., 10th, 50th, 90th percentiles) if available.
- Estimate `sigma_D` from historical forecast errors (MAE or RMSE).
- Adjust safety stock based on:
  - Product criticality (A-class products get higher safety stock).
  - Demand variability (higher variability → higher safety stock).
  - Lead time variability (if applicable).

**Target coverage calculation:**
- `target_coverage` = lead_time + review_period + safety_buffer
- Default: 7 days (1 day lead time + 1 day review + 5 days coverage).
- Adjustable per product category or store.

Then apply:

- Minimum / maximum order constraints.
- Case pack rounding.
- Service-level tuning (e.g., higher safety factor for A-class products).
- Shelf-life constraints (don't order more than can be sold before expiry).

### 8.4 Markdown / Discount Logic for Near-Expiry

- Define **expiry buckets** (e.g., 3 days left, 2 days, 1 day).
- For each bucket, define recommended discount levels per category.
- Estimate the trade-off:
  - Higher discount → more demand, less waste but lower margin.
  - No discount → higher margin but potential write-off.

**Markdown strategy:**
- **Elasticity estimation:** Use historical data to estimate price elasticity:
  - Compare sales during promotional periods vs regular periods.
  - Estimate demand uplift per discount percentage.
- **Rule-based markdowns (MVP):**
  - 3 days before expiry: 20% discount (if inventory > threshold).
  - 2 days before expiry: 35% discount.
  - 1 day before expiry: 50% discount.
  - Category-specific rules (e.g., fruits may need higher discounts than vegetables).
- **Markdown effectiveness tracking:**
  - Track: units sold after markdown, waste reduction, margin impact.
  - Compare actual vs expected demand uplift.
  - Use this data to refine markdown rules over time.
- **Future enhancement:** Implement optimization-based markdowns that maximize expected profit considering demand elasticity and waste costs.

---

## 9. Architecture & Technology

### 9.1 High-Level Architecture ✅ **IMPLEMENTED**

- **Data & Modeling Layer (Python):** ✅
  - Data ingestion from HuggingFace / parquet (`services/ingestion/datasets.py`).
  - Feature engineering & model training scripts (`services/forecasting/`).
  - Replenishment & markdown policy engine (`services/replenishment/`).
- **Serving Layer:** ✅
  - API Gateway (FastAPI) exposing:
    - `/api/v1/forecast` – demand predictions. ✅
    - `/api/v1/replenishment_plan` – order & markdown suggestions. ✅
    - `/health` – health check endpoint. ✅
    - `/api/v1/auth/*` – authentication endpoints (login, register, me). ✅
- **Frontends:** ✅
  - **Streamlit dashboard** (data/ops) - `apps/streamlit/`. ✅
  - **Web app** (store / chain managers) - `apps/webapp/`. ✅
- **Storage:** ✅
  - Training data in parquet/CSV.
  - Results and configurations in SQLite database (`data/replenishment.db`). ✅
  - Model artifacts stored in `data/models/` (versioned). ✅
- **Database Schema:** ✅
  - Tables: users, stores, products, inventory_snapshots, forecasts, recommendations, markdown_history
  - SQLAlchemy ORM models with relationships
  - Database initialization script

**Service communication:**
- API Gateway communicates with forecasting and replenishment services via HTTP.
- Services can also communicate via direct Python interfaces when running in the same process.
- See `guide.md` Section 3.3 for detailed communication patterns.

### 9.1.1 API Contract Definitions

**Forecast Endpoint:**
```
POST /api/v1/forecast
Request:
{
  "store_id": "string",
  "sku_id": "string",
  "horizon_days": integer (1-14),
  "include_uncertainty": boolean (optional)
}
Response:
{
  "store_id": "string",
  "sku_id": "string",
  "forecasts": [
    {
      "date": "YYYY-MM-DD",
      "predicted_demand": float,
      "lower_bound": float (if include_uncertainty=true),
      "upper_bound": float (if include_uncertainty=true)
    }
  ]
}
Error Response:
{
  "error": "string",
  "message": "string",
  "status_code": integer
}
```

**Replenishment Plan Endpoint:**
```
POST /api/v1/replenishment_plan
Request:
{
  "store_id": "string",
  "date": "YYYY-MM-DD",
  "current_inventory": [
    {
      "sku_id": "string",
      "quantity": integer,
      "expiry_date": "YYYY-MM-DD"
    }
  ]
}
Response:
{
  "store_id": "string",
  "date": "YYYY-MM-DD",
  "recommendations": [
    {
      "sku_id": "string",
      "order_quantity": integer,
      "markdown": {
        "discount_percent": float,
        "effective_date": "YYYY-MM-DD",
        "reason": "string"
      } (optional)
    }
  ]
}
```

**API Versioning:**
- Use URL versioning: `/api/v1/`, `/api/v2/`, etc.
- Maintain backward compatibility within a major version.
- Document breaking changes in API changelog.

---

### 9.2 Suggested Tech Stack

- **Language:** Python 3.10+.
- **Data:** pandas / polars, pyarrow, huggingface `datasets`.
- **ML / TS:** scikit-learn, LightGBM, a time-series library if needed.
- **API:** FastAPI.
- **Dashboards:** Streamlit.
- **DB:** SQLite for local dev; PostgreSQL in a more serious environment.
- **Orchestration (optional):** simple Makefile + scheduled scripts; upgrade later to Prefect/Airflow if needed.
- **HTTP Client:** httpx (for async HTTP requests between services).
- **Testing:** pytest, pytest-asyncio, pytest-mock.
- **Logging:** structlog or python-json-logger (for structured logging).

### 9.3 Deployment Strategy

**Development Environment:**
- Run all services locally (same machine, different ports).
- Use SQLite for database.
- Use file-based storage for models and data.

**Production Environment (Future):**
- **Containerization:** Use Docker containers for each service.
- **Orchestration:** Use Docker Compose for local deployment, Kubernetes for production (future).
- **Database:** PostgreSQL with connection pooling.
- **Caching:** Redis for caching forecasts and feature computations.
- **Load Balancing:** Use nginx or cloud load balancer for API Gateway.
- **Monitoring:** Integrate with monitoring tools (Prometheus, Grafana, or cloud-native solutions).

**Deployment Process:**
1. Build and test services.
2. Run integration tests.
3. Build Docker images (if containerized).
4. Deploy to staging environment.
5. Run smoke tests.
6. Deploy to production (blue-green or rolling deployment).
7. Monitor for errors and rollback if needed.

**Rollback Strategy:**
- Maintain previous model versions in `data/models/`.
- Keep database migration scripts for rollback.
- Use feature flags to disable new features if issues arise.
- Document rollback procedure in `docs/deployment.md`.

---

## 10. KPIs & Evaluation

### 10.1 Forecast Metrics

- MAE / RMSE per store–SKU.
- MAPE / WAPE at:
  - SKU level.
  - Category level.
  - Store level.
- Bias metrics:
  - Average signed error (tendency to over/under-stock).

### 10.2 Inventory & Business Metrics

- **Service level:** % of demand fulfilled (no stockout).
- **Stockout rate:** % of days with stockout per SKU.
- **Waste %:** write-off quantity / total received quantity.
- **Gross margin after markdowns.**
- **GMROII** (optional): Gross margin return on inventory investment.

---

## 11. Roadmap & Milestones

**Milestone 0 – Setup & EDA** ✅ **COMPLETE**

- Repo + environment created.
- Dataset understood, basic EDA done, first plots produced.
- ✅ **Status:** Completed - Repository structure, configuration, logging, and comprehensive EDA completed.

**Milestone 1 – Baseline Forecast & Simple Replenishment** ✅ **COMPLETE**

- Baseline forecasting models implemented and evaluated.
- Simple replenishment policy using forecasts.
- First offline simulation comparing baseline vs current heuristics.
- ✅ **Status:** Completed - LightGBM model (33.7% MAE improvement), Order-up-to policy, markdown rules, simulation framework.

**Milestone 2 – Latent Demand Recovery & Improved Forecast** ⏭️ **DEFERRED**

- Demand recovery model trained (optional but recommended).
- Forecast accuracy and bias improved vs baseline.
- ✅ **Status:** Deferred for MVP - LightGBM performs well on raw sales data. Can be added in future phase.

**Milestone 3 – Streamlit Analytics Dashboard** ✅ **COMPLETE**

- End-to-end pipeline: data → model → KPIs/plots in Streamlit.
- Scenario simulation page implemented.
- ✅ **Status:** Completed - 4-page dashboard (Global Overview, Store View, SKU Detail, Simulation) with full data integration.

**Milestone 4 – Store/Chain Web App (MVP)** ✅ **COMPLETE**

- Basic login & roles.
- Store dashboard with daily recommendations.
- Export functionality (CSV/Excel).
- ✅ **Status:** Completed - FastAPI backend with JWT auth, SQLite database, Streamlit web app with role-based dashboards, CSV export.

**Milestone 5 – Stabilization & Documentation** 🔄 **IN PROGRESS**

- Refactoring, tests, configuration cleanup.
- User documentation for managers and technical documentation for developers.
- ✅ **Status:** Partially Complete - Comprehensive test suite (51+ tests), integration tests, API tests. Documentation in progress (Phase 8).

---

## 12. Risks & Assumptions

**Assumptions:**

- FreshRetailNet-50K has enough coverage of promotions, weather, and stock status to model realistic behavior.
- We can approximate shelf life rules and markdown behavior from available fields or simple assumptions.

**Risks:**

- **Data mismatch:** Future real retailer data may differ significantly, requiring re-mapping and extra engineering.
- **Model complexity vs explainability:** Highly complex models may be difficult for managers to trust.
- **Over-optimization on this dataset:** Risk of overfitting project design to the structure of FreshRetailNet-50K rather than generalizing.

Mitigation: keep modeling pipeline modular and configurable; separate dataset-specific mapping from core logic.

---

## 13. Performance Requirements

### 13.1 Response Time Targets

- **API endpoints:**
  - Forecast endpoint: < 500ms (95th percentile).
  - Replenishment plan endpoint: < 1 second (95th percentile).
  - Health check: < 50ms.

- **Batch processing:**
  - Daily forecast generation for all stores: < 10 minutes.
  - Daily replenishment plan generation: < 5 minutes.

- **Dashboard loading:**
  - Streamlit dashboard initial load: < 3 seconds.
  - Web app page load: < 2 seconds.

### 13.2 Throughput Targets

- **API Gateway:** Handle 100 requests/second.
- **Forecasting service:** Process 1000 store-SKU combinations per minute.
- **Database:** Support 1000 queries/second.

### 13.3 Scalability Targets

- **Horizontal scaling:** Services should scale to handle 10x current load.
- **Database:** Support 100 stores, 1000 SKUs, 1 year of historical data.
- **Storage:** Efficiently store and query time-series data (consider partitioning by date).

---

## 14. Security & Compliance

### 14.1 Authentication & Authorization

- **User authentication:** JWT tokens with expiration.
- **Role-based access control:** Enforce permissions based on user roles.
- **API authentication:** API keys for service-to-service communication.

### 14.2 Data Privacy

- **Data encryption:** Encrypt sensitive data at rest and in transit (HTTPS, database encryption).
- **Access logging:** Log all data access for audit purposes.
- **Data retention:** Define data retention policies (e.g., keep 2 years of historical data).

### 14.3 Security Best Practices

- **Input validation:** Validate and sanitize all inputs.
- **SQL injection prevention:** Use parameterized queries.
- **Dependency management:** Regularly update dependencies and scan for vulnerabilities.
- **Secrets management:** Use environment variables or secret management services (never commit secrets).

---
