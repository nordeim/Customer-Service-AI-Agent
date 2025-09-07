# from repo root
docker-compose up --build -d postgres redis elasticsearch neo4j mongodb zookeeper kafka
# wait for services healthy, then:
docker-compose up --build -d api

# run migrations
docker-compose exec api alembic upgrade head
