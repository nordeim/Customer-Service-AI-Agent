pip install sqlalchemy[asyncio] asyncpg alembic pydantic pydantic-settings python-dotenv PyJWT passlib[bcrypt] cryptography python-json-logger ruff black mypy pytest pytest-asyncio pip-audit bandit

# generate key
python -c 'import secrets; print(secrets.token_hex(32))'

# run minimal
poetry run python scripts/test_business_logic.py

poetry run python scripts/test_ai_services.py

# docker-compose up -d postgres
# docker exec -it ai-customer-service-postgres psql -U ai_agent -d ai_customer_service -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"
