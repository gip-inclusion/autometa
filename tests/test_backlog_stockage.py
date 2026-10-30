from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete

from lib import backlog_stockage
from lib.backlog_stockage import backlog_contexte
from web.db import get_engine


def contexte(age=timedelta(0), equipes=None):
    return {"genere_le": (datetime.now(UTC) - age).isoformat(), "equipes": equipes or []}


def test_dod_2_contexte_courant_relit_notion_et_range_si_rien_n_est_frais(mocker):
    neuf = contexte()
    mocker.patch.object(backlog_stockage, "lire_contexte", return_value=None)
    charger = mocker.patch.object(backlog_stockage.backlog, "charger_contexte", return_value=neuf)
    range_ = mocker.patch.object(backlog_stockage, "enregistrer_contexte")
    assert backlog_stockage.contexte_courant() == neuf
    charger.assert_called_once()
    range_.assert_called_once_with(neuf)


def test_dod_2_contexte_courant_frais_ne_relit_pas_notion(mocker):
    frais = contexte(timedelta(hours=3))
    mocker.patch.object(backlog_stockage, "lire_contexte", return_value=frais)
    charger = mocker.patch.object(backlog_stockage.backlog, "charger_contexte")
    range_ = mocker.patch.object(backlog_stockage, "enregistrer_contexte")
    assert backlog_stockage.contexte_courant() == frais
    charger.assert_not_called()
    range_.assert_not_called()


def test_main_sans_configuration_ne_lit_pas_notion(mocker):
    mocker.patch.object(backlog_stockage.config, "NOTION_BACKLOG_DB", None)
    charger = mocker.patch.object(backlog_stockage.backlog, "charger_contexte")
    backlog_stockage.main()
    charger.assert_not_called()


def test_main_configure_charge_une_fois_et_range(mocker):
    neuf = contexte()
    mocker.patch.object(backlog_stockage.config, "NOTION_BACKLOG_DB", "db-factice")
    charger = mocker.patch.object(backlog_stockage.backlog, "charger_contexte", return_value=neuf)
    range_ = mocker.patch.object(backlog_stockage, "enregistrer_contexte")
    backlog_stockage.main()
    charger.assert_called_once()
    range_.assert_called_once_with(neuf)


@pytest.fixture
def table_vide():
    backlog_stockage.ensure_schema()
    with get_engine().begin() as conn:
        conn.execute(delete(backlog_contexte))
    yield


@pytest.mark.integration
@pytest.mark.usefixtures("_db", "table_vide")
class TestStockage:
    def test_dod_2_ecrire_puis_lire_renvoie_le_meme_contexte(self):
        ctx = contexte(timedelta(hours=1), [{"id": "e1", "nom": "Equipe", "epics": [], "tickets_recents": ["t"]}])
        backlog_stockage.enregistrer_contexte(ctx)
        assert backlog_stockage.lire_contexte() == ctx

    def test_lire_sans_table_renvoie_none(self):
        backlog_contexte.drop(get_engine(), checkfirst=True)
        assert backlog_stockage.lire_contexte() is None

    def test_lire_sans_ligne_renvoie_none(self):
        assert backlog_stockage.lire_contexte() is None

    @pytest.mark.parametrize(
        ("ecart", "attendu_present"),
        [(timedelta(minutes=-1), True), (timedelta(minutes=1), False)],
    )
    def test_dod_2_fraicheur_autour_de_la_limite(self, ecart, attendu_present):
        age_max = timedelta(hours=30)
        ctx = contexte(age_max + ecart)
        backlog_stockage.enregistrer_contexte(ctx)
        assert (backlog_stockage.lire_contexte(age_max) == ctx) is attendu_present

    def test_un_chargement_plus_ancien_n_ecrase_pas_un_plus_recent(self):
        recent = contexte(timedelta(hours=1), [{"id": "recent"}])
        ancien = contexte(timedelta(hours=5), [{"id": "ancien"}])
        backlog_stockage.enregistrer_contexte(recent)
        backlog_stockage.enregistrer_contexte(ancien)
        assert backlog_stockage.lire_contexte() == recent
