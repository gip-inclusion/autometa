"""Déclinaisons d'un tableau de bord : une clé lisible, un libellé, un jeton qui ouvre le lien."""

import re
import uuid
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from lib.dashboard_errors import DashboardNotFound
from web import config, s3
from web.db import get_db
from web.models import Dashboard, DashboardPublication, DashboardVariant

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


def validate_variant(key: str, label: str) -> str:
    """Refuse une clé ou un libellé hors format ; renvoie le libellé nettoyé."""
    if not KEY_RE.match(key):
        raise ValueError(f"clé invalide : {key!r} (lettres minuscules, chiffres et tirets, 1 à 64 caractères)")
    label = label.strip()
    if not label:
        raise ValueError("libellé obligatoire")
    return label


def add_variant(slug: str, key: str, label: str) -> dict:
    """Déclare une déclinaison ; le jeton est généré ici et ne change plus."""
    label = validate_variant(key, label)
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
        try:
            session.flush()
        except IntegrityError as exc:
            # Why: deux déclarations simultanées passent toutes deux le SELECT ; la contrainte
            # d'unicité tranche, et l'appelant reçoit le même refus qu'un doublon ordinaire.
            raise ValueError(f"déclinaison déjà déclarée : {key}") from exc
        return to_dict(variant)


def remove_variant(slug: str, key: str) -> bool:
    """Retire une déclinaison et son fichier de données, interne et dans chaque snapshot publié."""
    with get_db() as session:
        variant = session.scalar(
            select(DashboardVariant).where(DashboardVariant.dashboard_slug == slug, DashboardVariant.key == key)
        )
        if variant is None:
            return False
        path = data_path(variant.token)
        # Why: les fichiers d'abord, la ligne ensuite — une ligne disparue avec un fichier encore en
        # ligne laisserait un lien vivant qu'aucun contrôle ne verrait plus.
        if not s3.interactive.delete(f"{slug}/{path}"):
            raise ValueError(f"fichier S3 non supprimé, déclinaison conservée : {slug}/{path}")
        active = session.scalars(
            select(DashboardPublication.publication_id).where(
                DashboardPublication.dashboard_slug == slug, DashboardPublication.unpublished_at.is_(None)
            )
        )
        for publication_id in active:
            s3.publications.delete(f"{slug}/{publication_id}/{path}")
        (config.INTERACTIVE_DIR / slug / path).unlink(missing_ok=True)
        session.delete(variant)
        session.flush()
    return True


def exposed_tokens(files: Iterable[tuple[str, bytes]], variants: list[dict]) -> list[str]:
    """Fichiers dont le contenu contient un jeton — le nom de fichier ne compte pas."""
    if not variants:
        return []
    key_by_token = {v["token"].encode(): v["key"] for v in variants}
    pattern = re.compile(b"|".join(re.escape(token) for token in key_by_token))
    problems = []
    for name, content in files:
        for token in sorted(set(pattern.findall(content))):
            problems.append(f"{name} expose le jeton de {key_by_token[token]}")
    return problems


def folder_files(folder: Path) -> Iterable[tuple[str, bytes]]:
    for path in sorted(p for p in folder.rglob("*") if p.is_file()):
        yield str(path.relative_to(folder)), path.read_bytes()


def s3_files(slug: str) -> Iterable[tuple[str, bytes]]:
    prefix = f"{slug}/"
    for entry in s3.interactive.list_files(prefix):
        content = s3.interactive.download(entry["path"])
        if content is not None:
            yield entry["path"][len(prefix) :], content
