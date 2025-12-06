"""FastAPI application main entry point."""

from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from services.api_gateway.database import init_db, get_db
from services.api_gateway.schemas import (
    ForecastRequest,
    ForecastResponse,
    ForecastItem,
    ReplenishmentRequest,
    ReplenishmentResponse,
    HealthResponse,
    ErrorResponse
)
from services.api_gateway.services import ForecastingService, ReplenishmentService
from services.api_gateway.auth import get_current_user, require_role
from services.api_gateway.auth_routes import router as auth_router
from services.api_gateway.store_routes import router as store_router
from services.api_gateway.order_routes import router as order_router
from services.api_gateway.markdown_routes import router as markdown_router
from services.api_gateway.inventory_routes import router as inventory_router
from services.api_gateway.price_routes import router as price_router
from services.api_gateway.notification_routes import router as notification_router
from services.api_gateway.analytics_routes import router as analytics_router
from services.api_gateway.settings_routes import router as settings_router
from services.api_gateway.models import User
from shared.config import get_config, DEFAULT_JWT_SECRET
from shared.logging_setup import get_logger

logger = get_logger(__name__)
config = get_config()

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Initialize FastAPI app
app = FastAPI(
    title="Fresh Product Replenishment Manager API",
    description="API for demand forecasting and replenishment recommendations",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc
    openapi_url="/openapi.json"  # OpenAPI schema
)

# Add rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware - enforce strict origin validation
allowed_origins = config.api.allowed_origins or []
if config.environment == "dev":
    # In development, allow localhost origins
    if not allowed_origins:
        allowed_origins = [
            "http://localhost:8501",
            "http://localhost:8502",
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:5173",
            "http://127.0.0.1:8501",
            "http://127.0.0.1:8502",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
            "http://127.0.0.1:5173",
        ]
else:
    # In production, fail if wildcard or empty origins
    if "*" in allowed_origins or not allowed_origins:
        raise RuntimeError(
            "CORS allowed_origins must be explicitly set (no wildcards) in production. "
            "Set API_ALLOWED_ORIGINS environment variable."
        )

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    expose_headers=["X-Request-ID"],
)

# Include routers
app.include_router(auth_router)
app.include_router(store_router)
app.include_router(order_router)
app.include_router(markdown_router)
app.include_router(inventory_router)
app.include_router(price_router)
app.include_router(notification_router)
app.include_router(analytics_router)
app.include_router(settings_router)

# Initialize services using singleton getters
from services.api_gateway.services import get_forecasting_service, get_replenishment_service
forecasting_service = get_forecasting_service()
replenishment_service = get_replenishment_service()


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    try:
        # Ensure data directory exists
        from pathlib import Path
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        
        # Validate security configuration
        if config.environment != "dev":
            if config.auth.jwt_secret_key == DEFAULT_JWT_SECRET:
                raise RuntimeError(
                    "JWT_SECRET_KEY must be set via AUTH_JWT_SECRET_KEY environment variable "
                    "in non-development environments"
                )
            if "*" in allowed_origins or not allowed_origins:
                raise RuntimeError(
                    "CORS allowed_origins must be explicitly set (no wildcards) in production. "
                    "Set API_ALLOWED_ORIGINS environment variable."
                )

        # Initialize database
        init_db()
        logger.info("API Gateway started - Database initialized")
    except RuntimeError:
        # Re-raise security validation errors
        raise
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        # Continue anyway - database might already exist


@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint."""
    return HealthResponse(
        status="ok",
        version="1.0.0"
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        version="1.0.0"
    )


@app.post("/api/v1/forecast", response_model=ForecastResponse)
@limiter.limit("30/minute")  # 30 requests per minute per IP
async def forecast(
    request: Request,
    forecast_request: ForecastRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Generate demand forecast for a store-SKU combination.
    
    Requires authentication.
    Rate limit: 30 requests per minute per IP address.
    """
    try:
        logger.info(f"Forecast request: store_id={forecast_request.store_id}, sku_id={forecast_request.sku_id}, horizon={forecast_request.horizon_days}")
        
        forecasts = forecasting_service.forecast(
            store_id=forecast_request.store_id,
            sku_id=forecast_request.sku_id,
            horizon_days=forecast_request.horizon_days,
            include_uncertainty=forecast_request.include_uncertainty
        )
        
        forecast_items = [
            ForecastItem(**f) for f in forecasts
        ]
        
        return ForecastResponse(
            store_id=forecast_request.store_id,
            sku_id=forecast_request.sku_id,
            forecasts=forecast_items,
            model_type="lightgbm"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in forecast endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.post("/api/v1/replenishment_plan", response_model=ReplenishmentResponse)
@limiter.limit("20/minute")  # 20 requests per minute per IP
async def replenishment_plan(
    request: Request,
    replenishment_request: ReplenishmentRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Generate replenishment plan for a store.
    
    Requires authentication.
    Rate limit: 20 requests per minute per IP address.
    """
    try:
        logger.info(f"Replenishment plan request: store_id={replenishment_request.store_id}, target_date={replenishment_request.target_date}")
        
        # Convert inventory items to dict format
        inventory_list = [
            {
                "sku_id": item.sku_id,
                "quantity": item.quantity,
                "expiry_date": item.expiry_date.isoformat() if item.expiry_date else None
            }
            for item in replenishment_request.current_inventory
        ]
        
        # Handle empty inventory case
        if not inventory_list:
            logger.warning("Empty inventory list provided, using default sample")
            # Provide a default sample inventory item
            inventory_list = [{
                "sku_id": "123",
                "quantity": 50.0,
                "expiry_date": None
            }]
        
        recommendations = replenishment_service.generate_replenishment_plan(
            store_id=str(replenishment_request.store_id),
            target_date=replenishment_request.target_date,
            current_inventory=inventory_list
        )
        
        from services.api_gateway.schemas import ReplenishmentItem, MarkdownRecommendation
        
        recommendation_items = []
        for rec in recommendations:
            markdown = None
            if rec.get("markdown"):
                markdown = MarkdownRecommendation(**rec["markdown"])
            
            recommendation_items.append(
                ReplenishmentItem(
                    sku_id=rec["sku_id"],
                    order_quantity=rec["order_quantity"],
                    markdown=markdown
                )
            )
        
        return ReplenishmentResponse(
            store_id=replenishment_request.store_id,
            date=replenishment_request.target_date,
            recommendations=recommendation_items
        )
    except ValueError as e:
        logger.warning(f"Validation error in replenishment_plan endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in replenishment_plan endpoint: {e}", exc_info=True)
        # Don't expose internal error details
        error_message = str(e) if config.environment == "dev" else "Failed to generate replenishment plan"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_message
        )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    import traceback
    
    # Log full exception details
    logger.error(
        f"Unhandled exception: {exc}",
        exc_info=True,
        path=request.url.path,
        method=request.method
    )
    
    # Don't expose internal error details in production
    if config.environment == "dev":
        error_message = str(exc)
        error_detail = traceback.format_exc()
    else:
        error_message = "An internal error occurred. Please contact support."
        error_detail = None
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": error_message,
            "status_code": 500,
            "detail": error_detail if config.environment == "dev" else None
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "services.api_gateway.main:app",
        host=config.api.host,
        port=config.api.port,
        reload=True
    )

