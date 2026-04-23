.PHONY: dev test lint format security ci migrate

dev:
	uv run --frozen autometa

migrate:
	uv run --frozen alembic upgrade head

lint:
	uv run --frozen ruff check web/ lib/ tests/
	uv run --frozen ruff format --check web/ lib/ tests/

format:
	uv run --frozen ruff check --fix web/ lib/ tests/
	uv run --frozen ruff format web/ lib/ tests/

security:
	uv run --frozen bandit -r web/ lib/ -c pyproject.toml --severity-level medium --confidence-level high -q
	uv export --frozen --no-hashes --no-emit-project > /tmp/requirements.txt && uv run --frozen pip-audit -r /tmp/requirements.txt --ignore-vuln CVE-2026-4539

test:
	uv run --frozen pytest tests/ -q --tb=short -m "not integration"

ci: lint security test
