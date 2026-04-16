.PHONY: dev test lint format security ci migrate

dev:
	autometa

migrate:
	uv run --locked alembic upgrade head

lint:
	uv run --locked ruff check web/ lib/ tests/
	uv run --locked ruff format --check web/ lib/ tests/

format:
	uv run --locked ruff check --fix web/ lib/ tests/
	uv run --locked ruff format web/ lib/ tests/

security:
	uv run --locked bandit -r web/ lib/ -c pyproject.toml --severity-level medium --confidence-level high -q
	uv export --locked --no-hashes --no-emit-project > /tmp/requirements.txt && uv run --locked pip-audit -r /tmp/requirements.txt --ignore-vuln CVE-2026-4539

test:
	uv run --locked pytest tests/ -q --tb=short -m "not integration"

ci: lint security test
