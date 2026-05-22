"""Test-only schema bootstrap and tag taxonomy seed. Production schema is managed by Alembic."""

from sqlalchemy import text

from .db import get_db, init_tables


def init_db():
    """Initialize database schema via SQLAlchemy models."""
    init_tables()
    with get_db() as session:
        seed_tags(session)


TAGS = [
    ("emplois", "product", "Emplois"),
    ("dora", "product", "Dora"),
    ("marche", "product", "Marché"),
    ("communaute", "product", "Communauté"),
    ("pilotage", "product", "Pilotage"),
    ("plateforme", "product", "Plateforme"),
    ("rdv-insertion", "product", "RDV-Insertion"),
    ("mon-recap", "product", "Mon Récap"),
    ("multi", "product", "Multi-produits"),
    ("matomo", "source", "Matomo"),
    ("stats", "source", "Metabase stats"),
    ("datalake", "source", "Metabase datalake"),
    ("candidats", "theme", "Candidats"),
    ("prescripteurs", "theme", "Prescripteurs"),
    ("employeurs", "theme", "Employeurs"),
    ("structures", "theme", "Structures / SIAE"),
    ("acheteurs", "theme", "Acheteurs"),
    ("fournisseurs", "theme", "Fournisseurs"),
    ("iae", "theme", "IAE"),
    ("orientation", "theme", "Orientation"),
    ("depot-de-besoin", "theme", "Dépôt de besoin"),
    ("demande-de-devis", "theme", "Demande de devis"),
    ("commandes", "theme", "Commandes"),
    ("trafic", "theme", "Trafic"),
    ("conversions", "theme", "Conversions"),
    ("retention", "theme", "Rétention"),
    ("geographique", "theme", "Géographique"),
    ("extraction", "type_demande", "Extraction"),
    ("analyse", "type_demande", "Analyse"),
    ("appli", "type_demande", "Appli"),
    ("meta", "type_demande", "Meta"),
]


def seed_tags(session):
    """Seed the tags table with taxonomy."""
    for name, type_, label in TAGS:
        session.execute(
            text("INSERT INTO tags (name, type, label) VALUES (:name, :type, :label) ON CONFLICT (name) DO NOTHING"),
            {"name": name, "type": type_, "label": label},
        )
