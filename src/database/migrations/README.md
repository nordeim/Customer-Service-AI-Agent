# Migrations Scaffold

This directory holds database migrations (Alembic). A full Alembic setup will be added in a later step. For now, this placeholder documents the intended layout:

- env.py: Alembic environment
- versions/: versioned migration scripts

To initialize later:
- alembic init -t async src/database/migrations
- configure SQLAlchemy URL from settings or env
- generate: alembic revision --autogenerate -m "init schema"
- upgrade: alembic upgrade head
