import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "check_paved_road", Path(__file__).parent.parent / "scripts" / "check_paved_road.py"
)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


DEFINITION = """# Télécharger un rapport

## Ce qui devra marcher

DOD-1 — Quand je clique sur « Télécharger », alors un fichier se
  télécharge, au lieu de s'afficher dans un onglet.

DOD-2 — Le fichier porte le titre du rapport.

## Questions ouvertes

Aucune.
"""

ATTESTATION = """# DOD-1

**Critère** — Quand je clique sur « Télécharger », un fichier se télécharge.

**Commande** — `true`

**Code de sortie** — 0

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `aaa008c06fa8b56ac7d2a770e599491cba675106` |

**Verdict** — démontré.
"""


def parcours(tmp_path, definition=DEFINITION, attestations=("DOD-1", "DOD-2")):
    dossier = tmp_path / "telecharger-rapport"
    (dossier / "attestations").mkdir(parents=True)
    (dossier / "definition-of-done.md").write_text(definition)
    for identifiant in attestations:
        (dossier / "attestations" / f"{identifiant}.md").write_text(ATTESTATION.replace("DOD-1", identifiant))
    return dossier


@pytest.mark.parametrize(
    ("fichiers", "applicable"),
    [
        (["web/routes/reports.py"], True),
        (["lib/matomo.py"], True),
        (["skills/rpe/scripts/query.py"], True),
        (["alembic/versions/abc.py"], True),
        (["docs/plans/design.md"], False),
        (["knowledge/sites/dora.md"], False),
        (["uv.lock", "pyproject.toml"], False),
        ([], False),
    ],
)
def test_le_declencheur_de_perimetre(fichiers, applicable):
    texte, code = _module.rapport(fichiers, [])

    assert code == (1 if applicable else 0)
    assert ("rien à démontrer ici" in texte) is not applicable


def test_le_label_break_glass_leve_le_check_et_journalise_la_dispense():
    texte, code = _module.rapport(["web/routes/reports.py"], ["break-glass"])

    assert code == 0
    assert "break-glass" in texte
    assert "`web/routes/reports.py`" in texte


def test_un_diff_dans_le_perimetre_sans_definition_of_done_echoue_en_famille_c():
    texte, code = _module.rapport(["web/routes/reports.py"], ["documentation"])

    assert code == 1
    assert "**Famille C**" in texte


def test_le_script_lit_les_criteres_avec_le_meme_analyseur_que_prove():
    """Un seul analyseur : deux lectures divergentes du même contrat, c'est un contrat de moins."""
    assert _module.attestation.criteria(DEFINITION) == {
        "DOD-1": "Quand je clique sur « Télécharger », alors un fichier se télécharge, au lieu de s'afficher dans un onglet.",
        "DOD-2": "Le fichier porte le titre du rapport.",
    }


def test_une_attestation_se_lit_avec_le_meme_lecteur_que_prove():
    preuve = _module.attestation.parse_attestation(ATTESTATION)

    assert (preuve.command, preuve.exit_code, preuve.proven) == ("true", 0, True)


def test_le_parcours_est_vert_quand_chaque_critere_est_rejoue_avec_son_code_de_sortie(tmp_path, mocker):
    mocker.patch.object(_module, "empreinte_courante", return_value="aaa008c06fa8b56ac7d2a770e599491cba675106")

    attendus, echecs = _module.verifier_parcours(parcours(tmp_path))

    assert list(attendus) == ["DOD-1", "DOD-2"]
    assert echecs == []


def test_une_preuve_devient_perimee_quand_le_contenu_prouve_a_change(tmp_path, mocker):
    mocker.patch.object(_module, "empreinte_courante", return_value="0" * 40)

    _, echecs = _module.verifier_parcours(parcours(tmp_path))

    assert [echec.famille for echec in echecs] == ["A", "A"]
    assert "la preuve est périmée" in echecs[0].phrase


def test_un_critere_sans_attestation_n_est_pas_demontre(tmp_path, mocker):
    mocker.patch.object(_module, "empreinte_courante", return_value="aaa008c06fa8b56ac7d2a770e599491cba675106")

    _, echecs = _module.verifier_parcours(parcours(tmp_path, attestations=("DOD-1",)))

    assert [(echec.famille, echec.critere) for echec in echecs] == [("A", "DOD-2")]


def test_la_ci_rejoue_et_son_resultat_l_emporte_sur_le_verdict_journalise(tmp_path, mocker):
    """Le journal est un cache et une source de statistiques, pas une autorité."""
    mocker.patch.object(_module, "empreinte_courante", return_value="aaa008c06fa8b56ac7d2a770e599491cba675106")
    dossier = parcours(tmp_path)
    menteuse = ATTESTATION.replace("**Commande** — `true`", "**Commande** — `false`")
    (dossier / "attestations" / "DOD-1.md").write_text(menteuse)

    _, echecs = _module.verifier_parcours(dossier)

    assert [(echec.famille, echec.critere) for echec in echecs] == [("A", "DOD-1")]
    assert "le rejeu renvoie 1" in echecs[0].phrase


def test_un_service_absent_est_une_panne_et_non_un_travail_a_reprendre(tmp_path, mocker):
    mocker.patch.object(_module, "empreinte_courante", return_value="aaa008c06fa8b56ac7d2a770e599491cba675106")
    mocker.patch.object(_module.attestation, "run_command", return_value=(4, "psql: Connection refused"))
    dossier = parcours(tmp_path, attestations=("DOD-1",))

    _, echecs = _module.verifier_parcours(dossier)

    assert echecs[0].famille == "B"
    assert "l'environnement" in echecs[0].phrase


def test_un_fichier_non_markdown_sous_attestations_est_interdit(tmp_path, mocker):
    mocker.patch.object(_module, "empreinte_courante", return_value="aaa008c06fa8b56ac7d2a770e599491cba675106")
    dossier = parcours(tmp_path)
    (dossier / "attestations" / "capture.png").write_bytes(b"\x89PNG")

    _, echecs = _module.verifier_parcours(dossier)

    assert [echec.famille for echec in echecs] == ["D"]
    assert "le dépôt est public" in echecs[0].phrase


@pytest.mark.parametrize(
    ("definition", "manque"),
    [
        (DEFINITION.replace("## Questions ouvertes", "## Autre chose"), "Questions ouvertes"),
        ("# Titre\n\n## Ce qui devra marcher\n\nRien.\n", "aucun critère"),
    ],
)
def test_une_definition_of_done_mal_formee_est_une_question_metier(tmp_path, definition, manque):
    _, echecs = _module.verifier_parcours(parcours(tmp_path, definition=definition))

    assert echecs[0].famille == "C"
    assert manque in echecs[0].phrase


def test_les_dossiers_de_parcours_sont_ceux_que_la_branche_touche():
    fichiers = [
        "paved-road/telecharger-rapport/definition-of-done.md",
        "paved-road/telecharger-rapport/attestations/DOD-1.md",
        "paved-road/export-pdf/definition-of-done.md",
        "web/routes/reports.py",
    ]

    assert _module.dossiers_de_parcours(fichiers) == [
        Path("paved-road/export-pdf"),
        Path("paved-road/telecharger-rapport"),
    ]


def test_le_rapport_recapitule_les_criteres_demontres(tmp_path, mocker, monkeypatch):
    monkeypatch.chdir(tmp_path)
    mocker.patch.object(_module, "empreinte_courante", return_value="aaa008c06fa8b56ac7d2a770e599491cba675106")
    parcours(tmp_path / "paved-road")

    texte, code = _module.rapport(["web/routes/reports.py", "paved-road/telecharger-rapport/definition-of-done.md"], [])

    assert code == 0
    assert "# Ce qui devait marcher" in texte
    assert "| DOD-2 | Le fichier porte le titre du rapport. | démontré |" in texte
    assert "la CI les a rejoués elle-même" in texte


def test_le_rapport_nomme_ce_qui_bloque_et_sa_famille(tmp_path, mocker, monkeypatch):
    monkeypatch.chdir(tmp_path)
    mocker.patch.object(_module, "empreinte_courante", return_value="0" * 40)
    parcours(tmp_path / "paved-road")

    texte, code = _module.rapport(["lib/matomo.py", "paved-road/telecharger-rapport/definition-of-done.md"], [])

    assert code == 1
    assert "## Ce qui bloque" in texte
    assert "**non démontré**" in texte
    assert "**Famille A** — réparable" in texte


def test_un_parcours_sans_definition_of_done_dans_son_dossier(tmp_path):
    (tmp_path / "paved-road" / "export-pdf").mkdir(parents=True)

    _, echecs = _module.verifier_parcours(tmp_path / "paved-road" / "export-pdf")

    assert [echec.famille for echec in echecs] == ["C"]
    assert "rien ne dit ce qui devait marcher" in echecs[0].phrase


def test_l_empreinte_d_un_chemin_absent_de_l_arbre_est_nulle():
    assert _module.empreinte_courante("chemin/qui/n/existe/pas") is None
    assert len(_module.empreinte_courante("scripts")) == 40


def test_les_fichiers_modifies_viennent_du_diff_git(mocker):
    lance = mocker.patch.object(
        _module.subprocess, "run", return_value=mocker.Mock(stdout="web/app.py\nlib/matomo.py\n")
    )

    assert _module.fichiers_modifies("origin/main") == ["web/app.py", "lib/matomo.py"]
    assert lance.call_args[0][0] == ["git", "diff", "--name-only", "origin/main...HEAD"]


def test_main_imprime_le_rapport_et_rend_son_code(mocker, capsys):
    mocker.patch.object(_module.sys, "argv", ["check_paved_road.py", "--base", "origin/main", "--label", "break-glass"])
    mocker.patch.object(_module, "fichiers_modifies", return_value=["web/app.py"])

    assert _module.main() == 0
    assert "break-glass" in capsys.readouterr().out


@pytest.mark.parametrize("mention", ["E2E", "nightly"])
def test_une_preuve_non_rejouable_est_acceptee_sans_etre_rejouee(tmp_path, mocker, mention):
    """Ce job n'a ni navigateur ni accès nightly : rejouer rendrait la PR infusionnable."""
    mocker.patch.object(_module, "empreinte_courante", return_value="aaa008c06fa8b56ac7d2a770e599491cba675106")
    rejeu = mocker.patch.object(_module.attestation, "run_command")
    dossier = parcours(tmp_path, attestations=("DOD-1",))
    (dossier / "attestations" / "DOD-1.md").write_text(
        ATTESTATION.replace("**Verdict** — démontré.", f"**Verdict** — démontré ({mention}).")
    )

    _, echecs = _module.verifier_parcours(dossier)

    assert [echec.critere for echec in echecs] == ["DOD-2"]
    rejeu.assert_not_called()
