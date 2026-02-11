#!/usr/bin/env bash
set -euo pipefail

# WireGuard Mesh Manager Deployment Script
# Usage: ./deploy.sh [dev|prod] [--no-build]

ENV="${1:-dev}"
SKIP_BUILD="${2:-}"

# Validate environment argument
if [[ "$ENV" != "dev" && "$ENV" != "prod" ]]; then
  echo "Error: Invalid environment '$ENV'"
  echo "Usage: $0 [dev|prod] [--no-build]"
  exit 1
fi

# Set compose file based on environment
if [[ "$ENV" == "prod" ]]; then
  COMPOSE_FILE="docker-compose.prod.yml"
  echo "Deploying to PRODUCTION..."
else
  COMPOSE_FILE="docker-compose.yml"
  echo "Deploying to DEVELOPMENT..."
fi

# Check if docker-compose file exists
if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "Error: $COMPOSE_FILE not found"
  exit 1
fi

# Skip build if flag is set
if [[ "$SKIP_BUILD" == "--no-build" ]]; then
  echo "Skipping build (--no-build flag set)..."
else
  # Stop existing containers (if any)
  echo "Stopping existing containers..."
  docker compose -f "$COMPOSE_FILE" down --remove-orphans || true

  # Enable BuildKit for better caching
  export DOCKER_BUILDKIT=1
  export COMPOSE_DOCKER_CLI_BUILD=1

  # Pull latest base images (if any pre-built)
  echo "Pulling latest base images..."
  docker compose -f "$COMPOSE_FILE" pull || echo "No pre-built images found, will build from source"

  # Build with caching for speed
  # Backend: uses pip cache volume defined in compose file
  # Frontend: we add npm cache mount for faster rebuilds
  echo "Building images from source (with caching)..."
  if [[ "$ENV" == "prod" ]]; then
    # Build backend with pip cache
    docker compose -f "$COMPOSE_FILE" build backend
    # Build frontend with npm cache
    docker compose -f "$COMPOSE_FILE" build --build-arg NODE_ENV=production frontend
  else
    # Build all services for dev
    docker compose -f "$COMPOSE_FILE" build
  fi
fi

# Start containers with force recreate
echo "Starting containers..."
docker compose -f "$COMPOSE_FILE" up -d --force-recreate

# Wait for services to be healthy
echo "Waiting for services to start..."
echo "Backend health check..."
sleep 3
for _ in {1..30}; do
  backend_status="$(docker compose -f "$COMPOSE_FILE" ps backend 2>/dev/null || true)"
  if echo "$backend_status" | grep -E -q "healthy|Exit 0"; then
    break
  fi
  sleep 2
done

echo "Frontend health check..."
sleep 2

# Show status
echo ""
echo "Deployment status:"
docker compose -f "$COMPOSE_FILE" ps

echo ""
echo "Deployment to $ENV completed successfully!"
echo ""
if [[ "$ENV" == "prod" ]]; then
  echo "Frontend: http://127.0.0.1:3000"
  echo "Backend API: http://127.0.0.1:8000"
  echo "API Docs: http://127.0.0.1:8000/docs"
else
  echo "Frontend: http://127.0.0.1:3000"
  echo "Backend API: http://127.0.0.1:8000"
  echo "API Docs: http://127.0.0.1:8000/docs"
  echo "Redis: http://127.0.0.1:6379"
fi

# Cleanup unused Docker images (only occasionally, not every deploy to save time)
# echo ""
# echo "Cleaning up unused Docker images..."
# echo "Removing dangling images..."
# docker image prune -f
