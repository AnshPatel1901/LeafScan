.PHONY: help install dev migrate migrate-rollback test lint format clean

# ── Config ────────────────────────────────────────────────────────────────────
PYTHON     = python
PIP        = pip
UVICORN    = uvicorn
ALEMBIC    = alembic
PYTEST     = pytest

help:
	@echo ""
	@echo "Crop Disease Detection API — Developer Commands"
	@echo "================================================"
	@echo "  make install          Install all dependencies"
	@echo "  make dev              Run dev server with hot reload"
	@echo "  make migrate          Apply all pending DB migrations"
	@echo "  make migrate-rollback Roll back last migration"
	@echo "  make test             Run full test suite"
	@echo "  make test-unit        Run unit tests only"
	@echo "  make test-integration Run integration tests only"
	@echo "  make lint             Run ruff linter"
	@echo "  make format           Auto-format with ruff"
	@echo "  make clean            Remove cache and temp files"
	@echo ""

# ── Setup ─────────────────────────────────────────────────────────────────────

install:
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

# ── Development server ────────────────────────────────────────────────────────

dev:
	$(UVICORN) app.main:app \
		--host 0.0.0.0 \
		--port 8000 \
		--reload \
		--reload-dir app \
		--log-level debug

# ── Database migrations ───────────────────────────────────────────────────────

migrate:
	$(ALEMBIC) upgrade head

migrate-rollback:
	$(ALEMBIC) downgrade -1

migrate-new:
	@read -p "Migration message: " msg; \
	$(ALEMBIC) revision --autogenerate -m "$$msg"

# ── Testing ───────────────────────────────────────────────────────────────────

test:
	$(PYTEST) tests/ -v --tb=short

test-unit:
	$(PYTEST) tests/unit/ -v --tb=short

test-integration:
	$(PYTEST) tests/integration/ -v --tb=short

test-coverage:
	$(PYTEST) tests/ --cov=app --cov-report=html --cov-report=term-missing

# ── Code quality ──────────────────────────────────────────────────────────────

lint:
	ruff check app/ tests/

format:
	ruff format app/ tests/
	ruff check --fix app/ tests/

# ── Cleanup ───────────────────────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -name ".coverage" -delete
