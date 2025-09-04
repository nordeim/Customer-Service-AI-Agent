PYTHON := python3
PIP := pip

.PHONY: help install lint format typecheck test test-cov security run build clean

help:
	@echo "Available targets: install, lint, format, typecheck, test, test-cov, security, run, build, clean"

install:
	$(PIP) install -U pip
	$(PIP) install -e .[dev]

lint:
	ruff check .
	black --check .
	test -f pyproject.toml && echo "ruff/black passed"

format:
	black .
	ruff check --fix .
	echo "Formatted with black and ruff"

typecheck:
	mypy src

test:
	pytest -q

test-cov:
	pytest -q --cov=src --cov-report=term-missing

security:
	pip-audit -r requirements.txt || true
	bandit -q -r src || true

run:
	$(PYTHON) -m src.api.main

build:
	@echo "Build placeholder (container build handled by CI/CD)"

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache __pycache__ dist build *.egg-info
