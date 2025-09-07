# from repo root
docker-compose down

docker-compose up --build -d postgres redis neo4j mongodb zookeeper kafka elasticsearch

# Wait for green/yellow health: 
curl http://localhost:${ELASTICSEARCH_PORT:-9200}/_cluster/health

# wait for services healthy, then:
docker-compose up --build -d api

# run migrations
docker-compose exec api alembic upgrade head
