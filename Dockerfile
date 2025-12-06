# Backend Dockerfile for Fresh Product Replenishment Manager
# Multi-stage build for smaller final image

FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY services/ ./services/
COPY shared/ ./shared/
COPY scripts/ ./scripts/
COPY apps/streamlit/ ./apps/streamlit/
COPY config/ ./config/
COPY data/models/ ./data/models/
COPY data/hf_cache/ ./data/hf_cache/
COPY FreshRetailNet-50K/ ./FreshRetailNet-50K/

# Create data directories
RUN mkdir -p data/raw data/processed data/models

# Environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=prod

# Expose ports
EXPOSE 8000 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command - start both API and Streamlit
CMD ["sh", "-c", "uvicorn services.api_gateway.main:app --host 0.0.0.0 --port 8000 & streamlit run apps/streamlit/app.py --server.port 8501 --server.headless true --server.address 0.0.0.0"]

