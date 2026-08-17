.PHONY: dev test diff-cover lint format security ci migrate check-migrations

dev:
	uv run --frozen autometa

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
	uv run --frozen pytest tests/ infra/ -q --tb=short -m "not integration and not external" \
		--cov --cov-branch \
		--cov-report=term-missing:skip-covered --cov-report=xml

diff-cover:
	uv run --frozen diff-cover coverage.xml --compare-branch=origin/main --config-file pyproject.toml

ci: lint security check-migrations test diff-cover

.PHONY: paved-road-baseline

paved-road-baseline:
	uv run --frozen python scripts/paved_road_baseline.py --days $(or $(DAYS),90)
