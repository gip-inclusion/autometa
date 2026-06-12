#!/usr/bin/env python3
"""Pre-tool-use hook: en environnement live, restreint les chemins d'écriture de l'agent."""

import json
import os
import sys

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
    if env.get("AUTOMETA_ENV", "dev") == "dev":
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


if __name__ == "__main__":
    data = json.load(sys.stdin)
    path = data.get("tool_input", {}).get("file_path", "")
    if not path:
        sys.exit(0)
    msg = verdict(path, os.getcwd(), os.environ)
    if msg:
        print(msg, file=sys.stderr)
        sys.exit(2)
