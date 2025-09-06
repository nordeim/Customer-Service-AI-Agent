# Docker Infrastructure Setup for AI Customer Service Agent

This document provides comprehensive instructions for setting up the Docker infrastructure for the AI Customer Service Agent project.

## Overview

The Docker setup includes:
- **PostgreSQL 16-alpine** - Primary database with vector extensions
- **Redis 7-alpine** - Caching and session management
- **Elasticsearch 8.11.3** - Full-text search and analytics
- **Neo4j 5.15.0** - Graph database for relationships
- **MongoDB 7.0.5** - Session storage
- **Kafka 3.6.1** - Message streaming with Zookeeper
- **FastAPI Application** - Main API server

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 1.29+
- 8GB+ available RAM
- 10GB+ available disk space

## Quick Start

1. **Clone and setup environment:**
   ```bash
   # Copy the Docker environment file
   cp .env.docker .env
   
   # Copy the application environment template
   cp .env.example .env.local
   ```

2. **Start the infrastructure:**
   ```bash
   # Using the convenience script
   ./scripts/docker-start.sh up --build
   
   # Or using docker-compose directly
   docker-compose up -d --build
   ```

3. **Check service health:**
   ```bash
   ./scripts/docker-start.sh status
   # or
   docker-compose ps
   ```

## Service URLs and Ports

| Service | Port | URL | Description |
|---------|------|-----|-------------|
| PostgreSQL | 5432 | localhost:5432 | Primary database |
| Redis | 6379 | localhost:6379 | Cache and sessions |
| Elasticsearch | 9200 | localhost:9200 | Search engine |
| Neo4j Browser | 7474 | localhost:7474 | Graph database UI |
| Neo4j Bolt | 7687 | localhost:7687 | Graph database API |
| MongoDB | 27017 | localhost:27017 | Session storage |
| Kafka | 9092 | localhost:9092 | Message broker |
| Kafka (external) | 29092 | localhost:29092 | External access |
| Zookeeper | 2181 | localhost:2181 | Kafka coordinator |
| API Server | 8000 | localhost:8000 | Main application |

## Database Configuration

### PostgreSQL 16-alpine
- **Database**: `ai_customer_service`
- **User**: `ai_agent`
- **Extensions**: uuid-ossp, pgcrypto, pg_trgm, btree_gin, btree_gist, hstore, pg_stat_statements, vector
- **Custom Types**: conversation_status, conversation_channel, sentiment_label, emotion_label, model_provider
- **Row Level Security**: Enabled for multi-tenancy

### Schema Structure
```
core         - Business entities (organizations, users, conversations, messages)
ai           - AI/ML components (knowledge entries, model interactions)
analytics    - Materialized views for reporting
audit        - Compliance and activity logs
cache        - Performance optimization
tegration    - External system sync (Salesforce)
monitoring   - Helper views for monitoring
```

## Management Commands

### Using the convenience script:
```bash
# Start all services
./scripts/docker-start.sh up --build

# Start in detached mode
./scripts/docker-start.sh up -d --build

# View logs
./scripts/docker-start.sh logs

# Check status
./scripts/docker-start.sh status

# Stop services
./scripts/docker-start.sh stop

# Stop and remove everything
./scripts/docker-start.sh down

# Clean up volumes and images
./scripts/docker-start.sh clean
```

### Direct Docker Compose commands:
```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Scale specific services
docker-compose up -d --scale api=3

# Restart specific service
docker-compose restart postgres

# Execute commands in containers
docker-compose exec postgres psql -U ai_agent -d ai_customer_service
docker-compose exec redis redis-cli
docker-compose exec api python -m pytest tests/
```

## Health Checks

All services include health checks with the following configuration:

- **PostgreSQL**: `pg_isready` command
- **Redis**: `redis-cli ping` command  
- **Elasticsearch**: HTTP health endpoint
- **Neo4j**: Built-in status command
- **MongoDB**: `mongosh` ping command
- **Kafka**: Broker API versions check
- **API**: HTTP health endpoint

## Data Persistence

Docker volumes are used for data persistence:
- `postgres_data` - PostgreSQL data
- `redis_data` - Redis data
- `elasticsearch_data` - Elasticsearch indices
- `neo4j_data` - Neo4j graph data
- `neo4j_logs` - Neo4j logs
- `mongodb_data` - MongoDB collections
- `kafka_data` - Kafka topics and logs

## Performance Tuning

### PostgreSQL Configuration
The PostgreSQL container includes optimized settings:
- `shared_buffers = 256MB`
- `work_mem = 4MB`
- `effective_cache_size = 1GB`
- `random_page_cost = 1.1`
- Vector extension enabled for embeddings

### Resource Limits
Uncomment and adjust resource limits in `.env.docker`:
```bash
POSTGRES_MEMORY_LIMIT=1g
POSTGRES_CPUS_LIMIT=1.0
ELASTICSEARCH_MEMORY_LIMIT=1g
KAFKA_MEMORY_LIMIT=1g
```

## Security

### Default Credentials
**IMPORTANT**: Change default passwords in production:
- PostgreSQL: `SecurePass123!`
- Neo4j: `SecureNeo4j123!`
- MongoDB: `SecureMongo123!`

### Network Security
- Services communicate over isolated Docker network
- No external access to databases by default
- API server exposed only on localhost:8000

## Troubleshooting

### Port Conflicts
If ports are already in use:
1. Check what's using the ports: `lsof -i :5432`
2. Modify port mappings in `.env.docker`
3. Or stop conflicting services

### Memory Issues
For systems with limited memory:
1. Reduce Elasticsearch heap: `ES_JAVA_OPTS=-Xms256m -Xmx256m`
2. Disable unnecessary services in docker-compose.yml
3. Use resource limits in `.env.docker`

### Database Connection Issues
1. Check PostgreSQL logs: `docker-compose logs postgres`
2. Verify schema was applied: `docker-compose exec postgres psql -U ai_agent -d ai_customer_service -c "\dt"`
3. Check network connectivity: `docker network ls`

### Service Startup Failures
1. Check service logs: `docker-compose logs [service-name]`
2. Verify Docker daemon is running
3. Check available disk space: `docker system df`
4. Clean up if needed: `docker system prune`

## Development Workflow

1. **Start infrastructure**: `./scripts/docker-start.sh up -d`
2. **Wait for health checks**: `./scripts/docker-start.sh status`
3. **Run migrations**: `docker-compose exec api alembic upgrade head`
4. **Start development**: Edit code with auto-reload enabled
5. **Run tests**: `docker-compose exec api python -m pytest`
6. **View logs**: `docker-compose logs -f api`

## Production Considerations

- Use external managed databases (RDS, Cloud SQL, etc.)
- Implement proper backup strategies
- Use Docker secrets for sensitive data
- Set up monitoring and alerting
- Configure SSL/TLS for all connections
- Use load balancers for API scaling
- Implement log aggregation

## Monitoring

Access service-specific monitoring:
- **PostgreSQL**: `docker-compose exec postgres psql -c "SELECT * FROM pg_stat_activity;"`
- **Redis**: `docker-compose exec redis redis-cli INFO`
- **Elasticsearch**: `curl localhost:9200/_cluster/health`
- **Neo4j**: Open browser at http://localhost:7474

## Cleanup

To completely remove all containers, volumes, and networks:
```bash
./scripts/docker-start.sh clean
# or
docker-compose down -v --remove-orphans
docker system prune -f
```

## Support

For issues with the Docker setup:
1. Check service logs first
2. Verify health check status
3. Review resource utilization
4. Check GitHub issues for known problems