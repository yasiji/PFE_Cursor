# Fresh Product Replenishment Manager

An end-to-end decision support system for predicting daily order quantities for fresh products at store level, minimizing waste and stockouts while protecting profitability.

---

## 🐳 Quick Start with Docker

**Run with a single command:**

```bash
# Clone and run
git clone https://github.com/YOUR_USERNAME/PFE_Cursor.git
cd PFE_Cursor
docker-compose up -d
```

**Or pull pre-built image:**

```bash
docker run -d -p 80:80 -p 8000:8000 -p 8501:8501 --name pfe-app ghcr.io/YOUR_USERNAME/pfe-replenishment:latest
```

**Access the app:**
| Service | URL |
|---------|-----|
| 🖥️ Frontend | http://localhost |
| 📚 API Docs | http://localhost:8000/docs |
| 📊 ML Dashboard | http://localhost:8501 |

**Login:** `test_user` / `test123`

---

## 🎯 Overview

This system provides:
- **Demand Forecasting**: ML-based predictions for daily product demand
- **Replenishment Recommendations**: Order quantity suggestions with safety stock calculations
- **Markdown Management**: Discount recommendations for near-expiry products
- **Analytics Dashboards**: Streamlit dashboards for data analysis
- **Operational Web App**: Store/chain manager interface for daily operations

### 👩‍💼 Manager Workflow: Understand → Anticipate → Act

- **Understand (Business Overview)**: Daily view of revenue, profit, and loss (waste, markdown, expiry) so managers instantly know how yesterday performed and where money leaked.
- **Anticipate (Forecast Outlook)**: Select a start date to see tomorrow’s drivers, 7-day factor breakdowns, and a 30-day revenue/profit/loss projection tailored to the period the manager cares about.
- **Act (Refill & Inventory)**: A date-driven Refill Plan automates shelf/backroom/markdown moves for the chosen day, while Inventory & Expiry maintains shelf vs stock and expiry visibility to execute decisions confidently.

## 🏗️ Architecture

The system follows a microservices architecture:

- **API Gateway** (`services/api_gateway/`): FastAPI REST API with authentication
- **Forecasting Service** (`services/forecasting/`): LightGBM-based demand forecasting
- **Replenishment Service** (`services/replenishment/`): Order-up-to policy and markdown logic
- **Ingestion Service** (`services/ingestion/`): Data loading and preprocessing
- **Streamlit Dashboard** (`apps/streamlit/`): Analytics and visualization
- **Web App** (`apps/webapp/`): Operational interface for store managers

## 📋 Prerequisites

- Python 3.10 or higher
- pip or conda package manager
- Git

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd PFE_Cursor
```

### 2. Create Virtual Environment

```bash
# Using venv
python -m venv .venv

# Activate virtual environment
# Windows:
.\.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Create a `.env` file in the project root (see `.env.example` for template):

```bash
# Copy example file
cp .env.example .env

# Edit .env and set your configuration
# CRITICAL: Set AUTH_JWT_SECRET_KEY in production!
```

### 5. Initialize Database

```bash
python scripts/init_database.py
```

### 6. Train Model (Optional)

If you want to train a new model:

```bash
python scripts/train_lightgbm_model.py
```

### 7. Start Services

**Start API Server** (Terminal 1):
```bash
uvicorn services.api_gateway.main:app --reload
```

**Start Everything** (One Command):
```bash
start.bat
```

This will automatically:
- Check prerequisites
- Install dependencies if needed
- Initialize database
- Seed test data if needed
- Start backend server
- Start frontend server
- Open browser

**Or start manually:**

**Start Store Manager Frontend** (Terminal 2):
```bash
cd apps/store-manager-frontend
npm install  # First time only
npm run dev
```

**Start Streamlit Dashboard** (Terminal 3) - For analytics:
```bash
streamlit run apps/streamlit/app.py
```

### 8. Access Applications

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **Store Manager Platform**: http://localhost:3000 ⭐ **Main Platform**
- **Streamlit Dashboard**: http://localhost:8501 (Analytics)
- **Legacy Web App**: http://localhost:8502 (Streamlit-based)

## 🔐 Security Configuration

### Production Setup

**CRITICAL**: Before deploying to production:

1. **Set JWT Secret Key**:
   ```bash
   export AUTH_JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
   ```

2. **Set CORS Origins**:
   ```bash
   export API_ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
   ```

3. **Set Environment**:
   ```bash
   export ENVIRONMENT=prod
   ```

4. **Database URL** (if using PostgreSQL):
   ```bash
   export DATABASE_URL=postgresql://user:password@localhost:5432/replenishment_db
   ```

## 📖 Usage

### API Usage

#### Authentication

```bash
# Register a user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "store_manager",
    "email": "manager@example.com",
    "password": "secure_password",
    "role": "store_manager",
    "store_id": 235
  }'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=store_manager&password=secure_password"
```

#### Generate Forecast

```bash
curl -X POST http://localhost:8000/api/v1/forecast \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "store_id": "235",
    "sku_id": "123",
    "horizon_days": 7,
    "include_uncertainty": true
  }'
```

#### Generate Replenishment Plan

```bash
curl -X POST http://localhost:8000/api/v1/replenishment_plan \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "store_id": "235",
    "date": "2024-01-15",
    "current_inventory": [
      {
        "sku_id": "123",
        "quantity": 50.0,
        "expiry_date": "2024-01-18"
      }
    ]
  }'
```

### Web App Usage

1. **Login** with credentials created via the API.
2. **Business Overview (Understand)** – Review yesterday’s revenue, profit, and loss (waste/markdown), top-line KPIs, and alerts.
3. **Forecast Outlook (Anticipate)** – Use the date picker + window selector to inspect tomorrow’s drivers, a rolling 7-day breakdown, and a configurable 7/14/30-day revenue/profit/loss outlook.
4. **Refill Plan (Act)** – Choose the target date to automatically refresh shelf/backroom refills, orders, markdowns, and factor chips.
5. **Inventory & Expiry** – Monitor shelf vs stock levels, expiry buckets, in-transit loads, and discard queues.
6. **History / Settings** – Audit past decisions and configure API/base settings; Chain Dashboard remains available for regional roles.

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_baseline_models.py

# Run integration tests
pytest tests/integration/
```

## 📁 Project Structure

```
.
├── apps/                    # Frontend applications
│   ├── streamlit/          # Analytics dashboard
│   └── webapp/             # Operational web app
├── config/                 # Configuration files
│   ├── config.yaml        # Base configuration
│   ├── dev.yaml           # Development overrides
│   └── prod.yaml         # Production overrides
├── data/                   # Data storage (gitignored)
│   ├── models/            # Trained models
│   ├── processed/        # Processed data
│   └── raw/              # Raw data
├── docs/                  # Documentation
├── notebooks/             # Jupyter notebooks for EDA
├── scripts/               # Utility scripts
├── services/              # Backend services
│   ├── api_gateway/      # FastAPI application
│   ├── forecasting/      # Forecasting service
│   ├── ingestion/        # Data ingestion
│   └── replenishment/   # Replenishment logic
├── shared/                # Shared utilities
├── tests/                 # Test suite
└── requirements.txt       # Python dependencies
```

## 🔧 Configuration

Configuration is managed through YAML files and environment variables:

1. **Base Config**: `config/config.yaml`
2. **Environment Overrides**: `config/dev.yaml` or `config/prod.yaml`
3. **Environment Variables**: `.env` file (highest priority)

See `config/config.yaml` for all available configuration options.

## 📊 Model Information

- **Primary Model**: LightGBM
- **Features**: 30+ features including lags, rolling stats, calendar, weather
- **Performance**: 33.7% MAE improvement over baseline
- **Model Path**: `data/models/lightgbm_model.pkl`

## 🐛 Troubleshooting

### API Won't Start

- Check if port 8000 is available
- Verify `.env` file exists and is configured
- Check database connection string

### Authentication Fails

- Verify `AUTH_JWT_SECRET_KEY` is set
- Check token expiration (default: 30 minutes)
- Ensure user exists in database

### Model Not Found

- Train model: `python scripts/train_lightgbm_model.py`
- Check model path in config
- Verify model file exists: `data/models/lightgbm_model.pkl`

### Database Errors

- Run database initialization: `python scripts/init_database.py`
- Check database file permissions
- Verify database URL in config

## 📚 Documentation

- **Architecture**: See `project.md`
- **Development Guide**: See `guide.md`
- **Task Tracking**: See `task.md`
- **API Documentation**: http://localhost:8000/docs (when API is running)
- **Deployment Guide**: See `docs/DEPLOYMENT.md`

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📝 License

[Add your license here]

## 👥 Authors

- Yassine

## 🙏 Acknowledgments

- FreshRetailNet-50K dataset from HuggingFace
- LightGBM team for the excellent ML library

## 📞 Support

For issues and questions, please open an issue on GitHub.

---

**Note**: This is an MVP version. See `PROJECT_REVIEW.md` for production readiness assessment.

