from datetime import UTC, datetime, timedelta

import pytest

from lib import backlog_stockage
from lib.query import QueryResult


def resultat(lignes=None):
    return QueryResult(
        success=True,
        data={"columns": ["contenu", "genere_le"], "rows": lignes or [], "row_count": len(lignes or [])},
    )


def contexte(age):
    return {"genere_le": (datetime.now(UTC) - age).isoformat(), "equipes": []}


def test_dod_2_lire_contexte_renvoie_le_contexte_frais(mocker):
    frais = contexte(timedelta(hours=3))
    mocker.patch.object(
        backlog_stockage, "query_storage", side_effect=[resultat(), resultat([[frais, frais["genere_le"]]])]
    )
    assert backlog_stockage.lire_contexte() == frais


def test_dod_2_lire_contexte_perime_renvoie_none(mocker):
    vieux = contexte(timedelta(days=2))
    mocker.patch.object(
        backlog_stockage, "query_storage", side_effect=[resultat(), resultat([[vieux, vieux["genere_le"]]])]
    )
    assert backlog_stockage.lire_contexte() is None


def test_dod_2_contexte_courant_relit_notion_et_range_si_rien_n_est_frais(mocker):
    neuf = contexte(timedelta(0))
    mocker.patch.object(backlog_stockage, "lire_contexte", return_value=None)
    mocker.patch.object(backlog_stockage.backlog, "charger_contexte", return_value=neuf)
    range_ = mocker.patch.object(backlog_stockage, "enregistrer_contexte")
    assert backlog_stockage.contexte_courant() == neuf
    range_.assert_called_once_with(neuf)


def test_enregistrer_contexte_cree_la_table_puis_ecrit(mocker):
    stockage = mocker.patch.object(backlog_stockage, "query_storage", return_value=resultat())
    backlog_stockage.enregistrer_contexte(contexte(timedelta(0)))
    assert stockage.call_args_list[0].args[0] == backlog_stockage.CREER
    assert stockage.call_args_list[1].args[0] == backlog_stockage.ECRIRE
    assert '"equipes": []' in stockage.call_args_list[1].args[1]["contenu"]


def test_echec_du_stockage_leve_une_erreur(mocker):
    mocker.patch.object(
        backlog_stockage, "query_storage", return_value=QueryResult(success=False, data=None, error="refus")
    )
    with pytest.raises(RuntimeError, match="refus"):
        backlog_stockage.lire_contexte()


def test_main_sans_configuration_ne_lit_pas_notion(mocker):
    mocker.patch.object(backlog_stockage.config, "NOTION_BACKLOG_DB", None)
    charger = mocker.patch.object(backlog_stockage.backlog, "charger_contexte")
    backlog_stockage.main()
    charger.assert_not_called()
