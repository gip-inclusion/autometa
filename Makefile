.PHONY: dev hooks test test-cov diff-cover lint format security ci migrate check-migrations

dev:
	uv run --frozen autometa

hooks:
	uv run --frozen pre-commit install --hook-type pre-commit

migrate:
	uv run --frozen alembic upgrade head

check-migrations:
	uv run --frozen alembic check

lint:
	uv run --frozen ruff check
	uv run --frozen ruff format --check
	uv run --frozen python scripts/check_test_quality.py tests

format:
	uv run --frozen ruff check --fix
	uv run --frozen ruff format

security:
	uv run --frozen bandit -r web/ lib/ -c pyproject.toml --severity-level medium --confidence-level high -q
	uv export --frozen --no-hashes --no-emit-project > /tmp/requirements.txt && uv run --frozen pip-audit -r /tmp/requirements.txt --ignore-vuln CVE-2026-4539

test:
	DATABASE_URL= REDIS_URL= SLACK_BOT_TOKEN= SLACK_ALERT_CHANNEL= uv run --frozen pytest tests/ infra/ -q --tb=short \
		-p no:cacheprovider -m "not integration and not e2e and not external"

test-cov:
	rm -f .coverage .coverage.unit .coverage.integration coverage.xml
	DATABASE_URL= REDIS_URL= SLACK_BOT_TOKEN= SLACK_ALERT_CHANNEL= COVERAGE_FILE=.coverage.unit uv run --frozen pytest tests/ infra/ -q \
		-p no:cacheprovider -m "not integration and not e2e and not external" \
		--cov --cov-branch --cov-fail-under=0 --cov-report=
	SLACK_BOT_TOKEN= SLACK_ALERT_CHANNEL= COVERAGE_FILE=.coverage.integration uv run --frozen pytest tests/ -q -m "integration or e2e" \
		--cov --cov-branch --cov-fail-under=0 --cov-report=
	uv run --frozen coverage combine .coverage.unit .coverage.integration
	uv run --frozen coverage report
	uv run --frozen coverage xml

diff-cover:
	uv run --frozen diff-cover coverage.xml --compare-branch=origin/main --config-file pyproject.toml

ci: lint security check-migrations test-cov diff-cover
