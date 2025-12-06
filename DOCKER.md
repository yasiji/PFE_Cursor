# 🐳 Docker Deployment Guide

This guide explains how to run the Fresh Product Replenishment Manager using Docker.

---

## 🚀 Quick Run (For Anyone)

If someone shared this app with you, just run:

```bash
# Download and start
curl -o docker-compose.yml https://raw.githubusercontent.com/YOUR_REPO/main/docker-compose.public.yml
docker-compose up -d

# Open in browser
# Frontend: http://localhost
# API Docs: http://localhost:8000/docs
# ML Dashboard: http://localhost:8501
```

Login: `test_user` / `test123`

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (version 20.10+)
- [Docker Compose](https://docs.docker.com/compose/install/) (version 2.0+)

## Quick Start

### 1. Clone the repository
```bash
git clone <repository-url>
cd PFE_Cursor
```

### 2. Build and run with Docker Compose

**Production mode:**
```bash
docker-compose up --build -d
```

**Development mode (with hot reload):**
```bash
docker-compose -f docker-compose.dev.yml up --build
```

### 3. Access the application

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost | Main Store Manager UI |
| Backend API | http://localhost:8000 | FastAPI REST API |
| API Docs | http://localhost:8000/docs | Swagger Documentation |
| ML Dashboard | http://localhost:8501 | Streamlit ML Dashboard |

### 4. Login credentials
- **Username:** `test_user`
- **Password:** `test123`

## Docker Commands

### Start services
```bash
# Production
docker-compose up -d

# Development with logs
docker-compose -f docker-compose.dev.yml up

# Rebuild after code changes
docker-compose up --build -d
```

### Stop services
```bash
docker-compose down

# Stop and remove volumes (WARNING: deletes data)
docker-compose down -v
```

### View logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Access container shell
```bash
docker-compose exec backend sh
docker-compose exec frontend sh
```

## Configuration

### Environment Variables

Create a `.env` file from the example:
```bash
cp .env.example .env
```

Edit `.env` with your production values:
```env
# IMPORTANT: Change this in production!
JWT_SECRET_KEY=your-super-secret-key-minimum-32-characters

# Environment
ENVIRONMENT=prod
```

### Persistent Data

Data is persisted in the `./data` directory:
- `data/replenishment_dev.db` - SQLite database
- `data/models/` - Trained ML models
- `data/hf_cache/` - Dataset cache

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Docker Network                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐ │
│  │   Frontend   │────▶│   Backend    │     │  Streamlit   │ │
│  │   (Nginx)    │     │  (FastAPI)   │     │  Dashboard   │ │
│  │   Port 80    │     │  Port 8000   │     │  Port 8501   │ │
│  └──────────────┘     └──────┬───────┘     └──────────────┘ │
│                              │                               │
│                       ┌──────▼───────┐                       │
│                       │   SQLite DB  │                       │
│                       │  (./data/)   │                       │
│                       └──────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs backend

# Verify ports are available
netstat -an | findstr 8000
netstat -an | findstr 80
```

### Database issues
```bash
# Reset database (inside container)
docker-compose exec backend python scripts/seed_test_data.py
```

### Frontend can't connect to API
- Check that backend is healthy: `docker-compose ps`
- Verify CORS settings in backend
- Check nginx proxy configuration

### Performance issues
```bash
# Increase Docker resources in Docker Desktop settings
# Recommended: 4GB RAM, 2 CPUs
```

## Production Deployment

For production deployment:

1. **Use a proper database** (PostgreSQL instead of SQLite)
2. **Set secure JWT secret**
3. **Enable HTTPS** with SSL certificates
4. **Configure proper logging**
5. **Set up monitoring** (Prometheus, Grafana)

### Example production docker-compose override:
```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  backend:
    environment:
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - DATABASE_URL=postgresql://user:pass@db:5432/pfe
    deploy:
      resources:
        limits:
          memory: 2G
  
  frontend:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.frontend.rule=Host(`yourdomain.com`)"
```

## Building Individual Images

```bash
# Backend only
docker build -t pfe-backend:latest .

# Frontend only
docker build -t pfe-frontend:latest -f Dockerfile.frontend .
```

## Cleaning Up

```bash
# Remove all containers
docker-compose down

# Remove unused images
docker image prune -a

# Remove all Docker resources (CAUTION)
docker system prune -a
```

---

## 🌍 Sharing Your App Publicly

### Option 1: Docker Hub (Recommended)

1. **Create account** at [hub.docker.com](https://hub.docker.com)

2. **Login and publish:**
```bash
# Login to Docker Hub
docker login

# Publish (Windows)
scripts\docker-publish.bat YOUR_DOCKERHUB_USERNAME v1.0

# Publish (Mac/Linux)
chmod +x scripts/docker-publish.sh
./scripts/docker-publish.sh YOUR_DOCKERHUB_USERNAME v1.0
```

3. **Share with others** - They can run:
```bash
# Create docker-compose.yml with your username
curl -o docker-compose.yml https://raw.githubusercontent.com/YOUR_REPO/docker-compose.public.yml

# Set your Docker Hub username and run
set DOCKERHUB_USER=YOUR_DOCKERHUB_USERNAME
docker-compose up -d
```

### Option 2: GitHub Container Registry

If your code is on GitHub:

```bash
# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Tag and push
docker tag pfe-backend:latest ghcr.io/USERNAME/pfe-backend:latest
docker push ghcr.io/USERNAME/pfe-backend:latest
```

### Option 3: Deploy to Cloud

**DigitalOcean (Easiest):**
1. Create a Droplet ($6/month)
2. Install Docker: `curl -fsSL https://get.docker.com | sh`
3. Clone repo and run: `docker-compose up -d`
4. Share your server's IP address

**Railway.app (Free tier):**
1. Connect GitHub repo
2. Railway auto-deploys from Dockerfile
3. Get a public URL automatically

**Render.com (Free tier):**
1. Create Web Service from GitHub
2. Point to your Dockerfile
3. Get free subdomain

### Quick Share Link Template

After publishing, share this with others:

```
🚀 Fresh Product Replenishment Manager

Run with Docker:
1. Install Docker: https://docker.com
2. Run these commands:

docker pull YOUR_USERNAME/pfe-replenishment-backend:latest
docker pull YOUR_USERNAME/pfe-replenishment-frontend:latest
docker-compose -f docker-compose.public.yml up -d

3. Open http://localhost
4. Login: test_user / test123

📊 ML Dashboard: http://localhost:8501
📚 API Docs: http://localhost:8000/docs
```

