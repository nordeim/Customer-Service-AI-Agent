# from repo root
python -m venv .venv
source .venv/bin/activate

# install runtime deps
pip install -r requirements.txt

# export envs (example, pick secure values or use your .env management)
export POSTGRES_PASSWORD='SecurePass123!'
export MONGODB_PASSWORD='SecureMongo123!'
export NEO4J_PASSWORD='SecureNeo4j123!'
export SECRET_KEY='dev-secret'
export OPENAI_API_KEY=''  # optional for local
# ...set any other required secrets

# run migrations (if you use alembic in repo)
# (the repo includes migrations scaffold; ensure ALEMBIC config is present)
alembic upgrade head || echo "No alembic or migrations run"

# start uvicorn (use the proper module)
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
