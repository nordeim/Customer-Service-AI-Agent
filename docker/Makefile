# Docker Operations Makefile for AI Customer Service Agent
# This Makefile provides commands for Docker infrastructure management

.PHONY: help build up down logs status clean test db-reset health-check backup restore

# Default target
help:
	@echo "🐳 Docker Infrastructure Management for AI Customer Service Agent"
	@echo ""
	@echo "Environment Setup:"
	@echo "  init             - Initialize Docker environment (copy .env.docker)"
	@echo "  build            - Build all Docker images"
	@echo ""
	@echo "Service Management:"
	@echo "  up               - Start all services in detached mode"
	@echo "  up-logs          - Start all services with logs in foreground"
	@echo "  down             - Stop and remove all services"
	@echo "  stop             - Stop services but keep containers"
	@echo "  restart          - Restart all services"
	@echo "  logs             - Show logs for all services"
	@echo "  logs-follow      - Follow logs for all services"
	@echo "  status           - Show service status"
	@echo ""
	@echo "Individual Services:"
	@echo "  postgres-up      - Start PostgreSQL only"
	@echo "  redis-up         - Start Redis only"
	@echo "  elasticsearch-up - Start Elasticsearch only"
	@echo "  neo4j-up         - Start Neo4j only"
	@echo "  mongodb-up       - Start MongoDB only"
	@echo "  kafka-up         - Start Kafka and Zookeeper"
	@echo ""
	@echo "Database Operations:"
	@echo "  db-reset         - Reset database schema"
	@echo "  db-connect       - Connect to PostgreSQL CLI"
	@echo "  db-backup        - Create database backup"
	@echo "  db-restore       - Restore database from backup"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean            - Clean up containers and volumes"
	@echo "  prune            - Clean up Docker system"
	@echo "  health-check     - Check health of all services"
	@echo "  update-images    - Pull latest Docker images"
	@echo ""
	@echo "Development:"
	@echo "  dev-setup        - Quick development setup"
	@echo "  seed-data        - Seed database with test data"
	@echo "  migrate          - Run database migrations"
	@echo "  test-connection  - Test database connections"

# Environment setup
init:
	@echo "⚙️  Initializing Docker environment..."
	@if [ ! -f .env ]; then cp .env.docker .env; echo "✅ Created .env from .env.docker"; fi
	@mkdir -p logs backups
	@echo "✅ Environment initialized"

# Build operations
build:
	@echo "🔨 Building Docker images..."
	@docker-compose build

# Service management
up:
	@echo "🚀 Starting all services..."
	@docker-compose up -d
	@echo "⏳ Waiting for services to be ready..."
	@sleep 10
	@$(MAKE) health-check

up-logs:
	@echo "🚀 Starting all services with logs..."
	@docker-compose up

down:
	@echo "🛑 Stopping all services..."
	@docker-compose down

stop:
	@echo "⏸️  Stopping services..."
	@docker-compose stop

restart:
	@echo "🔄 Restarting all services..."
	@docker-compose restart
	@sleep 5
	@$(MAKE) health-check

logs:
	@echo "📋 Service logs:"
	@docker-compose logs --tail=50

logs-follow:
	@echo "📋 Following service logs (Ctrl+C to exit)..."
	@docker-compose logs -f

status:
	@echo "📊 Service Status:"
	@docker-compose ps

# Individual service management
postgres-up:
	@echo "🐘 Starting PostgreSQL..."
	@docker-compose up -d postgres
	@sleep 5
	@docker-compose exec postgres pg_isready -U ai_agent -d ai_customer_service

redis-up:
	@echo "🔴 Starting Redis..."
	@docker-compose up -d redis
	@sleep 3
	@docker-compose exec redis redis-cli ping

elasticsearch-up:
	@echo "🔍 Starting Elasticsearch..."
	@docker-compose up -d elasticsearch
	@sleep 10
	@curl -f http://localhost:9200/_cluster/health || echo "⚠️  Elasticsearch may still be starting"

neo4j-up:
	@echo "🕸️  Starting Neo4j..."
	@docker-compose up -d neo4j
	@sleep 10
	@echo "Neo4j Browser: http://localhost:7474"

mongodb-up:
	@echo "🍃 Starting MongoDB..."
	@docker-compose up -d mongodb
	@sleep 5
	@docker-compose exec mongodb mongosh --eval "db.adminCommand('ping')"

kafka-up:
	@echo "📨 Starting Kafka and Zookeeper..."
	@docker-compose up -d zookeeper kafka
	@sleep 15
	@docker-compose exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092

# Database operations
db-reset:
	@echo "🔄 Resetting database schema..."
	@docker-compose exec postgres psql -U ai_agent -d ai_customer_service -f /docker-entrypoint-initdb.d/01-schema.sql
	@echo "✅ Database schema reset complete"

db-connect:
	@echo "🔗 Connecting to PostgreSQL..."
	@docker-compose exec postgres psql -U ai_agent -d ai_customer_service

db-backup:
	@echo "💾 Creating database backup..."
	@mkdir -p backups
	@docker-compose exec postgres pg_dump -U ai_agent -d ai_customer_service > backups/ai_customer_service_$$(date +%Y%m%d_%H%M%S).sql
	@echo "✅ Backup created: backups/ai_customer_service_$$(date +%Y%m%d_%H%M%S).sql"

db-restore:
	@echo "📂 Available backups:"
	@ls -la backups/
	@echo ""
	@echo "Usage: make db-restore FILE=backups/your-backup.sql"
	@if [ -n "$(FILE)" ]; then \
		docker-compose exec -T postgres psql -U ai_agent -d ai_customer_service < $(FILE); \
		echo "✅ Database restored from $(FILE)"; \
	fi

# Maintenance operations
clean:
	@echo "🧹 Cleaning up containers and volumes..."
	@docker-compose down -v --remove-orphans
	@echo "✅ Cleanup complete"

prune:
	@echo "🧹 Cleaning Docker system..."
	@docker system prune -f
	@docker volume prune -f
	@echo "✅ Docker system cleaned"

health-check:
	@echo "🏥 Checking service health..."
	@echo "PostgreSQL: $$(docker-compose exec postgres pg_isready -U ai_agent -d ai_customer_service && echo '✅ Healthy' || echo '❌ Unhealthy')"
	@echo "Redis: $$(docker-compose exec redis redis-cli ping && echo '✅ Healthy' || echo '❌ Unhealthy')"
	@echo "Elasticsearch: $$(curl -s -f http://localhost:9200/_cluster/health > /dev/null && echo '✅ Healthy' || echo '❌ Unhealthy')"
	@echo "Neo4j: $$(docker-compose exec neo4j neo4j status > /dev/null 2>&1 && echo '✅ Healthy' || echo '❌ Unhealthy')"
	@echo "MongoDB: $$(docker-compose exec mongodb mongosh --eval "db.adminCommand('ping')" > /dev/null 2>&1 && echo '✅ Healthy' || echo '❌ Unhealthy')"
	@echo "Kafka: $$(docker-compose exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092 > /dev/null 2>&1 && echo '✅ Healthy' || echo '❌ Unhealthy')"

update-images:
	@echo "🔄 Updating Docker images..."
	@docker-compose pull
	@echo "✅ Images updated"

# Development operations
dev-setup:
	@echo "🚀 Setting up development environment..."
	@$(MAKE) init
	@$(MAKE) build
	@$(MAKE) up
	@echo "✅ Development environment ready!"
	@echo "API: http://localhost:8000"
	@echo "PostgreSQL: localhost:5432"
	@echo "Redis: localhost:6379"
	@echo "Elasticsearch: http://localhost:9200"
	@echo "Neo4j: http://localhost:7474"

seed-data:
	@echo "🌱 Seeding database with test data..."
	@docker-compose exec api python scripts/seed_database.py || echo "⚠️  Seed script not found or failed"

migrate:
	@echo "🚀 Running database migrations..."
	@docker-compose exec api alembic upgrade head || echo "⚠️  Migration script not found or failed"

test-connection:
	@echo "🔗 Testing database connections..."
	@echo "PostgreSQL connection test:"
	@docker-compose exec postgres psql -U ai_agent -d ai_customer_service -c "SELECT version();"
	@echo ""
	@echo "Redis connection test:"
	@docker-compose exec redis redis-cli ping
	@echo ""
	@echo "MongoDB connection test:"
	@docker-compose exec mongodb mongosh --eval "db.adminCommand('ping')"

# Utility operations
shell-postgres:
	@docker-compose exec postgres bash

shell-redis:
	@docker-compose exec redis sh

shell-api:
	@docker-compose exec api bash

logs-postgres:
	@docker-compose logs -f postgres

logs-api:
	@docker-compose logs -f api

# Quick shortcuts
quick-start: init build up health-check
	@echo "🎉 Quick start complete!"
	@echo "Run 'make status' to check service status"
	@echo "Run 'make logs-follow' to view logs"

stop-all: stop
	@echo "🛑 All services stopped"

restart-all: restart
	@echo "🔄 All services restarted"

# Cleanup shortcuts
clean-all: clean prune
	@echo "🧹 Complete cleanup finished"

# Help shortcut
h: help