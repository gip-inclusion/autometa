"""Déclinaisons d'un tableau de bord : une clé lisible, un libellé, un jeton qui ouvre le lien."""

import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from lib.dashboard_errors import DashboardNotFound
from web import config, s3
from web.db import get_db
from web.models import Dashboard, DashboardVariant

KEY_RE = re.compile(r"^[a-z0-9-]{1,64}$")
TOKEN_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def data_path(token: str) -> str:
    """Chemin du fichier de données d'une déclinaison, relatif au dossier du tableau de bord."""
    return f"data/{token}.json"


def to_dict(variant: DashboardVariant) -> dict:
    return {
        "key": variant.key,
        "label": variant.label,
        "token": variant.token,
        "path": data_path(variant.token),
        "url": f"/interactive/{variant.dashboard_slug}/?q={variant.token}",
    }


def list_variants(slug: str) -> list[dict]:
    """Déclinaisons déclarées d'un tableau de bord, par clé."""
    with get_db() as session:
        rows = session.scalars(
            select(DashboardVariant).where(DashboardVariant.dashboard_slug == slug).order_by(DashboardVariant.key)
        )
        return [to_dict(v) for v in rows]


def add_variant(slug: str, key: str, label: str) -> dict:
    """Déclare une déclinaison ; le jeton est généré ici et ne change plus."""
    if not KEY_RE.match(key):
        raise ValueError(f"clé invalide : {key!r} (lettres minuscules, chiffres et tirets, 1 à 64 caractères)")
    label = label.strip()
    if not label:
        raise ValueError("libellé obligatoire")
    with get_db() as session:
        if session.scalar(select(Dashboard.slug).where(Dashboard.slug == slug)) is None:
            raise DashboardNotFound(slug)
        existing = session.scalar(
            select(DashboardVariant).where(DashboardVariant.dashboard_slug == slug, DashboardVariant.key == key)
        )
        if existing is not None:
            raise ValueError(f"déclinaison déjà déclarée : {key}")
        variant = DashboardVariant(
            dashboard_slug=slug,
            key=key,
            label=label,
            token=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc),
        )
        session.add(variant)
        session.flush()
        return to_dict(variant)


def remove_variant(slug: str, key: str) -> bool:
    """Retire une déclinaison et son fichier de données interne. False si elle n'existe pas."""
    with get_db() as session:
        variant = session.scalar(
            select(DashboardVariant).where(DashboardVariant.dashboard_slug == slug, DashboardVariant.key == key)
        )
        if variant is None:
            return False
        path = data_path(variant.token)
        session.delete(variant)
        session.flush()
    (config.INTERACTIVE_DIR / slug / path).unlink(missing_ok=True)
    s3.interactive.delete(f"{slug}/{path}")
    return True


def exposed_tokens(folder: Path, variants: list[dict]) -> list[str]:
    """Fichiers du dossier dont le contenu contient un jeton — le nom de fichier ne compte pas."""
    problems = []
    for path in sorted(p for p in folder.rglob("*") if p.is_file()):
        content = path.read_bytes()
        for variant in variants:
            if variant["token"].encode() in content:
                problems.append(f"{path.relative_to(folder)} expose le jeton de {variant['key']}")
    return problems
