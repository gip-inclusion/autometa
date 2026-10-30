"""Contexte des équipes du backlog, rangé dans dashboard_storage et rafraîchi chaque jour."""

import json
import logging
from datetime import UTC, datetime, timedelta

from lib import backlog
from lib.dashboard_api import query_storage
from web import config

logger = logging.getLogger(__name__)

CREER = (
    "CREATE TABLE IF NOT EXISTS dashboard_storage.backlog_contexte "
    "(cle text PRIMARY KEY, contenu jsonb NOT NULL, genere_le timestamptz NOT NULL)"
)
ECRIRE = (
    "INSERT INTO dashboard_storage.backlog_contexte (cle, contenu, genere_le) "
    "VALUES ('courant', CAST(:contenu AS jsonb), CAST(:genere_le AS timestamptz)) "
    "ON CONFLICT (cle) DO UPDATE SET contenu = EXCLUDED.contenu, genere_le = EXCLUDED.genere_le"
)
LIRE = "SELECT contenu, genere_le FROM dashboard_storage.backlog_contexte WHERE cle = 'courant'"


def executer(sql: str, params: dict | None = None) -> dict:
    """Exécute une requête sur dashboard_storage, ou lève l'erreur qu'elle renvoie."""
    resultat = query_storage(sql, params)
    if not resultat.success:
        raise RuntimeError(f"dashboard_storage : {resultat.error}")
    return resultat.data


def enregistrer_contexte(contexte: dict) -> None:
    """Range le contexte, en remplaçant le précédent."""
    executer(CREER)
    executer(ECRIRE, {"contenu": json.dumps(contexte, ensure_ascii=False), "genere_le": contexte["genere_le"]})


def lire_contexte(age_max: timedelta = timedelta(days=1)) -> dict | None:
    """Le contexte rangé s'il a moins de age_max, sinon None."""
    executer(CREER)
    lignes = executer(LIRE)["rows"]
    if not lignes:
        return None
    contenu, genere_le = lignes[0]
    contenu = json.loads(contenu) if isinstance(contenu, str) else contenu
    genere_le = datetime.fromisoformat(genere_le) if isinstance(genere_le, str) else genere_le
    if datetime.now(UTC) - genere_le > age_max:
        return None
    return contenu


def contexte_courant() -> dict:
    """Le contexte rangé s'il est frais, sinon un contexte relu dans Notion, puis rangé."""
    contexte = lire_contexte()
    if contexte is None:
        contexte = backlog.charger_contexte()
        enregistrer_contexte(contexte)
    return contexte


def main() -> None:
    """Point d'entrée du cron quotidien."""
    if not config.NOTION_BACKLOG_DB:
        logger.warning("NOTION_BACKLOG_DB absent : contexte du backlog non rafraîchi")
        return
    contexte = backlog.charger_contexte()
    enregistrer_contexte(contexte)
    logger.info("Contexte du backlog rangé : %d équipes", len(contexte["equipes"]))
