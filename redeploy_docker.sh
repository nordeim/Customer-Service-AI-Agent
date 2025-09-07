#!/bin/bash
set -e

echo "Stopping containers..."
docker-compose down

read -p "Remove ALL volumes? This will delete ALL persisted data (y/N): " confirm
if [[ "$confirm" =~ ^[Yy]$ ]]; then
    echo "Removing all volumes..."
    docker-compose down --volumes
else
    echo "Skipping volume removal."
fi

echo "Rebuilding images..."
docker-compose build --no-cache

echo "Starting infrastructure services..."
docker-compose up --build -d postgres redis elasticsearch neo4j mongodb zookeeper kafka

echo "Waiting for services to become healthy..."
# Loop until all infra services are healthy
services=(postgres redis elasticsearch neo4j mongodb kafka)
for service in "${services[@]}"; do
    echo "Waiting for $service..."
    until [ "$(docker inspect --format='{{.State.Health.Status}}' ai-customer-service-$service)" == "healthy" ]; do
        sleep 3
    done
done

echo "Starting API service..."
docker-compose up --build -d api

echo "Waiting for API to become healthy..."
until [ "$(docker inspect --format='{{.State.Health.Status}}' ai-customer-service-api)" == "healthy" ]; do
    sleep 3
done

echo "Running database migrations..."
docker-compose exec api alembic upgrade head

echo "✅ Environment reset and ready."

