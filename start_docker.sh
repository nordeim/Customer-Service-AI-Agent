# from repo root
docker-compose down

# elasticsearch restarting because vm.max_map_count too low on the host Elasticsearch requires:
# sudo sysctl -w vm.max_map_count=262144
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

docker-compose up --build -d postgres redis neo4j mongodb zookeeper kafka elasticsearch

# Wait for green/yellow health: 
curl http://localhost:${ELASTICSEARCH_PORT:-9200}/_cluster/health
# check version to see 9.1.3
curl http://localhost:${ELASTICSEARCH_PORT:-9200}

# wait for services healthy, then:
docker-compose build --no-cache api
docker-compose up -d api
# docker-compose up --build -d api

# once container is built and running (or even if it’s restarting), you can exec into it and run:
docker exec -it ai-customer-service-api python -c "import sys; print(sys.path); import src.main; print('✅ src.main import OK')"

# run migrations
docker-compose exec api alembic upgrade head
