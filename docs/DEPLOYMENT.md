# Deployment Guide

This guide covers deploying the Fresh Product Replenishment Manager to production.

## 🎯 Prerequisites

- Python 3.10+
- PostgreSQL (recommended for production) or SQLite (for small deployments)
- Reverse proxy (nginx recommended)
- SSL certificate (for HTTPS)

## 📋 Pre-Deployment Checklist

- [ ] All environment variables set
- [ ] JWT secret key generated and secured
- [ ] Database configured and migrated
- [ ] Model trained and saved
- [ ] CORS origins configured
- [ ] SSL certificates obtained
- [ ] Monitoring configured
- [ ] Backup strategy in place

## 🔐 Security Configuration

### 1. Generate JWT Secret Key

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Save this securely and set as environment variable:
```bash
export AUTH_JWT_SECRET_KEY="your-generated-secret-key"
```

### 2. Configure CORS Origins

Set allowed origins (no wildcards):
```bash
export API_ALLOWED_ORIGINS=https://app.yourdomain.com,https://dashboard.yourdomain.com
```

### 3. Set Production Environment

```bash
export ENVIRONMENT=prod
```

## 🗄️ Database Setup

### PostgreSQL (Recommended)

1. **Install PostgreSQL**:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install postgresql postgresql-contrib
   
   # macOS
   brew install postgresql
   ```

2. **Create Database**:
   ```sql
   CREATE DATABASE replenishment_db;
   CREATE USER replenishment_user WITH PASSWORD 'secure_password';
   GRANT ALL PRIVILEGES ON DATABASE replenishment_db TO replenishment_user;
   ```

3. **Set Connection String**:
   ```bash
   export DATABASE_URL=postgresql://replenishment_user:secure_password@localhost:5432/replenishment_db
   ```

4. **Initialize Schema**:
   ```bash
   python scripts/init_database.py
   ```

### SQLite (Small Deployments)

SQLite works for small deployments but has limitations:
- Single writer
- No concurrent access
- Not recommended for >100 stores

```bash
export DATABASE_URL=sqlite:///./data/replenishment.db
python scripts/init_database.py
```

## 🐳 Docker Deployment (Recommended)

### 1. Create Dockerfile

Create `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "services.api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Create docker-compose.yml

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=prod
      - AUTH_JWT_SECRET_KEY=${AUTH_JWT_SECRET_KEY}
      - DATABASE_URL=${DATABASE_URL}
      - API_ALLOWED_ORIGINS=${API_ALLOWED_ORIGINS}
    volumes:
      - ./data:/app/data
    restart: unless-stopped

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=replenishment_db
      - POSTGRES_USER=replenishment_user
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  postgres_data:
```

### 3. Deploy

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## 🚀 Manual Deployment

### 1. Server Setup

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Python and dependencies
sudo apt-get install python3.10 python3-pip python3-venv

# Create application user
sudo useradd -m -s /bin/bash replenishment
sudo su - replenishment
```

### 2. Application Setup

```bash
# Clone repository
git clone <repository-url> replenishment-manager
cd replenishment-manager

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with production values
```

### 3. Systemd Service

Create `/etc/systemd/system/replenishment-api.service`:

```ini
[Unit]
Description=Fresh Product Replenishment Manager API
After=network.target postgresql.service

[Service]
Type=simple
User=replenishment
WorkingDirectory=/home/replenishment/replenishment-manager
Environment="PATH=/home/replenishment/replenishment-manager/.venv/bin"
EnvironmentFile=/home/replenishment/replenishment-manager/.env
ExecStart=/home/replenishment/replenishment-manager/.venv/bin/uvicorn services.api_gateway.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable replenishment-api
sudo systemctl start replenishment-api
sudo systemctl status replenishment-api
```

## 🔄 Nginx Reverse Proxy

Create `/etc/nginx/sites-available/replenishment`:

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and restart:
```bash
sudo ln -s /etc/nginx/sites-available/replenishment /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 📊 Monitoring

### Health Checks

The API provides a health endpoint:
```bash
curl http://localhost:8000/health
```

### Logging

Logs are written to stdout. For production, configure log aggregation:

```bash
# Using systemd journal
journalctl -u replenishment-api -f

# Or redirect to file
# Add to systemd service:
StandardOutput=append:/var/log/replenishment/api.log
StandardError=append:/var/log/replenishment/error.log
```

### Metrics

Consider integrating:
- Prometheus for metrics
- Grafana for visualization
- Sentry for error tracking

## 🔄 Updates and Rollbacks

### Update Process

1. **Backup Database**:
   ```bash
   pg_dump replenishment_db > backup_$(date +%Y%m%d).sql
   ```

2. **Pull Updates**:
   ```bash
   git pull origin main
   ```

3. **Update Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run Migrations** (if any):
   ```bash
   # Future: alembic upgrade head
   ```

5. **Restart Service**:
   ```bash
   sudo systemctl restart replenishment-api
   ```

### Rollback

1. **Restore Database**:
   ```bash
   psql replenishment_db < backup_YYYYMMDD.sql
   ```

2. **Revert Code**:
   ```bash
   git checkout <previous-commit>
   ```

3. **Restart Service**:
   ```bash
   sudo systemctl restart replenishment-api
   ```

## 🔒 Security Best Practices

1. **Firewall**: Only allow necessary ports
   ```bash
   sudo ufw allow 22/tcp  # SSH
   sudo ufw allow 80/tcp  # HTTP
   sudo ufw allow 443/tcp # HTTPS
   sudo ufw enable
   ```

2. **SSL/TLS**: Always use HTTPS in production

3. **Secrets Management**: Use secret management service (AWS Secrets Manager, HashiCorp Vault)

4. **Regular Updates**: Keep system and dependencies updated

5. **Backup**: Regular automated backups

## 📈 Scaling

### Horizontal Scaling

1. **Load Balancer**: Use nginx or cloud load balancer
2. **Multiple Instances**: Run multiple API instances
3. **Database**: Use read replicas for read-heavy workloads

### Vertical Scaling

1. **Increase Resources**: More CPU/RAM
2. **Database Optimization**: Tune PostgreSQL
3. **Caching**: Add Redis for caching

## 🐛 Troubleshooting

### Service Won't Start

```bash
# Check logs
journalctl -u replenishment-api -n 50

# Check configuration
python -c "from shared.config import get_config; print(get_config())"

# Test database connection
python scripts/init_database.py
```

### High Memory Usage

- Check for memory leaks
- Reduce batch sizes in config
- Add caching layer

### Slow Performance

- Check database indexes
- Enable query logging
- Profile API endpoints

## 📞 Support

For deployment issues, check:
1. Application logs
2. System logs
3. Database logs
4. Nginx logs

---

**Note**: This deployment guide is for production use. For development, see README.md.

