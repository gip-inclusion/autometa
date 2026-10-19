"""Inventaire des symboles du dépôt qu'utilisent les tableaux de bord : publié par le cron, vérifié par la CI."""

# Les scripts des TDB vivent sur S3, hors du dépôt : une PR ne voit pas ce qu'elle casse chez eux.
# Le cron facade-audit publie chaque matin quels symboles ils utilisent ; la CI
# (`python -m web.facade_manifest`) vérifie que chacun existe encore dans l'arbre de la PR.

import argparse
import functools
import importlib
import json
import logging
import sys
from collections import defaultdict
from datetime import datetime, timedelta

import httpx

from lib import facade_imports
from web import config, s3
from web.cron import s3_map
from web.environment import Environment
from web.helpers import sanitize_for_log, utcnow

logger = logging.getLogger(__name__)

# Why: lisible sans secret par la CI d'un dépôt public — des noms de symboles et de TDB, jamais de code.
MANIFEST_KEY = "contrat-tdb/manifest.json"
MANIFEST_URL = f"{config.PUBLIC_DASHBOARDS_PROD_URL}/{MANIFEST_KEY}"
# Why: le cron publie chaque matin ; au-delà, l'inventaire ne dit plus l'état de la prod.
STALE_AFTER = timedelta(days=3)


def dashboard_sources(slug: str) -> list[str]:
    """Tous les fichiers .py d'un tableau de bord : un cron.py peut importer ses voisins."""
    entries = s3.interactive.list_files(f"{slug}/", raise_errors=True)
    paths = [entry["path"] for entry in entries if entry["path"].endswith(".py")]
    return [content.decode(errors="replace") for content in s3_map(s3.interactive.download, paths) if content]


def build_manifest(tasks: list[dict]) -> dict:
    """Pour chaque symbole applicatif utilisé par un tableau de bord cronné, les slugs qui l'utilisent."""
    users = defaultdict(set)
    for task in tasks:
        # Why: les crons système sont du code du dépôt, que la CI voit déjà ; une publication n'a pas de cron.
        if task.get("source") != "s3":
            continue
        for source in dashboard_sources(task["slug"]):
            try:
                symbols = facade_imports.imported_symbols(source)
            except SyntaxError:
                logger.warning("manifeste : un fichier de %s est illisible, ignoré", sanitize_for_log(task["slug"]))
                continue
            for symbol in symbols:
                users[symbol].add(task["slug"])
    return {
        "generated_at": utcnow().isoformat(),
        "symbols": {symbol: sorted(slugs) for symbol, slugs in sorted(users.items())},
    }


def publish_manifest(manifest: dict) -> bool:
    """Dépose l'inventaire dans le bucket public de production ; ailleurs, ne fait rien."""
    # Why: la staging connaît aussi le bucket public de production ; son inventaire écraserait celui de la prod.
    if config.ENV != Environment.PROD or not config.PUBLIC_S3_BUCKET_PROD:
        logger.info("manifeste non publié hors production")
        return False
    content = json.dumps(manifest, ensure_ascii=False, indent=1).encode()
    return s3.put_object(config.PUBLIC_S3_BUCKET_PROD, MANIFEST_KEY, content, "application/json")


def resolves(symbol: str) -> bool:
    """Le plus long préfixe importable de `symbol`, puis ses attributs, existent-ils dans l'arbre courant ?"""
    parts = symbol.split(".")
    for end in range(len(parts), 0, -1):
        try:
            module = importlib.import_module(".".join(parts[:end]))
        except ImportError:
            continue
        try:
            functools.reduce(getattr, parts[end:], module)
        except AttributeError:
            return False
        return True
    return False


def missing_symbols(manifest: dict) -> dict[str, list[str]]:
    """Symboles de l'inventaire absents de l'arbre courant, avec les tableaux de bord qui les utilisent."""
    return {symbol: slugs for symbol, slugs in manifest["symbols"].items() if not resolves(symbol)}


def load_manifest(location: str) -> dict:
    if location.startswith("https://"):
        response = httpx.get(location, timeout=10)
        response.raise_for_status()
        return response.json()
    with open(location, encoding="utf-8") as f:
        return json.load(f)


def check(location: str) -> int:
    """Code de sortie de la CI : 1 si l'arbre courant a perdu un symbole qu'un tableau de bord utilise."""
    try:
        manifest = load_manifest(location)
    except (httpx.HTTPError, OSError, ValueError) as e:
        # Why: une panne du site public ne doit pas bloquer toutes les PR ; l'avertissement reste dans le job.
        print(f"::warning::inventaire des tableaux de bord illisible ({e}) : contrat non vérifié")
        return 0
    age = utcnow() - datetime.fromisoformat(manifest["generated_at"])
    if age > STALE_AFTER:
        print(
            f"::warning::inventaire des tableaux de bord vieux de {age.days} jours : le cron facade-audit tourne-t-il ?"
        )
    missing = missing_symbols(manifest)
    for symbol, slugs in sorted(missing.items()):
        print(f"::error::{symbol} a disparu, or il est utilisé par : {', '.join(slugs)}")
    if not missing:
        print(f"{len(manifest['symbols'])} symboles utilisés par les tableaux de bord, tous présents.")
    return 1 if missing else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Vérifie que l'arbre courant garde les symboles utilisés par les TDB.")
    parser.add_argument("--manifest", default=MANIFEST_URL, help="URL https ou chemin local de l'inventaire")
    sys.exit(check(parser.parse_args().manifest))
