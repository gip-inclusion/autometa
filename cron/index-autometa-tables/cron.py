"""Recrée les index d'autometa_tables_db, supprimés à chaque reconstruction des tables. Périodique."""

import logging

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

from web import config

logger = logging.getLogger(__name__)

# Colonnes fréquemment utilisées en WHERE/JOIN par l'agent. Les tables sont reconstruites
# chaque nuit par le DAG populate_matometa_db (pilotage-airflow) avec if_exists="replace",
# ce qui supprime les index — d'où la recréation quotidienne ici.
INDEXES = {
    ("les_emplois", "candidats"): [("id",), ("département",)],
    ("les_emplois", "candidatures_echelle_locale"): [
        ("id_candidat",),
        ("id_structure",),
        ("id_org_prescripteur",),
        ("date_candidature",),
        ("état",),
        ("département_structure",),
    ],
    ("les_emplois", "fiches_de_poste_par_candidature"): [("id_candidature",), ("id_fiche_de_poste",)],
    ("les_emplois", "structures"): [("id",), ("département",), ("type",), ("siret",)],
    ("les_emplois", "prolongations"): [("id_pass_agrément",)],
    ("les_emplois", "organisations"): [("id",), ("département",), ("type",)],
    ("les_emplois", "utilisateurs"): [("id",), ("type",)],
    ("les_emplois", "pass_agréments"): [
        ("id",),
        ("id_candidat",),
        ("id_structure",),
        ("date_début",),
        ("date_fin",),
    ],
    ("les_emplois", "suspensions_pass"): [("id_pass_agrément",)],
    ("les_emplois", "suivi_auto_prescription"): [
        ("id_candidat",),
        ("id_structure",),
        ("date_candidature",),
        ("département_structure",),
    ],
    ("asp", "fluxIAE_Structure_v2"): [("structure_id_siae",)],
    ("asp", "suivi_realisation_convention_par_structure"): [
        ("id_annexe_financiere",),
        ("structure_id_siae",),
        ("annee_af",),
    ],
    ("asp", "suivi_realisation_convention_mensuelle"): [
        ("id_annexe_financiere",),
        ("structure_id_siae",),
        ("annee_af",),
    ],
    ("asp", "suivi_etp_conventionnes_v2"): [("id_annexe_financiere",), ("structure_id_siae",), ("annee_af",)],
    ("asp", "fluxIAE_ContratMission_v2"): [
        ("contrat_id_ctr",),
        ("contrat_id_pph",),
        ("contrat_id_structure",),
        ("contrat_date_embauche",),
    ],
    ("asp", "fluxIAE_Salarie_v2"): [("salarie_id",)],
    ("monrecap", "Commandes"): [("département",)],
    ("data_inclusion", "structures_v1"): [("id",), ("source",), ("siret",), ("code_postal",)],
    ("data_inclusion", "services_v1"): [("id",), ("structure_id",), ("source",)],
    ("datalake", "pdi_base_unique_tous_les_pros"): [("email",), ("source",), ("departement_structure",)],
    ("dora", "structures_structure"): [("id",), ("department",), ("siret",)],
    ("dora", "structures_structuremember"): [("user_id",), ("structure_id",)],
    ("dora", "services_service"): [("id",), ("structure_id",), ("status",)],
    ("dora", "services_service_categories"): [("service_id",), ("servicecategory_id",)],
    ("dora", "orientations_orientation"): [
        ("id",),
        ("service_id",),
        ("prescriber_structure_id",),
        ("creation_date",),
    ],
    ("dora", "users_user"): [("id",), ("email",)],
    ("dora", "stats_searchview"): [("date",), ("department",), ("user_kind",)],
    ("dora", "stats_serviceview"): [
        ("date",),
        ("structure_department",),
        ("user_kind",),
        ("service_id",),
        ("structure_id",),
    ],
    ("dora", "stats_mobilisationevent"): [("date",), ("structure_department",), ("user_kind",), ("service_id",)],
    ("dora", "stats_structureinfosview"): [("date",), ("structure_department",), ("structure_id",)],
    ("dora", "stats_structureview"): [("date",), ("structure_department",), ("user_kind",), ("structure_id",)],
}


def table_statements(schema: str, table: str, columns_list: list[tuple[str, ...]]) -> list[str]:
    statements = []
    for columns in columns_list:
        # PostgreSQL tronque les identifiants au-delà de 63 octets ; le slice garde un nom stable pour IF NOT EXISTS.
        name = f"idx_{table}_{'_'.join(columns)}"[:63]
        cols = ", ".join(f'"{col}"' for col in columns)
        statements.append(f'CREATE INDEX IF NOT EXISTS "{name}" ON "{schema}"."{table}" ({cols})')
    statements.append(f'ANALYZE "{schema}"."{table}"')
    return statements


def main() -> None:
    if not config.AUTOMETA_TABLES_DATABASE_URL:
        logger.info("AUTOMETA_TABLES_DATABASE_URL not configured; skipping")
        return

    # Why: prod et staging partagent la même autometa_tables_db ; deux runs concurrents font
    # courir CREATE INDEX IF NOT EXISTS (collision pg_class). Seul prod entretient les index.
    if not config.ENV.owns_shared_db:
        logger.info("AUTOMETA_ENV=%s (not prod); skipping to avoid racing prod on the shared DB", config.ENV.value)
        return

    # Why: AUTOCOMMIT — chaque statement est indépendant, un échec n'avorte pas les suivants.
    engine = create_engine(
        config.AUTOMETA_TABLES_DATABASE_URL,
        poolclass=NullPool,
        isolation_level="AUTOCOMMIT",
        connect_args={"options": "-c statement_timeout=600000", "connect_timeout": 10},
    )
    failures = []
    with engine.connect() as conn:
        for (schema, table), columns_list in INDEXES.items():
            for statement in table_statements(schema, table, columns_list):
                try:
                    conn.execute(text(statement))
                except SQLAlchemyError as exc:
                    logger.warning("statement failed: %s (%s)", statement, exc)
                    failures.append(f"{statement} — {exc}")
            logger.info("indexed and analyzed %s.%s", schema, table)

    if failures:
        raise RuntimeError(f"{len(failures)} statements failed:\n" + "\n".join(failures))
    logger.info("recreated indexes for %d tables", len(INDEXES))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
