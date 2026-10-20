"""Cohérence des connaissances de l'agent — couloir hermétique, aucun accès aux bases."""

import json
import re
import warnings
from collections import Counter
from datetime import date
from pathlib import Path

import pytest
import yaml

from lib import knowledge_lint

REPO = Path(__file__).parent.parent
TODAY = date(2026, 10, 12)

AGENT = """# Consignes

## Sources de données

- **autometa_tables_db** est la base centrale, prioritaire sur Metabase pour toute donnée qui s'y trouve déjà.

## Sites web

| Site | URL | ID Matomo | Fiche knowledge |
|---|---|---|---|
| Plateforme (ex-Emplois) | plateforme.inclusion.gouv.fr | 117 | plateforme.md |
| Site institutionnel | inclusion.gouv.fr | 212 | institutionnel.md |
"""
SKILL = """---
name: autometa_tables_db
description: Base centrale.
---

## Règles de sélection des tables

Ne jamais requêter une table qui ne figure ni parmi les tables de référence ni dans le catalogue.

## Tables de référence

| Domaine | Tables |
|---|---|
| Emplois | `candidats` |
"""
SOURCES = {
    "metabase": {"stats": {"url": "https://stats"}, "dora": {"url": "https://dora"}},
    "matomo": {"inclusion": {"url": "https://matomo"}},
    "autometa_tables_db": {"database_url": "x"},
    "tag_manager": {
        "sites": [
            {"name": "Emplois", "matomo_id": 117, "container_id": "TlN6Ou1K"},
            {"name": "Site institutionnel", "matomo_id": 212, "container_id": "SAGWfnKo"},
        ]
    },
}
CATALOG = {"source": "autometa_tables_db", "extracted_at": "2026-10-12", "documented_tables": ["int_archive"], "tables": {
    "public.candidats": ["id", "date_inscription"],
    "raw_dora.stats_mobilisationevent": ["id", "user_id"],
    "public_intermediate.int_iMER": ["kind", "date"],
    "monrecap.Contacts": ["id"],
}}  # fmt: skip


def knowledge(body: str, source: str = "metabase:stats", checked: str = "2026-10-01") -> str:
    return f"---\nsource: {source}\nverifie_le: {checked}\n---\n{body}"


def make_repo(tmp_path: Path, files: dict[str, str] | None = None, sources: dict | None = None) -> Path:
    contents = {
        "AGENT.md": AGENT,
        "skills/autometa_tables_db/SKILL.md": SKILL,
        "config/sources.yaml": yaml.safe_dump(sources or SOURCES, allow_unicode=True),
        "lib/reel.py": "def presente():\n    return 1\n",
        **(files or {}),
    }
    for name, text in contents.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text)
    return tmp_path


def messages(found: list[knowledge_lint.Finding]) -> str:
    return "\n".join(map(str, found))


@pytest.mark.parametrize(
    "body,expected",
    [
        ("Voir `knowledge/absente.md`.", "chemin introuvable : knowledge/absente.md"),
        ("Voir [la fiche](../sites/absente.md).", "lien introuvable : ../sites/absente.md"),
        ("```python\nfrom lib.inexistant import quelque_chose\n```", "module introuvable : lib.inexistant"),
        ("```python\nfrom lib.reel import presente, absente\n```", "lib.reel ne définit pas absente"),
    ],
)
def test_dod_1_une_reference_introuvable_est_nommee_avec_sa_ligne(tmp_path, body, expected):
    root = make_repo(tmp_path, {"knowledge/stats/fiche.md": knowledge(body)})
    found = knowledge_lint.dead_references(root)
    assert [(f.path, f.line) for f in found] == [("knowledge/stats/fiche.md", 5 + body.startswith("```"))]
    assert expected in found[0].message


def test_dod_1_une_reference_existante_passe(tmp_path):
    body = "`lib/reel.py`, [consignes](../../AGENT.md)\n```python\nfrom lib.reel import presente\n```"
    root = make_repo(tmp_path, {"knowledge/stats/fiche.md": knowledge(body)})
    assert knowledge_lint.dead_references(root) == []


@pytest.mark.parametrize(
    "files,sources,expected",
    [
        ({"knowledge/a.md": knowledge("| Site | ID Matomo |\n|---|---|\n| Plateforme | 212 |")}, None,
         "« Plateforme » associé au site 212, le tableau des sites lui donne le 117"),
        ({"knowledge/a.md": knowledge("Le site Plateforme (inclusion.gouv.fr) a baissé.")}, None,
         "qui désigne Site institutionnel (212)"),
        ({"knowledge/a.md": knowledge("| Site | ID | Conteneur |\n|---|---|---|\n| Emplois | 117 | oBBrLa4S |")}, None,
         "conteneur oBBrLa4S pour le site 117, config/sources.yaml dit TlN6Ou1K"),
        ({}, {**SOURCES, "tag_manager": {"sites": [{"name": "Plateforme", "matomo_id": 212, "container_id": "x"}]}},
         "« Plateforme » porte le site 212, le tableau des sites lui donne le 117"),
        ({"knowledge/a.md": knowledge("- URL : https://plateforme.inclusion.beta.gouv.fr")}, None,
         "adresse plateforme.inclusion.beta.gouv.fr pour Plateforme, le tableau des sites dit plateforme.inclusion.gouv.fr"),
    ],
)  # fmt: skip
def test_dod_2_un_site_contredisant_le_tableau_des_sites_est_refuse(tmp_path, files, sources, expected):
    root = make_repo(tmp_path, files, sources)
    assert expected in messages(knowledge_lint.site_conflicts(root))


def test_dod_2_un_conteneur_mal_nomme_pointe_sa_ligne_de_config(tmp_path):
    config = yaml.safe_dump({k: v for k, v in SOURCES.items() if k != "tag_manager"}) + (
        "tag_manager:\n  sites:\n    - name: Plateforme\n      matomo_id: 212\n      container_id: x\n"
    )
    found = knowledge_lint.site_conflicts(make_repo(tmp_path, {"config/sources.yaml": config}))
    assert [(f.path, f.line) for f in found] == [
        ("config/sources.yaml", config.splitlines().index("    - name: Plateforme") + 1)
    ]


@pytest.mark.parametrize(
    "call",
    ['execute_metabase_query(instance="pilotage", sql=sql)', 'execute_metabase_query(\n    instance="pilotage",\n)'],
)
def test_dod_2_une_instance_metabase_inconnue_est_refusee(tmp_path, call):
    root = make_repo(tmp_path, {"knowledge/a.md": knowledge(f"```python\n{call}\n```")})
    assert [str(f) for f in knowledge_lint.unknown_metabase_instances(root)] == [
        "knowledge/a.md:6 — instance Metabase inconnue : pilotage"
    ]


def test_dod_2_une_ancienne_adresse_citee_comme_donnee_passe(tmp_path):
    body = "| Page | Visites |\n|---|---|\n| `https://plateforme.inclusion.beta.gouv.fr/` | 12 |"
    assert knowledge_lint.site_conflicts(make_repo(tmp_path, {"knowledge/a.md": knowledge(body)})) == []


def test_dod_2_un_site_conforme_passe(tmp_path):
    body = "| Site | ID Matomo |\n|---|---|\n| Emplois | 117 |\n\nLe Site institutionnel (212) est distinct de Dora (212 services)."
    root = make_repo(tmp_path, {"knowledge/a.md": knowledge(body)})
    assert knowledge_lint.site_conflicts(root) == []


@pytest.mark.parametrize(
    "text,expected",
    [
        ("# Sans en-tête", "« source » (la source décrite) est requis"),
        ("---\nsource: metabase:pilotage\nverifie_le: 2026-10-01\n---\n", "source inconnue : metabase:pilotage"),
        ("---\nsource: metabase:stats\n---\n", "« verifie_le » (AAAA-MM-JJ) est requis"),
    ],
)
def test_dod_3_une_fiche_sans_source_ni_date_de_verification_est_refusee(tmp_path, text, expected):
    root = make_repo(tmp_path, {"knowledge/a.md": text})
    assert expected in messages(knowledge_lint.front_matter_problems(root))


def test_dod_3_une_fiche_ancienne_est_signalee_sans_bloquer(tmp_path):
    root = make_repo(tmp_path, {"knowledge/a.md": knowledge("# Fiche", checked="2026-01-02")})
    assert [f.path for f in knowledge_lint.stale_documents(root, TODAY)] == ["knowledge/a.md"]
    assert knowledge_lint.findings(root) == []


def test_dod_3_les_fiches_du_depot_sont_signalees_quand_elles_vieillissent():
    stale = knowledge_lint.stale_documents(REPO, date.today())
    for finding in stale:
        warnings.warn(f"fiche à revérifier : {finding}", stacklevel=1)
    assert not knowledge_lint.front_matter_problems(REPO), messages(knowledge_lint.front_matter_problems(REPO))


def test_dod_4_une_regle_recopiee_ailleurs_est_refusee_et_ses_deux_endroits_nommes(tmp_path):
    copy = "Autometa_tables_db est la base centrale, prioritaire sur Metabase pour toute donnée qui s'y trouve."
    root = make_repo(tmp_path, {"knowledge/a.md": knowledge(copy), "CLAUDE.md": f"# Dev\n\n- {copy}\n"})
    found = knowledge_lint.copied_rules(root)
    assert {f.path for f in found} == {"knowledge/a.md", "CLAUDE.md"}
    assert all("recopie la règle de AGENT.md:5" in f.message for f in found)


def test_dod_4_une_regle_de_choix_des_tables_recopiee_est_refusee(tmp_path):
    copy = "Ne jamais requêter une table qui ne figure ni parmi les tables de référence ni dans le catalogue."
    found = knowledge_lint.copied_rules(make_repo(tmp_path, {"knowledge/a.md": knowledge(copy)}))
    assert [str(f) for f in found] == [
        "knowledge/a.md:5 — recopie la règle de skills/autometa_tables_db/SKILL.md:8, qui doit rester seule — y renvoyer"
    ]


def test_dod_4_un_renvoi_vers_la_regle_passe(tmp_path):
    root = make_repo(tmp_path, {"CLAUDE.md": "Choix des sources : voir la section dédiée d'`AGENT.md`.\n"})
    assert knowledge_lint.copied_rules(root) == []


def test_dod_4_les_regles_de_choix_des_sources_ne_vivent_qu_a_un_endroit():
    assert knowledge_lint.copied_rules(REPO) == [], messages(knowledge_lint.copied_rules(REPO))


def test_dod_5_une_affirmation_refutee_ne_revient_pas(tmp_path):
    refutations = yaml.safe_dump(
        [{"motif": "Je suis intéressé", "raison": "aucun bouton de ce nom"}], allow_unicode=True
    )
    root = make_repo(
        tmp_path, {"knowledge/refutations.yaml": refutations, "knowledge/a.md": knowledge('Clics "Je suis intéressé".')}
    )
    assert [str(f) for f in knowledge_lint.refuted_claims(root)] == [
        "knowledge/a.md:5 — affirmation réfutée « Je suis intéressé » : aucun bouton de ce nom"
    ]


def test_dod_5_une_affirmation_refutee_dans_certains_fichiers_n_y_est_cherchee_que_la(tmp_path):
    refutations = yaml.safe_dump([{"motif": "master", "raison": "renommée en main", "fichiers": ["AGENT.md"]}])
    files = {
        "knowledge/refutations.yaml": refutations,
        "AGENT.md": f"{AGENT}\nBranche master.\n",
        "knowledge/a.md": knowledge("Branche master."),
    }
    assert [f.path for f in knowledge_lint.refuted_claims(make_repo(tmp_path, files))] == ["AGENT.md"]


def test_dod_5_la_fiche_dora_decrit_les_vraies_mobilisations():
    dora = (REPO / "knowledge/dora/README.md").read_text()
    assert knowledge_lint.refuted_claims(REPO) == [], messages(knowledge_lint.refuted_claims(REPO))
    assert "suis intéressé" not in dora.lower()
    for evidence in ("trackMobilisation", "Orienter votre bénéficiaire", "coordonnées", "external_link"):
        assert evidence in dora


def test_dod_6_la_fiche_dora_et_le_skill_donnent_la_meme_route():
    dora = (REPO / "knowledge/dora/README.md").read_text()
    first_sql = dora.index("```sql")
    assert knowledge_lint.declared_sources(knowledge_lint.front_matter(dora)) == ["metabase:dora"]
    assert -1 < dora.find("fct_dora__imer") < first_sql
    assert -1 < dora.find("skill `autometa_tables_db`") < first_sql
    assert "à confirmer" in dora


def test_dod_6_les_actes_metier_renvoient_a_la_definition_de_l_imer():
    actes = (REPO / "knowledge/stats/actes-metier.md").read_text()
    imer = actes[actes.index("### Dora — iMER") :].split("\n### ")[0]
    assert "knowledge/dora/README.md" in imer
    assert "n'est pas l'iMER complet" in imer
    assert "double compte" in imer


def test_dod_7_l_ordre_de_priorite_est_ecrit_une_seule_fois_dans_les_consignes():
    lines = [
        line for _, line in knowledge_lint.section((REPO / "AGENT.md").read_text(), "Quand deux consignes divergent")
    ]
    ranks = [line for line in lines if re.match(r"\d+\. ", line)]
    positions = [next(i for i, line in enumerate(ranks) if word in line) for word in ("catalogue", "skill", "fiche")]
    assert positions == sorted(positions)
    assert any("signaler" in line for line in lines)
    others = [d for d in knowledge_lint.documents(REPO) if d.name != "AGENT.md"]
    assert not [d for d in others if knowledge_lint.section(d.read_text(), "Quand deux consignes divergent")]


def test_dod_8_le_depot_ne_porte_plus_aucune_incoherence_detectable():
    assert knowledge_lint.findings(REPO) == [], messages(knowledge_lint.findings(REPO))


def test_dod_8_le_repli_metabase_connait_toutes_les_instances():
    configured = yaml.safe_load((REPO / "config/sources.yaml").read_text())["metabase"]
    instances = {name for name in configured if not name.startswith("_")} - {"data_inclusion"}
    skill = (REPO / "skills/metabase_query/SKILL.md").read_text()
    assert all(f"`{name}`" in skill for name in instances)


@pytest.mark.parametrize(
    "sql,expected",
    [
        ("SELECT * FROM public.absente", "table absente du catalogue : public.absente"),
        ("SELECT c.nom FROM candidats c", "colonne absente du catalogue : c.nom"),
        ("SELECT me.id FROM raw_dora.stats_mobilisationevent me JOIN fantome f ON f.id = me.id",
         "table absente du catalogue : fantome"),
        ("SELECT * FROM public_intermediate.int_imer", "table absente du catalogue : public_intermediate.int_imer"),
        ('SELECT i.Kind FROM public_intermediate."int_iMER" i', "colonne absente du catalogue : i.Kind"),
    ],
)  # fmt: skip
def test_dod_9_une_table_ou_colonne_absente_du_catalogue_est_nommee(tmp_path, sql, expected):
    files = {
        "knowledge/a.md": knowledge(f"```sql\n{sql}\n```", source="autometa_tables_db"),
        "knowledge/catalog/autometa_tables_db.json": json.dumps(CATALOG),
    }
    found = knowledge_lint.catalog_problems(make_repo(tmp_path, files))
    assert [(f.path, f.line, f.message) for f in found] == [("knowledge/a.md", 6, expected)]


@pytest.mark.parametrize(
    "sql",
    [
        "WITH recents AS (SELECT id FROM candidats)\n"
        "SELECT c.id, EXTRACT(YEAR FROM c.date_inscription) FROM public.candidats AS c JOIN recents r ON r.id = c.id",
        'SELECT i.kind FROM public_intermediate."int_iMER" i',
        "SELECT * FROM int_archive",
        "-- compte les candidats from la base\nSELECT * FROM candidats",
        "SELECT table_name FROM information_schema.tables",
    ],
)
def test_dod_9_une_requete_conforme_au_catalogue_passe(tmp_path, sql):
    files = {
        "knowledge/a.md": knowledge(f"```sql\n{sql}\n```", source="autometa_tables_db"),
        "knowledge/catalog/autometa_tables_db.json": json.dumps(CATALOG),
    }
    assert knowledge_lint.catalog_problems(make_repo(tmp_path, files)) == []


def test_dod_9_une_table_de_reference_absente_du_catalogue_est_nommee(tmp_path):
    catalog = {**CATALOG, "tables": {"public.autre": ["id"]}}
    root = make_repo(tmp_path, {"knowledge/catalog/autometa_tables_db.json": json.dumps(catalog)})
    assert [str(f) for f in knowledge_lint.catalog_problems(root)] == [
        "skills/autometa_tables_db/SKILL.md:14 — table de référence absente du catalogue : candidats"
    ]


@pytest.mark.parametrize(("cited", "expected"), [("`Contacts`", []), ("`contacts`", ["contacts"])])
def test_dod_9_la_casse_des_tables_de_reference_compte(tmp_path, cited, expected):
    files = {
        "skills/autometa_tables_db/SKILL.md": SKILL.replace("`candidats`", cited),
        "knowledge/catalog/autometa_tables_db.json": json.dumps(CATALOG),
    }
    found = knowledge_lint.catalog_problems(make_repo(tmp_path, files))
    assert [f.message.rsplit(" ", 1)[1] for f in found] == expected


def test_dod_9_les_sources_du_depot_sans_instantane_sont_signalees():
    missing = Counter(f.message for f in knowledge_lint.uncatalogued(REPO))
    for message, count in missing.items():
        warnings.warn(f"{message} ({count} documents)", stacklevel=1)
    for finding in knowledge_lint.stale_catalogs(REPO, date.today()):
        warnings.warn(str(finding), stacklevel=1)
    found = knowledge_lint.catalog_problems(REPO)
    assert found == [], f"{messages(found)}\nTable réelle absente de l'instantané : régénérer avec `make catalog`."


def test_dod_9_un_instantane_ancien_est_signale_sans_bloquer(tmp_path):
    catalog = {**CATALOG, "extracted_at": "2026-01-02"}
    root = make_repo(tmp_path, {"knowledge/catalog/autometa_tables_db.json": json.dumps(catalog)})
    assert [str(f) for f in knowledge_lint.stale_catalogs(root, TODAY)] == [
        "knowledge/catalog/autometa_tables_db.json:1 — extrait le 2026-01-02, il y a plus de 180 jours "
        "— régénérer : make catalog"
    ]
    assert knowledge_lint.stale_catalogs(root, date(2026, 6, 1)) == []
    assert knowledge_lint.findings(root) == []


def test_dod_9_sans_instantane_la_source_est_signalee_et_ses_tables_non_controlees(tmp_path):
    root = make_repo(
        tmp_path, {"knowledge/a.md": knowledge("```sql\nSELECT * FROM absente\n```", "autometa_tables_db")}
    )
    assert knowledge_lint.catalog_problems(root) == []
    assert {f.path for f in knowledge_lint.uncatalogued(root)} == {
        "knowledge/a.md",
        "skills/autometa_tables_db/SKILL.md",
    }
