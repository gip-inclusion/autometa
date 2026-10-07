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

# Why: un UUID a aussi la forme d'une clé — une seule forme valide les jetons des deux modes.
KEY_RE = re.compile(r"[a-z0-9-]{1,64}")


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
    if not KEY_RE.fullmatch(key):
        raise ValueError(f"clé invalide : {key!r} (lettres minuscules, chiffres et tirets, 1 à 64 caractères)")
    label = label.strip()
    if not label:
        raise ValueError("libellé obligatoire")
    return label


def data_locations(session, slug: str) -> list[tuple[s3.S3Store, str]]:
    """Le dossier interne du tableau, puis le snapshot de chaque publication active."""
    active = session.scalars(
        select(DashboardPublication.publication_id).where(
            DashboardPublication.dashboard_slug == slug, DashboardPublication.unpublished_at.is_(None)
        )
    )
    return [(s3.interactive, f"{slug}/"), *((s3.publications, f"{slug}/{pid}/") for pid in active)]


def set_obfuscation(slug: str, obfuscate: bool) -> list[str]:
    """Bascule le mode des jetons : chaque déclinaison change de jeton, son fichier le suit ; renvoie les clés."""
    with get_db() as session:
        dashboard = session.scalar(select(Dashboard).where(Dashboard.slug == slug))
        if dashboard is None:
            raise DashboardNotFound(slug)
        if dashboard.obfuscate_variants == obfuscate:
            return []
        variants = session.scalars(
            select(DashboardVariant).where(DashboardVariant.dashboard_slug == slug).order_by(DashboardVariant.key)
        ).all()
        tokens = {v.key: str(uuid.uuid4()) if obfuscate else v.key for v in variants}
        # Why: copier partout avant de changer un seul jeton — une copie ratée laisse le tableau
        # entier dans l'ancien mode, liens et fichiers intacts.
        copied = []
        for store, prefix in data_locations(session, slug):
            present = {f["path"] for f in store.list_files(f"{prefix}data/", raise_errors=True)}
            for v in variants:
                old = f"{prefix}{data_path(v.token)}"
                if old not in present:
                    continue
                content = store.download(old)
                if content is None or not store.upload(f"{prefix}{data_path(tokens[v.key])}", content):
                    raise ValueError(f"copie S3 échouée, aucun jeton n'a changé : {old}")
                copied.append((store, old))
        local = config.INTERACTIVE_DIR / slug
        renames = [(local / data_path(v.token), local / data_path(tokens[v.key])) for v in variants]
        for v in variants:
            v.token = tokens[v.key]
        dashboard.obfuscate_variants = obfuscate
    for old, new in renames:
        if old.exists():
            old.rename(new)
    leftovers = [path for store, path in copied if not store.delete(path)]
    if leftovers:
        raise ValueError(f"jetons changés, mais fichiers de l'ancien mode non supprimés : {', '.join(leftovers)}")
    return list(tokens)


def add_variant(slug: str, key: str, label: str) -> dict:
    """Déclare une déclinaison ; son jeton est la clé, ou un UUID sur un tableau obfusqué."""
    label = validate_variant(key, label)
    with get_db() as session:
        obfuscated = session.scalar(select(Dashboard.obfuscate_variants).where(Dashboard.slug == slug))
        if obfuscated is None:
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
            token=str(uuid.uuid4()) if obfuscated else key,
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
        for store, prefix in data_locations(session, slug):
            if not store.delete(f"{prefix}{path}"):
                raise ValueError(f"fichier S3 non supprimé, déclinaison conservée : {prefix}{path}")
        (config.INTERACTIVE_DIR / slug / path).unlink(missing_ok=True)
        session.delete(variant)
        session.flush()
    return True


def exposed_tokens(files: Iterable[tuple[str, bytes]], variants: list[dict]) -> list[str]:
    """Fichiers dont le contenu contient un jeton obfusqué — le nom de fichier ne compte pas."""
    # Why: un jeton égal à sa clé est lisible par construction, il n'a rien à cacher.
    key_by_token = {v["token"].encode(): v["key"] for v in variants if v["token"] != v["key"]}
    if not key_by_token:
        return []
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
