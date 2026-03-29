.PHONY: dev test lint format security ci migrate

dev:
	autometa

migrate:
	uv run --frozen alembic upgrade head

lint:
	uv run --frozen ruff check web/ lib/ scripts/ tests/
	uv run --frozen ruff format --check web/ lib/ scripts/ tests/

format:
	uv run --frozen ruff check --fix web/ lib/ scripts/ tests/
	uv run --frozen ruff format web/ lib/ scripts/ tests/

security:
	uv run --frozen bandit -r web/ lib/ scripts/ -c pyproject.toml --severity-level medium --confidence-level high -q
	uv export --frozen --no-hashes --no-emit-project > /tmp/requirements.txt && uv run --frozen pip-audit -r /tmp/requirements.txt --ignore-vuln CVE-2026-4539

test:
	uv run --frozen pytest tests/ -q --tb=short -m "not integration" --ignore=tests/test_metabase_answers.py

ci: lint security test
