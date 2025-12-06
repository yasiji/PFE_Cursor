# API Documentation

The Fresh Product Replenishment Manager API provides REST endpoints for demand forecasting and replenishment planning.

## 🔗 Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://api.yourdomain.com`

## 📚 Interactive Documentation

When the API is running, interactive documentation is available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## 🔐 Authentication

All endpoints (except `/health` and `/api/v1/auth/*`) require authentication using JWT Bearer tokens.

### Register User

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "username": "store_manager",
  "email": "manager@example.com",
  "password": "secure_password",
  "role": "store_manager",
  "store_id": 235
}
```

**Response:**
```json
{
  "username": "store_manager",
  "email": "manager@example.com",
  "role": "store_manager",
  "store_id": 235
}
```

### Login

```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=store_manager&password=secure_password
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Using the Token

Include the token in the Authorization header:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## 📊 Endpoints

### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00"
}
```

### Generate Forecast

```http
POST /api/v1/forecast
Authorization: Bearer <token>
Content-Type: application/json

{
  "store_id": "235",
  "sku_id": "123",
  "horizon_days": 7,
  "include_uncertainty": true
}
```

**Response:**
```json
{
  "store_id": "235",
  "sku_id": "123",
  "forecasts": [
    {
      "date": "2024-01-16",
      "predicted_demand": 45.2,
      "lower_bound": 32.1,
      "upper_bound": 58.3
    },
    {
      "date": "2024-01-17",
      "predicted_demand": 48.5,
      "lower_bound": 34.2,
      "upper_bound": 62.8
    }
  ],
  "model_type": "lightgbm",
  "generated_at": "2024-01-15T10:30:00"
}
```

**Rate Limit**: 30 requests per minute per IP address

### Generate Replenishment Plan

```http
POST /api/v1/replenishment_plan
Authorization: Bearer <token>
Content-Type: application/json

{
  "store_id": "235",
  "date": "2024-01-15",
  "current_inventory": [
    {
      "sku_id": "123",
      "quantity": 50.0,
      "expiry_date": "2024-01-18"
    },
    {
      "sku_id": "456",
      "quantity": 30.0,
      "expiry_date": "2024-01-20"
    }
  ]
}
```

**Response:**
```json
{
  "store_id": "235",
  "date": "2024-01-15",
  "recommendations": [
    {
      "sku_id": "123",
      "order_quantity": 25.0,
      "markdown": {
        "discount_percent": 20.0,
        "effective_date": "2024-01-15",
        "reason": "Near expiry"
      }
    },
    {
      "sku_id": "456",
      "order_quantity": 15.0,
      "markdown": null
    }
  ],
  "generated_at": "2024-01-15T10:30:00"
}
```

**Rate Limit**: 20 requests per minute per IP address

## 🚦 Status Codes

- `200 OK`: Request successful
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Missing or invalid authentication token
- `403 Forbidden`: Insufficient permissions
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

## ⚠️ Error Responses

Error responses follow this format:

```json
{
  "error": "Error Type",
  "message": "Human-readable error message",
  "status_code": 400
}
```

Example:
```json
{
  "error": "Validation Error",
  "message": "horizon_days must be between 1 and 14",
  "status_code": 400
}
```

## 🔒 Rate Limiting

API endpoints are rate-limited to prevent abuse:

- **Forecast endpoint**: 30 requests/minute per IP
- **Replenishment endpoint**: 20 requests/minute per IP
- **Auth endpoints**: 10 requests/minute per IP

When rate limit is exceeded, you'll receive:

```json
{
  "error": "Rate Limit Exceeded",
  "message": "Rate limit exceeded: 30 per 1 minute",
  "status_code": 429
}
```

## 📝 Request/Response Schemas

### ForecastRequest

```json
{
  "store_id": "string (required, min_length: 1)",
  "sku_id": "string (required, min_length: 1)",
  "horizon_days": "integer (1-14, default: 1)",
  "include_uncertainty": "boolean (default: false)"
}
```

### ReplenishmentRequest

```json
{
  "store_id": "string (required)",
  "date": "date (required, YYYY-MM-DD)",
  "current_inventory": [
    {
      "sku_id": "string (required)",
      "quantity": "float (required, >= 0)",
      "expiry_date": "date (optional, YYYY-MM-DD)"
    }
  ]
}
```

## 🔄 Pagination

Currently, endpoints return all results. Future versions may support pagination.

## 📅 Date Formats

All dates use ISO 8601 format: `YYYY-MM-DD`

Example: `2024-01-15`

## 🧪 Testing

Use the interactive Swagger UI at `/docs` to test endpoints directly in your browser.

For programmatic testing:

```python
import requests

# Login
response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    data={"username": "user", "password": "pass"}
)
token = response.json()["access_token"]

# Make authenticated request
headers = {"Authorization": f"Bearer {token}"}
response = requests.post(
    "http://localhost:8000/api/v1/forecast",
    json={
        "store_id": "235",
        "sku_id": "123",
        "horizon_days": 7
    },
    headers=headers
)
print(response.json())
```

## 📞 Support

For API issues:
1. Check the interactive docs at `/docs`
2. Review error messages in responses
3. Check application logs
4. Open an issue on GitHub

---

**Note**: For the most up-to-date API documentation, visit `/docs` when the API is running.

