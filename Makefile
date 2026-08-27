.PHONY: setup doctor dev claude hooks install-hooks test test-cov test-unit-cov \
        test-integration-cov coverage-report e2e diff-cover lint format security ci \
        migrate check-migrations paved-road paved-road-baseline
        migrate check-migrations paved-road paved-road-baseline

# Vulnérabilités amont sans correctif disponible, revues à chaque passe de `make security`.
PIP_AUDIT_IGNORES := --ignore-vuln CVE-2026-4539 --ignore-vuln CVE-2026-3219

# Branche de comparaison des gates de diff. La CI la surcharge avec la base réelle de la PR :
# c'est ce paramètre qui permet à la CI d'appeler ces cibles au lieu de réécrire les commandes.
BASE ?= main
LABELS ?=

setup:
	uv sync --group dev
	test -f .env || cp .env.example .env
	docker compose up -d --wait db redis minio
	docker compose up -d minio-init
	uv run --frozen alembic upgrade head
	@$(MAKE) --no-print-directory hooks
	@$(MAKE) --no-print-directory install-hooks
	@$(MAKE) --no-print-directory doctor

doctor:
	@uv run --frozen python scripts/doctor.py

dev:
	uv run --frozen autometa

# Le parcours paved road vit dans un plugin du dépôt : la commande `/paved-road:paved-road` et ses
# sous-agents ne sont chargés que par cette cible, jamais par un `claude` lancé à la main.
claude:
	claude --plugin-dir plugins/paved-road

hooks:
	uv run --frozen pre-commit install --hook-type pre-commit

migrate:
	uv run --frozen alembic upgrade head

check-migrations:
	uv run --frozen alembic check
	uv run --frozen python scripts/check_migration_backfill.py

lint:
	uv run --frozen ruff check
	uv run --frozen ruff format --check
	uv run --frozen python scripts/check_test_quality.py tests browser
	uv run --frozen python scripts/check_http_timeouts.py
	uv run --frozen ruff check --select S608,BLE001 --statistics --exit-zero

format:
	uv run --frozen ruff check --fix
	uv run --frozen ruff format

security:
	uv run --frozen bandit -r web/ lib/ skills/ -c pyproject.toml --severity-level medium --confidence-level high -q
	uv run --frozen python scripts/check_route_auth.py
	uv run --frozen python scripts/check_required_checks.py
	uv export --frozen --no-hashes --no-emit-project > /tmp/requirements.txt
	uv run --frozen pip-audit -r /tmp/requirements.txt $(PIP_AUDIT_IGNORES)

test:
	DATABASE_URL= REDIS_URL= uv run --frozen pytest tests/ infra/ -q --tb=short \
		-p no:cacheprovider -m "not integration and not e2e and not external and not browser"

# Les seuils vivent dans gates.toml, couvert par CODEOWNERS : abaisser un plancher reste un acte visible.
# Un couloir par cible, pour que la CI appelle ces cibles au lieu de réécrire les commandes :
# sans cela, « la CI relance le même check » est faux et la dérive s'installe sans qu'on la voie.
test-unit-cov:
	DATABASE_URL= REDIS_URL= COVERAGE_FILE=.coverage.unit uv run --frozen pytest tests/ infra/ -q \
		-p no:cacheprovider -m "not integration and not e2e and not external and not browser" \
		--cov --cov-branch --cov-config=gates.toml --cov-fail-under=0 --cov-report=

test-integration-cov:
	COVERAGE_FILE=.coverage.integration uv run --frozen pytest tests/ -q -m "(integration or e2e) and not browser" \
		--cov --cov-branch --cov-config=gates.toml --cov-fail-under=0 --cov-report=

coverage-report:
	uv run --frozen coverage combine .coverage.unit .coverage.integration
	uv run --frozen coverage report --rcfile=gates.toml
	uv run --frozen coverage xml --rcfile=gates.toml

test-cov:
	rm -f .coverage .coverage.unit .coverage.integration coverage.xml
	@$(MAKE) --no-print-directory test-unit-cov
	@$(MAKE) --no-print-directory test-integration-cov
	@$(MAKE) --no-print-directory coverage-report

# Parcours de navigateur — exige une application servie (`make dev` dans un autre terminal),
# ou E2E_BASE_URL pointant sur une review app.
e2e:
	uv run --frozen playwright install chromium
	uv run --frozen pytest browser -q -m browser

diff-cover:
	uv run --frozen diff-cover coverage.xml --compare-branch=origin/$(BASE) --config-file gates.toml

paved-road:
	@uv run --frozen python scripts/check_paved_road.py --base origin/$(BASE) $(LABELS)

# Un shim, pas une copie : le contenu réel reste versionné dans .githooks/ et suit la branche.
# `core.hooksPath` est volontairement laissé tel quel — il désactiverait le pre-commit du dépôt.
install-hooks:
	@printf '#!/usr/bin/env bash\nhook="$$(git rev-parse --show-toplevel)/.githooks/pre-push"\n[ -x "$$hook" ] && exec "$$hook" "$$@"\nexit 0\n' \
		> "$$(git rev-parse --git-common-dir)/hooks/pre-push"
	@chmod +x "$$(git rev-parse --git-common-dir)/hooks/pre-push"
	@echo "Hook pre-push installé — lint et tests unitaires avant chaque push."

ci: lint security check-migrations test-cov diff-cover paved-road

ci: lint security check-migrations test diff-cover paved-road

paved-road-baseline:
	uv run --frozen python scripts/paved_road_baseline.py --days $(or $(DAYS),90)

.PHONY: paved-road-start paved-road-status paved-road-checks paved-road-advance

PAVED_ROAD := uv run --frozen python scripts/paved_road_cli.py $(if $(FEATURE),--feature $(FEATURE))

paved-road-start:
	@$(PAVED_ROAD) start

paved-road-status:
	@$(PAVED_ROAD) status

paved-road-checks:
	@$(PAVED_ROAD) check $(CHECK)

paved-road-advance:
	@$(PAVED_ROAD) advance $(if $(DOD),--dod $(DOD) --command "$(CMD)") $(if $(PATHS),--paths $(PATHS))
