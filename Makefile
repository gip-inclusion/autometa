.PHONY: setup doctor dev test diff-cover lint format security deps-audit ci migrate check-migrations

# Vulnérabilités amont sans correctif disponible — revues à chaque passe nightly du
# workflow Dependencies, qui exécute cette même cible.
PIP_AUDIT_IGNORES := --ignore-vuln CVE-2026-4539 --ignore-vuln CVE-2026-3219

setup:
	uv sync --group dev
	test -f .env || cp .env.example .env
	docker compose up -d --wait db redis minio
	docker compose up -d minio-init
	uv run --frozen alembic upgrade head
	@$(MAKE) --no-print-directory doctor

doctor:
	@uv run --frozen python scripts/doctor.py

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
	uv run --frozen ruff check --select S608,BLE001 --statistics --exit-zero

format:
	uv run --frozen ruff check --fix
	uv run --frozen ruff format

security:
	uv run --frozen bandit -r web/ lib/ -c pyproject.toml --severity-level medium --confidence-level high -q
	uv run --frozen python scripts/check_route_auth.py
	uv run --frozen python scripts/check_required_checks.py

deps-audit:
	uv export --frozen --no-hashes --no-emit-project > /tmp/requirements.txt
	uv run --frozen pip-audit -r /tmp/requirements.txt $(PIP_AUDIT_IGNORES)

test:
	uv run --frozen pytest tests/ infra/ -q --tb=short -m "not integration and not external" \
		--cov --cov-branch --cov-config=gates.toml \
		--cov-report=term-missing:skip-covered --cov-report=xml

diff-cover:
	uv run --frozen diff-cover coverage.xml --compare-branch=origin/main --config-file gates.toml

ci: lint security check-migrations test diff-cover

.PHONY: paved-road-baseline

paved-road-baseline:
	uv run --frozen python scripts/paved_road_baseline.py --days $(or $(DAYS),90)
