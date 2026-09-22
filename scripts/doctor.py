"""Diagnostique l'environnement de développement local."""

# Chaque panne se restitue en une phrase française qui dit quoi faire. Le fichier .env est lu
# comme un fichier, pas comme de l'environnement : le diagnostic doit tenir même quand
# l'application ne démarre pas.

import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx
import redis
import sqlalchemy
from dotenv import dotenv_values
from sqlalchemy.exc import SQLAlchemyError

ENV_FILE = Path(".env")
CREDENTIALS_FILE = Path.home() / ".claude" / ".credentials.json"
BIOME = Path("node_modules") / ".bin" / "biome"


def check_docker(settings):
    if shutil.which("docker") is None:
        return "Docker n'est pas installé. Installez Docker Desktop : https://docs.docker.com/desktop/"
    if subprocess.run(["docker", "info"], capture_output=True, check=False).returncode != 0:
        return "Docker est installé mais ne tourne pas. Ouvrez l'application Docker, puis relancez `make doctor`."
    return None


def check_postgres(settings):
    url = settings.get("DATABASE_URL")
    if not url:
        return "DATABASE_URL est absent de .env. Reprenez la ligne correspondante de .env.example."
    try:
        sqlalchemy.create_engine(url, connect_args={"connect_timeout": 3}).connect().close()
    except SQLAlchemyError:
        return f"PostgreSQL ne répond pas sur {urlparse(url).netloc}. Lancez `make setup` pour démarrer les services."
    return None


def check_redis(settings):
    url = settings.get("REDIS_URL") or "redis://localhost:6379/0"
    try:
        redis.from_url(url, socket_connect_timeout=3).ping()
    except redis.RedisError:
        return f"Redis ne répond pas sur {url}. Lancez `make setup` pour démarrer les services."
    return None


def check_object_storage(settings):
    endpoint = settings.get("S3_ENDPOINT")
    if not endpoint:
        return None
    try:
        httpx.get(f"{endpoint}/minio/health/live", timeout=3)
    except httpx.RequestError:
        return f"Le stockage de fichiers ne répond pas sur {endpoint}. Lancez `make setup`."
    return None


def check_migrations(settings):
    result = subprocess.run(
        ["uv", "run", "--frozen", "alembic", "current"], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        return "L'état des migrations est illisible. Vérifiez d'abord PostgreSQL, puis lancez `make migrate`."
    if "(head)" not in result.stdout:
        return "La base de données n'est pas à jour. Lancez `make migrate`."
    return None


def check_agent_cli(settings):
    if settings.get("AGENT_BACKEND", "cli") != "cli":
        return None
    if shutil.which(settings.get("CLAUDE_CLI") or "claude") is None:
        return "La CLI Claude Code est absente. Installez-la : npm install -g @anthropic-ai/claude-code"
    return None


def warn_agent_auth(settings):
    if settings.get("CLAUDE_CODE_OAUTH_TOKEN") or CREDENTIALS_FILE.exists():
        return None
    return (
        "L'agent n'est pas authentifié. Lancez `claude` une fois pour vous connecter, "
        "ou renseignez CLAUDE_CODE_OAUTH_TOKEN dans .env."
    )


def warn_data_sources(settings):
    missing = [key for key in ("MATOMO_API_KEY", "METABASE_STATS_API_KEY") if not settings.get(key)]
    if not missing:
        return None
    return (
        f"Clés d'accès absentes ({', '.join(missing)}) : les analyses sur ces sources échoueront. "
        "Demandez-les à l'équipe et ajoutez-les à .env."
    )


# Why: ni le parcours, ni les hooks, ni `make lint` n'ont besoin de Node ou d'un navigateur. Les
# rendre bloquants prendrait le parcours en otage — c'est ce qu'on a refusé pour Docker et le smoke.
# Mais `make setup` ne les posait pas et `doctor` ne les regardait pas : le trou se découvrait en
# lançant `make lint-js` ou `make e2e`, c'est-à-dire trop tard.
def warn_front(settings):
    if shutil.which("npm") is None:
        return "npm est absent : Biome, seul filet du front, ne pourra pas tourner. Installez Node.js 20+."
    if not BIOME.exists():
        return "Les dépendances du front ne sont pas installées. Lancez `make lint-js`, qui les installe."
    return None


def playwright_cache(settings):
    """Où Playwright range ses navigateurs, selon la plateforme ou ce que .env impose."""
    if override := settings.get("PLAYWRIGHT_BROWSERS_PATH"):
        return Path(override)
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "ms-playwright"
    return Path.home() / ".cache" / "ms-playwright"


def warn_browser(settings):
    cache = playwright_cache(settings)
    if cache.is_dir() and any(cache.glob("chromium-*")):
        return None
    return (
        "Aucun navigateur Playwright installé : les tests sous `browser/` ne tourneront pas ici. "
        "Lancez `make browsers`. Le parcours n'en dépend pas — il n'exige que la présence du test."
    )


REQUIRED = [
    ("Docker", check_docker),
    ("PostgreSQL", check_postgres),
    ("Redis", check_redis),
    ("Stockage de fichiers", check_object_storage),
    ("Migrations", check_migrations),
    ("CLI de l'agent", check_agent_cli),
]

OPTIONAL = [
    ("Authentification de l'agent", warn_agent_auth),
    ("Front", warn_front),
    ("Navigateur", warn_browser),
    ("Sources de données", warn_data_sources),
]


def run(checks, settings, marker):
    problems = []
    for label, check in checks:
        problem = check(settings)
        if problem is None:
            print(f"  {'ok':<5} {label}")
        else:
            print(f"  {marker:<5} {label} — {problem}")
            problems.append(problem)
    return problems


def main() -> int:
    if not ENV_FILE.exists():
        print("Fichier .env absent. Lancez `make setup`, qui le crée à partir de .env.example.")
        return 1

    settings = dotenv_values(ENV_FILE)
    problems = run(REQUIRED, settings, "PANNE")
    run(OPTIONAL, settings, "note")

    # Why: cette dernière ligne est tout ce que le journal du parcours retient d'une panne
    # d'environnement. Un compte ne dit ni ce qui casse ni quoi faire : elle porte le geste.
    if problems:
        plural = "s" if len(problems) > 1 else ""
        print(f"\n{len(problems)} point{plural} à corriger. Commencer par : {problems[0]}")
        return 1
    print("\nEnvironnement prêt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
