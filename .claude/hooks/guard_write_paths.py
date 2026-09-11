#!/usr/bin/env python3
"""Pre-tool-use hook: sur les serveurs, restreint les chemins d'écriture de l'agent."""

import json
import os
import sys
from pathlib import Path

# Why: hook autonome lancé hors package — la racine du dépôt doit être sur sys.path
# pour partager web/environment.py (stdlib uniquement) avec l'application.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from lib.facade_imports import FACADE, facade_violations  # noqa: E402
from web.environment import Environment  # noqa: E402

BLOCK_BAD_ENV_MSG = (
    "Écriture refusée : AUTOMETA_ENV invalide — corriger la variable d'environnement (voir web/environment.py)."
)
BLOCK_CODE_MSG = (
    "Écriture refusée : le code de l'application est immuable en prod (baked dans l'image Docker, "
    "toute modification serait perdue au redéploiement). Chemins autorisés : data/, .claude/, /tmp. "
    "Pour persister des données, utiliser dashboard_storage — "
    "voir docs/interactive-dashboards.md § Persistance dashboard_storage."
)
BLOCK_GUARD_MSG = "Écriture refusée : la configuration des hooks de garde n'est pas modifiable par l'agent."
BLOCK_UNREGISTERED_MSG = (
    "Écriture refusée : TDB non enregistré dans la table dashboards — utiliser le skill "
    "create_dashboard (option --adopt pour enregistrer un dossier existant)."
)
BLOCK_FACADE_MSG = (
    "Écriture refusée : un tableau de bord n'importe que `{facade}` — {violations} n'offre aucune "
    "stabilité et sort du contrat versionné. Voir docs/interactive-dashboards.md."
)
BLOCK_ROOT_HTML_MSG = (
    "Écriture refusée : tout HTML accessible aux utilisateurs doit appartenir à un TDB enregistré "
    "(skill create_dashboard). La racine de data/interactive/ est réservée aux fichiers one-off non-HTML."
)


def slug_exists(slug):
    url = os.environ.get("DATABASE_URL")
    if not url:
        return True
    try:
        import psycopg2

        conn = psycopg2.connect(url, connect_timeout=2)
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM dashboards WHERE slug = %(slug)s", {"slug": slug})
            return cur.fetchone() is not None
        finally:
            conn.close()
    except Exception:  # Why: fail-open — un incident DB ne doit jamais bloquer toutes les écritures.
        return True


def verdict(path, repo_root, env, exists=slug_exists):
    try:
        environment = Environment.current(env.get("AUTOMETA_ENV"))
    except ValueError:  # Why: fail-closed — une valeur inconnue ne doit pas désactiver la garde.
        return BLOCK_BAD_ENV_MSG
    if not environment.is_server:
        return None
    real = os.path.realpath(path)
    _tmp = os.path.realpath("/tmp")
    if real == _tmp or real.startswith(_tmp + os.sep):
        return None
    rel = os.path.relpath(real, os.path.realpath(repo_root))
    if rel.startswith(".."):
        return BLOCK_CODE_MSG
    parts = rel.split(os.sep)
    if parts[0] == ".claude":
        if len(parts) >= 2 and (parts[1].startswith("settings") or parts[1] == "hooks"):
            return BLOCK_GUARD_MSG
        return None
    if parts[0] != "data":
        return BLOCK_CODE_MSG
    if len(parts) >= 3 and parts[1] == "interactive":
        if len(parts) == 3:
            return BLOCK_ROOT_HTML_MSG if parts[2].lower().endswith((".html", ".htm")) else None
        if not exists(parts[2]):
            return BLOCK_UNREGISTERED_MSG
    return None


# Why: le hook est le seul point où le code d'un TDB passe avant d'exister. `adopt_dashboard` et la
# création le contrôlent aussi, mais `update_dashboard` ne touche que des métadonnées : elle n'a rien
# à juger du code, et tout TDB antérieur à la façade la violerait par construction.
def facade_verdict(path, code, repo_root):
    """Refuse le code d'un tableau de bord qui importe hors de la façade — quel que soit l'environnement."""
    rel = os.path.relpath(os.path.realpath(path), os.path.realpath(repo_root)).split(os.sep)
    if len(rel) < 4 or rel[:2] != ["data", "interactive"] or not path.endswith(".py"):
        return None
    try:
        violations = facade_violations(code)
    except SyntaxError:  # Why: un fragment d'Edit n'est pas un module complet — le hook n'a rien à dire.
        return None
    if not violations:
        return None
    return BLOCK_FACADE_MSG.format(facade=FACADE, violations=", ".join(violations))


if __name__ == "__main__":
    data = json.load(sys.stdin)
    tool_input = data.get("tool_input", {})
    path = tool_input.get("file_path", "")
    if not path:
        sys.exit(0)
    code = tool_input.get("content") or tool_input.get("new_string") or ""
    # Why: le cwd du CLI n'est pas la racine du dépôt (session ouverte ailleurs) — le hook, lui, y vit.
    msg = verdict(path, REPO_ROOT, os.environ) or facade_verdict(path, code, REPO_ROOT)
    if msg:
        print(msg, file=sys.stderr)
        sys.exit(2)
