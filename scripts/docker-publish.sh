#!/bin/bash
# Script to build and publish Docker images to Docker Hub
# Usage: ./scripts/docker-publish.sh <dockerhub-username>

set -e

DOCKERHUB_USER=${1:-"yourusername"}
VERSION=${2:-"latest"}
APP_NAME="pfe-replenishment"

echo "🐳 Building and publishing to Docker Hub..."
echo "   User: $DOCKERHUB_USER"
echo "   Version: $VERSION"

# Build backend image
echo "📦 Building backend image..."
docker build -t $DOCKERHUB_USER/$APP_NAME-backend:$VERSION .

# Build frontend image
echo "📦 Building frontend image..."
docker build -t $DOCKERHUB_USER/$APP_NAME-frontend:$VERSION -f Dockerfile.frontend .

# Push to Docker Hub
echo "🚀 Pushing to Docker Hub..."
docker push $DOCKERHUB_USER/$APP_NAME-backend:$VERSION
docker push $DOCKERHUB_USER/$APP_NAME-frontend:$VERSION

echo "✅ Done! Images available at:"
echo "   docker pull $DOCKERHUB_USER/$APP_NAME-backend:$VERSION"
echo "   docker pull $DOCKERHUB_USER/$APP_NAME-frontend:$VERSION"

